"""Shared URL regex patterns."""

from __future__ import annotations

import re

URL_PATTERN = re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+', re.IGNORECASE)
