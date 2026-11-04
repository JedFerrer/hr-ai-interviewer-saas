"""Real ASGI routes/services and committed SQLite state; only providers are doubled."""
import asyncio
import copy
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import httpx
import pytest
import pytest_asyncio
from openai import APIConnectionError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import get_db
from app.main import app
from app.models import Base, Candidate, Company, Interview, JobPosting
from app.models.evaluation import EvaluationRecord
from app.services import interview_service, llm_client


class ProviderDouble:
    def __init__(self):
        self.calls = []
        self.fail = None
        self.pause = None
        self.entered = asyncio.Event()
        self.release = asyncio.Event()

    async def __call__(self, *, operation, **kwargs):
        self.calls.append(operation)
        if operation == self.pause:
            self.entered.set()
            await asyncio.wait_for(self.release.wait(), 5)
        if operation == self.fail:
            raise APIConnectionError(message="private-provider-payload", request=httpx.Request("POST", "https://example.test"))
        content = {
            "opening": "Describe a database improvement?",
            "answer": json.dumps({"quality": "detailed", "follow_up": "NEXT"}),
            "reply": "Explain your testing approach?",
            "evaluate": json.dumps({"overall_score": 8, "summary": "Fictional evaluation", "recommendation": "maybe"}),
        }[operation]
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
                               usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5)), "gpt-4.1-mini"


@pytest_asyncio.fixture
async def harness(tmp_path, monkeypatch):
    path = tmp_path / "owned-interview.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{path}")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with factory() as db:
        company = Company(name="Fictional Integrity Company")
        db.add(company)
        await db.flush()
        job = JobPosting(company_id=company.id, title="Engineer", description="Invented database work")
        db.add(job)
        await db.flush()
        candidate = Candidate(job_posting_id=job.id, name="Avery Example", email="avery@example.com",
                              status="ready", interview_token="fictional-integrity-token",
                              interview_link_expires_at=datetime.now(timezone.utc) + timedelta(days=1))
        db.add(candidate)
        await db.flush()
        interview = Interview(candidate_id=candidate.id, job_posting_id=job.id,
                              planned_questions=[{"category": "technical", "question": q} for q in
                                                 ["Describe a database improvement?", "Explain your testing approach?"]])
        db.add(interview)
        await db.commit()
        ids = candidate.id, interview.id

    async def dependency():
        async with factory() as session:
            yield session

    provider = ProviderDouble()
    previous = app.dependency_overrides[get_db]
    app.dependency_overrides[get_db] = dependency
    monkeypatch.setattr(interview_service, "async_session_factory", factory)
    monkeypatch.setattr(interview_service, "get_async_openai_client", lambda: None)
    monkeypatch.setattr(interview_service, "llm_chat_completion", provider)
    monkeypatch.setattr(llm_client, "llm_chat_completion", provider)

    async def snapshot():
        # Every observation uses a new session, never the request identity map.
        async with factory() as db:
            candidate = await db.get(Candidate, ids[0])
            interview = await db.get(Interview, ids[1])
            evaluations = (await db.scalars(select(EvaluationRecord))).all()
            return copy.deepcopy({
                "transcript": interview.transcript, "index": interview.current_question_index,
                "signals": interview.integrity_signals, "status": interview.status,
                "candidate_status": candidate.status, "completed": interview.completed_at,
                "candidate_completed": candidate.completed_at, "score": candidate.overall_score,
                "tokens": (interview.total_prompt_tokens, interview.total_completion_tokens),
                "cost": interview.cost_usd, "evaluations": [e.id for e in evaluations],
            })

    async def drain():
        tasks = list(interview_service._BACKGROUND_TASKS)
        if tasks:
            await asyncio.wait_for(asyncio.gather(*tasks), 5)

    try:
        yield provider, snapshot, drain
    finally:
        provider.release.set()
        await drain()
        app.dependency_overrides[get_db] = previous
        await engine.dispose()
        path.unlink()
        assert not path.exists()


START = "/interview/session/fictional-integrity-token/start"
ANSWERS = ["I added a composite index and measured query latency before deployment.",
           "Our regression suite verified transaction isolation with independent connections and fixtures."]


async def request(path, payload=None):
    # Separate client and dependency-created database session for each request.
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        return await client.post(path, json=payload)


async def answer(index=0):
    return await request("/interview/message", {"interview_token": "fictional-integrity-token",
        "message": ANSWERS[index], "integrity_signals": {"was_pasted": True, "time_to_answer_seconds": 20}})


@pytest.mark.asyncio
@pytest.mark.parametrize("turn", [0, 1])
async def test_failed_turn_rolls_back_committed_state_and_retries(harness, turn):
    provider, snapshot, drain = harness
    assert (await request(START)).status_code == 200
    if turn:
        assert (await answer()).status_code == 200
    before = await snapshot()
    provider.fail = "reply"  # After answer assessment and in-memory question advancement.
    response = await answer(turn)
    assert response.status_code == 503
    assert "private-provider-payload" not in response.text
    assert await snapshot() == before
    provider.fail = None
    assert (await answer(turn)).status_code == 200
    await drain()
    after = await snapshot()
    assert after["index"] == turn + 1
    assert [m["content"] for m in after["transcript"] if m["role"] == "candidate"] == ANSWERS[:turn + 1]
    assert after["signals"]["paste_count"] == turn + 1
    assert len(after["signals"]["timings"]) == turn + 1
    assert len(after["evaluations"]) == turn
    assert (after["status"], after["candidate_status"]) == (("completed", "completed") if turn else ("in_progress", "in_progress"))
    assert bool(after["completed"]) == bool(after["candidate_completed"]) == bool(turn)


@pytest.mark.asyncio
async def test_overlapping_starts_have_one_opening(harness):
    provider, snapshot, _ = harness
    provider.pause = "opening"
    first = asyncio.create_task(request(START))
    try:
        await asyncio.wait_for(provider.entered.wait(), 5)
        assert (await request(START)).status_code == 409
        assert (await snapshot())["transcript"] == []
    finally:
        provider.release.set()
        response = await first
    assert response.status_code == 200
    resumed = await request(START)
    assert resumed.status_code == 200
    assert resumed.json() == response.json()
    state = await snapshot()
    assert len(state["transcript"]) == 1
    assert state["index"] == 0 and state["evaluations"] == []
    assert provider.calls == ["opening"]


@pytest.mark.asyncio
@pytest.mark.parametrize("turn", [0, 1])
async def test_overlapping_answers_and_completion_are_single_transition(harness, turn):
    provider, snapshot, drain = harness
    assert (await request(START)).status_code == 200
    if turn:
        assert (await answer()).status_code == 200
    before = await snapshot()
    provider.pause = "reply"
    first = asyncio.create_task(answer(turn))
    try:
        await asyncio.wait_for(provider.entered.wait(), 5)
        assert (await answer(turn)).status_code == 409
        assert (await request(START)).status_code == 409
        assert await snapshot() == before
    finally:
        provider.release.set()
        response = await first
    assert response.status_code == 200
    await drain()
    after = await snapshot()
    assert after["index"] == turn + 1
    assert len(after["transcript"]) == len(before["transcript"]) + 2
    assert [m["question_index"] for m in after["transcript"] if m["role"] == "candidate"] == list(range(turn + 1))
    assert [m["content"] for m in after["transcript"] if m["role"] == "candidate"] == ANSWERS[:turn + 1]
    assert len(after["evaluations"]) == provider.calls.count("evaluate") == turn
    if turn:
        assert (await answer(turn)).status_code == 400
        assert (await request(START)).status_code == 400
        assert await snapshot() == after
    else:
        assert (await answer(1)).status_code == 200
        await drain()
        final = await snapshot()
        assert final["index"] == 2 and len(final["transcript"]) == 5
        assert len(final["evaluations"]) == provider.calls.count("evaluate") == 1
