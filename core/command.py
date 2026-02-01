"""
Command system for the WhatsApp bot.

Provides:
- Command base class for creating commands
- CommandContext with client, message, and args
- CommandLoader for auto-discovering commands
- Prefix matching (string or regex)
- Plugin system for external command directories
- Config-based aliases
"""

from __future__ import annotations

import importlib
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from difflib import get_close_matches
from pathlib import Path
from typing import TYPE_CHECKING

from core.client import BotClient
from core.message import MessageHelper
from core.runtime_config import runtime_config
from core.types import ChatType

if TYPE_CHECKING:
    pass


@dataclass
class CommandContext:
    """
    Context passed to command execution.

    Contains everything a command needs to process and respond.

    Attributes:
        client: The BotClient for sending responses
        message: MessageHelper with parsed message data
        args: List of arguments after the command name
        raw_args: The raw argument string after command name
        command_name: The command that was invoked
        prefix: The display-friendly command prefix
    """

    client: BotClient
    message: MessageHelper
    args: list[str] = field(default_factory=list)
    raw_args: str = ""
    command_name: str = ""

    @property
    def prefix(self) -> str:
        """Get the display-friendly command prefix."""
        return runtime_config.display_prefix


class Command(ABC):
    """
    Base class for all bot commands.

    To create a new command:
    1. Create a new file in commands/<group>/
    2. Create a class that inherits from Command
    3. Set the class attributes (name, description, usage)
    4. Implement the execute() method

    Example:
        class PingCommand(Command):
            name = "ping"
            description = "Check if bot is online"
            usage = "/ping"
            enabled = True
            private_only = False
            group_only = False

            async def execute(self, ctx: CommandContext) -> None:
                await ctx.client.reply(ctx.message, "Pong! 🏓")
    """

    name: str = ""
    aliases: list[str] = []
    description: str = ""
    usage: str = ""
    category: str = ""

    enabled: bool = True
    private_only: bool = False
    group_only: bool = False
    owner_only: bool = False
    admin_only: bool = False
    bot_admin_required: bool = False

    def can_execute(self, chat_type: ChatType) -> bool:
        """
        Check if this command can execute in the given chat type.

        Args:
            chat_type: The type of chat (PRIVATE or GROUP)

        Returns:
            True if the command can execute, False otherwise
        """
        if not self.enabled:
            return False

        if self.private_only and chat_type != ChatType.PRIVATE:
            return False

        return not (self.group_only and chat_type != ChatType.GROUP)

    @abstractmethod
    async def execute(self, ctx: CommandContext) -> None:
        """
        Execute the command.

        Override this method in your command class.

        Args:
            ctx: CommandContext with client, message, and args
        """
        pass

    def __repr__(self) -> str:
        return f"Command(name={self.name!r}, enabled={self.enabled})"


class CommandLoader:
    """
    Loads and manages bot commands.

    Auto-discovers commands from the commands/ directory and
    provides methods to find and execute them.

    Features:
    - Auto-discovery from commands/ directory
    - Plugin system for external directories
    - Config-based aliases
    - Fuzzy command matching for suggestions
    """

    def __init__(self) -> None:
        self._commands: dict[str, Command] = {}
        self._aliases: dict[str, str] = {}
        self._prefix_pattern: re.Pattern | None = None
        self._setup_prefix()
        self._load_aliases()

    def _get_prefix(self) -> str:
        """Get the current prefix from runtime config."""
        return runtime_config.prefix or ""

    def _setup_prefix(self) -> None:
        """Setup the prefix matching pattern (auto-detects regex vs string, handles empty)."""
        prefix = self._get_prefix()

        if not prefix:
            self._prefix_pattern = re.compile(r"^")
            self._current_prefix = ""
            return

        self._current_prefix = prefix

        regex_chars = r"^$.*+?{}[]|()\\"
        is_regex = any(c in prefix for c in regex_chars)

        if is_regex:
            self._prefix_pattern = re.compile(prefix)
        else:
            self._prefix_pattern = re.compile(re.escape(prefix))

    def _load_aliases(self) -> None:
        """Load command aliases from config."""
        try:
            aliases = runtime_config.get_nested("aliases", default={})
            if isinstance(aliases, dict):
                self._aliases = {k.lower(): v.lower() for k, v in aliases.items()}
        except Exception:
            pass

    def register(self, command: Command) -> None:
        """
        Register a command.

        Args:
            command: The command instance to register
        """
        self._commands[command.name.lower()] = command
        for alias in command.aliases:
            self._commands[alias.lower()] = command

    def get(self, name: str) -> Command | None:
        """
        Get a command by name, checking aliases first.

        Args:
            name: The command name (without prefix)

        Returns:
            The Command if found, None otherwise
        """
        name_lower = name.lower()

        if name_lower in self._aliases:
            name_lower = self._aliases[name_lower]

        return self._commands.get(name_lower)

    def find_similar(self, name: str, max_results: int = 3) -> list[str]:
        """
        Find similar command names for suggestions.

        Args:
            name: The mistyped command name
            max_results: Maximum number of suggestions

        Returns:
            List of similar command names
        """
        all_names = list({cmd.name for cmd in self._commands.values()})
        return get_close_matches(name.lower(), all_names, n=max_results, cutoff=0.5)

    @property
    def all_commands(self) -> dict[str, Command]:
        """Get all registered commands."""
        return self._commands.copy()

    @property
    def enabled_commands(self) -> dict[str, Command]:
        """Get all enabled commands."""
        return {name: cmd for name, cmd in self._commands.items() if cmd.enabled}

    @property
    def unique_commands(self) -> list[Command]:
        """Get unique commands (no duplicates from aliases)."""
        seen = set()
        result = []
        for cmd in self._commands.values():
            if cmd.name not in seen:
                seen.add(cmd.name)
                result.append(cmd)
        return result

    def get_commands_by_category(self) -> dict[str, list[Command]]:
        """
        Get commands organized by category.

        Returns:
            Dict mapping category name to list of commands
        """
        result: dict[str, list[Command]] = {}

        for cmd in self.unique_commands:
            if not cmd.enabled:
                continue
            category = cmd.category or "general"
            if category not in result:
                result[category] = []
            result[category].append(cmd)

        for category in result:
            result[category].sort(key=lambda c: c.name)

        return result

    def get_grouped_commands(self) -> dict[str, list[Command]]:
        """
        Get commands organized by category (for help menu).

        Returns:
            Dict mapping category name to list of commands
        """
        result: dict[str, list[Command]] = {}
        seen = set()

        for cmd in self._commands.values():
            if cmd.name in seen:
                continue
            if not cmd.enabled:
                continue

            seen.add(cmd.name)
            category = cmd.category or "Other"

            if category not in result:
                result[category] = []
            result[category].append(cmd)

        for category in result:
            result[category].sort(key=lambda c: c.name)

        return result

    def parse_command(self, text: str) -> tuple[str | None, str, list[str]]:
        """
        Parse a message to extract command and arguments.

        Args:
            text: The message text

        Returns:
            Tuple of (command_name, raw_args, args_list)
            Returns (None, "", []) if not a command
        """
        if not text:
            return None, "", []

        current_prefix = self._get_prefix()
        if not hasattr(self, "_current_prefix") or current_prefix != self._current_prefix:
            self._setup_prefix()

        match = self._prefix_pattern.match(text)
        if not match:
            return None, "", []

        remaining = text[match.end() :].strip()
        if not remaining:
            return None, "", []

        parts = remaining.split(maxsplit=1)
        command_name = parts[0].lower()
        raw_args = parts[1] if len(parts) > 1 else ""
        args = raw_args.split() if raw_args else []

        if not self._current_prefix:
            if not self.get(command_name):
                return None, "", []

        return command_name, raw_args, args

    def load_commands(self) -> int:
        """
        Auto-discover and load all commands from commands/ directory.

        Returns:
            Number of commands loaded
        """
        commands_dir = Path(__file__).parent.parent / "commands"

        if not commands_dir.exists():
            return 0

        count = 0

        for group_dir in commands_dir.iterdir():
            if not group_dir.is_dir():
                continue
            if group_dir.name.startswith("_"):
                continue

            category = group_dir.name.replace("_", " ").title()

            for file_path in group_dir.glob("*.py"):
                if file_path.name.startswith("_"):
                    continue

                module_name = f"commands.{group_dir.name}.{file_path.stem}"

                try:
                    module = importlib.import_module(module_name)

                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (
                            isinstance(attr, type)
                            and issubclass(attr, Command)
                            and attr is not Command
                            and hasattr(attr, "name")
                            and attr.name
                        ):
                            cmd = attr()
                            if not cmd.category:
                                cmd.category = category
                            self.register(cmd)
                            count += 1
                except Exception as e:
                    print(f"[!] Failed to load command from {module_name}: {e}")

        return count

    def reload_aliases(self) -> None:
        """Reload aliases from config."""
        self._load_aliases()


command_loader = CommandLoader()
