"""
Centralized constants for the Zero Ichi bot.

All shared paths, directories, and field mappings live here
to avoid duplication across modules.
"""

from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
LOCALES_DIR = BASE_DIR / "locales"

DOWNLOADS_DIR = DATA_DIR / "downloads"
MEDIA_DIR = DATA_DIR / "media"
MEMORY_DIR = DATA_DIR / "ai_memory"
SKILLS_DIR = DATA_DIR / "ai_skills"

TASKS_FILE = DATA_DIR / "scheduled_tasks.json"

MEDIA_FIELDS = (
    ("imageMessage", "image"),
    ("videoMessage", "video"),
    ("stickerMessage", "sticker"),
    ("documentMessage", "document"),
    ("audioMessage", "audio"),
)

MEDIA_FIELD_MAP = {friendly: field for field, friendly in MEDIA_FIELDS}

CONTEXT_FIELDS = (
    "extendedTextMessage",
    "imageMessage",
    "videoMessage",
    "stickerMessage",
    "documentMessage",
    "audioMessage",
)

TEXT_SOURCES = (
    ("conversation", None),
    ("extendedTextMessage", "text"),
    ("imageMessage", "caption"),
    ("videoMessage", "caption"),
)
