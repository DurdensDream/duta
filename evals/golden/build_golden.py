#!/usr/bin/env python3
"""Build golden-set pre-labels by sampling the seed generator's planted-case manifest.

Slice sizes follow docs/engagement/02-eval-plan.md 1. Output is PRE-LABELS: every record
carries review_status=pending_human_review until a human reviews it (see LABELING.md).
The sampling is deterministic (seed 7) so the golden set is stable across rebuilds.
"""

import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "data" / "generated" / "manifest.json"
OUT = Path(__file__).resolve().parent / "golden.jsonl"

# eval-plan slice -> (manifest cases, sample size)
SLICES = [
    ("clean_strong_match", ["strong_match"], 25),
    ("wrong_req_bait", ["bait"], 15),
    ("missing_essentials", ["missing_info"], 12),
    ("cross_source_duplicates", ["dup_exact", "dup_intra_drop"], 10),
    ("fuzzy_duplicates", ["dup_fuzzy_corroborated"], 5),
    ("fuzzy_borderline", ["dup_fuzzy_borderline"], 3),
    ("genuinely_ambiguous", ["ambiguous"], 15),
    ("dirty_data_stress", ["dirty_strong", "dirty_review"], 10),
    ("adversarial_injection", ["injection"], 5),
]


def source_of(ref):
    if ref.startswith("KES-"):
        return "kestrel"
    if ref.startswith("JW-"):
        return "jobwire"
    return "talentbase"


def main():
    rng = random.Random(7)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    planted = manifest["planted"]

    records = []
    for slice_name, cases, n in SLICES:
        pool = [p for p in planted if p["case"] in cases]
        if len(pool) < n:
            raise SystemExit("slice {}: need {} but only {} planted".format(slice_name, n, len(pool)))
        for p in rng.sample(pool, n):
            records.append({
                "application_ref": p["ref"],
                "source": source_of(p["ref"]),
                "slice": slice_name,
                "planted_case": p["case"],
                "expected_decision": p["expected_decision"],
                "expected_requisition_id": p["expected_req"],
                "expected_duplicate_of": p["duplicate_of"],
                "rationale": p["note"],
                "labeler": "heuristic-prelabel",
                "label_confidence": "high" if p["case"] in
                    ("strong_match", "dup_exact", "dup_intra_drop", "missing_info", "injection") else "medium",
                "review_status": "pending_human_review",
            })

    records.sort(key=lambda r: r["application_ref"])
    with open(OUT, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    by_dec = {}
    for r in records:
        by_dec[r["expected_decision"]] = by_dec.get(r["expected_decision"], 0) + 1
    print("golden: wrote {} records -> {}".format(len(records), OUT.relative_to(ROOT)))
    print("golden: expected-decision distribution: {}".format(json.dumps(by_dec, sort_keys=True)))


if __name__ == "__main__":
    main()
