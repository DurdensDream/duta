"""Deterministic duplicate detection (ADR-0003). No model calls, ever.

Rule evaluation is a pure function over normalized identity dicts so it can be exhaustively
unit-tested; the DB layer only fetches comparison sets.

Tiers:
  exact       email_norm or phone_norm equality            -> DUPLICATE
  fuzzy       name trigram >= 0.85 + corroborating signal   -> DUPLICATE
              (corroboration = same city AND same employer; pilot sources carry no structured
               employer, so this tier fires only against CRM-vs-CRM shapes — kept for
               completeness and tested, but in practice pilot fuzzies land borderline)
  borderline  name trigram >= 0.85, no corroboration        -> REVIEW (humans link identities)
"""

from ..models import TriageDecision, TriageResult
from ..normalize import trigram_similarity

FUZZY_THRESHOLD = 0.85
ENGINE_VERSION = "dedup-1"


def evaluate_rules(app: dict, other: dict) -> tuple[str, str] | None:
    """Pure: compare one application's normalized identity against one existing identity.

    Returns (tier, rule) where tier is 'exact' | 'fuzzy' | 'borderline', or None.
    `other` carries: ref, name_norm, email_norm, phone_norm, city_norm, employer (nullable).
    """
    if app.get("email_norm") and app["email_norm"] == other.get("email_norm"):
        return ("exact", "email_exact")
    if app.get("phone_norm") and app["phone_norm"] == other.get("phone_norm"):
        return ("exact", "phone_exact")
    a_name, o_name = app.get("name_norm"), other.get("name_norm")
    if a_name and o_name and trigram_similarity(a_name, o_name) >= FUZZY_THRESHOLD:
        same_city = app.get("city_norm") and app["city_norm"] == other.get("city_norm")
        same_employer = app.get("employer") and app["employer"] == other.get("employer")
        if same_city and same_employer:
            return ("fuzzy", "fuzzy_corroborated")
        return ("borderline", "fuzzy_name_only")
    return None


def find_duplicate(conn, app_row: dict) -> TriageResult | None:
    """Check an ingested application against CRM candidates and earlier applications.

    Returns a DUPLICATE result, a borderline REVIEW result, or None (no identity signal).
    """
    from ..normalize import norm_city  # local import keeps module import-light for tests

    app = {
        "email_norm": app_row.get("email_norm"),
        "phone_norm": app_row.get("phone_norm"),
        "name_norm": app_row.get("name_norm"),
        "city_norm": norm_city(app_row.get("location_raw")),
        "employer": None,  # pilot sources carry no structured employer
    }

    candidates = []
    # Exact-tier probes are indexed lookups; the fuzzy sweep over CRM candidates is a bounded
    # scan (~2k rows at pilot scale — measured, and flagged as a scale limit in the ADR).
    if app["email_norm"] or app["phone_norm"]:
        candidates += conn.execute(
            """
            SELECT 'crm_candidate' AS kind, source_ref AS ref, name_norm, email_norm,
                   phone_norm, city_norm, current_employer AS employer
            FROM duta.candidates
            WHERE (email_norm IS NOT NULL AND email_norm = %(email)s)
               OR (phone_norm IS NOT NULL AND phone_norm = %(phone)s)
            """,
            {"email": app["email_norm"], "phone": app["phone_norm"]},
        ).fetchall()
        candidates += conn.execute(
            """
            SELECT 'application' AS kind, source_ref AS ref, name_norm, email_norm,
                   phone_norm, NULL AS city_norm, NULL AS employer
            FROM duta.applications
            WHERE id < %(id)s  -- earlier arrivals only: the first occurrence stays primary,
                               -- otherwise an identical pair links mutually and both vanish
              AND ((email_norm IS NOT NULL AND email_norm = %(email)s)
                OR (phone_norm IS NOT NULL AND phone_norm = %(phone)s))
            ORDER BY id ASC
            """,
            {"id": app_row["id"], "email": app["email_norm"], "phone": app["phone_norm"]},
        ).fetchall()
    if app["name_norm"]:
        last = app["name_norm"].split()[-1]
        candidates += conn.execute(
            """
            SELECT 'crm_candidate' AS kind, source_ref AS ref, name_norm, email_norm,
                   phone_norm, city_norm, current_employer AS employer
            FROM duta.candidates
            WHERE name_norm LIKE %(last)s
            """,
            {"last": "%" + last},
        ).fetchall()

    best = None  # (tier_rank, rule, kind, ref, name)
    tier_rank = {"exact": 0, "fuzzy": 1, "borderline": 2}
    for cand in candidates:
        hit = evaluate_rules(app, cand)
        if hit is None:
            continue
        tier, rule = hit
        key = (tier_rank[tier], rule, cand["kind"], cand["ref"], cand.get("name_norm"))
        if best is None or key < best:
            best = key

    if best is None:
        return None
    rank, rule, kind, ref, matched_name = best
    evidence = {"rule": rule, "matched_kind": kind, "matched_ref": ref, "matched_name": matched_name}

    if rank <= 1:  # exact or corroborated fuzzy -> DUPLICATE, non-destructive link
        conn.execute(
            """
            INSERT INTO duta.duplicate_links (application_id, matched_kind, matched_ref, rule)
            VALUES (%s, %s, %s, %s) ON CONFLICT (application_id) DO NOTHING
            """,
            (app_row["id"], kind, ref, rule),
        )
        return TriageResult(
            decision=TriageDecision.DUPLICATE,
            duplicate_of=ref,
            rationale="{} matched existing {} {}".format(rule, kind, ref),
            evidence=evidence,
            engine=ENGINE_VERSION,
            confidence=1.0,
            cost_usd=0.0,
        )
    return TriageResult(  # borderline: humans link identities, not trigram scores
        decision=TriageDecision.REVIEW,
        rationale="possible duplicate of {} {} (name similarity, no corroborating signal)".format(kind, ref),
        evidence=evidence,
        engine=ENGINE_VERSION,
        cost_usd=0.0,
    )
