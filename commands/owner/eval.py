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

        code = ctx.raw_args

        if code.startswith("```") and code.endswith("```"):
            code = code[3:-3]
            if code.startswith("python\n"):
                code = code[7:]
            elif code.startswith("py\n"):
                code = code[3:]

        env = {
            "ctx": ctx,
            "bot": ctx.client,
            "msg": ctx.message,
            "message": ctx.message,
            "client": ctx.client,
            "raw": ctx.client.raw,
        }
        env.update(globals())

        stdout = io.StringIO()
        stderr = io.StringIO()

        try:
            with redirect_stdout(stdout), redirect_stderr(stderr):
                try:
                    result = eval(code, env)
                except SyntaxError:
                    exec(code, env)
                    result = None

            output_parts = []

            stdout_val = stdout.getvalue()
            stderr_val = stderr.getvalue()

            if stdout_val:
                output_parts.append(f"*stdout:*\n```\n{stdout_val[:1000]}```")
            if stderr_val:
                output_parts.append(f"*stderr:*\n```\n{stderr_val[:1000]}```")
            if result is not None:
                result_str = repr(result)
                if len(result_str) > 1000:
                    result_str = result_str[:1000] + "..."
                output_parts.append(f"*{t('eval.result')}:*\n```\n{result_str}```")

            if output_parts:
                await ctx.client.reply(ctx.message, "\n\n".join(output_parts))
            else:
                await ctx.client.reply(ctx.message, t_success("eval.no_output"))

        except Exception as e:
            error_msg = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            if len(error_msg) > 1500:
                error_msg = error_msg[:1500] + "..."
            await ctx.client.reply(ctx.message, f"❌ *{t('eval.error')}:*\n```\n{error_msg}```")


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

        code = ctx.raw_args

        if code.startswith("```") and code.endswith("```"):
            code = code[3:-3]
            if code.startswith("python\n"):
                code = code[7:]
            elif code.startswith("py\n"):
                code = code[3:]

        env = {
            "ctx": ctx,
            "bot": ctx.client,
            "msg": ctx.message,
            "message": ctx.message,
            "client": ctx.client,
            "raw": ctx.client.raw,
        }
        env.update(globals())

        stdout = io.StringIO()
        stderr = io.StringIO()

        try:
            wrapped_code = "async def __aeval_func__():\n"
            for line in code.split("\n"):
                wrapped_code += f"    {line}\n"
            wrapped_code += "    return None"

            with redirect_stdout(stdout), redirect_stderr(stderr):
                exec(wrapped_code, env)
                result = await env["__aeval_func__"]()

            output_parts = []

            stdout_val = stdout.getvalue()
            stderr_val = stderr.getvalue()

            if stdout_val:
                output_parts.append(f"*stdout:*\n```\n{stdout_val[:1000]}```")
            if stderr_val:
                output_parts.append(f"*stderr:*\n```\n{stderr_val[:1000]}```")
            if result is not None:
                result_str = repr(result)
                if len(result_str) > 1000:
                    result_str = result_str[:1000] + "..."
                output_parts.append(f"*{t('eval.result')}:*\n```\n{result_str}```")

            if output_parts:
                await ctx.client.reply(ctx.message, "\n\n".join(output_parts))
            else:
                await ctx.client.reply(ctx.message, t_success("eval.no_output"))

        except Exception as e:
            error_msg = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            if len(error_msg) > 1500:
                error_msg = error_msg[:1500] + "..."
            await ctx.client.reply(ctx.message, f"❌ *{t('eval.error')}:*\n```\n{error_msg}```")
