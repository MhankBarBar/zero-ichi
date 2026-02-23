"""
JSONC (JSON with Comments) parser utility.

Supports:
- Single-line comments (//)
- Multi-line comments (/* ... */)
- Trailing commas
"""

import json
import re
from pathlib import Path
from typing import Any


def strip_comments(jsonc_str: str) -> str:
    """
    Remove comments from JSONC string.

    Handles:
    - Single-line comments (//)
    - Multi-line comments (/* ... */)
    - Comments inside strings are preserved
    """
    result = []
    i = 0
    in_string = False
    escape_next = False

    while i < len(jsonc_str):
        char = jsonc_str[i]

        if escape_next:
            result.append(char)
            escape_next = False
            i += 1
            continue

        if char == "\\" and in_string:
            result.append(char)
            escape_next = True
            i += 1
            continue

        if char == '"' and not escape_next:
            in_string = not in_string
            result.append(char)
            i += 1
            continue

        if not in_string:
            if char == "/" and i + 1 < len(jsonc_str) and jsonc_str[i + 1] == "/":
                while i < len(jsonc_str) and jsonc_str[i] != "\n":
                    i += 1
                continue

            if char == "/" and i + 1 < len(jsonc_str) and jsonc_str[i + 1] == "*":
                i += 2
                while i + 1 < len(jsonc_str):
                    if jsonc_str[i] == "*" and jsonc_str[i + 1] == "/":
                        i += 2
                        break
                    i += 1
                continue

        result.append(char)
        i += 1

    return "".join(result)


def strip_trailing_commas(json_str: str) -> str:
    """Remove trailing commas before ] or }."""
    json_str = re.sub(r",\s*([}\]])", r"\1", json_str)
    return json_str


def loads(jsonc_str: str) -> Any:
    """Parse JSONC string to Python object."""
    clean = strip_comments(jsonc_str)
    clean = strip_trailing_commas(clean)
    return json.loads(clean)


def load(file_path: Path | str) -> Any:
    """Load and parse JSONC file."""
    path = Path(file_path)
    if not path.exists():
        return {}

    with open(path, encoding="utf-8") as f:
        return loads(f.read())


def dumps(obj: Any, indent: int = 2) -> str:
    """Dump Python object to JSON string (no comments - those are manual)."""
    return json.dumps(obj, indent=indent, ensure_ascii=False)


def dump(obj: Any, file_path: Path | str, indent: int = 2) -> None:
    """Dump Python object to JSON file."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        f.write(dumps(obj, indent))
