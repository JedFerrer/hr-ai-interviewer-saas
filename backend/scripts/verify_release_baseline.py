"""Verify migrations/startup or tests in an owned temporary source copy, without .env.
Run with the locked environment: python scripts/verify_release_baseline.py [--tests]
No application database or inherited provider credentials are used.
"""

from __future__ import annotations

import os
import secrets
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from contextlib import closing
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
HEAD = "g7a8b9c0d1e2"
PREVIOUS = "d4e5f6a7b8c9"


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="hr-release-check-") as directory:
        owned = Path(directory)
        for name in ("app", "alembic", "tests", "scripts"):
            shutil.copytree(
                BACKEND / name,
                owned / name,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
        shutil.copy(BACKEND / "alembic.ini", owned / "alembic.ini")
        env = {
            k: v
            for k, v in os.environ.items()
            if k.upper()
            in {
                "SYSTEMROOT",
                "WINDIR",
                "TEMP",
                "TMP",
                "PATH",
                "COMSPEC",
                "PATHEXT",
                "USERPROFILE",
            }
        }
        env.update(
            PYTHONUTF8="1",
            ENVIRONMENT="development",
            JWT_SECRET_KEY=secrets.token_hex(64),
            RATE_LIMIT_ENABLED="false",
            RUN_SCREENING_EVAL="",
        )

        def run(*args: str, timeout: int = 120) -> None:
            subprocess.run(
                [sys.executable, *args], cwd=owned, env=env, check=True, timeout=timeout
            )

        if "--tests" in sys.argv:
            run(
                "-m",
                "pytest",
                "tests",
                "-q",
                "--timeout=30",
                *sys.argv[sys.argv.index("--tests") + 1:],
                "--allow-hosts=127.0.0.1,::1",
                "-o",
                "asyncio_default_fixture_loop_scope=function",
                timeout=600,
            )
            return

        for name, previous in (("empty", None), ("upgrade", PREVIOUS), ("role-policy", "f6a7b8c9d0e1")):
            db = owned / (name + ".db")
            env["DATABASE_URL"] = "sqlite+aiosqlite:///" + db.as_posix()
            if previous:
                run("-m", "alembic", "upgrade", previous)
                with closing(sqlite3.connect(db)) as conn:
                    conn.execute(
                        "INSERT INTO companies (id,name,created_at,updated_at) VALUES ('fixture-company','Fictional migration company',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"
                    )
                    if previous == "f6a7b8c9d0e1":
                        conn.execute("INSERT INTO user_invites (id,company_id,email,role,token_hash,expires_at) VALUES ('legacy-invite','fixture-company','fixture@example.com','admin','fictional-hash','2099-01-01')")
                    conn.commit()
            run("-m", "alembic", "upgrade", "head")
            with closing(sqlite3.connect(db)) as conn:
                assert (
                    conn.execute("SELECT version_num FROM alembic_version").fetchone()[
                        0
                    ]
                    == HEAD
                )
                assert "resume_content_hash" in {
                    r[1] for r in conn.execute("PRAGMA table_info(candidates)")
                }
                assert (
                    conn.execute("SELECT count(*) FROM user_invites").fetchone()[0] == (1 if previous == "f6a7b8c9d0e1" else 0)
                )
                if previous == "f6a7b8c9d0e1":
                    assert conn.execute("SELECT revoked_at FROM user_invites WHERE id='legacy-invite'").fetchone()[0] is not None
                role_column = next(r for r in conn.execute("PRAGMA table_info(user_invites)") if r[1] == "role")
                assert "recruiter" in role_column[4]
                if previous:
                    assert (
                        conn.execute(
                            "SELECT name FROM companies WHERE id='fixture-company'"
                        ).fetchone()[0]
                        == "Fictional migration company"
                    )
            print(name + " migration path: PASS", flush=True)

        # ASGI transport runs the real lifespan and auth/job routes against migrated DB.
        # Prohibit external network connects; the ASGI transport is in-process.
        run("-c", SMOKE)


SMOKE = r"""import asyncio
import socket
from unittest.mock import patch
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.config import get_settings
s = get_settings()
assert not any((s.openai_api_key, s.deepseek_api_key, s.anthropic_api_key, s.resend_api_key))
original_connect = socket.socket.connect

def local_only(sock, address):
    if isinstance(address, tuple) and address[0] in ("127.0.0.1", "::1"):
        return original_connect(sock, address)
    raise RuntimeError("Outbound network disabled during smoke verification")

async def verify():
    async with app.router.lifespan_context(app), AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        assert (await client.get("/health")).status_code == 200
        result = await client.post("/auth/signup", json={"email":"release@example.com","password":"Fictional123!","name":"Release Fixture","company_name":"Fictional Release Co"})
        assert result.status_code == 201, result.status_code
        assert (await client.get("/auth/me")).status_code == 200
        assert (await client.get("/jobs")).status_code == 200
        result = await client.post("/auth/login", json={"email":"release@example.com","password":"Fictional123!"}, headers={"X-Requested-With":"XMLHttpRequest"})
        assert result.status_code == 200, result.status_code
with patch.object(socket.socket, "connect", local_only):
    asyncio.run(verify())
print("Credential-free lifespan, signup, login and jobs: PASS")
"""


if __name__ == "__main__":
    main()
