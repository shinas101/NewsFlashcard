"""
Asianet News Scraper
- Website: asianetnews.com
- Domain: Malayalam Regional & Kerala News
"""
import logging
from typing import Optional
from bs4 import BeautifulSoup

from .base import BaseSiteScraper

logger = logging.getLogger("scrapers.asianet")


class AsianetScraper(BaseSiteScraper):
    """Specialized scraper for Asianet News articles."""

    name = "Asianet News Malayalam"
    domains = ["asianetnews.com"]

    def extract(self, soup: BeautifulSoup, url: str = "") -> Optional[str]:
        try:
            body = (
                soup.find("div", {"itemprop": "articleBody"})
                or soup.find("div", class_="article_content")
                or soup.find("div", class_="article-desc")
            )
            if body:
                paras = [p.get_text(" ", strip=True) for p in body.find_all("p")[:6]]
                content = " ".join(p for p in paras if len(p) > 15).strip()
                if len(content) >= 30:
                    return content
        except Exception as e:
            logger.debug("Asianet extraction failed: %s", e)
        return None
