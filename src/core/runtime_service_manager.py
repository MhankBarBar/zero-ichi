from __future__ import annotations

import importlib
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from core.logger import log_warning
from core.shared import set_bot


@dataclass
class RuntimeServiceManager:
    runtime_config: Any
    pipeline: Any = None
    scheduler: Any = None
    dashboard_task: Any = None
    webhook_runtime: Any = None
    bot: Any = None
    message_cache: Any = None
    tg_forwarder: Any = None
    _config_callbacks: list[Callable[[], None]] = field(default_factory=list)
    _pipeline_factory: Callable[[], Any] | None = None

    def rebuild_pipeline(self, *, factory: Callable[[], Any]):
        self._pipeline_factory = factory
        self.pipeline = factory()
        return self.pipeline

    def start_scheduler_if_needed(self):
        if self.scheduler and not self.scheduler._scheduler.running:
            self.scheduler.start()

    def start_dashboard(self, *, enabled: bool, create_task_fn, server_factory):
        if not enabled:
            self.dashboard_task = None
            return None
        if self.dashboard_task is not None:
            return self.dashboard_task

        server = server_factory()
        self.dashboard_task = create_task_fn(server.serve())
        return self.dashboard_task

    def start_tg_forwarder_if_needed(self, create_task_fn):
        if not self.tg_forwarder:
            log_warning("Telegram forwarder: not initialized (tg_forwarder is None)")
            return
        if self.tg_forwarder.is_running:
            log_info("Telegram forwarder: already running")
            return
        cfg = self.runtime_config.get_telegram_forwarder()
        if not cfg.get("enabled", False):
            log_info("Telegram forwarder: disabled in config")
            return
        log_info("Telegram forwarder: starting...")
        create_task_fn(self.tg_forwarder.start())

    def register_config_callback(self, callback: Callable[[], None]):
        self._config_callbacks.append(callback)

    def notify_config_changed(self):
        for callback in self._config_callbacks:
            try:
                callback()
            except Exception as exc:
                log_warning(f"Runtime config callback failed: {exc}")

    def reload_core_module(self, *, client, message_cache, core_client_module, bot_client_cls):
        importlib.reload(core_client_module)
        self.bot = bot_client_cls(client)
        self.bot.message_cache = message_cache
        self.message_cache = message_cache
        set_bot(self.bot)
        if self._pipeline_factory is not None:
            self.pipeline = self._pipeline_factory()
        return self.bot

    async def stop_all(self):
        """Stop all runtime services gracefully."""
        if self.tg_forwarder and self.tg_forwarder.is_running:
            try:
                await self.tg_forwarder.stop()
            except Exception as e:
                log_warning(f"Error stopping tg_forwarder: {e}")

        if self.scheduler and self.scheduler._scheduler.running:
            try:
                self.scheduler.shutdown()
            except Exception as e:
                log_warning(f"Error stopping scheduler: {e}")

        if self.dashboard_task:
            self.dashboard_task.cancel()
            self.dashboard_task = None
