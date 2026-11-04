"""Stage C regressions. Synthetic data; external provider operations are mocked."""

import asyncio
import io
import json
import logging
import os
import secrets
import subprocess
import sys
import tempfile
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from app.config import Settings
from app.main import app
from app.models import Base, Candidate, Company, JobPosting, User
from app.models.user_invite import UserInvite
from app.services import candidate_service, interview_service, invite_service
from app.services.resume_service import extract_text_from_bytes
from app.utils.passwords import validate_password_bytes
from app.utils.security import hash_password, verify_password
from app.utils.storage import MAX_FILE_SIZE, read_resume_upload, validate_resume_content
from docx import Document
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.requests import Request

from tests import test_tier1_features
from tests.conftest import db_session_factory

seeded = test_tier1_features.seeded  # Register the shared fixture in this module.


@pytest.mark.parametrize(
    "secret",
    [
        "",
        "short",
        "change-this-in-production",
        "hr-interviewer-dev-secret-key-2026",
        "replace-me-with-a-64-byte-hex-secret",
        " " * 80,
    ],
)
def test_production_rejects_published_secrets(secret):
    with pytest.raises(ValueError):
        Settings(_env_file=None, environment="production", jwt_secret_key=secret)


@pytest.mark.parametrize(
    "environment", ["prod", "productionn", "staging", "", "developmnt"]
)
def test_environment_typos_fail_closed(environment):
    with pytest.raises(ValueError):
        Settings(_env_file=None, environment=environment)


def test_configuration_accepts_generated_secret_and_credential_free_development():
    assert (
        Settings(
            _env_file=None,
            environment="production",
            jwt_secret_key=secrets.token_hex(32),
        ).environment
        == "production"
    )
    assert not Settings(_env_file=None).active_llm_api_key
    with pytest.raises(ValueError):
        Settings(_env_file=None, trusted_proxy_ips=["127.0.0.1"])
    with pytest.raises(ValueError):
        Settings(
            _env_file=None,
            environment="production",
            jwt_secret_key=secrets.token_hex(32),
            enable_test_emails=True,
        )


@pytest.mark.parametrize(
    "password", ["a1" * 37, "界" * 24 + "1", "a1\0abcdefghi", "\ud800"]
)
def test_password_byte_limits_without_truncation(password):
    with pytest.raises(ValueError):
        validate_password_bytes(password)
    assert verify_password(password, hash_password("validpassword123")) is False


@pytest.mark.asyncio
async def test_password_routes_reject_long_unicode(client):
    value = "界" * 24 + "1"
    for path, data in [
        (
            "/auth/signup",
            {
                "email": "unicode@example.com",
                "password": value,
                "name": "Fixture",
                "company_name": "Fixture",
            },
        ),
        ("/auth/login", {"email": "unicode@example.com", "password": value}),
    ]:
        response = await client.post(path, json=data)
        assert response.status_code == 422
    boundary = "A1" + "界" * 23 + "a"  # exactly 72 UTF-8 bytes
    assert len(boundary.encode()) == 72
    result = await client.post(
        "/auth/signup",
        json={
            "email": "boundary@example.com",
            "password": boundary,
            "name": "Fixture",
            "company_name": "Fixture",
        },
    )
    assert result.status_code == 201
    assert (
        await client.post(
            "/auth/login", json={"email": "boundary@example.com", "password": boundary}
        )
    ).status_code == 200


@pytest.mark.asyncio
async def test_manual_notification_failure_retry_conflict_and_status(client, seeded):
    base = f"/candidates/{seeded['candidate_id']}"
    headers = seeded["headers"]
    sender = AsyncMock(side_effect=[False, True, True, True])
    with patch("app.services.email_service.send_status_email", sender):
        await client.post(base + "/shortlist", headers=headers)
        sender.assert_not_awaited()
        assert (
            await client.post(
                base + "/send-notification", headers=headers, json={"kind": "reject"}
            )
        ).status_code == 409
        failed = await client.post(
            base + "/send-notification", headers=headers, json={"kind": "shortlist"}
        )
        assert failed.json()["sent"] is False
        assert failed.json()["last_notification_sent_at"] is None
        good = await client.post(
            base + "/send-notification", headers=headers, json={"kind": "shortlist"}
        )
        assert good.json()["sent"] is True
        repeated = await client.post(
            base + "/send-notification",
            headers=headers,
            json={"kind": "shortlist", "force": True},
        )
        assert repeated.json()["sent"] is False  # force never bypasses cooldown
        await client.post(base + "/reject", headers=headers)
        conflict = await client.post(
            base + "/send-notification", headers=headers, json={"kind": "reject"}
        )
        assert (
            conflict.status_code == 409
            and conflict.json()["detail"]["code"] == "notification_conflict"
        )
        correction = await client.post(
            base + "/send-notification",
            headers=headers,
            json={"kind": "status_correction"},
        )
        assert correction.json()["sent"] is True
        assert (
            await client.post(
                base + "/send-notification",
                headers=headers,
                json={"kind": "reject", "force": True},
            )
        ).json()["sent"] is True
    assert sender.await_count == 4


@pytest.mark.asyncio
async def test_notification_cooldown_allows_later_resend(client, seeded):
    base = f"/candidates/{seeded['candidate_id']}"
    await client.post(base + "/shortlist", headers=seeded["headers"])
    async with db_session_factory() as db:
        candidate = await db.get(Candidate, seeded["candidate_id"])
        candidate.last_status_email_kind = "shortlist"
        candidate.last_status_email_sent_at = datetime.now(UTC) - timedelta(minutes=2)
        await db.commit()
    with patch(
        "app.services.email_service.send_status_email", AsyncMock(return_value=True)
    ) as sender:
        assert (
            await client.post(
                base + "/send-notification",
                headers=seeded["headers"],
                json={"kind": "shortlist"},
            )
        ).json()["sent"] is True
        sender.assert_awaited_once()


@pytest.mark.asyncio
async def test_cross_company_direct_routes(client, seeded):
    other = await client.post(
        "/auth/signup",
        json={
            "email": "other@example.com",
            "password": "otherpassword123",
            "name": "Other",
            "company_name": "Other",
        },
    )
    headers = {
        "Authorization": "Bearer " + other.json()["access_token"],
        "X-Requested-With": "XMLHttpRequest",
    }
    client.cookies.clear()
    cid, jid = seeded["candidate_id"], seeded["job_id"]
    for method, path, payload in [
        ("GET", f"/candidates/{cid}", None),
        ("GET", f"/candidates/{cid}/resume", None),
        ("POST", f"/candidates/{cid}/shortlist", None),
        ("POST", f"/candidates/{cid}/send-notification", {"kind": "shortlist"}),
        ("POST", f"/candidates/{cid}/share", None),
        ("DELETE", f"/candidates/{cid}/share/fake", None),
        ("GET", f"/jobs/{jid}", None),
        ("GET", f"/jobs/{jid}/candidates", None),
        ("GET", f"/jobs/{jid}/stream", None),
        ("GET", f"/analytics/jobs/{jid}", None),
    ]:
        response = await client.request(method, path, headers=headers, json=payload)
        assert response.status_code == 404, (method, path, response.status_code)
    overview = await client.get("/analytics/overview", headers=headers)
    assert (
        overview.status_code == 200
        and cid not in overview.text
        and jid not in overview.text
    )
    members = await client.get("/team/members", headers=headers)
    assert "test@example.com" not in members.text


@pytest.mark.asyncio
async def test_recruiter_cannot_invite_escalate_or_list_invites(client, auth_headers):
    async with db_session_factory() as db:
        user = (await db.execute(select(User))).scalar_one()
        user.role = "recruiter"
        await db.commit()
    # The existing JWT still says admin: authorization must use the current DB user.
    for method, path, payload in [
        ("POST", "/team/invites", {"email": "new@example.com"}),
        ("GET", "/team/invites", None),
        ("DELETE", "/team/invites/fake", None),
    ]:
        assert (
            await client.request(method, path, headers=auth_headers, json=payload)
        ).status_code == 403
    assert (await client.get("/team/members", headers=auth_headers)).status_code == 200


@pytest.mark.asyncio
async def test_invite_delivery_failure_revokes_and_allows_retry(client, auth_headers):
    with patch(
        "app.services.invite_service.send_invite_email", AsyncMock(return_value=False)
    ):
        failed = await client.post(
            "/team/invites", headers=auth_headers, json={"email": "retry@example.com"}
        )
        assert failed.status_code == 503
    async with db_session_factory() as db:
        row = (await db.execute(select(UserInvite))).scalar_one()
        assert row.revoked_at is not None
    with patch(
        "app.services.invite_service.send_invite_email", AsyncMock(return_value=True)
    ):
        assert (
            await client.post(
                "/team/invites",
                headers=auth_headers,
                json={"email": "retry@example.com"},
            )
        ).status_code == 201
        assert (
            await client.post(
                "/team/invites",
                headers=auth_headers,
                json={"email": "elevate@example.com", "role": "admin"},
            )
        ).status_code == 422


@pytest.mark.asyncio
async def test_concurrent_acceptance_and_notification_file_database(tmp_path):
    engine = create_async_engine(
        "sqlite+aiosqlite:///" + (tmp_path / "concurrent.db").as_posix()
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        async with factory() as db:
            company = Company(name="Synthetic")
            db.add(company)
            await db.flush()
            owner = User(
                company_id=company.id,
                email="owner@example.com",
                name="Owner",
                role="admin",
                password_hash=hash_password("synthetic123"),
            )
            db.add(owner)
            await db.flush()
            _invite, token = await invite_service.create_invite(
                db, company_id=company.id, inviter=owner, email="join@example.com"
            )
            job = JobPosting(
                company_id=company.id,
                title="Fixture",
                description="Fixture",
                employment_type="full_time",
                interview_config={},
            )
            db.add(job)
            await db.flush()
            candidate = Candidate(
                job_posting_id=job.id,
                email="candidate@example.com",
                normalized_email="candidate@example.com",
                name="Fixture",
                status="shortlisted",
            )
            db.add(candidate)
            await db.commit()
            cid, company_id = candidate.id, company.id

        async def accept():
            async with factory() as db:
                try:
                    return await invite_service.accept_invite(
                        db, raw_token=token, name="Joiner", password="synthetic123"
                    )
                except HTTPException as exc:
                    return exc.status_code

        results = await asyncio.gather(accept(), accept())
        assert sum(isinstance(r, tuple) for r in results) == 1
        async with factory() as db:
            assert (
                await db.scalar(
                    select(func.count())
                    .select_from(User)
                    .where(User.email == "join@example.com")
                )
            ) == 1

        async def notify():
            async with factory() as db:
                return (
                    await candidate_service.send_status_notification(
                        db, cid, company_id, kind="shortlist"
                    )
                )[1]

        async def delivered(**kwargs):
            await asyncio.sleep(0.02)
            return True

        with patch(
            "app.services.email_service.send_status_email",
            AsyncMock(side_effect=delivered),
        ) as sender:
            results = await asyncio.gather(notify(), notify())
            assert sorted(results) == [False, True]
            sender.assert_awaited_once()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_token_and_error_logs_never_include_sensitive_markers(client, caplog):
    caplog.set_level(logging.INFO)
    marker = "SYNTHETIC_PRIVATE_TOKEN_123456789"
    await client.get(
        "/auth/invite/" + marker + "?token=" + marker,
        headers={
            "Authorization": "Bearer " + marker,
            "Cookie": "hri_session=" + marker,
        },
    )
    await client.get("/unknown/" + marker)
    try:
        raise RuntimeError("provider echoed " + marker)
    except RuntimeError:
        logging.getLogger("app.services.email_service").exception("failed %s", marker)
    logging.getLogger("uvicorn.access").info(
        '%s - "%s %s HTTP/%s" %d', "127.0.0.1", "GET", "/report/" + marker, "1.1", 404
    )
    logging.getLogger("httpx").info("HTTP Request %s", "http://local/?token=" + marker)
    assert marker not in caplog.text
    assert "/auth/invite/{token}" in caplog.text and "status=404" in caplog.text


def request_for(peer, headers):
    return Request(
        {
            "type": "http",
            "client": (peer, 123),
            "headers": [(k.encode(), v.encode()) for k, v in headers.items()],
            "method": "GET",
            "path": "/",
        }
    )


def test_proxy_identity_requires_peer_secret_and_valid_ip(monkeypatch):
    from app.middleware import rate_limiter as module

    cfg = Settings(
        _env_file=None, trusted_proxy_ips=["127.0.0.1"], proxy_auth_secret="s" * 32
    )
    monkeypatch.setattr(module, "get_settings", lambda: cfg)
    assert (
        module._client_key(request_for("10.0.0.2", {"x-forwarded-for": "8.8.8.8"}))
        == "10.0.0.2"
    )
    valid = {
        "x-hr-proxy-token": "s" * 32,
        "x-hr-client-ip": "192.0.2.1",
        "x-forwarded-for": "8.8.8.8",
    }
    assert module._client_key(request_for("127.0.0.1", valid)) == "192.0.2.1"
    assert module._client_key(request_for("10.0.0.2", valid)) == "10.0.0.2"
    assert (
        module._client_key(
            request_for("127.0.0.1", {**valid, "x-hr-proxy-token": "forged"})
        )
        == "127.0.0.1"
    )


@pytest.mark.asyncio
async def test_enabled_legacy_limiter_blocks_spoofing_and_separates_proxy_clients(
    monkeypatch,
):
    from app.middleware import rate_limiter as module

    cfg = Settings(
        _env_file=None, trusted_proxy_ips=["127.0.0.1"], proxy_auth_secret="s" * 32
    )
    monkeypatch.setattr(module, "get_settings", lambda: cfg)
    module.limiter.enabled = True
    module.limiter.reset()
    async with AsyncClient(
        transport=ASGITransport(app=app, client=("127.0.0.1", 123)),
        base_url="http://test",
    ) as client:
        with patch(
            "app.services.interview_service.get_job_by_token",
            AsyncMock(side_effect=HTTPException(404, "not found")),
        ):
            for i in range(11):
                response = await client.post(
                    "/interview/start",
                    data={
                        "job_token": "fictional",
                        "candidate_name": "Fixture",
                        "candidate_email": "fixture@example.com",
                    },
                    files={"resume": ("fixture.pdf", b"%PDF-")},
                    headers={"x-forwarded-for": f"192.0.2.{i}"},
                )
                assert response.status_code == (404 if i < 10 else 429)
            for ip in ("192.0.2.40", "192.0.2.41"):
                response = await client.post(
                    "/interview/start",
                    data={
                        "job_token": "fictional",
                        "candidate_name": "Fixture",
                        "candidate_email": "fixture@example.com",
                    },
                    files={"resume": ("fixture.pdf", b"%PDF-")},
                    headers={"x-hr-client-ip": ip, "x-hr-proxy-token": "s" * 32},
                )
                assert response.status_code == 404
    module.limiter.reset()


@pytest.mark.parametrize(
    "script",
    [
        "seed_data",
        "reset_db",
        "dump_transcripts",
        "stress_test_interview_flow",
        "probe_pathological_answers",
        "stress_test_scoring",
        "stress_test_scoring_nontech",
        "stress_test_stuffing",
        "run_resume_parsing_eval",
    ],
)
@pytest.mark.parametrize("environment", ["production", "development"])
def test_scripts_refuse_before_mutation_or_sensitive_output(
    script, tmp_path, environment
):
    backend = Path(__file__).resolve().parents[1]
    victim = tmp_path / "untouched.db"
    victim.write_text("SYNTHETIC_PRIVATE_CONTENT")
    env = {
        k: v
        for k, v in os.environ.items()
        if k.upper() in {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP"}
    }
    env.update(
        ENVIRONMENT=environment, DATABASE_URL="sqlite+aiosqlite:///" + victim.as_posix()
    )
    result = subprocess.run(
        [sys.executable, str(backend / "scripts" / (script + ".py"))],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        timeout=15,
    )
    assert result.returncode != 0 and b"REFUSING" in result.stderr + result.stdout
    assert b"SYNTHETIC_PRIVATE_CONTENT" not in result.stderr + result.stdout
    assert victim.read_text() == "SYNTHETIC_PRIVATE_CONTENT"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["untouched.db"]


def test_owned_guard_contains_paths_and_rejects_inherited_db(monkeypatch):
    from scripts.owned_workspace import owned_path, require_owned_workspace

    with tempfile.TemporaryDirectory(prefix="hr-owned-") as directory:
        root = Path(directory).resolve()
        token = secrets.token_hex(32)
        (root / ".hr-owned.json").write_text(json.dumps({"token": token}))
        monkeypatch.chdir(root)
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("HR_OWNED_WORKSPACE", str(root))
        monkeypatch.setenv("HR_OWNED_TOKEN", token)
        monkeypatch.setenv(
            "DATABASE_URL", "sqlite+aiosqlite:///" + (root / "owned.db").as_posix()
        )
        assert require_owned_workspace() == root
        for target in [
            root.parent / "outside.db",
            root / ".." / "sibling" / "owned.db",
        ]:
            with pytest.raises(SystemExit):
                owned_path(target)
        monkeypatch.setenv(
            "DATABASE_URL",
            "sqlite+aiosqlite:///" + (root.parent / "outside.db").as_posix(),
        )
        with pytest.raises(SystemExit):
            require_owned_workspace()
        monkeypatch.chdir(root.parent)


@pytest.mark.asyncio
async def test_bounded_read_stops_at_limit_and_never_uses_unbounded_read():
    class Upload:
        size = None
        filename = "fixture.pdf"
        read_bytes = 0

        async def read(self, n):
            assert 0 < n <= 65536
            self.read_bytes += n
            return b"x" * n

    upload = Upload()
    with pytest.raises(HTTPException) as caught:
        await read_resume_upload(upload)
    assert caught.value.status_code == 413 and upload.read_bytes == MAX_FILE_SIZE + 1


@pytest.mark.asyncio
async def test_request_body_limit_before_multipart_parsing(client):
    response = await client.post(
        "/interview/apply",
        content=b"small",
        headers={"Content-Length": str(12 * 1024 * 1024)},
    )
    assert response.status_code == 413


@pytest.mark.parametrize("kind", ["fake", "bomb", "entity", "empty"])
def test_hostile_docx_is_rejected(kind):
    if kind == "empty":
        content = b""
    else:
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("[Content_Types].xml", "fixture")
            if kind != "fake":
                z.writestr(
                    "word/document.xml",
                    "x" * (1024 * 1024)
                    if kind == "bomb"
                    else '<!DOCTYPE x [<!ENTITY a "evil">]><x/>',
                )
        content = output.getvalue()
    with pytest.raises(ValueError):
        validate_resume_content("fixture.docx", content)


def test_parser_accepts_synthetic_docx_and_rejects_bad_pdf():
    document = Document()
    document.add_paragraph("Fictional applicant: Python engineering")
    buffer = io.BytesIO()
    document.save(buffer)
    assert "Fictional applicant" in extract_text_from_bytes(
        buffer.getvalue(), "fixture.docx"
    )
    with pytest.raises(ValueError):
        extract_text_from_bytes(b"%PDF-1.4 malformed", "bad.pdf")


@pytest.mark.asyncio
async def test_expired_and_revoked_interview_tokens(client, seeded):
    token = "synthetic-interview-token"
    async with db_session_factory() as db:
        candidate = await db.get(Candidate, seeded["candidate_id"])
        candidate.interview_token = token
        candidate.status = "in_progress"
        candidate.interview_link_expires_at = datetime.now(UTC) - timedelta(seconds=1)
        from app.models.interview import Interview

        interview = await db.get(Interview, seeded["interview_id"])
        interview.status = "in_progress"
        await db.commit()
    for method, path, payload in [
        ("GET", f"/interview/session/{token}", None),
        ("POST", f"/interview/session/{token}/start", None),
        (
            "POST",
            "/interview/message",
            {"interview_token": token, "message": "Fixture response"},
        ),
        ("GET", f"/interview/{token}/status", None),
    ]:
        assert (await client.request(method, path, json=payload)).status_code == 410
    async with db_session_factory() as db:
        candidate = await db.get(Candidate, seeded["candidate_id"])
        candidate.status = "rejected"
        candidate.interview_link_expires_at = datetime.now(UTC) + timedelta(days=1)
        await db.commit()
    assert (await client.get(f"/interview/session/{token}")).status_code == 404
    assert (
        await client.post(
            "/interview/message", json={"interview_token": token, "message": "Fixture"}
        )
    ).status_code == 400


@pytest.mark.asyncio
async def test_old_admin_invite_cannot_be_consumed_before_migration(
    client, auth_headers
):
    async with db_session_factory() as db:
        owner = (await db.execute(select(User))).scalar_one()
        invite, token = await invite_service.create_invite(
            db, company_id=owner.company_id, inviter=owner, email="legacy@example.com"
        )
        invite.role = "admin"
        await db.commit()
    assert (await client.get("/auth/invite/" + token)).status_code == 404
    assert (
        await client.post(
            "/auth/invite/" + token + "/accept",
            json={"name": "Legacy", "password": "fictional123"},
        )
    ).status_code == 404


@pytest.mark.asyncio
async def test_interview_email_retry_does_not_regenerate_or_duplicate(client, seeded):
    async with db_session_factory() as db:
        candidate = await db.get(Candidate, seeded["candidate_id"])
        candidate.status = "ready"
        candidate.invite_sent_at = None
        candidate.interview_token = "synthetic-session"
        candidate.interview_link_expires_at = datetime.now(UTC) + timedelta(days=1)
        await db.commit()
    path = f"/candidates/{seeded['candidate_id']}/retry-invite"
    with patch(
        "app.services.email_service.send_interview_invite",
        AsyncMock(side_effect=[False, True]),
    ) as sender:
        assert (await client.post(path, headers=seeded["headers"])).status_code == 503
        assert (await client.post(path, headers=seeded["headers"])).status_code == 200
        assert (await client.post(path, headers=seeded["headers"])).status_code == 409
        assert sender.await_count == 2
    from app.models.interview import Interview

    async with db_session_factory() as db:
        assert (
            await db.scalar(
                select(func.count())
                .select_from(Interview)
                .where(Interview.candidate_id == seeded["candidate_id"])
            )
            == 1
        )
        assert (
            await db.get(Candidate, seeded["candidate_id"])
        ).invite_sent_at is not None


@pytest.mark.asyncio
async def test_processing_failure_is_sanitized_and_duplicate_background_work_stops(
    client, seeded
):
    async with db_session_factory() as db:
        candidate = await db.get(Candidate, seeded["candidate_id"])
        candidate.status = "processing"
        await db.commit()
    with (
        patch.object(interview_service, "async_session_factory", db_session_factory),
        patch.object(
            interview_service,
            "get_async_openai_client",
            side_effect=RuntimeError("SYNTHETIC_PROVIDER_SECRET"),
        ) as provider,
    ):
        await interview_service.process_application_background(
            seeded["candidate_id"], seeded["job_id"], b"fixture", "fixture.pdf"
        )
        await interview_service.process_application_background(
            seeded["candidate_id"], seeded["job_id"], b"fixture", "fixture.pdf"
        )
        assert provider.call_count == 1
    async with db_session_factory() as db:
        candidate = await db.get(Candidate, seeded["candidate_id"])
        assert candidate.status == "error" and "retry" in candidate.pre_screen_reason
        assert "SYNTHETIC_PROVIDER_SECRET" not in candidate.pre_screen_reason


def synthetic_pdf(pages=1):
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b""]
    page_ids = []
    for _ in range(pages):
        page_id = len(objects) + 1
        page_ids.append(page_id)
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> /Contents {page_id + 1} 0 R >>".encode()
        )
        stream = b"BT /F1 12 Tf 72 720 Td (Fictional PDF resume) Tj ET"
        objects.append(
            b"<< /Length "
            + str(len(stream)).encode()
            + b" >>\nstream\n"
            + stream
            + b"\nendstream"
        )
    objects[1] = (
        f"<< /Type /Pages /Count {pages} /Kids ["
        + " ".join(f"{i} 0 R" for i in page_ids)
        + "] >>"
    ).encode()
    output = b"%PDF-1.4\n"
    offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(output))
        output += str(i).encode() + b" 0 obj\n" + obj + b"\nendobj\n"
    xref = len(output)
    output += f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode()
    for off in offsets[1:]:
        output += f"{off:010d} 00000 n \n".encode()
    output += f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    return output


def test_parser_accepts_pdf_and_enforces_page_limit():
    assert "Fictional PDF resume" in extract_text_from_bytes(
        synthetic_pdf(), "fixture.pdf"
    )
    with pytest.raises(ValueError):
        extract_text_from_bytes(synthetic_pdf(31), "fixture.pdf")


def test_parser_timeout_becomes_controlled_failure():
    with patch(
        "app.services.resume_service.subprocess.run",
        side_effect=subprocess.TimeoutExpired("parser", 12),
    ), pytest.raises(ValueError, match="time limit"):
        extract_text_from_bytes(synthetic_pdf(), "fixture.pdf")


@pytest.mark.asyncio
async def test_chunked_multipart_body_limit(client):
    async def chunks():
        yield b'--boundary\r\nContent-Disposition: form-data; name="resume"; filename="large.pdf"\r\nContent-Type: application/pdf\r\n\r\n'
        for _ in range(12):
            yield b"x" * (1024 * 1024)
        yield b"\r\n--boundary--\r\n"

    response = await client.post(
        "/interview/apply",
        content=chunks(),
        headers={"Content-Type": "multipart/form-data; boundary=boundary"},
    )
    assert response.status_code == 413
