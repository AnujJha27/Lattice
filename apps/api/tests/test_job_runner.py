from contextlib import asynccontextmanager
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest

from app.db.models.job import JobStatus, JobType
from app.db.models.source import IngestStatus
from app.jobs import handlers, runner
from app.jobs.handlers import _source_fallback_url


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
async def test_arxiv_source_fetches_the_pdf_variant(monkeypatch):
    requested_urls = []
    source = SimpleNamespace(
        id=uuid4(),
        url="https://arxiv.org/abs/1706.03762",
        arxiv_id="1706.03762",
        storage_path=None,
        metadata_={},
        ingest_status=IngestStatus.PENDING,
        content_hash=None,
    )
    session = _SourceSession(source)

    class _Client(_HttpClient):
        async def get(self, url):
            requested_urls.append(url)
            return _HttpResponse()

    class _Page:
        def extract_text(self):
            return "Readable PDF text. " * 20

    class _Reader:
        def __init__(self, _stream):
            self.pages = [_Page()]

    class _Embedder:
        def __init__(self):
            pass

        async def embed(self, texts):
            return [[0.0] * 768 for _ in texts]

    monkeypatch.setattr(handlers.httpx, "AsyncClient", _Client)
    monkeypatch.setattr("pypdf.PdfReader", _Reader)
    monkeypatch.setattr("app.providers.embedding.GeminiEmbeddingProvider", _Embedder)

    await handlers.handle_source_ingest(session, {"source_id": str(source.id)})

    assert requested_urls == ["https://arxiv.org/pdf/1706.03762"]


@pytest.mark.asyncio
async def test_remote_pdf_with_octet_stream_content_type_is_extracted(monkeypatch):
    source = SimpleNamespace(
        id=uuid4(),
        url="https://repository.example/paper",
        storage_path=None,
        metadata_={},
        ingest_status=IngestStatus.PENDING,
        content_hash=None,
    )
    session = _SourceSession(source)

    class _OctetResponse(_HttpResponse):
        headers = {"content-type": "application/octet-stream"}

    class _Client(_HttpClient):
        async def get(self, _url):
            return _OctetResponse()

    class _Page:
        def extract_text(self):
            return "Readable PDF text. " * 20

    class _Reader:
        def __init__(self, _stream):
            self.pages = [_Page()]

    class _Embedder:
        def __init__(self):
            pass

        async def embed(self, texts):
            return [[0.0] * 768 for _ in texts]

    monkeypatch.setattr(handlers.httpx, "AsyncClient", _Client)
    monkeypatch.setattr("pypdf.PdfReader", _Reader)
    monkeypatch.setattr("app.providers.embedding.GeminiEmbeddingProvider", _Embedder)

    result = await handlers.handle_source_ingest(session, {"source_id": str(source.id)})

    assert result["chunks"] == 1


@pytest.mark.parametrize(
    ("url", "fallback"),
    [
        (
            "https://en.wikipedia.org/wiki/Spectral_graph_theory",
            "https://en.wikipedia.org/api/rest_v1/page/html/Spectral_graph_theory",
        ),
        (
            "https://pubmed.ncbi.nlm.nih.gov/12345678/",
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=12345678&rettype=abstract&retmode=text",
        ),
    ],
)
def test_blocked_source_uses_an_official_read_api(url, fallback):
    assert _source_fallback_url(url) == fallback


def test_blocked_lookalike_domain_has_no_official_fallback():
    assert _source_fallback_url("https://notwikipedia.org/wiki/Article") is None


@pytest.mark.asyncio
async def test_blocked_wikipedia_page_retries_with_official_read_api(monkeypatch):
    source = SimpleNamespace(
        id=uuid4(),
        url="https://en.wikipedia.org/wiki/Spectral_graph_theory",
        arxiv_id=None,
        storage_path=None,
        metadata_={},
        ingest_status=IngestStatus.PENDING,
        content_hash=None,
    )
    session = _SourceSession(source)
    requested_urls = []

    class _HtmlResponse:
        headers = {"content-type": "text/html"}
        text = "<p>Readable source text. " + "word " * 80 + "</p>"
        content = text.encode()

        def raise_for_status(self):
            return None

    class _Client(_HttpClient):
        async def get(self, url):
            requested_urls.append(url)
            if len(requested_urls) == 1:
                request = httpx.Request("GET", url)
                return httpx.Response(403, request=request)
            return _HtmlResponse()

    class _Embedder:
        def __init__(self):
            pass

        async def embed(self, texts):
            return [[0.0] * 768 for _ in texts]

    monkeypatch.setattr(handlers.httpx, "AsyncClient", _Client)
    monkeypatch.setattr("app.providers.embedding.GeminiEmbeddingProvider", _Embedder)

    await handlers.handle_source_ingest(session, {"source_id": str(source.id)})

    assert requested_urls == [
        "https://en.wikipedia.org/wiki/Spectral_graph_theory",
        "https://en.wikipedia.org/api/rest_v1/page/html/Spectral_graph_theory",
    ]


@pytest.mark.asyncio
async def test_blocked_source_uses_saved_provider_content(monkeypatch):
    source = SimpleNamespace(
        id=uuid4(),
        url="https://blocked.example/source",
        arxiv_id=None,
        storage_path=None,
        metadata_={"content": "Readable provider content. " * 40},
        ingest_status=IngestStatus.PENDING,
        content_hash=None,
    )
    session = _SourceSession(source)
    requested_urls = []

    class _Client(_HttpClient):
        async def get(self, url):
            requested_urls.append(url)
            request = httpx.Request("GET", url)
            return httpx.Response(403, request=request)

    class _Embedder:
        def __init__(self):
            pass

        async def embed(self, texts):
            return [[0.0] * 768 for _ in texts]

    monkeypatch.setattr(handlers.httpx, "AsyncClient", _Client)
    monkeypatch.setattr("app.providers.embedding.GeminiEmbeddingProvider", _Embedder)

    await handlers.handle_source_ingest(session, {"source_id": str(source.id)})

    assert requested_urls == ["https://blocked.example/source"]
    assert source.ingest_status == IngestStatus.EMBEDDED


@pytest.mark.asyncio
async def test_blocked_source_uses_tavily_extract_for_existing_source(monkeypatch):
    source = SimpleNamespace(
        id=uuid4(),
        url="https://blocked.example/source",
        arxiv_id=None,
        storage_path=None,
        metadata_={},
        ingest_status=IngestStatus.PENDING,
        content_hash=None,
    )
    session = _SourceSession(source)

    class _Client(_HttpClient):
        async def get(self, url):
            request = httpx.Request("GET", url)
            return httpx.Response(403, request=request)

    async def fake_extract(_provider, url):
        assert url == source.url
        return "Readable extracted source content. " * 40

    class _Embedder:
        def __init__(self):
            pass

        async def embed(self, texts):
            return [[0.0] * 768 for _ in texts]

    monkeypatch.setattr(handlers.httpx, "AsyncClient", _Client)
    monkeypatch.setattr("app.core.config.get_settings", lambda: SimpleNamespace(tavily_api_key="key"))
    monkeypatch.setattr("app.providers.tavily.TavilySearchProvider.extract", fake_extract)
    monkeypatch.setattr("app.providers.embedding.GeminiEmbeddingProvider", _Embedder)

    await handlers.handle_source_ingest(session, {"source_id": str(source.id)})

    assert source.ingest_status == IngestStatus.EMBEDDED
    assert source.metadata_["content_source"] == "tavily_extract"


@pytest.mark.asyncio
async def test_blocked_doi_source_uses_openalex_pdf_fallback(monkeypatch):
    source = SimpleNamespace(
        id=uuid4(),
        url="https://dl.acm.org/doi/10.1234/example",
        doi="10.1234/example",
        arxiv_id=None,
        storage_path=None,
        metadata_={},
        ingest_status=IngestStatus.PENDING,
        content_hash=None,
    )
    session = _SourceSession(source)
    requested_urls = []

    class _OpenAlexResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "best_oa_location": {"pdf_url": "https://repository.example/paper.pdf"},
            }

    class _Client(_HttpClient):
        async def get(self, url):
            requested_urls.append(url)
            if url == source.url:
                request = httpx.Request("GET", url)
                return httpx.Response(403, request=request)
            if url.startswith("https://api.openalex.org/works/"):
                return _OpenAlexResponse()
            return _HttpResponse()

    class _Page:
        def extract_text(self):
            return "Readable PDF text. " * 20

    class _Reader:
        def __init__(self, _stream):
            self.pages = [_Page()]

    class _Embedder:
        def __init__(self):
            pass

        async def embed(self, texts):
            return [[0.0] * 768 for _ in texts]

    monkeypatch.setattr(handlers.httpx, "AsyncClient", _Client)
    monkeypatch.setattr("pypdf.PdfReader", _Reader)
    monkeypatch.setattr("app.providers.embedding.GeminiEmbeddingProvider", _Embedder)

    await handlers.handle_source_ingest(session, {"source_id": str(source.id)})

    assert requested_urls == [
        source.url,
        "https://api.openalex.org/works/https://doi.org/10.1234/example",
        "https://repository.example/paper.pdf",
    ]


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
