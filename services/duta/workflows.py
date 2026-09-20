from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from .activities import ingest_jobwire, ingest_kestrel, sync_talentbase, triage_application

_RETRY = RetryPolicy(initial_interval=timedelta(seconds=2), backoff_coefficient=2.0,
                     maximum_interval=timedelta(minutes=1), maximum_attempts=5)


async def _triage_all(new_ids: list) -> dict:
    decisions: dict = {}
    for app_id in new_ids:
        decision = await workflow.execute_activity(
            triage_application,
            app_id,
            start_to_close_timeout=timedelta(minutes=1),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )
        decisions[decision] = decisions.get(decision, 0) + 1
    return decisions


@workflow.defn
class KestrelSyncWorkflow:
    """One durable sync pass: ingest new Kestrel applications, then triage each of them.

    A worker crash at any point resumes from history — completed triage activities are not
    re-run, and the ones that do re-run hit idempotent persistence (no duplicate decisions,
    no duplicate queue items, by schema constraint rather than by care)."""

    @workflow.run
    async def run(self, deep: bool = False) -> dict:
        new_ids = await workflow.execute_activity(
            ingest_kestrel,
            deep,
            start_to_close_timeout=timedelta(minutes=10),
            heartbeat_timeout=timedelta(minutes=2),
            retry_policy=_RETRY,
        )
        decisions = await _triage_all(new_ids)
        return {"ingested": len(new_ids), "decisions": decisions}


@workflow.defn
class TalentbaseSyncWorkflow:
    """Requisitions + candidates from the CRM replica into the canonical store (ADR-0001)."""

    @workflow.run
    async def run(self, deep: bool = False) -> dict:
        return await workflow.execute_activity(
            sync_talentbase,
            deep,
            start_to_close_timeout=timedelta(minutes=15),
            heartbeat_timeout=timedelta(minutes=2),
            retry_policy=_RETRY,
        )


@workflow.defn
class JobwireImportWorkflow:
    """Process the JobWire dropzone; every new row is triaged like any other application."""

    @workflow.run
    async def run(self) -> dict:
        new_ids = await workflow.execute_activity(
            ingest_jobwire,
            start_to_close_timeout=timedelta(minutes=10),
            heartbeat_timeout=timedelta(minutes=2),
            retry_policy=_RETRY,
        )
        decisions = await _triage_all(new_ids)
        return {"ingested": len(new_ids), "decisions": decisions}
