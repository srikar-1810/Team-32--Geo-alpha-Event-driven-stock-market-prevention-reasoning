from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional, Set

from app.logging_config import get_logger

logger = get_logger(__name__)


class ScheduledTask:
    """A single scheduled ingestion task with interval tracking and overlap prevention."""

    def __init__(
        self,
        name: str,
        interval_seconds: int,
        callback: Callable[[], Awaitable[Dict[str, Any]]],
        description: str = "",
    ) -> None:
        self.name = name
        self.interval = interval_seconds
        self.callback = callback
        self.description = description
        self._last_run: Optional[datetime] = None
        self._next_run: datetime = datetime.now(timezone.utc)
        self._is_running: bool = False
        self._run_count: int = 0
        self._error_count: int = 0
        self._last_result: Optional[Dict[str, Any]] = None
        self._last_error: Optional[str] = None

    async def execute(self) -> Dict[str, Any]:
        if self._is_running:
            logger.warning("Task '%s' is already running, skipping.", self.name)
            return {"status": "skipped", "reason": "already_running", "name": self.name}

        self._is_running = True
        now = datetime.now(timezone.utc)
        self._last_run = now
        from datetime import timedelta
        self._next_run = now + timedelta(seconds=self.interval)

        try:
            result = await self.callback()
            self._run_count += 1
            self._last_result = result
            self._last_error = None
            status = result.get("status", "success")
            logger.info("Task '%s' completed: status=%s, run=%d", self.name, status, self._run_count)
            return result
        except Exception as e:
            self._error_count += 1
            self._last_error = str(e)
            logger.error("Task '%s' failed: %s", self.name, e)
            return {"status": "error", "error": str(e), "name": self.name}
        finally:
            self._is_running = False

    async def _sleep(self, duration: int) -> None:
        await asyncio.sleep(0)

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def last_run(self) -> Optional[datetime]:
        return self._last_run

    @property
    def next_run(self) -> datetime:
        return self._next_run

    @property
    def run_count(self) -> int:
        return self._run_count

    @property
    def error_count(self) -> int:
        return self._error_count

    @property
    def last_result(self) -> Optional[Dict[str, Any]]:
        return self._last_result

    @property
    def last_error(self) -> Optional[str]:
        return self._last_error

    def status(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "interval_seconds": self.interval,
            "is_running": self._is_running,
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "next_run": self._next_run.isoformat() if self._next_run else None,
            "run_count": self._run_count,
            "error_count": self._error_count,
            "last_error": self._last_error,
            "description": self.description,
        }


class IngestionScheduler:
    """Async scheduler that manages periodic ingestion tasks with overlap protection."""

    def __init__(self) -> None:
        self._tasks: Dict[str, ScheduledTask] = {}
        self._is_running: bool = False
        self._scheduler_task: Optional[asyncio.Task] = None
        self._on_error: Optional[Callable[[str, Exception], Awaitable[None]]] = None

    def register(
        self,
        name: str,
        interval_seconds: int,
        callback: Callable[[], Awaitable[Dict[str, Any]]],
        description: str = "",
    ) -> ScheduledTask:
        task = ScheduledTask(
            name=name,
            interval_seconds=interval_seconds,
            callback=callback,
            description=description,
        )
        self._tasks[name] = task
        logger.info(
            "Registered scheduled task '%s': interval=%ds, desc='%s'",
            name, interval_seconds, description,
        )
        return task

    def unregister(self, name: str) -> None:
        self._tasks.pop(name, None)
        logger.info("Unregistered task '%s'", name)

    def get_task(self, name: str) -> Optional[ScheduledTask]:
        return self._tasks.get(name)

    def list_tasks(self) -> Dict[str, Dict[str, Any]]:
        return {name: task.status() for name, task in self._tasks.items()}

    async def start(self) -> None:
        if self._is_running:
            logger.warning("Scheduler is already running.")
            return

        self._is_running = True
        logger.info("Ingestion scheduler started with %d tasks", len(self._tasks))
        self._scheduler_task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        self._is_running = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
            self._scheduler_task = None
        logger.info("Ingestion scheduler stopped.")

    async def trigger_now(self, name: str) -> Optional[Dict[str, Any]]:
        task = self._tasks.get(name)
        if not task:
            logger.warning("No task named '%s' found", name)
            return None
        logger.info("Manually triggering task '%s'", name)
        return await task.execute()

    async def trigger_all(self) -> Dict[str, Any]:
        results = {}
        for name in self._tasks:
            results[name] = await self.trigger_now(name)
        return results

    async def _run_loop(self) -> None:
        if not self._tasks:
            logger.warning("No tasks registered, scheduler idle.")
            return

        while self._is_running:
            now = datetime.now(timezone.utc)
            due_tasks = []

            for name, task in self._tasks.items():
                if now >= task.next_run and not task.is_running:
                    due_tasks.append(task)

            for task in due_tasks:
                asyncio.create_task(self._run_task(task))

            await asyncio.sleep(5)

        logger.info("Scheduler loop ended.")

    async def _run_task(self, task: ScheduledTask) -> None:
        try:
            await task.execute()
        except Exception as e:
            logger.error("Unhandled exception in task '%s': %s", task.name, e)
            if self._on_error:
                await self._on_error(task.name, e)

    def set_error_handler(
        self, handler: Callable[[str, Exception], Awaitable[None]]
    ) -> None:
        self._on_error = handler

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def task_count(self) -> int:
        return len(self._tasks)

    def status(self) -> Dict[str, Any]:
        return {
            "is_running": self._is_running,
            "task_count": self.task_count,
            "tasks": self.list_tasks(),
        }
