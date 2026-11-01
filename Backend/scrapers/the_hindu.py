"""
The Hindu Scraper
- Website: thehindu.com
- Domain: India National, International, and Editorial News
"""
import json
import logging
from typing import Optional
from bs4 import BeautifulSoup

from .base import BaseSiteScraper, _RE_DISCARD_STARTS

logger = logging.getLogger("scrapers.the_hindu")


class TheHinduScraper(BaseSiteScraper):
    """Specialized scraper for The Hindu news articles."""

    name = "The Hindu"
    domains = ["thehindu.com"]

    def extract(self, soup: BeautifulSoup, url: str = "") -> Optional[str]:
        try:
            # 1. Prefer high-fidelity JSON-LD editorial description
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(script.string or "")
                    candidates = data if isinstance(data, list) else [data]
                    for entry in candidates:
                        if isinstance(entry, dict) and entry.get("@type") in ("NewsArticle", "Article") and entry.get("description"):
                            desc = str(entry["description"]).strip()
                            if len(desc) >= 30:
                                return desc
                except Exception:
                    continue

            # 2. Extract from primary article body containers
            body = (
                soup.find("div", class_="articlebodycontent")
                or soup.find("div", {"itemprop": "articleBody"})
                or soup.find("div", class_="article-body")
            )
            if body:
                paragraphs = [
                    p.get_text(" ", strip=True)
                    for p in body.find_all("p")
                    if len(p.get_text(strip=True)) > 25 and not _RE_DISCARD_STARTS.search(p.get_text(strip=True))
                ]
                content = " ".join(paragraphs[:6]).strip()
                if len(content) >= 30:
                    return content
        except Exception as e:
            logger.debug("The Hindu extraction failed: %s", e)
        return None
