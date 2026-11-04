"""Team management endpoints: list members, manage invites."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException

from app.database import get_db
from app.models.user import User
from app.schemas.team import (
    InviteCreateRequest,
    InviteListResponse,
    InviteResponse,
    TeamMemberResponse,
    TeamMembersResponse,
)
from app.services import invite_service
from app.utils.security import csrf_protect, get_current_user, require_admin

router = APIRouter(prefix="/team", tags=["team"], dependencies=[Depends(csrf_protect)])


@router.get("/members", response_model=TeamMembersResponse)
async def list_team_members(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List active users in the current company."""
    result = await db.execute(
        select(User)
        .where(User.company_id == user.company_id)
        .order_by(User.created_at.asc())
    )
    members = result.scalars().all()
    return TeamMembersResponse(
        members=[TeamMemberResponse.model_validate(m) for m in members]
    )


@router.get("/invites", response_model=InviteListResponse)
async def list_invites(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    """List outstanding (not accepted, not revoked) invites."""
    invites = await invite_service.list_invites(db, user.company_id)
    return InviteListResponse(
        invites=[InviteResponse.model_validate(i) for i in invites]
    )


@router.post("/invites", response_model=InviteResponse, status_code=201)
async def create_invite(
    body: InviteCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Create a pending invite and email the link to the invitee."""
    invite, raw_token = await invite_service.create_invite(
        db,
        company_id=user.company_id,
        inviter=user,
        email=body.email,
    )
    # Best-effort send. We never expose the raw token in the API response \u2014
    # only the email recipient should ever see it.
    sent = await invite_service.send_invite_email(
        invitee_email=invite.email,
        inviter_name=user.name,
        company_name=user.company.name if user.company else "Your team",
        raw_token=raw_token,
    )
    if not sent:
        await invite_service.revoke_invite(db, invite.id, user.company_id, revoker=user)
        raise HTTPException(status_code=503, detail="Invitation email was not delivered. Configure email and retry.")
    return InviteResponse.model_validate(invite)


@router.delete("/invites/{invite_id}", status_code=204)
async def revoke_invite(
    invite_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Revoke an outstanding invite. Idempotent."""
    await invite_service.revoke_invite(
        db, invite_id, user.company_id, revoker=user
    )
    return None
