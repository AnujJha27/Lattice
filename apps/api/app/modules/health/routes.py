"""Health module."""
from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    settings = get_settings()
    llm = (
        f"openrouter:{settings.openrouter_model}"
        if settings.openrouter_api_key and settings.openrouter_model
        else ("gemini" if settings.google_api_key_pool else None)
    )
    return {
        "ok": True,
        "environment": settings.environment,
        "providers": {
            "llm": llm,
            "embeddings": "gemini" if settings.google_api_key_pool else None,
            "web_search": "tavily" if settings.tavily_api_key else None,
            "academic": ["arxiv", "openalex"],
        },
    }
