"""Ownership boundary for destructive/data-export/provider development utilities."""

import hmac
import json
import os
import tempfile
from pathlib import Path

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


def require_owned_workspace(*, providers=False, http_target=False) -> Path:
    # Never load .env or echo connection strings on a refusal path.
    if os.environ.get("ENVIRONMENT", "development").strip().lower() != "development":
        raise SystemExit(
            "REFUSING: utilities require development in an owned disposable workspace"
        )
    raw = os.environ.get("HR_OWNED_WORKSPACE", "")
    token = os.environ.get("HR_OWNED_TOKEN", "")
    if not raw or len(token) < 32:
        raise SystemExit(
            "REFUSING: use scripts/run_owned_utility.py; no ownership proof"
        )
    original = Path(raw).absolute()
    root = original.resolve()
    if (
        root != original
        or not root.name.startswith("hr-owned-")
        or not root.is_relative_to(Path(tempfile.gettempdir()).resolve())
        or Path.cwd().resolve() != root
    ):
        raise SystemExit("REFUSING: workspace is not an owned temporary target")
    try:
        marker = json.loads((root / ".hr-owned.json").read_text(encoding="utf-8"))
        valid = hmac.compare_digest(str(marker.get("token", "")), token)
    except (OSError, ValueError):
        valid = False
    if not valid or (root / ".env").exists():
        raise SystemExit("REFUSING: invalid workspace marker or inherited .env")
    try:
        url = make_url(os.environ.get("DATABASE_URL", ""))
        db = Path(url.database or "").resolve()
        valid = (
            url.drivername == "sqlite+aiosqlite"
            and db == root / "owned.db"
            and not url.query
        )
    except (ArgumentError, ValueError, OSError, RuntimeError):
        valid = False
    if not valid:
        raise SystemExit("REFUSING: database is not the runner-owned SQLite target")
    if providers and os.environ.get("HR_ALLOW_PROVIDERS") != "1":
        raise SystemExit(
            "REFUSING: live provider utility requires explicit --allow-providers"
        )
    if http_target:
        raise SystemExit(
            "REFUSING: HTTP stress tools need a runner-owned API; stage D integration is required"
        )
    return root


def owned_path(path) -> Path:
    root = require_owned_workspace()
    target = Path(path).resolve()
    if not target.is_relative_to(root) or target == root:
        raise SystemExit("REFUSING: output/deletion target escapes owned workspace")
    return target
