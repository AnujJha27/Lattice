"""Versioned Intellectual Portrait APIs."""
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, CurrentUserDep
from app.core.config import get_settings
from app.core.errors import NotFound
from app.db.models import Job, PortraitEvent, PortraitSnapshot
from app.db.models.job import JobStatus, JobType
from app.db.session import get_session
from app.modules.portrait.schemas import (
    PortraitChange,
    PortraitDebugElement,
    PortraitDebugFactor,
    PortraitDebugReport,
    PortraitElementExplanation,
    PortraitEventIn,
    PortraitModel,
    PortraitRefresh,
    PortraitVisualRefresh,
)
from app.modules.portrait.service import (
    build_portrait,
    get_portrait,
    get_portrait_history,
    get_portrait_snapshot,
)
from app.modules.visual_sources.schemas import VisualAssetOut
from app.modules.visual_sources.service import cached_image_path, visual_sources_for_snapshot

router = APIRouter(tags=["portrait"])


@router.get("/portrait", response_model=PortraitModel)
async def portrait(user: CurrentUser = CurrentUserDep, session: AsyncSession = Depends(get_session)) -> PortraitModel:
    return await get_portrait(session, user, recompute=False)


@router.post(
    "/portrait/refresh",
    response_model=PortraitRefresh,
    status_code=status.HTTP_202_ACCEPTED,
)
async def refresh_portrait(user: CurrentUser = CurrentUserDep,
                           session: AsyncSession = Depends(get_session)) -> PortraitRefresh:
    from app.jobs.queue import enqueue_job

    job = await enqueue_job(
        session,
        JobType.PORTRAIT_REFRESH.value,
        {"user_id": str(user.id)},
        dedupe_key=f"portrait:{user.id}",
    )
    await session.commit()
    return PortraitRefresh(job_id=str(job.id), status=job.status.value)


@router.get("/portrait/refresh/{job_id}", response_model=PortraitRefresh)
async def portrait_refresh_status(job_id: str, user: CurrentUser = CurrentUserDep,
                                  session: AsyncSession = Depends(get_session)) -> PortraitRefresh:
    try:
        parsed_job_id = UUID(job_id)
    except ValueError:
        raise NotFound("portrait refresh", job_id) from None
    job = await session.scalar(select(Job).where(
        Job.id == parsed_job_id, Job.type == JobType.PORTRAIT_REFRESH,
    ))
    if job is None or job.payload.get("user_id") != str(user.id):
        raise NotFound("portrait refresh", job_id)

    model = None
    if job.status in (JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED):
        snapshot_id = (job.result or {}).get("snapshot_id")
        if snapshot_id:
            try:
                model = await get_portrait_snapshot(session, user, UUID(snapshot_id))
            except ValueError:
                model = None
        if model is None:
            model = await get_portrait(session, user, recompute=False)
    return PortraitRefresh(
        job_id=str(job.id), status=job.status.value, portrait=model, error=job.last_error,
    )


@router.get("/portrait/history", response_model=list[PortraitModel])
async def portrait_history(user: CurrentUser = CurrentUserDep, session: AsyncSession = Depends(get_session)) -> list[PortraitModel]:
    return await get_portrait_history(session, user)


@router.get("/portrait/debug", response_model=PortraitDebugReport)
async def portrait_debug(user: CurrentUser = CurrentUserDep,
                         session: AsyncSession = Depends(get_session)) -> PortraitDebugReport:
    if get_settings().is_production:
        raise NotFound("portrait debug report", "disabled")
    debug: list[dict] = []
    model = await build_portrait(session, user, debug=debug)
    latest = await session.scalar(select(PortraitSnapshot).where(
        PortraitSnapshot.user_id == user.id
    ).order_by(PortraitSnapshot.created_at.desc()).limit(1))
    visual_sources = await visual_sources_for_snapshot(session, latest.id) if latest else []
    visual_debug = []
    for source in visual_sources:
        asset = source.asset
        factors = [
            PortraitDebugFactor(name="asset relevance", value=asset.relevance_score, weight=0.38,
                                contribution=round(asset.relevance_score * 0.38, 3)),
            PortraitDebugFactor(name="aesthetic fit", value=asset.aesthetic_score, weight=0.18,
                                contribution=round(asset.aesthetic_score * 0.18, 3)),
            PortraitDebugFactor(name="rights suitability", value=asset.rights_score, weight=0.22,
                                contribution=round(asset.rights_score * 0.22, 3)),
            PortraitDebugFactor(name="quality", value=asset.quality_score, weight=0.22,
                                contribution=round(asset.quality_score * 0.22, 3)),
        ]
        visual_debug.append(PortraitDebugElement(
            kind="visual_source", id=source.asset_id, name=asset.title,
            score=round(sum(factor.contribution for factor in factors), 3),
            threshold="rights-cleared and rights score >= 0.70", selected=True, factors=factors,
        ))
    return PortraitDebugReport(
        snapshot_id=str(latest.id) if latest else None,
        input_hash=model.input_hash,
        algorithm_version=model.algorithm_version,
        config_version=model.config_version,
        elements=debug,
        visual_sources=visual_debug,
    )


@router.post("/portrait/events", status_code=status.HTTP_204_NO_CONTENT)
async def portrait_event(payload: PortraitEventIn, user: CurrentUser = CurrentUserDep,
                         session: AsyncSession = Depends(get_session)) -> Response:
    from app.modules.users.routes import ensure_profile

    await ensure_profile(session, user.id, user.email)
    if payload.snapshot_id is not None:
        snapshot = await session.scalar(select(PortraitSnapshot).where(
            PortraitSnapshot.id == payload.snapshot_id, PortraitSnapshot.user_id == user.id
        ))
        if snapshot is None:
            raise NotFound("portrait snapshot", payload.snapshot_id)
    session.add(PortraitEvent(
        user_id=user.id,
        snapshot_id=payload.snapshot_id,
        element_id=payload.element_id,
        event_type=payload.event_type,
    ))
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/portrait/{snapshot_id}", response_model=PortraitModel)
async def portrait_snapshot(snapshot_id: str, user: CurrentUser = CurrentUserDep,
                           session: AsyncSession = Depends(get_session)) -> PortraitModel:
    try:
        parsed_id = UUID(snapshot_id)
    except ValueError:
        raise NotFound("portrait snapshot", snapshot_id) from None
    model = await get_portrait_snapshot(session, user, parsed_id)
    if model is None:
        raise NotFound("portrait snapshot", snapshot_id)
    return model


@router.get("/portrait/{snapshot_id}/element/{element_id}", response_model=PortraitElementExplanation)
async def portrait_element(snapshot_id: str, element_id: str, user: CurrentUser = CurrentUserDep,
                           session: AsyncSession = Depends(get_session)) -> PortraitElementExplanation:
    try:
        parsed_id = UUID(snapshot_id)
    except ValueError:
        raise NotFound("portrait snapshot", snapshot_id) from None
    model = await get_portrait_snapshot(session, user, parsed_id)
    if model is None:
        raise NotFound("portrait snapshot", snapshot_id)
    for kind, elements in (
        ("anchor", model.anchors),
        ("bridge", model.bridges),
        ("frontier", model.frontiers),
        ("emerging_thread", model.emerging_threads),
        ("dormant_thread", model.dormant_threads),
    ):
        element = next((item for item in elements if item.id == element_id), None)
        if element is not None:
            return PortraitElementExplanation(snapshot_id=model.snapshot_id, kind=kind, element=element)
    raise NotFound("portrait element", element_id)


@router.get("/portrait/{snapshot_id}/changes", response_model=list[PortraitChange])
async def portrait_changes(snapshot_id: str, user: CurrentUser = CurrentUserDep,
                           session: AsyncSession = Depends(get_session)) -> list[PortraitChange]:
    try:
        parsed_id = UUID(snapshot_id)
    except ValueError:
        raise NotFound("portrait snapshot", snapshot_id) from None
    model = await get_portrait_snapshot(session, user, parsed_id)
    if model is None:
        raise NotFound("portrait snapshot", snapshot_id)
    return model.changes_since_previous


@router.post(
    "/portrait/{snapshot_id}/visuals/refresh",
    response_model=PortraitVisualRefresh,
    status_code=status.HTTP_202_ACCEPTED,
)
async def refresh_visuals(snapshot_id: str, user: CurrentUser = CurrentUserDep,
                          session: AsyncSession = Depends(get_session)) -> PortraitVisualRefresh:
    try:
        parsed_id = UUID(snapshot_id)
    except ValueError:
        raise NotFound("portrait snapshot", snapshot_id) from None
    snapshot = await session.scalar(select(PortraitSnapshot).where(
        PortraitSnapshot.id == parsed_id, PortraitSnapshot.user_id == user.id
    ))
    if snapshot is None:
        raise NotFound("portrait snapshot", snapshot_id)
    from app.jobs.queue import enqueue_job

    job = await enqueue_job(
        session,
        JobType.PORTRAIT_VISUAL_REFRESH.value,
        {"snapshot_id": str(parsed_id), "user_id": str(user.id)},
        dedupe_key=f"portrait-visuals:{user.id}:{parsed_id}",
    )
    await session.commit()
    return PortraitVisualRefresh(job_id=str(job.id), snapshot_id=str(parsed_id), status=job.status.value)


@router.get("/portrait/{snapshot_id}/visuals/refresh/{job_id}", response_model=PortraitVisualRefresh)
async def visual_refresh_status(snapshot_id: str, job_id: str, user: CurrentUser = CurrentUserDep,
                                session: AsyncSession = Depends(get_session)) -> PortraitVisualRefresh:
    try:
        parsed_snapshot_id = UUID(snapshot_id)
        parsed_job_id = UUID(job_id)
    except ValueError:
        raise NotFound("portrait visual refresh", job_id) from None
    job = await session.scalar(select(Job).where(
        Job.id == parsed_job_id, Job.type == JobType.PORTRAIT_VISUAL_REFRESH,
    ))
    if job is None or job.payload.get("snapshot_id") != str(parsed_snapshot_id) or job.payload.get("user_id") != str(user.id):
        raise NotFound("portrait visual refresh", job_id)
    model = None
    error = None
    if job.status in (JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED):
        model = await get_portrait_snapshot(session, user, parsed_snapshot_id)
        error = job.last_error
    return PortraitVisualRefresh(
        job_id=str(job.id), snapshot_id=str(parsed_snapshot_id), status=job.status.value,
        portrait=model, error=error,
    )


@router.get("/portrait/{snapshot_id}/visual/{visual_id}", response_model=VisualAssetOut)
async def portrait_visual(snapshot_id: str, visual_id: str, user: CurrentUser = CurrentUserDep,
                          session: AsyncSession = Depends(get_session)) -> VisualAssetOut:
    try:
        parsed_snapshot_id = UUID(snapshot_id)
        parsed_visual_id = UUID(visual_id)
    except ValueError:
        raise NotFound("portrait visual", visual_id) from None
    from app.db.models import PortraitVisual, VisualAsset
    link = await session.scalar(select(PortraitVisual).where(
        PortraitVisual.snapshot_id == parsed_snapshot_id, PortraitVisual.visual_asset_id == parsed_visual_id
    ))
    if link is None:
        raise NotFound("portrait visual", visual_id)
    snapshot = await session.scalar(select(PortraitSnapshot).where(
        PortraitSnapshot.id == parsed_snapshot_id, PortraitSnapshot.user_id == user.id
    ))
    if snapshot is None:
        raise NotFound("portrait visual", visual_id)
    asset = await session.scalar(select(VisualAsset).where(VisualAsset.id == parsed_visual_id))
    if asset is None:
        raise NotFound("portrait visual", visual_id)
    from app.modules.visual_sources.service import _asset_out
    return _asset_out(asset, cached_image_path(parsed_snapshot_id, asset.id) if asset.cached_image_key else None)


@router.get("/portrait/{snapshot_id}/visual/{visual_id}/image", include_in_schema=False)
async def portrait_visual_image(snapshot_id: str, visual_id: str, user: CurrentUser = CurrentUserDep,
                                session: AsyncSession = Depends(get_session)) -> Response:
    try:
        parsed_snapshot_id = UUID(snapshot_id)
        parsed_visual_id = UUID(visual_id)
    except ValueError:
        raise NotFound("portrait visual", visual_id) from None
    from app.db.models import PortraitVisual, VisualAsset
    snapshot = await session.scalar(select(PortraitSnapshot).where(
        PortraitSnapshot.id == parsed_snapshot_id, PortraitSnapshot.user_id == user.id
    ))
    if snapshot is None:
        raise NotFound("cached portrait visual", visual_id)
    link = await session.scalar(select(PortraitVisual).where(
        PortraitVisual.snapshot_id == parsed_snapshot_id, PortraitVisual.visual_asset_id == parsed_visual_id
    ))
    asset = await session.scalar(select(VisualAsset).where(VisualAsset.id == parsed_visual_id)) if link else None
    content_type = (asset.metadata_ or {}).get("cached_content_type") if asset else None
    if asset is None or asset.cached_image_key is None or not isinstance(content_type, str) or not content_type.startswith("image/"):
        raise NotFound("cached portrait visual", visual_id)
    from app.providers.storage import make_storage
    try:
        data = await make_storage().get(asset.cached_image_key)
    except (FileNotFoundError, OSError, RuntimeError):
        raise NotFound("cached portrait visual", visual_id) from None
    return Response(content=data, media_type=content_type, headers={"Cache-Control": "private, max-age=86400"})
