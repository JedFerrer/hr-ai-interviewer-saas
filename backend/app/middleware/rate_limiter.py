"""Rate limiter built on slowapi.

Uses Redis when REDIS_URL is set, otherwise falls back to in-memory storage.
"""

from __future__ import annotations

import hmac
import ipaddress
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import get_settings


def _client_key(request: Request) -> str:
    peer = request.client.host if request.client else "anonymous"
    # Never read client-controlled X-Forwarded-For. The supported custom Next
    # server derives identity from its socket and authenticates it to this API.
    cfg = get_settings()
    if peer in cfg.trusted_proxy_ips and cfg.proxy_auth_secret:
        supplied = request.headers.get("x-hr-proxy-token", "")
        if hmac.compare_digest(supplied, cfg.proxy_auth_secret):
            try:
                return str(ipaddress.ip_address(request.headers.get("x-hr-client-ip", "")))
            except ValueError:
                pass
    return peer


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
