"""
Add Command - Dynamically add new commands to the bot via code.

Allows the owner to send Python code that defines a Command class,
which will be verified, saved, and registered.
"""

import ast
import importlib
import sys
from pathlib import Path

from core import symbols as sym
from core.command import Command, CommandContext, command_loader
from core.i18n import t, t_error, t_info, t_success, t_warning
from core.logger import log_error, log_info

DYNAMIC_COMMANDS_DIR = Path(__file__).parent.parent / "dynamic"


class AddCommandCommand(Command):
    """Add a new command to the bot by sending code."""

    name = "addcommand"
    aliases = ["addcmd", "newcmd"]
    description = "Add a new command by sending Python code"
    usage = "addcommand <code>"
    owner_only = True

    async def execute(self, ctx: CommandContext) -> None:
        if not ctx.raw_args:
            await self._show_help(ctx)
            return

        code = ctx.raw_args

        if code.startswith("```") and code.endswith("```"):
            code = code[3:-3]
            if code.startswith("python\n"):
                code = code[7:]
            elif code.startswith("py\n"):
                code = code[3:]

        result = self._verify_command_code(code)

        if not result["valid"]:
            await ctx.client.reply(
                ctx.message, t_error("addcommand.invalid_code", error=result["error"])
            )
            return

        cmd_name = result["command_name"]

        existing = command_loader.get(cmd_name)
        if existing:
            await ctx.client.reply(
                ctx.message, t_warning("addcommand.exists", name=cmd_name, prefix=ctx.prefix)
            )
            return

        try:
            saved_path = self._save_command(cmd_name, code)
            new_cmd = self._load_command(cmd_name, saved_path)

            if new_cmd:
                command_loader.register(new_cmd)

                p = ctx.prefix
                msg = sym.box(
                    t("addcommand.added_title"),
                    [
                        f"{t('addcommand.name_label')}: `{new_cmd.name}`",
                        f"{t('addcommand.desc_label')}: {new_cmd.description}",
                        f"{t('addcommand.usage_label')}: `{new_cmd.usage}`",
                        "",
                        t("addcommand.try_it", prefix=p, name=new_cmd.name),
                    ],
                )
                await ctx.client.reply(ctx.message, msg)
                log_info(f"[ADDCMD] Added new command: {new_cmd.name}")
            else:
                await ctx.client.reply(ctx.message, t_error("addcommand.load_failed"))
        except Exception as e:
            log_error(f"[ADDCMD] Error adding command: {e}")
            await ctx.client.reply(ctx.message, t_error("addcommand.error", error=str(e)))

    async def _show_help(self, ctx: CommandContext) -> None:
        """Show help for adding commands."""
        p = ctx.prefix
        msg = sym.box(
            t("addcommand.help_title"),
            [
                t("addcommand.help_desc"),
                "",
                f"*{t('addcommand.required_structure')}:*",
                "```python",
                "from core.command import Command, CommandContext",
                "",
                "class MyCommand(Command):",
                '    name = "mycommand"',
                '    description = "What it does"',
                f'    usage = "{p}mycommand"',
                "",
                "    async def execute(self, ctx):",
                "        await ctx.client.reply(",
                "            ctx.message,",
                '            "Hello!"',
                "        )",
                "```",
                "",
                f"*{t('addcommand.requirements')}:*",
                t("addcommand.req_inherit"),
                t("addcommand.req_name"),
                t("addcommand.req_execute"),
                t("addcommand.req_valid"),
            ],
        )
        await ctx.client.reply(ctx.message, msg)

    def _verify_command_code(self, code: str) -> dict:
        """
        Verify that the code is a valid command.

        Returns:
            dict with keys: valid (bool), error (str), command_name (str)
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {
                "valid": False,
                "error": f"{t('addcommand.syntax_error')}: {e.msg} (line {e.lineno})",
                "command_name": None,
            }

        command_class = None
        command_name = None

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    base_name = None
                    if isinstance(base, ast.Name):
                        base_name = base.id
                    elif isinstance(base, ast.Attribute):
                        base_name = base.attr

                    if base_name == "Command":
                        command_class = node
                        break

        if not command_class:
            return {
                "valid": False,
                "error": t("addcommand.no_command_class"),
                "command_name": None,
            }

        has_name = False
        has_execute = False

        for item in command_class.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and target.id == "name":
                        has_name = True
                        if isinstance(item.value, ast.Constant):
                            command_name = item.value.value

            if isinstance(item, ast.AsyncFunctionDef) and item.name == "execute":
                has_execute = True
            elif isinstance(item, ast.FunctionDef) and item.name == "execute":
                has_execute = True

        if not has_name:
            return {
                "valid": False,
                "error": t("addcommand.missing_name"),
                "command_name": None,
            }

        if not has_execute:
            return {
                "valid": False,
                "error": t("addcommand.missing_execute"),
                "command_name": None,
            }

        if not command_name:
            return {
                "valid": False,
                "error": t("addcommand.cannot_determine_name"),
                "command_name": None,
            }

        try:
            compile(code, "<string>", "exec")
        except Exception as e:
            return {
                "valid": False,
                "error": f"{t('addcommand.compile_error')}: {e}",
                "command_name": None,
            }

        return {"valid": True, "error": None, "command_name": command_name}

    def _save_command(self, name: str, code: str) -> Path:
        """Save command code to a file."""
        DYNAMIC_COMMANDS_DIR.mkdir(parents=True, exist_ok=True)

        init_file = DYNAMIC_COMMANDS_DIR / "__init__.py"
        if not init_file.exists():
            init_file.write_text("# Dynamic commands\n")
        safe_name = name.replace(" ", "_").lower()
        file_path = DYNAMIC_COMMANDS_DIR / f"{safe_name}.py"
        file_path.write_text(code, encoding="utf-8")

        return file_path

    def _load_command(self, name: str, file_path: Path) -> Command | None:
        """Load command from saved file."""
        try:
            module_name = f"commands.dynamic.{file_path.stem}"

            if module_name in sys.modules:
                del sys.modules[module_name]

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
                    return attr()

            return None
        except Exception as e:
            log_error(f"[ADDCMD] Failed to load command: {e}")
            return None


class DeleteCommandCommand(Command):
    """Delete a dynamically added command."""

    name = "delcommand"
    aliases = ["delcmd", "rmcmd", "removecommand"]
    description = "Delete a dynamically added command"
    usage = "delcommand <name>"
    owner_only = True

    async def execute(self, ctx: CommandContext) -> None:
        if not ctx.args:
            await ctx.client.reply(ctx.message, t_error("addcommand.del_usage"))
            return

        cmd_name = ctx.args[0].lower()

        safe_name = cmd_name.replace(" ", "_")
        file_path = DYNAMIC_COMMANDS_DIR / f"{safe_name}.py"

        if not file_path.exists():
            await ctx.client.reply(ctx.message, t_error("addcommand.not_dynamic", name=cmd_name))
            return

        try:
            if cmd_name in command_loader._commands:
                cmd = command_loader._commands[cmd_name]
                keys_to_remove = [cmd_name]
                if hasattr(cmd, "aliases"):
                    keys_to_remove.extend(cmd.aliases)

                for key in keys_to_remove:
                    command_loader._commands.pop(key.lower(), None)

            file_path.unlink()

            module_name = f"commands.dynamic.{safe_name}"
            if module_name in sys.modules:
                del sys.modules[module_name]

            await ctx.client.reply(ctx.message, t_success("addcommand.deleted", name=cmd_name))
            log_info(f"[DELCMD] Deleted dynamic command: {cmd_name}")

        except Exception as e:
            log_error(f"[DELCMD] Error deleting command: {e}")
            await ctx.client.reply(ctx.message, t_error("addcommand.del_error", error=str(e)))


class ListDynamicCommandsCommand(Command):
    """List all dynamically added commands."""

    name = "listdynamic"
    aliases = ["dynamiccmds", "listdyn"]
    description = "List all dynamically added commands"
    usage = "listdynamic"
    owner_only = True

    async def execute(self, ctx: CommandContext) -> None:
        if not DYNAMIC_COMMANDS_DIR.exists():
            await ctx.client.reply(ctx.message, t_info("addcommand.no_commands"))
            return

        files = list(DYNAMIC_COMMANDS_DIR.glob("*.py"))
        files = [f for f in files if f.name != "__init__.py"]

        if not files:
            await ctx.client.reply(ctx.message, t_info("addcommand.no_commands"))
            return

        items = []
        for f in sorted(files):
            cmd_name = f.stem
            cmd = command_loader.get(cmd_name)
            if cmd:
                items.append(f"`{cmd.name}` - {cmd.description}")
            else:
                items.append(f"`{cmd_name}` _({t('addcommand.not_loaded')})_")

        await ctx.client.reply(ctx.message, sym.section(t("addcommand.list_title"), items))
