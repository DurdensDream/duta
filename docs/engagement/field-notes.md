# Engagement field notes

Dated, unpolished, kept on purpose. The postmortems are the formal version; this is the lab bench.

---

## 2026-07-27 — watermark sync silently dropped 2 of 10 new Kestrel applications

**What happened.** Minutes after the walking skeleton's first successful sync, a staged release
of 10 new vendor applications ingested only 8. `KES-000331` and `KES-000332` were visible in the
vendor API but absent from the canonical store — a silent gap, caught only because the release
count was known.

**Root cause.** Kestrel compares `updated_since` as a raw string, and spells `updatedAt` in three
timezone forms. `KES-000331` was updated at `2026-07-27T05:40:00-05:00` = **10:40 UTC — newer**
than the `2026-07-27T06:50:00Z` watermark, but the string `"...05:40:00-05:00"` sorts *before*
`"...06:50:00Z"`, so the vendor filtered it out server-side.

**Why the designed defense failed.** ADR-0001's overlap window rewinds the watermark 6h on every
pull, sized as "greater than the worst offset seen (-05:00)". That sizing was wrong: the string
comparison shifts a -05:00 record's *apparent* time by 5h, so exclusion happens whenever the
record's UTC instant is older than `max_seen - overlap + offset` — the safe window depends on the
time-spread of arriving data, which is unbounded. **No fixed overlap is provably safe against a
string-comparing vendor.**

**Fix.** Watermarks stay (freshness, cheap), but correctness now comes from **deep
reconciliation**: `KestrelSyncWorkflow(deep=true)` ignores the watermark and re-scans the vendor
completely; schema-level idempotency makes re-reads free. Deep runs are scheduled alongside
incremental ones (pilot: hourly deep, 5-min incremental — at 8 pages/scan this is far inside the
60 rpm quota; the productization memo must re-price this at full-BU volume).

**The metric that would have caught it without luck:** vendor-visible count vs canonical-store
count per source — added to the observability plan as `sync_completeness` (G4).

**Lesson.** "Parse timestamps, don't compare strings" was already in the client. The lesson is
one level up: *your* code being timezone-correct doesn't help when the **vendor's filter** isn't —
integration defenses have to assume the remote side's comparison semantics, not just its data
format. Trust arithmetic you run, not arithmetic you request.
