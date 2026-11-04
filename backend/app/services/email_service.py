"""Email service using Resend SDK."""

from __future__ import annotations

import html
import logging

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


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
    if not settings.resend_api_key:
        logger.warning("RESEND_API_KEY not set, skipping email to %s", candidate_email)
        return False

    import resend

    resend.api_key = settings.resend_api_key

    safe_name = html.escape(candidate_name)
    safe_title = html.escape(job_title)
    safe_company = html.escape(company_name)

    try:
        resend.Emails.send({
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
        return True
    except Exception:
        logger.exception("Failed to send interview invite to %s", candidate_email)
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
    if not settings.resend_api_key:
        logger.warning("RESEND_API_KEY not set, skipping notification to %s", hr_email)
        return False

    import resend

    resend.api_key = settings.resend_api_key

    safe_name = html.escape(candidate_name)
    safe_title = html.escape(job_title)
    dashboard_link = f"{settings.app_url}/candidates/{candidate_id}"

    try:
        resend.Emails.send({
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
        return True
    except Exception:
        logger.exception("Failed to send completion notification to %s", hr_email)
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
    if not settings.resend_api_key:
        logger.warning("RESEND_API_KEY not set, skipping status email to %s", candidate_email)
        return False

    import resend

    resend.api_key = settings.resend_api_key

    try:
        resend.Emails.send({
            "from": settings.from_email,
            "to": [candidate_email],
            "subject": subject,
            "html": body_html,
        })
        return True
    except Exception:
        logger.exception("Failed to send status email to %s", candidate_email)
        return False
