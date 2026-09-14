import fakeredis
from rq import Queue, SimpleWorker

from worker.dead_letter import list_dead_letters


def always_fails():
    raise RuntimeError("boom")


def test_list_dead_letters_surfaces_failed_job():
    connection = fakeredis.FakeStrictRedis()
    queue = Queue("triage", connection=connection)

    job = queue.enqueue(always_fails)
    SimpleWorker([queue], connection=connection).work(burst=True)

    dead_letters = list_dead_letters(connection, queue_name="triage")

    assert len(dead_letters) == 1
    assert dead_letters[0].job_id == job.id
    assert "boom" in dead_letters[0].exc_info


def test_list_dead_letters_empty_when_nothing_failed():
    connection = fakeredis.FakeStrictRedis()

    dead_letters = list_dead_letters(connection, queue_name="triage")

    assert dead_letters == []
