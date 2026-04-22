"""Auth endpoint tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_signup_success(client: AsyncClient):
    resp = await client.post("/auth/signup", json={
        "email": "user@example.com",
        "password": "securepass123",
        "name": "Jane Doe",
        "company_name": "Acme Inc",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["user"]["email"] == "user@example.com"
    assert data["user"]["name"] == "Jane Doe"
    assert data["company"]["name"] == "Acme Inc"
    assert "access_token" in data


@pytest.mark.asyncio
async def test_signup_duplicate_email(client: AsyncClient):
    payload = {
        "email": "dupe@example.com",
        "password": "securepass123",
        "name": "User",
        "company_name": "Corp",
    }
    await client.post("/auth/signup", json=payload)
    resp = await client.post("/auth/signup", json=payload)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_signup_short_password(client: AsyncClient):
    resp = await client.post("/auth/signup", json={
        "email": "short@example.com",
        "password": "abc",
        "name": "User",
        "company_name": "Corp",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_signup_invalid_email(client: AsyncClient):
    resp = await client.post("/auth/signup", json={
        "email": "not-an-email",
        "password": "securepass123",
        "name": "User",
        "company_name": "Corp",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    await client.post("/auth/signup", json={
        "email": "login@example.com",
        "password": "securepass123",
        "name": "User",
        "company_name": "Corp",
    })
    resp = await client.post("/auth/login", json={
        "email": "login@example.com",
        "password": "securepass123",
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post("/auth/signup", json={
        "email": "wrong@example.com",
        "password": "securepass123",
        "name": "User",
        "company_name": "Corp",
    })
    resp = await client.post("/auth/login", json={
        "email": "wrong@example.com",
        "password": "wrongpassword",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    resp = await client.post("/auth/login", json={
        "email": "nobody@example.com",
        "password": "whatever",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_authenticated(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["user"]["email"] == "test@example.com"
    assert data["company"]["name"] == "Test Corp"


@pytest.mark.asyncio
async def test_me_no_token(client: AsyncClient):
    resp = await client.get("/auth/me")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_me_invalid_token(client: AsyncClient):
    resp = await client.get("/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
    assert resp.status_code == 401
