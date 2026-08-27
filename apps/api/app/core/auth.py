"""Auth dependencies. Every user-owned resource must require CurrentUser."""
import uuid
from dataclasses import dataclass

from fastapi import Depends, Request

from app.core.config import get_settings
from app.core.errors import AppError, Forbidden
from app.core.security import InvalidToken, verify_supabase_jwt


@dataclass(frozen=True)
class CurrentUser:
    id: uuid.UUID
    email: str | None = None


async def get_current_user(request: Request) -> CurrentUser:
    auth_header = request.headers.get("authorization", "")
    if not auth_header.lower().startswith("bearer "):
        raise AppError("unauthorized", "Missing bearer token", status_code=401)
    token = auth_header.split(" ", 1)[1]
    try:
        claims = verify_supabase_jwt(token)
    except InvalidToken as exc:
        raise AppError("unauthorized", f"Invalid token: {exc}", status_code=401) from exc
    sub = claims.get("sub")
    if not sub:
        raise AppError("unauthorized", "Token missing subject claim", status_code=401)
    email = claims.get("email")
    settings = get_settings()
    if settings.is_production and (
        not isinstance(email, str) or email.casefold() not in settings.allowed_email_set
    ):
        raise Forbidden("This email is not authorized to use this application")
    return CurrentUser(id=uuid.UUID(sub), email=email if isinstance(email, str) else None)


CurrentUserDep = Depends(get_current_user)
