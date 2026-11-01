"""News scrapers package with dedicated website scraper modules."""
from .base import (
    BaseSiteScraper,
    fetch_page_html,
    clean_scraped_text,
    strip_unwanted_elements,
)
from .google_news import (
    decode_google_news_url,
    decode_url,
    get_decoding_params,
    get_base64_str,
    fetch_google_news_feed,
)
from .manorama import ManoramaScraper
from .mathrubhumi import MathrubhumiScraper
from .asianet import AsianetScraper
from .news18 import News18Scraper
from .madhyamam import MadhyamamScraper
from .the_hindu import TheHinduScraper
from .times_of_india import TimesOfIndiaScraper
from .ndtv import NDTVScraper
from .indian_express import IndianExpressScraper
from .generic import GenericScraper
from .news_scraper import (
    scrape_news,
    extract_article_content,
    SITE_SCRAPERS,
    GENERIC_SCRAPER,
)

__all__ = [
    # Core public functions
    "scrape_news",
    "extract_article_content",
    "decode_google_news_url",
    "decode_url",
    "get_decoding_params",
    "get_base64_str",
    "fetch_page_html",
    "fetch_google_news_feed",
    "clean_scraped_text",
    "strip_unwanted_elements",
    # Specific scrapers & classes
    "BaseSiteScraper",
    "ManoramaScraper",
    "MathrubhumiScraper",
    "AsianetScraper",
    "News18Scraper",
    "MadhyamamScraper",
    "TheHinduScraper",
    "TimesOfIndiaScraper",
    "NDTVScraper",
    "IndianExpressScraper",
    "GenericScraper",
    "SITE_SCRAPERS",
    "GENERIC_SCRAPER",
]
