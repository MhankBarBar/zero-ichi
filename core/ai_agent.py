"""
Agentic AI module using Pydantic AI framework.

This module allows an AI to process raw messages and execute bot actions
using the Pydantic AI agent framework with proper tool calling.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai import Agent, RunContext

from core.ai_memory import get_memory
from core.logger import log_debug, log_error, log_info
from core.runtime_config import runtime_config

if TYPE_CHECKING:
    from core.client import BotClient
    from core.message import MessageHelper


@dataclass
class BotDependencies:
    """Dependencies passed to AI tools."""

    bot: "BotClient"
    msg: "MessageHelper"


bot_agent = Agent(
    "openai:gpt-4o-mini",
    deps_type=BotDependencies,
    output_type=str,
    instructions="""You are a WhatsApp bot assistant. Be concise and efficient.

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
""",
)


@bot_agent.tool
async def reply(ctx: RunContext[BotDependencies], message: str, with_mentions: bool = False) -> str:
    """Send a message to the current chat. Set with_mentions=True if message contains @mentions like @123456789."""
    try:
        await ctx.deps.bot.reply(ctx.deps.msg, message, mentions_are_lids=with_mentions)
        return "Message sent"
    except Exception as e:
        return f"Failed to send message: {e}"


@bot_agent.tool
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


@bot_agent.tool
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


@bot_agent.tool
async def toggle_feature(ctx: RunContext[BotDependencies], feature: str, enabled: bool) -> str:
    """Toggle a bot feature on or off. Features: anti_delete, anti_link, welcome, notes, etc."""
    runtime_config.set_feature(feature, enabled)
    return f"Feature {feature} is now {'enabled' if enabled else 'disabled'}"


@bot_agent.tool
async def get_group_info(ctx: RunContext[BotDependencies], group_jid: str = "") -> str:
    """Get information about a WhatsApp group."""
    jid = group_jid or ctx.deps.msg.chat_jid
    info = await ctx.deps.bot.get_group_info(jid)
    if info:
        return f"Group: {info.get('name', 'Unknown')}, Members: {len(info.get('participants', []))}"
    return "Could not get group info"


class AgenticAI:
    """
    AI agent wrapper that uses Pydantic AI.

    Provides the same interface as before but uses the robust Pydantic AI framework.
    """

    @property
    def enabled(self) -> bool:
        """Check if agentic AI is enabled."""
        return runtime_config.get_nested("agentic_ai", "enabled", default=False)

    @property
    def api_key(self) -> str:
        """Get the API key (from env var AI_API_KEY or config)."""
        import os

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

    async def should_respond(self, msg: "MessageHelper", bot: "BotClient" = None) -> bool:
        """
        Check if AI should handle this message based on trigger mode.
        """
        log_debug(
            f"AI should_respond check: enabled={self.enabled}, has_key={bool(self.api_key)}, mode={self.trigger_mode}"
        )

        if not self.enabled or not self.api_key:
            log_debug(f"AI not responding: enabled={self.enabled}, has_key={bool(self.api_key)}")
            return False

        if self.owner_only:
            owner_jid = runtime_config.get_owner_jid()
            log_debug(f"AI owner check: sender={msg.sender_jid}, owner={owner_jid}")
            if owner_jid and msg.sender_jid != owner_jid:
                log_debug(
                    f"AI not responding: owner_only and sender {msg.sender_jid} != owner {owner_jid}"
                )
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
                import re

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

    async def process(self, msg: "MessageHelper", bot: "BotClient") -> str | None:
        """
        Process message with Pydantic AI agent.

        Returns the AI's text response, or None if no response.
        """
        import os

        if not self.api_key:
            return None

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

        # Get memory for this chat
        memory = get_memory(msg.chat_jid)
        history_text = memory.get_context_string()
        if history_text:
            history_text = "\n\n" + history_text

        try:
            # Run the agent with context + history
            user_message = f"{context_info}{history_text}\n\nUser message: {msg.text}"
            result = await bot_agent.run(
                user_message,
                deps=deps,
                model=model_str,
            )

            # Store in memory with rich context
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

            log_debug(f"AI response: {result.output}")
            return result.output

        except Exception as e:
            error_str = str(e)
            # Check if this is the null content error after tool execution
            # This happens when AI returns empty after using a tool - which is expected behavior
            if "expected a string, got null" in error_str:
                log_debug("AI completed tool execution (null response is expected)")
                # Store user message in memory
                if msg.text:
                    memory.add(
                        role="user",
                        content=msg.text,
                        sender_name=msg.sender_name,
                        message_type=message_type,
                        is_reply=is_reply,
                        reply_to=reply_to,
                    )
                return None  # Tool already responded, no additional message needed
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
