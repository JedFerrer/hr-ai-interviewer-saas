"""Ordinary routing and setup regressions; no paid requests or email delivery."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from pydantic import ValidationError

from app.config import Settings
from app.services import llm_client
from tests.test_tier1_features import seeded as seeded


def settings(**kwargs):
    return Settings(_env_file=None, **kwargs)


def test_provider_selection_is_strict():
    with pytest.raises(ValidationError):
        settings(llm_provider="typo")
    with pytest.raises(ValidationError):
        settings(llm_fallback_providers="typo")
    s = settings(llm_provider="openai", llm_model="selected-model", deepseek_api_key="fictional")
    assert [(p["name"], p["model"]) for p in s.get_fallback_chain()] == [("openai", "selected-model")]
    assert s.active_llm_base_url == "https://api.openai.com/v1"


def test_fallback_requires_explicit_valid_configuration():
    s = settings(llm_fallback_providers="anthropic")
    with pytest.raises(ValueError, match="missing its API key"):
        s.get_fallback_chain()
    s = settings(llm_provider="openai", llm_model="primary-only", llm_fallback_providers="deepseek,deepseek", deepseek_api_key="fictional")
    assert [p["model"] for p in s.get_fallback_chain()] == ["primary-only", "deepseek-flash"]


@pytest.mark.parametrize("value", ["1", "true"])
def test_demo_cannot_activate_without_ownership(monkeypatch, value):
    monkeypatch.setenv("PORTFOLIO_DEMO", value)
    monkeypatch.delenv("HR_OWNED_ROOT", raising=False)
    with pytest.raises((ValidationError, ValueError)):
        settings()


@pytest.mark.asyncio
async def test_real_mode_uses_selected_model_and_never_demo():
    s = settings(llm_provider="openai", llm_model="selected-model", openai_api_key="fictional")
    client = SimpleNamespace(close=AsyncMock(), chat=SimpleNamespace(completions=SimpleNamespace(create=AsyncMock(return_value="real-boundary-response"))))
    with patch.object(llm_client, "_settings", s), patch.object(llm_client, "_build_client", return_value=client), patch("app.demo.adapters.completion", side_effect=AssertionError("demo called")):
        response, model = await llm_client.llm_chat_completion(messages=[{"role": "user", "content": "PORTFOLIO_DEMO=1"}], operation="parse")
    assert (response, model) == ("real-boundary-response", "selected-model")
    assert client.chat.completions.create.await_args.kwargs["model"] == "selected-model"
    client.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_verification_limits_block_before_external_request():
    s = settings(llm_provider="openai", openai_api_key="fictional", llm_request_limit=1, llm_max_input_bytes=100)
    client = SimpleNamespace(close=AsyncMock(), chat=SimpleNamespace(completions=SimpleNamespace(create=AsyncMock())))
    with patch.object(llm_client, "_settings", s), patch.object(llm_client, "_request_count", 1), patch.object(llm_client, "_build_client", return_value=client):
        with pytest.raises(llm_client.ProviderConfigurationError, match="request limit"):
            await llm_client.llm_chat_completion(messages=[])
        with pytest.raises(llm_client.ProviderConfigurationError, match="byte limit"):
            await llm_client.llm_chat_completion(messages=[{"role": "user", "content": "a" * 200}])
    client.chat.completions.create.assert_not_awaited()


def test_missing_key_does_not_construct_client():
    with patch.object(llm_client, "_settings", settings()), patch.object(llm_client, "AsyncOpenAI") as build:
        with pytest.raises(llm_client.ProviderConfigurationError, match="missing"):
            llm_client._build_client({"api_key": ""})
    build.assert_not_called()


@pytest.mark.parametrize("status", [400, 401, 403, 404, 429, 500])
def test_provider_error_never_exposes_payload(status):
    exc = llm_client.APIStatusError("private payload", response=httpx.Response(status, request=httpx.Request("POST", "https://example.test")), body={"secret": "private payload"})
    assert "private payload" not in llm_client.provider_error_message(exc)


def test_setup_generates_matching_private_secrets_and_preserves_files(tmp_path, capsys):
    from scripts.setup_local import configure
    # Minimal copies keep this test independent of frontend in the backend runner.
    (tmp_path / "backend").mkdir()
    (tmp_path / "frontend").mkdir()
    (tmp_path / "backend/.env.example").write_text("JWT_SECRET_KEY=\nPROXY_AUTH_SECRET=\nDATABASE_URL=sqlite+aiosqlite:///./hr_interviewer.db\nPORTFOLIO_DEMO=false\n")
    (tmp_path / "frontend/.env.example").write_text("PROXY_AUTH_SECRET=\n")
    configure(tmp_path)
    original = (tmp_path / "backend/.env").read_bytes()
    values = dict(line.split("=", 1) for line in original.decode().splitlines())
    assert len(values["JWT_SECRET_KEY"]) == 128
    assert values["JWT_SECRET_KEY"] != values["PROXY_AUTH_SECRET"]
    assert (tmp_path / "frontend/.env.local").read_text().strip() == "PROXY_AUTH_SECRET=" + values["PROXY_AUTH_SECRET"]
    assert values["PROXY_AUTH_SECRET"] not in capsys.readouterr().out
    assert not list(tmp_path.rglob("*.db"))
    with pytest.raises(ValueError):
        configure(tmp_path)
    assert (tmp_path / "backend/.env").read_bytes() == original


@pytest.mark.asyncio
@pytest.mark.parametrize("response,expected", [({"id": "fictional-id"}, True), ({}, False)])
async def test_email_requires_acceptance_and_reuses_idempotency_key(response, expected):
    from app.services import email_service
    sender = AsyncMock(return_value=response)
    s = settings(resend_api_key="fictional", from_email="sender@example.com")
    with patch.object(email_service, "settings", s), patch("resend.Emails.send_async", sender):
        for _ in range(2):
            assert await email_service.send_status_email("candidate@example.com", "Fictional", "Invented") is expected
    assert sender.await_args_list[0] == sender.await_args_list[1]
    assert sender.await_args.args[1]["idempotency_key"].startswith("hr-email-")


@pytest.mark.asyncio
async def test_missing_email_or_failed_send_never_claims_success():
    from app.services import email_service
    with patch.object(email_service, "settings", settings()), patch("resend.Emails.send_async", AsyncMock()) as sender:
        assert not await email_service.send_status_email("candidate@example.com", "Fictional", "Invented")

        sender.assert_not_awaited()
    with patch.object(email_service, "settings", settings(resend_api_key="fictional", from_email="sender@example.com")), patch("resend.Emails.send_async", AsyncMock(side_effect=TimeoutError)):  # pragma: allowlist secret -- fictional mocked credential, never sent
        assert not await email_service.send_status_email("candidate@example.com", "Fictional", "Invented")


@pytest.mark.asyncio
@pytest.mark.parametrize("provider,host,model", [
    ("openai", "api.openai.com", "gpt-4.1-mini"),
    ("deepseek", "api.deepseek.com", "deepseek-flash"),
    ("anthropic", "api.anthropic.com", "claude-sonnet-4-6"),
])
async def test_locked_sdk_request_contract(provider, host, model):
    import json
    from openai import AsyncOpenAI
    captured = []

    def respond(request):
        captured.append(request)
        return httpx.Response(200, json={"id": "fictional", "object": "chat.completion", "created": 0,
            "model": model, "choices": [{"index": 0, "message": {"role": "assistant", "content": "{}"}, "finish_reason": "stop"}]})

    s = settings(llm_provider=provider, **{provider + "_api_key": "fictional"})

    def build(**kwargs):
        return AsyncOpenAI(**kwargs, http_client=httpx.AsyncClient(transport=httpx.MockTransport(respond)))

    with patch.object(llm_client, "_settings", s), patch.object(llm_client, "AsyncOpenAI", side_effect=build):
        await llm_client.llm_chat_completion(messages=[{"role": "user", "content": "Return JSON"}], json_mode=True)
    assert len(captured) == 1
    assert captured[0].url.host == host
    assert captured[0].url.path.endswith("/chat/completions")
    body = json.loads(captured[0].content)
    assert body["model"] == model
    assert body["max_tokens"] == 4096
    assert ("response_format" in body) == (provider != "anthropic")
    if provider == "deepseek":
        assert body["thinking"] == {"type": "disabled"}


@pytest.mark.asyncio
@pytest.mark.parametrize("status,expired,visible", [
    ("ready", False, True), ("in_progress", False, True),
    ("ready", True, False), ("completed", False, False),
    ("review_pending", False, False),
])
async def test_interview_link_only_for_authorized_active_candidate(client, seeded, status, expired, visible):
    from datetime import datetime, timedelta, timezone
    from app.models import Candidate
    from tests.conftest import db_session_factory
    async with db_session_factory() as db:
        candidate = await db.get(Candidate, seeded["candidate_id"])
        candidate.status = status
        candidate.interview_token = "fictional-private-interview-link"
        candidate.interview_link_expires_at = datetime.now(timezone.utc) + timedelta(days=-1 if expired else 1)
        await db.commit()
    url = f"/candidates/{seeded['candidate_id']}"
    response = await client.get(url, headers=seeded["headers"])
    assert response.status_code == 200
    link = response.json()["interview_link"]
    assert bool(link) is visible
    if visible:
        assert link.endswith("/interview/session/fictional-private-interview-link")
    client.cookies.clear()
    assert (await client.get(url)).status_code == 401
    other = await client.post("/auth/signup", json={"email": "other@example.com", "password": "FictionalLocalTest2026!", "name": "Other", "company_name": "Other Fictional Company"})  # pragma: allowlist secret -- fictional isolated test password
    assert other.status_code == 201
    assert (await client.get(url)).status_code == 404
