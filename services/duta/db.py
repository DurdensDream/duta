import hashlib
import json

import psycopg
from psycopg.rows import dict_row

from . import config
from .models import CanonicalApplication, CanonicalCandidate, CanonicalRequisition, TriageResult
from .normalize import norm_city, norm_email, norm_name, norm_phone


def connect():
    return psycopg.connect(config.APP_DB_DSN, row_factory=dict_row)


def payload_hash(canon: CanonicalApplication) -> str:
    blob = canon.model_dump_json(exclude_none=False)
    return hashlib.sha256(blob.encode()).hexdigest()[:32]


def upsert_application(conn, canon: CanonicalApplication) -> tuple[int, bool]:
    """Insert if unseen; replays are no-ops by the (source, source_ref) constraint.

    Returns (application_id, newly_inserted).
    """
    h = payload_hash(canon)
    row = conn.execute(
        """
        INSERT INTO duta.applications
            (source, source_ref, candidate_name, email, phone, location_raw, work_auth,
             resume_text, position_title, position_code, submitted_at, payload_hash,
             email_norm, phone_norm, name_norm)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (source, source_ref) DO NOTHING
        RETURNING id
        """,
        (canon.source, canon.source_ref, canon.candidate_name, canon.email, canon.phone,
         canon.location_raw, canon.work_auth, canon.resume_text, canon.position_title,
         canon.position_code, canon.submitted_at, h,
         norm_email(canon.email), norm_phone(canon.phone), norm_name(canon.candidate_name)),
    ).fetchone()
    if row:
        return row["id"], True
    row = conn.execute(
        "SELECT id FROM duta.applications WHERE source = %s AND source_ref = %s",
        (canon.source, canon.source_ref),
    ).fetchone()
    return row["id"], False


def candidate_row_hash(canon: CanonicalCandidate) -> str:
    return hashlib.sha256(canon.model_dump_json().encode()).hexdigest()[:32]


def upsert_candidate(conn, canon: CanonicalCandidate) -> bool:
    """Sync a CRM candidate into the canonical store. Returns True if inserted or changed."""
    h = candidate_row_hash(canon)
    row = conn.execute(
        """
        INSERT INTO duta.candidates
            (source, source_ref, full_name, email, phone, city, state, current_title,
             current_employer, skills_txt, work_auth, email_norm, phone_norm, name_norm,
             city_norm, row_hash)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (source, source_ref) DO UPDATE SET
            full_name = EXCLUDED.full_name, email = EXCLUDED.email, phone = EXCLUDED.phone,
            city = EXCLUDED.city, state = EXCLUDED.state, current_title = EXCLUDED.current_title,
            current_employer = EXCLUDED.current_employer, skills_txt = EXCLUDED.skills_txt,
            work_auth = EXCLUDED.work_auth, email_norm = EXCLUDED.email_norm,
            phone_norm = EXCLUDED.phone_norm, name_norm = EXCLUDED.name_norm,
            city_norm = EXCLUDED.city_norm, row_hash = EXCLUDED.row_hash, synced_at = now()
        WHERE duta.candidates.row_hash <> EXCLUDED.row_hash
        RETURNING id
        """,
        (canon.source, canon.source_ref, canon.full_name, canon.email, canon.phone, canon.city,
         canon.state, canon.current_title, canon.current_employer, canon.skills_txt,
         canon.work_auth, norm_email(canon.email), norm_phone(canon.phone),
         norm_name(canon.full_name), norm_city(canon.city), h),
    ).fetchone()
    return row is not None


def upsert_requisition(conn, canon: CanonicalRequisition) -> bool:
    """Sync a requisition; hash-compared because TalentBase's updated_at is unreliable here."""
    h = hashlib.sha256(canon.model_dump_json().encode()).hexdigest()[:32]
    row = conn.execute(
        """
        INSERT INTO duta.requisitions
            (external_code, title, seniority, city, remote_policy, skills_txt, description,
             status, row_hash)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (external_code) DO UPDATE SET
            title = EXCLUDED.title, seniority = EXCLUDED.seniority, city = EXCLUDED.city,
            remote_policy = EXCLUDED.remote_policy, skills_txt = EXCLUDED.skills_txt,
            description = EXCLUDED.description, status = EXCLUDED.status,
            row_hash = EXCLUDED.row_hash, synced_at = now()
        WHERE duta.requisitions.row_hash <> EXCLUDED.row_hash
        RETURNING id
        """,
        (canon.external_code, canon.title, canon.seniority, canon.city, canon.remote_policy,
         canon.skills_txt, canon.description, canon.status, h),
    ).fetchone()
    return row is not None


def get_watermark(conn, source: str) -> str | None:
    row = conn.execute("SELECT watermark FROM duta.sync_state WHERE source = %s", (source,)).fetchone()
    return row["watermark"] if row else None


def set_watermark(conn, source: str, watermark: str):
    conn.execute(
        """
        INSERT INTO duta.sync_state (source, watermark, updated_at) VALUES (%s, %s, now())
        ON CONFLICT (source) DO UPDATE SET watermark = EXCLUDED.watermark, updated_at = now()
        """,
        (source, watermark),
    )


def save_triage(conn, application_id: int, result: TriageResult) -> bool:
    """Persist a triage decision; idempotent per application. Returns False if already triaged."""
    row = conn.execute(
        """
        INSERT INTO duta.triage_results
            (application_id, decision, requisition_code, duplicate_of, confidence,
             evidence, rationale, engine, cost_usd, latency_ms)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (application_id) DO NOTHING
        RETURNING id
        """,
        (application_id, result.decision.value, result.requisition_code, result.duplicate_of,
         result.confidence, json.dumps(result.evidence), result.rationale, result.engine,
         result.cost_usd, result.latency_ms),
    ).fetchone()
    if not row:
        return False
    if result.decision.value == "REVIEW":
        conn.execute(
            """
            INSERT INTO duta.review_queue (application_id, reason)
            VALUES (%s, %s) ON CONFLICT (application_id) DO NOTHING
            """,
            (application_id, result.rationale or "escalated"),
        )
    return True


def audit(conn, actor: str, action: str, subject: str | None = None, detail: dict | None = None):
    conn.execute(
        "INSERT INTO duta.audit_log (actor, action, subject, detail) VALUES (%s, %s, %s, %s)",
        (actor, action, subject, json.dumps(detail or {})),
    )
