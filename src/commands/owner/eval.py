"""
Eval command - Execute Python code sent by owner.

⚠️ DANGEROUS: Only use if you know what you're doing.
This command can execute arbitrary Python code.
"""

import io
import traceback
from contextlib import redirect_stderr, redirect_stdout

from core.command import Command, CommandContext
from core.i18n import t, t_error, t_success


def _strip_code_block(code: str) -> str:
    """Strip markdown code block fences from code."""
    if code.startswith("```") and code.endswith("```"):
        code = code[3:-3]
        if code.startswith("python\n"):
            code = code[7:]
        elif code.startswith("py\n"):
            code = code[3:]
    return code


def _build_env(ctx: CommandContext) -> dict:
    """Build the execution environment for eval."""
    env = {
        "ctx": ctx,
        "bot": ctx.client,
        "msg": ctx.message,
        "message": ctx.message,
        "client": ctx.client,
        "raw": ctx.client.raw,
    }
    env.update(globals())
    return env


def _format_output(stdout: io.StringIO, stderr: io.StringIO, result) -> str | None:
    """Format eval output into a reply message."""
    parts = []

    stdout_val = stdout.getvalue()
    stderr_val = stderr.getvalue()

    if stdout_val:
        parts.append(f"*stdout:*\n```\n{stdout_val[:1000]}```")
    if stderr_val:
        parts.append(f"*stderr:*\n```\n{stderr_val[:1000]}```")
    if result is not None:
        result_str = repr(result)
        if len(result_str) > 1000:
            result_str = result_str[:1000] + "..."
        parts.append(f"*{t('eval.result')}:*\n```\n{result_str}```")

    return "\n\n".join(parts) if parts else None


def _format_error(e: Exception) -> str:
    """Format an exception into an error reply."""
    error_msg = "".join(traceback.format_exception(type(e), e, e.__traceback__))
    if len(error_msg) > 1500:
        error_msg = error_msg[:1500] + "..."
    return f"❌ *{t('eval.error')}:*\n```\n{error_msg}```"


class EvalCommand(Command):
    """Execute Python code (owner only)."""

    name = "eval"
    aliases = ["py", "exec"]
    description = "Execute Python code"
    usage = "eval <code>"
    owner_only = True

    async def execute(self, ctx: CommandContext) -> None:
        if not ctx.raw_args:
            await ctx.client.reply(ctx.message, t_error("eval.usage"))
            return

        code = _strip_code_block(ctx.raw_args)
        env = _build_env(ctx)
        stdout = io.StringIO()
        stderr = io.StringIO()

        try:
            with redirect_stdout(stdout), redirect_stderr(stderr):
                try:
                    result = eval(code, env)
                except SyntaxError:
                    exec(code, env)
                    result = None

            output = _format_output(stdout, stderr, result)
            await ctx.client.reply(ctx.message, output or t_success("eval.no_output"))
        except Exception as e:
            await ctx.client.reply(ctx.message, _format_error(e))


class AsyncEvalCommand(Command):
    """Execute async Python code (owner only)."""

    name = "aeval"
    aliases = ["apy", "aexec", "await"]
    description = "Execute async Python code"
    usage = "aeval <async code>"
    owner_only = True

    async def execute(self, ctx: CommandContext) -> None:
        if not ctx.raw_args:
            await ctx.client.reply(ctx.message, t_error("eval.async_usage"))
            return

        code = _strip_code_block(ctx.raw_args)
        env = _build_env(ctx)
        stdout = io.StringIO()
        stderr = io.StringIO()

        try:
            wrapped = "async def __aeval_func__():\n"
            for line in code.split("\n"):
                wrapped += f"    {line}\n"
            wrapped += "    return None"

            with redirect_stdout(stdout), redirect_stderr(stderr):
                exec(wrapped, env)
                result = await env["__aeval_func__"]()

            output = _format_output(stdout, stderr, result)
            await ctx.client.reply(ctx.message, output or t_success("eval.no_output"))
        except Exception as e:
            await ctx.client.reply(ctx.message, _format_error(e))
