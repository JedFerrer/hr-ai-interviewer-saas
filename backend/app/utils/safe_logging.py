"""Process-wide logging boundary: no URLs, headers, provider payloads or tracebacks.
Install before importing routers/providers. Request logs use route templates.
"""

import logging
import re

_UUID = re.compile(r"^[0-9a-fA-F-]{36}$")


def install_safe_logging():
    previous = logging.getLogRecordFactory()
    if getattr(previous, "_hr_safe", False):
        return

    def factory(*args, **kwargs):
        record = previous(*args, **kwargs)
        exception_type = record.exc_info[0].__name__ if record.exc_info else "none"
        if record.name == "uvicorn.access":
            status = (
                record.args[-1]
                if isinstance(record.args, tuple) and record.args
                else "unknown"
            )
            record.msg = "HTTP access status=%s"
            record.args = (status if isinstance(status, int) else "unknown",)
        elif record.name == "audit":
            # Event names are static code constants; fields filtered by formatter.
            pass
        elif record.name != "app.main":
            record.msg = "event logger=%s function=%s level=%s exception=%s"
            record.args = (
                record.name,
                record.funcName,
                record.levelname,
                exception_type,
            )
        record.exc_info = None
        record.exc_text = None
        record.stack_info = None
        return record

    factory._hr_safe = True
    logging.setLogRecordFactory(factory)


def safe_audit_fields(fields):
    return {
        key: value
        for key, value in fields.items()
        if key.endswith("_id") and isinstance(value, str) and _UUID.fullmatch(value)
    }
