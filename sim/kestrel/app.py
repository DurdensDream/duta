"""Kestrel ATS — staged vendor API.

Reproduces the vendor behaviors found in discovery (docs/engagement/00-discovery-memo.md §4):
OAuth2 client-credentials, a hard 60 req/min quota with Retry-After 429s, intermittent 5xx,
cursor pagination, and one authentic vendor bug: pages are ordered by the *string* value of
`updatedAt`, which is emitted in three timezone spellings — so page order is NOT chronological.
Clients that trust page order will corrupt their watermarks; ours must parse timestamps.

Admin endpoints (things a real vendor wouldn't give you — used to stage demos and drills):
  POST /admin/release   {"batch": N}                 -> new applications "arrive"
  POST /admin/chaos     {"error_rate": 0.02, "latency_ms": 0}
"""

import base64
import json
import math
import os
import random
import time
import uuid

from fastapi import FastAPI, Header, HTTPException, Query, Response
from pydantic import BaseModel

app = FastAPI(title="Kestrel ATS (staged)")

STORE_PATH = os.environ.get("KESTREL_STORE", "/data/kestrel_store.json")
CLIENT_ID = os.environ.get("KESTREL_CLIENT_ID", "meridian-pilot")
CLIENT_SECRET = os.environ.get("KESTREL_CLIENT_SECRET", "kestrel-pilot-secret-2026")
RATE_CAPACITY = int(os.environ.get("KESTREL_RATE_CAPACITY", "60"))  # 60 req/min, per discovery
RATE_REFILL_PER_SEC = RATE_CAPACITY / 60.0

state = {
    "apps": [],
    "release": 0,               # highest releaseBatch currently visible
    "error_rate": float(os.environ.get("KESTREL_ERROR_RATE", "0.02")),
    "latency_ms": 0,
    "tokens": {},               # bearer -> expiry epoch
    "bucket": {"level": float(RATE_CAPACITY), "at": time.monotonic()},
    "rng": random.Random(1337),
}


@app.on_event("startup")
def load_store():
    with open(STORE_PATH, encoding="utf-8") as f:
        data = json.load(f)
    # The vendor bug, faithfully staged: string sort on mixed-timezone timestamps.
    state["apps"] = sorted(data["applications"], key=lambda a: (a["updatedAt"], a["applicationId"]))


# ------------------------------------------------------------------ auth

class TokenForm(BaseModel):
    grant_type: str
    client_id: str
    client_secret: str


@app.post("/oauth/token")
def token(form: TokenForm):
    if form.grant_type != "client_credentials":
        raise HTTPException(400, {"error": "unsupported_grant_type"})
    if form.client_id != CLIENT_ID or form.client_secret != CLIENT_SECRET:
        raise HTTPException(401, {"error": "invalid_client"})
    tok = uuid.uuid4().hex
    state["tokens"][tok] = time.time() + 3600
    return {"access_token": tok, "token_type": "Bearer", "expires_in": 3600}


def require_auth(authorization):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, {"error": "missing_bearer"})
    tok = authorization.split(" ", 1)[1]
    exp = state["tokens"].get(tok)
    if not exp or exp < time.time():
        raise HTTPException(401, {"error": "invalid_or_expired_token"})


def take_rate_token(response: Response):
    b = state["bucket"]
    now = time.monotonic()
    b["level"] = min(RATE_CAPACITY, b["level"] + (now - b["at"]) * RATE_REFILL_PER_SEC)
    b["at"] = now
    if b["level"] < 1.0:
        retry = math.ceil((1.0 - b["level"]) / RATE_REFILL_PER_SEC)
        raise HTTPException(429, {"error": "rate_limited"}, headers={"Retry-After": str(retry)})
    b["level"] -= 1.0
    response.headers["X-RateLimit-Remaining"] = str(int(b["level"]))


# ------------------------------------------------------------------ applications

def enc_cursor(offset):
    return base64.urlsafe_b64encode("o:{}".format(offset).encode()).decode()


def dec_cursor(cursor):
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        return int(raw.split(":", 1)[1])
    except Exception:
        raise HTTPException(400, {"error": "invalid_cursor"})


@app.get("/v2/applications")
def applications(response: Response,
                 authorization: str = Header(default=None),
                 cursor: str = Query(default=None),
                 limit: int = Query(default=50, le=50, ge=1),
                 updated_since: str = Query(default=None)):
    require_auth(authorization)
    take_rate_token(response)

    if state["latency_ms"]:
        time.sleep(state["latency_ms"] / 1000.0)
    if state["rng"].random() < state["error_rate"]:
        raise HTTPException(500, {"error": "internal_error", "incident": uuid.uuid4().hex[:8]})

    visible = [a for a in state["apps"] if a.get("releaseBatch", 0) <= state["release"]]
    if updated_since:
        # vendor compares raw strings here too; >= so clients re-see boundary records (at-least-once)
        visible = [a for a in visible if a["updatedAt"] >= updated_since]

    offset = dec_cursor(cursor) if cursor else 0
    page = visible[offset:offset + limit]
    out = []
    for a in page:
        a = dict(a)
        a.pop("releaseBatch", None)  # internal staging field, not part of the vendor payload
        out.append(a)
    next_cursor = enc_cursor(offset + limit) if offset + limit < len(visible) else None
    return {"data": out, "nextCursor": next_cursor, "total": len(visible)}


# ------------------------------------------------------------------ admin (staging controls)

class ReleaseForm(BaseModel):
    batch: int


@app.post("/admin/release")
def release(form: ReleaseForm):
    state["release"] = max(state["release"], form.batch)
    now_visible = sum(1 for a in state["apps"] if a.get("releaseBatch", 0) <= state["release"])
    return {"release": state["release"], "visible_applications": now_visible}


class ChaosForm(BaseModel):
    error_rate: float = None
    latency_ms: int = None


@app.post("/admin/chaos")
def chaos(form: ChaosForm):
    if form.error_rate is not None:
        state["error_rate"] = max(0.0, min(1.0, form.error_rate))
    if form.latency_ms is not None:
        state["latency_ms"] = max(0, form.latency_ms)
    return {"error_rate": state["error_rate"], "latency_ms": state["latency_ms"]}


@app.get("/health")
def health():
    return {"status": "ok", "applications_loaded": len(state["apps"]), "release": state["release"]}
