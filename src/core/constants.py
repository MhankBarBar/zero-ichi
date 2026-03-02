"""
Centralized constants for the Zero Ichi bot.

All shared paths, directories, and field mappings live here
to avoid duplication across modules.
"""

from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
LOCALES_DIR = Path(__file__).parent.parent / "locales"

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

PHOTO_IMAGE_EXTENSIONS = frozenset(
    {
        "jpg",
        "jpeg",
        "png",
        "webp",
        "gif",
        "bmp",
        "tif",
        "tiff",
        "avif",
    }
)

PHOTO_DEFAULT_HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
}

PHOTO_AUTH_REQUIRED_HINTS = (
    "redirect to login page",
    "accounts/login",
    "login required",
    "requires authentication",
    "not logged in",
)

AUTO_DL_PHOTO_FIRST_HOSTS = frozenset(
    {
        "danbooru.donmai.us",
        "cdn.donmai.us",
        "gelbooru.com",
        "safebooru.org",
        "rule34.xxx",
    }
)

PHOTO_DESCRIPTION_PATHS = (
    "description",
    "caption",
    "title",
    "content",
    "text",
    "message",
    "post.title",
    "post.description",
)

PHOTO_USERNAME_PATHS = (
    "username",
    "user.username",
    "owner.username",
    "author",
    "uploader",
    "creator",
    "artist",
    "artist.name",
    "account.username",
    "profile.username",
    "profile.name",
    "display_name",
    "name",
    "tags_artist.0",
    "category",
)

PHOTO_LIKES_PATHS = (
    "likes",
    "like_count",
    "likes_count",
    "favorite_count",
    "favorites_count",
    "favourites_count",
    "fav_count",
    "reaction_count",
    "score",
    "up_score",
)

PHOTO_HANDLE_PATTERN = r"^[A-Za-z0-9._-]{2,64}$"
