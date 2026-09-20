# Pilot scoping & success criteria — Meridian application triage

- **Author:** Ayush Sharma, forward-deployed engineer
- **Date:** 2026-07-27
- **Approved by:** Marcus Reed (champion), Dana Whitfield (sponsor) — kickoff review
- **Pilot scope:** Technology BU (~640 applications/week, 38 open requisitions, 5-recruiter pod)

---

## 1. Decision taxonomy

Every application receives exactly one triage decision:

| Decision | Meaning | Who acts |
|---|---|---|
| `ADVANCE` | Clear fit for a specific requisition; added to that requisition's shortlist with cited evidence | Auto (recruiter sees it on the shortlist) |
| `NEEDS_INFO` | Essentials missing (no phone, no work authorization, no location); templated info request **drafted** for recruiter approval | Auto-draft, human send |
| `DUPLICATE` | Same human already exists in the canonical store; records linked, best contact info surfaced | Auto (link only — never destructive merge) |
| `REVIEW` | Everything ambiguous: borderline match, guardrail trip, budget breach, low confidence | Human, via review queue |

**There is no `REJECT`.** Not as policy — as structure: the decision type does not contain it, so
no prompt, bug, or model update can produce one ([ADR-0004](../adr/0004-no-auto-reject-action-space.md)).

**Auto-resolved** ≜ `ADVANCE`, `NEEDS_INFO`, or `DUPLICATE` produced without human touch.
`REVIEW` is the fail-safe default: every error path degrades to a human, never to silence.

## 2. Success criteria (the pilot SLA)

Agreed with Dana and Marcus at kickoff. The pilot converts from shadow mode to assisted mode only
while **all** of these hold on the golden set and on shadow traffic:

| # | Metric | Target | Why this number |
|---|---|---|---|
| S1 | Auto-resolution rate | **≥ 60%** | Below this the pod's manual load doesn't measurably drop |
| S2 | Auto-`ADVANCE` precision | **≥ 97%** | A wrong auto-advance burns recruiter trust; this is the 2024-rollout scar tissue |
| S3 | First touch, auto-resolved apps | **< 15 min** from source arrival | The "call first" business case |
| S4 | Triage latency | **p95 < 60 s** per application | Keeps S3 achievable at peak arrival rate |
| S5 | Cost per application | **< $0.02** measured | Pilot spend cap, measured not estimated |
| S6 | EEO/PII fields in any model payload | **0, ever** | Counsel's condition; CI-enforced |
| S7 | Recruiter override rate (of auto-resolved) | **< 10%** by week 2 of assisted mode | Adoption proxy — overrides mean distrust |

## 3. Scope cuts (decided now, revisited at productization)

Recorded so nobody discovers them by surprise:

1. **No outreach is sent by the system.** `NEEDS_INFO` produces a draft; a human sends it.
2. **No writes to TalentBase** — our outputs live in our own schema and export outward as CSV.
3. **No use of historical rejection data** (trust + compliance risk; discovery memo §7).
4. **No vector database** in the pilot ([ADR-0002](../adr/0002-postgres-fts-shortlist-no-vector-db.md)).
5. **No fine-tuning** — prompt + retrieval + guardrails only; the eval harness would have to
   justify anything heavier with numbers.
6. **English only** (Technology BU inbound is >98% English in the sampled month).
7. **Voice/chat surfaces: none.** This is a queue-and-review product in the pilot.

## 4. Delivery plan — walking skeleton first

**Day-5 demo (gate G0):** one real application flows Kestrel → translation layer → triage
(stub decision) → review queue UI, on the real messy seed data, in front of Dana. Nothing smart —
but every pipe is real: OAuth2 against the rate-limited API, canonical schema, durable execution,
queue UI. *(Palantir-style: value visible in week one, not month six.)*

Then weekly iteration, each phase gated:

| Gate | Phase lands | Exit criterion |
|---|---|---|
| G0 | Walking skeleton | Day-5 demo runs live, end to end |
| G1 | Integration hardening | All 3 sources syncing; idempotent replays proven by test; survives injected 429/500/dup storms |
| G2 | Triage agent + guardrails | Golden-set eval: S1, S2 met in `shadow` mode; S6 test green |
| G3 | Review UI + auth | Pilot pod logs in via SSO; every human decision audited |
| G4 | Observability + ops | SLA dashboard live; S3–S5 measured; incident drill run and postmortem written |
| G5 | Readout | Eval report, exec readout, productization memo delivered |

## 5. Rollout & rollback

- **Shadow mode** (weeks 1–2 of operation): system triages everything, recruiters see nothing;
  we measure against their actual decisions.
- **Assisted mode**: recommendations + shortlists visible; auto-resolution live for
  `DUPLICATE`/`NEEDS_INFO`; `ADVANCE` stays recommend-only.
- **Auto mode**: `ADVANCE` auto-resolves only after S2 holds ≥97% across two consecutive weeks
  of assisted traffic.
- **Rollback is one switch**: modes are a config value; dropping a mode level requires no deploy.
  The queue keeps filling in every mode, so recruiters lose nothing when we roll back.

## 6. Risks

| Risk | Mitigation |
|---|---|
| Kestrel quota starves sync at peak | Adaptive poll interval + backoff honoring `Retry-After`; measured sync-lag metric with alert |
| JobWire re-sends applications across drops | Idempotency on source-record identity, not file position |
| Recruiter distrust (2024 scar tissue) | Citations on every recommendation; no negative actions; override always available and measured (S7) |
| Model cost drift | Per-application budget enforcement — breach degrades to `REVIEW`, never to overspend (S5) |
| Gatekeeper lead times (Ellen: 2 weeks) | All credential requests filed in week 1; pilot runs on replica reads only |

---

*Staged engagement — see repo README. The SLA numbers are targets the real system in this repo is
measured against; the eval report holds the results.*
