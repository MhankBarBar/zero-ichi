"""Shared helpers for AI-powered text utility commands."""

from __future__ import annotations

import os

from pydantic_ai import Agent

from core.command import CommandContext
from core.i18n import t_error
from core.runtime_config import runtime_config


def get_ai_model() -> str:
    """Build provider:model string from runtime config."""
    provider = runtime_config.get_nested("agentic_ai", "provider", default="openai")
    model = runtime_config.get_nested("agentic_ai", "model", default="gpt-5-mini")
    return f"{provider}:{model}"


def get_api_key() -> str:
    """Get AI API key from env first, then runtime config."""
    env_key = os.getenv("AI_API_KEY", "")
    if env_key:
        return env_key
    return runtime_config.get_nested("agentic_ai", "api_key", default="")


def ensure_provider_key(provider: str, api_key: str) -> None:
    """Set provider-specific API key env vars for pydantic-ai."""
    if provider == "openai":
        os.environ["OPENAI_API_KEY"] = api_key
    elif provider == "anthropic":
        os.environ["ANTHROPIC_API_KEY"] = api_key
    elif provider == "google":
        os.environ["GOOGLE_API_KEY"] = api_key
        os.environ["GEMINI_API_KEY"] = api_key
    elif provider == "groq":
        os.environ["GROQ_API_KEY"] = api_key


async def ensure_ai_ready_or_reply(ctx: CommandContext, disabled_key: str) -> bool:
    """Validate AI enabled + API key; reply with localized error when invalid."""
    ai_enabled = runtime_config.get_nested("agentic_ai", "enabled", default=False)
    if not ai_enabled:
        await ctx.client.reply(ctx.message, t_error(disabled_key))
        return False

    api_key = get_api_key()
    if not api_key:
        await ctx.client.reply(ctx.message, t_error("summarize.no_api_key"))
        return False
    return True


async def run_text_prompt(prompt: str) -> str:
    """Execute a single text prompt with configured AI provider/model."""
    api_key = get_api_key()
    provider = runtime_config.get_nested("agentic_ai", "provider", default="openai")
    ensure_provider_key(provider, api_key)

    agent = Agent(get_ai_model(), output_type=str)
    result = await agent.run(prompt)
    return result.output.strip() if result.output else ""
