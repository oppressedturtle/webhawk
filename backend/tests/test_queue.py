"""Queue + worker tests using an in-memory fake Redis list."""

from __future__ import annotations

from app.core.queue import ScanJob, ScanQueue
from app.worker import run


class FakeRedis:
    """Minimal in-memory stand-in for the redis list operations we use."""

    def __init__(self) -> None:
        self.store: dict[str, list[bytes]] = {}

    def rpush(self, name: str, *values: str) -> int:
        bucket = self.store.setdefault(name, [])
        bucket.extend(v.encode() for v in values)
        return len(bucket)

    def blpop(self, keys: str, timeout: int = 0) -> tuple[bytes, bytes] | None:
        bucket = self.store.get(keys, [])
        if not bucket:
            return None
        return keys.encode(), bucket.pop(0)

    def llen(self, name: str) -> int:
        return len(self.store.get(name, []))


def test_scan_job_json_round_trip() -> None:
    job = ScanJob(scan_id="scan-1", target_id="target-1")
    restored = ScanJob.from_json(job.to_json())
    assert restored == job


def test_enqueue_dequeue_fifo_order() -> None:
    queue = ScanQueue(FakeRedis())
    queue.enqueue(ScanJob(scan_id="a", target_id="t"))
    queue.enqueue(ScanJob(scan_id="b", target_id="t"))

    assert queue.depth() == 2
    first = queue.dequeue(timeout=1)
    second = queue.dequeue(timeout=1)
    assert first is not None and first.scan_id == "a"
    assert second is not None and second.scan_id == "b"
    assert queue.dequeue(timeout=1) is None


def test_worker_processes_enqueued_jobs() -> None:
    queue = ScanQueue(FakeRedis())
    queue.enqueue(ScanJob(scan_id="a", target_id="t"))
    queue.enqueue(ScanJob(scan_id="b", target_id="t"))

    processed = run(queue, max_jobs=2)

    assert processed == 2
    assert queue.depth() == 0
