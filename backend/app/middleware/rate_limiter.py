"""Rate limiter built on slowapi.

Uses Redis when REDIS_URL is set, otherwise falls back to in-memory storage.
"""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import get_settings


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "anonymous"


_settings = get_settings()
_storage_uri = _settings.redis_url.strip() if _settings.redis_url else "memory://"

limiter = Limiter(
    key_func=_client_key,
    storage_uri=_storage_uri or "memory://",
    # headers_enabled=False: avoids slowapi requiring `response: Response` in
    # every decorated handler (it crashes with 500 otherwise). Limit info is
    # still surfaced via the 429 JSON detail.
    headers_enabled=False,
    swallow_errors=True,
    enabled=_settings.rate_limit_enabled,
)


def _rate_limit_handler(request, exc):
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": f"Rate limit exceeded: {exc.detail}"},
    )


def install_rate_limiter(app: FastAPI) -> None:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
    app.add_middleware(SlowAPIMiddleware)


__all__ = ["limiter", "install_rate_limiter"]
