import logging

import redis
from rq import Queue, SimpleWorker

from .config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("worker.main")


def run() -> None:
    connection = redis.from_url(settings.redis_url)
    queue = Queue(settings.triage_queue_name, connection=connection)
    # SimpleWorker (no fork-per-job) rather than the default Worker: the
    # pipeline loads an ML model (sentence-transformers) which forking
    # would either reload on every job or crash outright (SIGABRT - macOS's
    # Objective-C fork-safety guard trips when a forked child touches
    # PyTorch/Accelerate). Running in-process also lets the embedder/DB
    # engine/LLM client singletons in pipeline.py actually stay cached
    # across jobs instead of being pointless.
    worker = SimpleWorker([queue], connection=connection)
    logger.info("worker listening on queue '%s'", settings.triage_queue_name)
    worker.work(with_scheduler=True)


if __name__ == "__main__":
    run()
