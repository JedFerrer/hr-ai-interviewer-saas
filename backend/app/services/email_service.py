"""Email service using Resend SDK."""

from __future__ import annotations

import html
import logging
import hashlib
import json

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def send_resend(payload: dict) -> bool:
    """Return API acceptance, not receipt. Same payload retries deduplicate for 24h."""
    import resend
    if settings.portfolio_demo:
        raise RuntimeError("Live email forbidden in portfolio demo")
    if not settings.resend_api_key or not settings.from_email:
        return False
    resend.api_key = settings.resend_api_key
    resend.api_url = "https://api.resend.com"
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    response = await resend.Emails.send_async(payload, {"idempotency_key": "hr-email-" + digest})
    return isinstance(response, dict) and bool(response.get("id"))


async def send_interview_invite(
    candidate_email: str,
    candidate_name: str,
    job_title: str,
    company_name: str,
    interview_link: str,
) -> bool:
    """Send interview invitation email to a candidate."""
    if settings.portfolio_demo:
        from app.demo.adapters import capture
        return capture("interview", candidate_email, f"Interview: {job_title}", f"Synthetic invitation for {candidate_name} at {company_name}", interview_link)
    if not settings.resend_api_key or not settings.from_email:
        logger.warning("RESEND_API_KEY or FROM_EMAIL missing; invitation delivery disabled")
        return False


    safe_name = html.escape(candidate_name)
    safe_title = html.escape(job_title)
    safe_company = html.escape(company_name)

    try:
        accepted = await send_resend({
            "from": settings.from_email,
            "to": [candidate_email],
            "subject": f"Interview Invitation: {safe_title} at {safe_company}",
            "html": f"""
                <h2>Hi {safe_name},</h2>
                <p>You've been invited to complete a screening interview for the
                <strong>{safe_title}</strong> position at <strong>{safe_company}</strong>.</p>
                <p><a href="{interview_link}"
                   style="background:#2563eb;color:white;padding:12px 24px;
                          text-decoration:none;border-radius:6px;display:inline-block;">
                   Start Interview</a></p>
                <p>The interview takes about 15-20 minutes and is conducted by an AI assistant.</p>
                <p>Good luck!</p>
            """,
        })
        return accepted
    except Exception:
        logger.exception("Failed to send interview invite")
        return False


async def send_completion_notification(
    hr_email: str,
    candidate_name: str,
    job_title: str,
    candidate_id: str,
) -> bool:
    """Notify HR user that a candidate completed their interview."""
    if settings.portfolio_demo:
        from app.demo.adapters import capture
        return capture("completion", hr_email, "Interview completed", f"Synthetic interview completed by {candidate_name}")
    if not settings.resend_api_key or not settings.from_email:
        logger.warning("RESEND_API_KEY or FROM_EMAIL missing; completion delivery disabled")
        return False


    safe_name = html.escape(candidate_name)
    safe_title = html.escape(job_title)
    dashboard_link = f"{settings.app_url}/dashboard"

    try:
        accepted = await send_resend({
            "from": settings.from_email,
            "to": [hr_email],
            "subject": f"Interview Completed: {safe_name} for {safe_title}",
            "html": f"""
                <h2>New Interview Completed</h2>
                <p><strong>{safe_name}</strong> has completed their screening interview
                for <strong>{safe_title}</strong>.</p>
                <p><a href="{dashboard_link}"
                   style="background:#2563eb;color:white;padding:12px 24px;
                          text-decoration:none;border-radius:6px;display:inline-block;">
                   View Evaluation</a></p>
            """,
        })
        return accepted
    except Exception:
        logger.exception("Failed to send completion notification")
        return False


async def send_status_email(
    candidate_email: str,
    subject: str,
    body_html: str,
) -> bool:
    """Send a pre-rendered candidate-status email (shortlist / reject).

    Subject and body are produced by `email_template_service.render_template`,
    which already HTML-escapes user-controlled values. We pass them through
    verbatim here.
    """
    if settings.portfolio_demo:
        from app.demo.adapters import capture
        return capture("status", candidate_email, subject, body_html)
    if not settings.resend_api_key or not settings.from_email:
        logger.warning("RESEND_API_KEY or FROM_EMAIL missing; status delivery disabled")
        return False


    try:
        accepted = await send_resend({
            "from": settings.from_email,
            "to": [candidate_email],
            "subject": subject,
            "html": body_html,
        })
        return accepted
    except Exception:
        logger.exception("Failed to send status email")
        return False
