"""
Broadcast command - Send a message to all groups (owner only).
"""

import asyncio

from core.command import Command, CommandContext
from core.i18n import t, t_error, t_success
from core.logger import log_error
from core.storage import Storage


class BroadcastCommand(Command):
    name = "broadcast"
    description = "Send a message to all groups (owner only)"
    usage = "broadcast <message> | list"
    aliases = ["bc", "announce"]
    owner_only = True

    async def execute(self, ctx: CommandContext) -> None:
        """Broadcast a message to all groups."""
        if not ctx.args:
            await ctx.client.reply(ctx.message, t_error("broadcast.usage", prefix=ctx.prefix))
            return

        action = ctx.args[0].lower()
        storage = Storage()
        groups = storage.get_all_groups()

        target_groups = [jid for jid in groups.keys() if jid.endswith("@g.us")]

        if action == "list":
            if not target_groups:
                await ctx.client.reply(ctx.message, t("broadcast.no_groups"))
                return

            lines = [f"*{t('broadcast.list_title')} ({len(target_groups)})*"]
            limit = 50
            for i, jid in enumerate(target_groups):
                if i >= limit:
                    lines.append(t("broadcast.and_more", count=len(target_groups) - limit))
                    break

                group_data = groups[jid]
                group_name = group_data.get("name", "Unknown Group")
                lines.append(f"• {group_name}")

            await ctx.client.reply(ctx.message, "\n".join(lines))
            return

        message = " ".join(ctx.args)

        await ctx.client.reply(ctx.message, t("broadcast.starting", count=len(target_groups)))

        success_count = 0
        fail_count = 0

        for jid in target_groups:
            try:
                if not jid:
                    continue

                await asyncio.sleep(1.5)

                await ctx.client.send(jid, message)
                success_count += 1
            except Exception as e:
                log_error(f"Failed to broadcast to {jid}: {e}")
                fail_count += 1

        await ctx.client.reply(
            ctx.message, t_success("broadcast.finished", success=success_count, fail=fail_count)
        )
