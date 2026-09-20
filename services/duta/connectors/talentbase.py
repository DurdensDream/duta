"""TalentBase (legacy CRM) connector — read-only replica access, per Ellen's grant.

ADR-0001: watermark pulls where updated_at is trustworthy (candidates), full-scan + row-hash
where it isn't (requisitions). deep=True forces a full candidate scan, which also picks up the
~20% of candidate rows with NULL updated_at that watermarks structurally miss.

ADR-0005: the allowlist starts AT THE SQL. The EEO columns (gender, ethnicity, date_of_birth,
veteran_status, disability_status, marital_status) are never selected — they don't enter this
process's memory, let alone the canonical store or a model payload.
"""

import psycopg
from psycopg.rows import dict_row

from .. import config

CANDIDATE_COLUMNS = ("candidate_id, full_name, email, phone, city_raw, state, current_title, "
                     "current_employer, skills_txt, work_auth, updated_at")
REQUISITION_COLUMNS = ("req_id, external_code, title, bu, seniority, city, remote_policy, "
                       "skills_txt, description, status")


def connect_crm():
    return psycopg.connect(config.CRM_DB_DSN, row_factory=dict_row)


def fetch_requisitions(crm) -> list[dict]:
    """Full scan every pass: updated_at is unreliable on this table (often NULL). The upsert
    layer hash-compares, so an unchanged row costs one comparison, not a write."""
    return crm.execute(
        "SELECT {} FROM talentbase.tb_requisitions WHERE bu = 'Technology'".format(REQUISITION_COLUMNS)
    ).fetchall()


def fetch_candidates(crm, watermark: str | None, deep: bool = False) -> list[dict]:
    if deep or watermark is None:
        return crm.execute(
            "SELECT {} FROM talentbase.tb_candidates".format(CANDIDATE_COLUMNS)
        ).fetchall()
    return crm.execute(
        "SELECT {} FROM talentbase.tb_candidates WHERE updated_at > %s ORDER BY updated_at"
        .format(CANDIDATE_COLUMNS),
        (watermark,),
    ).fetchall()
