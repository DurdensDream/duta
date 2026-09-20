# Discovery memo — Meridian Staffing Group

- **Engagement:** Application triage pilot, Technology business unit
- **Author:** Ayush Sharma, forward-deployed engineer
- **Date:** 2026-07-27 (end of discovery week)
- **Status:** Reviewed with Marcus Reed (champion); open questions tracked below
- **Sources:** 6 stakeholder sessions, 2 recruiter shadowing sessions, read-only access to all three systems

---

## 1. The problem as sold vs. the problem as found

The engagement was sold as *"we need AI to score candidates."* One week of discovery says the
bleeding wound is somewhere else.

Watching recruiters work, the pattern is consistent: an application arrives in one of **three
systems**, sits untouched for hours, and when a recruiter finally opens it, they spend most of
their time not judging the candidate but **reconstructing context** — is this person already in
TalentBase? Did they also apply through JobWire last month? Which of my 38 open requisitions is
this actually for? Only after that reconstruction does any judgment happen, and the judgment
itself is usually fast.

Meridian is a staffing agency. Their candidates are simultaneously in other agencies' pipelines,
and **the first agency to call usually wins the placement**. Median first touch on an inbound
application is ~26 hours (per Kestrel timestamps sampled across four weeks). Speed, not scoring
quality, is what the business loses money on.

**The real problem: routing and deduplication latency, not candidate scoring.** A scoring model
bolted onto a 26-hour queue optimizes the wrong stage.

One more finding shapes everything: Meridian rolled out an "AI ranking" feature from a previous
vendor in 2024. Recruiters describe it as a black box that buried candidates they would have
called. Adoption was ~12% after 90 days and the feature was quietly disabled. **Trust is the
constraint.** Anything we ship must show its evidence, and must never take a negative action on
a candidate autonomously.

## 2. Numbers gathered in discovery

All figures measured or sampled during discovery week (methodology noted inline):

| Metric | Value | How measured |
|---|---|---|
| Inbound applications, agency-wide | ~1,900 / week | Kestrel + JobWire + CRM counts, 4-week window |
| Inbound applications, Technology BU (pilot scope) | ~640 / week | Same window, BU filter |
| Median first touch | ~26 h | Kestrel `submitted_at` → first recruiter activity |
| Median manual triage time | ~11 min / application | Shadowing, n=23 applications across 2 recruiters |
| Duplicate rate (same human, ≥2 records) | ~8% | Email/phone exact-match sample across systems |
| Open Technology-BU requisitions | 38 | CRM query |
| Recruiters in pilot pod | 5 | Agreed with Marcus |

## 3. Stakeholder map

| Person | Role | What they care about | Notes |
|---|---|---|---|
| **Dana Whitfield** | VP Recruiting Ops — exec sponsor | Fill rate, time-to-submit, not embarrassing the brand | Sponsors the pilot; wants a live demo by Friday of week 2 |
| **Marcus Reed** | Director, TA Operations — champion | Recruiter productivity; owns the pilot pod | Our day-to-day counterpart; burned by the 2024 AI rollout, wants evidence-first |
| **Ellen Park** | DBA lead — TalentBase gatekeeper | Stability of a 15-year-old system nobody wants to touch | Read-only replica access only; **no schema changes, no extensions, no replication slots**; 2-week lead time on any credential request |
| **Kestrel CSM** | Vendor customer success | Contract renewal | API quota is 60 req/min and **will not be raised for a pilot** |
| **Priya N.** + pod | Senior recruiter, pilot pod lead | "Don't hide candidates from me" | The adoption make-or-break; wants to see *why* for every recommendation |
| Meridian counsel | Compliance | EEO/PII exposure | Hard condition recorded in §5 |

## 4. Systems and data map

### TalentBase CRM (system of record, 2011, self-hosted PostgreSQL)
- ~480k candidate records, ~30k Technology BU. No API — direct SQL against a **read-only replica**.
- Data quality, sampled: free-text locations (`"Columbus, OH"`, `"columbus"`, `"CBUS/remote"`),
  three coexisting date formats, job categories are recruiter free-text, phone numbers in 5+
  formats, and **EEO self-identification fields (gender, ethnicity, DOB, veteran status,
  disability status) stored inline on the candidate row**, a 2011 design decision with 2026
  consequences (§5).
- Ellen's constraints (no extensions, no replication slots on the replica) rule out CDC for the
  pilot — see [ADR-0001](../adr/0001-watermark-sync-over-cdc.md).

### Kestrel ATS (SaaS, 2021 — where new Technology-BU applications land)
- OAuth2 client-credentials API. **60 req/min hard cap**, 429s with `Retry-After` when exceeded.
- Cursor pagination; sampled behavior shows **unstable ordering under concurrent writes** and
  intermittent 5xx (vendor status page confirms "elevated error rates" twice in the sampled month).
- `updated_since` filter exists and works; this is our incremental pull handle.

### JobWire partner feed (job-board applications, Industrial + Technology BUs)
- Nightly CSV over SFTP. Latin-1 encoded, header names drift between drops
  (`"E-mail"` / `"email_address"` / `"Email"`), duplicate rows within a single drop are common.
- No push option, no API, no negotiating a format change: the feed is what it is.

## 5. Constraints (non-negotiable, recorded verbatim where possible)

1. **EEO/PII boundary** — counsel's condition for the pilot: *"self-identification data does not
   leave the systems it lives in and is not provided to any model, hosted or otherwise."*
   → enforced structurally, see [ADR-0005](../adr/0005-eeo-pii-allowlist-boundary.md).
2. **No writes to TalentBase.** Read-only replica, period. Anything we produce lives in our own
   schema and exports outward.
3. **No autonomous negative actions.** No candidate is rejected, deprioritized, or buried by the
   system without a human decision → [ADR-0004](../adr/0004-no-auto-reject-action-space.md).
4. **Auditability.** Every automated decision must be reconstructable: inputs, evidence, model
   version, prompt version, timestamp.
5. **Pilot spend cap** on model usage; per-application cost must be measured and reported.

## 6. What the pilot should therefore be

An **application triage layer** for the Technology BU that:
- ingests continuously from Kestrel (API), TalentBase (read-only SQL), and JobWire (nightly CSV)
  into one canonical, allowlisted schema;
- for each application: detects duplicates deterministically, shortlists matching requisitions,
  and produces a **cited** match recommendation;
- **auto-resolves** the unambiguous outcomes (advance to shortlist, request missing info, merge
  duplicate) and **escalates** everything else to a review queue owned by the pilot pod;
- measures itself: auto-resolution rate, advance precision, first-touch latency, cost per
  application — on a dashboard Meridian can see.

## 7. Open questions & labeled assumptions

- **[Assumption]** Kestrel's 60 rpm cap is enforced per client-id, not per endpoint. Sampling
  suggests per client-id; worst case halves our sync frequency. Validate in week 2.
- **[Assumption]** ~640 apps/week holds outside the sampled month (no seasonal spike data).
- **[Open]** Does JobWire dedupe across drops, or can the same application reappear days later?
  Treat re-appearance as possible until proven otherwise.
- **[Open]** Historical rejection data exists in TalentBase — deliberately **not** used in the
  pilot (trust + compliance risk outweighs any ranking gain). Revisit only with counsel at
  productization.

---

*Meridian and its staff are synthetic; this memo is written from the staged environment in this
repo, which reproduces every constraint above (including the hostile ones) so the engagement can
be run for real. — see the repo README.*
