from core.timefmt import format_uptime


def test_format_uptime_without_seconds():
    assert format_uptime(18 * 60) == "18m"
    assert format_uptime(2 * 3600 + 5 * 60) == "2h 5m"


def test_format_uptime_with_seconds():
    assert format_uptime(59, include_seconds=True) == "59s"
    assert format_uptime(61, include_seconds=True) == "1m 1s"
