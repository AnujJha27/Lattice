"""Grounding context gathering for lesson generation.

Strategy (overrides §26): prefer chunks already embedded in the user's
library; if too few, discover fresh authoritative sources and use their
search snippets as provisional context (marked from_snippet=True).
"""
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser
from app.db.models import Concept, ConceptSource, Source, SourceChunk
from app.db.models.source import IngestStatus
from app.modules.sources.discovery import discover

logger = logging.getLogger(__name__)

MIN_CONTEXTS = 3


async def gather_contexts(
    session: AsyncSession, concept: Concept, k: int = 8
) -> list[dict]:
    """Returns grounding contexts as plain dicts matching SourceContext fields."""
    # 1) Vector retrieval over embedded library chunks
    contexts = await _retrieve_embedded(session, concept, k)

    # 2) Discovery fallback with snippets as provisional excerpts
    if len(contexts) < MIN_CONTEXTS:
        logger.info("lesson context thin (%d), discovering fresh sources", len(contexts))
        candidates, _raw = await discover(concept.canonical_name, concept.domain, limit=4)
        existing_urls = {c["url"] for c in contexts}
        for ranked in candidates:
            c = ranked.candidate
            if c.url in existing_urls or not c.snippet:
                continue
            # Persist so future ingestions/citations can reference the real record.
            source = await _persist_discovered(session, concept, c)
            contexts.append({
                "source_id": str(source.id),
                "title": c.title,
                "publisher": c.publisher,
                "year": c.published.year if c.published else None,
                "authors": c.authors[:5],
                "url": c.url,
                "excerpt": c.snippet,
                "from_snippet": True,
            })
            if len(contexts) >= MIN_CONTEXTS + 2:
                break

    return contexts[:k]


async def _retrieve_embedded(session: AsyncSession, concept: Concept, k: int) -> list[dict]:
    from app.providers.embedding import GeminiEmbeddingProvider

    query_text = f"{concept.canonical_name}. {concept.description or ''}"
    embedder = GeminiEmbeddingProvider()
    [query_vector] = await embedder.embed([query_text])

    distance_expr = SourceChunk.embedding.cosine_distance(query_vector)
    stmt = (
        select(SourceChunk, Source, distance_expr)
        .join(Source, Source.id == SourceChunk.source_id)
        .where(Source.ingest_status == IngestStatus.EMBEDDED)
        .order_by(distance_expr)
        .limit(k * 2)
    )

    rows = await session.execute(stmt)
    seen_sources: set[str] = set()
    contexts: list[dict] = []
    for chunk, source, _distance in rows.all():
        sid = str(source.id)
        if sid in seen_sources:  # max 1 chunk per source keeps diversity
            continue
        seen_sources.add(sid)
        contexts.append({
            "source_id": sid,
            "title": source.title,
            "publisher": source.publisher,
            "year": source.publication_date.year if source.publication_date else None,
            "authors": (source.authors or [])[:5],
            "url": source.url,
            "excerpt": chunk.content[:900],
            "from_snippet": False,
        })
        if len(contexts) >= k:
            break
    return contexts


async def _persist_discovered(session: AsyncSession, concept: Concept, candidate):
    """Persist a discovered candidate (deduped) and link it to the concept."""
    from datetime import UTC, datetime

    from sqlalchemy import select as sa_select

    from app.db.models.source import SourceOrigin, SourceType
    from app.jobs.queue import enqueue_job
    from app.modules.sources.dedup import canonicalize_url

    result = await session.execute(sa_select(Source).where(Source.url == candidate.url))
    source = result.scalar_one_or_none()
    if source is None:
        source = Source(
            title=candidate.title[:500],
            url=candidate.url,
            canonical_url=canonicalize_url(candidate.url),
            source_type=SourceType(candidate.source_type),
            origin=SourceOrigin.DISCOVERED,
            publisher=candidate.publisher,
            authors=candidate.authors or [],
            publication_date=candidate.published,
            authority_score=candidate.authority,
            doi=candidate.doi,
            arxiv_id=candidate.arxiv_id,
            retrieved_at=datetime.now(UTC),
            ingest_status=IngestStatus.PENDING,
        )
        session.add(source)
        await session.flush()

    if source.ingest_status == IngestStatus.PENDING:
        await enqueue_job(
            session, "SOURCE_INGEST", {"source_id": str(source.id)},
            dedupe_key=f"ingest:{source.id}",
        )

    link = await session.execute(
        sa_select(ConceptSource).where(
            ConceptSource.concept_id == concept.id, ConceptSource.source_id == source.id
        )
    )
    if link.scalar_one_or_none() is None:
        session.add(ConceptSource(concept_id=concept.id, source_id=source.id, relevance=0.7))

    return source


_ = CurrentUser  # reserved for per-user context scoping
