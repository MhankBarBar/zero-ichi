"""
Admins command - List all group admins.
"""

from core.command import Command, CommandContext
from core.i18n import t, t_error


class AdminsCommand(Command):
    name = "admins"
    description = "List all group admins"
    usage = "/admins"
    group_only = True

    async def execute(self, ctx: CommandContext) -> None:
        """List all group admins."""
        group_jid = ctx.message.chat_jid

        try:
            group_info = await ctx.client._client.get_group_info(ctx.client.to_jid(group_jid))

            admins = []
            owner = None

            for participant in group_info.Participants:
                if participant.IsSuperAdmin:
                    owner = participant.JID.User
                elif participant.IsAdmin:
                    admins.append(participant.JID.User)

            lines = [f"{t('group.group')}: {group_info.GroupName.Name}", ""]

            if owner:
                lines.append(f"{t('group.owner')}: @{owner}")

            if admins:
                lines.append(f"\n{t('group.admins')} ({len(admins)}):")
                for admin in admins:
                    lines.append(f"  • @{admin}")
            else:
                lines.append(t("admin.no_admins"))

            await ctx.client.reply(ctx.message, "\n".join(lines), mentions_are_lids=True)
        except Exception as e:
            await ctx.client.reply(ctx.message, t_error("admin.list_failed", error=str(e)))
