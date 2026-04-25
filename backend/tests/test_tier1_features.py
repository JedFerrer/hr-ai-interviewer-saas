"""Tier 1 features: shareable report, status emails, comparison/ranking."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select

from app.models import (
    Candidate,
    CandidateShareToken,
    Company,
    EvaluationRecord,
    Interview,
    JobPosting,
    User,
)
from app.services.share_service import _hash_token
from tests.conftest import test_session_factory


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


async def _build_candidate_with_evaluation(
    company_email: str = "test@example.com",
    *,
    auto_send: bool = True,
    candidate_email: str = "alice@candidate.com",
) -> dict[str, str]:
    """Create company/job/candidate/interview/evaluation directly via the DB.

    Returns a dict of useful IDs for the test.
    """
    async with test_session_factory() as session:
        # The signed-up user already created a company; reuse it.
        user_q = await session.execute(select(User).where(User.email == company_email))
        user = user_q.scalar_one()
        company_q = await session.execute(
            select(Company).where(Company.id == user.company_id)
        )
        company = company_q.scalar_one()

        job = JobPosting(
            company_id=company.id,
            created_by=user.id,
            title="Senior Engineer",
            description="x" * 60,
            employment_type="full_time",
            interview_config={"num_questions": 5, "style": "standard"},
            interview_link_token="job-tok-" + company.id[:8],
            auto_send_status_emails=auto_send,
        )
        session.add(job)
        await session.flush()

        cand = Candidate(
            job_posting_id=job.id,
            name="Alice Candidate",
            email=candidate_email,
            normalized_email=candidate_email.lower(),
            status="completed",
            completed_at=datetime.now(timezone.utc),
        )
        session.add(cand)
        await session.flush()

        interview = Interview(
            candidate_id=cand.id,
            job_posting_id=job.id,
            transcript=[
                {"role": "interviewer", "content": "Tell me about yourself.", "timestamp": "t1"},
                {"role": "candidate", "content": "I am a Python dev.", "timestamp": "t2"},
            ],
            status="completed",
            completed_at=datetime.now(timezone.utc),
        )
        session.add(interview)
        await session.flush()

        ev = EvaluationRecord(
            interview_id=interview.id,
            overall_score=8.4,
            skill_match=9.0,
            communication=8.0,
            problem_solving=8.5,
            cultural_fit=8.0,
            summary="Strong candidate.",
            strengths=["Python", "Clear communicator"],
            gaps=["No Kubernetes experience"],
            red_flags=[],
            recommendation="yes",
        )
        session.add(ev)
        await session.commit()

        return {
            "company_id": company.id,
            "job_id": job.id,
            "candidate_id": cand.id,
            "interview_id": interview.id,
        }


@pytest_asyncio.fixture
async def seeded(client: AsyncClient, auth_headers: dict):
    """Provide a logged-in user plus a candidate with a completed evaluation."""
    ids = await _build_candidate_with_evaluation()
    return {"headers": auth_headers, **ids}


# ---------------------------------------------------------------------------
# Feature 1 — Shareable Evaluation Report
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_share_link_returns_token_and_url(
    client: AsyncClient, seeded: dict
):
    resp = await client.post(
        f"/candidates/{seeded['candidate_id']}/share", headers=seeded["headers"]
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["token"]
    assert data["url"].endswith(f"/report/{data['token']}")
    assert data["expires_at"]
    assert data["token_id"]


@pytest.mark.asyncio
async def test_public_report_returns_evaluation(client: AsyncClient, seeded: dict):
    create = await client.post(
        f"/candidates/{seeded['candidate_id']}/share", headers=seeded["headers"]
    )
    token = create.json()["token"]

    resp = await client.get(f"/public/report/{token}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["candidate_name"] == "Alice Candidate"
    assert data["job_title"] == "Senior Engineer"
    assert data["company_name"] == "Test Corp"
    assert data["evaluation"]["overall_score"] == 8.4
    assert data["evaluation"]["scores"]["skill_match"] == 9.0
    assert "Python" in data["evaluation"]["strengths"]
    assert len(data["transcript"]) == 2
    # No HR-internal fields leak.
    assert "email" not in data
    assert "integrity_signals" not in data
    assert "resume_url" not in data
    # Search engines must not index.
    assert "noindex" in resp.headers.get("x-robots-tag", "")


@pytest.mark.asyncio
async def test_public_report_invalid_token_returns_404(client: AsyncClient):
    resp = await client.get("/public/report/totally-bogus-token-1234567890")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_public_report_expired_token_returns_404(
    client: AsyncClient, seeded: dict
):
    create = await client.post(
        f"/candidates/{seeded['candidate_id']}/share", headers=seeded["headers"]
    )
    token = create.json()["token"]

    # Force-expire the token in the DB.
    async with test_session_factory() as session:
        result = await session.execute(
            select(CandidateShareToken).where(
                CandidateShareToken.token_hash == _hash_token(token)
            )
        )
        record = result.scalar_one()
        record.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        await session.commit()

    resp = await client.get(f"/public/report/{token}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_revoked_token_returns_404(client: AsyncClient, seeded: dict):
    create = await client.post(
        f"/candidates/{seeded['candidate_id']}/share", headers=seeded["headers"]
    )
    token = create.json()["token"]
    token_id = create.json()["token_id"]

    revoke = await client.delete(
        f"/candidates/{seeded['candidate_id']}/share/{token_id}",
        headers=seeded["headers"],
    )
    assert revoke.status_code == 204

    resp = await client.get(f"/public/report/{token}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_share_token_not_visible_to_other_company(
    client: AsyncClient, seeded: dict
):
    # Sign up a second company; their auth token must not let them share Alice.
    # Clear any cookie set by the first signup so the cookie doesn't override
    # the bearer header (`_extract_token` prefers the cookie).
    client.cookies.clear()
    other = await client.post(
        "/auth/signup",
        json={
            "email": "other@example.com",
            "password": "securepass123",
            "name": "Other",
            "company_name": "Other Corp",
        },
    )
    assert other.status_code == 201
    client.cookies.clear()
    other_headers = {
        "Authorization": f"Bearer {other.json()['access_token']}",
        "X-Requested-With": "XMLHttpRequest",
    }

    resp = await client.post(
        f"/candidates/{seeded['candidate_id']}/share", headers=other_headers
    )
    assert resp.status_code == 404  # candidate not found in their tenant


@pytest.mark.asyncio
async def test_share_link_stored_hashed(client: AsyncClient, seeded: dict):
    create = await client.post(
        f"/candidates/{seeded['candidate_id']}/share", headers=seeded["headers"]
    )
    raw = create.json()["token"]

    async with test_session_factory() as session:
        result = await session.execute(select(CandidateShareToken))
        rows = list(result.scalars().all())
        assert len(rows) == 1
        # Raw token must not appear in the DB; only the hash.
        assert rows[0].token_hash != raw
        assert rows[0].token_hash == _hash_token(raw)


# ---------------------------------------------------------------------------
# Feature 2 — Candidate Status Emails
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_shortlist_sends_email_when_toggle_on(
    client: AsyncClient, seeded: dict
):
    sender = AsyncMock(return_value=True)
    with patch("app.services.email_service.send_status_email", sender):
        resp = await client.post(
            f"/candidates/{seeded['candidate_id']}/shortlist",
            headers=seeded["headers"],
        )
    assert resp.status_code == 200
    sender.assert_awaited_once()
    kwargs = sender.await_args.kwargs
    assert kwargs["candidate_email"] == "alice@candidate.com"
    assert "Congratulations" in kwargs["subject"] or "next round" in kwargs["subject"]
    # Templates must HTML-escape the company name.
    assert "Test Corp" in kwargs["body_html"]


@pytest.mark.asyncio
async def test_reject_sends_email_when_toggle_on(
    client: AsyncClient, seeded: dict
):
    sender = AsyncMock(return_value=True)
    with patch("app.services.email_service.send_status_email", sender):
        resp = await client.post(
            f"/candidates/{seeded['candidate_id']}/reject",
            headers=seeded["headers"],
        )
    assert resp.status_code == 200
    sender.assert_awaited_once()
    kwargs = sender.await_args.kwargs
    assert "application" in kwargs["subject"].lower() or "update" in kwargs["subject"].lower()


@pytest.mark.asyncio
async def test_status_email_skipped_when_toggle_off(
    client: AsyncClient, auth_headers: dict
):
    ids = await _build_candidate_with_evaluation(auto_send=False)

    sender = AsyncMock(return_value=True)
    with patch("app.services.email_service.send_status_email", sender):
        resp = await client.post(
            f"/candidates/{ids['candidate_id']}/shortlist", headers=auth_headers
        )
    assert resp.status_code == 200
    sender.assert_not_awaited()


@pytest.mark.asyncio
async def test_status_email_idempotent_on_repeat_within_window(
    client: AsyncClient, seeded: dict
):
    sender = AsyncMock(return_value=True)
    with patch("app.services.email_service.send_status_email", sender):
        await client.post(
            f"/candidates/{seeded['candidate_id']}/shortlist",
            headers=seeded["headers"],
        )
        # Second shortlist of an already-shortlisted candidate: no email.
        await client.post(
            f"/candidates/{seeded['candidate_id']}/shortlist",
            headers=seeded["headers"],
        )
    assert sender.await_count == 1


@pytest.mark.asyncio
async def test_email_templates_get_returns_defaults(
    client: AsyncClient, auth_headers: dict
):
    resp = await client.get(
        "/companies/me/email-templates", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "shortlist" in data and "reject" in data
    assert "{{candidate_name}}" in data["shortlist"]["body_html"]


@pytest.mark.asyncio
async def test_email_templates_put_persists(
    client: AsyncClient, auth_headers: dict
):
    body = {
        "shortlist": {
            "subject": "Custom subject for {{candidate_name}}",
            "body_html": "<p>Hi {{candidate_name}} — custom body.</p>",
        }
    }
    resp = await client.put(
        "/companies/me/email-templates", json=body, headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["shortlist"]["subject"].startswith("Custom subject")

    # And the GET reflects it.
    get_resp = await client.get(
        "/companies/me/email-templates", headers=auth_headers
    )
    assert get_resp.json()["shortlist"]["body_html"].startswith("<p>Hi")


@pytest.mark.asyncio
async def test_custom_template_used_when_present(
    client: AsyncClient, seeded: dict
):
    await client.put(
        "/companies/me/email-templates",
        json={
            "shortlist": {
                "subject": "CUSTOM {{candidate_name}}",
                "body_html": "<p>CUSTOM_BODY for {{job_title}}</p>",
            }
        },
        headers=seeded["headers"],
    )
    sender = AsyncMock(return_value=True)
    with patch("app.services.email_service.send_status_email", sender):
        await client.post(
            f"/candidates/{seeded['candidate_id']}/shortlist",
            headers=seeded["headers"],
        )
    kwargs = sender.await_args.kwargs
    assert kwargs["subject"] == "CUSTOM Alice Candidate"
    assert "CUSTOM_BODY" in kwargs["body_html"]
    assert "Senior Engineer" in kwargs["body_html"]


# ---------------------------------------------------------------------------
# Feature 3 — Candidate Comparison & Ranking Board
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_candidate_list_returns_subscores(
    client: AsyncClient, seeded: dict
):
    resp = await client.get(
        f"/jobs/{seeded['job_id']}/candidates", headers=seeded["headers"]
    )
    assert resp.status_code == 200
    cands = resp.json()["candidates"]
    assert len(cands) == 1
    c = cands[0]
    assert c["overall_score"] == 8.4
    assert c["skill_match"] == 9.0
    assert c["communication"] == 8.0
    assert c["problem_solving"] == 8.5
    assert c["cultural_fit"] == 8.0
    assert c["recommendation"] == "yes"


@pytest.mark.asyncio
async def test_candidate_list_sortable_by_subscore(
    client: AsyncClient, auth_headers: dict
):
    # Build two candidates with different skill_match scores.
    ids = await _build_candidate_with_evaluation(
        candidate_email="alice@candidate.com"
    )
    async with test_session_factory() as session:
        job = (await session.execute(
            select(JobPosting).where(JobPosting.id == ids["job_id"])
        )).scalar_one()
        cand2 = Candidate(
            job_posting_id=job.id,
            name="Bob",
            email="bob@candidate.com",
            normalized_email="bob@candidate.com",
            status="completed",
        )
        session.add(cand2)
        await session.flush()
        iv2 = Interview(
            candidate_id=cand2.id,
            job_posting_id=job.id,
            transcript=[],
            status="completed",
        )
        session.add(iv2)
        await session.flush()
        session.add(EvaluationRecord(
            interview_id=iv2.id,
            overall_score=5.0,
            skill_match=2.0,
            communication=6.0,
            problem_solving=5.0,
            cultural_fit=6.0,
            recommendation="no",
        ))
        await session.commit()

    resp = await client.get(
        f"/jobs/{ids['job_id']}/candidates?sort=skill_match&order=desc",
        headers=auth_headers,
    )
    cands = resp.json()["candidates"]
    assert [c["name"] for c in cands] == ["Alice Candidate", "Bob"]

    resp_asc = await client.get(
        f"/jobs/{ids['job_id']}/candidates?sort=skill_match&order=asc",
        headers=auth_headers,
    )
    assert [c["name"] for c in resp_asc.json()["candidates"]] == ["Bob", "Alice Candidate"]
