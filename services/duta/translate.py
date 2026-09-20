"""Translation layer: every source record passes through here, and ONLY the fields this module
explicitly maps survive (ADR-0005 — allowlist, fails closed). No source dict is ever forwarded."""

from datetime import datetime

from .models import CanonicalApplication, CanonicalCandidate, CanonicalRequisition


def parse_vendor_ts(raw: str | None) -> datetime | None:
    """Kestrel spells timestamps three ways ('Z', '+00:00', '-05:00'). Parse, don't compare strings."""
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def from_talentbase_candidate(row: dict) -> CanonicalCandidate:
    """TalentBase candidate row -> canonical. The SQL already selects only allowlisted columns
    (see connectors/talentbase.py); this mapping is the second, fail-closed layer — a row dict
    containing EEO keys loses them here because there is nowhere for them to go (ADR-0005)."""
    return CanonicalCandidate(
        source="talentbase",
        source_ref="TB-CAND-{:06d}".format(row["candidate_id"]),
        full_name=row.get("full_name"),
        email=row.get("email") or None,
        phone=row.get("phone") or None,
        city=row.get("city_raw") or None,
        state=row.get("state") or None,
        current_title=row.get("current_title"),
        current_employer=row.get("current_employer"),
        skills_txt=row.get("skills_txt"),
        work_auth=row.get("work_auth") or None,
    )


def from_talentbase_requisition(row: dict) -> CanonicalRequisition:
    return CanonicalRequisition(
        external_code=row["external_code"],
        title=row["title"],
        seniority=row.get("seniority"),
        city=row.get("city"),
        remote_policy=row.get("remote_policy"),
        skills_txt=row.get("skills_txt"),
        description=row.get("description"),
        status=row.get("status") or "open",
    )


def from_jobwire(mapped: dict, source_ref: str, submitted_at: datetime | None) -> CanonicalApplication:
    """JobWire CSV row (already header-mapped by the connector) -> canonical."""
    return CanonicalApplication(
        source="jobwire",
        source_ref=source_ref,
        candidate_name=mapped.get("name") or None,
        email=(mapped.get("email") or None),
        phone=(mapped.get("phone") or None),
        location_raw=(mapped.get("location") or None),
        work_auth=None,
        resume_text=mapped.get("resume") or None,
        position_title=None,
        position_code=(mapped.get("position_code") or None),
        submitted_at=submitted_at,
    )


def from_kestrel(rec: dict) -> CanonicalApplication:
    cand = rec.get("candidate") or {}
    pos = rec.get("position") or {}
    return CanonicalApplication(
        source="kestrel",
        source_ref=rec["applicationId"],
        candidate_name=cand.get("name"),
        email=(cand.get("emailAddress") or None),
        phone=(cand.get("phoneNumber") or None),
        location_raw=(cand.get("location") or None),
        work_auth=None,  # kestrel doesn't carry it; NEEDS_INFO logic reads the resume text
        resume_text=rec.get("resumeText"),
        position_title=pos.get("title"),
        position_code=pos.get("jobCode"),
        submitted_at=parse_vendor_ts(rec.get("submittedAt")),
    )
