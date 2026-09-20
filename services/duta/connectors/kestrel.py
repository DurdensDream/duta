"""Kestrel ATS client.

Vendor behaviors this client is written against (verified on the staged vendor):
- 60 req/min quota -> 429 + Retry-After: honored, not retried blind.
- Intermittent 500s -> raised to the caller; the Temporal activity retry policy owns backoff.
- Page order is by RAW STRING of updatedAt across mixed tz spellings -> chronological order is a
  lie. We parse every timestamp, track the max UTC instant, and rewind the watermark by an
  overlap window on the next pull (config.KESTREL_WATERMARK_OVERLAP_HOURS); schema-level
  idempotency (duta.applications unique key) makes the re-reads free.
"""

import time
from datetime import timedelta, timezone

import httpx

from .. import config
from ..translate import parse_vendor_ts


class KestrelClient:
    def __init__(self):
        self._token = None
        self._client = httpx.Client(base_url=config.KESTREL_BASE_URL, timeout=15.0)

    def _auth(self) -> str:
        if self._token:
            return self._token
        r = self._client.post("/oauth/token", json={
            "grant_type": "client_credentials",
            "client_id": config.KESTREL_CLIENT_ID,
            "client_secret": config.KESTREL_CLIENT_SECRET,
        })
        r.raise_for_status()
        self._token = r.json()["access_token"]
        return self._token

    def _get(self, params: dict) -> dict:
        for attempt in range(6):
            r = self._client.get("/v2/applications", params=params,
                                 headers={"Authorization": "Bearer " + self._auth()})
            if r.status_code == 401:
                self._token = None  # expired mid-run; refresh once
                continue
            if r.status_code == 429:
                wait = int(r.headers.get("Retry-After", "2"))
                time.sleep(min(wait, 30))
                continue
            r.raise_for_status()  # 5xx -> caller's retry policy decides
            return r.json()
        raise RuntimeError("kestrel: quota-throttled beyond retry budget")

    def fetch_since(self, updated_since: str | None):
        """Yield raw application records; caller translates and upserts."""
        params: dict = {"limit": 50}
        if updated_since:
            params["updated_since"] = updated_since
        cursor = None
        while True:
            if cursor:
                params["cursor"] = cursor
            page = self._get(dict(params))
            for rec in page["data"]:
                yield rec
            cursor = page.get("nextCursor")
            if not cursor:
                return

    @staticmethod
    def next_watermark(records_max_utc) -> str | None:
        """Watermark = max parsed instant minus overlap, spelled as Z (vendor string-compares)."""
        if not records_max_utc:
            return None
        rewound = records_max_utc.astimezone(timezone.utc) - timedelta(
            hours=config.KESTREL_WATERMARK_OVERLAP_HOURS)
        return rewound.strftime("%Y-%m-%dT%H:%M:%SZ")


def max_updated_utc(records) -> object:
    best = None
    for rec in records:
        ts = parse_vendor_ts(rec.get("updatedAt"))
        if ts and (best is None or ts > best):
            best = ts
    return best
