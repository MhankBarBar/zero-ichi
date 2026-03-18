"""Rewrite command - AI-powered text rewrite in different styles."""

from __future__ import annotations

from core import symbols as sym
from core.command import Command, CommandContext
from core.i18n import t, t_error

from ._ai_text import ensure_ai_ready_or_reply, run_text_prompt

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
        if not await ensure_ai_ready_or_reply(ctx, "rewrite.ai_disabled"):
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

        source_text = ""
        quoted = ctx.message.quoted_message
        if quoted and quoted.get("text"):
            source_text = quoted["text"]
        elif len(ctx.args) > 1:
            source_text = " ".join(ctx.args[1:]).strip()

        if not source_text:
            await ctx.client.reply(ctx.message, t_error("rewrite.no_text", prefix=ctx.prefix))
            return

        progress = await ctx.client.reply(ctx.message, f"{sym.LOADING} {t('rewrite.processing')}")

        prompt = (
            "You are a writing assistant. Rewrite the following text in a "
            f"{style} style. Preserve the original meaning. "
            "Return ONLY the rewritten text, with no explanation.\n\n"
            f"Text:\n{source_text[:3000]}"
        )

        try:
            rewritten = await run_text_prompt(prompt)
            if not rewritten:
                await ctx.client.edit_message(
                    ctx.message.chat_jid,
                    progress.ID,
                    t_error("rewrite.failed"),
                )
                return

            output = sym.box(
                t("rewrite.title"),
                [
                    sym.status_line(t("rewrite.style"), style),
                    "",
                    rewritten,
                ],
            )
            await ctx.client.edit_message(ctx.message.chat_jid, progress.ID, output)
        except Exception:
            await ctx.client.edit_message(
                ctx.message.chat_jid,
                progress.ID,
                t_error("rewrite.failed"),
            )
