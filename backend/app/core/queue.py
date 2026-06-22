"""Redis-backed job queue for asynchronous scans.

The API enqueues a lightweight :class:`ScanJob` (just the scan id + metadata);
a separate worker process pops jobs and runs the scan. A plain Redis list is
used as a FIFO queue: ``RPUSH`` to enqueue, blocking ``BLPOP`` to dequeue. This
keeps the dependency surface tiny while still giving durable, cross-process
hand-off.

The queue accepts an injected Redis client so it can be unit-tested with a
fake; in production it lazily builds one from settings.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Protocol, cast

from app.config import get_settings

SCAN_QUEUE_KEY = "webhawk:scans:queue"


@dataclass(frozen=True, slots=True)
class ScanJob:
    """A unit of work handed to the worker."""

    scan_id: str
    target_id: str

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, raw: str | bytes) -> ScanJob:
        data: dict[str, Any] = json.loads(raw)
        return cls(scan_id=str(data["scan_id"]), target_id=str(data["target_id"]))


class RedisLike(Protocol):
    """Subset of the redis client interface the queue depends on."""

    def rpush(self, name: str, *values: str) -> int: ...

    def blpop(
        self, keys: str, timeout: int = ...
    ) -> tuple[bytes, bytes] | None: ...

    def llen(self, name: str) -> int: ...


def _build_redis() -> RedisLike:
    # Imported lazily so importing this module never requires a live Redis.
    import redis

    settings = get_settings()
    return cast(RedisLike, redis.Redis.from_url(settings.redis_url))


class ScanQueue:
    """FIFO scan queue over a Redis list."""

    def __init__(
        self, client: RedisLike | None = None, *, key: str = SCAN_QUEUE_KEY
    ) -> None:
        self._client = client
        self._key = key

    @property
    def client(self) -> RedisLike:
        if self._client is None:
            self._client = _build_redis()
        return self._client

    def enqueue(self, job: ScanJob) -> None:
        """Append a job to the tail of the queue."""
        self.client.rpush(self._key, job.to_json())

    def dequeue(self, timeout: int = 5) -> ScanJob | None:
        """Block up to ``timeout`` seconds for the next job; None on timeout."""
        result = self.client.blpop(self._key, timeout=timeout)
        if result is None:
            return None
        _key, raw = result
        return ScanJob.from_json(raw)

    def depth(self) -> int:
        """Number of jobs currently waiting in the queue."""
        return self.client.llen(self._key)
