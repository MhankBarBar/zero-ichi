"""
Scheduler Module

Provides scheduling functionality for reminders, auto-messages, and recurring tasks.
Uses APScheduler for background job scheduling.
"""

from __future__ import annotations

import base64
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from neonize.proto.waE2E.WAWebProtobufsE2E_pb2 import Message

from core.constants import DATA_DIR, TASKS_FILE
from core.logger import log_error, log_info, log_success, log_warning

if TYPE_CHECKING:
    from core.client import BotClient


class TaskType:
    """Task type constants."""

    REMINDER = "reminder"
    AUTO_MESSAGE = "auto_message"
    RECURRING = "recurring"


class ScheduledTask:
    """Represents a scheduled task."""

    def __init__(
        self,
        task_id: str,
        task_type: str,
        chat_jid: str,
        message: str,
        trigger_time: datetime | None = None,
        cron_expression: str | None = None,
        interval_minutes: int | None = None,
        creator_jid: str | None = None,
        created_at: datetime | None = None,
        enabled: bool = True,
        metadata: dict | None = None,
        media_type: str | None = None,
        media_path: str | None = None,
    ):
        self.task_id = task_id
        self.task_type = task_type
        self.chat_jid = chat_jid
        self.message = message
        self.trigger_time = trigger_time
        self.cron_expression = cron_expression
        self.interval_minutes = interval_minutes
        self.creator_jid = creator_jid
        self.created_at = created_at or datetime.now()
        self.enabled = enabled
        self.metadata = metadata or {}
        self.media_type = media_type
        self.media_path = media_path
        self.forward_message_data: str | None = None

    def to_dict(self) -> dict:
        """Convert task to dictionary for storage."""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "chat_jid": self.chat_jid,
            "message": self.message,
            "trigger_time": self.trigger_time.isoformat() if self.trigger_time else None,
            "cron_expression": self.cron_expression,
            "interval_minutes": self.interval_minutes,
            "creator_jid": self.creator_jid,
            "created_at": self.created_at.isoformat(),
            "enabled": self.enabled,
            "metadata": self.metadata,
            "media_type": self.media_type,
            "media_path": self.media_path,
            "forward_message_data": self.forward_message_data,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ScheduledTask:
        """Create task from dictionary."""
        task = cls(
            task_id=data["task_id"],
            task_type=data["task_type"],
            chat_jid=data["chat_jid"],
            message=data["message"],
            trigger_time=datetime.fromisoformat(data["trigger_time"])
            if data.get("trigger_time")
            else None,
            cron_expression=data.get("cron_expression"),
            interval_minutes=data.get("interval_minutes"),
            creator_jid=data.get("creator_jid"),
            created_at=datetime.fromisoformat(data["created_at"])
            if data.get("created_at")
            else None,
            enabled=data.get("enabled", True),
            metadata=data.get("metadata", {}),
            media_type=data.get("media_type"),
            media_path=data.get("media_path"),
        )
        task.forward_message_data = data.get("forward_message_data")
        return task


class Scheduler:
    """Task scheduler for the bot."""

    def __init__(self, bot: BotClient):
        self.bot = bot
        self._scheduler = AsyncIOScheduler()
        self._tasks: dict[str, ScheduledTask] = {}
        self._task_counter = 0
        self._started = False
        self._load_tasks()

    def _load_tasks(self) -> None:
        """Load tasks from storage."""
        if not TASKS_FILE.exists():
            return

        try:
            with open(TASKS_FILE, encoding="utf-8") as f:
                data = json.load(f)
                for task_data in data.get("tasks", []):
                    task = ScheduledTask.from_dict(task_data)
                    self._tasks[task.task_id] = task
                self._task_counter = data.get("counter", 0)
            log_info(f"Loaded {len(self._tasks)} scheduled tasks")
        except (OSError, json.JSONDecodeError) as e:
            log_warning(f"Failed to load scheduled tasks: {e}")

    def _save_tasks(self) -> None:
        """Save tasks to storage."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        try:
            with open(TASKS_FILE, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "tasks": [t.to_dict() for t in self._tasks.values()],
                        "counter": self._task_counter,
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
        except OSError as e:
            log_error(f"Failed to save scheduled tasks: {e}")

    def _generate_task_id(self) -> str:
        """Generate a unique short hex task ID."""
        return uuid.uuid4().hex[:6]

    async def _execute_task(self, task_id: str) -> None:
        """Execute a scheduled task."""
        task = self._tasks.get(task_id)
        if not task or not task.enabled:
            log_warning(f"Task {task_id} not found or disabled, skipping execution")
            return

        log_info(f"Executing scheduled task: {task_id}")

        try:
            if task.forward_message_data:
                msg_bytes = base64.b64decode(task.forward_message_data)
                forward_msg = Message()
                forward_msg.ParseFromString(msg_bytes)
                response = await self.bot.forward_message(task.chat_jid, forward_msg)

                log_info(f"Forward response ID: {getattr(response, 'ID', None)}")

                if response and response.ID:
                    if task.message and task.message.strip():
                        await self.bot.send_reply_to_message(
                            task.chat_jid, task.message, response.ID, forward_msg
                        )
                else:
                    log_warning("No response ID from forward, sending without quote")
                    if task.message and task.message.strip():
                        await self.bot.send(task.chat_jid, task.message)
            elif task.media_type and task.media_path and Path(task.media_path).exists():
                media_path = Path(task.media_path)

                if task.media_type == "sticker":
                    if task.message and task.message.strip():
                        await self.bot.send(task.chat_jid, task.message)
                    await self.bot.send_media(
                        task.chat_jid,
                        task.media_type,
                        task.media_path,
                    )
                else:
                    await self.bot.send_media(
                        task.chat_jid,
                        task.media_type,
                        task.media_path,
                        caption=task.message,
                    )

                if task.task_type == TaskType.REMINDER and media_path.exists():
                    try:
                        media_path.unlink()
                        log_info(f"Cleaned up media file: {media_path}")
                    except Exception as e:
                        log_warning(f"Failed to cleanup media: {e}")
            else:
                await self.bot.send(task.chat_jid, task.message)

            log_success(f"Executed scheduled task: {task_id}")

            if task.task_type == TaskType.REMINDER:
                self.remove_task(task_id)
        except Exception as e:
            log_error(f"Failed to execute task {task_id}: {e}")

    def start(self) -> None:
        """Start the scheduler and load existing tasks."""
        if self._started:
            log_info("Scheduler already started, skipping")
            return

        if not self._scheduler.running:
            self._scheduler.start()
            log_success("Scheduler started")

        self._started = True

        self._cleanup_expired()

        scheduled_count = 0
        for task in list(self._tasks.values()):
            if task.enabled:
                if self._schedule_task(task):
                    scheduled_count += 1

        log_info(f"Scheduled {scheduled_count}/{len(self._tasks)} tasks")

    def _cleanup_expired(self) -> None:
        """Remove reminders that have already passed."""
        now = datetime.now()
        expired = []
        for task_id, task in self._tasks.items():
            if task.task_type == TaskType.REMINDER and task.trigger_time:
                if task.trigger_time < now:
                    expired.append(task_id)

        for task_id in expired:
            del self._tasks[task_id]
            log_warning(f"Removed expired reminder: {task_id}")

        if expired:
            self._save_tasks()

    def stop(self) -> None:
        """Stop the scheduler."""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            log_info("Scheduler stopped")
        self._started = False

    def _schedule_task(self, task: ScheduledTask) -> bool:
        """Schedule a task with APScheduler."""
        try:
            try:
                self._scheduler.remove_job(task.task_id)
            except Exception:
                pass

            if task.task_type == TaskType.REMINDER and task.trigger_time:
                if task.trigger_time > datetime.now():
                    self._scheduler.add_job(
                        self._execute_task,
                        trigger=DateTrigger(run_date=task.trigger_time),
                        args=[task.task_id],
                        id=task.task_id,
                        replace_existing=True,
                    )
                    log_info(f"Scheduled reminder {task.task_id} for {task.trigger_time}")
                    return True
                else:
                    log_warning(f"Reminder {task.task_id} time has passed, skipping")
                    return False

            elif task.task_type == TaskType.RECURRING and task.cron_expression:
                self._scheduler.add_job(
                    self._execute_task,
                    trigger=CronTrigger.from_crontab(task.cron_expression),
                    args=[task.task_id],
                    id=task.task_id,
                    replace_existing=True,
                )
                return True

            elif task.task_type == TaskType.AUTO_MESSAGE and task.interval_minutes:
                self._scheduler.add_job(
                    self._execute_task,
                    trigger=IntervalTrigger(minutes=task.interval_minutes),
                    args=[task.task_id],
                    id=task.task_id,
                    replace_existing=True,
                )
                return True

        except Exception as e:
            log_error(f"Failed to schedule task {task.task_id}: {e}")
            return False

        return False

    def add_reminder(
        self,
        chat_jid: str,
        message: str,
        trigger_time: datetime,
        creator_jid: str | None = None,
        media_type: str | None = None,
        media_path: str | None = None,
        forward_message=None,
    ) -> ScheduledTask:
        """Add a one-time reminder with optional media or forwarded message."""
        task_id = self._generate_task_id()
        task = ScheduledTask(
            task_id=task_id,
            task_type=TaskType.REMINDER,
            chat_jid=chat_jid,
            message=message,
            trigger_time=trigger_time,
            creator_jid=creator_jid,
            media_type=media_type,
            media_path=media_path,
        )

        if forward_message is not None:
            msg_bytes = forward_message.SerializeToString()
            task.forward_message_data = base64.b64encode(msg_bytes).decode("utf-8")

        self._tasks[task_id] = task
        if self._started:
            self._schedule_task(task)
        self._save_tasks()
        return task

    def add_recurring(
        self,
        chat_jid: str,
        message: str,
        cron_expression: str,
        creator_jid: str | None = None,
        media_type: str | None = None,
        media_path: str | None = None,
        forward_message=None,
    ) -> ScheduledTask:
        """Add a recurring task with cron expression and optional media/forward."""
        task_id = self._generate_task_id()
        task = ScheduledTask(
            task_id=task_id,
            task_type=TaskType.RECURRING,
            chat_jid=chat_jid,
            message=message,
            cron_expression=cron_expression,
            creator_jid=creator_jid,
            media_type=media_type,
            media_path=media_path,
        )

        if forward_message is not None:
            msg_bytes = forward_message.SerializeToString()
            task.forward_message_data = base64.b64encode(msg_bytes).decode("utf-8")
        self._tasks[task_id] = task
        if self._started:
            self._schedule_task(task)
        self._save_tasks()
        return task

    def add_auto_message(
        self,
        chat_jid: str,
        message: str,
        interval_minutes: int,
        creator_jid: str | None = None,
        media_type: str | None = None,
        media_path: str | None = None,
        forward_message=None,
    ) -> ScheduledTask:
        """Add an auto-message that repeats at fixed intervals with optional media/forward."""
        task_id = self._generate_task_id()
        task = ScheduledTask(
            task_id=task_id,
            task_type=TaskType.AUTO_MESSAGE,
            chat_jid=chat_jid,
            message=message,
            interval_minutes=interval_minutes,
            creator_jid=creator_jid,
            media_type=media_type,
            media_path=media_path,
        )

        if forward_message is not None:
            msg_bytes = forward_message.SerializeToString()
            task.forward_message_data = base64.b64encode(msg_bytes).decode("utf-8")
        self._tasks[task_id] = task
        if self._started:
            self._schedule_task(task)
        self._save_tasks()
        return task

    def remove_task(self, task_id: str) -> bool:
        """Remove a scheduled task."""
        if task_id not in self._tasks:
            return False

        try:
            self._scheduler.remove_job(task_id)
        except Exception:
            pass

        del self._tasks[task_id]
        self._save_tasks()
        return True

    def toggle_task(self, task_id: str, enabled: bool) -> bool:
        """Enable or disable a task."""
        task = self._tasks.get(task_id)
        if not task:
            return False

        task.enabled = enabled
        if enabled:
            self._schedule_task(task)
        else:
            try:
                self._scheduler.remove_job(task_id)
            except Exception:
                pass

        self._save_tasks()
        return True

    def get_task(self, task_id: str) -> ScheduledTask | None:
        """Get a task by ID."""
        return self._tasks.get(task_id)

    def get_tasks_for_chat(self, chat_jid: str) -> list[ScheduledTask]:
        """Get all tasks for a specific chat."""
        return [t for t in self._tasks.values() if t.chat_jid == chat_jid]

    def get_all_tasks(self) -> list[ScheduledTask]:
        """Get all scheduled tasks."""
        return list(self._tasks.values())

    def get_tasks_count(self) -> int:
        """Get total number of tasks."""
        return len(self._tasks)


_scheduler: Scheduler | None = None


def get_scheduler() -> Scheduler | None:
    """Get the global scheduler instance."""
    return _scheduler


def init_scheduler(bot: BotClient) -> Scheduler:
    """Initialize the global scheduler (does NOT start it - call start() after event loop is running)."""
    global _scheduler
    _scheduler = Scheduler(bot)
    return _scheduler
