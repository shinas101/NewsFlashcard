"""
Application Configuration
Centralized configuration with environment variable support and safe production defaults.
"""
import os
import logging

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Server & Runtime
PORT = int(os.getenv("PORT", 8000))
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Redis Cache configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_DB_FILE = os.path.join(BASE_DIR, "redis_cache.db")

# Time-to-live constants (in seconds)
SCRAPED_TTL = int(os.getenv("SCRAPED_TTL", 3600))        # 1 hour fresh window
CACHE_LONG_TTL = int(os.getenv("CACHE_LONG_TTL", 86400 * 7))  # 7 days persistent fallback

# HTTP Scraper settings
SCRAPER_MAX_WORKERS = int(os.getenv("SCRAPER_MAX_WORKERS", 6))
SCRAPER_TIMEOUT = int(os.getenv("SCRAPER_TIMEOUT", 10))

# Model inference settings
T5_MODEL_ID = os.getenv("T5_MODEL_ID", "google-t5/t5-small")
T5_BATCH_SIZE = int(os.getenv("T5_BATCH_SIZE", 6))
