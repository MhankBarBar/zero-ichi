"""
System command - Show machine-level system data for the server running the bot.

Shows bot + system uptime, RAM/swap usage, CPU load, disk usage, and
process info. Reads Linux /proc directly (no psutil dependency).
"""

from __future__ import annotations

import os
import platform
import shutil
import time
from pathlib import Path

from core import symbols as sym
from core.command import Command, CommandContext
from core.i18n import t
from core.timefmt import format_uptime

from commands.general.uptime import _start_time


def _read_proc(path: str) -> str:
    """Safely read a /proc file, returning '' on any error."""
    try:
        return Path(path).read_text()
    except Exception:
        return ""


def _meminfo() -> dict[str, int]:
    """Parse /proc/meminfo into a {name: kB} dict."""
    data: dict[str, int] = {}
    for line in _read_proc("/proc/meminfo").splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0].endswith(":"):
            try:
                data[parts[0][:-1]] = int(parts[1])
            except ValueError:
                continue
    return data


def _fmt_kb(kb: int) -> str:
    """Format kilobytes into a human-readable size string."""
    value = float(kb) * 1024
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.1f}{unit}" if unit != "B" else f"{int(value)}B"
        value /= 1024
    return f"{value:.1f}TB"


def _system_uptime() -> float:
    """Seconds since boot from /proc/uptime."""
    try:
        return float(_read_proc("/proc/uptime").split()[0])
    except (IndexError, ValueError):
        return 0.0


def _cpu_load() -> list[float]:
    """1/5/15-min load averages from /proc/loadavg."""
    parts = _read_proc("/proc/loadavg").split()
    try:
        return [float(p) for p in parts[:3]]
    except ValueError:
        return []


def _process_rss_mb() -> int:
    """Resident set size of this process in MB from /proc/self/status."""
    for line in _read_proc("/proc/self/status").splitlines():
        if line.startswith("VmRSS:"):
            try:
                return int(line.split()[1]) // 1024  # kB -> MB
            except (IndexError, ValueError):
                break
    return 0


def _process_threads() -> int:
    """Thread count of this process from /proc/self/status."""
    for line in _read_proc("/proc/self/status").splitlines():
        if line.startswith("Threads:"):
            try:
                return int(line.split()[1])
            except (IndexError, ValueError):
                break
    return 0


class SystemCommand(Command):
    name = "system"
    aliases = ["sys", "sysinfo"]
    description = "Show server system data (uptime, RAM, storage, CPU)"
    usage = "system"
    category = "general"

    async def execute(self, ctx: CommandContext) -> None:
        """Show machine-level system stats for the server running the bot."""
        # ---- uptime -------------------------------------------------- #
        bot_uptime = format_uptime(time.time() - _start_time, include_seconds=False)
        sys_uptime = format_uptime(_system_uptime(), include_seconds=False)

        # ---- memory -------------------------------------------------- #
        mem = _meminfo()
        mem_total = mem.get("MemTotal", 0)
        mem_avail = mem.get("MemAvailable", 0)
        mem_used = max(0, mem_total - mem_avail)
        mem_pct = (mem_used / mem_total * 100) if mem_total else 0.0
        swap_total = mem.get("SwapTotal", 0)
        swap_free = mem.get("SwapFree", 0)
        swap_used = max(0, swap_total - swap_free)

        # ---- cpu ----------------------------------------------------- #
        load = _cpu_load()
        load_str = ", ".join(f"{v:.2f}" for v in load) if load else "N/A"
        cores = os.cpu_count() or 1

        # ---- disk ---------------------------------------------------- #
        try:
            usage = shutil.disk_usage(str(Path(__file__).resolve().parent.parent.parent))
            disk_total, disk_used = usage.total, usage.used
            disk_pct = (disk_used / disk_total * 100) if disk_total else 0.0
            disk_str = f"{_fmt_kb(disk_used // 1024)} / {_fmt_kb(disk_total // 1024)} ({disk_pct:.0f}%)"
        except OSError:
            disk_str = "N/A"

        # ---- process / platform ------------------------------------- #
        pid = os.getpid()
        rss_mb = _process_rss_mb()
        threads = _process_threads()
        process_str = f"PID {pid} · {rss_mb}MB RSS · {threads} threads"
        host_str = (
            f"{platform.node()} ({platform.system()} {platform.release()} {platform.machine()})"
        )
        python_str = f"{platform.python_implementation()} {platform.python_version()}"

        lines = [
            sym.status_line(t("system.bot_uptime"), bot_uptime),
            sym.status_line(t("system.uptime"), sys_uptime),
            "",
            sym.status_line(
                t("system.ram"),
                f"{_fmt_kb(mem_used)} / {_fmt_kb(mem_total)} ({mem_pct:.0f}%)",
            ),
            sym.status_line(
                t("system.swap"),
                f"{_fmt_kb(swap_used)} / {_fmt_kb(swap_total)}",
            ),
            sym.status_line(t("system.cpu"), f"{load_str} ({cores} cores)"),
            sym.status_line(t("system.disk"), disk_str),
            "",
            sym.status_line(t("system.process"), process_str),
            sym.status_line(t("system.host"), host_str),
            sym.status_line(t("system.python"), python_str),
        ]

        await ctx.client.reply(ctx.message, sym.box(t("system.title"), lines))
