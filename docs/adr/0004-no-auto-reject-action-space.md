# ADR-0004: `REJECT` does not exist in the system's action space

- **Status:** Accepted — load-bearing for the whole engagement
- **Date:** 2026-07-27
- **Deciders:** Ayush Sharma (FDE), Dana Whitfield (sponsor), Meridian counsel

## Context

Two facts from discovery dominate: (1) recruiters abandoned the 2024 "AI ranking" tool because it
buried candidates without explanation — adoption died at ~12%; (2) counsel treats any autonomous
negative action on a candidate as EEOC exposure that a pilot has no business taking.

The usual mitigation is a prompt instruction: *"never reject a candidate."* Prompt instructions
are policies; policies drift, get overridden by a bad merge, or fail silently on a model upgrade.

## Decision

Rejection is **structurally impossible**, not discouraged:

- The `TriageDecision` enum has four members: `ADVANCE`, `NEEDS_INFO`, `DUPLICATE`, `REVIEW`.
  There is no fifth. Model output is parsed into this type; anything unparseable degrades to
  `REVIEW`.
- No ranking, hiding, or suppression: `REVIEW` items are ordered by arrival time, not by score,
  so the system cannot bury a candidate by sorting either.
- A CI test asserts the enum's exact membership and fails the build if anyone adds a negative
  action without tripping over this ADR.

Negative decisions remain where they were: with a named human, in the review queue, audited.

## Consequences

- The auto-resolution ceiling is accepted knowingly: applications that are genuinely poor fits
  still consume human attention (as `REVIEW`). S1's 60% target was set with this ceiling in mind.
- Trust story is simple enough for a recruiter town hall: *"the system can shortlist you, ask you
  for info, or hand you to a human. That is all it can do."*
- Guardrail-by-construction beats guardrail-by-prompt: this decision costs nothing at runtime and
  cannot regress quietly.
