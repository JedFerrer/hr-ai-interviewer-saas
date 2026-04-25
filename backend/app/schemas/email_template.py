"""Email-template request/response schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

TemplateKind = Literal["shortlist", "reject", "status_correction"]


# Default templates rendered when a company has not customized the kind yet.
DEFAULT_TEMPLATES: dict[str, dict[str, str]] = {
    "shortlist": {
        "subject": "Congratulations — you're moving to the next round at {{company_name}}",
        "body_html": (
            "<p>Hi {{candidate_name}},</p>"
            "<p>Thank you for completing the screening interview for the "
            "<strong>{{job_title}}</strong> role at <strong>{{company_name}}</strong>.</p>"
            "<p>We were impressed with your interview and would like to move you "
            "forward to the next stage of our hiring process. A member of our team "
            "will be in touch shortly with the next steps.</p>"
            "<p>Congratulations, and talk soon!</p>"
            "<p>— The {{company_name}} hiring team</p>"
        ),
    },
    "reject": {
        "subject": "Update on your application for {{job_title}} at {{company_name}}",
        "body_html": (
            "<p>Hi {{candidate_name}},</p>"
            "<p>Thank you for taking the time to interview for the "
            "<strong>{{job_title}}</strong> role at <strong>{{company_name}}</strong>. "
            "We received many strong applications and after careful review, we won't "
            "be moving forward with your application at this time.</p>"
            "<p>We genuinely appreciate your interest and the effort you put into the "
            "process, and we wish you all the best in your search.</p>"
            "<p>— The {{company_name}} hiring team</p>"
        ),
    },
    "status_correction": {
        "subject": "Correction regarding your application for {{job_title}} at {{company_name}}",
        "body_html": (
            "<p>Hi {{candidate_name}},</p>"
            "<p>You may have recently received an email from us regarding your "
            "application for the <strong>{{job_title}}</strong> role at "
            "<strong>{{company_name}}</strong>. That message was sent in error, "
            "and we sincerely apologise for any confusion it caused.</p>"
            "<p>A member of our team will follow up shortly with the correct "
            "status of your application. Thank you for your patience.</p>"
            "<p>— The {{company_name}} hiring team</p>"
        ),
    },
}


class TemplateBody(BaseModel):
    subject: str = Field(min_length=1, max_length=255)
    body_html: str = Field(min_length=1, max_length=20000)


class EmailTemplatesResponse(BaseModel):
    shortlist: TemplateBody
    reject: TemplateBody
    status_correction: TemplateBody


class EmailTemplatesUpdateRequest(BaseModel):
    shortlist: TemplateBody | None = None
    reject: TemplateBody | None = None
    status_correction: TemplateBody | None = None
