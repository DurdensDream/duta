# ADR-0002: Postgres FTS + trigram shortlist; no vector database in the pilot

- **Status:** Accepted (pilot); revisit triggers listed below
- **Date:** 2026-07-27
- **Deciders:** Ayush Sharma (FDE)

## Context

Matching an application to requisitions is a retrieve-then-judge problem: first shortlist
plausible requisitions, then let the model judge fit with evidence. I have built hybrid
BM25+vector retrieval with measured nDCG before, so the embedding route is familiar, not feared.

The pilot corpus is **38 open requisitions**. That number changes the calculus: embedding
infrastructure (index lifecycle, model versioning, drift on requisition edits) is operational
weight inside a customer boundary — weight that must be justified by measured recall we cannot
get more cheaply.

## Decision

Shortlist with **PostgreSQL full-text search + `pg_tsvector` over requisition title/skills/description,
plus trigram similarity for fuzzy title matches**, taking the top 10 into the judgment step. The
LLM judges fit only within the shortlist; shortlist quality is measured as **recall@10 against the
golden set** so this decision is falsifiable, not aesthetic.

## Consequences

- Zero new infrastructure: the store we already run does the retrieval.
- Shortlist recall@10 is a first-class eval metric. If it drops below 0.95 on golden data, this
  ADR is wrong and gets superseded.
- **Revisit triggers, recorded now:** requisition count > 500; multilingual requisitions; measured
  recall@10 < 0.95; or productization across all BUs. The upgrade path (pgvector in the same
  Postgres, hybrid with RRF) is deliberately one we have prior art for.
- This is also the pilot's explicit "we did not use the fancier thing because the problem didn't
  ask for it yet" decision — the eval numbers, not the architecture diagram, carry the argument.
