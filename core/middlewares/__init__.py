"""
Middleware package — all middleware functions for the message pipeline.

Provides build_pipeline() to construct the full middleware pipeline.
"""

from core.middleware import MiddlewarePipeline

from .ai import ai_middleware
from .antidelete import antidelete_middleware
from .antilink import antilink_middleware
from .auto_actions import auto_actions_middleware
from .blacklist import blacklist_middleware
from .command import command_middleware
from .download_reply import download_reply_middleware
from .features import features_middleware
from .mute import mute_middleware
from .self_mode import self_mode_middleware
from .stats import stats_middleware


def build_pipeline() -> MiddlewarePipeline:
    """Build and return the full middleware pipeline."""
    pipeline = MiddlewarePipeline()
    pipeline.use("self_mode", self_mode_middleware)
    pipeline.use("stats", stats_middleware)
    pipeline.use("auto_actions", auto_actions_middleware)
    pipeline.use("antidelete", antidelete_middleware)
    pipeline.use("blacklist", blacklist_middleware)
    pipeline.use("antilink", antilink_middleware)
    pipeline.use("mute", mute_middleware)
    pipeline.use("features", features_middleware)
    pipeline.use("download_reply", download_reply_middleware)
    pipeline.use("ai", ai_middleware)
    pipeline.use("command", command_middleware)
    return pipeline
