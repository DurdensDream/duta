# ADR-0003: Deterministic duplicate detection — no LLM in the dedup path

- **Status:** Accepted
- **Date:** 2026-07-27
- **Deciders:** Ayush Sharma (FDE), Marcus Reed (champion)

## Context

~8% of inbound applications belong to a human who already exists in some Meridian system — the
double-outreach problem recruiters find embarrassing. An LLM could judge "same person?" — but a
merge decision touches candidate identity, must be explainable to compliance, and must be
**replayable**: the same inputs must always produce the same links.

## Decision

Duplicate detection is **pure deterministic code**:

1. **Exact tier:** normalized email equality, or normalized phone (E.164) equality → `DUPLICATE`.
2. **Fuzzy tier:** trigram similarity of normalized full name ≥ 0.85 **and** one corroborating
   signal (same phone, same city + same current employer) → `DUPLICATE`.
3. **Borderline tier:** fuzzy name match with no corroboration → **`REVIEW`**, never auto-linked.

Linking is non-destructive: records are associated under a canonical person id; nothing is merged
or deleted, and every link stores the rule that produced it.

No model call appears anywhere in this path.

## Consequences

- Every dedup outcome is explainable in one sentence ("email matched after normalization") and
  reproducible in a test — which is exactly what a compliance reviewer asks for.
- Free and instant: dedup runs before any model spend, so true duplicates cost ~$0 to triage.
- Recall is knowingly imperfect: aliases and changed emails slip to the borderline tier and land
  on humans. That trade — precision and explainability over recall — is the right one for an
  action that touches identity.
- Thresholds (0.85, corroboration rules) are config, tuned against the golden set's labeled
  duplicate pairs, so the choice is measured rather than folklore.
