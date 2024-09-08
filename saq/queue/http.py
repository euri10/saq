"""
HTTP Queue
"""

from __future__ import annotations

import json
import typing as t

from saq.errors import MissingDependencyError
from saq.queue.base import Queue, logger

if t.TYPE_CHECKING:
    from collections.abc import Iterable

    from saq.job import Job, Status

    from saq.types import (
        CountKind,
        QueueInfo,
        QueueStats,
    )

try:
    from aiohttp import ClientSession
except ModuleNotFoundError as e:
    raise MissingDependencyError(
        "Missing dependencies for Http. Install them with `pip install saq[http]`. "
        "Prefix url with redis or postgres if you meant to use those instead."
    ) from e


class HttpProxy:
    def __init__(self, queue: Queue):
        self.queue = queue

    @staticmethod
    def serialize(job: t.Optional[Job]) -> str | None:
        if job:
            return json.dumps(job.to_dict())
        return None

    async def process(self, body: str) -> str | None:
        req = json.loads(body)
        kind = req["kind"]
        job = self.queue.deserialize(req.get("job"))

        if job:
            if kind == "enqueue":
                return self.serialize(await self.queue.enqueue(job))
            if kind == "update":
                await self.queue.update(job)
                return None
            if kind == "finish":
                await self.queue.finish(
                    job, status=req["status"], result=req["result"], error=req["error"]
                )
                return None
            if kind == "retry":
                await self.queue.retry(job, error=req["error"])
                return None
            if kind == "abort":
                await self.queue.abort(job, error=req["error"], ttl=req["ttl"])
                return None
            if kind == "finish_abort":
                await self.queue.finish_abort(job)
                return None
            if kind == "notify":
                await self.queue.notify(job)
                return None
        else:
            if kind == "dequeue":
                return self.serialize(await self.queue.dequeue(req["timeout"]))
            if kind == "job":
                return self.serialize(await self.queue.job(req["job_key"]))
            if kind == "jobs":
                return json.dumps(
                    [
                        job.to_dict() if job else None
                        for job in await self.queue.jobs(req["job_keys"])
                    ]
                )
            if kind == "count":
                return json.dumps(await self.queue.count(req["count_kind"]))
            if kind == "schedule":
                return json.dumps(await self.queue.schedule(req["lock"]))
            if kind == "sweep":
                return json.dumps(await self.queue.sweep(lock=req["lock"], abort=req["abort"]))
            if kind == "info":
                return json.dumps(
                    await self.queue.info(jobs=req["job"], offset=req["offset"], limit=req["limit"])
                )
            if kind == "write_stats":
                await self.queue.write_stats(req["stats"], ttl=req["ttl"])
                return None
        raise ValueError(f"Invalid request {body}")


class HttpQueue(Queue):
    """
    Queue is used to interact with Http.

    Args:
        url: The url to hit.
        name: name of the queue (default "default")
    """

    @classmethod
    def from_url(cls: type[HttpQueue], url: str, **kwargs: t.Any) -> HttpQueue:
        """Create a queue from a url pointing to an http proxy with session kwargs."""
        return cls(url, **kwargs)

    def __init__(
        self,
        url: str,
        name: str = "default",
        **kwargs: t.Any,
    ) -> None:
        super().__init__(name=name, dump=None, load=None)

        self.url = url
        self.session_kwargs = kwargs
        self.session: t.Optional[ClientSession] = None

    async def connect(self) -> None:
        if not self.session:
            self.session = ClientSession(**self.session_kwargs)

    async def disconnect(self) -> None:
        if self.session:
            await self.session.close()
            self.session = None

    async def _send(self, kind: str, **kwargs: t.Any) -> str:
        assert self.session

        try:
            async with self.session.post(self.url, json={"kind": kind, **kwargs}) as resp:
                return await resp.text()
        except Exception as e:
            logger.debug(e)
            return ""

    async def _enqueue(self, job: Job) -> Job | None:
        return self.deserialize(await self._send("enqueue", job=self.serialize(job)))

    async def _finish(
        self,
        job: Job,
        status: Status,
        *,
        result: t.Any = None,
        error: str | None = None,
    ) -> None:
        await self._send(
            "finish", job=self.serialize(job), status=status, result=result, error=error
        )

    async def _retry(self, job: Job, error: str | None) -> None:
        await self._send("retry", job=self.serialize(job), error=error)

    async def notify(self, job: Job) -> None:
        await self._send("notify", job=self.serialize(job))

    async def update(self, job: Job) -> None:
        await self._send("update", job=self.serialize(job))

    async def job(self, job_key: str) -> Job | None:
        return self.deserialize(await self._send("job", job_key=job_key))

    async def jobs(self, job_keys: Iterable[str]) -> t.List[Job | None]:
        return [
            self.deserialize(job_dict)
            for job_dict in json.loads(await self._send("jobs", job_keys=list(job_keys)))
        ]

    async def abort(self, job: Job, error: str, ttl: float = 5) -> None:
        await self._send("abort", job=self.serialize(job), error=error, ttl=ttl)

    async def finish_abort(self, job: Job) -> None:
        await self._send("finish_abort", job=self.serialize(job))

    async def dequeue(self, timeout: float = 0) -> Job | None:
        return self.deserialize(await self._send("dequeue", timeout=timeout))

    async def write_stats(self, stats: QueueStats, ttl: int) -> None:
        await self._send("write_stats", stats=stats, ttl=ttl)

    async def info(self, jobs: bool = False, offset: int = 0, limit: int = 10) -> QueueInfo:
        return json.loads(await self._send("info", jobs=jobs, offset=offset, limit=limit))

    async def count(self, kind: CountKind) -> int:
        return int(await self._send("count", count_kind=kind))

    async def schedule(self, lock: int = 1) -> list[str]:
        return json.loads(await self._send("schedule", lock=lock))

    async def sweep(self, lock: int = 60, abort: float = 5.0) -> list[str]:
        return json.loads(await self._send("sweep", lock=lock, abort=abort))