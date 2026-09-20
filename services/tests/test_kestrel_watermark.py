"""The vendor's timestamp jank, pinned by tests (see field-notes 2026-07-27)."""

from datetime import timezone

from duta.connectors.kestrel import KestrelClient, max_updated_utc
from duta.translate import parse_vendor_ts


def test_three_tz_spellings_parse_to_instants():
    z = parse_vendor_ts("2026-07-27T10:40:00Z")
    off0 = parse_vendor_ts("2026-07-27T10:40:00+00:00")
    off5 = parse_vendor_ts("2026-07-27T05:40:00-05:00")
    assert z == off0 == off5  # same instant, three spellings


def test_string_order_lies_but_instants_do_not():
    a = "2026-07-27T05:40:00-05:00"  # 10:40 UTC
    b = "2026-07-27T06:50:00Z"       # 06:50 UTC
    assert a < b  # the vendor's comparison (wrong)
    assert parse_vendor_ts(a) > parse_vendor_ts(b)  # reality


def test_max_updated_utc_picks_true_latest():
    records = [{"updatedAt": "2026-07-27T06:50:00Z"},
               {"updatedAt": "2026-07-27T05:40:00-05:00"},  # true max (10:40Z)
               {"updatedAt": "garbage"}]
    best = max_updated_utc(records)
    assert best.astimezone(timezone.utc).hour == 10


def test_next_watermark_rewinds_and_spells_z():
    best = parse_vendor_ts("2026-07-27T12:00:00Z")
    wm = KestrelClient.next_watermark(best)
    assert wm == "2026-07-27T06:00:00Z"  # 6h overlap, Z spelling
    assert KestrelClient.next_watermark(None) is None
