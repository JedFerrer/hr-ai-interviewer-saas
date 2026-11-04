"""Safety regressions for the owned portfolio provider and lifecycle boundaries."""

import importlib.util
import json
import os
import secrets
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
from scripts import run_portfolio_demo as runner


@pytest.fixture
def owned(monkeypatch):
    run_id = "test-" + secrets.token_hex(8)
    root = runner.root_for(run_id)
    root.mkdir()
    marker = {
        "purpose": "portfolio",
        "run_id": run_id,
        "token": secrets.token_hex(32),
        "mailbox_token": secrets.token_hex(32),
    }
    (root / ".hr-owned.json").write_text(json.dumps(marker))
    (root / "mailbox").mkdir()
    for key in list(os.environ):
        if key not in {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP"}:
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("PORTFOLIO_DEMO", "1")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("HR_OWNED_WORKSPACE", str(root))
    monkeypatch.setenv("HR_OWNED_TOKEN", marker["token"])
    monkeypatch.setenv("HR_DEMO_RUN_ID", run_id)
    monkeypatch.setenv(
        "DATABASE_URL", "sqlite+aiosqlite:///" + (root / "owned.db").as_posix()
    )
    monkeypatch.chdir(root)
    yield root, marker
    monkeypatch.chdir(Path(tempfile.gettempdir()))
    # Restore the test's own marker if the test deliberately tampered with it.
    (root / ".hr-owned.json").write_text(json.dumps(marker))
    runner.clean(root, run_id, marker["token"])


def test_activation_requires_ownership(monkeypatch):
    from app.config import Settings

    monkeypatch.delenv("HR_OWNED_WORKSPACE", raising=False)
    monkeypatch.setenv("PORTFOLIO_DEMO", "1")
    with pytest.raises(ValueError):
        Settings(_env_file=None, portfolio_demo=True)
    with pytest.raises(ValueError, match="forbidden in production"):
        Settings(
            _env_file=None,
            portfolio_demo=True,
            environment="production",
            jwt_secret_key=secrets.token_hex(32),
        )


def test_owned_activation_and_tampering(owned, monkeypatch):
    from app.demo.guard import require_demo

    root, marker = owned
    assert require_demo() == root
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-must-be-rejected")
    with pytest.raises(ValueError):
        require_demo()
    monkeypatch.delenv("OPENAI_API_KEY")
    (root / ".hr-owned.json").unlink()
    with pytest.raises(ValueError):
        require_demo()
    with pytest.raises(OSError):
        runner.clean(root, marker["run_id"], marker["token"])
    assert root.exists()


def test_capture_and_failures_are_owned_only(owned):
    from app.demo.adapters import capture, completion

    root, _ = owned
    assert capture(
        "status",
        "person@example.com",
        "<script>bad</script>",
        "<img src='https://external.invalid'>",
        "javascript:alert(1)",
    )
    assert not capture("status", "person@not-reserved.invalid", "test", "test")
    rendered = runner.mailbox_html(root, "http://127.0.0.1:3000").decode()
    assert (
        "<script>" not in rendered
        and "<img" not in rendered
        and "javascript:" not in rendered
    )
    (root / "fail-email").touch()
    assert not capture("team", "person@example.com", "test", "test")
    assert capture("team", "person@example.com", "test", "test")
    (root / "fail-processing").touch()
    with pytest.raises(ValueError, match="one-shot"):
        completion("parse", {"text": "Avery Example"})
    assert (
        "Avery Example"
        in completion("parse", {"text": "Avery Example"}).choices[0].message.content
    )
    with pytest.raises(ValueError, match="live fallback forbidden"):
        completion("unknown", {})


@pytest.mark.asyncio
async def test_live_client_and_fallback_never_reached(owned, monkeypatch):
    from types import SimpleNamespace

    from app.services import email_service, invite_service, llm_client

    config = SimpleNamespace(portfolio_demo=True)
    monkeypatch.setattr(llm_client, "_settings", config)
    monkeypatch.setattr(email_service, "settings", config)
    monkeypatch.setattr(
        invite_service,
        "get_settings",
        lambda: SimpleNamespace(portfolio_demo=True, app_url="http://127.0.0.1:3000"),
    )

    def forbidden(*args, **kwargs):
        pytest.fail("Live SDK reached")

    monkeypatch.setattr(llm_client, "AsyncOpenAI", forbidden)
    import resend

    monkeypatch.setattr(resend.Emails, "send", forbidden)
    result, model = await llm_client.llm_chat_completion(
        messages=[], operation="evaluate"
    )
    assert (
        model == "portfolio-synthetic"
        and "SYNTHETIC" in result.choices[0].message.content
    )
    with pytest.raises(ValueError):
        await llm_client.llm_chat_completion(messages=[], operation="missing")
    with pytest.raises(RuntimeError):
        llm_client._build_client({})
    assert llm_client.get_async_openai_client() is None
    assert await email_service.send_interview_invite(
        "a@example.com",
        "A",
        "Job",
        "Co",
        "http://127.0.0.1:3000/interview/session/test",
    )
    assert await email_service.send_status_email("a@example.com", "Status", "Body")
    assert await email_service.send_completion_notification(
        "a@example.com", "A", "Job", "id"
    )
    assert await invite_service.send_invite_email(
        invitee_email="b@example.com",
        inviter_name="A",
        company_name="Co",
        raw_token="synthetic",
    )


def test_socket_denial_in_subprocess():
    code = """
import socket
from app.demo.network import install
install()
with socket.socket() as server:
 server.bind(("127.0.0.1", 0)); server.listen()
 with socket.socket() as client: client.connect(server.getsockname())
 for operation in [lambda: socket.socket().connect(("192.0.2.1", 80)), lambda: socket.socket().connect_ex(("192.0.2.1", 80)), lambda: socket.getaddrinfo("example.com",80), lambda: socket.gethostbyname("example.com"), lambda: socket.gethostbyaddr("192.0.2.1"), lambda: socket.socket(type=socket.SOCK_DGRAM).sendto(b"x", ("192.0.2.1",53))]:
  try: operation()
  except OSError: pass
  else: raise AssertionError("network escape")
print("loopback allowed; external TCP/UDP/DNS denied")
"""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
    result = subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        check=False,
        capture_output=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr.decode()


def test_cleanup_refuses_wrong_token_and_path(owned, tmp_path):
    root, marker = owned
    sentinel = tmp_path / "ordinary.db"
    sentinel.write_bytes(b"ordinary data")
    with pytest.raises(ValueError):
        runner.clean(root, marker["run_id"], "wrong")
    with pytest.raises(ValueError):
        runner.clean(tmp_path, marker["run_id"], marker["token"])
    assert sentinel.read_bytes() == b"ordinary data"
    assert root.exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows MAX_PATH regression")
def test_cleanup_handles_deep_next_route_cache(owned):
    root, _ = owned
    deep = Path("\\\\?\\" + str(root)) / "frontend/.next/server/route-cache"
    for _ in range(8):
        deep /= "fictional-route-segment-0123456789"
    deep.mkdir(parents=True)
    (deep / "page.rsc").write_text("fictional cache")
    # The owned fixture's real cleanup must remove this without following links.


@pytest.mark.skipif(os.name != "nt", reason="Windows junction ownership boundary")
def test_redirected_resource_refuses_access_and_cleanup(owned, tmp_path):
    import _winapi

    from app.demo.guard import require_demo

    root, marker = owned
    sentinel = tmp_path / "ordinary.db"
    sentinel.write_text("unrelated fixture data")
    junction = root / "uploads"
    _winapi.CreateJunction(str(tmp_path), str(junction))
    try:
        with pytest.raises(ValueError, match="Redirected"):
            require_demo()
        with pytest.raises(ValueError, match="Redirected"):
            runner.clean(root, marker["run_id"], marker["token"])
        assert sentinel.read_text() == "unrelated fixture data"
        assert (root / ".hr-owned.json").exists()
    finally:
        os.rmdir(junction)  # Remove the junction itself, never its target.


def test_stale_state_never_terminates_pid(owned, monkeypatch):
    root, marker = owned
    (root / "state.json").write_text(
        json.dumps({"control_port": 1, "pid": os.getpid()})
    )
    monkeypatch.setattr(
        runner, "fetch", lambda *a, **kw: (_ for _ in ()).throw(OSError("unavailable"))
    )
    with pytest.raises(OSError):
        runner.control(root, marker, "stop")
    assert root.exists()


def test_environment_strips_credentials_and_secrets_are_distinct(owned, monkeypatch):
    root, marker = owned
    monkeypatch.setenv("RESEND_API_KEY", "never-forward")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "never-forward")
    first = runner.clean_env(root, marker, 5001, 5002)
    (root / "tmp").rmdir()
    second = runner.clean_env(root, marker, 5003, 5004)
    assert "RESEND_API_KEY" not in first and "AWS_SECRET_ACCESS_KEY" not in first
    assert first["JWT_SECRET_KEY"] != second["JWT_SECRET_KEY"]
    assert first["PROXY_AUTH_SECRET"] != second["PROXY_AUTH_SECRET"]


def test_fixtures_reproducible_and_real_extraction(tmp_path):
    source = Path(__file__).parent / "fixtures/portfolio/generate.py"
    spec = importlib.util.spec_from_file_location("portfolio_generate_test", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    from app.services.resume_service import extract_text_from_bytes

    module.generate(tmp_path / "one")
    module.generate(tmp_path / "two")
    for file in (tmp_path / "one").iterdir():
        assert file.read_bytes() == (tmp_path / "two" / file.name).read_bytes()
        text = extract_text_from_bytes(file.read_bytes(), file.name)
        assert "FICTIONAL PORTFOLIO RESUME" in text
        assert "example.com" in text
