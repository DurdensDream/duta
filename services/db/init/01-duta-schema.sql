-- Pilot-owned schema. Everything the pilot produces lives here; TalentBase is never written
-- (discovery memo §5.2). Idempotency is enforced at the schema level, not in application code.

CREATE SCHEMA IF NOT EXISTS duta;

CREATE TABLE duta.applications (
    id             SERIAL PRIMARY KEY,
    source         TEXT NOT NULL,             -- kestrel | jobwire | talentbase
    source_ref     TEXT NOT NULL,             -- KES-000123 / JW-20260724-0007 / TB-APP-000001
    candidate_name TEXT,
    email          TEXT,
    phone          TEXT,
    location_raw   TEXT,
    work_auth      TEXT,
    resume_text    TEXT,
    position_title TEXT,
    position_code  TEXT,
    submitted_at   TIMESTAMPTZ,
    payload_hash   TEXT NOT NULL,             -- change detection for re-triage (later phase)
    ingested_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source, source_ref)               -- replays are no-ops, by construction
);

CREATE TABLE duta.requisitions (
    id            SERIAL PRIMARY KEY,
    external_code TEXT UNIQUE NOT NULL,
    title         TEXT NOT NULL,
    seniority     TEXT,
    city          TEXT,
    remote_policy TEXT,
    skills_txt    TEXT,
    description   TEXT,
    status        TEXT NOT NULL,
    row_hash      TEXT NOT NULL,
    synced_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE duta.triage_results (
    id               SERIAL PRIMARY KEY,
    application_id   INTEGER NOT NULL UNIQUE REFERENCES duta.applications (id),
    decision         TEXT NOT NULL CHECK (decision IN ('ADVANCE', 'NEEDS_INFO', 'DUPLICATE', 'REVIEW')),
    requisition_code TEXT,
    duplicate_of     TEXT,
    confidence       REAL,
    evidence         JSONB,
    rationale        TEXT,
    engine           TEXT NOT NULL,            -- e.g. 'stub-0' | 'llm:<model>#prompt:<ver>'
    cost_usd         NUMERIC(8, 5),
    latency_ms       INTEGER,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE duta.review_queue (
    id             SERIAL PRIMARY KEY,
    application_id INTEGER NOT NULL UNIQUE REFERENCES duta.applications (id),
    reason         TEXT NOT NULL,
    status         TEXT NOT NULL DEFAULT 'open',   -- open | decided
    human_decision TEXT,
    decided_by     TEXT,
    decided_at     TIMESTAMPTZ,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- ADR-0004: the queue is worked oldest-first, never score-ordered.
CREATE INDEX idx_review_queue_open ON duta.review_queue (status, created_at);

CREATE TABLE duta.sync_state (
    source     TEXT PRIMARY KEY,
    watermark  TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE duta.audit_log (
    id      SERIAL PRIMARY KEY,
    at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    actor   TEXT NOT NULL,                     -- 'system:<component>' or a human subject
    action  TEXT NOT NULL,
    subject TEXT,
    detail  JSONB
);
