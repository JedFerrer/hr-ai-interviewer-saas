"""SSE candidate-update stream endpoint tests."""

from __future__ import annotations

import asyncio
import json

import pytest
from httpx import AsyncClient

from app.routers.jobs import _candidate_event_stream
from app.utils.pubsub import InMemoryPubSub, get_pubsub, job_channel, set_pubsub


JOB_PAYLOAD = {
    "title": "Senior Python Developer",
    "description": "We need a Python expert to build APIs and work with our FastAPI backend infrastructure team on scalable systems.",
    "department": "Engineering",
    "location": "Remote",
    "employment_type": "full_time",
    "required_skills": ["Python"],
    "custom_questions": [],
}


@pytest.fixture(autouse=True)
def _fresh_pubsub():
    set_pubsub(InMemoryPubSub())
    yield
    set_pubsub(None)


@pytest.mark.asyncio
async def test_stream_requires_auth(client: AsyncClient):
    resp = await client.get("/jobs/some-id/stream")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_stream_404_for_unknown_job(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/jobs/does-not-exist/stream", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_event_stream_emits_connected_then_published_event():
    """Drive the generator directly: avoids the complexity of true SSE over httpx."""
    job_id = "job-xyz"
    gen = _candidate_event_stream(job_id)

    # First frame is the one-shot 'connected' event.
    first = await asyncio.wait_for(gen.__anext__(), timeout=1.0)
    assert b"event: connected" in first

    # Publish to the matching channel; the generator should yield it.
    await get_pubsub().publish(
        job_channel(job_id),
        {"type": "candidate_updated", "candidate_id": "c1", "status": "ready"},
    )
    second = await asyncio.wait_for(gen.__anext__(), timeout=1.0)
    assert b"event: candidate_updated" in second
    # Body is the JSON payload after the SSE 'data: ' prefix.
    data_line = next(
        line for line in second.splitlines() if line.startswith(b"data: ")
    )
    payload = json.loads(data_line[len(b"data: "):])
    assert payload["candidate_id"] == "c1"
    assert payload["status"] == "ready"

    await gen.aclose()


@pytest.mark.asyncio
async def test_event_stream_unsubscribes_on_close():
    """Ensure the registry is cleaned up when the generator is closed."""
    job_id = "job-cleanup"
    bus = get_pubsub()

    gen = _candidate_event_stream(job_id)
    await asyncio.wait_for(gen.__anext__(), timeout=1.0)  # consume connected
    assert job_channel(job_id) in bus._channels  # type: ignore[attr-defined]

    await gen.aclose()
    assert job_channel(job_id) not in bus._channels  # type: ignore[attr-defined]
