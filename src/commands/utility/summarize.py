"""
Summarize command - AI-powered text summarization.

Summarizes a quoted message or recent chat context using the AI agent.
"""

from __future__ import annotations

from core import symbols as sym
from core.command import Command, CommandContext
from core.i18n import t, t_error
from core.privacy import is_chat_memory_enabled

from ._ai_text import ensure_ai_ready_or_reply, run_prompt_with_progress

_SUMMARIZE_PROMPT = """You are a concise summarizer. Summarize the following text in 2-4 bullet points.
Be clear, factual, and brief. Use plain language. Do not add opinions.

Text to summarize:
{text}"""


class SummarizeCommand(Command):
    name = "summarize"
    aliases = ["tldr"]
    description = "Summarize a message or recent chat context using AI"
    usage = "summarize (reply to a message) | summarize"
    category = "utility"
    cooldown = 30

    async def execute(self, ctx: CommandContext) -> None:
        """Summarize quoted text or recent chat memory."""
        if not await ensure_ai_ready_or_reply(
            ctx,
            "summarize.ai_disabled",
            no_key_key="summarize.no_api_key",
        ):
            return

        text_to_summarize = ""
        quoted = ctx.message.quoted_message
        if quoted and quoted.get("text"):
            text_to_summarize = quoted["text"]
        else:
            if not is_chat_memory_enabled(ctx.message.chat_jid):
                await ctx.client.reply(ctx.message, t_error("summarize.memory_disabled"))
                return

            from ai.memory import get_memory

            memory = get_memory(ctx.message.chat_jid)
            history = memory.get_history(limit=10)
            if history:
                lines = []
                for entry in history:
                    prefix = entry.sender_name or entry.role
                    lines.append(f"[{prefix}]: {entry.content}")
                text_to_summarize = "\n".join(lines)

        if not text_to_summarize.strip():
            await ctx.client.reply(ctx.message, t_error("summarize.no_content"))
            return

        prompt = _SUMMARIZE_PROMPT.format(text=text_to_summarize[:3000])

        def _render(summary: str) -> str:
            output = sym.box(t("summarize.title"), [summary])
            return output

        await run_prompt_with_progress(
            ctx,
            processing_key="summarize.processing",
            failure_key="summarize.failed",
            prompt=prompt,
            render_output=_render,
        )
