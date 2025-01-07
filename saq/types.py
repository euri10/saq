"""
Types
"""

from __future__ import annotations

import typing as t
from collections.abc import Collection


if t.TYPE_CHECKING:
    from asyncio import Task

    from saq.job import CronJob, Job, Status
    from saq.worker import Worker
    from saq.queue import Queue
    from typing_extensions import Required


class Context(t.TypedDict, total=False):
    """
    Task context.

    Extra context fields are allowed.
    """

    worker: Required[Worker]
    "Worker currently executing the task"
    job: Job
    "Job() instance of the task"
    queue: Queue
    "Queue the task is running on"
    exception: t.Optional[Exception]
    "Exception raised by the task if any"


class JobTaskContext(t.TypedDict, total=False):
    """
    Jobs Task Context
    """

    task: Task[t.Any]
    "asyncio Task of the Job"
    aborted: t.Optional[str]
    "If this task has been aborted, this is the reason"


class QueueInfo(t.TypedDict):
    """
    Queue Info
    """

    workers: dict[str, dict[str, t.Any]]
    "Worker information"
    name: str
    "Queue name"
    queued: int
    "Number of jobs currently in the queue"
    active: int
    "Number of jobs currently active"
    scheduled: int
    jobs: list[dict[str, t.Any]]
    "A truncated list containing the jobs that are scheduled to execute soonest"


class QueueStats(t.TypedDict):
    """
    Queue Stats, could also be used for Worker Stats
    """

    complete: int
    "Number of complete tasks"
    failed: int
    "Number of failed tasks"
    retried: int
    "Number of retries"
    aborted: int
    "Number of aborted tasks"
    uptime: int
    "Queue uptime in milliseconds"


class TimersDict(t.TypedDict):
    """
    Timers Dictionary
    """

    schedule: int
    "How often we poll to schedule jobs in seconds (default 1)"
    stats: int
    "How often to update stats in seconds (default 10)"
    sweep: int
    "How often to clean up stuck jobs in seconds (default 60)"
    abort: int
    "How often to check if a job is aborted in seconds (default 1)"


class PartialTimersDict(TimersDict, total=False):
    """
    For argument to `Worker`, all keys are not required
    """


class SettingsDict(t.TypedDict, total=False):
    """
    Settings
    """

    queue: Queue
    functions: Required[Collection[Function | tuple[str, Function]]]
    concurrency: int
    cron_jobs: Collection[CronJob]
    startup: ReceivesContext
    shutdown: ReceivesContext
    before_process: ReceivesContext
    after_process: ReceivesContext
    timers: PartialTimersDict
    dequeue_timeout: float


BeforeEnqueueType = t.Callable[["Job"], t.Awaitable[t.Any]]
CountKind = t.Literal["queued", "active", "incomplete"]
DumpType = t.Callable[[t.Mapping[t.Any, t.Any]], t.Union[bytes, str]]
DurationKind = t.Literal["process", "start", "total", "running"]
Function = t.Callable[..., t.Any]
ListenCallback = t.Callable[[str, "Status"], t.Any]
LoadType = t.Callable[[t.Union[bytes, str]], t.Any]
ReceivesContext = t.Callable[[Context], t.Any]
VersionTuple = t.Tuple[int, ...]
