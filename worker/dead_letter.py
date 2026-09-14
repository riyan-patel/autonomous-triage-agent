"""Dead-letter visibility (docs/ARCHITECTURE.md section 4: "permanent
failures go to a dead-letter queue for inspection"). RQ already parks a
job that exhausts its retries (the Retry policy webhook-ingress sets at
enqueue time) in a per-queue FailedJobRegistry automatically - this module
just makes that queryable in a structured way instead of requiring
someone to poke at Redis directly.
"""

from dataclasses import dataclass

from redis import Redis
from rq import Queue
from rq.registry import FailedJobRegistry

from .config import settings


@dataclass
class DeadLetter:
    job_id: str
    description: str
    exc_info: str | None
    enqueued_at: str | None


def list_dead_letters(connection: Redis, queue_name: str | None = None) -> list[DeadLetter]:
    queue = Queue(queue_name or settings.triage_queue_name, connection=connection)
    registry = FailedJobRegistry(queue=queue)

    dead_letters = []
    for job_id in registry.get_job_ids():
        job = queue.fetch_job(job_id)
        if job is None:
            continue
        result = job.latest_result()
        dead_letters.append(
            DeadLetter(
                job_id=job.id,
                description=job.description or "",
                exc_info=result.exc_string if result else None,
                enqueued_at=job.enqueued_at.isoformat() if job.enqueued_at else None,
            )
        )
    return dead_letters
