"""
Base Scraper Infrastructure & Shared Utilities
- Thread-safe HTTP connection pooling (requests.Session + HTTPAdapter).
- Fast HTML parser selection (selectolax / BeautifulSoup).
- Pre-compiled regex patterns for ad stripping, container detection, and text cleaning.
- Base site scraper interface.
"""
import re
import logging
from abc import ABC, abstractmethod
from typing import Optional, List
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup

from config import SCRAPER_MAX_WORKERS, SCRAPER_TIMEOUT

logger = logging.getLogger("scrapers.base")

# Try fast HTML parser selectolax
try:
    from selectolax.lexbor import LexborHTMLParser as HTMLParser
except ImportError:
    try:
        from selectolax.parser import HTMLParser
    except ImportError:
        HTMLParser = None

# Configure reusable, thread-safe connection-pooled session
_session = requests.Session()
_retries = Retry(
    total=2,
    backoff_factor=0.3,
    status_forcelist=[500, 502, 503, 504],
    raise_on_status=False,
)
_adapter = HTTPAdapter(
    pool_connections=SCRAPER_MAX_WORKERS * 2,
    pool_maxsize=SCRAPER_MAX_WORKERS * 4,
    max_retries=_retries,
)
_session.mount("https://", _adapter)
_session.mount("http://", _adapter)

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
)
_session.headers.update({"User-Agent": DEFAULT_USER_AGENT})

# Curl-cffi optional bypass for advanced anti-bot protections
try:
    from curl_cffi import requests as cffi_requests

    def fetch_page_html(url: str, timeout: int = SCRAPER_TIMEOUT) -> str:
        return cffi_requests.get(url, impersonate="chrome120", timeout=timeout).text
except ImportError:
    def fetch_page_html(url: str, timeout: int = SCRAPER_TIMEOUT) -> str:
        res = _session.get(url, timeout=timeout)
        return res.text


# Pre-compiled regex constants
_RE_GARBAGE = re.compile(
    r"(please enable js|disable any ad.?blocker"
    r"|you don.t have any active subscription|account subscription benefits"
    r"|share your thoughts in the comments|be respectful.*?community guidelines"
    r"|toi community guidelines|unlock these with subscription"
    r"|need help with your subscription)",
    re.I | re.DOTALL,
)

_RE_CONTAINER_CLASSES = re.compile(
    r"(article-body|story-body|article__body|story__content|story_details|entry-content|normal|main-content)",
    re.I,
)

_RE_AD_PROMO = re.compile(
    r"(ad|promo|social|author|caption|copyright|disclaimer)",
    re.I,
)

_RE_DISCARD_STARTS = re.compile(
    r"^(also read|read also|click here|subscribe|advertisement|follow us|download the app|disclaimer:|copyright|photo:)",
    re.I,
)

_RE_MALAYALAM_CHARS = re.compile(r"[^\u0D00-\u0D7F\s]")


def clean_scraped_text(txt: str) -> str:
    """Strip garbage, promotional notices, and subscription banners."""
    if not txt:
        return ""
    cleaned = _RE_GARBAGE.sub("", txt).strip()
    return cleaned if len(cleaned) >= 30 else ""


def strip_unwanted_elements(soup: BeautifulSoup) -> None:
    """Decompose non-editorial DOM nodes from BeautifulSoup tree."""
    for unwanted in soup(
        ["script", "style", "nav", "header", "footer", "aside", "figure", "noscript", "form", "button", "svg", "iframe"]
    ):
        unwanted.decompose()


class BaseSiteScraper(ABC):
    """Abstract base class for website-specific scrapers."""

    name: str = "BaseScraper"
    domains: List[str] = []

    def can_handle(self, source: str, url: str) -> bool:
        """Determines if this scraper specializes in the given news source or URL domain."""
        if source and source.strip().lower() == self.name.lower():
            return True
        if url and self.domains:
            parsed = urlparse(url)
            host = (parsed.hostname or "").lower()
            return any(d in host for d in self.domains)
        return False

    @abstractmethod
    def extract(self, soup: BeautifulSoup, url: str = "") -> Optional[str]:
        """Extract main article body from the parsed HTML tree."""
        raise NotImplementedError
