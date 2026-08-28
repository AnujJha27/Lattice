import pytest


@pytest.mark.asyncio
async def test_openalex_prefers_https_open_access_pdf(monkeypatch):
    from app.providers.openalex import OpenAlexProvider

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "results": [{
                    "title": "Open mathematics paper",
                    "primary_location": {"landing_page_url": "https://publisher.example/paper"},
                    "best_oa_location": {"pdf_url": "https://repository.example/paper.pdf"},
                    "doi": "https://doi.org/10.1234/example",
                    "publication_date": "2026-01-02",
                    "authorships": [],
                }],
            }

    class Client:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def get(self, *_args, **_kwargs):
            return Response()

    monkeypatch.setattr("httpx.AsyncClient", Client)

    [hit] = await OpenAlexProvider().search("open mathematics")

    assert hit.url == "https://repository.example/paper.pdf"
    assert hit.extra["doi"] == "10.1234/example"


@pytest.mark.asyncio
async def test_tavily_preserves_raw_content_for_source_ingestion(monkeypatch):
    from app.providers.tavily import TavilySearchProvider

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"results": [{
                "title": "Readable source",
                "url": "https://blocked.example/source",
                "content": "short search excerpt",
                "raw_content": "full source text",
            }]}

    class Client:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, _url, **_kwargs):
            assert _kwargs["headers"]["Authorization"] == "Bearer key"
            return Response()

    monkeypatch.setattr("httpx.AsyncClient", Client)

    [hit] = await TavilySearchProvider("key").search("source", limit=1)

    assert hit.extra["raw_content"] == "full source text"


@pytest.mark.asyncio
async def test_tavily_extracts_a_specific_source_url(monkeypatch):
    from app.providers.tavily import TavilySearchProvider

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"results": [{
                "url": "https://blocked.example/source",
                "raw_content": "full extracted source text",
            }]}

    class Client:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, _url, **kwargs):
            assert kwargs["headers"]["Authorization"] == "Bearer key"
            assert kwargs["json"] == {
                "urls": "https://blocked.example/source",
                "extract_depth": "basic",
            }
            return Response()

    monkeypatch.setattr("httpx.AsyncClient", Client)

    content = await TavilySearchProvider("key").extract("https://blocked.example/source")

    assert content == "full extracted source text"
