import pytest

import core.permissions as permissions_module
from core.permissions import check_command_permissions
from core.types import ChatType


class DummyCommand:
    def __init__(self, name: str, owner_only: bool = True):
        self.name = name
        self.owner_only = owner_only
        self.admin_only = False
        self.bot_admin_required = False
        self.group_only = False
        self.private_only = False

    def can_execute(self, chat_type):
        return chat_type in {ChatType.PRIVATE, ChatType.GROUP}


class DummyMessage:
    def __init__(self, text: str, is_group: bool = False):
        self.text = text
        self.is_group = is_group
        self.chat_type = ChatType.GROUP if is_group else ChatType.PRIVATE
        self.sender_jid = "12345@s.whatsapp.net"


async def _false_owner(_sender_jid, _bot):
    return False


@pytest.mark.asyncio
async def test_config_owner_me_allowed_when_owner_not_set(monkeypatch):
    monkeypatch.setattr(permissions_module.runtime_config, "get_owner_jid", lambda: "")
    monkeypatch.setattr(permissions_module.runtime_config, "is_owner_async", _false_owner)

    cmd = DummyCommand("config", owner_only=True)
    msg = DummyMessage("/config owner me")

    result = await check_command_permissions(cmd, msg, bot=object())
    assert result.allowed is True


@pytest.mark.asyncio
async def test_config_all_blocked_when_owner_not_set(monkeypatch):
    monkeypatch.setattr(permissions_module.runtime_config, "get_owner_jid", lambda: "")
    monkeypatch.setattr(permissions_module.runtime_config, "is_owner_async", _false_owner)

    cmd = DummyCommand("config", owner_only=True)
    msg = DummyMessage("/config all")

    result = await check_command_permissions(cmd, msg, bot=object())
    assert result.allowed is False


@pytest.mark.asyncio
async def test_setup_start_allowed_when_owner_not_set(monkeypatch):
    monkeypatch.setattr(permissions_module.runtime_config, "get_owner_jid", lambda: "")
    monkeypatch.setattr(permissions_module.runtime_config, "is_owner_async", _false_owner)

    cmd = DummyCommand("setup", owner_only=True)
    msg = DummyMessage("/setup start")

    result = await check_command_permissions(cmd, msg, bot=object())
    assert result.allowed is True


@pytest.mark.asyncio
async def test_setup_write_blocked_when_owner_not_set(monkeypatch):
    monkeypatch.setattr(permissions_module.runtime_config, "get_owner_jid", lambda: "")
    monkeypatch.setattr(permissions_module.runtime_config, "is_owner_async", _false_owner)

    cmd = DummyCommand("setup", owner_only=True)
    msg = DummyMessage("/setup anti-link on warn")

    result = await check_command_permissions(cmd, msg, bot=object())
    assert result.allowed is False


@pytest.mark.asyncio
async def test_owner_only_still_blocked_when_owner_set(monkeypatch):
    monkeypatch.setattr(
        permissions_module.runtime_config,
        "get_owner_jid",
        lambda: "owner@s.whatsapp.net",
    )
    monkeypatch.setattr(permissions_module.runtime_config, "is_owner_async", _false_owner)

    cmd = DummyCommand("config", owner_only=True)
    msg = DummyMessage("/config owner me")

    result = await check_command_permissions(cmd, msg, bot=object())
    assert result.allowed is False
