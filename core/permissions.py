"""
Permission checking utilities for admin commands.
"""

from neonize.proto.Neonize_pb2 import GroupParticipant


def is_group_admin(participant: GroupParticipant) -> bool:
    """Check if participant is a group admin."""
    return participant.IsAdmin or participant.IsSuperAdmin


def is_group_owner(participant: GroupParticipant) -> bool:
    """Check if participant is the group owner/superadmin."""
    return participant.IsSuperAdmin


async def get_participant(client, group_jid: str, user_jid: str) -> GroupParticipant | None:
    """Get participant info from a group."""
    try:
        group_info = await client._client.get_group_info(client.to_jid(group_jid))
        for participant in group_info.Participants:
            if participant.JID.User == user_jid.split("@")[0]:
                return participant
    except Exception:
        pass
    return None


async def check_admin_permission(client, group_jid: str, user_jid: str) -> bool:
    """Check if user is admin in the group."""
    participant = await get_participant(client, group_jid, user_jid)
    if participant:
        return is_group_admin(participant)
    return False


async def check_bot_admin(client, group_jid: str) -> bool:
    """Check if bot is admin in the group."""
    try:
        me = await client._client.get_me()
        if me and me.JID:
            bot_jid = f"{me.JID.User}@{me.JID.Server}"
            return await check_admin_permission(client, group_jid, bot_jid)
    except Exception:
        pass
    return False
