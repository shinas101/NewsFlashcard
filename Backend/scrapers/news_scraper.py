"""
High-Performance News Scraper & Decoder
- Parallel multi-threaded extraction of Indian National and Malayalam news.
- Thread-safe HTTP connection pooling (requests.Session + HTTPAdapter).
- Fast HTML parsing with selectolax/lxml fallback.
- Pre-compiled regex patterns for minimal CPU overhead.
"""
import json
import time
import re
import logging
from typing import Optional, List, Dict, Any
from urllib.parse import quote, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

import feedparser
from bs4 import BeautifulSoup
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import SCRAPER_MAX_WORKERS, SCRAPER_TIMEOUT

logger = logging.getLogger("scrapers.news")

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
    raise_on_status=False
)
_adapter = HTTPAdapter(
    pool_connections=SCRAPER_MAX_WORKERS * 2,
    pool_maxsize=SCRAPER_MAX_WORKERS * 4,
    max_retries=_retries
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
    re.I
)

_RE_AD_PROMO = re.compile(
    r"(ad|promo|social|author|caption|copyright|disclaimer)",
    re.I
)

_RE_DISCARD_STARTS = re.compile(
    r"^(also read|read also|click here|subscribe|advertisement|follow us|download the app|disclaimer:|copyright|photo:)",
    re.I
)

_RE_MALAYALAM_CHARS = re.compile(r"[^\u0D00-\u0D7F\s]")


def get_base64_str(source_url: str) -> dict:
    try:
        url = urlparse(source_url)
        path = url.path.split("/")
        if (
            url.hostname == "news.google.com"
            and len(path) > 1
            and path[-2] in ["articles", "read"]
        ):
            return {"status": True, "base64_str": path[-1]}
        return {"status": False, "message": "Invalid Google News URL format."}
    except Exception as e:
        logger.debug("get_base64_str error for %s: %s", source_url, e)
        return {"status": False, "message": f"Error in get_base64_str: {str(e)}"}


def get_decoding_params(base64_str: str) -> dict:
    try:
        url = f"https://news.google.com/articles/{base64_str}"
        response = _session.get(url, timeout=6)
        response.raise_for_status()

        if HTMLParser:
            parser = HTMLParser(response.text)
            data_element = parser.css_first("c-wiz > div[jscontroller]")
            if data_element is not None:
                return {
                    "status": True,
                    "signature": data_element.attributes.get("data-n-a-sg"),
                    "timestamp": data_element.attributes.get("data-n-a-ts"),
                    "base64_str": base64_str,
                }
        else:
            soup = BeautifulSoup(response.text, "html.parser")
            data_div = soup.select_one("c-wiz > div[jscontroller]")
            if data_div is not None:
                return {
                    "status": True,
                    "signature": data_div.get("data-n-a-sg"),
                    "timestamp": data_div.get("data-n-a-ts"),
                    "base64_str": base64_str,
                }

        # Fallback to RSS articles URL
        url_rss = f"https://news.google.com/rss/articles/{base64_str}"
        response_rss = _session.get(url_rss, timeout=6)
        response_rss.raise_for_status()

        if HTMLParser:
            parser = HTMLParser(response_rss.text)
            data_element = parser.css_first("c-wiz > div[jscontroller]")
            if data_element is not None:
                return {
                    "status": True,
                    "signature": data_element.attributes.get("data-n-a-sg"),
                    "timestamp": data_element.attributes.get("data-n-a-ts"),
                    "base64_str": base64_str,
                }
        else:
            soup = BeautifulSoup(response_rss.text, "html.parser")
            data_div = soup.select_one("c-wiz > div[jscontroller]")
            if data_div is not None:
                return {
                    "status": True,
                    "signature": data_div.get("data-n-a-sg"),
                    "timestamp": data_div.get("data-n-a-ts"),
                    "base64_str": base64_str,
                }

        return {
            "status": False,
            "message": "Failed to fetch data attributes from Google News.",
        }
    except Exception as e:
        logger.debug("get_decoding_params failed for %s: %s", base64_str, e)
        return {"status": False, "message": str(e)}


def decode_url(signature: str, timestamp: str, base64_str: str) -> dict:
    try:
        url = "https://news.google.com/_/DotsSplashUi/data/batchexecute"
        payload = [
            "Fbv4je",
            f'["garturlreq",[["X","X",["X","X"],null,null,1,1,"US:en",null,1,null,null,null,null,null,0,1],"X","X",1,[1,1,1],1,1,null,0,0,null,0],"{base64_str}",{timestamp},"{signature}"]',
        ]
        headers = {
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        }
        response = _session.post(
            url,
            headers=headers,
            data=f"f.req={quote(json.dumps([[payload]]))}",
            timeout=6
        )
        response.raise_for_status()
        parsed_data = json.loads(response.text.split("\n\n")[1])[:-2]
        decoded_url = json.loads(parsed_data[0][2])[1]
        return {"status": True, "decoded_url": decoded_url}
    except Exception as e:
        logger.debug("decode_url error for %s: %s", base64_str, e)
        return {"status": False, "message": str(e)}


def decode_google_news_url(source_url: str, interval: Optional[int] = None) -> dict:
    try:
        base64_response = get_base64_str(source_url)
        if not base64_response.get("status"):
            return base64_response

        decoding_params_response = get_decoding_params(base64_response["base64_str"])
        if not decoding_params_response.get("status"):
            return decoding_params_response

        decoded_url_response = decode_url(
            decoding_params_response["signature"],
            decoding_params_response["timestamp"],
            decoding_params_response["base64_str"],
        )
        if interval:
            time.sleep(interval)
        return decoded_url_response
    except Exception as e:
        logger.debug("Failed decoding Google News URL (%s): %s", source_url, e)
        return {"status": False, "message": str(e)}


def extract_article_content(url: str, source: str = "") -> str:
    """
    Dynamic article extractor with specialized handling for Malayalam and national Indian media.
    """
    if not url or not url.startswith("http"):
        return ""

    try:
        html = fetch_page_html(url, timeout=SCRAPER_TIMEOUT)
        if not html:
            return ""

        soup = BeautifulSoup(html, "lxml")

        # Prefer structured description from JSON-LD if available (e.g. The Hindu, Indian Express)
        description = None
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string or '')
                candidates = data if isinstance(data, list) else [data]
                for entry in candidates:
                    if entry.get('@type') in ('NewsArticle', 'Article') and entry.get('description'):
                        description = entry['description']
                        break
                if description:
                    break
            except Exception:
                continue

        if description:
            return description.strip()

        # Strip non-editorial elements
        for unwanted in soup(["script", "style", "nav", "header", "footer", "aside", "figure", "noscript", "form", "button", "svg", "iframe"]):
            unwanted.decompose()

        # Specific Malayalam Portal Handlers
        if source == "Manorama Online":
            paras = [p.get_text(" ", strip=True) for p in soup.find_all("p") if p.get_text(strip=True) and p.get("class") is None]
            if paras:
                return " ".join(paras[:6])
        elif source == "Mathrubhumi":
            body = soup.find("div", {"class": "article-body"})
            if body:
                return " ".join(_RE_MALAYALAM_CHARS.sub("", body.get_text(" ", strip=True)).split()[:80])
        elif source == "Asianet News Malayalam":
            body = soup.find("div", {"itemprop": "articleBody"})
            if body:
                return " ".join(p.get_text(" ", strip=True) for p in body.find_all("p")[:6])
        elif source == "News18 Malayalam":
            body = soup.find("div", {"class": "normal"})
            if body:
                return " ".join(_RE_MALAYALAM_CHARS.sub("", body.get_text(" ", strip=True)).split()[:80])
        elif source == "Madhyamam":
            body = soup.find("div", {"class": "story"})
            if body:
                return " ".join(_RE_MALAYALAM_CHARS.sub("", body.get_text(" ", strip=True)).split()[:80])

        # Dynamic containers for Indian & general news
        container = (
            soup.find("div", {"itemprop": "articleBody"}) or
            soup.find(id="ins_storybody") or
            soup.find("div", class_="ins_storybody") or
            soup.find("article") or
            soup.find("div", class_=_RE_CONTAINER_CLASSES) or
            soup.find("main") or
            soup
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

        # Meta description fallback
        if len(content) < 40:
            meta = soup.find("meta", {"property": "og:description"}) or soup.find("meta", {"name": "description"})
            if meta and meta.get("content"):
                content = meta["content"].strip()

        return content
    except Exception as e:
        logger.debug("Failed extracting content from %s: %s", url, e)
        return ""


def scrape_news(lang: str = "en", limit: int = 25) -> List[Dict[str, str]]:
    """
    Scrapes major headlines from Google News (India English or Malayalam).
    Extracts article content dynamically across news portals in parallel.
    """
    start_time = time.time()
    news_data = []

    if lang == "ml":
        rss_url = "https://news.google.com/rss?hl=ml&gl=IN&ceid=IN%3Aml"
    else:
        rss_url = "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en"

    logger.info("Fetching RSS feed for language: %s (%s)", lang, rss_url)
    try:
        d = feedparser.parse(rss_url)
        entries = d.entries[:limit] if hasattr(d, "entries") else d.get("items", [])[:limit]
        logger.info("Retrieved %d RSS entries for %s", len(entries), lang)
    except Exception as e:
        logger.error("Error parsing Google News RSS feed for %s: %s", lang, e)
        return []

    def _process_entry(item: Dict[str, Any]) -> Optional[Dict[str, str]]:
        raw_title = item.get("title", "")
        parts = raw_title.rsplit("-", 1)
        title = parts[0].strip() if len(parts) > 1 else raw_title.strip()
        source = parts[-1].strip() if len(parts) > 1 else ("Malayalam News" if lang == "ml" else "India News")

        raw_link = item.get("link", "")
        try:
            decoded = decode_google_news_url(raw_link)
            link = decoded.get("decoded_url", raw_link) if decoded.get("status") else raw_link
        except Exception:
            link = raw_link

        description = extract_article_content(link, source=source)

        def _clean_desc(txt: str) -> str:
            if not txt:
                return txt
            cleaned = _RE_GARBAGE.sub("", txt).strip()
            return cleaned if len(cleaned) >= 30 else ""

        description = _clean_desc(description)

        if not description:
            rss_summary = item.get("summary", "")
            if rss_summary:
                clean_rss = BeautifulSoup(rss_summary, "html.parser").get_text(" ", strip=True)
                if len(clean_rss) > 20:
                    description = clean_rss

        return {
            "title": title,
            "link": link,
            "source": source,
            "description": description
        }

    with ThreadPoolExecutor(max_workers=SCRAPER_MAX_WORKERS, thread_name_prefix=f"scraper-{lang}") as executor:
        futures = [executor.submit(_process_entry, entry) for entry in entries]
        for f in as_completed(futures):
            try:
                res = f.result()
                if res and res.get("title"):
                    news_data.append(res)
            except Exception as e:
                logger.warning("Error scraping entry: %s", e)

    elapsed = time.time() - start_time
    logger.info("Successfully scraped %d %s news articles in %.2fs", len(news_data), lang, elapsed)
    return news_data

