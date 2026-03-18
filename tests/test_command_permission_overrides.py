import pytest

import core.permissions as permissions_module
from core.permissions import check_command_permissions
from core.types import ChatType


class DummyCommand:
    def __init__(
        self,
        name: str,
        *,
        owner_only: bool = False,
        admin_only: bool = False,
    ):
        self.name = name
        self.owner_only = owner_only
        self.admin_only = admin_only
        self.bot_admin_required = False
        self.group_only = False
        self.private_only = False

    def can_execute(self, chat_type):
        return chat_type in {ChatType.PRIVATE, ChatType.GROUP}


class DummyMessage:
    def __init__(
        self,
        text: str,
        *,
        sender_jid: str = "111@s.whatsapp.net",
        chat_jid: str = "123@g.us",
        is_group: bool = True,
    ):
        self.text = text
        self.sender_jid = sender_jid
        self.chat_jid = chat_jid
        self.is_group = is_group
        self.chat_type = ChatType.GROUP if is_group else ChatType.PRIVATE


async def _owner_false(_sender_jid, _bot):
    return False


@pytest.mark.asyncio
async def test_global_admin_override_blocks_member(monkeypatch):
    async def _is_admin(_bot, _group_jid, _user_jid):
        return False

    monkeypatch.setattr(
        permissions_module.runtime_config, "get_owner_jid", lambda: "owner@s.whatsapp.net"
    )
    monkeypatch.setattr(permissions_module.runtime_config, "is_owner_async", _owner_false)
    monkeypatch.setattr(permissions_module, "check_admin_permission", _is_admin)
    monkeypatch.setattr(
        permissions_module.runtime_config,
        "get_command_role_override",
        lambda name, group_jid=None: "admin" if name == "ping" else None,
    )
    monkeypatch.setattr(permissions_module.runtime_config, "is_command_enabled", lambda _name: True)

    cmd = DummyCommand("ping")
    msg = DummyMessage("/ping", is_group=True)

    result = await check_command_permissions(cmd, msg, bot=object())
    assert result.allowed is False


@pytest.mark.asyncio
async def test_global_admin_override_allows_admin(monkeypatch):
    async def _is_admin(_bot, _group_jid, _user_jid):
        return True

    monkeypatch.setattr(
        permissions_module.runtime_config, "get_owner_jid", lambda: "owner@s.whatsapp.net"
    )
    monkeypatch.setattr(permissions_module.runtime_config, "is_owner_async", _owner_false)
    monkeypatch.setattr(permissions_module, "check_admin_permission", _is_admin)
    monkeypatch.setattr(
        permissions_module.runtime_config,
        "get_command_role_override",
        lambda name, group_jid=None: "admin" if name == "ping" else None,
    )
    monkeypatch.setattr(permissions_module.runtime_config, "is_command_enabled", lambda _name: True)

    cmd = DummyCommand("ping")
    msg = DummyMessage("/ping", is_group=True)

    result = await check_command_permissions(cmd, msg, bot=object())
    assert result.allowed is True


@pytest.mark.asyncio
async def test_group_override_can_relax_admin_to_member(monkeypatch):
    async def _is_admin(_bot, _group_jid, _user_jid):
        return False

    monkeypatch.setattr(
        permissions_module.runtime_config, "get_owner_jid", lambda: "owner@s.whatsapp.net"
    )
    monkeypatch.setattr(permissions_module.runtime_config, "is_owner_async", _owner_false)
    monkeypatch.setattr(permissions_module, "check_admin_permission", _is_admin)
    monkeypatch.setattr(
        permissions_module.runtime_config,
        "get_command_role_override",
        lambda name, group_jid=None: "member"
        if name == "warn" and group_jid == "123@g.us"
        else None,
    )
    monkeypatch.setattr(permissions_module.runtime_config, "is_command_enabled", lambda _name: True)

    cmd = DummyCommand("warn", admin_only=True)
    msg = DummyMessage("/warn @user")

    result = await check_command_permissions(cmd, msg, bot=object())
    assert result.allowed is True


@pytest.mark.asyncio
async def test_owner_only_cannot_be_relaxed(monkeypatch):
    async def _is_admin(_bot, _group_jid, _user_jid):
        return True

    monkeypatch.setattr(
        permissions_module.runtime_config, "get_owner_jid", lambda: "owner@s.whatsapp.net"
    )
    monkeypatch.setattr(permissions_module.runtime_config, "is_owner_async", _owner_false)
    monkeypatch.setattr(permissions_module, "check_admin_permission", _is_admin)
    monkeypatch.setattr(
        permissions_module.runtime_config,
        "get_command_role_override",
        lambda name, group_jid=None: "member" if name == "eval" else None,
    )
    monkeypatch.setattr(permissions_module.runtime_config, "is_command_enabled", lambda _name: True)

    cmd = DummyCommand("eval", owner_only=True)
    msg = DummyMessage("/eval 1+1")

    result = await check_command_permissions(cmd, msg, bot=object())
    assert result.allowed is False
