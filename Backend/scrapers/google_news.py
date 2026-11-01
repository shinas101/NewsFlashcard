"""
Google News Scraper & Batchexecute URL Decoder
- Decodes obfuscated news.google.com redirection URLs to direct publisher canonical links.
- Fetches Google News RSS feeds for English and Malayalam.
"""
import json
import time
import logging
from typing import Optional, List, Dict, Any
from urllib.parse import quote, urlparse

from bs4 import BeautifulSoup
import feedparser

from .base import _session, HTMLParser

logger = logging.getLogger("scrapers.google_news")


def get_base64_str(source_url: str) -> dict:
    """Extract base64 article token from news.google.com URL."""
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
    """Fetch decoding signature and timestamp from Google News article page."""
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
    """Request batch execute endpoint to decode canonical publisher URL."""
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
            timeout=6,
        )
        response.raise_for_status()
        parsed_data = json.loads(response.text.split("\n\n")[1])[:-2]
        decoded_url = json.loads(parsed_data[0][2])[1]
        return {"status": True, "decoded_url": decoded_url}
    except Exception as e:
        logger.debug("decode_url error for %s: %s", base64_str, e)
        return {"status": False, "message": str(e)}


def decode_google_news_url(source_url: str, interval: Optional[int] = None) -> dict:
    """Decode Google News redirect URL to direct article target."""
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


def fetch_google_news_feed(lang: str = "en", limit: int = 25) -> List[Dict[str, Any]]:
    """Fetch raw Google News RSS entries for specified language."""
    if lang == "ml":
        rss_url = "https://news.google.com/rss?hl=ml&gl=IN&ceid=IN%3Aml"
    else:
        rss_url = "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en"

    logger.info("Fetching Google News RSS feed for %s (%s)", lang, rss_url)
    try:
        d = feedparser.parse(rss_url)
        entries = d.entries[:limit] if hasattr(d, "entries") else d.get("items", [])[:limit]
        logger.info("Retrieved %d RSS entries for %s", len(entries), lang)
        return entries
    except Exception as e:
        logger.error("Error parsing Google News RSS feed for %s: %s", lang, e)
        return []

