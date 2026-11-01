"""
NDTV Scraper
- Website: ndtv.com
- Domain: India National, Business, and World News
"""
import logging
from typing import Optional
from bs4 import BeautifulSoup

from .base import (
    BaseSiteScraper,
    _RE_AD_PROMO,
    _RE_DISCARD_STARTS,
)

logger = logging.getLogger("scrapers.ndtv")


class NDTVScraper(BaseSiteScraper):
    """Specialized scraper for NDTV news articles."""

    name = "NDTV"
    domains = ["ndtv.com"]

    def extract(self, soup: BeautifulSoup, url: str = "") -> Optional[str]:
        try:
            body = (
                soup.find(id="ins_storybody")
                or soup.find("div", class_="ins_storybody")
                or soup.find("div", class_="story__content")
                or soup.find("div", class_="sp-cn")
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
            logger.debug("NDTV extraction failed: %s", e)
        return None

