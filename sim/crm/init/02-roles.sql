-- Ellen's grant: one read-only role for the pilot. No writes, no DDL, revocable in one statement.
-- (Staged reproduction of the real constraint: the pilot integrates least-invasively, ADR-0001.)

CREATE ROLE duta_ro LOGIN PASSWORD 'duta_ro_pw';

GRANT CONNECT ON DATABASE talentbase TO duta_ro;
GRANT USAGE ON SCHEMA talentbase TO duta_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA talentbase TO duta_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA talentbase GRANT SELECT ON TABLES TO duta_ro;
