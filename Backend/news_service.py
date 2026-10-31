import time
import threading
import logging

from scraper import scrape_news
from summarizer import generate_news_hash
from t5_summarizer import summarize_with_t5
from cache_utils import (
    cache_get,
    cache_set
)
from config import SCRAPED_TTL

logger = logging.getLogger("news_service")

_refresh_locks = {
    "en": threading.Lock(),
    "ml": threading.Lock()
}
_is_refreshing = {
    "en": False,
    "ml": False
}


def normalize_title(title: str) -> str:
    """Normalize Malayalam unicode characters (ZWNJ, ZWJ, non-breaking space) for reliable matching."""
    if not title:
        return ""
    return (
        title.replace("\u200c", "")
        .replace("\u200d", "")
        .replace("\xa0", " ")
        .strip()
    )


def _build_news_pipeline(lang: str = "en") -> dict:
    """Scrapes and summarizes news locally using T5 model."""
    news_data = scrape_news(lang=lang)
    summaries = summarize_with_t5(news_data, lang=lang)

    summary_map = {
        item.get("title", ""): item.get("summary", "")
        for item in summaries
        if isinstance(item, dict)
    }
    norm_summary_map = {
        normalize_title(item.get("title", "")): item.get("summary", "")
        for item in summaries
        if isinstance(item, dict)
    }

    final_news = []
    for i, article in enumerate(news_data):
        raw_title = article.get("title", "")
        norm_title = normalize_title(raw_title)

        summary = summary_map.get(raw_title)
        if not summary:
            summary = norm_summary_map.get(norm_title)
        if not summary and i < len(summaries):
            candidate = summaries[i]
            if isinstance(candidate, dict):
                summary = candidate.get("summary")
        if not summary:
            summary = article.get("description", "").strip() or raw_title

        final_news.append({
            "title": raw_title,
            "source": article.get("source", ""),
            "link": article.get("link", ""),
            "description": article.get("description", ""),
            "summary": summary
        })

    payload = {
        "count": len(final_news),
        "news": final_news,
        "updated_at": time.time(),
        "is_updating": False,
        "stale": False
    }

    # Store in Redis: long-term latest cache (7 days) + fresh flag (SCRAPED_TTL)
    cache_set(f"news:final:{lang}:latest", payload, ttl=86400 * 7)
    cache_set(f"news:final:{lang}:fresh", True, ttl=SCRAPED_TTL)

    return payload


def _background_refresh_worker(lang: str):
    """Background worker that fetches fresh news without blocking users."""
    global _is_refreshing
    lock = _refresh_locks.get(lang, _refresh_locks["en"])
    if not lock.acquire(blocking=False):
        # Another worker is already updating this language
        return

    try:
        _is_refreshing[lang] = True
        logger.info(f"Starting background refresh for {lang} news...")
        _build_news_pipeline(lang=lang)
        logger.info(f"Background refresh for {lang} news complete.")
    except Exception as e:
        logger.error(f"Error during background refresh for {lang}: {e}")
    finally:
        _is_refreshing[lang] = False
        lock.release()


def trigger_background_refresh(lang: str):
    """Launches a background worker thread if not already running."""
    if not _is_refreshing.get(lang, False):
        t = threading.Thread(
            target=_background_refresh_worker,
            args=(lang,),
            name=f"bg-refresh-{lang}",
            daemon=True
        )
        t.start()


def get_final_news(lang: str = "en", force_refresh: bool = False):
    """
    Stale-While-Revalidate (SWR) news fetcher.
    - If previous/old news exists, returns it immediately (sub-millisecond)
      so the user NEVER waits on a loading screen.
    - Triggers background scrape & summarization when stale or force_refresh is requested.
    - Only blocks if no news has ever been fetched (very first cold run).
    """
    latest = cache_get(f"news:final:{lang}:latest")
    is_fresh = cache_get(f"news:final:{lang}:fresh")

    if latest and isinstance(latest, dict) and latest.get("news"):
        if force_refresh or not is_fresh:
            trigger_background_refresh(lang)
            return {
                **latest,
                "is_updating": True,
                "stale": True
            }
        return {
            **latest,
            "is_updating": _is_refreshing.get(lang, False),
            "stale": False
        }

    # First time ever cold run (nothing in cache): build initial feed
    return _build_news_pipeline(lang=lang)
