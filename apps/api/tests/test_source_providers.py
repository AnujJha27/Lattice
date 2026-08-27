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
