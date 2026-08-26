"""Supabase Auth JWT verification.

Supabase issues asymmetric (ES/RS256) JWTs exposed via a JWKS endpoint;
older projects may still use HS256 with the legacy JWT secret. We verify
against JWKS and fall back to the shared secret when configured.
"""
import time

import jwt
from jwt import PyJWKClient

from app.core.config import get_settings

_jwk_client: PyJWKClient | None = None


def _get_jwk_client() -> PyJWKClient:
    global _jwk_client
    if _jwk_client is None:
        _jwk_client = PyJWKClient(get_settings().jwks_url, cache_keys=True, lifespan=3600)
    return _jwk_client


class InvalidToken(Exception):
    pass


def verify_supabase_jwt(token: str) -> dict:
    """Return the verified claims dict or raise InvalidToken."""
    settings = get_settings()
    try:
        try:
            key = _get_jwk_client().get_signing_key_from_jwt(token).key
            return jwt.decode(token, key, algorithms=["ES256", "RS256"], audience="authenticated")
        except jwt.PyJWKClientError:
            # Project may use legacy HS256 secrets.
            if not settings.supabase_jwt_secret:
                raise
            return jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
            )
    except jwt.InvalidTokenError as exc:
        raise InvalidToken(str(exc)) from exc


def is_token_expired(claims: dict) -> bool:
    return claims.get("exp", 0) < time.time()
