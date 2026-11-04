"""Company model."""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.job_posting import JobPosting


class Company(Base, TimestampMixin):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    logo_url: Mapped[str | None] = mapped_column(String(500))

    # Relationships
    users: Mapped[list["User"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    job_postings: Mapped[list["JobPosting"]] = relationship(back_populates="company", cascade="all, delete-orphan")
