from functools import lru_cache

import redis
from rq import Queue
from rq.job import Job

from .config import settings


@lru_cache(maxsize=1)
def get_redis_connection() -> redis.Redis:
    return redis.from_url(settings.redis_url)


@lru_cache(maxsize=1)
def get_queue() -> Queue:
    return Queue(settings.triage_queue_name, connection=get_redis_connection())


def enqueue_issue_event(delivery_id: str, event: str, payload: dict) -> tuple[str, bool]:
    """Enqueue a job for the worker to process a GitHub issue event.

    Uses the GitHub delivery ID as the RQ job ID so a redelivered webhook
    (GitHub retries on timeout/non-2xx) is a no-op instead of double-queuing
    the same work. Returns (job_id, was_duplicate).

    The job function is referenced by import path so it resolves inside the
    worker process (worker.jobs.process_issue_event, added in build step 2)
    without webhook-ingress needing to import worker code.
    """
    connection = get_redis_connection()
    if Job.exists(delivery_id, connection=connection):
        return delivery_id, True

    job = get_queue().enqueue(
        "worker.jobs.process_issue_event",
        job_id=delivery_id,
        kwargs={"event": event, "payload": payload},
    )
    return job.id, False
