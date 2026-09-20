"""ADR-0004 enforcement: the system's action space has exactly four members and REJECT is not
one of them. If this test is failing, you are adding a negative action — supersede ADR-0004 in
the same PR or stop."""

from duta.api import HUMAN_DECISIONS
from duta.models import TriageDecision


def test_action_space_is_exactly_four():
    assert {d.value for d in TriageDecision} == {"ADVANCE", "NEEDS_INFO", "DUPLICATE", "REVIEW"}


def test_system_cannot_reject():
    assert "REJECT" not in {d.value for d in TriageDecision}
    assert not hasattr(TriageDecision, "REJECT")


def test_humans_may_reject():
    # the asymmetry is the design: negative decisions belong to named humans, audited
    assert "REJECT" in HUMAN_DECISIONS
