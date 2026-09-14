import logging

import redis
from rq import Queue, Worker

from .config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("worker.main")


def run() -> None:
    connection = redis.from_url(settings.redis_url)
    queue = Queue(settings.triage_queue_name, connection=connection)
    worker = Worker([queue], connection=connection)
    logger.info("worker listening on queue '%s'", settings.triage_queue_name)
    worker.work(with_scheduler=True)


if __name__ == "__main__":
    run()
