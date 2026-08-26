"""Job handlers: SOURCE_INGEST (fetch → extract → chunk → embed → index)."""
import logging
import uuid
from datetime import UTC, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Source, SourceChunk
from app.db.models.source import IngestStatus
from app.modules.sources.chunking import chunk_text
from app.modules.sources.extraction import extract_text

logger = logging.getLogger(__name__)

MAX_TEXT_CHARS = 400_000


async def handle_source_ingest(session: AsyncSession, payload: dict) -> dict:
    source_id = payload["source_id"]
    result = await session.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()
    if source is None:
        raise ValueError(f"source {source_id} not found")
    if source.url:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=30,
            headers={"User-Agent": "LatticeSourceBot/0.1 (+learning research)"},
        ) as client:
            response = await client.get(source.url)
            response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if "text/html" not in content_type and "text/plain" not in content_type and "application/pdf" not in content_type:
            raise ValueError(f"unsupported content type: {content_type}")
        if "application/pdf" in content_type:
            raise ValueError("PDF extraction requires a PDF parser dependency")
        text = extract_text(response.text)[:MAX_TEXT_CHARS]
    elif source.storage_path and (source.metadata_ or {}).get("content_type") == "application/pdf":
        from io import BytesIO
        from pypdf import PdfReader
        from app.providers.storage import make_storage
        data = await make_storage().get(source.storage_path)
        text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(data)).pages)[:MAX_TEXT_CHARS]
    else:
        text = str((source.metadata_ or {}).get("content", ""))[:MAX_TEXT_CHARS]
    if len(text) < 200:
        raise ValueError("page contained too little readable text to ingest")
    source.ingest_status = IngestStatus.EXTRACTED

    # ── Chunk ─────────────────────────────────────────────────────
    chunks = chunk_text(text)
    if not chunks:
        raise ValueError("chunking produced no usable segments")
    source.content_hash = hashlib_sha256(text)

    # Replace any previous chunks (re-ingest safety).
    existing = await session.execute(
        select(SourceChunk).where(SourceChunk.source_id == source.id)
    )
    for old in existing.scalars().all():
        await session.delete(old)

    for position, content in enumerate(chunks):
        session.add(
            SourceChunk(
                source_id=source.id,
                position=position,
                content=content,
                token_count=len(content) // 4,  # rough estimate; fine for budgeting
            )
        )
    source.ingest_status = IngestStatus.CHUNKED
    await session.flush()

    # ── Embed + index ─────────────────────────────────────────────
    from app.providers.embedding import GeminiEmbeddingProvider

    embedder = GeminiEmbeddingProvider()
    vectors = await embedder.embed(chunks)
    chunk_rows = await session.execute(
        select(SourceChunk).where(SourceChunk.source_id == source.id).order_by(SourceChunk.position)
    )
    for row, vector in zip(chunk_rows.scalars().all(), vectors, strict=False):
        row.embedding = vector  # type: ignore[assignment]

    source.ingest_status = IngestStatus.EMBEDDED
    return {
        "chunks": len(chunks),
        "characters": len(text),
        "embedded_at": datetime.now(UTC).isoformat(),
    }


def hashlib_sha256(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


async def handle_pathway_generation(session: AsyncSession, payload: dict) -> dict:
    """Generate pathway structure via Gemini, validate, persist. Lazy: no lessons."""
    from sqlalchemy import select

    from app.db.models import AIGeneration, Pathway
    from app.db.models.learning import PathwayStatus
    from app.modules.brain.service import get_brain_graph
    from app.modules.pathways.generator import (
        PROMPT_KEY,
        PROMPT_VERSION,
        SYSTEM_PROMPT,
        persist_pathway,
        user_prompt,
        validate_generated,
    )
    from app.modules.pathways.schemas import GeneratedPathway

    result = await session.execute(select(Pathway).where(Pathway.id == payload["pathway_id"]))
    pathway = result.scalar_one_or_none()
    if pathway is None:
        raise ValueError(f"pathway {payload['pathway_id']} not found")

    brain = await get_brain_graph(session, type("U", (), {"id": pathway.user_id})())
    known = [n.name for n in brain.nodes if n.mastery_score >= 40]

    from app.providers.factory import get_llm_provider

    provider = get_llm_provider()
    response = await provider.generate_structured(
        prompt=user_prompt(pathway.topic or pathway.title, payload.get("target_depth", "beginner"), known),
        schema=GeneratedPathway,
        system=SYSTEM_PROMPT,
    )

    # Cost tracking (spec §40)
    session.add(AIGeneration(
        user_id=pathway.user_id,
        feature="pathway_generation",
        prompt_key=PROMPT_KEY,
        prompt_version=PROMPT_VERSION,
        provider=response.provider,
        model=response.model,
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        latency_ms=response.latency_ms,
        success=1 if response.structured else 0,
    ))

    if response.structured is None:
        raise ValueError("model returned unparseable JSON for pathway generation")

    generated, skipped = validate_generated(GeneratedPathway.model_validate(response.structured))
    await persist_pathway(session, pathway, generated, skipped)
    pathway.status = PathwayStatus.READY
    return {
        "concepts": len(generated.concepts),
        "sections": len(generated.sections),
        "skipped_edges": skipped,
        "input_tokens": response.input_tokens,
        "output_tokens": response.output_tokens,
    }


async def handle_lesson_generation(session: AsyncSession, payload: dict) -> dict:
    """Generate a full book-chapter lesson. Runs in the worker: minutes are fine."""
    from datetime import UTC, datetime

    from sqlalchemy import select

    from app.core.auth import CurrentUser
    from app.db.models import Concept, Lesson, MasteryState, UserConcept
    from app.modules.lessons.generator import generate_lesson

    concept = (await session.execute(
        select(Concept).where(Concept.id == payload["concept_id"])
    )).scalar_one_or_none()
    if concept is None:
        raise ValueError(f"concept {payload['concept_id']} not found")
    user_id = uuid.UUID(payload["user_id"])

    user = CurrentUser(id=user_id)
    out, stats = await generate_lesson(session, user, concept, payload.get("depth", "beginner"))
    await session.commit()

    # Opening/learning a concept nudges mastery state forward.
    state = (await session.execute(
        select(UserConcept).where(
            UserConcept.user_id == user_id, UserConcept.concept_id == concept.id
        )
    )).scalar_one_or_none()
    if state is not None and state.state in (MasteryState.UNSEEN, MasteryState.AVAILABLE):
        state.state = MasteryState.LEARNING
        state.last_seen_at = datetime.now(UTC)
        await session.commit()

    _ = Lesson  # imported for handler registry symmetry
    return {
        "lesson_id": str(out.concept_id),
        "grounding": out.grounding,
        "sections": len(out.content.sections),
        **stats,
    }
