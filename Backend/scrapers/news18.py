"""
News18 Malayalam Scraper
- Website: news18.com / malayalam.news18.com
- Domain: Malayalam Regional & Kerala News
"""
import logging
from typing import Optional
from bs4 import BeautifulSoup

from .base import BaseSiteScraper, _RE_MALAYALAM_CHARS

logger = logging.getLogger("scrapers.news18")


class News18Scraper(BaseSiteScraper):
    """Specialized scraper for News18 Malayalam articles."""

    name = "News18 Malayalam"
    domains = ["malayalam.news18.com", "news18.com"]

    def extract(self, soup: BeautifulSoup, url: str = "") -> Optional[str]:
        try:
            body = (
                soup.find("div", {"class": "normal"})
                or soup.find("article", class_="article-content")
                or soup.find("div", class_="articlebody")
            )
            if body:
                raw_text = body.get_text(" ", strip=True)
                cleaned = _RE_MALAYALAM_CHARS.sub("", raw_text)
                words = cleaned.split()[:80]
                if words:
                    content = " ".join(words).strip()
                    if len(content) >= 30:
                        return content
        except Exception as e:
            logger.debug("News18 extraction failed: %s", e)
        return None

