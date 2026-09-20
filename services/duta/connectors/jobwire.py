"""JobWire nightly CSV feed connector.

The feed is what it is (discovery memo §4): latin-1 encoded, header names drift between drops,
duplicate rows occur inside a single drop, and dates arrive in three formats — two of which are
ambiguous with each other. Defenses, in order:

- encoding: try UTF-8 strictly, fall back to latin-1 (which never throws) — the drop that IS
  valid UTF-8 still reads correctly, the latin-1 ones stop being mojibake.
- headers: normalized header names map onto canonical roles; an unmapped column is logged and
  dropped (allowlist thinking again), a missing required column fails the file loudly.
- dates: per-FILE format detection — the format that parses the most rows wins (a single row
  like 03/04/2026 is ambiguous; a file of them almost never is). Unparseable dates become NULL
  rather than wrong instants.
- duplicate rows: NOT handled here. Each row gets its positional source_ref and ingests;
  the dedup tier catches identical humans (ADR-0003). Idempotency handles re-processing:
  re-reading a whole file is a no-op by the (source, source_ref) constraint.
"""

import csv
import io
import re
from datetime import datetime, timezone
from pathlib import Path

HEADER_ROLES = {
    "fullname": "name", "name": "name",
    "email": "email", "emailaddress": "email",
    "phone": "phone", "phonenumber": "phone",
    "jobref": "position_code",
    "applied": "applied", "appliedon": "applied", "date": "applied",
    "location": "location", "city": "location",
    "summary": "resume", "resumesummary": "resume", "notes": "resume",
}
REQUIRED_ROLES = {"name", "email"}
DATE_FORMATS = ("%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y")


def _norm_header(h: str) -> str:
    return re.sub(r"[^a-z]", "", h.lower())


def read_drop(path: Path) -> tuple[list[dict], dict]:
    """Parse one drop file. Returns (rows as role-mapped dicts + source_ref, file report)."""
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
        encoding = "utf-8"
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
        encoding = "latin-1"

    reader = csv.reader(io.StringIO(text))
    header = next(reader)
    roles = [HEADER_ROLES.get(_norm_header(h)) for h in header]
    mapped_roles = {r for r in roles if r}
    if not REQUIRED_ROLES.issubset(mapped_roles):
        raise ValueError("{}: unmapped required columns (got header {})".format(path.name, header))

    day = path.stem.split("_")[-1]  # jobwire_20260724 -> 20260724
    rows = []
    for i, raw_row in enumerate(reader, start=1):
        mapped = {}
        for role, value in zip(roles, raw_row):
            if role:
                mapped[role] = value.strip()
        mapped["source_ref"] = "JW-{}-{:04d}".format(day, i)
        rows.append(mapped)

    fmt, parsed, failed = _detect_date_format([r.get("applied", "") for r in rows])
    for r in rows:
        r["submitted_at"] = _parse_date(r.get("applied", ""), fmt)

    report = {"file": path.name, "encoding": encoding, "rows": len(rows),
              "date_format": fmt, "dates_parsed": parsed, "dates_failed": failed,
              "unmapped_headers": [h for h, ro in zip(header, roles) if ro is None]}
    return rows, report


def _detect_date_format(values: list[str]) -> tuple[str | None, int, int]:
    best, best_count = None, -1
    for fmt in DATE_FORMATS:
        count = sum(1 for v in values if _try_parse(v, fmt))
        if count > best_count:
            best, best_count = fmt, count
    failed = sum(1 for v in values if v and not _try_parse(v, best))
    return best, best_count, failed


def _try_parse(value: str, fmt: str) -> bool:
    try:
        datetime.strptime(value, fmt)
        return True
    except (ValueError, TypeError):
        return False


def _parse_date(value: str, fmt: str | None):
    if not value or not fmt:
        return None
    try:
        return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
    except ValueError:
        return None  # planted chaos like 31/06/2026 lands here: NULL beats a wrong instant


def list_drops(dropzone: str) -> list[Path]:
    return sorted(Path(dropzone).glob("jobwire_*.csv"))
