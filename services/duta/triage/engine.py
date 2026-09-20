"""Triage engine. G0 walking skeleton: a stub that routes everything to humans.

The pipes are real, the brain is deliberately not — the review queue, audit trail, and
durability all exercise end to end before any model spend. The real engine lands at gate G2
behind the eval harness, and REVIEW-everything remains its fail-safe degradation mode.
"""

from ..models import TriageDecision, TriageResult

ENGINE_VERSION = "stub-0"


def triage(application_row: dict) -> TriageResult:
    return TriageResult(
        decision=TriageDecision.REVIEW,
        rationale="stub engine (G0): all applications route to humans until the triage model lands (G2)",
        engine=ENGINE_VERSION,
        confidence=None,
        evidence={"stub": True},
        cost_usd=0.0,
        latency_ms=0,
    )
