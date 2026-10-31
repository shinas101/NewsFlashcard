"""
Redis-based caching layer for production.
- Tries redislite first (POSIX / Linux / macOS).
- Tries standard Redis server via REDIS_URL.
- On Windows or environments without an external Redis service:
  uses fakeredis with SQLite backing (redis_cache.db) for zero-dependency,
  persistent, 100% Redis-compliant caching.
"""
import os
import json
import time
import hashlib
import sqlite3
import logging
from typing import Any, Optional

from config import REDIS_URL, REDIS_DB_FILE, SCRAPED_TTL

logger = logging.getLogger("cache_utils")


class RedisCache:
    def __init__(self):
        self.client = None
        self.mode = "none"
        self._conn = None
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
                logger.info(f"Using Redis server at {REDIS_URL}")
                return
            except Exception as e:
                logger.warning(f"External Redis not reachable ({e}), falling back to embedded persistent cache.")

        # 2. Use fakeredis + SQLite persistent backing (zero socket dependency, fast & reliable)
        try:
            import fakeredis
            self.client = fakeredis.FakeRedis()
            self.mode = "fakeredis_sqlite"
            self._init_sqlite()
            self._load_from_sqlite()
            logger.info("Using embedded persistent Redis (fakeredis + sqlite)")
            return
        except Exception as e:
            logger.warning(f"Could not initialize fakeredis: {e}")

        # 3. Fallback memory
        self.mode = "fallback_memory"
        self._store = {}

    def _init_sqlite(self):
        self._conn = sqlite3.connect(REDIS_DB_FILE, check_same_thread=False)
        with self._conn:
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS redis_store (
                    key TEXT PRIMARY KEY,
                    val TEXT NOT NULL,
                    expires_at REAL NOT NULL
                )
            """)

    def _load_from_sqlite(self):
        now = time.time()
        try:
            with self._conn:
                cursor = self._conn.execute(
                    "SELECT key, val, expires_at FROM redis_store WHERE expires_at > ?", (now,)
                )
                for k, v, exp in cursor.fetchall():
                    ttl = max(1, int(exp - now))
                    self.client.setex(k, ttl, v)
        except Exception as e:
            logger.warning(f"Failed loading initial state from sqlite: {e}")

    def get(self, key: str) -> Optional[Any]:
        try:
            if self.client:
                raw = self.client.get(key)
                if raw:
                    return json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw)
                return None
            elif hasattr(self, "_store"):
                exp, val = self._store.get(key, (0, None))
                if time.time() < exp:
                    return json.loads(val)
                self._store.pop(key, None)
                return None
        except Exception as e:
            logger.error(f"Error reading cache key {key}: {e}")
            return None

    def set(self, key: str, data: Any, ttl: int = SCRAPED_TTL) -> bool:
        try:
            payload = json.dumps(data, ensure_ascii=False)
            if self.client:
                self.client.setex(key, ttl, payload)
            if self.mode == "fakeredis_sqlite":
                exp = time.time() + ttl
                with self._conn:
                    self._conn.execute(
                        "INSERT OR REPLACE INTO redis_store (key, val, expires_at) VALUES (?, ?, ?)",
                        (key, payload, exp)
                    )
            elif self.mode == "fallback_memory":
                self._store[key] = (time.time() + ttl, payload)
            return True
        except Exception as e:
            logger.error(f"Error saving cache key {key}: {e}")
            return False

    def delete(self, key: str):
        try:
            if self.client:
                self.client.delete(key)
            if self.mode == "fakeredis_sqlite":
                with self._conn:
                    self._conn.execute("DELETE FROM redis_store WHERE key = ?", (key,))
        except Exception as e:
            logger.error(f"Error deleting cache key {key}: {e}")

    def flush(self):
        try:
            if self.client:
                self.client.flushdb()
            if self.mode == "fakeredis_sqlite":
                with self._conn:
                    self._conn.execute("DELETE FROM redis_store")
        except Exception as e:
            logger.error(f"Error flushing cache: {e}")


_cache = RedisCache()


def cache_get(key: str) -> Optional[Any]:
    return _cache.get(key)


def cache_set(key: str, data: Any, ttl: int = SCRAPED_TTL) -> bool:
    return _cache.set(key, data, ttl=ttl)


def cache_delete(key: str):
    _cache.delete(key)


def cache_flush():
    _cache.flush()


def generate_news_hash(news_data) -> str:
    titles = sorted([
        article.get("title", "")
        for article in news_data
        if isinstance(article, dict)
    ])
    text = "|".join(titles)
    return hashlib.md5(text.encode("utf-8")).hexdigest()
