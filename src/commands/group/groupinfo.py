"""
Groupinfo command - Show group information.
"""

from datetime import datetime

from core.command import Command, CommandContext
from core.i18n import t, t_error


class GroupinfoCommand(Command):
    name = "groupinfo"
    aliases = ["ginfo", "group"]
    description = "Show group information"
    usage = "groupinfo"
    group_only = True

    async def execute(self, ctx: CommandContext) -> None:
        """Show group information."""
        group_jid = ctx.message.chat_jid

        try:
            group_info = await ctx.client._client.get_group_info(ctx.client.to_jid(group_jid))

            name = t("common.unknown")
            if group_info.HasField("GroupName") and group_info.GroupName.Name:
                name = group_info.GroupName.Name

            topic = t("group.no_description")
            if group_info.HasField("GroupTopic") and group_info.GroupTopic.Topic:
                topic = group_info.GroupTopic.Topic

            owner = t("common.unknown")
            if group_info.HasField("OwnerJID") and group_info.OwnerJID.User:
                owner = group_info.OwnerJID.User

            created = t("common.unknown")
            if group_info.GroupCreated:
                created_dt = datetime.fromtimestamp(group_info.GroupCreated)
                created = created_dt.strftime("%Y-%m-%d %H:%M")

            total = len(group_info.Participants) if group_info.Participants else 0
            admins = sum(1 for p in (group_info.Participants or []) if p.IsAdmin or p.IsSuperAdmin)

            is_locked = False
            if group_info.HasField("GroupLocked"):
                is_locked = group_info.GroupLocked.isLocked

            is_announcement = False
            if group_info.HasField("GroupAnnounce"):
                is_announcement = group_info.GroupAnnounce.IsAnnounce

            info_lines = [
                f"*{name}*",
                "",
                f"*{t('group.description')}:*\n{topic}",
                "",
                f"*{t('group.owner')}:* @{owner}",
                f"*{t('group.created')}:* {created}",
                "",
                f"*{t('group.members')}:* {total}",
                f"*{t('group.admins')}:* {admins}",
            ]

            settings = []
            if is_locked:
                settings.append(t("group.locked"))
            if is_announcement:
                settings.append(t("group.announcement_only"))

            if settings:
                info_lines.append(f"*{t('headers.settings')}:* {', '.join(settings)}")

            await ctx.client.reply(ctx.message, "\n".join(info_lines), mentions_are_lids=True)

        except Exception as e:
            await ctx.client.reply(ctx.message, t_error("group.info_failed", error=str(e)))
