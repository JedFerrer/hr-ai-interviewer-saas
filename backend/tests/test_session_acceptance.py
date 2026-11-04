"""Deterministic cookie/session boundaries for ordinary-mode acceptance."""
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.models.user import User
from app.utils.security import COOKIE_NAME, decode_access_token
from tests.conftest import db_session_factory, get_test_settings


@pytest.mark.asyncio
async def test_cookie_mutation_requires_csrf_even_with_valid_session(client, auth_headers):
    assert (await client.get('/auth/me')).status_code == 200
    assert (await client.post('/auth/refresh')).status_code == 403
    assert (await client.post('/auth/logout')).status_code == 403
    assert (await client.get('/auth/me')).status_code == 200


@pytest.mark.asyncio
async def test_cookie_refresh_and_logout_clear_browser_session(client, auth_headers):
    csrf = {'X-Requested-With': 'XMLHttpRequest'}
    response = await client.post('/auth/refresh', headers=csrf)
    assert response.status_code == 200
    assert response.json()['expires_in'] > 0
    cookie = response.headers['set-cookie'].lower()
    assert 'httponly' in cookie and 'samesite=lax' in cookie
    assert (await client.get('/auth/me')).status_code == 200
    assert (await client.post('/auth/logout', headers=csrf)).status_code == 204
    assert (await client.get('/auth/me')).status_code == 401
    assert (await client.post('/auth/logout', headers=csrf)).status_code == 204


@pytest.mark.asyncio
async def test_expired_session_cannot_be_refreshed(client, auth_headers):
    payload = decode_access_token(auth_headers['Authorization'].split(' ', 1)[1])
    payload['exp'] = datetime.now(timezone.utc) - timedelta(seconds=5)
    settings = get_test_settings()
    expired = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    client.cookies.clear()
    client.cookies.set(COOKIE_NAME, expired)
    assert (await client.get('/auth/me')).status_code == 401
    response = await client.post('/auth/refresh', headers={'X-Requested-With': 'XMLHttpRequest'})
    assert response.status_code == 401
    assert 'set-cookie' not in response.headers


@pytest.mark.asyncio
async def test_password_change_revocation_also_blocks_refresh(client, auth_headers):
    payload = decode_access_token(auth_headers['Authorization'].split(' ', 1)[1])
    async with db_session_factory() as db:
        user = await db.get(User, payload['sub'])
        user.password_changed_at = datetime.now(timezone.utc) + timedelta(seconds=2)
        await db.commit()
    assert (await client.get('/auth/me')).status_code == 401
    assert (await client.post('/auth/refresh', headers={'X-Requested-With': 'XMLHttpRequest'})).status_code == 401
