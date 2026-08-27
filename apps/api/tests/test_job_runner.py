from contextlib import asynccontextmanager
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest

from app.db.models.job import JobStatus, JobType
from app.db.models.source import IngestStatus
from app.jobs import handlers, runner


class _Result:
    def __init__(self, value=None, rows=None):
        self.value = value
        self.rows = rows or []

    def scalar_one_or_none(self):
        return self.value

    def scalars(self):
        return SimpleNamespace(all=lambda: self.rows)


class _ExpiringJob:
    def __init__(self):
        self.id = uuid4()
        self.type = JobType.SOURCE_INGEST
        self.payload = {"source_id": str(uuid4())}
        self.attempts = 1
        self.max_attempts = 1
        self._expired = False

    def __getattribute__(self, name):
        if name in {"id", "type", "payload"} and object.__getattribute__(self, "_expired"):
            raise AssertionError(f"expired ORM field accessed after rollback: {name}")
        return object.__getattribute__(self, name)


class _RunnerSession:
    def __init__(self, job, source):
        self.job = job
        self.source = source
        self.commits = 0

    async def merge(self, _job):
        return self.job

    async def rollback(self):
        self.job._expired = True

    async def get(self, _model, _source_id):
        return self.source

    async def commit(self):
        self.commits += 1


@pytest.mark.asyncio
async def test_failed_job_is_recorded_without_reading_expired_orm_fields(monkeypatch):
    job = _ExpiringJob()
    source = SimpleNamespace(ingest_status=IngestStatus.PENDING)
    session = _RunnerSession(job, source)

    async def fail_handler(_session, _payload):
        raise RuntimeError("upstream rejected")

    @asynccontextmanager
    async def session_context():
        yield session

    monkeypatch.setitem(runner.HANDLERS, "SOURCE_INGEST", fail_handler)
    monkeypatch.setattr(runner.db_session, "session_factory", session_context)

    await runner.run_job(job)

    assert job.status == JobStatus.FAILED
    assert job.last_error == "RuntimeError: upstream rejected"
    assert source.ingest_status == IngestStatus.FAILED
    assert session.commits == 1


@pytest.mark.asyncio
async def test_permanent_http_failure_is_not_retried(monkeypatch):
    job = _ExpiringJob()
    job.max_attempts = 3
    source = SimpleNamespace(ingest_status=IngestStatus.PENDING)
    session = _RunnerSession(job, source)

    async def fail_handler(_session, _payload):
        request = httpx.Request("GET", "https://example.com/source")
        response = httpx.Response(403, request=request)
        raise httpx.HTTPStatusError("blocked", request=request, response=response)

    @asynccontextmanager
    async def session_context():
        yield session

    monkeypatch.setitem(runner.HANDLERS, "SOURCE_INGEST", fail_handler)
    monkeypatch.setattr(runner.db_session, "session_factory", session_context)

    await runner.run_job(job)

    assert job.status == JobStatus.FAILED
    assert source.ingest_status == IngestStatus.FAILED


class _HttpResponse:
    headers = {"content-type": "application/pdf"}
    content = b"%PDF-1.7"

    def raise_for_status(self):
        return None


class _HttpClient:
    def __init__(self, **_kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def get(self, _url):
        return _HttpResponse()


class _SourceSession:
    def __init__(self, source):
        self.source = source
        self.added = []
        self.executions = 0

    async def execute(self, _statement):
        self.executions += 1
        if self.executions == 1:
            return _Result(value=self.source)
        return _Result(rows=[])

    def add(self, value):
        self.added.append(value)

    async def delete(self, _value):
        return None

    async def flush(self):
        return None


@pytest.mark.asyncio
async def test_remote_pdf_is_extracted_with_installed_parser(monkeypatch):
    source = SimpleNamespace(
        id=uuid4(),
        url="https://example.com/paper.pdf",
        storage_path=None,
        metadata_={},
        ingest_status=IngestStatus.PENDING,
        content_hash=None,
    )
    session = _SourceSession(source)

    class _Page:
        def extract_text(self):
            assert source.ingest_status == IngestStatus.FETCHED
            return "Readable PDF text. " * 20

    class _Reader:
        def __init__(self, stream):
            assert stream.read(5) == b"%PDF-"
            self.pages = [_Page()]

    class _Embedder:
        def __init__(self):
            pass

        async def embed(self, texts):
            return [[0.0] * 768 for _ in texts]

    monkeypatch.setattr(handlers.httpx, "AsyncClient", _HttpClient)
    monkeypatch.setattr("pypdf.PdfReader", _Reader)
    monkeypatch.setattr("app.providers.embedding.GeminiEmbeddingProvider", _Embedder)

    result = await handlers.handle_source_ingest(session, {"source_id": str(source.id)})

    assert result["chunks"] == 1
    assert result["characters"] >= 200
    assert source.ingest_status == IngestStatus.EMBEDDED


@pytest.mark.asyncio
async def test_inline_source_is_fetched_before_chunking(monkeypatch):
    source = SimpleNamespace(
        id=uuid4(),
        url=None,
        storage_path=None,
        ingest_status=IngestStatus.PENDING,
        content_hash=None,
    )
    session = _SourceSession(source)
    observed_statuses = []

    class _InlineContent:
        def __str__(self):
            observed_statuses.append(source.ingest_status)
            return "Readable note text. " * 20

    source.metadata_ = {"content": _InlineContent()}

    class _Embedder:
        def __init__(self):
            pass

        async def embed(self, texts):
            return [[0.0] * 768 for _ in texts]

    monkeypatch.setattr("app.providers.embedding.GeminiEmbeddingProvider", _Embedder)

    await handlers.handle_source_ingest(session, {"source_id": str(source.id)})

    assert observed_statuses == [IngestStatus.FETCHED]
