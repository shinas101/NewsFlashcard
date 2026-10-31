import json
import time
import re
from typing import Optional
from urllib.parse import quote, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import feedparser
from bs4 import BeautifulSoup
import requests

try:
    from selectolax.lexbor import LexborHTMLParser as HTMLParser
except ImportError:
    from selectolax.parser import HTMLParser

try:
    from curl_cffi import requests as cffi_requests
    def fetch_page_html(url: str, timeout: int = 10) -> str:
        return cffi_requests.get(url, impersonate="chrome120", timeout=timeout).text
except ImportError:
    def fetch_page_html(url: str, timeout: int = 10) -> str:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
        }
        return requests.get(url, headers=headers, timeout=timeout).text


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
        return {"status": False, "message": f"Error in get_base64_str: {str(e)}"}


def get_decoding_params(base64_str: str) -> dict:
    try:
        url = f"https://news.google.com/articles/{base64_str}"
        response = requests.get(url)
        response.raise_for_status()

        parser = HTMLParser(response.text)
        data_element = parser.css_first("c-wiz > div[jscontroller]")
        if data_element is None:
            return {
                "status": False,
                "message": "Failed to fetch data attributes from Google News with the articles URL.",
            }

        return {
            "status": True,
            "signature": data_element.attributes.get("data-n-a-sg"),
            "timestamp": data_element.attributes.get("data-n-a-ts"),
            "base64_str": base64_str,
        }
    except requests.exceptions.RequestException:
        try:
            url = f"https://news.google.com/rss/articles/{base64_str}"
            response = requests.get(url)
            response.raise_for_status()

            parser = HTMLParser(response.text)
            data_element = parser.css_first("c-wiz > div[jscontroller]")
            if data_element is None:
                return {
                    "status": False,
                    "message": "Failed to fetch data attributes from Google News with the RSS URL.",
                }

            return {
                "status": True,
                "signature": data_element.attributes.get("data-n-a-sg"),
                "timestamp": data_element.attributes.get("data-n-a-ts"),
                "base64_str": base64_str,
            }
        except Exception as rss_err:
            return {"status": False, "message": str(rss_err)}
    except Exception as e:
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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
        }
        response = requests.post(url, headers=headers, data=f"f.req={quote(json.dumps([[payload]]))}")
        response.raise_for_status()
        parsed_data = json.loads(response.text.split("\n\n")[1])[:-2]
        decoded_url = json.loads(parsed_data[0][2])[1]
        return {"status": True, "decoded_url": decoded_url}
    except Exception as e:
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
        return {"status": False, "message": str(e)}


def extract_article_content(url: str, source: str = "") -> str:
    """
    Dynamic article extractor with specialized handling for Malayalam and national Indian media.
    """
    if not url or not url.startswith("http"):
        return ""

    try:
        html = fetch_page_html(url, timeout=10)
        if not html:
            return ""

        soup = BeautifulSoup(html, "lxml")

        # Prefer structured description from JSON‑LD if available (e.g., The Hindu)
        description = None
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string or '')
                # data may be a list or dict
                if isinstance(data, list):
                    candidates = data
                else:
                    candidates = [data]
                for entry in candidates:
                    if entry.get('@type') == 'NewsArticle' and entry.get('description'):
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

        # Specific Malayalam ... (rest unchanged)
        if source == "Manorama Online":
            paras = [p.get_text(" ", strip=True) for p in soup.find_all("p") if p.get_text(strip=True) and p.get("class") is None]
            if paras:
                return " ".join(paras[:6])
        elif source == "Mathrubhumi":
            body = soup.find("div", {"class": "article-body"})
            if body:
                return " ".join(re.sub(r"[^\u0D00-\u0D7F\s]", "", body.get_text(" ", strip=True)).split()[:80])
        elif source == "Asianet News Malayalam":
            body = soup.find("div", {"itemprop": "articleBody"})
            if body:
                return " ".join(p.get_text(" ", strip=True) for p in body.find_all("p")[:6])
        elif source == "News18 Malayalam":
            body = soup.find("div", {"class": "normal"})
            if body:
                return " ".join(re.sub(r"[^\u0D00-\u0D7F\s]", "", body.get_text(" ", strip=True)).split()[:80])
        elif source == "Madhyamam":
            body = soup.find("div", {"class": "story"})
            if body:
                return " ".join(re.sub(r"[^\u0D00-\u0D7F\s]", "", body.get_text(" ", strip=True)).split()[:80])

        # Dynamic containers for Indian & general news
        container = (
            soup.find("div", {"itemprop": "articleBody"}) or
            soup.find(id="ins_storybody") or
            soup.find("div", class_="ins_storybody") or
            soup.find("article") or
            soup.find("div", class_=re.compile(r"(article-body|story-body|article__body|story__content|story_details|entry-content|normal|main-content)", re.I)) or
            soup.find("main") or
            soup
        )

        paragraphs = []
        for p in container.find_all("p"):
            classes = " ".join(p.get("class", [])) if isinstance(p.get("class"), list) else (p.get("class") or "")
            if re.search(r"(ad|promo|social|author|caption|copyright|disclaimer)", classes, re.I):
                continue

            text = p.get_text(" ", strip=True)
            if len(text) > 25 and not re.search(r"^(also read|read also|click here|subscribe|advertisement|follow us|download the app|disclaimer:|copyright|photo:)", text, re.I):
                paragraphs.append(text)

        content = " ".join(paragraphs[:6]).strip()

        # Meta description fallback
        if len(content) < 40:
            meta = soup.find("meta", {"property": "og:description"}) or soup.find("meta", {"name": "description"})
            if meta and meta.get("content"):
                content = meta["content"].strip()

        return content
    except Exception:
        return ""


def scrape_news(lang: str = "en", limit: int = 25):
    """
    Scrapes major headlines from Google News (India English or Malayalam).
    Extracts article content dynamically across news portals in parallel.
    """
    news_data = []
    if lang == "ml":
        rss_url = "https://news.google.com/rss?hl=ml&gl=IN&ceid=IN%3Aml"
    else:
        rss_url = "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en"

    d = feedparser.parse(rss_url)
    entries = d.entries[:limit] if hasattr(d, "entries") else d.get("items", [])[:limit]

    def _process_entry(item):
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

        # Strip known anti-scraper / paywall placeholder text → fall back to RSS
        _GARBAGE = re.compile(
            r"(please enable js|disable any ad.?blocker"
            r"|you don.t have any active subscription|account subscription benefits"
            r"|share your thoughts in the comments|be respectful.*?community guidelines"
            r"|toi community guidelines|unlock these with subscription"
            r"|need help with your subscription)",
            re.I | re.DOTALL,
        )

        def _clean_desc(txt: str) -> str:
            if not txt:
                return txt
            cleaned = _GARBAGE.sub("", txt).strip()
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

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(_process_entry, entry) for entry in entries]
        for f in as_completed(futures):
            try:
                res = f.result()
                if res and res.get("title"):
                    news_data.append(res)
            except Exception as e:
                print(f"Error scraping entry: {e}")

    print(f"Successfully scraped {len(news_data)} {lang} news articles.")
    return news_data
