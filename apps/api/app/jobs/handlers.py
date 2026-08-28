"""Job handlers: SOURCE_INGEST (fetch → extract → chunk → embed → index)."""
import logging
import uuid
from datetime import UTC, datetime
from urllib.parse import quote, unquote, urlencode, urlparse

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Source, SourceChunk
from app.db.models.source import IngestStatus
from app.modules.sources.chunking import chunk_text
from app.modules.sources.extraction import extract_text

logger = logging.getLogger(__name__)

MAX_TEXT_CHARS = 400_000
SOURCE_HEADERS = {
    "Accept": "text/html, text/plain, application/pdf, application/xhtml+xml",
    "User-Agent": "LatticeSourceBot/0.1 (+learning research)",
}


async def handle_source_ingest(session: AsyncSession, payload: dict) -> dict:
    source_id = payload["source_id"]
    result = await session.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()
    if source is None:
        raise ValueError(f"source {source_id} not found")
    if source.url:
        fetch_url = _source_fetch_url(source)
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=30,
            headers=SOURCE_HEADERS,
        ) as client:
            response, fetch_url = await _fetch_source_response(client, source)
        source.ingest_status = IngestStatus.FETCHED
        content_type = response.headers.get("content-type", "").lower()
        is_pdf = (
            "application/pdf" in content_type
            or response.content.startswith(b"%PDF-")
            or urlparse(fetch_url).path.lower().endswith(".pdf")
        )
        if not is_pdf and not (
            content_type.startswith("text/")
            or "html" in content_type
            or not content_type
        ):
            raise ValueError(f"unsupported content type: {content_type}")
        if is_pdf:
            text = extract_pdf(response.content)[:MAX_TEXT_CHARS]
        else:
            text = extract_text(response.text)[:MAX_TEXT_CHARS]
    elif source.storage_path and (source.metadata_ or {}).get("content_type") == "application/pdf":
        from app.providers.storage import make_storage
        data = await make_storage().get(source.storage_path)
        source.ingest_status = IngestStatus.FETCHED
        text = extract_pdf(data)[:MAX_TEXT_CHARS]
    else:
        source.ingest_status = IngestStatus.FETCHED
        text = str((source.metadata_ or {}).get("content", ""))[:MAX_TEXT_CHARS]
    if len(text) < 200:
        fallback = await _source_content_fallback(source) if source.url else None
        if fallback is not None:
            response, _ = fallback
            text = extract_text(response.text)[:MAX_TEXT_CHARS]
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


def _source_fetch_url(source: Source) -> str:
    """Use arXiv's stable PDF endpoint when an academic source has an ID."""
    arxiv_id = getattr(source, "arxiv_id", None)
    if arxiv_id and urlparse(source.url).hostname in {"arxiv.org", "www.arxiv.org"}:
        identifier = str(arxiv_id).removeprefix("arXiv:").removeprefix("arxiv:")
        identifier = quote(identifier, safe="/.-")
        return f"https://arxiv.org/pdf/{identifier}"
    return source.url


async def _fetch_source_response(client: httpx.AsyncClient, source: Source):
    fetch_url = _source_fetch_url(source)
    try:
        response = await client.get(fetch_url)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        fallback_url = _source_fallback_url(source.url) if exc.response.status_code == 403 else None
        if fallback_url is not None:
            try:
                fetch_url = fallback_url
                response = await client.get(fetch_url)
                response.raise_for_status()
                return response, fetch_url
            except httpx.HTTPError:
                pass
        if exc.response.status_code == 403:
            fallback_url = await _openalex_fallback_url(client, source)
            if fallback_url is not None:
                try:
                    fetch_url = fallback_url
                    response = await client.get(fetch_url)
                    response.raise_for_status()
                    return response, fetch_url
                except httpx.HTTPError:
                    pass
        inline = await _source_content_fallback(source)
        if inline is not None:
            return inline
        raise
    except httpx.HTTPError:
        inline = await _source_content_fallback(source)
        if inline is not None:
            return inline
        raise
    return response, fetch_url


async def _openalex_fallback_url(client: httpx.AsyncClient, source: Source) -> str | None:
    doi = str(getattr(source, "doi", None) or "").strip()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        doi = doi.removeprefix(prefix)
    if not doi:
        return None
    lookup_url = f"https://api.openalex.org/works/https://doi.org/{quote(doi, safe='/.-_')}"
    try:
        response = await client.get(lookup_url)
        response.raise_for_status()
        from app.providers.openalex import _open_access_url

        return _open_access_url(response.json())
    except (AttributeError, httpx.HTTPError, TypeError, ValueError):
        return None


async def _source_content_fallback(source: Source):
    inline = _provider_content_response(source)
    if inline is not None:
        return inline

    from app.core.config import get_settings

    api_key = get_settings().tavily_api_key
    if not api_key:
        return None
    try:
        from app.providers.tavily import TavilySearchProvider

        content = await TavilySearchProvider(api_key).extract(source.url)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 429:
            raise
        return None
    except (httpx.HTTPError, TypeError, ValueError):
        return None
    if not isinstance(content, str) or len(content) < 200:
        return None
    source.metadata_ = {
        **(source.metadata_ or {}),
        "content": content[:400_000],
        "content_source": "tavily_extract",
    }
    return _provider_content_response(source)


def _provider_content_response(source: Source):
    content = (source.metadata_ or {}).get("content")
    if not isinstance(content, str) or len(content) < 200:
        return None
    request = httpx.Request("GET", source.url)
    return (
        httpx.Response(
            200,
            request=request,
            headers={"content-type": "text/plain"},
            content=content.encode("utf-8"),
        ),
        "provider-content",
    )


def _source_fallback_url(url: str) -> str | None:
    """Use a publisher's official read API after a blocked HTML page."""
    parsed = urlparse(url)
    host = parsed.hostname or ""
    path = parsed.path

    if (host == "wikipedia.org" or host.endswith(".wikipedia.org")) and path.startswith("/wiki/"):
        title = unquote(path.removeprefix("/wiki/")).strip("/")
        if title:
            return f"https://{host}/api/rest_v1/page/html/{quote(title, safe='')}"

    parts = [unquote(part) for part in path.split("/") if part]
    pubmed_id = None
    if host == "pubmed.ncbi.nlm.nih.gov" and len(parts) == 1 and parts[0].isdigit():
        pubmed_id = parts[0]
    elif host == "www.ncbi.nlm.nih.gov" and parts[:1] == ["pubmed"] and len(parts) == 2 and parts[1].isdigit():
        pubmed_id = parts[1]
    if pubmed_id:
        query = urlencode({"db": "pubmed", "id": pubmed_id, "rettype": "abstract", "retmode": "text"})
        return f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?{query}"

    return None


def hashlib_sha256(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def extract_pdf(data: bytes) -> str:
    from io import BytesIO

    from pypdf import PdfReader

    return "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(data)).pages)


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


async def handle_portrait_visual_refresh(session: AsyncSession, payload: dict) -> dict:
    """Fetch and cache portrait visuals without holding open the API request."""
    from app.core.auth import CurrentUser
    from app.modules.portrait.service import get_portrait_snapshot
    from app.modules.visual_sources.service import refresh_visual_sources

    user = CurrentUser(id=uuid.UUID(payload["user_id"]))
    snapshot_id = uuid.UUID(payload["snapshot_id"])
    model = await get_portrait_snapshot(session, user, snapshot_id)
    if model is None:
        raise ValueError(f"portrait snapshot {snapshot_id} not found")
    refreshed = await refresh_visual_sources(session, user, model)
    return {"snapshot_id": str(snapshot_id), "visual_count": len(refreshed.visual_sources)}


async def handle_portrait_refresh(session: AsyncSession, payload: dict) -> dict:
    """Recompute and persist a portrait outside the request lifecycle."""
    from app.core.auth import CurrentUser
    from app.modules.portrait.service import get_portrait

    user = CurrentUser(id=uuid.UUID(payload["user_id"]))
    model = await get_portrait(session, user, recompute=True, fallback_on_error=False)
    return {"snapshot_id": model.snapshot_id}
