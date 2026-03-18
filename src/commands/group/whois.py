"""
Whois command - Show information about a group member.
"""

from __future__ import annotations

from core import symbols as sym
from core.command import Command, CommandContext
from core.i18n import t, t_error
from core.storage import GroupData


class WhoisCommand(Command):
    name = "whois"
    aliases = ["userinfo"]
    description = "Show info about a group member"
    usage = "whois (reply to a message) | whois @user"
    category = "group"
    group_only = True

    async def execute(self, ctx: CommandContext) -> None:
        """Show user info: name, JID, admin status, warn count."""
        target_jid = ""

        quoted = ctx.message.quoted_message
        if quoted and quoted.get("sender"):
            target_jid = quoted["sender"]

        if not target_jid and ctx.message.mentions:
            target_jid = ctx.message.mentions[0]

        if not target_jid:
            await ctx.client.reply(ctx.message, t_error("errors.no_target"))
            return

        target_user = target_jid.split("@")[0].split(":")[0]

        is_admin = False
        is_superadmin = False

        try:
            group_info = await ctx.client.raw.get_group_info(
                ctx.client.to_jid(ctx.message.chat_jid)
            )
            for participant in group_info.Participants:
                if participant.JID.User == target_user:
                    is_admin = participant.IsAdmin
                    is_superadmin = participant.IsSuperAdmin
                    break
        except Exception:
            pass

        warnings_data = GroupData(ctx.message.chat_jid).warnings
        warn_count = 0
        if isinstance(warnings_data, dict):
            user_warns = warnings_data.get(target_user, {})
            if isinstance(user_warns, dict):
                warn_count = user_warns.get("count", 0)
            elif isinstance(user_warns, (int, float)):
                warn_count = int(user_warns)

        if is_superadmin:
            role = t("whois.superadmin")
        elif is_admin:
            role = t("whois.admin")
        else:
            role = t("whois.member")

        lines = [
            sym.status_line(t("whois.user_id"), f"`{target_user}`"),
            sym.status_line(t("whois.jid"), f"`{target_jid}`"),
            sym.status_line(t("whois.role"), role),
            sym.status_line(t("whois.warnings"), f"`{warn_count}`"),
        ]

        output = sym.box(t("whois.title"), lines)
        await ctx.client.reply(ctx.message, output)
