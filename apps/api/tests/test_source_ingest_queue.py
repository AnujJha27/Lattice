from uuid import uuid4

import pytest

from app.db.models import Concept, Source
from app.jobs.queue import enqueue_job
from app.modules.lessons.context import _persist_discovered
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
