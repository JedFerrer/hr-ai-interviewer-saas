"""Per-company email-template management."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.email_template import (
    EmailTemplatesResponse,
    EmailTemplatesUpdateRequest,
    TemplateBody,
)
from app.services import email_template_service
from app.utils.security import csrf_protect, get_current_user

router = APIRouter(
    prefix="/companies/me/email-templates",
    tags=["email-templates"],
    dependencies=[Depends(csrf_protect)],
)


@router.get("", response_model=EmailTemplatesResponse)
async def get_templates(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return current shortlist + reject templates (defaults if not customized)."""
    templates = await email_template_service.get_templates_for_company(db, user.company_id)
    return EmailTemplatesResponse(
        shortlist=templates["shortlist"],
        reject=templates["reject"],
    )


@router.put("", response_model=EmailTemplatesResponse)
async def update_templates(
    body: EmailTemplatesUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Upsert one or both templates for the current company."""
    if body.shortlist is not None:
        await email_template_service.upsert_template(
            db, user.company_id, "shortlist", body.shortlist
        )
    if body.reject is not None:
        await email_template_service.upsert_template(
            db, user.company_id, "reject", body.reject
        )
    templates = await email_template_service.get_templates_for_company(db, user.company_id)
    return EmailTemplatesResponse(
        shortlist=templates["shortlist"],
        reject=templates["reject"],
    )
