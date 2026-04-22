"""FastAPI application entry point."""

from __future__ import annotations

import json
import logging
import sys
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.middleware.rate_limiter import install_rate_limiter
from app.routers import auth, candidates, email_templates, interviews, jobs, public, share

settings = get_settings()

# --- Logging -----------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class _AuditFormatter(logging.Formatter):
    """Render audit events as a single-line JSON object on stdout.

    Audit records always carry an `audit=True` flag in `extra` so they can be
    routed separately by aggregators (Loki, Datadog, CloudWatch).
    """

    def format(self, record: logging.LogRecord) -> str:  # noqa: D401
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "event": record.getMessage(),
        }
        # Merge any structured fields placed under record.audit_fields
        fields = getattr(record, "audit_fields", None)
        if isinstance(fields, dict):
            payload.update(fields)
        return "AUDIT " + json.dumps(payload, default=str, separators=(",", ":"))


_audit_logger = logging.getLogger("audit")
if not any(getattr(h, "_audit", False) for h in _audit_logger.handlers):
    _audit_handler = logging.StreamHandler(sys.stdout)
    _audit_handler.setFormatter(_AuditFormatter())
    _audit_handler._audit = True  # type: ignore[attr-defined]
    _audit_logger.addHandler(_audit_handler)
    _audit_logger.setLevel(logging.INFO)
    _audit_logger.propagate = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan.

    Schema is owned by Alembic — no `create_all` here. Run migrations before
    starting the app:  `alembic upgrade head`.
    """
    logger.info("App starting (env=%s)", settings.environment)
    yield
    logger.info("App shutting down")


app = FastAPI(
    title="AI HR Interviewer API",
    description="AI-powered screening interview platform",
    version="0.1.0",
    lifespan=lifespan,
)

# --- Middleware ---

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    # Explicit allowlists (avoid wildcards with credentials).
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
    expose_headers=["content-disposition"],
)
install_rate_limiter(app)


_IS_PROD = settings.environment.lower() == "production"


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Apply baseline security headers to every response."""
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(
        "Permissions-Policy", "geolocation=(), microphone=(), camera=()"
    )
    if _IS_PROD:
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
        )
    return response


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log request method, path, and duration."""
    start = time.perf_counter()
    response = await call_next(request)
    duration = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s → %s (%.0fms)",
        request.method,
        request.url.path,
        response.status_code,
        duration,
    )
    return response


# --- Routers ---

app.include_router(auth.router)
app.include_router(jobs.router)
app.include_router(candidates.router)
app.include_router(share.router)
app.include_router(interviews.router)
app.include_router(email_templates.router)
app.include_router(public.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
