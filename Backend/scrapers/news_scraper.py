"""
High-Performance News Scraper Orchestrator
- Coordinates multi-threaded Google News RSS extraction.
- Routes article links to specialized site scrapers or generic fallback parser.
- Maintains 100% backward compatibility for all public functions.
"""
import time
import logging
from typing import Optional, List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup

from config import SCRAPER_MAX_WORKERS, SCRAPER_TIMEOUT
from .base import (
    _session,
    fetch_page_html,
    clean_scraped_text,
    strip_unwanted_elements,
    BaseSiteScraper,
    _RE_GARBAGE,
)
from .google_news import (
    decode_google_news_url,
    decode_url,
    get_decoding_params,
    get_base64_str,
    fetch_google_news_feed,
)
from .manorama import ManoramaScraper
from .mathrubhumi import MathrubhumiScraper
from .asianet import AsianetScraper
from .news18 import News18Scraper
from .madhyamam import MadhyamamScraper
from .the_hindu import TheHinduScraper
from .times_of_india import TimesOfIndiaScraper
from .ndtv import NDTVScraper
from .indian_express import IndianExpressScraper
from .generic import GenericScraper

logger = logging.getLogger("scrapers.orchestrator")

# Site-specific scraper registry
SITE_SCRAPERS: List[BaseSiteScraper] = [
    ManoramaScraper(),
    MathrubhumiScraper(),
    AsianetScraper(),
    News18Scraper(),
    MadhyamamScraper(),
    TheHinduScraper(),
    TimesOfIndiaScraper(),
    NDTVScraper(),
    IndianExpressScraper(),
]
GENERIC_SCRAPER = GenericScraper()


def extract_article_content(url: str, source: str = "") -> str:
    """
    Extract article content by routing to the dedicated website scraper,
    falling back to generic structured / semantic parsing.
    """
    if not url or not url.startswith("http"):
        return ""

    try:
        html = fetch_page_html(url, timeout=SCRAPER_TIMEOUT)
        if not html:
            return ""

        soup = BeautifulSoup(html, "lxml")

        # Strip scripts, styles, navigation, figures before DOM traversal
        strip_unwanted_elements(soup)

        # 1. Check specialized website scrapers first
        for scraper in SITE_SCRAPERS:
            if scraper.can_handle(source=source, url=url):
                content = scraper.extract(soup, url=url)
                if content:
                    logger.debug("Successfully extracted via %s for %s", scraper.name, url)
                    return content

        # 2. Fall back to generic parser (JSON-LD, standard article body containers, meta tags)
        generic_content = GENERIC_SCRAPER.extract(soup, url=url)
        if generic_content:
            return generic_content

        return ""
    except Exception as e:
        logger.debug("Failed extracting content from %s: %s", url, e)
        return ""


def scrape_news(lang: str = "en", limit: int = 25) -> List[Dict[str, str]]:
    """
    Scrapes major headlines from Google News (India English or Malayalam).
    Extracts article content concurrently across site-specific scrapers.
    """
    start_time = time.time()
    news_data = []

    entries = fetch_google_news_feed(lang=lang, limit=limit)
    if not entries:
        return []

    def _process_entry(item: Dict[str, Any]) -> Optional[Dict[str, str]]:
        raw_title = item.get("title", "")
        parts = raw_title.rsplit("-", 1)
        title = parts[0].strip() if len(parts) > 1 else raw_title.strip()
        source = parts[-1].strip() if len(parts) > 1 else ("Malayalam News" if lang == "ml" else "India News")

        raw_link = item.get("link", "")
        try:
            decoded = decode_google_news_url(raw_link)
            link = decoded.get("decoded_url", raw_link) if decoded.get("status") else raw_link
        except Exception:
            link = raw_link

        description = extract_article_content(link, source=source)
        description = clean_scraped_text(description)

        # Fallback to RSS summary if extracted page body is empty
        if not description:
            rss_summary = item.get("summary", "")
            if rss_summary:
                clean_rss = BeautifulSoup(rss_summary, "html.parser").get_text(" ", strip=True)
                if len(clean_rss) > 20:
                    description = clean_rss

        return {
            "title": title,
            "link": link,
            "source": source,
            "description": description
        }

    with ThreadPoolExecutor(max_workers=SCRAPER_MAX_WORKERS, thread_name_prefix=f"scraper-{lang}") as executor:
        futures = [executor.submit(_process_entry, entry) for entry in entries]
        for f in as_completed(futures):
            try:
                res = f.result()
                if res and res.get("title"):
                    news_data.append(res)
            except Exception as e:
                logger.warning("Error scraping entry: %s", e)

    elapsed = time.time() - start_time
    logger.info("Successfully scraped %d %s news articles in %.2fs", len(news_data), lang, elapsed)
    return news_data
