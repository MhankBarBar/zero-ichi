"""
AI Configuration module.

Handles AI-related settings like model, API key, trigger mode, etc.
"""

import os
from dataclasses import dataclass, field
from typing import Literal

TriggerMode = Literal["always", "mention", "reply"]


@dataclass
class AIConfig:
    """AI configuration settings."""

    enabled: bool = False
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    trigger_mode: TriggerMode = "mention"
    owner_only: bool = False
    _api_key: str = field(default="", repr=False)

    @property
    def api_key(self) -> str:
        """Get API key from env or config."""
        return os.getenv("AI_API_KEY", "") or self._api_key

    @api_key.setter
    def api_key(self, value: str) -> None:
        """Set API key."""
        self._api_key = value

    @property
    def full_model_name(self) -> str:
        """Get full model name for pydantic-ai (e.g., 'openai:gpt-4o-mini')."""
        return f"{self.provider}:{self.model}"

    def is_configured(self) -> bool:
        """Check if AI is properly configured with an API key."""
        return bool(self.api_key)
