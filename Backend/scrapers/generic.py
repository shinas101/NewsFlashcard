"""
Generic & Multi-Source News Scraper Fallback
- Extracts editorial content for Indian and international news portals (The Hindu, Indian Express, NDTV, Times of India, etc.).
- Leverages JSON-LD structured metadata, semantic HTML5 containers, and meta descriptions.
"""
import json
import logging
from typing import Optional
from bs4 import BeautifulSoup

from .base import (
    BaseSiteScraper,
    _RE_CONTAINER_CLASSES,
    _RE_AD_PROMO,
    _RE_DISCARD_STARTS,
)

logger = logging.getLogger("scrapers.generic")


class GenericScraper(BaseSiteScraper):
    """Fallback scraper utilizing JSON-LD metadata, article body containers, and OpenGraph descriptions."""

    name = "Generic Media"
    domains = []  # Catch-all

    def extract(self, soup: BeautifulSoup, url: str = "") -> Optional[str]:
        try:
            # 1. Prefer structured JSON-LD description (e.g., The Hindu, Indian Express)
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

            # 2. Inspect standard editorial containers
            container = (
                soup.find("div", {"itemprop": "articleBody"})
                or soup.find(id="ins_storybody")
                or soup.find("div", class_="ins_storybody")
                or soup.find("article")
                or soup.find("div", class_=_RE_CONTAINER_CLASSES)
                or soup.find("main")
                or soup
            )

            paragraphs = []
            for p in container.find_all("p"):
                classes = " ".join(p.get("class", [])) if isinstance(p.get("class"), list) else (p.get("class") or "")
                if _RE_AD_PROMO.search(classes):
                    continue

                text = p.get_text(" ", strip=True)
                if len(text) > 25 and not _RE_DISCARD_STARTS.search(text):
                    paragraphs.append(text)

            content = " ".join(paragraphs[:6]).strip()

            # 3. Fallback to OpenGraph or meta description if extracted body is too brief
            if len(content) < 40:
                meta = (
                    soup.find("meta", {"property": "og:description"})
                    or soup.find("meta", {"name": "description"})
                )
                if meta and meta.get("content"):
                    meta_text = meta["content"].strip()
                    if len(meta_text) > len(content):
                        content = meta_text

            return content if len(content) >= 30 else None
        except Exception as e:
            logger.debug("Generic extraction failed: %s", e)
            return None

