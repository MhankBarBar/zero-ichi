from commands.owner.config import (
    _is_sensitive_path,
    _mask_value,
    _resolve_diff_mode,
    render_diff_image,
)


def test_sensitive_path_detection_and_masking():
    assert _is_sensitive_path("agentic_ai.api_key")
    assert _is_sensitive_path("dashboard.password")
    assert not _is_sensitive_path("bot.prefix")

    assert _mask_value("agentic_ai.api_key", "sk-123") == "[redacted]"
    assert _mask_value("bot.prefix", "!") == "!"


def test_render_diff_image_returns_png_bytes():
    rows = [
        ("~ bot.prefix: / -> !", "changed"),
        ("+ privacy.ai_memory_enabled: True", "added"),
        ("- features.old_flag: False", "missing"),
    ]
    data = render_diff_image("Config Differences", rows)
    assert isinstance(data, bytes)
    assert data.startswith(b"\x89PNG\r\n\x1a\n")


def test_resolve_diff_mode_defaults_image_and_supports_text():
    assert _resolve_diff_mode(None) == "image"
    assert _resolve_diff_mode([]) == "image"
    assert _resolve_diff_mode(["text"]) == "text"
    assert _resolve_diff_mode(["txt"]) == "text"
    assert _resolve_diff_mode(["image"]) == "image"
