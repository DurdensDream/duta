# Duta — a forward-deployed engagement, end to end

**Duta** (दूत, *envoy*) is a complete forward-deployed engineering engagement run against a staged
enterprise customer: **Meridian Staffing Group**, a mid-market staffing agency drowning in inbound
job applications spread across three systems that don't talk to each other.

> **What's staged and what's real.** Meridian, its staff, and every record in this repo are
> synthetic — a deliberately messy customer environment built so the engagement could be run
> end to end, the way a forward-deployed engineer actually runs one. The engineering, the
> integrations, the auth, the measurements, the failures, and the postmortem are real.

## The engagement

Meridian's recruiters manually triage ~1,900 inbound applications a week across a 2011-era
self-hosted CRM ("TalentBase"), a rate-limited SaaS ATS ("Kestrel"), and a nightly CSV feed from a
job-board partner ("JobWire"). Median first touch on an application is measured in hours; in
staffing, candidates accept whoever calls first.

The pilot delivers an **application triage system** for one business unit: it ingests from all three
sources through a translation layer, and a durable agent triages every application — match-to-requisition
with cited evidence, duplicate detection, missing-info flags — **auto-resolving clear cases and
escalating everything ambiguous to a human review queue**. It never rejects anyone; rejection is
structurally outside its action space.

## Engagement artifacts

The docs are first-class deliverables, written in the order an engagement produces them:

| Artifact | Purpose |
|---|---|
| [Discovery memo](docs/engagement/00-discovery-memo.md) | What I found in week 1 — stakeholders, systems, the real problem vs the sold problem |
| [Scoping doc](docs/engagement/01-scoping-and-success-criteria.md) | Pilot SLA targets, decision taxonomy, scope cuts, rollout gates |
| [Eval plan](docs/engagement/02-eval-plan.md) | Golden dataset design, labeling rubric, gates — written before the agent existed |
| [ADRs](docs/adr/) | Every architecture decision, including what we deliberately did *not* build |
| Eval report | Measured results against the golden set *(produced by the eval harness)* |
| Incident postmortem + runbook | A production failure, injected, debugged, and written up |
| Exec readout + productization memo | The closing artifacts of the engagement |

## Quickstart (walking skeleton, gate G0)

```bash
make seed                    # generate the staged messy environment (deterministic)
docker compose up -d --build # crm-db, vendor-sim, app-db, temporal(+ui :8233), api :8000, worker

curl -X POST localhost:8000/api/sync/kestrel        # durable sync: OAuth2 -> pages -> triage
curl localhost:8000/api/stats                       # decisions, auto-resolution rate
curl "localhost:8000/api/queue?limit=5"             # the review queue (oldest first, always)

# stage a live demo: 10 new applications "arrive" at the vendor, then sync again
curl -X POST localhost:8100/admin/release -H 'Content-Type: application/json' -d '{"batch":1}'
curl -X POST "localhost:8000/api/sync/kestrel?deep=true"
```

The triage engine at G0 is deliberately a stub (everything routes to humans) — the pipes are
real: OAuth2 against a rate-limited vendor, translation allowlist, durable Temporal execution,
idempotent persistence, audit trail. See
[field-notes](docs/engagement/field-notes.md) for the watermark bug the staged vendor already
caught, and why `?deep=true` exists.

## Status

Engagement in progress — gate G0 (walking skeleton) passed. This README grows as phases land;
architecture diagram and live-demo link arrive with later gates.

## License

MIT
