"""Pure-rule tests for ADR-0003. Every tier, both directions, and the precedence."""

from duta.triage.dedupe import evaluate_rules

BASE = {"email_norm": "rob.smith@gmail.com", "phone_norm": "6145550142",
        "name_norm": "robert smith", "city_norm": "columbus", "employer": None}


def other(**kw):
    d = {"ref": "TB-CAND-000001", "email_norm": None, "phone_norm": None,
         "name_norm": None, "city_norm": None, "employer": None}
    d.update(kw)
    return d


def test_email_exact_wins():
    assert evaluate_rules(BASE, other(email_norm="rob.smith@gmail.com")) == ("exact", "email_exact")


def test_phone_exact():
    assert evaluate_rules(BASE, other(phone_norm="6145550142")) == ("exact", "phone_exact")


def test_fuzzy_needs_corroboration_city_alone_is_borderline():
    hit = evaluate_rules(BASE, other(name_norm="robert smith", city_norm="columbus"))
    assert hit == ("borderline", "fuzzy_name_only")


def test_fuzzy_corroborated_city_plus_employer():
    app = dict(BASE, employer="Nationwide", email_norm=None, phone_norm=None)
    hit = evaluate_rules(app, other(name_norm="robert smith", city_norm="columbus",
                                    employer="Nationwide"))
    assert hit == ("fuzzy", "fuzzy_corroborated")


def test_name_variant_only_is_borderline_never_auto_link():
    app = dict(BASE, email_norm=None, phone_norm=None)
    hit = evaluate_rules(app, other(name_norm="robert smith", city_norm="austin"))
    assert hit == ("borderline", "fuzzy_name_only")


def test_different_people_no_hit():
    assert evaluate_rules(BASE, other(name_norm="elena petrov",
                                      email_norm="elena@x.com", phone_norm="3125550000")) is None


def test_missing_identity_fields_never_match_on_none():
    app = {"email_norm": None, "phone_norm": None, "name_norm": None, "city_norm": None,
           "employer": None}
    assert evaluate_rules(app, other(email_norm=None, phone_norm=None)) is None
