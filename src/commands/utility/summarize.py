"""
Summarize command - AI-powered text summarization.

Summarizes a quoted message or recent chat context using the AI agent.
"""

from __future__ import annotations

import os

from pydantic_ai import Agent

from core import symbols as sym
from core.command import Command, CommandContext
from core.i18n import t, t_error
from core.privacy import is_chat_memory_enabled
from core.runtime_config import runtime_config

_SUMMARIZE_PROMPT = """You are a concise summarizer. Summarize the following text in 2-4 bullet points.
Be clear, factual, and brief. Use plain language. Do not add opinions.

Text to summarize:
{text}"""


def _get_ai_model() -> str:
    """Build the model string from config."""
    provider = runtime_config.get_nested("agentic_ai", "provider", default="openai")
    model = runtime_config.get_nested("agentic_ai", "model", default="gpt-5-mini")
    return f"{provider}:{model}"


def _get_api_key() -> str:
    """Get AI API key from env or config."""
    env_key = os.getenv("AI_API_KEY", "")
    if env_key:
        return env_key
    return runtime_config.get_nested("agentic_ai", "api_key", default="")


class SummarizeCommand(Command):
    name = "summarize"
    aliases = ["tldr"]
    description = "Summarize a message or recent chat context using AI"
    usage = "summarize (reply to a message) | summarize"
    category = "utility"
    cooldown = 30

    async def execute(self, ctx: CommandContext) -> None:
        """Summarize quoted text or recent chat memory."""
        ai_enabled = runtime_config.get_nested("agentic_ai", "enabled", default=False)
        if not ai_enabled:
            await ctx.client.reply(ctx.message, t_error("summarize.ai_disabled"))
            return

        api_key = _get_api_key()
        if not api_key:
            await ctx.client.reply(ctx.message, t_error("summarize.no_api_key"))
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

        progress_msg = await ctx.client.reply(
            ctx.message, f"{sym.LOADING} {t('summarize.processing')}"
        )

        try:
            model_str = _get_ai_model()
            provider = runtime_config.get_nested("agentic_ai", "provider", default="openai")

            if provider == "openai":
                os.environ["OPENAI_API_KEY"] = api_key
            elif provider == "anthropic":
                os.environ["ANTHROPIC_API_KEY"] = api_key
            elif provider == "google":
                os.environ["GOOGLE_API_KEY"] = api_key
                os.environ["GEMINI_API_KEY"] = api_key

            agent = Agent(model_str, output_type=str)
            prompt = _SUMMARIZE_PROMPT.format(text=text_to_summarize[:3000])
            result = await agent.run(prompt)
            summary = result.output.strip() if result.output else ""

            if not summary:
                await ctx.client.edit_message(
                    ctx.message.chat_jid, progress_msg.ID, t_error("summarize.failed")
                )
                return

            output = sym.box(t("summarize.title"), [summary])
            await ctx.client.edit_message(ctx.message.chat_jid, progress_msg.ID, output)

        except Exception:
            await ctx.client.edit_message(
                ctx.message.chat_jid, progress_msg.ID, t_error("summarize.failed")
            )
