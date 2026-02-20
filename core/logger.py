"""
Console and file logging utility using Rich and Python logging.

Provides styled console output and file logging for the bot.
"""

import json
import logging
import re
from datetime import datetime
from logging.handlers import RotatingFileHandler

from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from config.settings import FILE_LOGGING, LOG_LEVEL, VERBOSE_LOGGING
from core import symbols as sym
from core.constants import LOGS_DIR
from core.runtime_config import runtime_config

console = Console()


LOGS_DIR.mkdir(exist_ok=True)

LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
}

if FILE_LOGGING:
    bot_file_logger = logging.getLogger("bot_file")
    bot_file_logger.setLevel(logging.DEBUG)
    bot_file_logger.propagate = False
    bot_file_handler = RotatingFileHandler(
        LOGS_DIR / "bot.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    bot_file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    )
    bot_file_logger.addHandler(bot_file_handler)

    message_logger = logging.getLogger("messages")
    message_logger.setLevel(logging.DEBUG)
    message_logger.propagate = False
    message_handler = RotatingFileHandler(
        LOGS_DIR / "messages.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    message_handler.setFormatter(logging.Formatter("%(message)s"))
    message_logger.addHandler(message_handler)
else:
    bot_file_logger = None
    message_logger = None

if VERBOSE_LOGGING:
    logging.basicConfig(
        level=LOG_LEVELS.get(LOG_LEVEL, logging.INFO),
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(
                console=console,
                rich_tracebacks=True,
                tracebacks_show_locals=False,
                show_time=True,
                show_level=True,
                show_path=False,
                markup=True,
            )
        ],
    )


def strip_rich_markup(text: str) -> str:
    """Remove Rich markup tags from text for file logging."""
    return re.sub(r"\[/?[a-z0-9_ =]+\]", "", text)


def log_to_file(message: str, level: str = "INFO") -> None:
    """Log a message to bot.log file (strips Rich markup)."""
    if bot_file_logger:
        clean_message = strip_rich_markup(message)
        getattr(bot_file_logger, level.lower(), bot_file_logger.info)(clean_message)


def log_raw_message(event_data: dict) -> None:
    """Log raw message event data to messages.log as JSON."""
    if message_logger:
        entry = {
            "timestamp": datetime.now().isoformat(),
            "data": event_data,
        }
        message_logger.info(json.dumps(entry, ensure_ascii=False, default=str))

    if VERBOSE_LOGGING:
        console.print(
            f"[dim]↳ Raw:[/dim] [dim cyan]id={event_data.get('id', '?')}[/dim cyan] "
            f"[dim]text=[/dim][white]{str(event_data.get('text', ''))[:50]}[/white]"
        )


def log_command_execution(
    command: str,
    sender: str,
    chat_type: str,
    chat_id: str,
    success: bool,
    duration_ms: float = 0,
    error: str = "",
    prefix: str = "/",
) -> None:
    """Log command execution details."""
    status = "SUCCESS" if success else "FAILED"
    msg = f"CMD [{status}] {prefix}{command} | sender={sender} | chat={chat_type}:{chat_id} | time={duration_ms:.1f}ms"
    if error:
        msg += f" | error={error}"
    log_to_file(msg, "INFO" if success else "ERROR")

    if VERBOSE_LOGGING:
        status_color = "green" if success else "red"
        console.print(
            f"  [dim]└─[/dim] [{status_color}]{status}[/{status_color}] "
            f"[dim]in[/dim] [yellow]{duration_ms:.0f}ms[/yellow]"
            + (f" [red]error={error}[/red]" if error else "")
        )


def log_info(message: str) -> None:
    """Log an info message."""
    console.print(f"[cyan]{sym.INFO}[/cyan]  {message}")
    log_to_file(message)


def log_success(message: str) -> None:
    """Log a success message."""
    console.print(f"[green]{sym.SUCCESS}[/green]  {message}")
    log_to_file(message)


def log_warning(message: str) -> None:
    """Log a warning message."""
    console.print(f"[yellow]{sym.WARNING}[/yellow]  {message}")
    log_to_file(message, "WARNING")


def log_error(message: str) -> None:
    """Log an error message."""
    console.print(f"[red]{sym.ERROR}[/red]  {message}")
    log_to_file(message, "ERROR")


def log_step(message: str) -> None:
    """Log a step/action message."""
    console.print(f"[blue]{sym.ARROW}[/blue]  {message}")
    log_to_file(message)


def log_bullet(message: str) -> None:
    """Log a bullet point."""
    console.print(f"  [dim cyan]{sym.BULLET}[/dim cyan] [white]{message}[/white]")


def log_command(command: str, sender: str, chat_type: str, prefix: str = "/") -> None:
    """Log command execution to console with clear formatting."""
    chat_color = "magenta" if chat_type == "Group" else "blue"
    console.print(
        f"[green]→[/green] [bold yellow]{prefix}{command}[/bold yellow] "
        f"[dim]from[/dim] [cyan]{sender}[/cyan] "
        f"[dim]in[/dim] [{chat_color}]{chat_type}[/{chat_color}]"
    )


def log_command_skip(command: str, reason: str, prefix: str = "/") -> None:
    """Log when a command is skipped."""
    console.print(f"[dim]  ⊘ [yellow]{prefix}{command}[/yellow] [red]{reason}[/red][/dim]")


def log_debug(message: str) -> None:
    """Log a debug message (only if log level is DEBUG)."""
    level = runtime_config.get_nested("logging", "level", default="INFO")
    if level.upper() == "DEBUG":
        console.print(f"[dim cyan]{sym.SEARCH}[/dim cyan]  [dim]{message}[/dim]")
        log_to_file(message, "DEBUG")


def show_banner(title: str, subtitle: str = "") -> None:
    """Show a styled ASCII art banner."""
    logo_raw = (
        "████████\n"
        "██████████████████\n"
        "████              ████\n"
        "███                    ███\n"
        "███        ██ ███    ███   ███\n"
        "███      █████ ██████████    ███\n"
        "██     ████       ███████     ██\n"
        "██     ████          █ ███      ██\n"
        "██     ███           █ ███      ██\n"
        "██     ███           █ ███      ██\n"
        "██     ████          █ ███      ██\n"
        "██     ████       ███ ███     ██\n"
        "███      █████ ██████ ███    ███\n"
        "███        ██ ██     ███   ███\n"
        "███                    ███\n"
        "████              ████\n"
        "██████████████████\n"
        "████████"
    )
    logo = Text(logo_raw, style="bold green")
    console.print(logo, justify="center")
    console.print()
    text = Text(title, style="bold green")
    if subtitle:
        text.append(f"\n{subtitle}", style="dim green")
    console.print(text, justify="center")


def show_qr_prompt() -> None:
    """Show QR code scan prompt."""
    console.print()
    console.print(
        Panel(
            "[bold]▶ Scan QR Code[/bold]\n\n"
            "Open WhatsApp on your phone:\n"
            "  1. Go to Settings → Linked Devices\n"
            "  2. Tap 'Link a Device'\n"
            "  3. Scan the QR code below",
            title="[cyan]Login Required[/cyan]",
            border_style="cyan",
        )
    )
    console.print()


def show_pair_help() -> None:
    """Show pair code help panel."""
    console.print(
        Panel(
            "[dim]Open WhatsApp on your phone:\n"
            "  1. Go to Settings → Linked Devices\n"
            "  2. Tap 'Link a Device'\n"
            "  3. Select 'Link with phone number instead'\n"
            "  4. Enter this code[/dim]",
            title="[cyan]▶ Enter Pair Code[/cyan]",
            border_style="cyan",
        )
    )
    console.print()


def show_connected(device: str, bot_name: str, commands_count: int) -> None:
    """Show connection success panel."""
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="dim")
    table.add_column("Value", style="bold")
    table.add_row("Device", device)
    table.add_row("Bot Name", bot_name)
    table.add_row("Commands", str(commands_count))

    console.print()
    console.print(
        Panel(
            table,
            title="[green]✓ Connected[/green]",
            border_style="green",
        )
    )
    console.print()


def show_message(chat_type: str, sender: str, text: str) -> None:
    """Show incoming message log."""
    type_color = "magenta" if chat_type == "Group" else "blue"
    console.print(
        f"[dim]{chat_type}[/dim] "
        f"[{type_color}]{sender}[/{type_color}]: "
        f"[white]{text[:80]}{'...' if len(text) > 80 else ''}[/white]"
    )
