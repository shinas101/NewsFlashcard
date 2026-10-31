"""News scrapers package."""
from .news_scraper import (
    scrape_news,
    extract_article_content,
    decode_google_news_url,
    decode_url,
    get_decoding_params,
    get_base64_str,
    fetch_page_html,
)

__all__ = [
    "scrape_news",
    "extract_article_content",
    "decode_google_news_url",
    "decode_url",
    "get_decoding_params",
    "get_base64_str",
    "fetch_page_html",
]
