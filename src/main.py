"""
Zero Ichi - WhatsApp Bot entry point.
"""

import argparse
import asyncio
import base64
import importlib
import io
import os
import signal
import subprocess
import sys
import traceback
from copy import deepcopy
from pathlib import Path

import segno
from dotenv import load_dotenv
from google.protobuf.json_format import MessageToDict
from neonize.aioze.client import NewAClient
from neonize.events import (
    CallAcceptEv,
    CallOfferEv,
    CallOfferNoticeEv,
    CallTerminateEv,
    ConnectedEv,
    GroupInfoEv,
    MessageEv,
)
from neonize.proto.waCompanionReg.WAWebProtobufsCompanionReg_pb2 import DeviceProps
from neonize.utils.enum import BlocklistAction
from rich.console import Console
from watchfiles import awatch

from core.db import ensure_database_ready
from core.handlers.welcome import handle_member_join, handle_member_leave
from core.i18n import init_i18n, reload_locales
from core.jid_resolver import get_user_part, jids_match, resolve_pair
from core.logger import (
    console,
    log_bullet,
    log_error,
    log_info,
    log_raw_message,
    log_step,
    log_success,
    log_warning,
    show_banner,
    show_connected,
    show_pair_help,
    show_qr_prompt,
)
from core.runtime_config import runtime_config
from core.runtime_service_manager import RuntimeServiceManager
from core.scheduler import init_scheduler
from core.session import session_state
from core.shared import set_bot

_src_dir = Path(__file__).parent
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))
_project_root = _src_dir.parent
load_dotenv(_project_root / ".env")


def _parse_args():
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        prog="zero-ichi",
        description="Zero Ichi — WhatsApp Bot built with 💖",
    )
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("update", help="Pull latest code and sync dependencies")
    sub.add_parser("setup", help="Run interactive setup wizard")

    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--qr", action="store_true", help="Force QR code login")
    parser.add_argument(
        "--phone", type=str, metavar="NUMBER", help="Force pair code login with phone number"
    )
    parser.add_argument("--session", type=str, metavar="NAME", help="Override session name")
    parser.add_argument("--auto-reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--dashboard", action="store_true", help="Enable dashboard API")

    return parser.parse_args()


def _run_update():
    """Pull latest code and sync dependencies."""
    console = Console()
    console.print("[bold cyan]Updating Zero Ichi...[/bold cyan]\n")

    console.print("[dim]$ git pull[/dim]")
    result = subprocess.run(["git", "pull"], cwd=str(_project_root))
    if result.returncode != 0:
        console.print("[red]git pull failed[/red]")
        sys.exit(1)

    console.print()
    console.print("[dim]$ uv sync[/dim]")
    result = subprocess.run(["uv", "sync"], cwd=str(_project_root))
    if result.returncode != 0:
        console.print("[red]uv sync failed[/red]")
        sys.exit(1)

    console.print("\n[bold green]✅ Update complete![/bold green]")


def _prompt_text(label: str, default: str = "") -> str:
    """Prompt for text input with optional default value."""
    suffix = f" [{default}]" if default else ""
    value = input(f"{label}{suffix}: ").strip()
    return value if value else default


def _prompt_yes_no(label: str, default: bool) -> bool:
    """Prompt for yes/no input with default choice."""
    hint = "Y/n" if default else "y/N"
    while True:
        value = input(f"{label} ({hint}): ").strip().lower()
        if not value:
            return default
        if value in {"y", "yes", "1", "true", "on"}:
            return True
        if value in {"n", "no", "0", "false", "off"}:
            return False
        print("Please answer with y or n.")


def _prompt_choice(label: str, options: list[str], default: str) -> str:
    """Prompt for one value from a list of options."""
    opts = "/".join(options)
    while True:
        value = input(f"{label} ({opts}) [{default}]: ").strip().lower()
        selected = value or default
        if selected in options:
            return selected
        print(f"Please choose one of: {opts}")


def _prompt_int(
    label: str, default: int, min_value: int | None = None, max_value: int | None = None
) -> int:
    """Prompt for integer input with optional range bounds."""
    while True:
        raw = input(f"{label} [{default}]: ").strip()
        if not raw:
            value = default
        else:
            try:
                value = int(raw)
            except ValueError:
                print("Please enter a valid integer.")
                continue

        if min_value is not None and value < min_value:
            print(f"Value must be >= {min_value}.")
            continue
        if max_value is not None and value > max_value:
            print(f"Value must be <= {max_value}.")
            continue
        return value


def _prompt_float(
    label: str,
    default: float,
    min_value: float | None = None,
    max_value: float | None = None,
) -> float:
    """Prompt for float input with optional range bounds."""
    while True:
        raw = input(f"{label} [{default}]: ").strip()
        if not raw:
            value = default
        else:
            try:
                value = float(raw)
            except ValueError:
                print("Please enter a valid number.")
                continue

        if min_value is not None and value < min_value:
            print(f"Value must be >= {min_value}.")
            continue
        if max_value is not None and value > max_value:
            print(f"Value must be <= {max_value}.")
            continue
        return value


def _run_setup():
    """Run interactive setup wizard without starting the bot runtime."""
    current = deepcopy(runtime_config.all_config())
    candidate = deepcopy(current)

    bot_cfg = candidate.setdefault("bot", {})
    features = candidate.setdefault("features", {})
    anti_link = candidate.setdefault("anti_link", {})
    anti_spam = candidate.setdefault("anti_spam", {})
    ai_cfg = candidate.setdefault("agentic_ai", {})
    dashboard_cfg = candidate.setdefault("dashboard", {})
    rate_limit_cfg = candidate.setdefault("rate_limit", {})

    console.print("[bold cyan]Zero Ichi Setup Wizard[/bold cyan]")
    console.print("Configure key settings. Press Enter to keep current values.\n")

    bot_cfg["name"] = _prompt_text("Session name", str(bot_cfg.get("name", "zero_ichi_bot")))

    owner = _prompt_text("Owner JID", str(bot_cfg.get("owner_jid", "")))
    bot_cfg["owner_jid"] = owner

    prefix = _prompt_text("Command prefix", str(bot_cfg.get("prefix", "/")))
    bot_cfg["prefix"] = prefix or "/"

    login_method = _prompt_choice(
        "Login method",
        ["qr", "pair_code"],
        str(bot_cfg.get("login_method", "QR")).lower(),
    )
    bot_cfg["login_method"] = login_method.upper()
    if login_method == "pair_code":
        bot_cfg["phone_number"] = _prompt_text(
            "Pair-code phone number",
            str(bot_cfg.get("phone_number", "")),
        )
    else:
        bot_cfg["phone_number"] = ""

    bot_cfg["auto_read"] = _prompt_yes_no(
        "Enable auto-read",
        bool(bot_cfg.get("auto_read", False)),
    )
    bot_cfg["self_mode"] = _prompt_yes_no(
        "Enable self mode",
        bool(bot_cfg.get("self_mode", False)),
    )

    auto_react = _prompt_yes_no(
        "Enable auto-react",
        bool(bot_cfg.get("auto_react", False)),
    )
    bot_cfg["auto_react"] = auto_react
    if auto_react:
        bot_cfg["auto_react_emoji"] = _prompt_text(
            "Auto-react emoji",
            str(bot_cfg.get("auto_react_emoji", "👍")) or "👍",
        )
    else:
        bot_cfg["auto_react_emoji"] = ""

    dashboard_cfg["enabled"] = _prompt_yes_no(
        "Enable dashboard API",
        bool(dashboard_cfg.get("enabled", False)),
    )

    anti_link_enabled = _prompt_yes_no(
        "Enable anti-link",
        bool(features.get("anti_link", True)),
    )
    features["anti_link"] = anti_link_enabled
    anti_link["action"] = _prompt_choice(
        "Anti-link action",
        ["warn", "delete", "kick"],
        str(anti_link.get("action", "warn")),
    )

    anti_spam_enabled = _prompt_yes_no(
        "Enable anti-spam",
        bool(features.get("anti_spam", False)),
    )
    features["anti_spam"] = anti_spam_enabled
    anti_spam["action"] = _prompt_choice(
        "Anti-spam action",
        ["warn", "mute", "kick"],
        str(anti_spam.get("action", "warn")),
    )
    anti_spam["max_messages"] = _prompt_int(
        "Anti-spam max messages in window",
        int(anti_spam.get("max_messages", 5)),
        min_value=2,
        max_value=50,
    )
    anti_spam["window_seconds"] = _prompt_int(
        "Anti-spam window seconds",
        int(anti_spam.get("window_seconds", 10)),
        min_value=1,
        max_value=120,
    )
    anti_spam["whitelist_admins"] = _prompt_yes_no(
        "Whitelist admins for anti-spam",
        bool(anti_spam.get("whitelist_admins", True)),
    )

    ai_enabled = _prompt_yes_no("Enable AI", bool(ai_cfg.get("enabled", False)))
    features.setdefault("automation_rules", True)
    ai_cfg["enabled"] = ai_enabled

    if ai_enabled:
        ai_cfg["provider"] = _prompt_choice(
            "AI provider",
            ["openai", "google", "anthropic", "groq"],
            str(ai_cfg.get("provider", "openai")).lower(),
        )
        ai_cfg["model"] = _prompt_text(
            "AI model",
            str(ai_cfg.get("model", "gpt-5-mini")),
        )
        ai_cfg["trigger_mode"] = _prompt_choice(
            "AI trigger mode",
            ["mention", "reply", "always"],
            str(ai_cfg.get("trigger_mode", "mention")).lower(),
        )
        ai_cfg["owner_only"] = _prompt_yes_no(
            "AI owner-only mode",
            bool(ai_cfg.get("owner_only", True)),
        )

    current_key = str(ai_cfg.get("api_key", ""))
    if ai_enabled and not current_key:
        key_input = _prompt_text("AI API key")
        ai_cfg["api_key"] = key_input
    elif ai_enabled and current_key:
        if _prompt_yes_no("Update AI API key", False):
            ai_cfg["api_key"] = _prompt_text("AI API key", current_key)

    rate_limit_cfg["enabled"] = _prompt_yes_no(
        "Enable rate limiter",
        bool(rate_limit_cfg.get("enabled", True)),
    )
    rate_limit_cfg["user_cooldown"] = _prompt_float(
        "Rate limit user cooldown (seconds)",
        float(rate_limit_cfg.get("user_cooldown", 3.0)),
        min_value=0.0,
        max_value=60.0,
    )
    rate_limit_cfg["command_cooldown"] = _prompt_float(
        "Rate limit command cooldown (seconds)",
        float(rate_limit_cfg.get("command_cooldown", 2.0)),
        min_value=0.0,
        max_value=60.0,
    )
    rate_limit_cfg["burst_limit"] = _prompt_int(
        "Rate limit burst count",
        int(rate_limit_cfg.get("burst_limit", 5)),
        min_value=1,
        max_value=50,
    )
    rate_limit_cfg["burst_window"] = _prompt_float(
        "Rate limit burst window (seconds)",
        float(rate_limit_cfg.get("burst_window", 10.0)),
        min_value=1.0,
        max_value=120.0,
    )

    ok, details = runtime_config.validate_candidate(candidate)
    if not ok:
        console.print(f"\n[bold red]Configuration invalid:[/bold red] {details}")
        return

    console.print("\n[bold]Summary[/bold]")
    console.print(f"- session_name: {bot_cfg.get('name')}")
    console.print(f"- owner_jid: {bot_cfg.get('owner_jid') or '(not set)'}")
    console.print(f"- prefix: {bot_cfg.get('prefix')}")
    console.print(f"- login_method: {bot_cfg.get('login_method')}")
    if bot_cfg.get("login_method") == "PAIR_CODE":
        console.print(f"- phone_number: {bot_cfg.get('phone_number') or '(not set)'}")
    console.print(f"- auto_read: {'on' if bot_cfg.get('auto_read') else 'off'}")
    console.print(f"- self_mode: {'on' if bot_cfg.get('self_mode') else 'off'}")
    console.print(f"- auto_react: {'on' if bot_cfg.get('auto_react') else 'off'}")
    if bot_cfg.get("auto_react"):
        console.print(f"- auto_react_emoji: {bot_cfg.get('auto_react_emoji')}")
    console.print(f"- dashboard: {'on' if dashboard_cfg.get('enabled') else 'off'}")
    console.print(
        f"- anti_link: {'on' if anti_link_enabled else 'off'} ({anti_link.get('action')})"
    )
    console.print(
        f"- anti_spam: {'on' if anti_spam_enabled else 'off'} ({anti_spam.get('action')})"
    )
    console.print(
        f"- anti_spam limits: {anti_spam.get('max_messages')} msgs / {anti_spam.get('window_seconds')}s"
    )
    console.print(f"- ai: {'on' if ai_enabled else 'off'}")
    if ai_enabled:
        console.print(
            f"- ai provider/model/mode: {ai_cfg.get('provider')} / {ai_cfg.get('model')} / {ai_cfg.get('trigger_mode')}"
        )
    console.print(
        f"- rate_limit: {'on' if rate_limit_cfg.get('enabled') else 'off'} "
        f"(u:{rate_limit_cfg.get('user_cooldown')}s, c:{rate_limit_cfg.get('command_cooldown')}s)"
    )

    if not _prompt_yes_no("Apply these changes", True):
        console.print("[yellow]Setup cancelled.[/yellow]")
        return

    runtime_config.replace_config(candidate)
    console.print("\n[bold green]Setup complete.[/bold green]")
    console.print("You can now run: [bold]uv run zero-ichi[/bold]")


def _runtime_startup_settings() -> dict[str, str | bool]:
    """Resolve bot startup settings from live runtime config."""
    return {
        "bot_name": runtime_config.bot_name,
        "login_method": runtime_config.login_method,
        "phone_number": runtime_config.phone_number,
        "auto_reload": runtime_config.get_nested("bot", "auto_reload", default=True),
    }


def _session_filename(session_name: str) -> str:
    """Build a filesystem-safe Neonize session filename from configured session name."""
    safe = (
        (str(session_name or "").strip() or "zero_ichi_bot")
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
        .replace(":", "_")
    )
    return f"{safe}.session"


def _apply_cli_runtime_overrides(config, args) -> None:
    """Apply CLI flags as transient runtime config overrides."""
    if args.debug:
        config._config.setdefault("logging", {})["verbose"] = True
        config._config.setdefault("logging", {})["level"] = "DEBUG"

    if args.qr:
        config._config.setdefault("bot", {})["login_method"] = "QR"

    if args.phone:
        config._config.setdefault("bot", {})["login_method"] = "PAIR_CODE"
        config._config.setdefault("bot", {})["phone_number"] = args.phone

    if args.session:
        config._config.setdefault("bot", {})["name"] = args.session

    if args.auto_reload:
        config._config.setdefault("bot", {})["auto_reload"] = True

    if args.dashboard:
        config._config.setdefault("dashboard", {})["enabled"] = True


def _watch_targets(project_dir: Path) -> tuple[list[Path], list[Path]]:
    """Return directory and file watch targets for auto-reload."""
    locales_dir = project_dir / "locales"
    watch_dirs = [
        project_dir / "commands",
        project_dir / "core",
        project_dir / "config",
        project_dir / "ai",
        locales_dir,
    ]
    watch_files = [project_dir / "dashboard_api.py"]
    return watch_dirs, watch_files


def _module_name_from_path(path: Path, project_dir: Path) -> str:
    """Convert a Python file path into an importable module name."""
    rel_path = path.relative_to(project_dir)
    return str(rel_path.with_suffix("")).replace("\\", ".").replace("/", ".")


def _build_live_pipeline(*, import_module=importlib.import_module):
    """Build the middleware pipeline from the current imported module state."""
    middlewares_module = import_module("core.middlewares")
    return middlewares_module.build_pipeline()


def _message_runtime_bindings(*, import_module=importlib.import_module):
    """Resolve fresh MessageHelper and MessageContext bindings from current modules."""
    message_module = import_module("core.message")
    middleware_module = import_module("core.middleware")
    return message_module.MessageHelper, middleware_module.MessageContext


def _register_runtime_service_callbacks(service_manager, *, rate_limiter_module):
    """Register config-sensitive runtime refresh callbacks with the service manager."""

    def refresh_rate_limiter():
        rate_limiter_module.refresh_rate_limiter_from_runtime()

    service_manager.register_config_callback(refresh_rate_limiter)


def _build_dashboard_server(*, uvicorn_module, api_app):
    """Build a dashboard server instance using the current uvicorn module."""
    config = uvicorn_module.Config(api_app, host="0.0.0.0", port=8000, log_level="warning")
    return uvicorn_module.Server(config)


def _start_dashboard_via_manager(
    service_manager,
    *,
    enabled: bool,
    create_task_fn=asyncio.create_task,
    uvicorn_module=None,
    api_app=None,
):
    """Start dashboard API through the runtime service manager."""
    if not enabled:
        log_info("Dashboard API is disabled in config.json")
        return service_manager.start_dashboard(
            enabled=False,
            create_task_fn=create_task_fn,
            server_factory=lambda: None,
        )

    try:
        if uvicorn_module is None:
            import uvicorn as uvicorn_module
        if api_app is None:
            from dashboard_api import app as api_app

        task = service_manager.start_dashboard(
            enabled=True,
            create_task_fn=create_task_fn,
            server_factory=lambda: _build_dashboard_server(
                uvicorn_module=uvicorn_module, api_app=api_app
            ),
        )
        log_success("Dashboard API starting on http://localhost:8000")
        return task
    except ImportError:
        log_warning("Dashboard API not available (install fastapi & uvicorn)")
        return None
    except Exception as e:
        log_warning(f"Dashboard API failed to start: {e}")
        return None


def _maybe_start_dashboard_api(
    enabled: bool,
    *,
    create_task_fn=asyncio.create_task,
    uvicorn_module=None,
    api_app=None,
) -> None:
    """Start dashboard API server when enabled."""
    if not enabled:
        log_info("Dashboard API is disabled in config.json")
        return

    try:
        if uvicorn_module is None:
            import uvicorn as uvicorn_module
        if api_app is None:
            from dashboard_api import app as api_app

        config = uvicorn_module.Config(api_app, host="0.0.0.0", port=8000, log_level="warning")
        server = uvicorn_module.Server(config)
        create_task_fn(server.serve())
        log_success("Dashboard API starting on http://localhost:8000")
    except ImportError:
        log_warning("Dashboard API not available (install fastapi & uvicorn)")
    except Exception as e:
        log_warning(f"Dashboard API failed to start: {e}")


def _start_scheduler_if_needed(scheduler) -> None:
    """Start scheduler if present and not already running."""
    if scheduler and not scheduler._scheduler.running:
        scheduler.start()
        log_success("Scheduler started")


async def _connect_client(client, login_method: str, phone_number: str) -> bool:
    """Connect to WhatsApp via pair code or QR flow."""
    if login_method == "PAIR_CODE":
        log_step(f"Initiating Pair Code login for {phone_number}...")
        try:
            session_state.is_pairing = True
            session_state.phone_number = phone_number
            x = await client.PairPhone(phone_number, True)
            session_state.pair_code = x
            console.print(x)
            show_pair_help()
            return True
        except Exception as e:
            log_error(f"Pairing failed: {e}")
            return False

    await client.connect()
    return True


def _init_bot(args):
    """Initialize the bot infrastructure. Only called when actually running the bot."""
    ensure_database_ready()

    _ai_api_key = os.getenv("AI_API_KEY")
    if _ai_api_key and not os.getenv("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = str(_ai_api_key)

    _apply_cli_runtime_overrides(runtime_config, args)

    settings = _runtime_startup_settings()
    bot_name = str(settings["bot_name"])
    login_method = str(settings["login_method"])
    phone_number = str(settings["phone_number"])
    auto_reload = bool(settings["auto_reload"])

    from core import rate_limiter as rate_limiter_module
    from core.cache import message_cache
    from core.client import BotClient
    from core.command import command_loader
    from core.env import validate_environment

    validate_environment()

    client = NewAClient(
        _session_filename(bot_name),
        props=DeviceProps(
            os="Zero Ichi",
            platformType=DeviceProps.SAFARI,
        ),
    )
    bot = BotClient(client)
    bot.message_cache = message_cache

    init_i18n()
    set_bot(bot)

    scheduler = init_scheduler(bot)
    service_manager = RuntimeServiceManager(runtime_config)
    service_manager.bot = bot
    service_manager.message_cache = message_cache
    service_manager.scheduler = scheduler
    _register_runtime_service_callbacks(service_manager, rate_limiter_module=rate_limiter_module)
    service_manager.notify_config_changed()
    pipeline = service_manager.rebuild_pipeline(factory=_build_live_pipeline)

    _handled_call_ids: dict[str, float] = {}
    _CALL_GUARD_DEDUP_TTL_SECONDS = 120.0

    def _jid_to_str(jid_obj) -> str:
        """Convert a protobuf JID object into a jid@server string."""
        if not jid_obj:
            return ""
        user = getattr(jid_obj, "User", "")
        server = getattr(jid_obj, "Server", "")
        if not user or not server:
            return ""
        return f"{user}@{server}"

    def _extract_call_meta(event) -> tuple[str, str]:
        """Extract call_id and caller_jid from call events."""
        basic = getattr(event, "basicCallMeta", None)
        if not basic:
            return "", ""

        call_id = getattr(basic, "callID", "") or ""

        creator = _jid_to_str(getattr(basic, "callCreator", None))
        creator_alt = _jid_to_str(getattr(basic, "callCreatorAlt", None))
        candidates = [jid for jid in [creator, creator_alt] if jid]

        caller_jid = ""
        for jid in candidates:
            if jid.endswith("@s.whatsapp.net"):
                caller_jid = jid
                break
        if not caller_jid and candidates:
            caller_jid = candidates[0]

        return call_id, caller_jid

    def _is_duplicate_call_offer(call_id: str) -> bool:
        """Best-effort dedup for repeated call offer events."""
        if not call_id:
            return False

        now = asyncio.get_running_loop().time()
        for seen_id, ts in list(_handled_call_ids.items()):
            if now - ts > _CALL_GUARD_DEDUP_TTL_SECONDS:
                _handled_call_ids.pop(seen_id, None)

        seen = _handled_call_ids.get(call_id)
        if seen and now - seen <= _CALL_GUARD_DEDUP_TTL_SECONDS:
            return True

        _handled_call_ids[call_id] = now
        return False

    async def _is_whitelisted_caller(caller_jid: str) -> bool:
        """Return True if caller is in call guard whitelist."""
        whitelist = runtime_config.get_nested("call_guard", "whitelist", default=[])
        if not isinstance(whitelist, list):
            return False

        caller_user = caller_jid.split("@")[0].split(":")[0]

        for candidate in whitelist:
            if not isinstance(candidate, str) or not candidate.strip():
                continue

            entry = candidate.strip()
            try:
                if await jids_match(caller_jid, entry, bot):
                    return True
            except Exception:
                pass

            entry_user = entry.split("@")[0].split(":")[0]
            if entry_user and entry_user == caller_user:
                return True

        return False

    async def _resolve_call_jids(caller_jid: str) -> tuple[str, str]:
        """Resolve caller into PN/LID JIDs when possible."""
        try:
            pair = await bot.resolve_jid_pair(caller_jid)
            pn = str(pair.get("pn") or "").strip()
            lid = str(pair.get("lid") or "").strip()
            return pn, lid
        except Exception:
            return "", ""

    def _caller_display(caller_jid: str, pn_jid: str, lid_jid: str) -> str:
        """Format caller for logs and owner notices, preferring PN JID."""
        if pn_jid:
            number = get_user_part(pn_jid)
            if lid_jid:
                return f"{pn_jid} (number: {number}, lid: {lid_jid})"
            return f"{pn_jid} (number: {number})"
        if lid_jid:
            return lid_jid
        return caller_jid

    async def _handle_call_offer(event, source: str = "offer") -> None:
        """Handle incoming call-like events with configurable block action."""
        call_id, caller_jid = _extract_call_meta(event)
        if not caller_jid:
            log_warning(f"Call guard: incoming call has no caller JID (source={source})")
            return

        pn_jid, lid_jid = await _resolve_call_jids(caller_jid)
        caller_display = _caller_display(caller_jid, pn_jid, lid_jid)

        log_info(f"Incoming call ({source}): caller={caller_display} id={call_id or '-'}")

        cfg = runtime_config.get("call_guard", default={})
        if not isinstance(cfg, dict):
            return

        enabled = bool(cfg.get("enabled", False))
        action = str(cfg.get("action", "block")).lower()
        if not enabled or action == "off":
            return

        if _is_duplicate_call_offer(call_id):
            return

        if await runtime_config.is_owner_async(caller_jid, bot):
            log_info(f"Call guard: owner call ignored ({caller_display})")
            return

        if await _is_whitelisted_caller(caller_jid):
            log_info(f"Call guard: whitelisted caller ignored ({caller_display})")
            return

        delay = cfg.get("delay_seconds", 3)
        try:
            delay = int(delay)
        except (TypeError, ValueError):
            delay = 3
        delay = max(0, min(delay, 60))

        notify_target = pn_jid or caller_jid
        if bool(cfg.get("notify_caller", True)):
            try:
                await bot.send(notify_target, t("callguard.caller_notice"))
            except Exception as e:
                if notify_target != caller_jid:
                    try:
                        await bot.send(caller_jid, t("callguard.caller_notice"))
                    except Exception as fallback_error:
                        log_warning(
                            f"Call guard: failed to notify caller {caller_display}: {fallback_error}"
                        )
                else:
                    log_warning(f"Call guard: failed to notify caller {caller_display}: {e}")

        if delay > 0:
            await asyncio.sleep(delay)

        block_targets: list[str] = []
        for target in [pn_jid, lid_jid, caller_jid]:
            if target and target not in block_targets:
                block_targets.append(target)

        blocked_any = False
        for target in block_targets:
            try:
                await bot._client.update_blocklist(bot.to_jid(target), BlocklistAction.BLOCK)
                blocked_any = True
            except Exception as e:
                log_warning(f"Call guard: failed to block {target}: {e}")

        if blocked_any:
            log_warning(f"Call guard: blocked caller {caller_display} (call_id={call_id or '-'})")
        else:
            log_warning(
                f"Call guard: unable to block caller {caller_display} (call_id={call_id or '-'})"
            )

        if bool(cfg.get("notify_owner", True)):
            owner_jid = runtime_config.get_owner_jid()
            if owner_jid:
                try:
                    await bot.send(
                        owner_jid,
                        t(
                            "callguard.owner_notice",
                            caller=caller_display,
                            delay=delay,
                            call_id=call_id or "-",
                        ),
                    )
                except Exception as e:
                    log_warning(f"Call guard: failed to notify owner: {e}")

    @client.qr
    async def qr_handler(c: NewAClient, qr_data: bytes) -> None:
        """Handle QR code event - displays QR in terminal."""
        session_state.is_logged_in = False

        show_qr_prompt()
        qr = segno.make_qr(qr_data)
        qr.terminal(compact=True)

        buff = io.BytesIO()
        qr.save(buff, kind="png", scale=10)
        qr_b64 = base64.b64encode(buff.getvalue()).decode("utf-8")

        session_state.qr_code = qr_b64
        session_state.is_pairing = False

    @client.event(ConnectedEv)
    async def connected_handler(c: NewAClient, event: ConnectedEv) -> None:
        """Called when successfully connected to WhatsApp."""
        session_state.is_logged_in = True
        session_state.qr_code = None
        session_state.pair_code = None

        show_connected(
            device=event.device.User,
            bot_name=bot_name,
            commands_count=len(command_loader.enabled_commands),
        )

        log_info(
            f"Connected event fired, scheduler: {scheduler}, running: {scheduler._scheduler.running if scheduler else 'N/A'}"
        )
        service_manager.start_scheduler_if_needed()

        owner_jid = runtime_config.get_owner_jid()
        if owner_jid:
            await resolve_pair(owner_jid, bot)
            log_info(f"Preloaded JID cache for owner: {owner_jid}")

    @client.event(GroupInfoEv)
    async def group_info_handler(c: NewAClient, event: GroupInfoEv) -> None:
        """Handle group info events (join/leave)."""
        try:
            group_jid = f"{event.JID.User}@{event.JID.Server}" if event.JID else ""
            if not group_jid or not group_jid.endswith("@g.us"):
                return

            joined = list(event.Join)
            left = list(event.Leave)

            if not joined and not left:
                return

            for participant in joined:
                member_jid = f"{participant.User}@{participant.Server}" if participant else ""
                if not member_jid:
                    continue
                member_name = participant.User
                log_info(f"Member joined: {member_name} ({member_jid}) in {group_jid}")
                await handle_member_join(bot, group_jid, member_jid, member_name)

            for participant in left:
                member_jid = f"{participant.User}@{participant.Server}" if participant else ""
                if not member_jid:
                    continue
                member_name = participant.User
                log_info(f"Member left: {member_name} ({member_jid}) from {group_jid}")
                await handle_member_leave(bot, group_jid, member_jid, member_name)
        except Exception as e:
            log_warning(f"Error handling group info event: {e}")

    @client.event(CallOfferEv)
    async def call_offer_handler(c: NewAClient, event: CallOfferEv) -> None:
        """Handle incoming call offers based on call guard config."""
        try:
            await _handle_call_offer(event, source="offer")
        except Exception as e:
            log_warning(f"Error handling call offer event: {e}")

    @client.event(CallOfferNoticeEv)
    async def call_offer_notice_handler(c: NewAClient, event: CallOfferNoticeEv) -> None:
        """Handle incoming call offer notices (some devices emit this first)."""
        try:
            await _handle_call_offer(event, source="offer_notice")
        except Exception as e:
            log_warning(f"Error handling call offer notice event: {e}")

    @client.event(CallAcceptEv)
    async def call_accept_handler(c: NewAClient, event: CallAcceptEv) -> None:
        """Log call accept events for diagnostics."""
        try:
            call_id, caller_jid = _extract_call_meta(event)
            pn_jid, lid_jid = await _resolve_call_jids(caller_jid)
            caller_display = _caller_display(caller_jid, pn_jid, lid_jid)
            if call_id or caller_display:
                log_info(f"Call accepted: caller={caller_display or '-'} id={call_id or '-'}")
        except Exception:
            pass

    @client.event(CallTerminateEv)
    async def call_terminate_handler(c: NewAClient, event: CallTerminateEv) -> None:
        """Log call terminate events for diagnostics."""
        try:
            call_id, caller_jid = _extract_call_meta(event)
            pn_jid, lid_jid = await _resolve_call_jids(caller_jid)
            caller_display = _caller_display(caller_jid, pn_jid, lid_jid)
            reason = getattr(event, "reason", "") or ""
            if call_id or caller_display or reason:
                log_info(
                    f"Call terminated: caller={caller_display or '-'} id={call_id or '-'} reason={reason or '-'}"
                )

            await _handle_call_offer(event, source="terminate_fallback")
        except Exception:
            pass

    @client.event(MessageEv)
    async def message_handler(c: NewAClient, event: MessageEv) -> None:
        """Handle incoming messages through the middleware pipeline."""
        message_helper_cls, message_context_cls = _message_runtime_bindings()
        msg = message_helper_cls(event)

        try:
            raw_msg_dict = MessageToDict(event.Message)
        except Exception:
            raw_msg_dict = {"error": "Failed to convert protobuf"}

        try:
            log_raw_message(
                {
                    "id": event.Info.ID,
                    "chat": msg.chat_jid,
                    "sender": msg.sender_jid,
                    "sender_name": msg.sender_name,
                    "is_from_me": msg.is_from_me,
                    "is_group": msg.is_group,
                    "text": msg.text,
                    "timestamp": event.Info.Timestamp,
                    "raw_message": raw_msg_dict,
                }
            )
        except Exception as e:
            log_error(f"Failed to log raw message: {e}")

        try:
            ctx = message_context_cls(bot=bot, msg=msg, event=event)
            await pipeline.execute(ctx)
        except Exception as e:
            log_error(f"Unhandled error in message handler: {e}")
            log_error(traceback.format_exc())

    async def start_bot() -> None:
        """Main async entry point execution."""
        try:
            session_state.is_logged_in = False
            session_state.qr_code = None
            session_state.pair_code = None
            session_state.is_pairing = False

            show_banner("Zero Ichi", "WhatsApp Bot built with 💖")

            dashboard_enabled = runtime_config.get_nested("dashboard", "enabled", default=False)
            _start_dashboard_via_manager(service_manager, enabled=dashboard_enabled)

            log_step("Starting bot...")
            log_bullet(f"Session: {bot_name}")
            log_bullet(f"Login Method: {login_method}")

            num_commands = command_loader.load_commands()
            log_success(f"Loaded {num_commands} commands")

            log_step("Connecting to WhatsApp...")

            if not await _connect_client(client, login_method, phone_number):
                return

            service_manager.start_scheduler_if_needed()

            async def watch_and_reload():
                """Watch for file changes and reload commands and core modules."""
                project_dir = _src_dir
                locales_dir = project_dir / "locales"
                watch_dirs, watch_files = _watch_targets(project_dir)

                log_info("Auto-reload enabled. Watching for file changes...")

                async for changes in awatch(*watch_dirs, *watch_files):
                    for _, path in changes:
                        path = Path(path)
                        try:
                            if path.suffix == ".json" and (
                                path.parent == locales_dir or path.parent.name == "locales"
                            ):
                                reload_locales()
                                log_success(f"[b]↻ Reloaded:[/b] {path.name} (locales)")
                                continue

                            if path.suffix == ".py" and not path.name.startswith("_"):
                                module_name = _module_name_from_path(path, project_dir)

                                if module_name in sys.modules:
                                    importlib.reload(sys.modules[module_name])

                                if module_name == "dashboard_api":
                                    if "dashboard_api" in sys.modules:
                                        importlib.reload(sys.modules["dashboard_api"])
                                    log_success(f"[b]↻ Reloaded:[/b] {path.name} (API module)")
                                elif module_name.startswith("core."):
                                    from core.client import BotClient as ReloadedBotClient

                                    service_manager.reload_core_module(
                                        client=client,
                                        message_cache=message_cache,
                                        core_client_module=sys.modules["core.client"],
                                        bot_client_cls=ReloadedBotClient,
                                    )
                                    nonlocal bot, pipeline
                                    bot = service_manager.bot
                                    pipeline = service_manager.pipeline
                                    log_success(f"[b]↻ Reloaded:[/b] {path.name} (core module)")
                                else:
                                    command_loader._commands.clear()
                                    count = command_loader.load_commands()
                                    log_success(
                                        f"[b]↻ Reloaded:[/b] {path.name} ({count} commands)"
                                    )
                        except Exception as e:
                            log_error(f"Reload failed for {path.name}: {e}")

            if auto_reload:
                asyncio.create_task(watch_and_reload())
            else:
                log_info("Auto-reload disabled. Set 'auto_reload: true' in config.json to enable.")

            log_success("Bot is running! Press Ctrl+C to stop.")
            await client.idle()

        finally:
            console.print("\n\n[yellow]■[/yellow] Bot stopping...")
            try:
                await client.stop()
            except Exception:
                pass
            service_manager.stop_all()
            os._exit(0)

    def interrupt_handler(sig, frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGINT, interrupt_handler)

    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        pass
    finally:
        import threading

        print("Active threads at exit:")
        for t in threading.enumerate():
            print(f"  Thread: {t.name}, Daemon: {t.daemon}, Alive: {t.is_alive()}")


def main():
    """Entry point for the bot."""
    args = _parse_args()

    if args.command == "update":
        _run_update()
        return

    if args.command == "setup":
        _run_setup()
        return

    _init_bot(args)


if __name__ == "__main__":
    main()
