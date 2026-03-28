from commands.owner.addskill import build_inline_skill


def test_build_inline_skill_from_inline_text():
    skill = build_inline_skill("translator Always translate to English")
    assert skill is not None
    assert skill["name"] == "translator"
    assert "Always translate" in skill["content"]
    assert skill["trigger"] == "always"


def test_build_inline_skill_from_quoted_text():
    skill = build_inline_skill("translator", quoted_text="Translate to Indonesian")
    assert skill is not None
    assert skill["name"] == "translator"
    assert skill["content"] == "Translate to Indonesian"


def test_build_inline_skill_requires_content():
    assert build_inline_skill("translator") is None
