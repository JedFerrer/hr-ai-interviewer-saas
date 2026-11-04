"""Invite service unit tests + team / auth endpoint integration tests."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy import select

from app.models.user import User
from app.models.user_invite import UserInvite
from app.services import invite_service
from tests.conftest import db_session_factory


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _signup(client: AsyncClient, email: str = "owner@example.com"):
    resp = await client.post(
        "/auth/signup",
        json={
            "email": email,
            "password": "ownerpassword123",
            "name": "Owner",
            "company_name": "Acme Inc",
        },
    )
    assert resp.status_code in (200, 201)
    return resp.json()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Requested-With": "XMLHttpRequest"}


# ---------------------------------------------------------------------------
# Service-level unit tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_invite_persists_hashed_token_only(client: AsyncClient):
    """Raw token must never be persisted; only its SHA-256 digest."""
    body = await _signup(client)
    company_id = body["company"]["id"]

    async with db_session_factory() as db:
        owner = (
            await db.execute(select(User).where(User.company_id == company_id))
        ).scalar_one()

        invite, raw_token = await invite_service.create_invite(
            db, company_id=company_id, inviter=owner, email="new@example.com"
        )

    assert raw_token  # non-empty
    assert invite.token_hash != raw_token
    assert len(invite.token_hash) == 64  # SHA-256 hex


@pytest.mark.asyncio
async def test_create_invite_rejects_duplicate_outstanding(client: AsyncClient):
    body = await _signup(client)
    company_id = body["company"]["id"]

    async with db_session_factory() as db:
        owner = (
            await db.execute(select(User).where(User.company_id == company_id))
        ).scalar_one()
        await invite_service.create_invite(
            db, company_id=company_id, inviter=owner, email="dup@example.com"
        )

        with pytest.raises(Exception) as exc_info:
            await invite_service.create_invite(
                db, company_id=company_id, inviter=owner, email="dup@example.com"
            )
        assert "outstanding invite" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_create_invite_rejects_existing_user_email(client: AsyncClient):
    body = await _signup(client)
    company_id = body["company"]["id"]

    async with db_session_factory() as db:
        owner = (
            await db.execute(select(User).where(User.company_id == company_id))
        ).scalar_one()
        with pytest.raises(Exception) as exc_info:
            await invite_service.create_invite(
                db, company_id=company_id, inviter=owner, email=owner.email
            )
        assert "already exists" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_get_invite_by_token_hides_expired(client: AsyncClient):
    body = await _signup(client)
    company_id = body["company"]["id"]

    async with db_session_factory() as db:
        owner = (
            await db.execute(select(User).where(User.company_id == company_id))
        ).scalar_one()
        invite, raw_token = await invite_service.create_invite(
            db, company_id=company_id, inviter=owner, email="exp@example.com"
        )
        # Force-expire it.
        invite.expires_at = invite.expires_at - timedelta(days=10)
        await db.commit()

        with pytest.raises(Exception) as exc_info:
            await invite_service.get_invite_by_token(db, raw_token)
        assert "invalid or expired" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_accept_invite_creates_user_in_same_company(client: AsyncClient):
    body = await _signup(client)
    company_id = body["company"]["id"]

    async with db_session_factory() as db:
        owner = (
            await db.execute(select(User).where(User.company_id == company_id))
        ).scalar_one()
        invite, raw_token = await invite_service.create_invite(
            db, company_id=company_id, inviter=owner, email="newhire@example.com"
        )

    async with db_session_factory() as db:
        user, company, jwt = await invite_service.accept_invite(
            db, raw_token=raw_token, name="New Hire", password="strongpass123"
        )

    assert user.company_id == company_id
    assert user.email == "newhire@example.com"
    assert user.role == "recruiter"
    assert jwt  # non-empty

    # Invite is now consumed.
    async with db_session_factory() as db:
        consumed = (
            await db.execute(select(UserInvite).where(UserInvite.id == invite.id))
        ).scalar_one()
        assert consumed.accepted_at is not None


@pytest.mark.asyncio
async def test_accept_invite_rejects_reuse(client: AsyncClient):
    body = await _signup(client)
    company_id = body["company"]["id"]

    async with db_session_factory() as db:
        owner = (
            await db.execute(select(User).where(User.company_id == company_id))
        ).scalar_one()
        _, raw_token = await invite_service.create_invite(
            db, company_id=company_id, inviter=owner, email="once@example.com"
        )

    async with db_session_factory() as db:
        await invite_service.accept_invite(
            db, raw_token=raw_token, name="First", password="firstpass123"
        )
    async with db_session_factory() as db:
        with pytest.raises(Exception) as exc_info:
            await invite_service.accept_invite(
                db, raw_token=raw_token, name="Second", password="secondpass123"
            )
        assert "invalid or expired" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_revoke_invite_blocks_subsequent_accept(client: AsyncClient):
    body = await _signup(client)
    company_id = body["company"]["id"]

    async with db_session_factory() as db:
        owner = (
            await db.execute(select(User).where(User.company_id == company_id))
        ).scalar_one()
        invite, raw_token = await invite_service.create_invite(
            db, company_id=company_id, inviter=owner, email="revoke@example.com"
        )
        await invite_service.revoke_invite(
            db, invite.id, company_id, revoker=owner
        )

    async with db_session_factory() as db:
        with pytest.raises(HTTPException, match="Invalid or expired"):
            await invite_service.accept_invite(
                db, raw_token=raw_token, name="X", password="strongpass123"
            )


# ---------------------------------------------------------------------------
# Router-level integration tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_team_invite_endpoints_require_auth(client: AsyncClient):
    resp = await client.get("/team/invites")
    assert resp.status_code in (401, 403)
    resp = await client.post("/team/invites", json={"email": "x@y.com"})
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_team_create_and_list_and_revoke_invite(client: AsyncClient):
    body = await _signup(client)
    headers = _auth(body["access_token"])

    # Create
    resp = await client.post(
        "/team/invites", json={"email": "teammate@example.com"}, headers=headers
    )
    assert resp.status_code == 201, resp.text
    payload = resp.json()
    assert payload["email"] == "teammate@example.com"
    invite_id = payload["id"]
    # Raw token MUST NOT be in the API response.
    assert "token" not in payload
    assert "token_hash" not in payload
    assert "raw_token" not in payload

    # List
    resp = await client.get("/team/invites", headers=headers)
    assert resp.status_code == 200
    invites = resp.json()["invites"]
    assert len(invites) == 1
    assert invites[0]["id"] == invite_id

    # Revoke
    resp = await client.delete(f"/team/invites/{invite_id}", headers=headers)
    assert resp.status_code == 204

    # Now listed as 0 outstanding.
    resp = await client.get("/team/invites", headers=headers)
    assert resp.json()["invites"] == []


@pytest.mark.asyncio
async def test_team_company_isolation(client: AsyncClient):
    """Owner of company A cannot revoke an invite belonging to company B."""
    a = await _signup(client, email="a@example.com")
    headers_a = _auth(a["access_token"])
    # signup sets the session cookie; clear so subsequent calls fall back
    # to the explicit Bearer header (cookie wins over header otherwise).
    client.cookies.clear()

    b = await client.post(
        "/auth/signup",
        json={
            "email": "b@example.com",
            "password": "ownerpassword123",
            "name": "B Owner",
            "company_name": "B Corp",
        },
    )
    headers_b = _auth(b.json()["access_token"])
    client.cookies.clear()

    resp = await client.post(
        "/team/invites", json={"email": "guest@example.com"}, headers=headers_b
    )
    assert resp.status_code == 201, resp.text
    invite_id = resp.json()["id"]
    client.cookies.clear()

    # A tries to revoke B's invite \u2192 404 (not 403, to avoid existence leakage)
    resp = await client.delete(f"/team/invites/{invite_id}", headers=headers_a)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_public_preview_and_accept_flow(client: AsyncClient):
    body = await _signup(client)
    headers = _auth(body["access_token"])
    company_id = body["company"]["id"]

    # Owner creates the invite via the API \u2014 we then read the raw token from
    # the DB to simulate the email link.
    resp = await client.post(
        "/team/invites", json={"email": "newjoiner@example.com"}, headers=headers
    )
    assert resp.status_code == 201

    # Pull the raw token by re-creating one programmatically (the API doesn't
    # expose it). For a true end-to-end test we mint a fresh invite via the
    # service so we have the raw token in hand.
    async with db_session_factory() as db:
        # Revoke the API one to keep state clean.
        invite_to_clear = (
            await db.execute(
                select(UserInvite).where(UserInvite.email == "newjoiner@example.com")
            )
        ).scalar_one()
        invite_to_clear.revoked_at = invite_to_clear.expires_at  # any non-null
        await db.commit()

        owner = (
            await db.execute(select(User).where(User.company_id == company_id))
        ).scalar_one()
        _, raw_token = await invite_service.create_invite(
            db,
            company_id=company_id,
            inviter=owner,
            email="newjoiner2@example.com",
        )

    # Public preview.
    resp = await client.get(f"/auth/invite/{raw_token}")
    assert resp.status_code == 200, resp.text
    preview = resp.json()
    assert preview["email"] == "newjoiner2@example.com"
    assert preview["company_name"] == "Acme Inc"

    # Public accept.
    resp = await client.post(
        f"/auth/invite/{raw_token}/accept",
        json={"name": "New Joiner", "password": "joinerpass123"},
    )
    assert resp.status_code == 201, resp.text
    auth_payload = resp.json()
    assert auth_payload["user"]["email"] == "newjoiner2@example.com"
    assert auth_payload["company"]["id"] == company_id
    assert auth_payload["access_token"]


@pytest.mark.asyncio
async def test_public_preview_404_for_unknown_token(client: AsyncClient):
    resp = await client.get("/auth/invite/totally-bogus-token")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_accept_invite_password_validation(client: AsyncClient):
    body = await _signup(client)
    headers = _auth(body["access_token"])
    company_id = body["company"]["id"]

    async with db_session_factory() as db:
        owner = (
            await db.execute(select(User).where(User.company_id == company_id))
        ).scalar_one()
        _, raw_token = await invite_service.create_invite(
            db, company_id=company_id, inviter=owner, email="weak@example.com"
        )
    _ = headers  # silence linters

    # Too short \u2192 422
    resp = await client.post(
        f"/auth/invite/{raw_token}/accept",
        json={"name": "Weak", "password": "short"},
    )
    assert resp.status_code == 422
    # Letters-only \u2192 422 (no digits)
    resp = await client.post(
        f"/auth/invite/{raw_token}/accept",
        json={"name": "Weak", "password": "alllettersnoNumbers"},
    )
    assert resp.status_code == 422


@pytest.fixture(autouse=True)
def mock_invite_delivery():
    with patch("app.services.invite_service.send_invite_email", new=AsyncMock(return_value=True)):
        yield
