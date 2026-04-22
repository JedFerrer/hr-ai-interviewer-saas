"""Reset the development database: drop file, run migrations, run seeds.

Refuses to run if `ENVIRONMENT=production` to prevent catastrophe.
Usage:
    python scripts/reset_db.py
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

# Make `app.*` importable
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import get_settings  # noqa: E402


def _refuse_in_production(settings) -> None:
    if settings.environment.lower() == "production":
        raise SystemExit("REFUSING to reset DB in production environment.")


def _drop_sqlite_file(database_url: str) -> None:
    """If the URL points at a local SQLite file, delete it."""
    if "sqlite" not in database_url:
        print(f"⚠️  Non-sqlite URL ({database_url}); skipping file delete.")
        return

    parsed = urlparse(database_url.replace("+aiosqlite", "").replace("+pysqlite", ""))
    # sqlite:///./hr_interviewer.db  → path is "/./hr_interviewer.db"
    raw_path = parsed.path.lstrip("/")
    if not raw_path:
        print("⚠️  Could not parse sqlite path from URL; skipping.")
        return

    path = (ROOT / raw_path).resolve()
    for suffix in ("", "-journal", "-wal", "-shm"):
        target = path.with_name(path.name + suffix)
        if target.exists():
            target.unlink()
            print(f"🗑️  Deleted {target}")


def _run_alembic_upgrade() -> None:
    print("⏫ Running alembic upgrade head...")
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=ROOT,
        env=os.environ.copy(),
    )
    if result.returncode != 0:
        raise SystemExit("alembic upgrade failed")


def _run_seeds() -> None:
    print("🌱 Seeding database...")
    from scripts.seed_data import seed
    asyncio.run(seed())


def main() -> None:
    settings = get_settings()
    _refuse_in_production(settings)
    _drop_sqlite_file(settings.database_url)
    _run_alembic_upgrade()
    _run_seeds()
    print("✅ Database reset complete.")


if __name__ == "__main__":
    main()
