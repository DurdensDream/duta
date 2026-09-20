from duta.normalize import norm_city, norm_email, norm_name, norm_phone, trigram_similarity


def test_phone_formats_from_the_corpus_all_agree():
    spellings = ["(614) 555-0142", "614-555-0142", "614.555.0142", "+1 614 555 0142",
                 "6145550142", "614 555 0142 x22", "614 555 0142 (cell)"]
    assert {norm_phone(p) for p in spellings} == {"6145550142"}


def test_phone_garbage_is_none_not_wrong():
    assert norm_phone("call me") is None
    assert norm_phone("555-01") is None
    assert norm_phone(None) is None
    assert norm_phone("") is None


def test_email_normalization():
    assert norm_email("  Rob.Smith@Gmail.COM ") == "rob.smith@gmail.com"
    assert norm_email("") is None


def test_nickname_expansion_links_variants():
    assert norm_name("Rob Smith") == norm_name("Robert Smith")
    assert norm_name("Mike  O'Brien") == "michael o brien"


def test_accents_fold():
    assert norm_name("José Muñoz") == "jose munoz"
    assert norm_name("Zoë Köhler") == "zoe kohler"


def test_city_variants_from_discovery_memo():
    for raw in ("Columbus, OH", "columbus", "CBUS/remote", "Columbus Ohio"):
        assert norm_city(raw) == "columbus"
    assert norm_city("WFH") == "remote"
    assert norm_city(None) is None


def test_trigram_similarity_bounds():
    assert trigram_similarity("robert smith", "robert smith") == 1.0
    assert trigram_similarity("robert smith", "elena petrov") < 0.2
    assert trigram_similarity("", "x") == 0.0
