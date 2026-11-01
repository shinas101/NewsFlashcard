"""
The Indian Express Scraper
- Website: indianexpress.com / ieonline
- Domain: India National, Regional (including IE Malayalam), and Opinion
"""
import json
import logging
from typing import Optional
from bs4 import BeautifulSoup

from .base import (
    BaseSiteScraper,
    _RE_AD_PROMO,
    _RE_DISCARD_STARTS,
)

logger = logging.getLogger("scrapers.indian_express")


class IndianExpressScraper(BaseSiteScraper):
    """Specialized scraper for The Indian Express (National & Malayalam) articles."""

    name = "The Indian Express"
    domains = ["indianexpress.com"]

    def can_handle(self, source: str, url: str) -> bool:
        src = (source or "").strip().lower()
        if "indian express" in src:
            return True
        return super().can_handle(source, url)

    def extract(self, soup: BeautifulSoup, url: str = "") -> Optional[str]:
        try:
            # 1. Prefer JSON-LD metadata
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

            # 2. Main article body container
            body = (
                soup.find(id="pcl-full-content")
                or soup.find("div", class_="heading-part")
                or soup.find("div", class_="story-details")
                or soup.find("div", class_="content-wrapper")
            )
            if body:
                paragraphs = []
                for p in body.find_all("p"):
                    classes = " ".join(p.get("class", [])) if isinstance(p.get("class"), list) else (p.get("class") or "")
                    if _RE_AD_PROMO.search(classes):
                        continue
                    text = p.get_text(" ", strip=True)
                    if len(text) > 25 and not _RE_DISCARD_STARTS.search(text):
                        paragraphs.append(text)

                content = " ".join(paragraphs[:6]).strip()
                if len(content) >= 30:
                    return content
        except Exception as e:
            logger.debug("Indian Express extraction failed: %s", e)
        return None

