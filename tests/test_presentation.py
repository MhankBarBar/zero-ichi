from core.presentation import format_command_card


def test_format_command_card_contains_expected_sections():
    text = format_command_card(
        ".",
        "permission",
        "Manage role overrides for command access",
        ".permission list | set | reset",
        aliases=["permissions", "perm"],
        category="owner",
        restrictions=["Owner only"],
    )

    assert "「 `.permission` 」" in text
    assert "» Manage role overrides for command access" in text
    assert "• *Usage:* `.permission list | set | reset`" in text
    assert "• *Aliases:* `.permissions`, `.perm`" in text
    assert "• *Category:* ⛯ Owner" in text
    assert "⊘ *Restrictions:* Owner only" in text
