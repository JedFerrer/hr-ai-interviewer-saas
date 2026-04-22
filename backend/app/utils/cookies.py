"""Session cookie helpers.

Issuing the JWT in an HttpOnly cookie eliminates the largest XSS attack
surface (JS reading `localStorage`). To remain transport-agnostic during the
migration, `get_current_user` accepts either:

  - an `Authorization: Bearer <jwt>` header (legacy / API clients), or
  - a `hri_session` HttpOnly cookie (browser).

CSRF protection is handled separately in `routers` by requiring the
`X-Requested-With: XMLHttpRequest` header on mutating methods. Browsers will
not send this header on cross-site form submissions, which blocks CSRF
without paying the complexity cost of double-submit tokens.
"""

from __future__ import annotations

from fastapi import Response

from app.config import Settings

COOKIE_NAME = "hri_session"


def set_session_cookie(response: Response, token: str, settings: Settings) -> None:
    """Set the auth cookie on `response`.

    `Secure` is enabled only in production so cookies still work over plain
    `http://localhost` in dev. `SameSite=Lax` is enough because the frontend
    proxies API calls through Next.js (same-origin), so cookies are sent on
    every navigation/fetch without cross-site complications.
    """
    is_prod = settings.environment.lower() == "production"
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=settings.jwt_expiry_minutes * 60,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    """Remove the auth cookie."""
    response.delete_cookie(key=COOKIE_NAME, path="/")
