"""Temporal activities — all I/O lives here; workflows stay deterministic."""

from temporalio import activity

from . import config
from . import db as dbm
from .connectors import jobwire, talentbase
from .connectors.kestrel import KestrelClient, max_updated_utc
from .translate import (from_jobwire, from_kestrel, from_talentbase_candidate,
                        from_talentbase_requisition)
from .triage import dedupe
from .triage.engine import triage


@activity.defn
def ingest_kestrel(deep: bool = False) -> list[int]:
    """Pull everything Kestrel has past the (rewound) watermark; upsert; return NEW app ids.

    Safe to retry from scratch at any point: upserts are no-ops on replay, and the watermark
    only moves after a fully successful pass.

    deep=True ignores the watermark and re-scans the vendor completely. Field note 2026-07-27:
    Kestrel compares `updated_since` as a raw string across mixed tz spellings, so a -05:00
    record whose UTC instant is NEWER than the watermark can still be excluded — no fixed
    overlap window is provably safe. Deep reconciliation on a schedule is the correctness
    backstop; idempotent upserts make it cost only API calls.
    """
    client = KestrelClient()
    with dbm.connect() as conn:
        watermark = None if deep else dbm.get_watermark(conn, "kestrel")
        records = []
        new_ids = []
        for rec in client.fetch_since(watermark):
            records.append(rec)
            app_id, inserted = dbm.upsert_application(conn, from_kestrel(rec))
            if inserted:
                new_ids.append(app_id)
            if len(records) % 50 == 0:
                activity.heartbeat(len(records))
        next_wm = KestrelClient.next_watermark(max_updated_utc(records))
        if next_wm:
            dbm.set_watermark(conn, "kestrel", next_wm)
        dbm.audit(conn, "system:kestrel-sync", "sync_completed",
                  detail={"mode": "deep" if deep else "incremental",
                          "fetched": len(records), "new": len(new_ids),
                          "from_watermark": watermark, "next_watermark": next_wm})
    return new_ids


@activity.defn
def sync_talentbase(deep: bool = False) -> dict:
    """Read-only CRM sync: requisitions (hash full-scan) + candidates (watermark, deep=full)."""
    with talentbase.connect_crm() as crm, dbm.connect() as conn:
        req_rows = talentbase.fetch_requisitions(crm)
        req_changed = sum(1 for r in req_rows
                          if dbm.upsert_requisition(conn, from_talentbase_requisition(r)))
        watermark = None if deep else dbm.get_watermark(conn, "talentbase:candidates")
        cand_rows = talentbase.fetch_candidates(crm, watermark, deep=deep)
        cand_changed = 0
        max_updated = None
        for i, row in enumerate(cand_rows):
            if dbm.upsert_candidate(conn, from_talentbase_candidate(row)):
                cand_changed += 1
            if row.get("updated_at") and (max_updated is None or row["updated_at"] > max_updated):
                max_updated = row["updated_at"]
            if i % 500 == 0:
                activity.heartbeat(i)
        if max_updated is not None:
            dbm.set_watermark(conn, "talentbase:candidates", max_updated.isoformat())
        detail = {"mode": "deep" if deep or watermark is None else "incremental",
                  "requisitions_seen": len(req_rows), "requisitions_changed": req_changed,
                  "candidates_seen": len(cand_rows), "candidates_changed": cand_changed}
        dbm.audit(conn, "system:talentbase-sync", "sync_completed", detail=detail)
    return detail


@activity.defn
def ingest_jobwire() -> list[int]:
    """Process every drop in the dropzone. Re-processing is a no-op (idempotent refs)."""
    new_ids = []
    reports = []
    with dbm.connect() as conn:
        for path in jobwire.list_drops(config.JOBWIRE_DROPZONE):
            rows, report = jobwire.read_drop(path)
            fresh = 0
            for mapped in rows:
                canon = from_jobwire(mapped, mapped["source_ref"], mapped["submitted_at"])
                app_id, inserted = dbm.upsert_application(conn, canon)
                if inserted:
                    new_ids.append(app_id)
                    fresh += 1
            report["new"] = fresh
            reports.append(report)
            activity.heartbeat(path.name)
        dbm.audit(conn, "system:jobwire-import", "sync_completed", detail={"files": reports})
    return new_ids


@activity.defn
def triage_application(application_id: int) -> str:
    """Triage one application. Precedence mirrors the labeling rubric: dedup runs before any
    match judgment. Idempotent: an already-decided application is left untouched."""
    with dbm.connect() as conn:
        row = conn.execute("SELECT * FROM duta.applications WHERE id = %s",
                           (application_id,)).fetchone()
        if row is None:
            raise RuntimeError("application {} not found".format(application_id))
        result = dedupe.find_duplicate(conn, row) or triage(row)
        if dbm.save_triage(conn, application_id, result):
            dbm.audit(conn, "system:triage", "triage_decided", subject=row["source_ref"],
                      detail={"decision": result.decision.value, "engine": result.engine})
    return result.decision.value
