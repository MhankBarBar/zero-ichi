from ai import agent as ai_agent


def test_blocked_actions_are_enforced(monkeypatch):
    def fake_get_nested(*keys, default=None):
        if keys == ("agentic_ai", "allowed_actions"):
            return ["ping", "eval"]
        if keys == ("agentic_ai", "blocked_actions"):
            return ["eval"]
        return default

    monkeypatch.setattr(ai_agent.runtime_config, "get_nested", fake_get_nested)

    assert ai_agent._is_ai_action_allowed("ping")
    assert not ai_agent._is_ai_action_allowed("eval")
    assert not ai_agent._is_ai_action_allowed("help")


def test_allowed_actions_empty_uses_blocklist_only(monkeypatch):
    def fake_get_nested(*keys, default=None):
        if keys == ("agentic_ai", "allowed_actions"):
            return []
        if keys == ("agentic_ai", "blocked_actions"):
            return ["shutdown"]
        return default

    monkeypatch.setattr(ai_agent.runtime_config, "get_nested", fake_get_nested)

    assert ai_agent._is_ai_action_allowed("ping")
    assert not ai_agent._is_ai_action_allowed("shutdown")
