"""ID generation helpers."""

from __future__ import annotations

from typing import Any


def next_prefixed_id(
    entries: list[dict[str, Any]],
    *,
    prefix: str,
    width: int,
    key: str = "id",
) -> str:
    """Generate next sequential prefixed id (e.g. A001, H0001)."""
    normalized_prefix = str(prefix).upper()
    max_idx = 0
    for item in entries:
        raw = str(item.get(key, "")).strip().upper()
        if len(raw) != len(normalized_prefix) + width:
            continue
        if not raw.startswith(normalized_prefix):
            continue
        number_part = raw[len(normalized_prefix) :]
        if not number_part.isdigit():
            continue
        max_idx = max(max_idx, int(number_part))
    return f"{normalized_prefix}{max_idx + 1:0{width}d}"
