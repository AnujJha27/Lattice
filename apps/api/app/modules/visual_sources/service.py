"""Search, rank, persist, and associate rights-cleared visual assets."""
from datetime import UTC, datetime
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser
from app.db.models import PortraitSnapshot, PortraitVisual, VisualAsset
from app.modules.portrait.schemas import PortraitModel
from app.modules.visual_sources.cache import cache_image
from app.modules.visual_sources.providers import MetProvider, WikimediaProvider
from app.modules.visual_sources.ranking import VisualAssetCandidate, rank_candidates
from app.modules.visual_sources.schemas import PortraitVisualSource, VisualAssetOut
from app.providers.storage import ObjectStorageProvider, make_storage


def cached_image_path(snapshot_id: UUID, asset_id: UUID) -> str:
    return f"/api/portrait/{snapshot_id}/visual/{asset_id}/image"


def _asset_out(asset: VisualAsset, cached_url: str | None = None) -> VisualAssetOut:
    return VisualAssetOut(
        id=str(asset.id), title=asset.title, source_url=asset.source_url, canonical_url=asset.canonical_url,
        creator=asset.creator, institution=asset.institution, date=asset.source_date, license=asset.license,
        rights_class=asset.rights_class.value, attribution_text=asset.attribution_text, image_url=asset.image_url,
        thumbnail_url=asset.thumbnail_url, width=asset.width, height=asset.height, provider=asset.provider,
        relevance_score=asset.relevance_score, aesthetic_score=asset.aesthetic_score,
        rights_score=asset.rights_score, quality_score=asset.quality_score,
        cached_image_url=cached_url,
    )


async def visual_sources_for_snapshot(session: AsyncSession, snapshot_id: UUID) -> list[PortraitVisualSource]:
    rows = await session.execute(
        select(VisualAsset, PortraitVisual)
        .join(PortraitVisual, PortraitVisual.visual_asset_id == VisualAsset.id)
        .where(PortraitVisual.snapshot_id == snapshot_id)
        .order_by(PortraitVisual.relevance_score.desc())
    )
    return [PortraitVisualSource(
        asset_id=str(link.visual_asset_id), represents=link.represents, concept_ids=link.concept_ids or [],
        portrait_role=link.portrait_role,
        asset=_asset_out(
            asset,
            cached_image_path(snapshot_id, asset.id) if asset.cached_image_key else None,
        ),
    ) for asset, link in rows.all()]


async def with_visual_sources(session: AsyncSession, model: PortraitModel) -> PortraitModel:
    if not model.snapshot_id:
        return model
    sources = await visual_sources_for_snapshot(session, UUID(model.snapshot_id))
    return model.model_copy(update={"visual_sources": sources})


async def refresh_visual_sources(session: AsyncSession, user: CurrentUser, model: PortraitModel) -> PortraitModel:
    if not model.snapshot_id:
        return model
    snapshot = await session.scalar(select(PortraitSnapshot).where(
        PortraitSnapshot.id == UUID(model.snapshot_id), PortraitSnapshot.user_id == user.id
    ))
    if snapshot is None:
        return model
    providers = (WikimediaProvider(), MetProvider())
    storage: ObjectStorageProvider | None
    try:
        storage = make_storage()
    except RuntimeError:
        storage = None
    elements = [
        (item.name, item.id, "ANCHOR", item.score) for item in model.anchors[:3]
    ] + [
        (item.name, item.id, "BRIDGE", item.score) for item in model.bridges[:3]
    ] + [
        (item.name, item.id, "FRONTIER", item.score) for item in model.frontiers[:3]
    ] + [
        (item.name, item.concept_ids[0] if item.concept_ids else item.id, "EMERGING", item.score)
        for item in model.emerging_threads[:2]
    ]
    for represents, concept_id, role, _score in elements:
        all_candidates = []
        for provider in providers:
            if len(rank_candidates(all_candidates, limit=2)) >= 2:
                break
            try:
                all_candidates.extend(await provider.search(f"{represents} scientific diagram", limit=5))
            except Exception:
                continue
        candidates = rank_candidates(all_candidates, limit=2)
        for candidate in candidates:
            asset = await _get_or_create_asset(session, candidate)
            if storage is not None and asset.cached_image_key is None:
                try:
                    cached = await cache_image(candidate.image_url, storage)
                except (OSError, RuntimeError, httpx.HTTPError):
                    cached = None
                if cached is not None:
                    asset.cached_image_key = cached.key
                    asset.content_hash = cached.content_hash
                    asset.metadata_ = {
                        **(asset.metadata_ or {}),
                        "cached_content_type": cached.content_type,
                    }
            exists = await session.scalar(select(PortraitVisual).where(
                PortraitVisual.snapshot_id == snapshot.id, PortraitVisual.visual_asset_id == asset.id
            ))
            if exists is None:
                session.add(PortraitVisual(
                    snapshot_id=snapshot.id, visual_asset_id=asset.id, represents=represents,
                    concept_ids=[concept_id], portrait_role=role, relevance_score=candidate.relevance_score,
                ))
    await session.commit()
    return await with_visual_sources(session, model)


async def _get_or_create_asset(session: AsyncSession, candidate: VisualAssetCandidate) -> VisualAsset:
    asset = await session.scalar(select(VisualAsset).where(VisualAsset.canonical_url == candidate.canonical_url))
    if asset is not None:
        return asset
    asset = VisualAsset(
        title=candidate.title, source_url=candidate.canonical_url, canonical_url=candidate.canonical_url,
        creator=candidate.creator, institution=candidate.institution, source_date=candidate.date,
        license=candidate.license, rights_class=candidate.rights_class,
        attribution_text=candidate.attribution_text, image_url=candidate.image_url,
        thumbnail_url=candidate.thumbnail_url, width=candidate.width, height=candidate.height,
        provider=candidate.provider, relevance_score=candidate.relevance_score,
        aesthetic_score=candidate.aesthetic_score, rights_score=candidate.rights_score,
        quality_score=candidate.quality_score, retrieved_at=datetime.now(UTC),
    )
    session.add(asset)
    await session.flush()
    return asset
