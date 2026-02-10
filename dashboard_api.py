"""
Dashboard API Server.

A FastAPI backend that exposes bot configuration and stats to the dashboard.
Run alongside the bot or separately.
"""

import base64
import os
import secrets
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.utils import get_authorization_scheme_param
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent))

from core.command import command_loader
from core.runtime_config import runtime_config
from core.session import session_state
from core.storage import Storage

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
    dependencies=[Depends(get_current_username)],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


@app.post("/api/send-message")
async def send_message(req: MessageRequest):
    """Send a message via the bot."""
    from core.shared import get_bot

    bot = get_bot()
    if not await check_bot_logged_in(bot) or bot is None:
        raise HTTPException(status_code=503, detail="Bot not connected")

    try:
        await bot.send(req.to, req.text)
        return {"success": True, "message": "Message sent"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/api/send-media", dependencies=[Depends(get_current_username)])
async def send_media(
    to: str = Form(...),
    type: str = Form(...),
    caption: str = Form(""),
    file: UploadFile = File(...),
):
    """Send media via the bot."""
    from core.shared import get_bot

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


@app.get("/api/status")
async def get_status():
    """Get bot status."""
    from core.shared import get_bot

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


@app.get("/api/auth/status")
async def get_auth_status():
    """Get current authentication status."""
    from core.shared import get_bot

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


@app.get("/api/auth/qr")
async def get_qr():
    """Get current QR code."""
    if not session_state.qr_code:
        return {"qr": None}
    return {"qr": session_state.qr_code}


@app.post("/api/auth/pair")
async def start_pairing(req: PairRequest):
    """Start pairing with phone number."""
    runtime_config.set_nested("bot", "login_method", "pair_code")
    runtime_config.set_nested("bot", "phone_number", req.phone)
    runtime_config._save()

    return {
        "success": True,
        "message": "Login method updated to Pair Code. Please restart the bot.",
    }


@app.get("/api/config")
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


@app.put("/api/config")
async def update_config(update: ConfigUpdate):
    """Update a configuration value."""
    try:
        runtime_config.set_nested(update.section, update.key, update.value)
        runtime_config._save()
        return {"success": True, "message": f"Updated {update.section}.{update.key}"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/api/commands")
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


@app.patch("/api/commands/{name}")
async def toggle_command(name: str, toggle: CommandToggle):
    """Enable or disable a command."""
    disabled = runtime_config.get("disabled_commands", [])

    if toggle.enabled and name in disabled:
        disabled.remove(name)
    elif not toggle.enabled and name not in disabled:
        disabled.append(name)

    runtime_config.set("disabled_commands", disabled)
    runtime_config._save()

    return {"success": True, "name": name, "enabled": toggle.enabled}


@app.get("/api/groups")
async def get_groups():
    """Get all groups with settings."""
    from core.shared import get_bot
    from core.storage import GroupData

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


@app.get("/api/groups/{group_id}")
async def get_group(group_id: str):
    """Get a specific group's settings."""
    settings = storage.get_group_settings(group_id)
    if not settings:
        raise HTTPException(status_code=404, detail="Group not found")
    return settings


@app.put("/api/groups/{group_id}")
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
    return {"success": True}


@app.get("/api/stats")
async def get_stats():
    """Get bot statistics."""
    from core.shared import get_bot

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
        from core.scheduler import get_scheduler

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


@app.get("/api/logs")
async def get_logs(limit: int = 100, level: str | None = Query(None)):
    """Get recent bot logs."""
    import json

    logs_file = Path(__file__).parent / "logs" / "messages.log"

    if not logs_file.exists():
        logs_file = Path(__file__).parent / "logs" / "bot.log"

    if not logs_file.exists():
        return {"logs": []}

    try:

        def get_last_lines(filename, count):
            import os

            try:
                with open(filename, "rb") as f:
                    try:
                        f.seek(0, os.SEEK_END)
                        end_pos = f.tell()
                        buffer = bytearray()
                        lines_found = 0

                        chunk_size = 4096
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

        lines = get_last_lines(logs_file, limit + 10)

        parsed_lines = []
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue

            try:
                entry = json.loads(line)
                timestamp = entry.get("timestamp", "")
                data = entry.get("data", {})

                log_level = "info"

                if level and level.lower() != "info":
                    continue

                parsed_lines.append(
                    {
                        "id": data.get("id", timestamp),
                        "timestamp": timestamp,
                        "level": log_level,
                        "message": line,
                    }
                )
            except json.JSONDecodeError:
                import re

                match = re.match(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \[(\w+)\] (.*)", line)
                if match:
                    ts, lvl, msg = match.groups()

                    if level and level.upper() != lvl.upper():
                        continue

                    parsed_lines.append(
                        {"id": f"{ts}-{lvl}", "timestamp": ts, "level": lvl.lower(), "message": msg}
                    )
                else:
                    if level and level.lower() != "info":
                        continue
                    parsed_lines.append(
                        {"id": str(hash(line)), "timestamp": "", "level": "info", "message": line}
                    )

            if len(parsed_lines) >= limit:
                break

        return {"logs": parsed_lines}

    except Exception as e:
        return {"logs": [], "error": str(e)}


@app.get("/api/ratelimit")
async def get_rate_limit():
    """Get rate limit configuration."""
    from core.rate_limiter import rate_limiter

    config = rate_limiter.config
    return {
        "enabled": config.enabled,
        "user_cooldown": config.user_cooldown,
        "command_cooldown": config.command_cooldown,
        "burst_limit": config.burst_limit,
        "burst_window": config.burst_window,
    }


@app.put("/api/ratelimit")
async def update_rate_limit(settings: RateLimitSettings):
    """Update rate limit configuration."""
    from core.rate_limiter import rate_limiter

    rate_limiter.config.enabled = settings.enabled
    rate_limiter.config.user_cooldown = settings.user_cooldown
    rate_limiter.config.command_cooldown = settings.command_cooldown
    rate_limiter.config.burst_limit = settings.burst_limit
    rate_limiter.config.burst_window = settings.burst_window

    return {"success": True}


@app.get("/api/groups/{group_id}/welcome")
async def get_welcome(group_id: str):
    """Get welcome settings for a group."""
    from core.handlers.welcome import get_welcome_config

    config = get_welcome_config(group_id)
    return config


@app.put("/api/groups/{group_id}/welcome")
async def update_welcome(group_id: str, settings: WelcomeSettings):
    """Update welcome settings for a group."""
    from core.handlers.welcome import set_welcome_config

    set_welcome_config(group_id, enabled=settings.enabled, message=settings.message)
    return {"success": True}


@app.get("/api/groups/{group_id}/goodbye")
async def get_goodbye(group_id: str):
    """Get goodbye settings for a group."""
    from core.handlers.welcome import get_goodbye_config

    config = get_goodbye_config(group_id)
    return config


@app.put("/api/groups/{group_id}/goodbye")
async def update_goodbye(group_id: str, settings: GoodbyeSettings):
    """Update goodbye settings for a group."""
    from core.handlers.welcome import set_goodbye_config

    set_goodbye_config(group_id, enabled=settings.enabled, message=settings.message)
    return {"success": True}


@app.get("/api/tasks")
async def get_scheduled_tasks():
    """Get all scheduled tasks."""
    from core.scheduler import get_scheduler

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


@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str):
    """Delete a scheduled task."""
    from core.scheduler import get_scheduler

    scheduler = get_scheduler()
    if not scheduler:
        raise HTTPException(status_code=503, detail="Scheduler not available")

    if scheduler.remove_task(task_id):
        return {"success": True, "message": f"Task {task_id} deleted"}
    else:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")


@app.put("/api/tasks/{task_id}/toggle")
async def toggle_task(task_id: str, enabled: bool = True):
    """Enable or disable a scheduled task."""
    from core.scheduler import get_scheduler

    scheduler = get_scheduler()
    if not scheduler:
        raise HTTPException(status_code=503, detail="Scheduler not available")

    if scheduler.toggle_task(task_id, enabled):
        return {"success": True, "enabled": enabled}
    else:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")


# Notes API


class NoteCreate(BaseModel):
    """Model for creating a note."""

    name: str
    content: str
    media_type: str | None = None


class NoteUpdate(BaseModel):
    """Model for updating a note."""

    content: str
    media_type: str | None = None


@app.get("/api/groups/{group_id}/notes")
async def get_notes(group_id: str):
    """Get all notes for a group."""
    from core.storage import GroupData

    group_storage = GroupData(group_id)
    notes = group_storage.notes

    notes_list = []
    for name, data in notes.items():
        if isinstance(data, dict):
            notes_list.append(
                {
                    "name": name,
                    "content": data.get("content", ""),
                    "media_type": data.get("media_type", "text"),
                }
            )
        else:
            notes_list.append(
                {
                    "name": name,
                    "content": str(data),
                    "media_type": "text",
                }
            )

    return {"notes": notes_list, "count": len(notes_list)}


@app.post("/api/groups/{group_id}/notes")
async def create_note(group_id: str, note: NoteCreate):
    """Create a new note for a group."""
    from core.storage import GroupData

    group_storage = GroupData(group_id)
    notes = group_storage.notes

    if note.name in notes:
        raise HTTPException(status_code=400, detail=f"Note '{note.name}' already exists")

    notes[note.name] = {
        "content": note.content,
        "media_type": note.media_type or "text",
    }
    group_storage.save_notes(notes)

    return {"success": True, "message": f"Note '{note.name}' created"}


@app.put("/api/groups/{group_id}/notes/{note_name}")
async def update_note(group_id: str, note_name: str, note: NoteUpdate):
    """Update an existing note."""
    from core.storage import GroupData

    group_storage = GroupData(group_id)
    notes = group_storage.notes

    if note_name not in notes:
        raise HTTPException(status_code=404, detail=f"Note '{note_name}' not found")

    notes[note_name] = {
        "content": note.content,
        "media_type": note.media_type or "text",
    }
    group_storage.save_notes(notes)

    return {"success": True, "message": f"Note '{note_name}' updated"}


@app.delete("/api/groups/{group_id}/notes/{note_name}")
async def delete_note(group_id: str, note_name: str):
    """Delete a note."""
    from core.storage import GroupData

    group_storage = GroupData(group_id)
    notes = group_storage.notes

    if note_name not in notes:
        raise HTTPException(status_code=404, detail=f"Note '{note_name}' not found")

    del notes[note_name]
    group_storage.save_notes(notes)

    return {"success": True, "message": f"Note '{note_name}' deleted"}


class FilterCreate(BaseModel):
    """Model for creating a filter."""

    trigger: str
    response: str


@app.get("/api/groups/{group_id}/filters")
async def get_filters(group_id: str):
    """Get all filters for a group."""
    from core.storage import GroupData

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


@app.post("/api/groups/{group_id}/filters")
async def create_filter(group_id: str, filter_data: FilterCreate):
    """Create a new filter for a group."""
    from core.storage import GroupData

    group_storage = GroupData(group_id)
    filters = group_storage.filters

    if filter_data.trigger in filters:
        raise HTTPException(
            status_code=400, detail=f"Filter '{filter_data.trigger}' already exists"
        )

    filters[filter_data.trigger] = filter_data.response
    group_storage.save_filters(filters)

    return {"success": True, "message": f"Filter '{filter_data.trigger}' created"}


@app.delete("/api/groups/{group_id}/filters/{trigger}")
async def delete_filter(group_id: str, trigger: str):
    """Delete a filter."""
    from urllib.parse import unquote

    from core.storage import GroupData

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


@app.get("/api/groups/{group_id}/blacklist")
async def get_blacklist(group_id: str):
    """Get blacklisted words for a group."""
    from core.storage import GroupData

    group_storage = GroupData(group_id)
    words = group_storage.blacklist

    return {"words": words, "count": len(words)}


@app.post("/api/groups/{group_id}/blacklist")
async def add_blacklist_word(group_id: str, data: BlacklistWord):
    """Add a word to the blacklist."""
    from core.storage import GroupData

    group_storage = GroupData(group_id)
    words = group_storage.blacklist

    word = data.word.lower().strip()
    if word in words:
        raise HTTPException(status_code=400, detail=f"Word '{word}' already in blacklist")

    words.append(word)
    group_storage.save_blacklist(words)

    return {"success": True, "message": f"Word '{word}' added to blacklist"}


@app.delete("/api/groups/{group_id}/blacklist/{word}")
async def remove_blacklist_word(group_id: str, word: str):
    """Remove a word from the blacklist."""
    from urllib.parse import unquote

    from core.storage import GroupData

    word = unquote(word).lower().strip()
    group_storage = GroupData(group_id)
    words = group_storage.blacklist

    if word not in words:
        raise HTTPException(status_code=404, detail=f"Word '{word}' not in blacklist")

    words.remove(word)
    group_storage.save_blacklist(words)

    return {"success": True, "message": f"Word '{word}' removed from blacklist"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
