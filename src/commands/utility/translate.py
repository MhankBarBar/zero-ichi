"""Translate command - AI-powered translation."""

from __future__ import annotations

from core import symbols as sym
from core.command import Command, CommandContext
from core.i18n import t, t_error

from ._ai_text import (
    ensure_ai_ready_or_reply,
    extract_text_from_quoted_or_args,
    run_prompt_with_progress,
)


class TranslateCommand(Command):
    name = "translate"
    aliases = ["tr"]
    description = "Translate text using AI"
    usage = "translate <target_language> [text] (or reply to message)"
    category = "utility"
    cooldown = 10

    async def execute(self, ctx: CommandContext) -> None:
        if not await ensure_ai_ready_or_reply(ctx, "translate.ai_disabled"):
            return

        if not ctx.args:
            await ctx.client.reply(ctx.message, t_error("translate.usage", prefix=ctx.prefix))
            return

        target_language = ctx.args[0].strip()
        source_text = extract_text_from_quoted_or_args(ctx, ctx.args, start=1)

        if not source_text:
            await ctx.client.reply(ctx.message, t_error("translate.no_text", prefix=ctx.prefix))
            return

        prompt = (
            "You are a professional translator. Translate the following text into "
            f"{target_language}. Preserve meaning and tone. "
            "Return ONLY the translated text, with no explanation.\n\n"
            f"Text:\n{source_text[:3000]}"
        )

        def _render(translated: str) -> str:
            output = sym.box(
                t("translate.title"),
                [
                    sym.status_line(t("translate.target"), target_language),
                    "",
                    translated,
                ],
            )
            return output

        await run_prompt_with_progress(
            ctx,
            processing_key="translate.processing",
            failure_key="translate.failed",
            prompt=prompt,
            render_output=_render,
        )
