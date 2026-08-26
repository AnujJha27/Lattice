"""Vector retrieval over ingested sources — the grounding primitive for
lessons and the tutor (overrides §26, §35)."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, CurrentUserDep
from app.db.models import Source, SourceChunk
from app.db.session import get_session

router = APIRouter(tags=["retrieval"])


class RetrievalHit(BaseModel):
    source_id: str
    title: str
    url: str | None
    publisher: str | None
    chunk_position: int
    content: str
    distance: float


class RetrievalRequest(BaseModel):
    query: str = Field(min_length=3, max_length=1000)
    concept_id: str | None = None  # restrict to sources linked to a concept
    k: int = Field(default=6, ge=1, le=20)


@router.post("/retrieval/query", response_model=list[RetrievalHit])
async def query_retrieval(
    payload: RetrievalRequest,
    user: CurrentUser = CurrentUserDep,
    session: AsyncSession = Depends(get_session),
) -> list[RetrievalHit]:
    from app.providers.embedding import GeminiEmbeddingProvider

    embedder = GeminiEmbeddingProvider()
    [query_vector] = await embedder.embed([payload.query])

    distance_expr = SourceChunk.embedding.cosine_distance(query_vector)
    stmt = (
        select(SourceChunk, Source, distance_expr)
        .join(Source, Source.id == SourceChunk.source_id)
        .where(Source.ingest_status == "EMBEDDED")
        .order_by(distance_expr)
        .limit(payload.k)
    )
    if payload.concept_id:
        from app.db.models import ConceptSource

        stmt = stmt.where(
            SourceChunk.source_id.in_(
                select(ConceptSource.source_id).where(
                    ConceptSource.concept_id == payload.concept_id
                )
            )
        )

    rows = await session.execute(stmt)
    _ = user.id  # auth gate only; retrieved sources may be shared/global records

    return [
        RetrievalHit(
            source_id=str(chunk.source_id),
            title=source.title,
            url=source.url,
            publisher=source.publisher,
            chunk_position=chunk.position,
            content=chunk.content[:1200],
            distance=float(distance),
        )
        for chunk, source, distance in rows.all()
    ]
