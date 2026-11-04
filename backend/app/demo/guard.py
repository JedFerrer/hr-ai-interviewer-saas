"""Demo activation requires the existing utility ownership boundary."""

import json
import os
from pathlib import Path

from scripts.owned_workspace import require_owned_workspace


def require_demo() -> Path:
    if os.environ.get("PORTFOLIO_DEMO") != "1":
        raise ValueError("Portfolio demo requires explicit runner activation")
    try:
        root = require_owned_workspace()
    except SystemExit:
        raise ValueError("Portfolio demo requires verified runner ownership") from None
    for name in (
        ".hr-owned.json",
        "owned.db",
        "mailbox",
        "fixtures",
        "uploads",
        "uploads/resumes",
        "tmp",
    ):
        path = root / name
        if path.resolve() != path or path.is_symlink():
            raise ValueError("Redirected demo resource refused")
    marker = json.loads((root / ".hr-owned.json").read_text())
    if marker.get("purpose") != "portfolio" or marker.get("run_id") != os.environ.get(
        "HR_DEMO_RUN_ID"
    ):
        raise ValueError("Invalid portfolio ownership record")
    for key in (
        "OPENAI_API_KEY",
        "DEEPSEEK_API_KEY",
        "ANTHROPIC_API_KEY",
        "RESEND_API_KEY",
        "SUPABASE_URL",
        "SUPABASE_KEY",
        "REDIS_URL",
        "LLM_FALLBACK_PROVIDERS",
        "HR_ALLOW_PROVIDERS",
    ):
        if os.environ.get(key):
            raise ValueError("Live integration configuration forbidden in demo")
    return root
