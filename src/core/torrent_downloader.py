from __future__ import annotations

import asyncio
import shutil
import signal
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from core.constants import TORRENTS_DIR
from core.logger import log_error, log_info
from core.runtime_config import runtime_config


RPC_URL_TEMPLATE = "http://127.0.0.1:{port}/jsonrpc"


def format_speed(speed_bps: int) -> str:
    if speed_bps <= 0:
        return "~"
    if speed_bps >= 1_000_000:
        return f"{speed_bps / 1_000_000:.1f}MB"
    if speed_bps >= 1_000:
        return f"{speed_bps / 1_000:.0f}KB"
    return f"{speed_bps}B"


def format_eta(total: int, completed: int, speed: int) -> str:
    if speed <= 0 or total <= 0:
        return "~"
    remaining = total - completed
    seconds = remaining // speed if speed > 0 else 0
    if seconds <= 0:
        return "~"
    if seconds >= 3600:
        return f"{seconds // 3600}h {(seconds % 3600) // 60}m"
    if seconds >= 60:
        return f"{seconds // 60}m {seconds % 60}s"
    return f"{seconds}s"


@dataclass
class TorrentFile:
    name: str
    path: Path
    size: int


@dataclass
class TorrentJob:
    gid: str
    uri: str
    status: str = "active"
    progress: float = 0.0
    completed_length: int = 0
    total_length: int = 0
    download_speed: int = 0
    files: list[TorrentFile] = field(default_factory=list)
    sender_jid: str = ""
    chat_jid: str = ""
    created_at: float = field(default_factory=time.time)
    error: str | None = None


class Aria2RPC:
    def __init__(self) -> None:
        self._process: asyncio.subprocess.Process | None = None
        self._rpc_secret: str = ""
        self._rpc_port: int = 6800
        self._download_dir: Path = TORRENTS_DIR
        self._jobs: dict[str, TorrentJob] = {}
        self._poll_task: asyncio.Task | None = None
        self._running = False

    @property
    def rpc_url(self) -> str:
        return RPC_URL_TEMPLATE.format(port=self._rpc_port)

    async def _rpc_call(self, method: str, params: list | None = None) -> Any:
        payload = {"jsonrpc": "2.0", "id": str(int(time.time() * 1000)), "method": method}
        secret = self._rpc_secret
        if secret:
            payload["params"] = [f"token:{secret}"]
            if params:
                payload["params"].extend(params)
        else:
            payload["params"] = params if params else []
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(self.rpc_url, json=payload, headers={"Content-Type": "application/json"})
                data = resp.json()
                if "error" in data:
                    log_error(f"[Aria2RPC] RPC error: {data['error']}")
                    return None
                return data.get("result")
        except Exception as e:
            log_error(f"[Aria2RPC] RPC call failed: {e}")
            return None

    async def start_daemon(self) -> bool:
        config = runtime_config.get_nested("torrent", default={})
        if not isinstance(config, dict):
            config = {}
        self._rpc_secret = str(config.get("rpc_secret", ""))
        self._rpc_port = int(config.get("rpc_port", 6800))
        dir_str = str(config.get("download_dir", "data/downloads/torrents"))
        self._download_dir = Path(dir_str)
        if not self._download_dir.is_absolute():
            from core.constants import BASE_DIR
            self._download_dir = BASE_DIR / dir_str
        self._download_dir.mkdir(parents=True, exist_ok=True)
        max_concurrent = int(config.get("max_concurrent", 5))
        seed_time = int(config.get("seed_time", 0))

        if self._process and self._process.returncode is None:
            return True

        args = [
            "aria2c",
            "--enable-rpc",
            f"--rpc-listen-port={self._rpc_port}",
            f"--max-concurrent-downloads={max_concurrent}",
            f"--seed-time={seed_time}",
            f"--dir={self._download_dir}",
            "--console-log-level=warn",
            "--summary-interval=0",
            "--continue=true",
            "--allow-overwrite=true",
            "--auto-file-renaming=false",
        ]
        if self._rpc_secret:
            args.append(f"--rpc-secret={self._rpc_secret}")

        try:
            self._process = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.sleep(1)
            if self._process.returncode is not None and self._process.returncode != 0:
                log_error(f"[Aria2RPC] Daemon exited with code {self._process.returncode}")
                self._process = None
                return False

            self._running = True
            self._poll_task = asyncio.create_task(self._poll_active_downloads())
            log_info(f"[Aria2RPC] Daemon started on port {self._rpc_port}")
            return True
        except FileNotFoundError:
            log_error("[Aria2RPC] aria2c not found")
            return False
        except Exception as e:
            log_error(f"[Aria2RPC] Failed to start daemon: {e}")
            return False

    async def stop_daemon(self) -> None:
        if self._poll_task:
            self._poll_task.cancel()
            self._poll_task = None
        self._running = False
        if self._process and self._process.returncode is None:
            try:
                self._process.send_signal(signal.SIGTERM)
                await asyncio.wait_for(self._process.wait(), timeout=10)
            except asyncio.TimeoutError:
                self._process.kill()
                await self._process.wait()
            except Exception:
                pass
        self._process = None
        log_info("[Aria2RPC] Daemon stopped")

    async def add_download(self, uri: str, sender_jid: str = "", chat_jid: str = "") -> str | None:
        if not self._running:
            ok = await self.start_daemon()
            if not ok:
                return None

        result = await self._rpc_call("aria2.addUri", [[uri]])
        if not result:
            return None

        gid = str(result)
        job = TorrentJob(
            gid=gid,
            uri=uri,
            sender_jid=sender_jid,
            chat_jid=chat_jid,
        )
        self._jobs[gid] = job
        log_info(f"[Aria2RPC] Download added: {gid}")
        return gid

    async def get_job(self, gid: str) -> TorrentJob | None:
        return self._jobs.get(gid)

    async def cancel(self, gid: str) -> bool:
        result = await self._rpc_call("aria2.remove", [gid])
        if result:
            if gid in self._jobs:
                self._jobs[gid].status = "removed"
            return True
        return False

    def _update_job_from_status(self, gid: str, status: dict[str, Any]) -> TorrentJob | None:
        job = self._jobs.get(gid)
        if not job:
            return None

        s = status.get("status", "")
        completed = int(status.get("completedLength", "0"))
        total = int(status.get("totalLength", "0"))
        speed = int(status.get("downloadSpeed", "0"))

        job.status = s
        job.completed_length = completed
        job.total_length = total
        job.download_speed = speed
        job.progress = (completed / total * 100) if total > 0 else 0.0

        files_raw = status.get("files", [])
        files_list: list[TorrentFile] = []
        for f in files_raw:
            fpath_str = f.get("path", "")
            if not fpath_str:
                continue
            fpath = Path(fpath_str)
            fsize = int(f.get("length", "0"))
            files_list.append(TorrentFile(name=fpath.name, path=fpath, size=fsize))
        if files_list:
            job.files = files_list

        if s == "complete" and job.status != "complete":
            log_info(f"[Aria2RPC] Download complete: {gid}")
        elif s == "error":
            error_msg = status.get("errorMessage", "Unknown error")
            job.error = error_msg
            log_error(f"[Aria2RPC] Download error: {gid} — {error_msg}")

        return job

    async def _poll_active_downloads(self) -> None:
        while self._running:
            try:
                active = await self._rpc_call("aria2.tellActive")
                if isinstance(active, list):
                    for item in active:
                        gid = str(item.get("gid", ""))
                        if gid:
                            self._update_job_from_status(gid, item)

                waiting = await self._rpc_call("aria2.tellWaiting", [0, 100])
                if isinstance(waiting, list):
                    for item in waiting:
                        gid = str(item.get("gid", ""))
                        if gid:
                            self._update_job_from_status(gid, item)

                stopped = await self._rpc_call("aria2.tellStopped", [0, 100])
                if isinstance(stopped, list):
                    for item in stopped:
                        gid = str(item.get("gid", ""))
                        if gid and gid in self._jobs:
                            self._update_job_from_status(gid, item)

                self._cleanup_old_jobs()
            except asyncio.CancelledError:
                break
            except Exception as e:
                log_error(f"[Aria2RPC] Poll error: {e}")

            await asyncio.sleep(5)

    def _cleanup_old_jobs(self, ttl: int = 86400) -> None:
        now = time.time()
        expired = [
            gid for gid, job in self._jobs.items()
            if job.status in ("complete", "error", "removed")
            and (now - job.created_at) > ttl
        ]
        for gid in expired:
            dir_to_clean = self._download_dir / gid
            if dir_to_clean.exists():
                shutil.rmtree(dir_to_clean, ignore_errors=True)
            del self._jobs[gid]
        if expired:
            log_info(f"[Aria2RPC] Cleaned up {len(expired)} expired jobs")


aria2rpc = Aria2RPC()
