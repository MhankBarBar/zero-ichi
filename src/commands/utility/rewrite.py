"""Rewrite command - AI-powered text rewrite in different styles."""

from __future__ import annotations

from core import symbols as sym
from core.command import Command, CommandContext
from core.i18n import t, t_error

from ._ai_text import (
    ensure_ai_ready_or_reply,
    extract_text_from_quoted_or_args,
    run_prompt_with_progress,
)

_ALLOWED_STYLES = {
    "formal",
    "casual",
    "concise",
    "professional",
    "friendly",
}


class RewriteCommand(Command):
    name = "rewrite"
    aliases = ["rephrase"]
    description = "Rewrite text in a selected style"
    usage = "rewrite <formal|casual|concise|professional|friendly> [text]"
    category = "utility"
    cooldown = 10

    async def execute(self, ctx: CommandContext) -> None:
        if not await ensure_ai_ready_or_reply(
            ctx,
            "rewrite.ai_disabled",
            no_key_key="rewrite.no_api_key",
        ):
            return

        if not ctx.args:
            await ctx.client.reply(ctx.message, t_error("rewrite.usage", prefix=ctx.prefix))
            return

        style = ctx.args[0].strip().lower()
        if style not in _ALLOWED_STYLES:
            await ctx.client.reply(
                ctx.message,
                t_error("rewrite.invalid_style", styles=", ".join(sorted(_ALLOWED_STYLES))),
            )
            return

        source_text = extract_text_from_quoted_or_args(ctx, ctx.args, start=1)

        if not source_text:
            await ctx.client.reply(ctx.message, t_error("rewrite.no_text", prefix=ctx.prefix))
            return

        prompt = (
            "You are a writing assistant. Rewrite the following text in a "
            f"{style} style. Preserve the original meaning. "
            "Return ONLY the rewritten text, with no explanation.\n\n"
            f"Text:\n{source_text[:3000]}"
        )

        def _render(rewritten: str) -> str:
            output = sym.box(
                t("rewrite.title"),
                [
                    sym.status_line(t("rewrite.style"), style),
                    "",
                    rewritten,
                ],
            )
            return output

        await run_prompt_with_progress(
            ctx,
            processing_key="rewrite.processing",
            failure_key="rewrite.failed",
            prompt=prompt,
            render_output=_render,
        )
