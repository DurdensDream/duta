from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class TriageDecision(str, Enum):
    """The system's complete action space.

    ADR-0004: there is no REJECT and there must never be one. A CI test asserts this enum's
    exact membership; adding a negative action means deliberately breaking that test and
    superseding the ADR in the same PR.
    """

    ADVANCE = "ADVANCE"
    NEEDS_INFO = "NEEDS_INFO"
    DUPLICATE = "DUPLICATE"
    REVIEW = "REVIEW"


# ADR-0005: the canonical model IS the allowlist. EEO/PII fields have no place to live here;
# translation drops everything not in this model, so new sources fail closed.
class CanonicalApplication(BaseModel):
    source: str
    source_ref: str
    candidate_name: str | None = None
    email: str | None = None
    phone: str | None = None
    location_raw: str | None = None
    work_auth: str | None = None
    resume_text: str | None = None
    position_title: str | None = None
    position_code: str | None = None
    submitted_at: datetime | None = None


class CanonicalCandidate(BaseModel):
    """CRM candidate, post-translation. Like CanonicalApplication, this model IS the allowlist:
    TalentBase's inline EEO columns (ADR-0005) have no field to land in."""

    source: str
    source_ref: str
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    city: str | None = None
    state: str | None = None
    current_title: str | None = None
    current_employer: str | None = None
    skills_txt: str | None = None
    work_auth: str | None = None


class CanonicalRequisition(BaseModel):
    external_code: str
    title: str
    seniority: str | None = None
    city: str | None = None
    remote_policy: str | None = None
    skills_txt: str | None = None
    description: str | None = None
    status: str = "open"


class TriageResult(BaseModel):
    decision: TriageDecision
    requisition_code: str | None = None
    duplicate_of: str | None = None
    confidence: float | None = None
    evidence: dict = {}
    rationale: str = ""
    engine: str
    cost_usd: float | None = None
    latency_ms: int | None = None


# Runtime tripwire vocabulary (ADR-0005): if any of these ever appear as keys in an outbound
# model payload, the request is refused and the application degrades to REVIEW.
EEO_FIELD_DENYLIST = frozenset({
    "gender", "ethnicity", "date_of_birth", "dob", "birth_date", "age",
    "veteran_status", "disability_status", "marital_status", "race", "religion",
})
