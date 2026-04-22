"""FastAPI application entry point."""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.middleware.rate_limiter import RateLimiterMiddleware
from app.models import Base
from app.database import engine
from app.routers import auth, candidates, interviews, jobs

settings = get_settings()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables on startup (dev only — use Alembic in production)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/verified")
    yield


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
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["content-disposition"],
)
app.add_middleware(RateLimiterMiddleware)


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
app.include_router(interviews.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
