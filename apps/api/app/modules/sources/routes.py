"""Source persistence + linking routes."""
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, CurrentUserDep
from app.core.errors import NotFound
from app.db.models import Concept, ConceptSource, Job, Source, SourceChunk
from app.db.models.job import JobStatus, JobType
from app.db.models.source import IngestStatus, SourceOrigin, SourceType
from app.db.session import get_session
from app.modules.sources.dedup import canonicalize_url, dedupe_key
from app.modules.sources.discovery import discover
from app.modules.sources.schemas import (
    DiscoverRequest,
    DiscoverResponse,
    SourceAccept,
    SourceNote,
    SourceOut,
)

router = APIRouter(tags=["sources"])


@router.post("/sources/notes", response_model=SourceOut, status_code=status.HTTP_201_CREATED)
async def create_note(payload: SourceNote, user: CurrentUser = CurrentUserDep,
                      session: AsyncSession = Depends(get_session)):
    """Save a note/transcript as a first-class library source and index it."""
    from app.jobs.queue import enqueue_job
    from app.modules.users.routes import ensure_profile

    await ensure_profile(session, user.id, user.email)
    source = Source(
        title=payload.title,
        storage_path=f"notes/{uuid.uuid4()}.txt",
        source_type=SourceType(payload.source_type),
        origin=SourceOrigin.USER_UPLOADED,
        owner_id=user.id,
        ingest_status=IngestStatus.PENDING,
        metadata_={"content": payload.content, "kind": "note"},
    )
    session.add(source)
    await session.flush()
    await enqueue_job(session, "SOURCE_INGEST", {"source_id": str(source.id)}, dedupe_key=f"ingest:{source.id}")
    await session.commit()
    return _to_out(source, 0)


@router.post("/sources/upload", response_model=SourceOut, status_code=status.HTTP_201_CREATED)
async def upload_source(file: UploadFile = File(...), user: CurrentUser = CurrentUserDep,
                        session: AsyncSession = Depends(get_session)):
    """Store a PDF locally and queue text extraction/indexing."""
    if file.content_type != "application/pdf" and not (file.filename or "").lower().endswith(".pdf"):
        from fastapi import HTTPException
        raise HTTPException(status_code=415, detail="Only PDF files are supported")
    data = await file.read()
    if len(data) > 25 * 1024 * 1024:
        from fastapi import HTTPException
        raise HTTPException(status_code=413, detail="PDF must be 25 MB or smaller")
    from app.jobs.queue import enqueue_job
    from app.modules.users.routes import ensure_profile
    from app.providers.storage import make_storage

    await ensure_profile(session, user.id, user.email)
    key = f"uploads/{uuid.uuid4()}.pdf"
    await make_storage().put(key, data, "application/pdf")
    source = Source(title=(file.filename or "Uploaded PDF")[:500], storage_path=key,
                    source_type=SourceType.ACADEMIC_PAPER, origin=SourceOrigin.USER_UPLOADED,
                    owner_id=user.id, ingest_status=IngestStatus.PENDING,
                    metadata_={"content_type": "application/pdf"})
    session.add(source)
    await session.flush()
    await enqueue_job(session, "SOURCE_INGEST", {"source_id": str(source.id)}, dedupe_key=f"ingest:{source.id}")
    await session.commit()
    return _to_out(source, 0)


@router.post("/sources/discover", response_model=DiscoverResponse)
async def discover_sources(payload: DiscoverRequest, _user: CurrentUser = CurrentUserDep):
    """Search trusted providers and return ranked, deduplicated candidates."""
    candidates, raw = await discover(payload.query, payload.domain, payload.limit)
    return DiscoverResponse(
        candidates=candidates,
        policy=payload.domain or "general",
        deduped_from=raw,
    )


@router.post("/sources", response_model=SourceOut, status_code=status.HTTP_201_CREATED)
async def accept_source(
    payload: SourceAccept,
    user: CurrentUser = CurrentUserDep,
    session: AsyncSession = Depends(get_session),
):
    """Persist a discovered source (dedup by DOI > arXiv > canonical URL)
    and queue background ingestion."""
    from app.modules.users.routes import ensure_profile

    await ensure_profile(session, user.id, user.email)
    key = dedupe_key(payload.doi, payload.arxiv_id, payload.url)
    canonical = canonicalize_url(payload.url)
    del key  # existence checks below use the structured fields directly

    if payload.doi:
        result = await session.execute(select(Source).where(Source.doi == payload.doi.strip().lower()))
        source = result.scalar_one_or_none()
    elif payload.arxiv_id:
        result = await session.execute(select(Source).where(Source.arxiv_id == payload.arxiv_id.strip().lower()))
        source = result.scalar_one_or_none()
    else:
        result = await session.execute(select(Source).where(Source.canonical_url == canonical))
        source = result.scalar_one_or_none()

    if source is None:
        source = Source(
            title=payload.title[:500],
            url=payload.url,
            canonical_url=canonical,
            source_type=SourceType(payload.source_type),
            origin=SourceOrigin.DISCOVERED,
            publisher=payload.publisher,
            authors=payload.authors or [],
            publication_date=payload.published,
            authority_score=payload.authority,
            doi=payload.doi.strip().lower() if payload.doi else None,
            arxiv_id=payload.arxiv_id.strip().lower() if payload.arxiv_id else None,
            owner_id=user.id,
            retrieved_at=datetime.now(UTC),
            ingest_status=IngestStatus.PENDING,
            metadata_=(
                {"content": payload.content, "content_source": "search_provider"}
                if payload.content else {}
            ),
        )
        session.add(source)
        await session.flush()
    elif payload.content and source.ingest_status != IngestStatus.EMBEDDED:
        source.metadata_ = {
            **(source.metadata_ or {}),
            "content": payload.content,
            "content_source": "search_provider",
        }

    if payload.concept_id:
        concept_uuid = uuid.UUID(payload.concept_id)
        exists = await session.execute(select(Concept.id).where(Concept.id == concept_uuid))
        if exists.scalar_one_or_none() is None:
            raise NotFound("concept", payload.concept_id)
        link_exists = await session.execute(
            select(ConceptSource).where(
                ConceptSource.concept_id == concept_uuid,
                ConceptSource.source_id == source.id,
            )
        )
        if link_exists.scalar_one_or_none() is None:
            session.add(ConceptSource(concept_id=concept_uuid, source_id=source.id, relevance=0.8))

    from app.jobs.queue import enqueue_job

    await enqueue_job(session, "SOURCE_INGEST", {"source_id": str(source.id)},
                      dedupe_key=f"ingest:{source.id}")
    await session.commit()

    chunk_count = await session.scalar(
        select(func.count()).select_from(SourceChunk).where(SourceChunk.source_id == source.id)
    )
    return _to_out(source, int(chunk_count or 0))


@router.post("/sources/{source_id}/retry", response_model=SourceOut)
async def retry_source(
    source_id: uuid.UUID,
    user: CurrentUser = CurrentUserDep,
    session: AsyncSession = Depends(get_session),
):
    """Requeue a source after its URL or provider quota has been fixed."""
    from app.jobs.queue import enqueue_job

    result = await session.execute(
        select(Source).where(
            Source.id == source_id,
            or_(Source.owner_id == user.id, Source.owner_id.is_(None)),
        )
    )
    source = result.scalar_one_or_none()
    if source is None:
        raise NotFound("source", str(source_id))

    source.ingest_status = IngestStatus.PENDING
    await enqueue_job(
        session, "SOURCE_INGEST", {"source_id": str(source.id)},
        dedupe_key=f"ingest:{source.id}",
    )
    await session.commit()
    return _to_out(source, 0)


@router.get("/sources", response_model=list[SourceOut])
async def list_sources(user: CurrentUser = CurrentUserDep, session: AsyncSession = Depends(get_session)):
    rows = await session.execute(select(Source).where(or_(Source.owner_id == user.id, Source.owner_id.is_(None))).order_by(Source.created_at.desc()).limit(200))
    sources = rows.scalars().all()
    ingest_errors = {}
    if sources:
        jobs = await session.execute(
            select(Job)
            .where(
                Job.type == JobType.SOURCE_INGEST,
                Job.payload["source_id"].as_string().in_([str(source.id) for source in sources]),
            )
            .order_by(Job.updated_at.desc())
        )
        for job in jobs.scalars().all():
            source_id = str(job.payload.get("source_id"))
            if source_id not in ingest_errors:
                ingest_errors[source_id] = None if job.status == JobStatus.SUCCEEDED else job.last_error
        chunk_rows = await session.execute(
            select(SourceChunk.source_id, func.count())
            .where(SourceChunk.source_id.in_([source.id for source in sources]))
            .group_by(SourceChunk.source_id)
        )
        chunk_counts = {str(source_id): int(count) for source_id, count in chunk_rows.all()}
    else:
        chunk_counts = {}
    out = []
    for s in sources:
        out.append(_to_out(s, chunk_counts.get(str(s.id), 0), ingest_errors.get(str(s.id))))
    return out


def _to_out(s: Source, chunk_count: int, ingest_error: str | None = None) -> SourceOut:
    return SourceOut(
        id=str(s.id),
        title=s.title,
        url=s.url,
        source_type=s.source_type.value,
        origin=s.origin.value,
        publisher=s.publisher,
        authors=s.authors or [],
        published=s.publication_date,
        ingest_status=s.ingest_status.value,
        ingest_error=_display_ingest_error(ingest_error),
        chunk_count=chunk_count,
        created_at=s.created_at.isoformat() if s.created_at else None,
    )


def _display_ingest_error(error: str | None) -> str | None:
    if error and "403 Forbidden" in error:
        return (
            "This source blocks automated access. Open it directly in your browser, "
            "or use an open-access copy."
        )
    return error
