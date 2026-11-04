"""Check the metric contract used by the dashboard acceptance fixes."""
from datetime import datetime, timezone

import pytest

from app.models.candidate import Candidate
from tests.conftest import db_session_factory
from tests.test_tier1_features import seeded as seeded


@pytest.mark.asyncio
async def test_dashboard_recent_decisions_and_invitation_denominator(client, seeded):
    response = await client.get('/analytics/overview', headers=seeded['headers'])
    assert response.status_code == 200
    initial = response.json()
    assert initial['kpis']['completed_awaiting_decision'] == 1
    assert initial['action_needed']['awaiting_decision']['count'] == 0
    assert initial['kpis']['completion_rate'] is None

    async with db_session_factory() as db:
        candidate = await db.get(Candidate, seeded['candidate_id'])
        candidate.invite_sent_at = datetime.now(timezone.utc)
        db.add(Candidate(job_posting_id=seeded['job_id'], name='Uninvited Example',
                         email='uninvited@example.com', normalized_email='uninvited@example.com',
                         status='review_pending'))
        await db.commit()
    result = (await client.get('/analytics/overview', headers=seeded['headers'])).json()
    assert result['kpis']['applications'] == 2
    assert result['funnel']['invited'] == 1
    assert result['funnel']['completed'] == 1
    assert result['kpis']['completion_rate'] == 1.0
