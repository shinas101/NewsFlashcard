"""
Mathrubhumi Scraper
- Website: mathrubhumi.com
- Domain: Malayalam Regional & Kerala News
"""
import logging
from typing import Optional
from bs4 import BeautifulSoup

from .base import BaseSiteScraper, _RE_MALAYALAM_CHARS

logger = logging.getLogger("scrapers.mathrubhumi")


class MathrubhumiScraper(BaseSiteScraper):
    """Specialized scraper for Mathrubhumi articles."""

    name = "Mathrubhumi"
    domains = ["mathrubhumi.com"]

    def extract(self, soup: BeautifulSoup, url: str = "") -> Optional[str]:
        try:
            body = soup.find("div", {"class": "article-body"}) or soup.find("div", class_="story-content")
            if body:
                raw_text = body.get_text(" ", strip=True)
                cleaned = _RE_MALAYALAM_CHARS.sub("", raw_text)
                words = cleaned.split()[:80]
                if words:
                    content = " ".join(words).strip()
                    if len(content) >= 30:
                        return content
        except Exception as e:
            logger.debug("Mathrubhumi extraction failed: %s", e)
        return None

