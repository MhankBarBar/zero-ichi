"""Shared AI runtime helpers for provider/model/key resolution."""

from __future__ import annotations

import os

from core.runtime_config import runtime_config


def resolve_api_key() -> str:
    """Resolve API key from env var or runtime config."""
    env_key = os.getenv("AI_API_KEY", "")
    if env_key:
        return env_key
    return runtime_config.get_nested("agentic_ai", "api_key", default="")


def resolve_provider() -> str:
    """Resolve configured AI provider name."""
    return runtime_config.get_nested("agentic_ai", "provider", default="openai")


def resolve_model() -> str:
    """Resolve configured AI model name."""
    return runtime_config.get_nested("agentic_ai", "model", default="gpt-5-mini")


def resolve_model_name() -> str:
    """Resolve full provider:model name used by pydantic-ai."""
    return f"{resolve_provider()}:{resolve_model()}"


def apply_provider_env(provider: str, api_key: str) -> None:
    """Set provider-specific API key env vars for SDK compatibility."""
    if provider == "openai":
        os.environ["OPENAI_API_KEY"] = api_key
    elif provider == "anthropic":
        os.environ["ANTHROPIC_API_KEY"] = api_key
    elif provider == "google":
        os.environ["GOOGLE_API_KEY"] = api_key
        os.environ["GEMINI_API_KEY"] = api_key
    elif provider == "groq":
        os.environ["GROQ_API_KEY"] = api_key
