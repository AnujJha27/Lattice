"""Provider factory — the only place that decides which LLM backend runs.

Priority: OpenRouter (if configured) → Gemini. Embeddings always use Gemini
(OpenRouter has no embedding offering worth depending on).
"""
from app.providers.llm import LLMProvider


def get_llm_provider() -> LLMProvider:
    from app.core.config import get_settings

    settings = get_settings()
    if settings.openrouter_api_key and settings.openrouter_model:
        from app.providers.openrouter import OpenRouterProvider

        return OpenRouterProvider(settings.openrouter_api_key, settings.openrouter_model)

    if settings.google_api_key_pool:
        from app.providers.gemini import GeminiProvider

        return GeminiProvider()

    raise RuntimeError(
        "No LLM provider configured — set GOOGLE_API_KEY/GOOGLE_API_KEYS or "
        "OPENROUTER_API_KEY + OPENROUTER_MODEL"
    )
