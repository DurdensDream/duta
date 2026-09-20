import time

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from temporalio.client import Client

from . import config
from . import db as dbm

app = FastAPI(title="Duta — Meridian triage pilot")

_temporal: dict = {"client": None}

# Humans may take negative decisions; the system may not (ADR-0004). The asymmetry is the point.
HUMAN_DECISIONS = {"ADVANCE", "NEEDS_INFO", "DUPLICATE", "REJECT"}


async def temporal_client() -> Client:
    if _temporal["client"] is None:
        _temporal["client"] = await Client.connect(config.TEMPORAL_ADDRESS)
    return _temporal["client"]


@app.get("/health")
def health():
    with dbm.connect() as conn:
        conn.execute("SELECT 1")
    return {"status": "ok"}


@app.post("/api/sync/kestrel", status_code=202)
async def trigger_kestrel_sync(deep: bool = False):
    """deep=true bypasses the watermark: full reconciliation scan (see field-notes 2026-07-27)."""
    client = await temporal_client()
    workflow_id = "kestrel-sync-{}".format(int(time.time()))
    await client.start_workflow("KestrelSyncWorkflow", deep, id=workflow_id,
                                task_queue=config.TEMPORAL_TASK_QUEUE)
    return {"workflow_id": workflow_id, "mode": "deep" if deep else "incremental"}


@app.post("/api/sync/talentbase", status_code=202)
async def trigger_talentbase_sync(deep: bool = False):
    client = await temporal_client()
    workflow_id = "talentbase-sync-{}".format(int(time.time()))
    await client.start_workflow("TalentbaseSyncWorkflow", deep, id=workflow_id,
                                task_queue=config.TEMPORAL_TASK_QUEUE)
    return {"workflow_id": workflow_id, "mode": "deep" if deep else "incremental"}


@app.post("/api/sync/jobwire", status_code=202)
async def trigger_jobwire_import():
    client = await temporal_client()
    workflow_id = "jobwire-import-{}".format(int(time.time()))
    await client.start_workflow("JobwireImportWorkflow", id=workflow_id,
                                task_queue=config.TEMPORAL_TASK_QUEUE)
    return {"workflow_id": workflow_id}


@app.get("/api/sync/{workflow_id}")
async def sync_status(workflow_id: str):
    client = await temporal_client()
    handle = client.get_workflow_handle(workflow_id)
    desc = await handle.describe()
    out = {"workflow_id": workflow_id,
           "status": desc.status.name if desc.status else "UNKNOWN"}
    if desc.status and desc.status.name == "COMPLETED":
        out["result"] = await handle.result()
    return out


@app.get("/api/queue")
def review_queue(status: str = "open", limit: int = 100):
    with dbm.connect() as conn:
        rows = conn.execute(
            """
            SELECT q.id, q.application_id, a.source, a.source_ref, a.candidate_name,
                   a.position_title, q.reason, q.status, q.created_at
            FROM duta.review_queue q
            JOIN duta.applications a ON a.id = q.application_id
            WHERE q.status = %s
            ORDER BY q.created_at ASC       -- oldest first, never score-ordered (ADR-0004)
            LIMIT %s
            """,
            (status, limit),
        ).fetchall()
    return {"count": len(rows), "items": rows}


@app.get("/api/applications/{application_id}")
def application_detail(application_id: int):
    with dbm.connect() as conn:
        application = conn.execute("SELECT * FROM duta.applications WHERE id = %s",
                                   (application_id,)).fetchone()
        if application is None:
            raise HTTPException(404, "application not found")
        triage = conn.execute("SELECT * FROM duta.triage_results WHERE application_id = %s",
                              (application_id,)).fetchone()
        review = conn.execute("SELECT * FROM duta.review_queue WHERE application_id = %s",
                              (application_id,)).fetchone()
    return {"application": application, "triage": triage, "review": review}


class HumanDecision(BaseModel):
    decision: str
    actor: str
    note: str = ""


@app.post("/api/queue/{item_id}/decide")
def decide(item_id: int, body: HumanDecision):
    if body.decision not in HUMAN_DECISIONS:
        raise HTTPException(422, "decision must be one of {}".format(sorted(HUMAN_DECISIONS)))
    with dbm.connect() as conn:
        row = conn.execute(
            """
            UPDATE duta.review_queue
            SET status = 'decided', human_decision = %s, decided_by = %s, decided_at = now()
            WHERE id = %s AND status = 'open'
            RETURNING application_id
            """,
            (body.decision, body.actor, item_id),
        ).fetchone()
        if row is None:
            raise HTTPException(409, "queue item not found or already decided")
        dbm.audit(conn, body.actor, "human_decision", subject=str(row["application_id"]),
                  detail={"decision": body.decision, "note": body.note, "queue_item": item_id})
    return {"ok": True, "application_id": row["application_id"]}


@app.get("/api/stats")
def stats():
    with dbm.connect() as conn:
        by_decision = {r["decision"]: r["n"] for r in conn.execute(
            "SELECT decision, count(*) AS n FROM duta.triage_results GROUP BY decision").fetchall()}
        applications = conn.execute("SELECT count(*) AS n FROM duta.applications").fetchone()["n"]
        open_reviews = conn.execute(
            "SELECT count(*) AS n FROM duta.review_queue WHERE status = 'open'").fetchone()["n"]
    triaged = sum(by_decision.values())
    auto = sum(by_decision.get(d, 0) for d in ("ADVANCE", "NEEDS_INFO", "DUPLICATE"))
    return {
        "applications": applications,
        "triaged": triaged,
        "decisions": by_decision,
        "auto_resolution_rate": round(auto / triaged, 4) if triaged else None,
        "open_reviews": open_reviews,
    }
