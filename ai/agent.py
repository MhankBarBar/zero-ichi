"""
Agentic AI module using Pydantic AI framework.

This module allows an AI to process raw messages and execute bot actions
using the Pydantic AI agent framework with proper tool calling.
"""

from __future__ import annotations

import os
import re
from typing import TYPE_CHECKING

from pydantic_ai import Agent, BinaryContent, RunContext

from ai.context import BotDependencies
from ai.token_tracker import token_tracker
from core.logger import log_debug, log_error, log_info, log_warning
from core.runtime_config import runtime_config

if TYPE_CHECKING:
    from core.client import BotClient
    from core.message import MessageHelper


BASE_INSTRUCTIONS = """You are a WhatsApp bot assistant. Be concise and efficient.

AVAILABLE INFORMATION:
- Your context includes: sender name, chat info, message type, quoted message content (if reply)
- Use this info directly - don't ask for what you already have!

WHEN USER ASKS TO DO SOMETHING:
1. FIRST call get_commands() to see what commands are available
2. If a command exists (like "delete", "kick", "sticker", etc.), use run_command(name)
3. After run_command(), return "" - don't add any text or use reply()

NEVER say "I can't do that" or "I don't have that command" without first checking get_commands()!

FOR CHAT/QUESTIONS:
- Return a short response directly (no tool needed)
- Use context info you already have about quoted messages

CRITICAL RULES:
- ONE response only - never send the same message twice
- After run_command(), return "" only
- Max 1-2 tool calls per request
"""


def _create_agent() -> Agent:
    """Create and configure the Pydantic AI agent with all tools."""
    agent = Agent(
        "openai:gpt-4o-mini",
        deps_type=BotDependencies,
        output_type=str,
        instructions=BASE_INSTRUCTIONS,
    )

    _register_core_tools(agent)
    _register_group_tools(agent)

    return agent


def _register_core_tools(agent: Agent) -> None:
    """Register core tools with the agent."""

    @agent.tool
    async def reply(
        ctx: RunContext[BotDependencies], message: str, with_mentions: bool = False
    ) -> str:
        """Send a message to the current chat. Set with_mentions=True if message contains @mentions like @123456789."""
        try:
            await ctx.deps.bot.reply(ctx.deps.msg, message, mentions_are_lids=with_mentions)
            return "Message sent"
        except Exception as e:
            return f"Failed to send message: {e}"

    @agent.tool
    async def get_commands(ctx: RunContext[BotDependencies], category: str = "") -> str:
        """Get list of available bot commands. ALWAYS use this before telling users about commands."""
        from core.command import command_loader

        grouped = command_loader.get_grouped_commands()
        result_lines = []

        for group_name, commands in grouped.items():
            if category and category.lower() not in group_name.lower():
                continue
            result_lines.append(f"\n{group_name}:")
            for cmd in commands:
                result_lines.append(f"  - {cmd.name}: {cmd.description}")

        return "\n".join(result_lines) if result_lines else "No commands found"

    @agent.tool
    async def run_command(ctx: RunContext[BotDependencies], command: str, args: str = "") -> str:
        """Execute a bot command. Use this to run commands for the user."""
        from core.command import CommandContext, command_loader

        cmd_name = command.lower()
        cmd = command_loader.get(cmd_name)

        if not cmd:
            return f"Command '{cmd_name}' not found"

        if not cmd.enabled:
            return f"Command '{cmd_name}' is disabled"

        args_list = args.split() if args else []
        cmd_ctx = CommandContext(
            client=ctx.deps.bot,
            message=ctx.deps.msg,
            args=args_list,
            raw_args=args,
            command_name=cmd_name,
        )

        try:
            await cmd.execute(cmd_ctx)
            return f"Executed command: {cmd_name}"
        except Exception as e:
            return f"Command error: {str(e)}"


def _register_group_tools(agent: Agent) -> None:
    """Register group/feature tools with the agent."""

    @agent.tool
    async def toggle_feature(ctx: RunContext[BotDependencies], feature: str, enabled: bool) -> str:
        """Toggle a bot feature on or off. Features: anti_delete, anti_link, welcome, notes, etc."""
        runtime_config.set_feature(feature, enabled)
        return f"Feature {feature} is now {'enabled' if enabled else 'disabled'}"

    @agent.tool
    async def get_group_info(ctx: RunContext[BotDependencies], group_jid: str = "") -> str:
        """Get information about a WhatsApp group."""
        jid = group_jid or ctx.deps.msg.chat_jid
        info = await ctx.deps.bot.get_group_info(jid)
        if info:
            return f"Group: {info.get('name', 'Unknown')}, Members: {len(info.get('participants', []))}"
        return "Could not get group info"


_bot_agent: Agent | None = None


def get_agent() -> Agent:
    """Get or create the global agent instance."""
    global _bot_agent
    if _bot_agent is None:
        _bot_agent = _create_agent()
    return _bot_agent


class AgenticAI:
    """
    AI agent wrapper that uses Pydantic AI.

    Provides the same interface as before but uses the robust Pydantic AI framework.
    """

    def __init__(self):
        """Initialize the AI agent and load saved skills."""
        self._skills: dict[str, dict] = {}
        self._load_saved_skills()

    def _load_saved_skills(self) -> None:
        """Load all saved skills from disk."""
        from ai.skills import load_all_skills

        for skill in load_all_skills():
            self._skills[skill["name"]] = {
                "content": skill["content"],
                "description": skill["description"],
                "trigger": skill["trigger"],
            }

        if self._skills:
            log_info(f"Loaded {len(self._skills)} AI skills")

    @property
    def enabled(self) -> bool:
        """Check if agentic AI is enabled."""
        return runtime_config.get_nested("agentic_ai", "enabled", default=False)

    @property
    def api_key(self) -> str:
        """Get the API key (from env var AI_API_KEY or config)."""
        env_key = os.getenv("AI_API_KEY", "")
        if env_key:
            return env_key
        return runtime_config.get_nested("agentic_ai", "api_key", default="")

    @property
    def provider(self) -> str:
        """Get the AI provider."""
        return runtime_config.get_nested("agentic_ai", "provider", default="openai")

    @property
    def model(self) -> str:
        """Get the AI model."""
        return runtime_config.get_nested("agentic_ai", "model", default="gpt-4o-mini")

    @property
    def trigger_mode(self) -> str:
        """Get the trigger mode (always, mention, reply)."""
        return runtime_config.get_nested("agentic_ai", "trigger_mode", default="mention")

    @property
    def owner_only(self) -> bool:
        """Check if AI is restricted to owner only."""
        return runtime_config.get_nested("agentic_ai", "owner_only", default=True)

    @property
    def skills(self) -> dict[str, dict]:
        """Get all loaded skills."""
        return self._skills

    def add_skill(
        self, name: str, content: str, description: str = "", trigger: str = "always"
    ) -> bool:
        """Add a skill to the AI."""
        self._skills[name] = {
            "content": content,
            "description": description,
            "trigger": trigger,
        }
        log_info(f"Added AI skill: {name}")
        return True

    def remove_skill(self, name: str) -> bool:
        """Remove a skill from the AI."""
        if name in self._skills:
            del self._skills[name]
            log_info(f"Removed AI skill: {name}")
            return True
        return False

    def get_skill(self, name: str) -> dict | None:
        """Get a skill by name."""
        return self._skills.get(name)

    def _build_instructions(self) -> str:
        """Build full instructions including skills."""
        instructions = BASE_INSTRUCTIONS

        if self._skills:
            instructions += "\n\n--- SKILLS ---\n"
            for name, skill in self._skills.items():
                instructions += f"\n## {name}\n{skill['content']}\n"

        return instructions

    async def should_respond(self, msg: MessageHelper, bot: BotClient = None) -> bool:
        """Check if AI should handle this message based on trigger mode."""
        log_debug(
            f"AI should_respond check: enabled={self.enabled}, has_key={bool(self.api_key)}, mode={self.trigger_mode}"
        )

        if not self.enabled or not self.api_key:
            log_debug(f"AI not responding: enabled={self.enabled}, has_key={bool(self.api_key)}")
            return False

        if self.owner_only:
            log_debug(f"AI owner check: sender={msg.sender_jid}")
            if not await runtime_config.is_owner_async(msg.sender_jid, bot):
                log_debug(f"AI not responding: owner_only and sender {msg.sender_jid} is not owner")
                return False

        mode = self.trigger_mode

        bot_identifiers = []
        if bot:
            try:
                me = await bot._client.get_me()
                if me:
                    if me.JID and me.JID.User:
                        bot_identifiers.append(me.JID.User)
                        log_debug(f"AI bot JID user: {me.JID.User}")
                    if hasattr(me, "LID") and me.LID and me.LID.User:
                        bot_identifiers.append(me.LID.User)
                        log_debug(f"AI bot LID user: {me.LID.User}")
            except Exception as e:
                log_debug(f"Error getting bot identifiers: {e}")

        log_debug(f"AI bot identifiers: {bot_identifiers}")

        if mode == "always":
            return True

        if mode == "mention":
            bot_name = runtime_config.bot_name.lower()
            text = (msg.text or "").lower()

            log_debug(f"AI mention check: bot_name='{bot_name}', text='{text[:50]}...'")

            if bot_name in text:
                log_debug(f"AI triggered: bot name '{bot_name}' found in text")
                return True

            if bot_identifiers and msg.mentions:
                for mention in msg.mentions:
                    mention_user = mention.split("@")[0] if "@" in mention else mention
                    if mention_user in bot_identifiers:
                        log_debug("AI triggered: bot found in mentions!")
                        return True

            if bot_identifiers:
                mention_patterns = re.findall(r"@(\d+)", msg.text or "")
                log_debug(f"AI text @mentions: {mention_patterns}")
                for pattern in mention_patterns:
                    if pattern in bot_identifiers:
                        log_debug(f"AI triggered: @{pattern} matches bot identifier!")
                        return True

            return False

        if mode == "reply":
            quoted = msg.quoted_message
            log_debug(
                f"AI reply mode: quoted={quoted is not None}, bot_identifiers={bot_identifiers}"
            )
            if quoted and bot_identifiers:
                for bot_id in bot_identifiers:
                    log_debug(f"AI checking if quoted from bot_id={bot_id}")
                    if msg.is_quoted_from(bot_id):
                        log_debug(f"AI triggered: reply to bot message (matched {bot_id})")
                        return True
            else:
                if not quoted:
                    log_debug("AI reply mode: no quoted message found")
                if not bot_identifiers:
                    log_debug("AI reply mode: no bot_identifiers available")

        return False

    async def process(self, msg: MessageHelper, bot: BotClient) -> str | None:
        """
        Process message with Pydantic AI agent.

        Returns the AI's text response, or None if no response.
        """
        from ai.memory import get_memory

        if not self.api_key:
            return None

        user_id = msg.sender_jid.split("@")[0] if msg.sender_jid else "unknown"
        chat_id = msg.chat_jid
        if not token_tracker.can_use(user_id, chat_id):
            log_info(f"AI token limit reached for user={user_id} chat={chat_id}")
            return "⏳ AI daily limit reached. Try again tomorrow!"

        os.environ["OPENAI_API_KEY"] = self.api_key

        model_str = f"{self.provider}:{self.model}"
        log_info(f"AI processing with model: {model_str}")

        deps = BotDependencies(bot=bot, msg=msg)

        sender_id = msg.sender_jid.split("@")[0] if msg.sender_jid else "unknown"

        bot_jid = ""
        bot_lid = ""
        try:
            me = await bot._client.get_me()
            if me:
                if me.JID and me.JID.User:
                    bot_jid = me.JID.User
                if hasattr(me, "LID") and me.LID and me.LID.User:
                    bot_lid = me.LID.User
        except Exception:
            pass

        message_type = msg._detect_media_type(msg.raw_message) or "text"

        image_data: bytes | None = None
        if message_type == "image":
            try:
                msg_obj, _ = msg.get_media_message(bot)
                if msg_obj:
                    image_data = await bot._client.download_any(msg_obj)
                    log_debug(f"AI vision: downloaded {len(image_data)} bytes")
            except Exception as e:
                log_warning(f"AI vision: failed to download image: {e}")
                image_data = None

        quoted = msg.quoted_message
        is_reply = quoted is not None
        reply_to = quoted.get("text", "") if quoted else None
        reply_sender = quoted.get("sender", "").split("@")[0] if quoted else None

        quoted_context = ""
        if is_reply and reply_to:
            quoted_context = (
                f'\n- Quoted message content: "{reply_to}"\n- Quoted message sender: {reply_sender}'
            )

        context_info = f"""
Current context:
- Chat: {msg.chat_jid}
- Sender name: {msg.sender_name}
- Sender JID for mentioning: {sender_id} (use @{sender_id} with with_mentions=True to mention them)
- Is group: {msg.is_group}
- Message type: {message_type}
- Is reply to another message: {is_reply}{quoted_context}
- Bot JID: {bot_jid} (this is YOU, the bot)
- Bot LID: {bot_lid} (this is also YOU, the bot)
Note: When user mentions @{bot_jid} or @{bot_lid}, they are talking TO you, not asking you to mention yourself.
"""

        memory = get_memory(msg.chat_jid)
        history_text = memory.get_context_string()
        if history_text:
            history_text = "\n\n" + history_text

        try:
            skills_context = ""
            if self._skills:
                skills_context = "\n\n--- SKILLS (Follow these instructions) ---"
                for name, skill in self._skills.items():
                    skills_context += f"\n## {name}\n{skill['content']}"

            user_prompt_parts: list = []

            text_content = f"{context_info}{history_text}{skills_context}\n\nUser message: {msg.text or '(image)'}"
            user_prompt_parts.append(text_content)

            if image_data:
                user_prompt_parts.append(BinaryContent(data=image_data, media_type="image/jpeg"))

            result = await get_agent().run(
                user_prompt_parts,
                deps=deps,
                model=model_str,
            )

            if msg.text:
                memory.add(
                    role="user",
                    content=msg.text,
                    sender_name=msg.sender_name,
                    message_type=message_type,
                    is_reply=is_reply,
                    reply_to=reply_to,
                )
            if result.output:
                memory.add(role="assistant", content=result.output)

            try:
                usage = result.usage()
                total_tokens = (usage.total_tokens or 0) if usage else 0
                if total_tokens > 0:
                    token_tracker.record(user_id, chat_id, total_tokens)
            except Exception:
                token_tracker.record(user_id, chat_id, 1000)  # estimate

            log_debug(f"AI response: {result.output}")
            return result.output

        except Exception as e:
            error_str = str(e)
            if "expected a string, got null" in error_str:
                log_debug("AI completed tool execution (null response is expected)")
                if msg.text:
                    memory.add(
                        role="user",
                        content=msg.text,
                        sender_name=msg.sender_name,
                        message_type=message_type,
                        is_reply=is_reply,
                        reply_to=reply_to,
                    )
                return None
            log_error(f"AI agent error: {e}")
            return None

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable agentic AI."""
        runtime_config.set_nested("agentic_ai", "enabled", enabled)

    def set_api_key(self, key: str) -> None:
        """Set the API key."""
        runtime_config.set_nested("agentic_ai", "api_key", key)

    def set_trigger_mode(self, mode: str) -> None:
        """Set trigger mode (always, mention, reply)."""
        if mode in ("always", "mention", "reply"):
            runtime_config.set_nested("agentic_ai", "trigger_mode", mode)


agentic_ai = AgenticAI()
