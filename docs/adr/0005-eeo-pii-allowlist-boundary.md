# ADR-0005: EEO/PII never reaches a model — enforced by allowlist, not by redaction

- **Status:** Accepted — counsel's condition for the pilot
- **Date:** 2026-07-27
- **Deciders:** Ayush Sharma (FDE), Meridian counsel

## Context

TalentBase stores EEO self-identification (gender, ethnicity, DOB, veteran status, disability
status, marital status) **inline on the candidate row** — a 2011 schema decision. Counsel's
condition is absolute: this data is never provided to any model, hosted or local.

The common approach is **redaction**: take the record, strip the bad fields, pass the rest.
Redaction is a denylist, and denylists fail open — a new column, a renamed field, or a source
added later walks straight through.

## Decision

The boundary is an **allowlist that fails closed**, applied at the translation layer where every
source is mapped into the canonical schema:

- The canonical `Application`/`Candidate` types contain **only** fields on the allowlist. EEO
  fields have nowhere to live in the canonical model — parity with ADR-0004's
  "structurally impossible" principle.
- Model prompts are built exclusively from a dedicated `PromptView` projection of the canonical
  types — a second, narrower allowlist — so even future canonical additions don't leak by default.
- **Runtime tripwire:** the model client refuses to send any payload containing a denylisted
  field name or a DOB-shaped pattern; a trip raises, the application degrades to `REVIEW`, and
  the event is logged and counted (`eeo_tripwire_total` — S6 requires this stays at 0 trips
  from real leaks; the metric existing at all is what makes S6 auditable).
- **CI enforcement:** a test constructs source records with every known EEO field populated, runs
  the full translation + prompt-build path, and asserts none of those values appear in any
  outbound payload.

## Consequences

- Legitimate signals are lost with the illegitimate ones (e.g., DOB-derived seniority). Accepted;
  the model judges fit from skills, titles, and history only.
- Two allowlists (canonical + prompt view) cost a few minutes per new field. That friction is the
  feature: adding a field to a prompt is a reviewed decision, not a side effect.
- The tripwire's failure mode is conservative: a false positive sends one application to a human,
  a false negative is caught by the CI construction test. Both directions have a floor.
