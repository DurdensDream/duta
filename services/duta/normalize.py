"""Identity normalization — pure functions, exhaustively unit-tested.

Every dedup decision is explainable as "these two values normalized to the same thing"; this
module is where "the same thing" is defined, and nowhere else.
"""

import re
import unicodedata

# Kept deliberately small: expansions we have positive evidence for in the corpus. A missing
# nickname degrades to the fuzzy/borderline path (a human), never to a wrong auto-link.
NICKNAMES = {
    "rob": "robert", "bob": "robert", "jen": "jennifer", "mike": "michael", "tom": "thomas",
    "dave": "david", "dan": "daniel", "kev": "kevin", "sam": "samuel", "pete": "peter",
    "jim": "james", "beth": "elizabeth", "liz": "elizabeth", "chris": "christopher",
}

_CITY_HINTS = {
    "cbus": "columbus", "columbus": "columbus",
    "cle": "cleveland", "cleveland": "cleveland",
    "cincy": "cincinnati", "cincinnati": "cincinnati",
    "chicago": "chicago",
    "atx": "austin", "austin": "austin",
    "remote": "remote", "wfh": "remote", "anywhere": "remote",
}


def norm_email(email: str | None) -> str | None:
    if not email:
        return None
    e = email.strip().lower()
    return e or None


def norm_phone(phone: str | None) -> str | None:
    """Reduce any of the corpus's 5+ phone spellings to a bare 10-digit US number.

    '(614) 555-0142' / '614.555.0142' / '+1 614 555 0142' / '6145550142' / '614 555 0142 x22'
    all normalize to '6145550142'. Anything that can't yield 10 plausible digits returns None —
    unknown beats wrong for an identity signal.
    """
    if not phone:
        return None
    digits = re.sub(r"\D", "", phone)
    if len(digits) >= 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) >= 10:
        digits = digits[:10]  # trailing extension digits ('x22') fall off
        return digits
    return None


def norm_name(name: str | None) -> str | None:
    """Lowercase, deaccent, strip punctuation, expand known nicknames on the first token."""
    if not name:
        return None
    n = unicodedata.normalize("NFKD", name)
    n = "".join(ch for ch in n if not unicodedata.combining(ch))
    n = re.sub(r"[^a-z ]", " ", n.lower())
    tokens = n.split()
    if not tokens:
        return None
    tokens[0] = NICKNAMES.get(tokens[0], tokens[0])
    return " ".join(tokens)


def norm_city(raw: str | None) -> str | None:
    if not raw:
        return None
    r = re.sub(r"[^a-z ]", " ", raw.lower())
    for hint, city in _CITY_HINTS.items():
        if hint in r:
            return city
    return r.strip() or None


def trigram_similarity(a: str, b: str) -> float:
    """Jaccard similarity over character trigrams of padded strings (0.0 - 1.0)."""
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0

    def grams(s):
        s = "  " + s + " "
        return {s[i:i + 3] for i in range(len(s) - 2)}

    ga, gb = grams(a), grams(b)
    return len(ga & gb) / len(ga | gb)
