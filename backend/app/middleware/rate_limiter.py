"""Simple in-memory rate limiter middleware."""

from __future__ import annotations

import time
from collections import defaultdict

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware

# Config: {path_prefix: (max_requests, window_seconds)}
RATE_LIMITS: dict[str, tuple[int, int]] = {
    "/auth/login": (20, 60),       # 20 per minute
    "/auth/signup": (5, 60),       # 5 per minute
    "/interview/start": (10, 3600),  # 10 per hour
    "/interview/message": (60, 60),  # 60 per minute
}

# Exact-path rate limits (only match exact path, not prefix)
EXACT_RATE_LIMITS: dict[str, tuple[int, int]] = {
    "/interview/apply": (10, 60),    # 10 per minute (POST only, not status polls)
}


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Per-IP rate limiting for specific endpoints.

    Uses an in-memory store — fine for single-process MVP.
    Replace with Redis for multi-process production.
    """

    def __init__(self, app):
        super().__init__(app)
        # {(ip, path_prefix): [timestamp, ...]}
        self._requests: dict[tuple[str, str], list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        # Always skip rate limiting for CORS preflight requests (OPTIONS)
        if request.method.upper() == "OPTIONS":
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path

        for prefix, (max_req, window) in RATE_LIMITS.items():
            if path.startswith(prefix):
                key = (client_ip, prefix)
                now = time.time()

                # Prune old entries
                self._requests[key] = [
                    t for t in self._requests[key] if now - t < window
                ]

                if len(self._requests[key]) >= max_req:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"Rate limit exceeded. Max {max_req} requests per {window}s.",
                    )

                self._requests[key].append(now)
                break

        # Exact-path rate limits (don't match sub-paths like /apply/xxx/status)
        for exact_path, (max_req, window) in EXACT_RATE_LIMITS.items():
            if path == exact_path:
                key = (client_ip, exact_path)
                now = time.time()

                self._requests[key] = [
                    t for t in self._requests[key] if now - t < window
                ]

                if len(self._requests[key]) >= max_req:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"Rate limit exceeded. Max {max_req} requests per {window}s.",
                    )

                self._requests[key].append(now)
                break

        return await call_next(request)
