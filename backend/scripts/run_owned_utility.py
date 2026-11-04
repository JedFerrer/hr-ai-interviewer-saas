"""Create a fresh disposable DB for a development utility. Never targets local data.
Usage: python scripts/run_owned_utility.py seed_data [utility arguments ...]
Provider utilities need explicit --allow-providers; never forwards email keys.
"""

import argparse
import json
import os
import secrets
import subprocess
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
TOOLS = (
    "seed_data",
    "reset_db",
    "dump_transcripts",
    "stress_test_scoring",
    "stress_test_scoring_nontech",
    "stress_test_stuffing",
    "run_resume_parsing_eval",
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-providers", action="store_true")
    parser.add_argument("tool", choices=TOOLS)
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if os.environ.get(
        "ENVIRONMENT", "development"
    ).strip().lower() != "development" or os.environ.get("DATABASE_URL"):
        raise SystemExit(
            "REFUSING: clear production/environment database overrides before creating an owned workspace"
        )
    with tempfile.TemporaryDirectory(prefix="hr-owned-") as directory:
        root = Path(directory).resolve()
        token = secrets.token_hex(32)
        (root / ".hr-owned.json").write_text(
            json.dumps({"token": token}), encoding="utf-8"
        )
        env = {
            k: v
            for k, v in os.environ.items()
            if k.upper()
            in {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "COMSPEC", "PATHEXT"}
        }
        env.update(
            ENVIRONMENT="development",
            DATABASE_URL="sqlite+aiosqlite:///" + (root / "owned.db").as_posix(),
            JWT_SECRET_KEY=secrets.token_hex(64),
            HR_OWNED_WORKSPACE=str(root),
            HR_OWNED_TOKEN=token,
            PYTHONPATH=str(BACKEND),
            PYTHONUTF8="1",
        )
        if args.allow_providers:
            env["HR_ALLOW_PROVIDERS"] = "1"
            for key in (
                "OPENAI_API_KEY",
                "DEEPSEEK_API_KEY",
                "ANTHROPIC_API_KEY",
                "LLM_PROVIDER",
                "LLM_MODEL",
            ):
                if key in os.environ:
                    env[key] = os.environ[key]
        # Alembic script location is made absolute in a temporary config.
        config = (
            (BACKEND / "alembic.ini")
            .read_text(encoding="utf-8")
            .replace("%(here)s/alembic", (BACKEND / "alembic").as_posix())
        )
        (root / "alembic.ini").write_text(config, encoding="utf-8")
        subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=root,
            env=env,
            check=True,
            timeout=120,
        )
        subprocess.run(
            [
                sys.executable,
                str(BACKEND / "scripts" / (args.tool + ".py")),
                *args.arguments,
            ],
            cwd=root,
            env=env,
            check=True,
            timeout=600,
        )
        print("Owned utility completed; disposable workspace cleaned on exit.")


if __name__ == "__main__":
    main()
