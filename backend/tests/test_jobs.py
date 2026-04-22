"""Job CRUD endpoint tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


JOB_PAYLOAD = {
    "title": "Senior Python Developer",
    "description": "We need a Python expert to build APIs and work with our FastAPI backend infrastructure team on scalable systems.",
    "department": "Engineering",
    "location": "Remote",
    "employment_type": "full_time",
    "required_skills": ["Python", "FastAPI", "PostgreSQL"],
    "custom_questions": [{"question": "What is your experience with async Python?"}],
}


@pytest.mark.asyncio
async def test_create_job(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/jobs", json=JOB_PAYLOAD, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["job"]["title"] == JOB_PAYLOAD["title"]
    assert "interview_link" in data


@pytest.mark.asyncio
async def test_create_job_unauthenticated(client: AsyncClient):
    resp = await client.post("/jobs", json=JOB_PAYLOAD)
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_jobs(client: AsyncClient, auth_headers: dict):
    await client.post("/jobs", json=JOB_PAYLOAD, headers=auth_headers)
    resp = await client.get("/jobs", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert len(data["jobs"]) >= 1


@pytest.mark.asyncio
async def test_get_job(client: AsyncClient, auth_headers: dict):
    create_resp = await client.post("/jobs", json=JOB_PAYLOAD, headers=auth_headers)
    job_id = create_resp.json()["job"]["id"]

    resp = await client.get(f"/jobs/{job_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["job"]["id"] == job_id


@pytest.mark.asyncio
async def test_update_job(client: AsyncClient, auth_headers: dict):
    create_resp = await client.post("/jobs", json=JOB_PAYLOAD, headers=auth_headers)
    job_id = create_resp.json()["job"]["id"]

    resp = await client.put(
        f"/jobs/{job_id}",
        json={"title": "Lead Python Developer"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Lead Python Developer"


@pytest.mark.asyncio
async def test_delete_job(client: AsyncClient, auth_headers: dict):
    create_resp = await client.post("/jobs", json=JOB_PAYLOAD, headers=auth_headers)
    job_id = create_resp.json()["job"]["id"]

    resp = await client.delete(f"/jobs/{job_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert "archived" in resp.json()["message"].lower()

    # Should still exist but with archived status
    get_resp = await client.get(f"/jobs/{job_id}", headers=auth_headers)
    assert get_resp.json()["job"]["status"] == "archived"


@pytest.mark.asyncio
async def test_get_nonexistent_job(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/jobs/nonexistent-id", headers=auth_headers)
    assert resp.status_code == 404
