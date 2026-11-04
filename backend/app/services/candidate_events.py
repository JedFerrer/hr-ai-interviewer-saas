"""Pub/sub event payload helpers for candidate updates.

Centralizing the shape here means publishers (background pipeline, manual
HR action endpoints) and the SSE endpoint share a single contract — and the
frontend type only needs to track this one schema.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.models.candidate import Candidate
from app.utils.pubsub import job_channel, publish_safe


CANDIDATE_UPDATED = "candidate_updated"


def build_candidate_updated_event(
    candidate: Candidate,
    *,
    actor_user_id: str | None = None,
    actor_name: str | None = None,
) -> dict:
    """Build a single, stable ``candidate_updated`` event payload.

    ``actor_user_id``/``actor_name`` identify the human who triggered the
    change. Background-pipeline events leave both as ``None`` and are
    rendered as ``"system"`` to the frontend. The frontend uses
    ``actor_user_id`` to suppress no-op self-updates after an optimistic
    UI patch (avoids flicker).
    """
    return {
        "type": CANDIDATE_UPDATED,
        "candidate_id": candidate.id,
        "job_id": candidate.job_posting_id,
        "status": candidate.status,
        "name": candidate.name,
        "actor_user_id": actor_user_id,
        "actor_name": actor_name,
        "ts": datetime.now(timezone.utc).isoformat(),
    }


async def publish_candidate_updated(
    candidate: Candidate,
    *,
    actor_user_id: str | None = None,
    actor_name: str | None = None,
) -> None:
    """Convenience: build the event and publish on the candidate's job channel."""
    event = build_candidate_updated_event(
        candidate,
        actor_user_id=actor_user_id,
        actor_name=actor_name,
    )
    await publish_safe(job_channel(candidate.job_posting_id), event)
