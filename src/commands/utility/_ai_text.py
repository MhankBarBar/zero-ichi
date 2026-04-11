"""Shared helpers for AI-powered text utility commands."""

from __future__ import annotations

from pydantic_ai import Agent

from core import symbols as sym
from core.ai_runtime import (
    apply_provider_env,
    resolve_api_key,
    resolve_model_name,
    resolve_provider,
)
from core.command import CommandContext
from core.i18n import t, t_error
from core.runtime_config import runtime_config


def get_ai_model() -> str:
    """Build provider:model string from runtime config."""
    return resolve_model_name()


def get_api_key() -> str:
    """Get AI API key from env first, then runtime config."""
    return resolve_api_key()


def ensure_provider_key(provider: str, api_key: str) -> None:
    """Set provider-specific API key env vars for pydantic-ai."""
    apply_provider_env(provider, api_key)


async def ensure_ai_ready_or_reply(
    ctx: CommandContext,
    disabled_key: str,
    *,
    no_key_key: str = "summarize.no_api_key",
) -> bool:
    """Validate AI enabled + API key; reply with localized error when invalid."""
    ai_enabled = runtime_config.get_nested("agentic_ai", "enabled", default=False)
    if not ai_enabled:
        await ctx.client.reply(ctx.message, t_error(disabled_key))
        return False

    api_key = get_api_key()
    if not api_key:
        await ctx.client.reply(ctx.message, t_error(no_key_key))
        return False
    return True


async def run_text_prompt(prompt: str) -> str:
    """Execute a single text prompt with configured AI provider/model."""
    api_key = get_api_key()
    provider = resolve_provider()
    ensure_provider_key(provider, api_key)

    agent = Agent(get_ai_model(), output_type=str)
    result = await agent.run(prompt)
    return result.output.strip() if result.output else ""


def extract_text_from_quoted_or_args(ctx: CommandContext, args: list[str], start: int = 0) -> str:
    """Extract source text from quoted message or command args."""
    quoted = ctx.message.quoted_message
    if quoted and quoted.get("text"):
        return str(quoted["text"])
    if len(args) > start:
        return " ".join(args[start:]).strip()
    return ""


async def run_prompt_with_progress(
    ctx: CommandContext,
    *,
    processing_key: str,
    failure_key: str,
    prompt: str,
    render_output,
) -> None:
    """Run an AI prompt and edit one progress message with result or error."""
    progress = await ctx.client.reply(ctx.message, f"{sym.LOADING} {t(processing_key)}")

    try:
        output = await run_text_prompt(prompt)
        if not output:
            await ctx.client.edit_message(ctx.message.chat_jid, progress.ID, t_error(failure_key))
            return
        await ctx.client.edit_message(ctx.message.chat_jid, progress.ID, render_output(output))
    except Exception:
        await ctx.client.edit_message(ctx.message.chat_jid, progress.ID, t_error(failure_key))
