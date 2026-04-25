"""Share-link management for candidate evaluation reports (authenticated)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.user import User
from app.schemas.share import ShareTokenCreateResponse
from app.services import share_service
from app.utils.security import csrf_protect, get_current_user

router = APIRouter(tags=["share"], dependencies=[Depends(csrf_protect)])


@router.post(
    "/candidates/{candidate_id}/share",
    response_model=ShareTokenCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_share_link(
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a time-limited shareable URL for the candidate's evaluation report.

    The raw token is returned exactly once. Store it securely on the client —
    only the SHA-256 hash is persisted server-side.
    """
    record, raw_token = await share_service.create_share_token(db, candidate_id, user)
    settings = get_settings()
    url = f"{settings.app_url.rstrip('/')}/report/{raw_token}"
    return ShareTokenCreateResponse(
        token=raw_token,
        url=url,
        expires_at=record.expires_at,
        token_id=record.id,
    )


@router.delete(
    "/candidates/{candidate_id}/share/{token_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def revoke_share_link(
    candidate_id: str,
    token_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Revoke a previously issued share link."""
    await share_service.revoke_share_token(db, candidate_id, token_id, user)
    return None
