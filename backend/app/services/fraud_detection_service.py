"""Resume fraud / identity-mismatch detection.

Runs after resume parsing but before screening decisions. Compares the
identity declared on the application form (name + email) against the
identity embedded in the resume itself, and detects re-used resume content
across different applicants.

Pure functions only — DB access is isolated to `find_resume_hash_collision`
which takes an explicit session. No LLM calls; no network.

Three signals, three risk levels:
    - name_mismatch:           form name not similar to resume name
    - email_mismatch:          form email not equal to resume email (normalized)
    - resume_content_reused:   another candidate already submitted this exact file
                               under a different normalized email

Risk:
    - "none":  no signals
    - "warn":  one weak signal (name OR email alone)        -> force HR review,
                                                              annotate reason
    - "block": strong signal (name+email together, or hash  -> force HR review,
              collision with different email)                 skip auto-invite

We never auto-reject — HR sees the flag, reads the rationale, and decides.
"""

from __future__ import annotations

import hashlib
import logging
import os
import string
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


RiskLevel = Literal["none", "warn", "block"]
SignalKind = Literal["name_mismatch", "email_mismatch", "resume_content_reused"]


# Tokens stripped from names before comparison so titles/suffixes don't
# poison the similarity score (e.g. "Dr. John Smith Jr." vs "John Smith").
_NAME_NOISE_TOKENS: frozenset[str] = frozenset(
    {
        "mr", "mrs", "ms", "miss", "mx", "dr", "prof", "sir", "madam",
        "jr", "sr", "ii", "iii", "iv", "phd", "md", "esq", "cpa",
    }
)

# Default similarity threshold for name matching. Configurable via env so
# operators can tune for false-positive rate without redeploying code.
def _name_threshold() -> float:
    raw = os.getenv("FRAUD_NAME_SIMILARITY_THRESHOLD", "0.6")
    try:
        v = float(raw)
    except ValueError:
        return 0.6
    # Clamp to a sane range — anything outside [0.3, 0.95] is almost
    # certainly a misconfiguration.
    return max(0.3, min(0.95, v))


@dataclass(frozen=True)
class FraudSignal:
    kind: SignalKind
    detail: str

    def to_dict(self) -> dict:
        return {"kind": self.kind, "detail": self.detail}


@dataclass(frozen=True)
class FraudCheckResult:
    risk_level: RiskLevel
    signals: list[FraudSignal] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "risk_level": self.risk_level,
            "signals": [s.to_dict() for s in self.signals],
        }

    @property
    def has_signals(self) -> bool:
        return bool(self.signals)


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def compute_resume_hash(content: bytes) -> str:
    """SHA-256 of the raw resume bytes. Stable across re-uploads of the
    identical file, so we can detect the same resume submitted by a
    different applicant.
    """
    return hashlib.sha256(content).hexdigest()


def normalize_name(name: str | None) -> str:
    """Lowercase, strip punctuation, drop noise tokens (titles, suffixes)
    and single-letter initials. Returns the cleaned space-joined string.
    """
    if not name:
        return ""
    # Remove punctuation entirely (including periods after initials).
    cleaned = name.translate(str.maketrans("", "", string.punctuation))
    tokens = [t.lower() for t in cleaned.split() if t]
    tokens = [
        t for t in tokens
        if t not in _NAME_NOISE_TOKENS and len(t) > 1
    ]
    return " ".join(tokens)


def name_similarity(form_name: str | None, resume_name: str | None) -> float:
    """Return a 0..1 similarity score combining token-set overlap and
    sequence ratio. Returns 0.0 if either side is empty after normalization.
    """
    a = normalize_name(form_name)
    b = normalize_name(resume_name)
    if not a or not b:
        return 0.0

    # Token-set Jaccard handles re-ordering ("Smith John" vs "John Smith")
    # and extra middle names robustly.
    a_tokens = set(a.split())
    b_tokens = set(b.split())
    intersection = len(a_tokens & b_tokens)
    union = len(a_tokens | b_tokens)
    jaccard = intersection / union if union else 0.0

    # Sequence ratio catches typos / minor spelling differences.
    seq = SequenceMatcher(None, a, b).ratio()

    return max(jaccard, seq)


def _normalize_email(email: str | None) -> str:
    if not email:
        return ""
    e = email.strip().lower()
    local, _, domain = e.partition("@")
    if not domain:
        return e
    local = local.split("+", 1)[0]
    return f"{local}@{domain}"


def _extract_emails_from_resume(resume_data: dict) -> list[str]:
    """Resume parser populates `email` but defensive code: also scan the
    summary for any embedded address. We compare the form email against
    *all* emails the resume contains so a resume with multiple emails
    (e.g. work + personal) doesn't false-positive.
    """
    emails: list[str] = []
    primary = resume_data.get("email")
    if isinstance(primary, str) and primary.strip():
        emails.append(primary)
    return [_normalize_email(e) for e in emails if e]


# ---------------------------------------------------------------------------
# DB lookup (separate so unit tests can avoid a session)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CollisionMatch:
    candidate_id: str
    name: str | None
    email: str | None

    def display(self) -> str:
        """Human-readable label for use in signal detail messages."""
        parts: list[str] = []
        if self.name:
            parts.append(self.name)
        if self.email:
            parts.append(f"({self.email})")
        return " ".join(parts) if parts else "another applicant"


async def find_resume_hash_collision(
    db: AsyncSession,
    *,
    content_hash: str,
    current_candidate_id: str,
    normalized_email: str | None,
) -> CollisionMatch | None:
    """Return identity info for any *other* applicant who submitted the same
    resume bytes under a *different* normalized email, or None.

    Same email + same hash is a legitimate re-application (e.g. to a second
    job posting) and is intentionally ignored.
    """
    # Local import keeps this module decoupled from the model layer for
    # the pure-function tests.
    from app.models.candidate import Candidate

    stmt = select(Candidate.id, Candidate.name, Candidate.normalized_email).where(
        Candidate.resume_content_hash == content_hash,
        Candidate.id != current_candidate_id,
    )
    result = await db.execute(stmt)
    for row_id, row_name, row_email in result.all():
        if (row_email or "") != (normalized_email or ""):
            return CollisionMatch(
                candidate_id=row_id,
                name=row_name,
                email=row_email,
            )
    return None


# ---------------------------------------------------------------------------
# Top-level check
# ---------------------------------------------------------------------------


def _classify(signals: list[FraudSignal]) -> RiskLevel:
    if not signals:
        return "none"
    kinds = {s.kind for s in signals}
    # Hash-collision is always strong evidence of resume re-use.
    if "resume_content_reused" in kinds:
        return "block"
    # Name + email together is hard to explain away.
    if "name_mismatch" in kinds and "email_mismatch" in kinds:
        return "block"
    return "warn"


async def detect_fraud_signals(
    *,
    db: AsyncSession,
    candidate_id: str,
    form_name: str,
    form_email: str,
    resume_data: dict,
    content_hash: str | None,
) -> FraudCheckResult:
    """Run all fraud checks and return the combined result.

    Errors in any individual check are logged and skipped — a fraud check
    must never break the apply pipeline.
    """
    signals: list[FraudSignal] = []

    # ---- Name check ----------------------------------------------------
    try:
        resume_name = resume_data.get("name") if isinstance(resume_data, dict) else None
        if resume_name:  # Skip silently if the resume had no extractable name.
            sim = name_similarity(form_name, resume_name)
            if sim < _name_threshold():
                signals.append(
                    FraudSignal(
                        kind="name_mismatch",
                        detail=(
                            f"Form name '{form_name}' does not match resume name "
                            f"'{resume_name}' (similarity {sim:.2f} < "
                            f"{_name_threshold():.2f})."
                        ),
                    )
                )
    except Exception:  # noqa: BLE001 — defensive: never block the pipeline
        logger.exception("Name fraud check failed for candidate %s", candidate_id)

    # ---- Email check ---------------------------------------------------
    try:
        form_norm = _normalize_email(form_email)
        resume_emails = _extract_emails_from_resume(resume_data or {})
        # Only flag if the resume *has* an email and none of them match.
        if form_norm and resume_emails and form_norm not in resume_emails:
            signals.append(
                FraudSignal(
                    kind="email_mismatch",
                    detail=(
                        f"Form email '{form_email}' does not match any email on "
                        f"the resume ({', '.join(resume_emails)})."
                    ),
                )
            )
    except Exception:  # noqa: BLE001
        logger.exception("Email fraud check failed for candidate %s", candidate_id)

    # ---- Hash collision ------------------------------------------------
    if content_hash:
        try:
            collision = await find_resume_hash_collision(
                db,
                content_hash=content_hash,
                current_candidate_id=candidate_id,
                normalized_email=_normalize_email(form_email),
            )
            if collision:
                signals.append(
                    FraudSignal(
                        kind="resume_content_reused",
                        detail=(
                            f"Identical resume file previously submitted by "
                            f"{collision.display()} under a different email."
                        ),
                    )
                )
        except Exception:  # noqa: BLE001
            logger.exception(
                "Resume hash collision check failed for candidate %s", candidate_id
            )

    return FraudCheckResult(risk_level=_classify(signals), signals=signals)


__all__ = [
    "FraudCheckResult",
    "FraudSignal",
    "RiskLevel",
    "compute_resume_hash",
    "detect_fraud_signals",
    "find_resume_hash_collision",
    "name_similarity",
    "normalize_name",
]
