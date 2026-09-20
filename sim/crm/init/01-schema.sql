-- TalentBase — Meridian's 2011-era CRM schema (staged reproduction).
-- Deliberate period-authentic sins: free-text everywhere, EEO self-ID inline on the
-- candidate row (see ADR-0005), unreliable updated_at on two tables (see ADR-0001).

CREATE SCHEMA IF NOT EXISTS talentbase;

CREATE TABLE talentbase.tb_candidates (
    candidate_id      SERIAL PRIMARY KEY,
    full_name         TEXT NOT NULL,
    email             TEXT,
    phone             TEXT,           -- 5+ formats in the wild
    city_raw          TEXT,           -- free text: "Columbus, OH" / "columbus" / "CBUS/remote"
    state             TEXT,
    current_title     TEXT,
    current_employer  TEXT,
    skills_txt        TEXT,           -- comma/semicolon-mixed free text
    work_auth         TEXT,           -- free text: "US Citizen" / "H1B" / "" / NULL
    source            TEXT,
    -- 2011 design decision, 2026 consequences: EEO self-identification inline.
    -- These columns must never cross the translation layer (ADR-0005).
    gender            TEXT,
    ethnicity         TEXT,
    date_of_birth     DATE,
    veteran_status    TEXT,
    disability_status TEXT,
    marital_status    TEXT,
    created_at        TIMESTAMPTZ NOT NULL,
    updated_at        TIMESTAMPTZ    -- NULLable; trustworthy on this table
);

CREATE TABLE talentbase.tb_requisitions (
    req_id        SERIAL PRIMARY KEY,
    external_code TEXT UNIQUE,        -- "TECH-2026-014"; JobWire's "Job Ref" points here (when it does)
    title         TEXT NOT NULL,
    bu            TEXT NOT NULL,      -- "Technology" | "Healthcare" | "Industrial"
    seniority     TEXT,               -- "Junior" | "Mid" | "Senior" | "Lead"
    city          TEXT,
    remote_policy TEXT,               -- "onsite" | "hybrid" | "remote"
    skills_txt    TEXT,
    description   TEXT,
    status        TEXT NOT NULL,      -- "open" | "closed"
    bill_rate     NUMERIC(8,2),
    created_at    TIMESTAMPTZ NOT NULL,
    updated_at    TIMESTAMPTZ         -- unreliable on this table: often NULL (hash-fallback sync, ADR-0001)
);

CREATE TABLE talentbase.tb_applications (
    app_id       SERIAL PRIMARY KEY,
    candidate_id INTEGER NOT NULL REFERENCES talentbase.tb_candidates (candidate_id),
    req_id       INTEGER REFERENCES talentbase.tb_requisitions (req_id),  -- often NULL: arrives unassigned
    status       TEXT NOT NULL DEFAULT 'new',
    notes        TEXT,
    submitted_at TIMESTAMPTZ NOT NULL,
    updated_at   TIMESTAMPTZ          -- unreliable on this table too
);

CREATE INDEX idx_tb_candidates_email ON talentbase.tb_candidates (lower(email));
CREATE INDEX idx_tb_applications_submitted ON talentbase.tb_applications (submitted_at);
