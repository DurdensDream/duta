"""ADR-0005 enforcement: construct source rows with every known EEO field populated, run the
full translation path, and assert none of those values survive anywhere in the canonical output."""

import json

from duta.models import EEO_FIELD_DENYLIST, CanonicalApplication, CanonicalCandidate
from duta.translate import from_talentbase_candidate

EEO_VALUES = {
    "gender": "XX-SENTINEL-GENDER",
    "ethnicity": "XX-SENTINEL-ETHNICITY",
    "date_of_birth": "1990-01-01",
    "veteran_status": "XX-SENTINEL-VET",
    "disability_status": "XX-SENTINEL-DIS",
    "marital_status": "XX-SENTINEL-MARITAL",
}


def test_canonical_models_have_no_denylisted_fields():
    for model in (CanonicalApplication, CanonicalCandidate):
        overlap = set(model.model_fields) & EEO_FIELD_DENYLIST
        assert not overlap, "{} carries denylisted fields: {}".format(model.__name__, overlap)


def test_translation_drops_eeo_even_if_selected():
    # Simulate the failure mode the allowlist exists for: someone widens the SQL SELECT and the
    # raw row now carries EEO columns. Translation must still produce an EEO-free canonical row.
    row = {
        "candidate_id": 512,
        "full_name": "Robert Smith",
        "email": "rob@example.com",
        "phone": "(614) 555-0101",
        "city_raw": "CBUS/remote",
        "state": "OH",
        "current_title": "Backend Engineer",
        "current_employer": "Nationwide",
        "skills_txt": "Java; Kafka",
        "work_auth": "US Citizen",
        **EEO_VALUES,
    }
    canon = from_talentbase_candidate(row)
    blob = json.dumps(canon.model_dump(), default=str)
    for key, value in EEO_VALUES.items():
        assert value not in blob, "EEO value for '{}' leaked into canonical output".format(key)
    assert canon.source_ref == "TB-CAND-000512"
