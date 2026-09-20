-- Phase G1: canonical candidates (synced read-only from TalentBase) and duplicate links.
-- Linking is non-destructive (ADR-0003): nothing is merged, nothing is deleted, every link
-- records the deterministic rule that produced it.

CREATE TABLE duta.candidates (
    id               SERIAL PRIMARY KEY,
    source           TEXT NOT NULL,            -- talentbase
    source_ref       TEXT NOT NULL,            -- TB-CAND-000123
    full_name        TEXT,
    email            TEXT,
    phone            TEXT,
    city             TEXT,
    state            TEXT,
    current_title    TEXT,
    current_employer TEXT,
    skills_txt       TEXT,
    work_auth        TEXT,
    email_norm       TEXT,
    phone_norm       TEXT,
    name_norm        TEXT,
    city_norm        TEXT,
    row_hash         TEXT NOT NULL,
    synced_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source, source_ref)
);
CREATE INDEX idx_candidates_email_norm ON duta.candidates (email_norm);
CREATE INDEX idx_candidates_phone_norm ON duta.candidates (phone_norm);

CREATE TABLE duta.duplicate_links (
    id             SERIAL PRIMARY KEY,
    application_id INTEGER NOT NULL UNIQUE REFERENCES duta.applications (id),
    matched_kind   TEXT NOT NULL,              -- crm_candidate | application
    matched_ref    TEXT NOT NULL,              -- TB-CAND-000512 / KES-000123 / JW-...
    rule           TEXT NOT NULL,              -- email_exact | phone_exact | fuzzy_corroborated
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Normalized identity columns on applications, computed at ingest (dedup queries hit these).
ALTER TABLE duta.applications
    ADD COLUMN email_norm TEXT,
    ADD COLUMN phone_norm TEXT,
    ADD COLUMN name_norm  TEXT;
CREATE INDEX idx_applications_email_norm ON duta.applications (email_norm);
CREATE INDEX idx_applications_phone_norm ON duta.applications (phone_norm);
