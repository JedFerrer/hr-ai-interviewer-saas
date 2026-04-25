"""Per-company customizable email templates for status notifications.

Storage is keyed by (company_id, kind). When a company hasn't configured a
template yet, the built-in default from `schemas.email_template.DEFAULT_TEMPLATES`
is returned.

Rendering uses a tiny, intentionally restricted variable substitution
(`{{candidate_name}}`, `{{job_title}}`, `{{company_name}}`) — no Jinja, no
arbitrary expressions, no template injection.
"""

from __future__ import annotations

import html
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email_template import ALLOWED_TEMPLATE_KINDS, EmailTemplate
from app.schemas.email_template import DEFAULT_TEMPLATES, TemplateBody


_ALLOWED_VARS = {"candidate_name", "job_title", "company_name"}
_VAR_PATTERN = re.compile(r"\{\{\s*([a-zA-Z_]+)\s*\}\}")


def _render(template: str, context: dict[str, str]) -> str:
    """Replace `{{var}}` tokens with HTML-escaped values from `context`.

    Unknown variables are left untouched (visible in the email) rather than
    silently dropped, so authors notice typos.
    """

    def repl(match: re.Match[str]) -> str:
        name = match.group(1)
        if name in _ALLOWED_VARS and name in context:
            return html.escape(context[name])
        return match.group(0)

    return _VAR_PATTERN.sub(repl, template)


async def get_templates_for_company(
    db: AsyncSession, company_id: str
) -> dict[str, TemplateBody]:
    """Return all templates for a company, falling back to defaults per kind."""
    result = await db.execute(
        select(EmailTemplate).where(EmailTemplate.company_id == company_id)
    )
    overrides = {row.kind: row for row in result.scalars().all()}

    out: dict[str, TemplateBody] = {}
    for kind in ALLOWED_TEMPLATE_KINDS:
        if kind in overrides:
            row = overrides[kind]
            out[kind] = TemplateBody(subject=row.subject, body_html=row.body_html)
        else:
            d = DEFAULT_TEMPLATES[kind]
            out[kind] = TemplateBody(subject=d["subject"], body_html=d["body_html"])
    return out


async def upsert_template(
    db: AsyncSession, company_id: str, kind: str, body: TemplateBody
) -> EmailTemplate:
    if kind not in ALLOWED_TEMPLATE_KINDS:
        raise ValueError(f"Unsupported template kind: {kind}")

    result = await db.execute(
        select(EmailTemplate).where(
            EmailTemplate.company_id == company_id,
            EmailTemplate.kind == kind,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.subject = body.subject
        existing.body_html = body.body_html
        await db.commit()
        await db.refresh(existing)
        return existing

    record = EmailTemplate(
        company_id=company_id,
        kind=kind,
        subject=body.subject,
        body_html=body.body_html,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def render_template(
    db: AsyncSession,
    company_id: str,
    kind: str,
    *,
    candidate_name: str,
    job_title: str,
    company_name: str,
) -> tuple[str, str]:
    """Resolve a template (custom or default) and render it. Returns (subject, html)."""
    templates = await get_templates_for_company(db, company_id)
    body = templates.get(kind)
    if body is None:
        d = DEFAULT_TEMPLATES[kind]
        body = TemplateBody(subject=d["subject"], body_html=d["body_html"])

    ctx = {
        "candidate_name": candidate_name or "there",
        "job_title": job_title,
        "company_name": company_name,
    }
    return _render(body.subject, ctx), _render(body.body_html, ctx)
