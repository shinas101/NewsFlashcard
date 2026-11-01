"""
Manorama Online Scraper
- Website: manoramaonline.com
- Domain: Malayalam Regional & Kerala News
"""
import logging
from typing import Optional
from bs4 import BeautifulSoup

from .base import BaseSiteScraper

logger = logging.getLogger("scrapers.manorama")


class ManoramaScraper(BaseSiteScraper):
    """Specialized scraper for Manorama Online articles."""

    name = "Manorama Online"
    domains = ["manoramaonline.com"]

    def extract(self, soup: BeautifulSoup, url: str = "") -> Optional[str]:
        try:
            # Manorama editorial story paragraphs typically omit CSS class names
            paras = [
                p.get_text(" ", strip=True)
                for p in soup.find_all("p")
                if p.get_text(strip=True) and p.get("class") is None
            ]
            if paras:
                content = " ".join(paras[:6]).strip()
                if len(content) >= 30:
                    return content
        except Exception as e:
            logger.debug("Manorama extraction failed: %s", e)
        return None
