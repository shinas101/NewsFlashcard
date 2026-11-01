"""
The Times of India Scraper
- Website: timesofindia.indiatimes.com
- Domain: India National, City, and World News
"""
import logging
from typing import Optional
from bs4 import BeautifulSoup

from .base import (
    BaseSiteScraper,
    _RE_AD_PROMO,
    _RE_DISCARD_STARTS,
    _RE_GARBAGE,
)

logger = logging.getLogger("scrapers.times_of_india")


class TimesOfIndiaScraper(BaseSiteScraper):
    """Specialized scraper for The Times of India articles."""

    name = "The Times of India"
    domains = ["timesofindia.indiatimes.com", "indiatimes.com"]

    def extract(self, soup: BeautifulSoup, url: str = "") -> Optional[str]:
        try:
            # TOI editorial container classes
            body = (
                soup.find("div", class_="_s30J")
                or soup.find("div", class_="artText")
                or soup.find("div", attrs={"data-articlebody": True})
                or soup.find("div", class_="article-content")
                or soup.find("div", class_="main-content")
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
            logger.debug("Times of India extraction failed: %s", e)
        return None
