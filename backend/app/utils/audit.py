"""Structured audit logging.

Centralizes "who did what" events so they can be filtered, shipped to a SIEM,
or persisted to a dedicated audit table later without changing call sites.
"""

from __future__ import annotations

import logging
from typing import Any

# Dedicated logger name lets ops route audit events to a separate sink.
_audit_logger = logging.getLogger("audit")


def audit(event: str, **fields: Any) -> None:
    """Emit a structured audit event.

    Example:
        audit("user.login", user_id=user.id, company_id=user.company_id)
    """
    # `audit_fields` is consumed by the AuditFormatter installed in main.py.
    _audit_logger.info(event, extra={"audit": True, "audit_fields": fields})
