"""
News Service Layer (SWR Architecture)
- Stale-While-Revalidate caching pattern for instant sub-millisecond response times.
- Background asynchronous worker threads for non-blocking feed updates.
- Normalizes Malayalam & English unicode strings for zero-mismatch summary joining.
- Thread-safe state synchronization.
"""
import time
import threading
import logging
from typing import Dict, Any, List, Optional

from scrapers import scrape_news
from summarizers import summarize_with_t5
from storage import cache_get, cache_set
from config import SCRAPED_TTL, CACHE_LONG_TTL

logger = logging.getLogger("services.news")

# Concurrency control per language
_refresh_locks: Dict[str, threading.Lock] = {
    "en": threading.Lock(),
    "ml": threading.Lock()
}
_is_refreshing: Dict[str, bool] = {
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


def _match_summary(
    raw_title: str,
    norm_title: str,
    article_idx: int,
    article: Dict[str, Any],
    summaries: List[Dict[str, str]],
    summary_map: Dict[str, str],
    norm_summary_map: Dict[str, str]
) -> str:
    """Multi-tiered matching strategy to accurately link scraped articles with their generated summaries."""
    # 1. Exact title match
    summary = summary_map.get(raw_title)
    if summary:
        return summary

    # 2. Normalized unicode title match
    summary = norm_summary_map.get(norm_title)
    if summary:
        return summary

    # 3. Positional index candidate fallback
    if article_idx < len(summaries):
        candidate = summaries[article_idx]
        if isinstance(candidate, dict) and candidate.get("summary"):
            return candidate["summary"]

    # 4. Fallback to article description or raw headline
    return article.get("description", "").strip() or raw_title


def _build_news_pipeline(lang: str = "en") -> Dict[str, Any]:
    """Scrapes and summarizes news locally using T5 model."""
    start_time = time.time()
    logger.info("Executing news pipeline for '%s'...", lang)

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

    final_news: List[Dict[str, Any]] = []
    for i, article in enumerate(news_data):
        raw_title = article.get("title", "")
        norm_title = normalize_title(raw_title)

        summary = _match_summary(
            raw_title=raw_title,
            norm_title=norm_title,
            article_idx=i,
            article=article,
            summaries=summaries,
            summary_map=summary_map,
            norm_summary_map=norm_summary_map
        )

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
    cache_set(f"news:final:{lang}:latest", payload, ttl=CACHE_LONG_TTL)
    cache_set(f"news:final:{lang}:fresh", True, ttl=SCRAPED_TTL)

    elapsed = time.time() - start_time
    logger.info("News pipeline for '%s' completed successfully (%d articles, %.2fs).", lang, len(final_news), elapsed)
    return payload


def _background_refresh_worker(lang: str):
    """Background worker that fetches fresh news without blocking users."""
    global _is_refreshing
    lock = _refresh_locks.get(lang, _refresh_locks["en"])

    if not lock.acquire(blocking=False):
        logger.info("Background refresh worker for '%s' skipped: another task holds the lock.", lang)
        return

    try:
        _is_refreshing[lang] = True
        logger.info("Starting background refresh worker for '%s'...", lang)
        _build_news_pipeline(lang=lang)
        logger.info("Background refresh worker for '%s' completed.", lang)
    except Exception as e:
        logger.exception("Error during background refresh worker for '%s': %s", lang, e)
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
        logger.info("Launched background refresh thread '%s'", t.name)


def get_final_news(lang: str = "en", force_refresh: bool = False) -> Dict[str, Any]:
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
            logger.info("Serving cached news (stale=%s, force=%s), triggering background refresh.", not is_fresh, force_refresh)
            trigger_background_refresh(lang)
            return {
                **latest,
                "is_updating": True,
                "stale": True
            }

        logger.debug("Serving fresh cached news for '%s' (age: %.1fs).", lang, time.time() - latest.get("updated_at", 0))
        return {
            **latest,
            "is_updating": _is_refreshing.get(lang, False),
            "stale": False
        }

    # First time ever cold run (nothing in cache): build initial feed
    logger.info("Cold cache run for '%s': executing initial build synchronously.", lang)
    return _build_news_pipeline(lang=lang)

