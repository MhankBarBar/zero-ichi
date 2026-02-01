"""
Rate Limiter for command spam prevention.

Implements per-user and per-group cooldowns to prevent abuse.
"""

import time
from collections import defaultdict
from dataclasses import dataclass


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    user_cooldown: float = 3.0
    command_cooldown: float = 2.0
    burst_limit: int = 5
    burst_window: float = 10.0
    enabled: bool = True


class RateLimiter:
    """
    Rate limiter with per-user cooldowns and burst protection.

    Usage:
        limiter = RateLimiter()

        # Check if user can execute command
        if limiter.is_limited(user_id, command_name):
            remaining = limiter.get_remaining_cooldown(user_id, command_name)
            await ctx.client.reply(ctx.message, f"Cooldown: {remaining:.1f}s")
            return

        # Record the command execution
        limiter.record(user_id, command_name)
    """

    def __init__(self, config: RateLimitConfig | None = None):
        self.config = config or RateLimitConfig()

        self._user_last_command: dict[str, float] = {}

        self._command_last_use: dict[str, dict[str, float]] = defaultdict(dict)

        self._user_bursts: dict[str, list[float]] = defaultdict(list)

    def is_limited(self, user_id: str, command_name: str) -> bool:
        """
        Check if a user is rate limited.

        Args:
            user_id: The user's JID
            command_name: The command being executed

        Returns:
            True if rate limited, False if allowed
        """
        if not self.config.enabled:
            return False

        now = time.time()

        last_cmd = self._user_last_command.get(user_id, 0)
        if now - last_cmd < self.config.user_cooldown:
            return True

        cmd_last = self._command_last_use[user_id].get(command_name, 0)
        if now - cmd_last < self.config.command_cooldown:
            return True

        bursts = self._user_bursts[user_id]
        bursts = [t for t in bursts if now - t < self.config.burst_window]
        self._user_bursts[user_id] = bursts

        if len(bursts) >= self.config.burst_limit:
            return True

        return False

    def record(self, user_id: str, command_name: str) -> None:
        """
        Record a command execution.

        Args:
            user_id: The user's JID
            command_name: The command that was executed
        """
        now = time.time()
        self._user_last_command[user_id] = now
        self._command_last_use[user_id][command_name] = now
        self._user_bursts[user_id].append(now)

    def get_remaining_cooldown(self, user_id: str, command_name: str) -> float:
        """
        Get remaining cooldown time in seconds.

        Args:
            user_id: The user's JID
            command_name: The command name

        Returns:
            Remaining cooldown in seconds (0 if not limited)
        """
        now = time.time()
        remaining = 0.0

        last_cmd = self._user_last_command.get(user_id, 0)
        user_remaining = self.config.user_cooldown - (now - last_cmd)
        if user_remaining > remaining:
            remaining = user_remaining

        cmd_last = self._command_last_use[user_id].get(command_name, 0)
        cmd_remaining = self.config.command_cooldown - (now - cmd_last)
        if cmd_remaining > remaining:
            remaining = cmd_remaining

        return max(0, remaining)

    def reset_user(self, user_id: str) -> None:
        """Reset all rate limits for a user."""
        self._user_last_command.pop(user_id, None)
        self._command_last_use.pop(user_id, None)
        self._user_bursts.pop(user_id, None)

    def reset_all(self) -> None:
        """Reset all rate limits."""
        self._user_last_command.clear()
        self._command_last_use.clear()
        self._user_bursts.clear()


rate_limiter = RateLimiter()
