"""
Dashboard API Server.

A FastAPI backend that exposes bot configuration and stats to the dashboard.
Run alongside the bot or separately.
"""

import base64
import json
import os
import re
import secrets
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from fastapi import (
    APIRouter,
    Body,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.utils import get_authorization_scheme_param
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent))

from core.analytics import command_analytics
from core.command import command_loader
from core.event_bus import event_bus
from core.handlers.welcome import (
    get_goodbye_config,
    get_welcome_config,
    set_goodbye_config,
    set_welcome_config,
)
from core.rate_limiter import rate_limiter
from core.runtime_config import runtime_config
from core.scheduler import get_scheduler
from core.session import session_state
from core.shared import get_bot
from core.storage import GroupData, Storage

BOT_START_TIME = datetime.now()


async def get_current_username(request: Request) -> str:
    """
    Custom async HTTP Basic Auth - avoids the to_thread wrapper issue
    from Starlette's HTTPBasic security class.
    """
    authorization = request.headers.get("Authorization")

    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Basic"},
        )

    scheme, param = get_authorization_scheme_param(authorization)

    if scheme.lower() != "basic":
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication scheme",
            headers={"WWW-Authenticate": "Basic"},
        )

    try:
        decoded = base64.b64decode(param).decode("utf-8")
        cred_username, _, cred_password = decoded.partition(":")
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials format",
            headers={"WWW-Authenticate": "Basic"},
        ) from e

    expected_username = os.getenv("DASHBOARD_USERNAME", "admin")
    expected_password = os.getenv("DASHBOARD_PASSWORD", "admin")

    correct_username = secrets.compare_digest(cred_username, expected_username)
    correct_password = secrets.compare_digest(cred_password, expected_password)

    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )

    return cred_username


app = FastAPI(
    title="Zero Ichi Dashboard API",
    description="API for managing the Zero Ichi WhatsApp bot",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_api = APIRouter(dependencies=[Depends(get_current_username)])

storage = Storage()


async def check_bot_logged_in(bot) -> bool:
    """Safely check if the bot is logged in."""
    if not bot:
        return False
    try:
        return await bot.check_logged_in()
    except Exception as e:
        print(f"Error checking bot login state: {e}")
        return False


def get_uptime() -> str:
    """Get formatted uptime string."""
    delta = datetime.now() - BOT_START_TIME
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"


class ConfigUpdate(BaseModel):
    """Model for config updates."""

    section: str
    key: str
    value: Any


class MessageRequest(BaseModel):
    """Model for sending a message."""

    to: str
    text: str


class PairRequest(BaseModel):
    """Model for pairing request."""

    phone: str


class CommandToggle(BaseModel):
    """Model for command toggle."""

    name: str
    enabled: bool


class GroupSettings(BaseModel):
    """Model for group settings."""

    antilink: bool = False
    welcome: bool = False
    mute: bool = False


class RateLimitSettings(BaseModel):
    """Model for rate limit settings."""

    enabled: bool = True
    user_cooldown: float = 3.0
    command_cooldown: float = 2.0
    burst_limit: int = 5
    burst_window: float = 10.0


class WelcomeSettings(BaseModel):
    """Model for welcome message settings."""

    enabled: bool = True
    message: str = "Welcome to the group, {name}! 👋"


class GoodbyeSettings(BaseModel):
    """Model for goodbye message settings."""

    enabled: bool = False
    message: str = "Goodbye, {name}! 👋"


@_api.post("/api/send-message")
async def send_message(req: MessageRequest):
    """Send a message via the bot."""

    bot = get_bot()
    if not await check_bot_logged_in(bot) or bot is None:
        raise HTTPException(status_code=503, detail="Bot not connected")

    try:
        await bot.send(req.to, req.text)
        return {"success": True, "message": "Message sent"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@_api.post("/api/send-media", dependencies=[Depends(get_current_username)])
async def send_media(
    to: str = Form(...),
    type: str = Form(...),
    caption: str = Form(""),
    file: UploadFile = File(...),
):
    """Send media via the bot."""
    bot = get_bot()
    if not await check_bot_logged_in(bot) or bot is None:
        raise HTTPException(status_code=503, detail="Bot not connected")

    try:
        content = await file.read()
        await bot.send_media(
            to=to, media_type=type, data=content, caption=caption, filename=file.filename or "file"
        )

        return {"success": True, "message": f"{type.capitalize()} sent"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@_api.get("/api/status")
async def get_status():
    """Get bot status."""
    bot = get_bot()
    is_connected = False
    if bot:
        try:
            is_connected = await bot.check_connected()
        except Exception:
            pass

    return {
        "status": "online" if is_connected else "offline",
        "bot_name": runtime_config.bot_name,
        "prefix": runtime_config.prefix,
        "uptime": get_uptime(),
    }


@_api.get("/api/auth/status")
async def get_auth_status():
    """Get current authentication status."""
    bot = get_bot()

    bot_actual_logged_in = False
    if bot:
        bot_actual_logged_in = await check_bot_logged_in(bot)
        session_state.is_logged_in = bot_actual_logged_in

    if session_state.qr_code:
        session_state.is_logged_in = False

    is_logged_in = session_state.is_logged_in

    return {
        "is_logged_in": is_logged_in,
        "is_pairing": session_state.is_pairing,
        "pair_code": session_state.pair_code,
        "has_qr": session_state.qr_code is not None,
        "qr_code": session_state.qr_code,
        "login_method": runtime_config.login_method,
    }


@_api.get("/api/auth/qr")
async def get_qr():
    """Get current QR code."""
    if not session_state.qr_code:
        return {"qr": None}
    return {"qr": session_state.qr_code}


@_api.post("/api/auth/pair")
async def start_pairing(req: PairRequest):
    """Start pairing with phone number."""
    runtime_config.set_nested("bot", "login_method", "pair_code")
    runtime_config.set_nested("bot", "phone_number", req.phone)
    runtime_config._save()

    return {
        "success": True,
        "message": "Login method updated to Pair Code. Please restart the bot.",
    }


@_api.get("/api/config")
async def get_config():
    """Get all configuration."""
    return {
        "bot": {
            "name": runtime_config.bot_name,
            "prefix": runtime_config.prefix,
            "login_method": runtime_config.login_method,
            "owner_jid": runtime_config.get_owner_jid() or "",
            "auto_read": runtime_config.get_nested("bot", "auto_read", default=False),
            "auto_react": runtime_config.get_nested("bot", "auto_react", default=False),
        },
        "features": {
            "anti_delete": runtime_config.get_nested("features", "anti_delete", default=True),
            "anti_link": runtime_config.get_nested("features", "anti_link", default=False),
            "welcome": runtime_config.get_nested("features", "welcome", default=True),
            "notes": runtime_config.get_nested("features", "notes", default=True),
            "filters": runtime_config.get_nested("features", "filters", default=True),
            "blacklist": runtime_config.get_nested("features", "blacklist", default=True),
            "warnings": runtime_config.get_nested("features", "warnings", default=True),
        },
        "logging": {
            "log_messages": runtime_config.get_nested("logging", "log_messages", default=True),
            "verbose": runtime_config.get_nested("logging", "verbose", default=False),
            "level": runtime_config.get_nested("logging", "level", default="INFO"),
        },
        "anti_delete": {
            "forward_to": runtime_config.get_nested("anti_delete", "forward_to", default=""),
            "cache_ttl": runtime_config.get_nested("anti_delete", "cache_ttl", default=60),
        },
        "warnings": {
            "limit": runtime_config.get_nested("warnings", "limit", default=3),
            "action": runtime_config.get_nested("warnings", "action", default="kick"),
        },
    }


@_api.put("/api/config")
async def update_config(update: ConfigUpdate):
    """Update a configuration value."""
    try:
        runtime_config.set_nested(update.section, update.key, update.value)
        runtime_config._save()
        await event_bus.emit(
            "config_update", {"section": update.section, "key": update.key, "value": update.value}
        )
        return {"success": True, "message": f"Updated {update.section}.{update.key}"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@_api.get("/api/commands")
async def get_commands():
    """Get all commands with their status."""
    disabled = runtime_config.get("disabled_commands", [])

    if not command_loader._commands:
        command_loader.load_commands()

    commands = []
    grouped = command_loader.get_grouped_commands()
    for category, cmd_list in grouped.items():
        for cmd in cmd_list:
            commands.append(
                {
                    "name": cmd.name,
                    "description": cmd.description or "",
                    "category": category,
                    "enabled": cmd.name not in disabled,
                }
            )

    return {"commands": commands}


@_api.patch("/api/commands/{name}")
async def toggle_command(name: str, toggle: CommandToggle):
    """Enable or disable a command."""
    disabled = runtime_config.get("disabled_commands", [])

    if toggle.enabled and name in disabled:
        disabled.remove(name)
    elif not toggle.enabled and name not in disabled:
        disabled.append(name)

    runtime_config.set("disabled_commands", disabled)
    runtime_config._save()
    await event_bus.emit("command_update", {"name": name, "enabled": toggle.enabled})

    return {"success": True, "name": name, "enabled": toggle.enabled}


@_api.get("/api/groups")
async def get_groups():
    """Get all groups with settings."""
    bot = get_bot()
    groups = []

    if await check_bot_logged_in(bot) and bot is not None:
        try:
            live_groups = await bot.get_joined_groups()
            for g in live_groups:
                group_storage = GroupData(g["id"])
                groups.append(
                    {
                        "id": g["id"],
                        "name": g["name"],
                        "memberCount": g["member_count"],
                        "isAdmin": g["is_admin"],
                        "settings": {
                            "antilink": group_storage.anti_link.get("enabled", False),
                            "welcome": group_storage.load("welcome", {"enabled": True}).get(
                                "enabled", True
                            ),
                            "mute": group_storage.load("mute", {"enabled": False}).get(
                                "enabled", False
                            ),
                        },
                    }
                )
            return {"groups": groups}
        except Exception:
            pass

    groups_data = storage.get_all_groups()
    for group_id, settings in groups_data.items():
        groups.append(
            {
                "id": group_id,
                "name": settings.get("name", "Unknown"),
                "memberCount": settings.get("member_count", 0),
                "isAdmin": settings.get("is_admin", False),
                "settings": {
                    "antilink": settings.get("antilink", False),
                    "welcome": settings.get("welcome", True),
                    "mute": settings.get("mute", False),
                },
            }
        )

    return {"groups": groups}


@_api.post("/api/groups/{group_id}/leave")
async def leave_group(group_id: str):
    """Make the bot leave a group."""
    import time

    if not hasattr(leave_group, "_last_call"):
        leave_group._last_call = 0.0

    now = time.time()
    if now - leave_group._last_call < 10:
        remaining = int(10 - (now - leave_group._last_call))
        raise HTTPException(status_code=429, detail=f"Rate limited. Try again in {remaining}s")

    bot = get_bot()
    if not await check_bot_logged_in(bot) or bot is None:
        raise HTTPException(status_code=503, detail="Bot not connected")

    try:
        leave_group._last_call = now
        await bot.leave_group(group_id)
        await event_bus.emit("group_update", {"action": "leave", "group_id": group_id})
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@_api.post("/api/groups/bulk")
async def bulk_update_groups(
    group_ids: list[str] = Body(...),
    action: str = Body(...),
    value: bool = Body(...),
):
    """Bulk update group settings.

    Args:
        group_ids: List of group IDs to update.
        action: Setting to update (antilink, welcome, mute).
        value: New value for the setting.
    """
    valid_actions = ["antilink", "welcome", "mute"]
    if action not in valid_actions:
        raise HTTPException(
            status_code=400, detail=f"Invalid action. Must be one of {valid_actions}"
        )

    success_count = 0
    for gid in group_ids:
        try:
            group_storage = GroupData(gid)
            if action == "antilink":
                group_storage.set_anti_link(value)
            elif action == "welcome":
                current = group_storage.load("welcome", {"enabled": True, "message": "Welcome!"})
                current["enabled"] = value
                group_storage.save("welcome", current)
            elif action == "mute":
                current = group_storage.load("mute", {"enabled": False, "message": "Group Muted"})
                current["enabled"] = value
                group_storage.save("mute", current)
            success_count += 1
        except Exception:
            continue

    if success_count > 0:
        await event_bus.emit(
            "group_update",
            {"action": "bulk_update", "group_ids": group_ids, "setting": action, "value": value},
        )

    return {"success": True, "updated": success_count}


@_api.get("/api/groups/{group_id}")
async def get_group(group_id: str):
    """Get a specific group's settings."""
    settings = storage.get_group_settings(group_id)
    if not settings:
        raise HTTPException(status_code=404, detail="Group not found")
    return settings


@_api.put("/api/groups/{group_id}")
async def update_group(group_id: str, settings: GroupSettings):
    """Update a group's settings."""
    storage.set_group_settings(
        group_id,
        {
            "antilink": settings.antilink,
            "welcome": settings.welcome,
            "mute": settings.mute,
        },
    )
    await event_bus.emit(
        "group_update", {"action": "update", "group_id": group_id, "settings": settings.dict()}
    )
    return {"success": True}


@_api.get("/api/stats")
async def get_stats():
    """Get bot statistics."""
    bot = get_bot()
    active_groups = 0

    bot_logged_in = await check_bot_logged_in(bot)

    if bot and bot_logged_in:
        try:
            groups = await bot.get_joined_groups()
            active_groups = len(groups)
        except Exception:
            active_groups = len(storage.get_all_groups())
    else:
        active_groups = len(storage.get_all_groups())

    scheduled_tasks = 0
    try:
        scheduler = get_scheduler()
        if scheduler:
            scheduled_tasks = scheduler.get_tasks_count()
    except Exception:
        pass

    return {
        "messagesTotal": storage.get_stat("messages_total", 0),
        "commandsUsed": storage.get_stat("commands_used", 0),
        "activeGroups": active_groups,
        "scheduledTasks": scheduled_tasks,
        "uptime": get_uptime(),
    }


@_api.get("/api/logs")
async def get_logs(
    limit: int = 100,
    level: str | None = Query(None),
    source: str = Query("bot"),
):
    """Get recent bot logs.

    Args:
        limit: Max number of log entries to return.
        level: Filter by log level (info, warning, error, debug, command).
        source: Log source — 'bot' for structured bot.log, 'messages' for raw WA messages.
    """
    logs_dir = Path(__file__).parent.parent / "logs"

    if source == "messages":
        logs_file = logs_dir / "messages.log"
    else:
        logs_file = logs_dir / "bot.log"
        if not logs_file.exists():
            logs_file = logs_dir / "messages.log"

    if not logs_file.exists():
        return {"logs": [], "source": source}

    try:

        def get_last_lines(filename, count):
            try:
                with open(filename, "rb") as f:
                    try:
                        f.seek(0, os.SEEK_END)
                        end_pos = f.tell()
                        buffer = bytearray()
                        lines_found = 0

                        chunk_size = 8192
                        pos = end_pos

                        while pos > 0 and lines_found <= count:
                            read_size = min(chunk_size, pos)
                            pos -= read_size
                            f.seek(pos)
                            chunk = f.read(read_size)
                            buffer = chunk + buffer
                            lines_found = buffer.count(b"\n")

                        return [
                            line.decode("utf-8", errors="replace") for line in buffer.splitlines()
                        ]
                    except Exception:
                        with open(filename, encoding="utf-8") as f_text:
                            return f_text.readlines()
            except Exception:
                return []

        lines = get_last_lines(logs_file, limit + 20)

        parsed_lines = []
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue

            match = re.match(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \[(\w+)\] (.*)", line)
            if match:
                ts, lvl, msg = match.groups()
                log_level = lvl.lower()

                if msg.startswith("CMD ["):
                    log_level = "command"

                if level and level.lower() != log_level:
                    continue

                parsed_lines.append(
                    {
                        "id": f"{ts}-{hash(msg) % 100000}",
                        "timestamp": ts,
                        "level": log_level,
                        "message": msg,
                    }
                )
            else:
                try:
                    entry = json.loads(line)
                    timestamp = entry.get("timestamp", "")
                    data = entry.get("data", {})

                    if level and level.lower() != "info":
                        continue

                    parsed_lines.append(
                        {
                            "id": data.get("id", timestamp),
                            "timestamp": timestamp,
                            "level": "info",
                            "message": line,
                        }
                    )
                except json.JSONDecodeError:
                    if level and level.lower() != "info":
                        continue
                    parsed_lines.append(
                        {
                            "id": str(hash(line) % 10000000),
                            "timestamp": "",
                            "level": "info",
                            "message": line,
                        }
                    )

            if len(parsed_lines) >= limit:
                break

        return {"logs": parsed_lines, "source": source}

    except Exception as e:
        return {"logs": [], "source": source, "error": str(e)}


@_api.get("/api/ratelimit")
async def get_rate_limit():
    """Get rate limit configuration."""
    config = rate_limiter.config
    return {
        "enabled": config.enabled,
        "user_cooldown": config.user_cooldown,
        "command_cooldown": config.command_cooldown,
        "burst_limit": config.burst_limit,
        "burst_window": config.burst_window,
    }


@_api.put("/api/ratelimit")
async def update_rate_limit(settings: RateLimitSettings):
    """Update rate limit configuration."""
    rate_limiter.config.enabled = settings.enabled
    rate_limiter.config.user_cooldown = settings.user_cooldown
    rate_limiter.config.command_cooldown = settings.command_cooldown
    rate_limiter.config.burst_limit = settings.burst_limit
    rate_limiter.config.burst_window = settings.burst_window

    return {"success": True}


@_api.get("/api/groups/{group_id}/welcome")
async def get_welcome(group_id: str):
    """Get welcome settings for a group."""
    config = get_welcome_config(group_id)
    return config


@_api.put("/api/groups/{group_id}/welcome")
async def update_welcome(group_id: str, settings: WelcomeSettings):
    """Update welcome settings for a group."""
    set_welcome_config(group_id, enabled=settings.enabled, message=settings.message)
    return {"success": True}


@_api.get("/api/groups/{group_id}/goodbye")
async def get_goodbye(group_id: str):
    """Get goodbye settings for a group."""
    config = get_goodbye_config(group_id)
    return config


@_api.put("/api/groups/{group_id}/goodbye")
async def update_goodbye(group_id: str, settings: GoodbyeSettings):
    """Update goodbye settings for a group."""
    set_goodbye_config(group_id, enabled=settings.enabled, message=settings.message)
    return {"success": True}


@_api.get("/api/tasks")
async def get_scheduled_tasks():
    """Get all scheduled tasks."""

    scheduler = get_scheduler()
    if not scheduler:
        return {"tasks": [], "count": 0}

    tasks = []
    for task in scheduler.get_all_tasks():
        tasks.append(
            {
                "id": task.task_id,
                "type": task.task_type,
                "chat_jid": task.chat_jid,
                "message": task.message[:100] + "..." if len(task.message) > 100 else task.message,
                "trigger_time": task.trigger_time.isoformat() if task.trigger_time else None,
                "cron_expression": task.cron_expression,
                "interval_minutes": task.interval_minutes,
                "enabled": task.enabled,
                "created_at": task.created_at.isoformat() if task.created_at else None,
            }
        )

    return {"tasks": tasks, "count": len(tasks)}


@_api.post("/api/tasks")
async def create_task(task: dict = Body(...)):
    """Create a new scheduled task."""
    scheduler = get_scheduler()
    if not scheduler:
        raise HTTPException(status_code=503, detail="Scheduler not available")

    task_type = task.get("type")
    chat_jid = task.get("chat_jid")
    message = task.get("message")

    if not all([task_type, chat_jid, message]):
        raise HTTPException(status_code=400, detail="Missing required fields")

    try:
        if task_type == "reminder":
            trigger_time = task.get("trigger_time")
            if not trigger_time:
                raise HTTPException(status_code=400, detail="Missing trigger_time for reminder")

            new_task = scheduler.add_reminder(
                chat_jid=chat_jid,
                message=message,
                trigger_time=datetime.fromisoformat(trigger_time.replace("Z", "+00:00")),
                creator_jid="dashboard",
            )

        elif task_type == "auto_message":
            interval = task.get("interval_minutes")
            if not interval:
                raise HTTPException(
                    status_code=400, detail="Missing interval_minutes for auto_message"
                )

            new_task = scheduler.add_auto_message(
                chat_jid=chat_jid,
                message=message,
                interval_minutes=int(interval),
                creator_jid="dashboard",
            )

        elif task_type == "recurring":
            cron = task.get("cron_expression")
            if not cron:
                raise HTTPException(
                    status_code=400, detail="Missing cron_expression for recurring task"
                )

            new_task = scheduler.add_recurring(
                chat_jid=chat_jid,
                message=message,
                cron_expression=cron,
                creator_jid="dashboard",
            )

        else:
            raise HTTPException(status_code=400, detail="Invalid task type")

        return {"success": True, "task": new_task.to_dict()}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@_api.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str):
    """Delete a scheduled task."""

    scheduler = get_scheduler()
    if not scheduler:
        raise HTTPException(status_code=503, detail="Scheduler not available")

    if scheduler.remove_task(task_id):
        return {"success": True, "message": f"Task {task_id} deleted"}
    else:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")


@_api.put("/api/tasks/{task_id}/toggle")
async def toggle_task(task_id: str, enabled: bool = True):
    """Enable or disable a scheduled task."""

    scheduler = get_scheduler()
    if not scheduler:
        raise HTTPException(status_code=503, detail="Scheduler not available")

    if scheduler.toggle_task(task_id, enabled):
        return {"success": True, "enabled": enabled}
    else:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")


class NoteCreate(BaseModel):
    """Model for creating a note."""

    name: str
    content: str
    media_type: str | None = None


class NoteUpdate(BaseModel):
    """Model for updating a note."""

    content: str
    media_type: str | None = None


@_api.get("/api/groups/{group_id}/notes")
async def get_notes(group_id: str):
    """Get all notes for a group."""
    group_storage = GroupData(group_id)
    notes = group_storage.notes

    notes_list = []
    for name, data in notes.items():
        if isinstance(data, dict):
            notes_list.append(
                {
                    "name": name,
                    "content": data.get("content", ""),
                    "media_type": data.get("type", "text"),
                    "media_path": data.get("media_path"),
                }
            )
        else:
            notes_list.append(
                {
                    "name": name,
                    "content": str(data),
                    "media_type": "text",
                    "media_path": None,
                }
            )

    return {"notes": notes_list, "count": len(notes_list)}


@_api.post("/api/groups/{group_id}/notes")
async def create_note(group_id: str, note: NoteCreate):
    """Create a new note for a group."""
    group_storage = GroupData(group_id)
    notes = group_storage.notes

    if note.name in notes:
        raise HTTPException(status_code=400, detail=f"Note '{note.name}' already exists")

    notes[note.name] = {
        "type": note.media_type or "text",
        "content": note.content,
        "media_path": None,
    }
    group_storage.save_notes(notes)

    return {"success": True, "message": f"Note '{note.name}' created"}


@_api.put("/api/groups/{group_id}/notes/{note_name}")
async def update_note(group_id: str, note_name: str, note: NoteUpdate):
    """Update an existing note."""
    group_storage = GroupData(group_id)
    notes = group_storage.notes

    if note_name not in notes:
        raise HTTPException(status_code=404, detail=f"Note '{note_name}' not found")

    existing = notes[note_name] if isinstance(notes[note_name], dict) else {}
    notes[note_name] = {
        "type": note.media_type or existing.get("type", "text"),
        "content": note.content,
        "media_path": existing.get("media_path"),
    }
    group_storage.save_notes(notes)

    return {"success": True, "message": f"Note '{note_name}' updated"}


@_api.delete("/api/groups/{group_id}/notes/{note_name}")
async def delete_note(group_id: str, note_name: str):
    """Delete a note."""
    group_storage = GroupData(group_id)
    notes = group_storage.notes

    if note_name not in notes:
        raise HTTPException(status_code=404, detail=f"Note '{note_name}' not found")

    del notes[note_name]
    group_storage.save_notes(notes)

    return {"success": True, "message": f"Note '{note_name}' deleted"}


@_api.post("/api/groups/{group_id}/notes/{note_name}/media")
async def upload_note_media(
    group_id: str,
    note_name: str,
    file: UploadFile = File(...),
):
    """Upload media for a note."""
    from pathlib import Path

    group_storage = GroupData(group_id)
    notes = group_storage.notes

    if note_name not in notes:
        raise HTTPException(status_code=404, detail=f"Note '{note_name}' not found")

    ext = Path(file.filename or "file").suffix.lower()
    media_type_map = {
        ".jpg": "image",
        ".jpeg": "image",
        ".png": "image",
        ".gif": "image",
        ".webp": "sticker",
        ".mp4": "video",
        ".mkv": "video",
        ".avi": "video",
        ".mp3": "audio",
        ".ogg": "audio",
        ".wav": "audio",
        ".pdf": "document",
        ".doc": "document",
        ".docx": "document",
    }
    media_type = media_type_map.get(ext, "document")

    media_dir = Path(f"data/{group_id}/media")
    media_dir.mkdir(parents=True, exist_ok=True)

    file_path = media_dir / f"{note_name}{ext}"
    content = await file.read()
    file_path.write_bytes(content)

    note_data = (
        notes[note_name]
        if isinstance(notes[note_name], dict)
        else {"content": str(notes[note_name])}
    )
    note_data["type"] = media_type
    note_data["media_path"] = str(file_path.resolve())
    notes[note_name] = note_data
    group_storage.save_notes(notes)

    return {
        "success": True,
        "media_type": media_type,
        "media_path": str(file_path.resolve()),
    }


@_api.get("/api/groups/{group_id}/notes/{note_name}/media")
async def get_note_media(group_id: str, note_name: str):
    """Serve note media file."""
    from pathlib import Path

    group_storage = GroupData(group_id)
    notes = group_storage.notes

    if note_name not in notes:
        raise HTTPException(status_code=404, detail=f"Note '{note_name}' not found")

    note_data = notes[note_name]
    if not isinstance(note_data, dict) or not note_data.get("media_path"):
        raise HTTPException(status_code=404, detail="No media for this note")

    media_path = Path(note_data["media_path"])
    if not media_path.exists():
        raise HTTPException(status_code=404, detail="Media file not found")

    from fastapi.responses import FileResponse

    return FileResponse(str(media_path))


class FilterCreate(BaseModel):
    """Model for creating a filter."""

    trigger: str
    response: str


@_api.get("/api/groups/{group_id}/filters")
async def get_filters(group_id: str):
    """Get all filters for a group."""
    group_storage = GroupData(group_id)
    filters = group_storage.filters

    filters_list = []
    for trigger, response in filters.items():
        filters_list.append(
            {
                "trigger": trigger,
                "response": response if isinstance(response, str) else str(response),
            }
        )

    return {"filters": filters_list, "count": len(filters_list)}


@_api.post("/api/groups/{group_id}/filters")
async def create_filter(group_id: str, filter_data: FilterCreate):
    """Create a new filter for a group."""
    group_storage = GroupData(group_id)
    filters = group_storage.filters

    if filter_data.trigger in filters:
        raise HTTPException(
            status_code=400, detail=f"Filter '{filter_data.trigger}' already exists"
        )

    filters[filter_data.trigger] = filter_data.response
    group_storage.save_filters(filters)

    return {"success": True, "message": f"Filter '{filter_data.trigger}' created"}


@_api.delete("/api/groups/{group_id}/filters/{trigger}")
async def delete_filter(group_id: str, trigger: str):
    """Delete a filter."""
    trigger = unquote(trigger)
    group_storage = GroupData(group_id)
    filters = group_storage.filters

    if trigger not in filters:
        raise HTTPException(status_code=404, detail=f"Filter '{trigger}' not found")

    del filters[trigger]
    group_storage.save_filters(filters)

    return {"success": True, "message": f"Filter '{trigger}' deleted"}


class BlacklistWord(BaseModel):
    """Model for adding a blacklist word."""

    word: str


@_api.get("/api/groups/{group_id}/blacklist")
async def get_blacklist(group_id: str):
    """Get blacklisted words for a group."""
    group_storage = GroupData(group_id)
    words = group_storage.blacklist

    return {"words": words, "count": len(words)}


@_api.post("/api/groups/{group_id}/blacklist")
async def add_blacklist_word(group_id: str, data: BlacklistWord):
    """Add a word to the blacklist."""
    group_storage = GroupData(group_id)
    words = group_storage.blacklist

    word = data.word.lower().strip()
    if word in words:
        raise HTTPException(status_code=400, detail=f"Word '{word}' already in blacklist")

    words.append(word)
    group_storage.save_blacklist(words)

    return {"success": True, "message": f"Word '{word}' added to blacklist"}


@_api.delete("/api/groups/{group_id}/blacklist/{word}")
async def remove_blacklist_word(group_id: str, word: str):
    """Remove a word from the blacklist."""
    word = unquote(word).lower().strip()
    group_storage = GroupData(group_id)
    words = group_storage.blacklist

    if word not in words:
        raise HTTPException(status_code=404, detail=f"Word '{word}' not in blacklist")

    words.remove(word)
    group_storage.save_blacklist(words)

    return {"success": True, "message": f"Word '{word}' removed from blacklist"}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """WebSocket for real-time dashboard updates."""
    await ws.accept()
    queue = event_bus.subscribe()
    try:
        while True:
            event = await queue.get()
            await ws.send_json(event)
    except WebSocketDisconnect:
        pass
    finally:
        event_bus.unsubscribe(queue)


@_api.get("/api/analytics/commands")
async def get_analytics_commands(days: int = Query(7, ge=1, le=90), group_id: str = Query("")):
    """Get top commands by usage, optionally filtered by group."""
    return {
        "top_commands": command_analytics.get_top_commands(days, chat_jid=group_id),
        "total": command_analytics.get_total_commands(days, chat_jid=group_id),
        "days": days,
        "group_id": group_id,
    }


@_api.get("/api/analytics/timeline")
async def get_analytics_timeline(
    command: str = Query(""), days: int = Query(7, ge=1, le=90), group_id: str = Query("")
):
    """Get daily usage timeline, optionally filtered by group."""
    return {
        "timeline": command_analytics.get_usage_timeline(command, days, chat_jid=group_id),
        "command": command or "all",
        "days": days,
        "group_id": group_id,
    }


class AIConfigUpdate(BaseModel):
    """Model for AI configuration updates."""

    enabled: bool = False
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    trigger_mode: str = "mention"
    owner_only: bool = True


@_api.get("/api/ai-config")
async def get_ai_config():
    """Get AI configuration."""
    return {
        "enabled": runtime_config.get_nested("agentic_ai", "enabled", default=False),
        "provider": runtime_config.get_nested("agentic_ai", "provider", default="openai"),
        "model": runtime_config.get_nested("agentic_ai", "model", default="gpt-4o-mini"),
        "trigger_mode": runtime_config.get_nested("agentic_ai", "trigger_mode", default="mention"),
        "owner_only": runtime_config.get_nested("agentic_ai", "owner_only", default=True),
        "has_api_key": bool(
            runtime_config.get_nested("agentic_ai", "api_key", default="")
            or os.getenv("AI_API_KEY", "")
        ),
    }


@_api.put("/api/ai-config")
async def update_ai_config(config: AIConfigUpdate):
    """Update AI configuration."""
    runtime_config.set_nested("agentic_ai", "enabled", config.enabled)
    runtime_config.set_nested("agentic_ai", "provider", config.provider)
    runtime_config.set_nested("agentic_ai", "model", config.model)
    runtime_config.set_nested("agentic_ai", "trigger_mode", config.trigger_mode)
    runtime_config.set_nested("agentic_ai", "owner_only", config.owner_only)
    runtime_config._save()
    await event_bus.emit(
        "config_update", {"section": "agentic_ai", "key": "all", "value": config.dict()}
    )
    return {"success": True}


app.include_router(_api)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
