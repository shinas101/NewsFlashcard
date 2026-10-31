# config.py
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Redis Cache configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_DB_FILE = os.path.join(BASE_DIR, "redis_cache.db")

# Time-to-live for cached news (seconds) - 1 hour
SCRAPED_TTL = 3600
