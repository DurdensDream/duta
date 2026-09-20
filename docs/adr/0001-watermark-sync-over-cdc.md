# ADR-0001: Watermark incremental sync over CDC for TalentBase

- **Status:** Accepted (pilot); revisit at productization
- **Date:** 2026-07-27
- **Deciders:** Ayush Sharma (FDE), Ellen Park (DBA lead)

## Context

TalentBase is the 2011-era system of record. We need its candidates and requisitions continuously,
and I have shipped Debezium CDC pipelines before — it was my default instinct here.

But the access we actually have is a **read-only replica**, under a DBA constraint of *no
extensions, no replication slots, no schema changes*, with a 2-week lead time on any request.
Logical replication slots cannot be created on a standby replica on their PostgreSQL version, so
CDC would require primary access Ellen will not grant for a pilot — plus a Kafka/Connect footprint
we would have to operate inside the customer's boundary for the pilot's ~640 rows/week of change.

## Decision

Pull incrementally from the replica using **`updated_at` watermarks** per table, on a 5-minute
schedule, executed as durable workflows (retries, resumability). Watermarks are persisted in our
own schema; each pull is idempotent (upsert by source primary key + row hash).

The same pattern covers Kestrel (`updated_since` API parameter) — one sync abstraction, three
sources.

## Consequences

- **Freshness is bounded by the poll interval** (≤5 min added latency). S3 budget (15 min first
  touch) absorbs this; if the SLA ever tightens below the poll floor, CDC becomes the
  productization path — that argument, with numbers, goes in the productization memo.
- **Hard deletes are invisible** to watermark pulls. Acceptable: applications are append-mostly;
  a weekly full-key reconciliation sweep catches the residue and reports a `missing_keys` metric,
  so the blind spot is measured rather than assumed away.
- **Rows without trustworthy `updated_at`** (two TalentBase tables) fall back to full-table hash
  comparison on each pull — fine at pilot volume, flagged as a scale limit.
- Least-invasive integration: nothing is installed or changed on the customer's systems; the
  entire pilot can be revoked by dropping one read-only credential.
