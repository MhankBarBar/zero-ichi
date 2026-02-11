"""
AI Tools module.

Auto-loads all tool modules to register them with the agent.
"""

from ai.tools import core, group  # noqa: F401

__all__ = ["core", "group"]
