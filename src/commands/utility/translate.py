"""Translate command - AI-powered translation."""

from __future__ import annotations

from core import symbols as sym
from core.command import Command, CommandContext
from core.i18n import t, t_error

from ._ai_text import ensure_ai_ready_or_reply, run_text_prompt


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
        source_text = ""

        quoted = ctx.message.quoted_message
        if quoted and quoted.get("text"):
            source_text = quoted["text"]
        elif len(ctx.args) > 1:
            source_text = " ".join(ctx.args[1:]).strip()

        if not source_text:
            await ctx.client.reply(ctx.message, t_error("translate.no_text", prefix=ctx.prefix))
            return

        progress = await ctx.client.reply(ctx.message, f"{sym.LOADING} {t('translate.processing')}")

        prompt = (
            "You are a professional translator. Translate the following text into "
            f"{target_language}. Preserve meaning and tone. "
            "Return ONLY the translated text, with no explanation.\n\n"
            f"Text:\n{source_text[:3000]}"
        )

        try:
            translated = await run_text_prompt(prompt)
            if not translated:
                await ctx.client.edit_message(
                    ctx.message.chat_jid,
                    progress.ID,
                    t_error("translate.failed"),
                )
                return

            output = sym.box(
                t("translate.title"),
                [
                    sym.status_line(t("translate.target"), target_language),
                    "",
                    translated,
                ],
            )
            await ctx.client.edit_message(ctx.message.chat_jid, progress.ID, output)
        except Exception:
            await ctx.client.edit_message(
                ctx.message.chat_jid,
                progress.ID,
                t_error("translate.failed"),
            )
