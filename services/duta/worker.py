import asyncio
import concurrent.futures

from temporalio.client import Client
from temporalio.worker import Worker

from . import config
from .activities import ingest_jobwire, ingest_kestrel, sync_talentbase, triage_application
from .workflows import JobwireImportWorkflow, KestrelSyncWorkflow, TalentbaseSyncWorkflow


async def main():
    client = None
    for attempt in range(30):
        try:
            client = await Client.connect(config.TEMPORAL_ADDRESS)
            break
        except Exception as exc:  # temporal boots slower than we do
            print("worker: temporal not ready ({}); retry {}/30".format(exc, attempt + 1), flush=True)
            await asyncio.sleep(3)
    if client is None:
        raise SystemExit("worker: could not reach temporal at " + config.TEMPORAL_ADDRESS)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        worker = Worker(
            client,
            task_queue=config.TEMPORAL_TASK_QUEUE,
            workflows=[KestrelSyncWorkflow, TalentbaseSyncWorkflow, JobwireImportWorkflow],
            activities=[ingest_kestrel, sync_talentbase, ingest_jobwire, triage_application],
            activity_executor=executor,
        )
        print("worker: polling task queue '{}'".format(config.TEMPORAL_TASK_QUEUE), flush=True)
        await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
