"""
In-memory message cache for anti-delete feature.

Stores recent messages for a configurable TTL to enable
forwarding deleted messages.
"""

import pickle
import sqlite3
import time
import zlib
from typing import Any

from google.protobuf.json_format import MessageToDict

from config.settings import ANTI_DELETE_CACHE_TTL
from core.logger import log_error, log_info
from core.storage import DATA_DIR


class MessageCache:
    """
    SQLite-backed persistent cache for messages.

    Uses a single SQLite database file to store messages.
    Data is Pickled and Zlib-compressed to minimize size.
    This avoids Base64 overhead for media files and allows efficient
    random access without loading the entire cache into memory.
    """

    def __init__(self, ttl_minutes: int = ANTI_DELETE_CACHE_TTL, max_size: int = 5000):
        self._db_file = DATA_DIR / "messages.db"
        self._ttl_seconds = ttl_minutes * 60
        self._max_size = max_size
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database."""
        try:
            with sqlite3.connect(self._db_file) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS messages (
                        id TEXT PRIMARY KEY,
                        timestamp REAL,
                        data BLOB
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON messages(timestamp)")
                conn.commit()
            log_info("Message cache database initialized")
        except Exception as e:
            log_error(f"Failed to init message cache DB: {e}")

    def store(self, message_id: str, data: dict[str, Any]) -> None:
        """Store a message in the cache."""
        try:
            data_copy = data.copy()

            if data_copy.get("message") and not data_copy.get("message_dict"):
                try:
                    data_copy["message_dict"] = MessageToDict(data_copy["message"])
                except Exception:
                    pass
            data_copy.pop("message", None)

            serialized = pickle.dumps(data_copy)
            compressed = zlib.compress(serialized)

            timestamp = time.time()

            with sqlite3.connect(self._db_file) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO messages (id, timestamp, data) VALUES (?, ?, ?)",
                    (message_id, timestamp, compressed),
                )

                cursor = conn.execute("SELECT COUNT(*) FROM messages")
                count = cursor.fetchone()[0]

                if count > self._max_size:
                    conn.execute(
                        """
                        DELETE FROM messages WHERE id IN (
                            SELECT id FROM messages ORDER BY timestamp ASC LIMIT ?
                        )
                    """,
                        (count - self._max_size,),
                    )

                conn.execute(
                    "DELETE FROM messages WHERE timestamp < ?",
                    (timestamp - self._ttl_seconds,),
                )
                conn.commit()

        except Exception as e:
            log_error(f"Failed to store message {message_id}: {e}")

    def get(self, message_id: str) -> dict[str, Any] | None:
        """Get a message from the cache if it exists and hasn't expired."""
        try:
            with sqlite3.connect(self._db_file) as conn:
                cursor = conn.execute(
                    "SELECT timestamp, data FROM messages WHERE id = ?", (message_id,)
                )
                row = cursor.fetchone()

                if not row:
                    return None

                timestamp, blob = row

                if time.time() - timestamp > self._ttl_seconds:
                    conn.execute("DELETE FROM messages WHERE id = ?", (message_id,))
                    conn.commit()
                    return None

                try:
                    decompressed = zlib.decompress(blob)
                    data = pickle.loads(decompressed)
                    return data
                except Exception as e:
                    log_error(f"Failed to deserialize message {message_id}: {e}")
                    return None

        except Exception as e:
            log_error(f"Failed to get message {message_id}: {e}")
            return None

    def remove(self, message_id: str) -> dict[str, Any] | None:
        """Remove and return a message from the cache."""
        data = self.get(message_id)
        if data:
            try:
                with sqlite3.connect(self._db_file) as conn:
                    conn.execute("DELETE FROM messages WHERE id = ?", (message_id,))
                    conn.commit()
            except Exception:
                pass
        return data

    def __len__(self) -> int:
        try:
            with sqlite3.connect(self._db_file) as conn:
                return conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        except Exception:
            return 0


message_cache = MessageCache()
