"""Per-company customizable email templates for candidate status notifications."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, generate_uuid


# Supported template kinds. Kept as plain strings (no enum) per repo conventions.
TEMPLATE_KIND_SHORTLIST = "shortlist"
TEMPLATE_KIND_REJECT = "reject"
# A correction email is sent when HR previously notified the candidate of one
# decision (e.g. "rejected") and needs to walk it back. Kept as a separate
# kind so the copy can apologise / clarify rather than re-using shortlist or
# reject wording verbatim.
TEMPLATE_KIND_STATUS_CORRECTION = "status_correction"
ALLOWED_TEMPLATE_KINDS = {
    TEMPLATE_KIND_SHORTLIST,
    TEMPLATE_KIND_REJECT,
    TEMPLATE_KIND_STATUS_CORRECTION,
}


class EmailTemplate(Base):
    __tablename__ = "email_templates"
    __table_args__ = (
        UniqueConstraint("company_id", "kind", name="uq_email_template_company_kind"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    company_id: Mapped[str] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body_html: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
