from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.db.models import Concept, Source
from app.db.models.source import IngestStatus, SourceOrigin, SourceType
from app.jobs.queue import enqueue_job
from app.modules.lessons.context import _persist_discovered
from app.modules.sources.routes import _to_out, list_sources, retry_source
from app.modules.sources.schemas import SourceCandidate


class _Result:
    def __init__(self, value=None):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _Session:
    def __init__(self, results=None):
        self.results = list(results or [])
        self.added = []

    async def execute(self, _statement):
        return _Result(self.results.pop(0))

    def add(self, value):
        self.added.append(value)

    async def flush(self):
        for value in self.added:
            if isinstance(value, Source) and value.id is None:
                value.id = uuid4()


class _RowsResult:
    def __init__(self, *, scalar_rows=None, rows=None):
        self.scalar_rows = scalar_rows or []
        self.rows = rows or []

    def scalars(self):
        return SimpleNamespace(all=lambda: self.scalar_rows)

    def all(self):
        return self.rows


@pytest.mark.asyncio
async def test_discovered_source_is_queued(monkeypatch):
    queued = []

    async def fake_enqueue(_session, job_type, payload, **kwargs):
        queued.append((job_type, payload, kwargs))

    monkeypatch.setattr("app.jobs.queue.enqueue_job", fake_enqueue)
    concept = Concept(id=uuid4(), canonical_name="Test concept")
    candidate = SourceCandidate(title="Test source", url="https://example.com/source")

    await _persist_discovered(_Session([None, None]), concept, candidate)

    assert queued == [(
        "SOURCE_INGEST",
        {"source_id": queued[0][1]["source_id"]},
        {"dedupe_key": f"ingest:{queued[0][1]['source_id']}"},
    )]


@pytest.mark.asyncio
async def test_enqueue_job_persists_dedupe_key():
    session = _Session([None])

    job = await enqueue_job(session, "SOURCE_INGEST", {"source_id": "source"}, dedupe_key="ingest:source")

    assert job.dedupe_key == "ingest:source"


@pytest.mark.asyncio
async def test_enqueue_job_allows_a_new_run_after_terminal_dedupe_job():
    from app.db.models import Job
    from app.db.models.job import JobStatus, JobType

    previous = Job(
        type=JobType.PORTRAIT_VISUAL_REFRESH,
        status=JobStatus.SUCCEEDED,
        payload={"snapshot_id": "old"},
        dedupe_key="portrait-visuals:user:snapshot",
    )
    session = _Session([previous])

    job = await enqueue_job(
        session,
        JobType.PORTRAIT_VISUAL_REFRESH.value,
        {"snapshot_id": "new"},
        dedupe_key="portrait-visuals:user:snapshot",
    )

    assert job is not previous
    assert previous.dedupe_key is None
    assert job.dedupe_key == "portrait-visuals:user:snapshot"


def test_source_output_exposes_ingest_error():
    source = SimpleNamespace(
        id=uuid4(),
        title="Blocked source",
        url="https://example.com/source",
        source_type=SourceType.OTHER,
        origin=SourceOrigin.DISCOVERED,
        publisher=None,
        authors=[],
        publication_date=None,
        ingest_status=IngestStatus.FAILED,
        created_at=None,
    )

    output = _to_out(source, 0, "HTTPStatusError: 403 Forbidden")

    assert output.ingest_error == (
        "This source blocks automated access. Open it directly in your browser, "
        "or use an open-access copy."
    )


@pytest.mark.asyncio
async def test_failed_source_can_be_requeued(monkeypatch):
    source = SimpleNamespace(
        id=uuid4(),
        title="Blocked source",
        url="https://example.com/source",
        source_type=SourceType.OTHER,
        origin=SourceOrigin.DISCOVERED,
        publisher=None,
        authors=[],
        publication_date=None,
        ingest_status=IngestStatus.FAILED,
        created_at=None,
    )
    queued = []

    class Session:
        async def execute(self, _statement):
            return _Result(source)

        async def commit(self):
            return None

    async def fake_enqueue(_session, job_type, payload, **kwargs):
        queued.append((job_type, payload, kwargs))

    monkeypatch.setattr("app.jobs.queue.enqueue_job", fake_enqueue)

    output = await retry_source(str(source.id), SimpleNamespace(id=uuid4()), Session())

    assert source.ingest_status == IngestStatus.PENDING
    assert output.ingest_status == "PENDING"
    assert queued == [(
        "SOURCE_INGEST",
        {"source_id": str(source.id)},
        {"dedupe_key": f"ingest:{source.id}"},
    )]


@pytest.mark.asyncio
async def test_list_sources_counts_chunks_in_one_batch_query():
    source_id = uuid4()
    source = SimpleNamespace(
        id=source_id,
        title="Indexed source",
        url="https://example.com/source",
        source_type=SourceType.OTHER,
        origin=SourceOrigin.DISCOVERED,
        publisher=None,
        authors=[],
        publication_date=None,
        ingest_status=IngestStatus.EMBEDDED,
        created_at=None,
    )

    class Session:
        def __init__(self):
            self.calls = 0

        async def execute(self, _statement):
            self.calls += 1
            if self.calls == 1:
                return _RowsResult(scalar_rows=[source])
            if self.calls == 2:
                return _RowsResult(scalar_rows=[])
            return _RowsResult(rows=[(source_id, 4)])

    result = await list_sources(SimpleNamespace(id=uuid4()), Session())

    assert result[0].chunk_count == 4
