from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest


def test_portrait_analytics_payload_contains_identifiers_only():
    from app.db.models.portrait import PortraitEventType
    from app.modules.portrait.schemas import PortraitEventIn

    event = PortraitEventIn(
        event_type=PortraitEventType.ELEMENT_OPENED,
        snapshot_id=uuid4(),
        element_id="concept-123",
    )

    assert event.event_type == PortraitEventType.ELEMENT_OPENED
    assert event.element_id == "concept-123"
    assert "subject" not in event.model_dump()


def test_portrait_event_enum_persists_documented_values():
    from app.db.models.portrait import PortraitEvent

    assert PortraitEvent.__table__.c.event_type.type.enums == [
        "portrait_viewed",
        "portrait_refreshed",
        "portrait_element_opened",
        "portrait_element_hovered",
        "portrait_visual_source_opened",
        "portrait_brain_navigation",
        "portrait_discovery_navigation",
        "portrait_history_opened",
        "portrait_snapshot_selected",
        "portrait_photo_enabled",
        "portrait_photo_disabled",
    ]


@pytest.mark.asyncio
async def test_portrait_event_mirrors_new_user_before_insert():
    from app.core.auth import CurrentUser
    from app.db.models import PortraitEvent, Profile
    from app.db.models.portrait import PortraitEventType
    from app.modules.portrait.routes import portrait_event
    from app.modules.portrait.schemas import PortraitEventIn

    class Result:
        def scalar_one_or_none(self):
            return None

    class Session:
        def __init__(self):
            self.added = []

        async def execute(self, _statement):
            return Result()

        def add(self, value):
            self.added.append(value)

        async def flush(self):
            return None

        async def commit(self):
            return None

    user_id = uuid4()
    session = Session()

    response = await portrait_event(
        PortraitEventIn(event_type=PortraitEventType.VIEWED),
        CurrentUser(id=user_id, email="new-user@lattice.local"),
        session,
    )

    assert response.status_code == 204
    assert any(isinstance(value, Profile) and value.id == user_id for value in session.added)
    assert any(isinstance(value, PortraitEvent) and value.user_id == user_id for value in session.added)


@pytest.mark.asyncio
async def test_portrait_feedback_mirrors_new_user_before_insert(monkeypatch):
    from app.core.auth import CurrentUser
    from app.db.models import PortraitFeedback, Profile
    from app.modules.discovery.routes import PortraitFeedbackIn, portrait_feedback

    class Session:
        def __init__(self):
            self.added = []

        def add(self, value):
            self.added.append(value)

        async def commit(self):
            return None

    user_id = uuid4()
    session = Session()
    ensured = []

    async def fake_ensure_profile(_session, requested_id, email):
        ensured.append((requested_id, email))
        return Profile(id=requested_id)

    monkeypatch.setattr("app.modules.users.routes.ensure_profile", fake_ensure_profile)
    result = await portrait_feedback(
        PortraitFeedbackIn(kind="BRIDGE", subject="Linear Algebra", accepted=True),
        CurrentUser(id=user_id, email="new-user@lattice.local"),
        session,
    )

    assert result == {"ok": True}
    assert ensured == [(user_id, "new-user@lattice.local")]
    assert any(isinstance(value, PortraitFeedback) and value.user_id == user_id for value in session.added)


@pytest.mark.asyncio
async def test_portrait_debug_endpoint_is_development_only(monkeypatch):
    from app.core.auth import CurrentUser
    from app.core.errors import NotFound
    from app.modules.portrait import routes
    from app.modules.portrait.schemas import PortraitModel, PortraitSummary

    model = PortraitModel(
        snapshot_id="", generated_at=datetime.now(UTC), version=1,
        algorithm_version="portrait-1", config_version="portrait-defaults-1",
        input_hash="hash", summary=PortraitSummary(
            concept_count=0, mastered_concept_count=0, domain_count=0, active_frontier_count=0,
        ), narrative="still forming",
    )

    async def fake_build(_session, _user, debug=None):
        debug.append({
            "kind": "bridge", "id": "concept-1", "name": "Linear Algebra", "score": 0.8,
            "threshold": "at least one cross-domain connection", "selected": True,
            "factors": [],
        })
        return model

    class Session:
        async def scalar(self, _statement):
            return None

    monkeypatch.setattr(routes, "build_portrait", fake_build)
    monkeypatch.setattr(routes, "get_settings", lambda: SimpleNamespace(is_production=False))
    report = await routes.portrait_debug(CurrentUser(id=uuid4()), Session())

    assert report.input_hash == "hash"
    assert report.elements[0].name == "Linear Algebra"

    monkeypatch.setattr(routes, "get_settings", lambda: SimpleNamespace(is_production=True))
    with pytest.raises(NotFound):
        await routes.portrait_debug(CurrentUser(id=uuid4()), Session())


@pytest.mark.asyncio
async def test_portrait_refresh_queues_and_reports_job(monkeypatch):
    from app.core.auth import CurrentUser
    from app.db.models.job import JobStatus
    from app.modules.portrait import routes

    class Result:
        def scalars(self):
            return SimpleNamespace(all=lambda: [])

    class Session:
        async def execute(self, _statement):
            return Result()

        async def commit(self):
            return None

    user_id, job_id = uuid4(), uuid4()
    queued = {}

    async def fake_enqueue(_session, job_type, payload, **kwargs):
        queued.update(type=job_type, payload=payload, kwargs=kwargs)
        return SimpleNamespace(id=job_id, status=JobStatus.PENDING)

    monkeypatch.setattr("app.jobs.queue.enqueue_job", fake_enqueue)
    result = await routes.refresh_portrait(CurrentUser(id=user_id), Session())

    assert result.job_id == str(job_id)
    assert result.status == "PENDING"
    assert queued == {
        "type": "PORTRAIT_REFRESH",
        "payload": {"user_id": str(user_id)},
        "kwargs": {"dedupe_key": f"portrait:{user_id}"},
    }


@pytest.mark.asyncio
async def test_portrait_refresh_status_returns_completed_snapshot(monkeypatch):
    from app.core.auth import CurrentUser
    from app.db.models.job import JobStatus, JobType
    from app.modules.portrait import routes
    from app.modules.portrait.schemas import PortraitModel, PortraitSummary

    user_id, job_id, snapshot_id = uuid4(), uuid4(), uuid4()
    job = SimpleNamespace(
        id=job_id,
        type=JobType.PORTRAIT_REFRESH,
        payload={"user_id": str(user_id)},
        result={"snapshot_id": str(snapshot_id)},
        status=JobStatus.SUCCEEDED,
        last_error=None,
    )

    class Session:
        async def scalar(self, _statement):
            return job

    model = PortraitModel(
        snapshot_id=str(snapshot_id), generated_at=datetime.now(UTC), version=1,
        algorithm_version="portrait-1", config_version="portrait-defaults-1",
        input_hash="hash", summary=PortraitSummary(
            concept_count=0, mastered_concept_count=0, domain_count=0, active_frontier_count=0,
        ), narrative="still forming",
    )
    async def fake_snapshot(_session, user, requested_id):
        assert user.id == user_id
        assert requested_id == snapshot_id
        return model

    monkeypatch.setattr(routes, "get_portrait_snapshot", fake_snapshot)
    result = await routes.portrait_refresh_status(
        str(job_id), CurrentUser(id=user_id), Session()
    )

    assert result.status == "SUCCEEDED"
    assert result.portrait is model


@pytest.mark.asyncio
async def test_visual_refresh_deduplicates_by_user_and_snapshot(monkeypatch):
    from app.core.auth import CurrentUser
    from app.db.models.job import JobStatus
    from app.modules.portrait import routes

    user_id, snapshot_id, job_id = uuid4(), uuid4(), uuid4()
    queued = {}

    class Session:
        async def scalar(self, _statement):
            return SimpleNamespace(id=snapshot_id)

        async def commit(self):
            return None

    async def fake_enqueue(_session, job_type, payload, **kwargs):
        queued.update(type=job_type, payload=payload, kwargs=kwargs)
        return SimpleNamespace(id=job_id, status=JobStatus.PENDING)

    monkeypatch.setattr("app.jobs.queue.enqueue_job", fake_enqueue)
    result = await routes.refresh_visuals(
        str(snapshot_id), CurrentUser(id=user_id), Session()
    )

    assert result.job_id == str(job_id)
    assert queued["kwargs"] == {"dedupe_key": f"portrait-visuals:{user_id}:{snapshot_id}"}


@pytest.mark.asyncio
async def test_cached_portrait_visual_requires_snapshot_owner():
    from app.core.auth import CurrentUser
    from app.core.errors import NotFound
    from app.modules.portrait.routes import portrait_visual_image

    class Session:
        async def scalar(self, _statement):
            return None

    with pytest.raises(NotFound):
        await portrait_visual_image(
            str(uuid4()), str(uuid4()), CurrentUser(id=uuid4()), Session()
        )


@pytest.mark.asyncio
async def test_cached_portrait_visual_is_not_publicly_cacheable(monkeypatch):
    from app.core.auth import CurrentUser
    from app.modules.portrait.routes import portrait_visual_image

    values = iter([
        SimpleNamespace(),
        SimpleNamespace(),
        SimpleNamespace(
            cached_image_key="portrait/image.png",
            metadata_={"cached_content_type": "image/png"},
        ),
    ])

    class Session:
        async def scalar(self, _statement):
            return next(values)

    class Storage:
        async def get(self, _key):
            return b"png"

    monkeypatch.setattr("app.providers.storage.make_storage", lambda: Storage())
    response = await portrait_visual_image(
        str(uuid4()), str(uuid4()), CurrentUser(id=uuid4()), Session()
    )

    assert response.headers["cache-control"] == "private, max-age=86400"
