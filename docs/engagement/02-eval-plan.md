# Eval plan — written before the agent exists

- **Author:** Ayush Sharma, forward-deployed engineer
- **Date:** 2026-07-27
- **Principle:** the golden set and its rubric are committed **before** the triage agent is
  built. The agent is written to pass an exam that already exists — not graded by an exam
  written after we've seen its answers.

---

## 1. Golden dataset

**100 applications**, sampled from the staged Meridian sources to cover the distribution *and*
the traps:

| Slice | ~Count | What it exercises |
|---|---|---|
| Clean strong match to one open requisition | 25 | `ADVANCE` happy path, citation quality |
| Plausible but wrong-requisition bait (right skills, wrong seniority/location) | 15 | The precision killer — S2 lives or dies here |
| Missing essentials (no phone / no work auth / no location) | 12 | `NEEDS_INFO` |
| Cross-source duplicates (exact email/phone) | 10 | Dedup exact tier |
| Fuzzy duplicates (name variants, new email, corroborating phone) | 8 | Dedup fuzzy tier + borderline→`REVIEW` |
| Genuinely ambiguous fit (human judgment call) | 15 | Must land in `REVIEW`, not be guessed at |
| Dirty-data stress (encoding junk, header drift, date-format chaos) | 10 | Translation layer, not the model |
| Adversarial content (prompt-injection text in resume fields) | 5 | Injection must degrade to `REVIEW`, never execute |

Each golden record: `application_ref`, `expected_decision`, `expected_requisition_id` (nullable),
`expected_duplicate_of` (nullable), `rationale` (one sentence), `labeler`, `label_confidence`.

**Labeling process:** heuristic pre-labels generated with the seed data → **every label reviewed
by a human** (labeler field says who) → disagreements between pre-label and reviewer recorded in
`golden/label-changelog.md` — the disagreement rate is itself reported in the eval report.

## 2. Metrics

| Metric | Definition | Gate |
|---|---|---|
| Decision accuracy | exact-match on `expected_decision`, all 100 | report |
| **Auto-advance precision** | of predicted `ADVANCE`: % where golden agrees (decision + requisition) | **≥ 0.97 (S2) — blocking** |
| Auto-resolution rate | % predicted `ADVANCE`/`NEEDS_INFO`/`DUPLICATE` | ≥ 0.60 (S1) — blocking |
| Escalation correctness | of golden-`REVIEW` items: % predicted `REVIEW` (ambiguity must not be guessed) | ≥ 0.90 — blocking |
| Shortlist recall@10 | golden requisition present in FTS shortlist | ≥ 0.95 — blocking (ADR-0002 falsifier) |
| Dedup precision / recall | on labeled duplicate pairs | P ≥ 0.98 / R ≥ 0.85 — blocking |
| Injection containment | adversarial slice: % landing in `REVIEW` with tripwire logged | = 1.00 — blocking |
| Cost per application | measured tokens × published price | < $0.02 (S5) — report + alert |
| Latency | p95 per application, wall clock | < 60 s (S4) — report |

## 3. Judge policy — where an LLM judge is and isn't allowed

- Decision/requisition/duplicate correctness is **exact-match against human labels. No LLM judge.**
- An LLM judge is used for one thing only: **citation faithfulness** (does the cited evidence
  actually appear in the application and support the claim?). The judge is **calibrated**: its
  verdicts on a 30-item human-audited subset are compared to the human's, and the agreement rate
  ships in the eval report next to every judge-derived number. If agreement < 0.9, judge numbers
  are marked unreliable and excluded from gates.
- Nothing self-graded goes ungated: any metric produced by a model is either calibrated as above
  or clearly labeled non-blocking.

## 4. Runners and gates

| Runner | Model | When | Purpose |
|---|---|---|---|
| `stub` | none — deterministic canned outputs | every CI run | pipeline/guardrail/translation correctness, fast |
| `replay` | recorded real-model responses (committed fixtures) | every CI run | **regression gate**: blocking thresholds above, deterministic |
| `live` | configured provider (Anthropic default; Ollama for local dev) | pre-deploy, weekly, and on any prompt/model change | refreshes `evals/results/metrics.json` + replay fixtures; the numbers in the eval report come only from here |

- `evals/results/metrics.json` is **committed** — every number in the eval report and README is
  reproducible from the repo, with model id, prompt version, and git SHA embedded.
- CI fails if a blocking threshold in `evals/thresholds.yaml` regresses. Thresholds only move via
  PR that also updates this document.
- Prompt and model are versioned config; every eval result records both, so any regression
  bisects to a specific prompt/model change.

## 5. Drift & shadow evaluation (operation phase)

In shadow mode, the system's decisions are compared weekly against what the pilot pod actually
did (their actions are the moving ground truth). Disagreement rate per decision type feeds the
weekly report; a sustained rise is the trigger to re-sample 20 fresh golden items — golden sets
rot, and this one is scheduled to be re-fed, not assumed immortal.

---

*Staged engagement — see repo README. The golden set ships in `evals/golden/`; the labeling
rubric with worked examples is in `evals/golden/LABELING.md`.*
