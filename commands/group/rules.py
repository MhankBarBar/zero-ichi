"""
Rules command - Group rules management.
"""

from core import symbols as sym
from core.command import Command, CommandContext
from core.i18n import t
from core.storage import GroupData


class RulesCommand(Command):
    name = "rules"
    aliases = ["rule"]
    description = "Set or show group rules"
    usage = "rules [set <rules>]"
    category = "group"
    group_only = True
    examples = [
        "rules",
        "rules set 1. Be respectful\n2. No spam\n3. English only",
    ]

    async def execute(self, ctx: CommandContext) -> None:
        """Show or set group rules."""
        storage = GroupData(ctx.message.chat_jid)

        if not ctx.args:
            rules_config = storage.load("rules", {"text": ""})
            rules = rules_config.get("text", "")

            if not rules:
                await ctx.client.reply(
                    ctx.message, f"{sym.INFO} {t('rules.no_rules', prefix=ctx.prefix)}"
                )
                return

            await ctx.client.reply(ctx.message, f"{sym.NOTE} *{t('rules.title')}*\n\n{rules}")
            return

        action = ctx.args[0].lower()

        if action == "set":
            from core.permissions import check_command_permissions

            can_execute, error = await check_command_permissions(
                ctx.client, ctx.message, admin_only=True
            )
            if not can_execute:
                await ctx.client.reply(ctx.message, f"{sym.ERROR} {error}")
                return

            if len(ctx.args) < 2:
                await ctx.client.reply(
                    ctx.message, f"{sym.ERROR} {t('rules.provide_text', prefix=ctx.prefix)}"
                )
                return

            rules_text = " ".join(ctx.args[1:])
            storage.save("rules", {"text": rules_text})

            await ctx.client.reply(
                ctx.message, f"{sym.SUCCESS} {t('rules.updated')}\n\n{sym.NOTE} {rules_text}"
            )

        elif action == "clear":
            from core.permissions import check_command_permissions

            can_execute, error = await check_command_permissions(
                ctx.client, ctx.message, admin_only=True
            )
            if not can_execute:
                await ctx.client.reply(ctx.message, f"{sym.ERROR} {error}")
                return

            storage.save("rules", {"text": ""})
            await ctx.client.reply(ctx.message, f"{sym.SUCCESS} {t('rules.cleared')}")
        else:
            await ctx.client.reply(
                ctx.message,
                f"{sym.ERROR} {t('rules.unknown_action', prefix=ctx.prefix, bullet=sym.BULLET)}",
            )
