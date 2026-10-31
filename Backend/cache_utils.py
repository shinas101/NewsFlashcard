"""
Redis-based caching layer for production.
- Tries standard Redis server via REDIS_URL if an external server is configured.
- Embedded persistent cache using fakeredis backed by SQLite (WAL mode)
  for zero-dependency, crash-resilient, and thread-safe caching.
- In-memory fallback if persistence fails.
"""
import os
import json
import time
import hashlib
import sqlite3
import threading
import logging
from typing import Any, Optional, Union, List, Dict

from config import REDIS_URL, REDIS_DB_FILE, SCRAPED_TTL

logger = logging.getLogger("cache_utils")


class RedisCache:
    """Thread-safe Redis-compliant caching client with SQLite persistence."""

    def __init__(self):
        self.client = None
        self.mode = "none"
        self._conn = None
        self._lock = threading.RLock()
        self._init_client()

    def _init_client(self):
        # 1. Try standard external Redis via REDIS_URL if provided
        if REDIS_URL and "localhost" not in REDIS_URL and "127.0.0.1" not in REDIS_URL:
            try:
                import redis
                r = redis.Redis.from_url(REDIS_URL, socket_connect_timeout=2)
                r.ping()
                self.client = r
                self.mode = "redis_server"
                logger.info("Connected to external Redis server at %s", REDIS_URL)
                return
            except Exception as e:
                logger.warning(
                    "External Redis unreachable (%s). Falling back to embedded persistent cache.", e
                )

        # 2. Use fakeredis + SQLite persistent backing (zero external socket dependencies)
        try:
            import fakeredis
            self.client = fakeredis.FakeRedis()
            self.mode = "fakeredis_sqlite"
            self._init_sqlite()
            self._load_from_sqlite()
            logger.info("Using embedded persistent Redis cache (fakeredis + sqlite WAL: %s)", REDIS_DB_FILE)
            return
        except Exception as e:
            logger.warning("Could not initialize fakeredis persistent cache: %s", e)

        # 3. Fallback memory
        self.mode = "fallback_memory"
        self._store = {}
        logger.info("Using in-memory dictionary fallback cache.")

    def _init_sqlite(self):
        with self._lock:
            self._conn = sqlite3.connect(
                REDIS_DB_FILE,
                check_same_thread=False,
                timeout=15.0
            )
            # Enable WAL mode for high concurrency across threads
            self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.execute("PRAGMA synchronous=NORMAL;")
            with self._conn:
                self._conn.execute("""
                    CREATE TABLE IF NOT EXISTS redis_store (
                        key TEXT PRIMARY KEY,
                        val TEXT NOT NULL,
                        expires_at REAL NOT NULL
                    )
                """)
                self._conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_redis_expires ON redis_store (expires_at)
                """)

    def _load_from_sqlite(self):
        now = time.time()
        try:
            with self._lock:
                with self._conn:
                    # Clean expired keys immediately on startup
                    self._conn.execute("DELETE FROM redis_store WHERE expires_at <= ?", (now,))
                    cursor = self._conn.execute(
                        "SELECT key, val, expires_at FROM redis_store WHERE expires_at > ?", (now,)
                    )
                    rows = cursor.fetchall()

            loaded_count = 0
            for k, v, exp in rows:
                ttl = max(1, int(exp - now))
                self.client.setex(k, ttl, v)
                loaded_count += 1

            logger.info("Loaded %d active cached items from SQLite store.", loaded_count)
        except Exception as e:
            logger.warning("Failed loading initial state from sqlite: %s", e)

    def get(self, key: str) -> Optional[Any]:
        try:
            if self.client:
                raw = self.client.get(key)
                if raw is not None:
                    decoded = raw.decode("utf-8") if isinstance(raw, bytes) else raw
                    logger.debug("Cache HIT for key: %s", key)
                    return json.loads(decoded)
                logger.debug("Cache MISS for key: %s", key)
                return None
            elif hasattr(self, "_store"):
                with self._lock:
                    exp, val = self._store.get(key, (0, None))
                    if time.time() < exp:
                        logger.debug("Cache HIT (memory) for key: %s", key)
                        return json.loads(val)
                    self._store.pop(key, None)
                    logger.debug("Cache MISS (memory) for key: %s", key)
                    return None
        except Exception as e:
            logger.error("Error reading cache key %s: %s", key, e)
            return None

    def set(self, key: str, data: Any, ttl: int = SCRAPED_TTL) -> bool:
        try:
            payload = json.dumps(data, ensure_ascii=False)
            if self.client:
                self.client.setex(key, ttl, payload)

            if self.mode == "fakeredis_sqlite":
                exp = time.time() + ttl
                with self._lock:
                    with self._conn:
                        self._conn.execute(
                            "INSERT OR REPLACE INTO redis_store (key, val, expires_at) VALUES (?, ?, ?)",
                            (key, payload, exp)
                        )
            elif self.mode == "fallback_memory":
                with self._lock:
                    self._store[key] = (time.time() + ttl, payload)

            logger.debug("Cache SET key: %s (TTL: %ds)", key, ttl)
            return True
        except Exception as e:
            logger.error("Error saving cache key %s: %s", key, e)
            return False

    def delete(self, key: str):
        try:
            if self.client:
                self.client.delete(key)
            if self.mode == "fakeredis_sqlite":
                with self._lock:
                    with self._conn:
                        self._conn.execute("DELETE FROM redis_store WHERE key = ?", (key,))
            elif self.mode == "fallback_memory":
                with self._lock:
                    self._store.pop(key, None)
            logger.debug("Cache DELETE key: %s", key)
        except Exception as e:
            logger.error("Error deleting cache key %s: %s", key, e)

    def flush(self):
        try:
            if self.client:
                self.client.flushdb()
            if self.mode == "fakeredis_sqlite":
                with self._lock:
                    with self._conn:
                        self._conn.execute("DELETE FROM redis_store")
            elif self.mode == "fallback_memory":
                with self._lock:
                    self._store.clear()
            logger.info("Cache FLUSH complete.")
        except Exception as e:
            logger.error("Error flushing cache: %s", e)


_cache = RedisCache()


def cache_get(key: str) -> Optional[Any]:
    return _cache.get(key)


def cache_set(key: str, data: Any, ttl: int = SCRAPED_TTL) -> bool:
    return _cache.set(key, data, ttl=ttl)


def cache_delete(key: str):
    _cache.delete(key)


def cache_flush():
    _cache.flush()


def generate_news_hash(news_data: Union[str, List[Any], Dict[str, Any]]) -> str:
    """
    Polymorphic hashing utility:
    - If string: hashes content directly.
    - If list of articles: hashes sorted titles.
    - If dict: hashes string representation.
    """
    if isinstance(news_data, str):
        text = news_data.strip()
    elif isinstance(news_data, list):
        titles = sorted([
            article.get("title", "")
            for article in news_data
            if isinstance(article, dict) and article.get("title")
        ])
        text = "|".join(titles)
    elif isinstance(news_data, dict):
        text = str(news_data.get("title", "")) + str(news_data.get("description", ""))
    else:
        text = str(news_data)

    return hashlib.md5(text.encode("utf-8")).hexdigest()
