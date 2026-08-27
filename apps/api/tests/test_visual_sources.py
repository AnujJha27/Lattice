from datetime import UTC, datetime
from types import SimpleNamespace

from app.modules.visual_sources.ranking import VisualAssetCandidate, rank_candidates
from app.modules.visual_sources.rights import RightsClass, classify_license, is_composable


def test_unknown_or_restricted_rights_are_not_composable():
    assert classify_license("unknown") == RightsClass.UNKNOWN
    assert classify_license("All rights reserved") == RightsClass.RESTRICTED
    assert not is_composable(RightsClass.UNKNOWN)
    assert not is_composable(RightsClass.RESTRICTED)


def test_rank_candidates_prefers_relevant_allowed_assets():
    candidates = [
        VisualAssetCandidate("diagram", "https://a", "https://a/img", RightsClass.PUBLIC_DOMAIN, 0.9, 0.6, 0.8, 0.8),
        VisualAssetCandidate("diagram", "https://b", "https://b/img", RightsClass.UNKNOWN, 1.0, 1.0, 1.0, 1.0),
    ]
    assert rank_candidates(candidates, limit=1)[0].canonical_url == "https://a"


def test_rank_candidates_deduplicates_canonical_and_image_urls():
    candidates = [
        VisualAssetCandidate("same page", "https://a", "https://cdn/img", RightsClass.PUBLIC_DOMAIN, 0.8, 0.6, 0.8, 0.8),
        VisualAssetCandidate("same page again", "https://a", "https://cdn/img-2", RightsClass.PUBLIC_DOMAIN, 0.9, 0.6, 0.8, 0.8),
        VisualAssetCandidate("same image", "https://b", "https://cdn/img-2", RightsClass.PUBLIC_DOMAIN, 0.7, 0.6, 0.8, 0.8),
    ]

    ranked = rank_candidates(candidates)

    assert [candidate.canonical_url for candidate in ranked] == ["https://a"]


class MemoryStorage:
    def __init__(self):
        self.values = {}

    async def put(self, key, data, content_type):
        self.values[key] = (data, content_type)
        return key


class ImageResponse:
    headers = {"content-type": "image/png; charset=binary"}

    def raise_for_status(self):
        return None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def aiter_bytes(self):
        yield b"png-bytes"


class ImageClient:
    def __init__(self, **_kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    def stream(self, *_args, **_kwargs):
        return ImageResponse()


async def test_cache_image_stores_content_by_hash(monkeypatch):
    from app.modules.visual_sources import cache

    monkeypatch.setattr(cache.httpx, "AsyncClient", ImageClient)
    storage = MemoryStorage()

    cached = await cache.cache_image("https://cdn.example/image.png", storage)

    assert cached is not None
    assert cached.key.startswith("visuals/")
    assert cached.content_hash in cached.key
    assert storage.values[cached.key] == (b"png-bytes", "image/png")


def test_cached_image_path_is_scoped_to_snapshot_and_asset():
    from uuid import uuid4

    from app.modules.visual_sources.service import cached_image_path

    snapshot_id, asset_id = uuid4(), uuid4()

    assert cached_image_path(snapshot_id, asset_id) == f"/api/portrait/{snapshot_id}/visual/{asset_id}/image"


def test_portrait_visual_refresh_uses_the_durable_worker():
    from app.db.models.job import JobType
    from app.jobs.runner import HANDLERS

    assert JobType.PORTRAIT_VISUAL_REFRESH.value in HANDLERS
    assert JobType.PORTRAIT_REFRESH.value in HANDLERS


async def test_portrait_visual_refresh_handler_delegates_to_source_service(monkeypatch):
    from uuid import uuid4

    from app.jobs.handlers import handle_portrait_visual_refresh

    user_id, snapshot_id = uuid4(), uuid4()

    async def fake_snapshot(_session, user, requested_id):
        assert user.id == user_id
        assert requested_id == snapshot_id
        return object()

    async def fake_refresh(_session, user, model):
        assert user.id == user_id
        assert model is not None
        return type("Portrait", (), {"visual_sources": [object(), object()]})()

    monkeypatch.setattr("app.modules.portrait.service.get_portrait_snapshot", fake_snapshot)
    monkeypatch.setattr("app.modules.visual_sources.service.refresh_visual_sources", fake_refresh)

    result = await handle_portrait_visual_refresh(
        object(), {"user_id": str(user_id), "snapshot_id": str(snapshot_id)}
    )

    assert result == {"snapshot_id": str(snapshot_id), "visual_count": 2}


async def test_portrait_refresh_handler_recomputes_for_user(monkeypatch):
    from uuid import uuid4

    from app.jobs.handlers import handle_portrait_refresh

    user_id = uuid4()

    async def fake_get_portrait(_session, user, **kwargs):
        assert user.id == user_id
        assert kwargs == {"recompute": True, "fallback_on_error": False}
        return SimpleNamespace(snapshot_id="snapshot-1")

    monkeypatch.setattr("app.modules.portrait.service.get_portrait", fake_get_portrait)

    result = await handle_portrait_refresh(object(), {"user_id": str(user_id)})

    assert result == {"snapshot_id": "snapshot-1"}


async def test_met_provider_maps_only_public_domain_images(monkeypatch):
    from app.modules.visual_sources.providers import MetProvider

    class Response:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def get(self, url, params=None):
            if url.endswith("/search"):
                assert params["isPublicDomain"] == "true"
                return Response({"objectIDs": [101, 102]})
            object_id = url.rsplit("/", 1)[-1]
            if object_id == "101":
                return Response({
                    "objectID": 101,
                    "title": "Study of a geometric construction",
                    "isPublicDomain": True,
                    "primaryImage": "https://images.metmuseum.org/101.jpg",
                    "primaryImageSmall": "https://images.metmuseum.org/101-small.jpg",
                    "artistDisplayName": "Open Access Artist",
                    "objectDate": "1901",
                    "objectURL": "https://www.metmuseum.org/art/collection/search/101",
                })
            return Response({
                "objectID": 102,
                "title": "Unusable record",
                "isPublicDomain": False,
                "primaryImage": "",
            })

        def __init__(self, **_kwargs):
            pass

    monkeypatch.setattr("httpx.AsyncClient", Client)
    results = await MetProvider().search("geometric construction", limit=2)

    assert len(results) == 1
    assert results[0].canonical_url.endswith("/101")
    assert results[0].rights_class == RightsClass.PUBLIC_DOMAIN
    assert results[0].provider == "The Metropolitan Museum of Art"


async def test_visual_refresh_uses_met_when_wikimedia_has_too_few_results(monkeypatch):
    from uuid import uuid4

    from app.modules.portrait.schemas import PortraitModel, PortraitNode, PortraitSummary
    from app.modules.visual_sources import service

    snapshot_id = uuid4()
    model = PortraitModel(
        snapshot_id=str(snapshot_id), generated_at=datetime.now(UTC), version=1,
        algorithm_version="portrait-1", config_version="portrait-defaults-1", input_hash="hash",
        summary=PortraitSummary(concept_count=1, mastered_concept_count=1, domain_count=1, active_frontier_count=0),
        anchors=[PortraitNode(
            id="concept-1", name="Linear Algebra", domain="Mathematics", score=0.9,
            mastery=0.9, activity=0.8, reason="test",
        )], narrative="test",
    )
    candidate = VisualAssetCandidate(
        "Geometry", "https://met.example/1", "https://met.example/1.jpg", RightsClass.PUBLIC_DOMAIN,
        0.9, 0.6, 1.0, 0.65, provider="The Metropolitan Museum of Art",
    )
    calls = []

    class Wikimedia:
        async def search(self, _query, limit=5):
            calls.append("wikimedia")
            return []

    class Met:
        async def search(self, _query, limit=5):
            calls.append("met")
            return [candidate]

    class Session:
        def __init__(self):
            self.values = iter([SimpleNamespace(id=snapshot_id), None])
            self.added = []

        async def scalar(self, _statement):
            return next(self.values)

        def add(self, value):
            self.added.append(value)

        async def commit(self):
            return None

    asset = SimpleNamespace(
        id=uuid4(), cached_image_key=None, content_hash=None, metadata_={},
    )

    async def get_asset(*_args):
        return asset

    async def identity(_session, value):
        return value

    monkeypatch.setattr(service, "WikimediaProvider", Wikimedia)
    monkeypatch.setattr(service, "MetProvider", Met)
    monkeypatch.setattr(service, "make_storage", lambda: (_ for _ in ()).throw(RuntimeError("no storage")))
    monkeypatch.setattr(service, "_get_or_create_asset", get_asset)
    monkeypatch.setattr(service, "with_visual_sources", identity)

    await service.refresh_visual_sources(Session(), SimpleNamespace(id=uuid4()), model)

    assert calls == ["wikimedia", "met"]
