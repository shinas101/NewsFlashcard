"""
Local T5 Abstractive News Summarizer & Malayalam Extractive Pipeline
- google-t5/t5-small seq2seq transformer model for high-speed English summarization.
- Zero-token, local-only processing: 100% offline-capable, runs on CPU.
- Thread-safe singleton model initialization.
- Dynamic caching of individual article summaries in Redis.
"""
import os
import re
import time
import threading
import logging
from typing import List, Dict, Any, Tuple, Optional

# Ensure Hugging Face cache uses secondary disk if present
if os.path.exists("D:\\"):
    CACHE_DIR = "D:/huggingface_cache"
else:
    CACHE_DIR = os.path.expanduser("~/.cache/huggingface")

os.environ.setdefault("HF_HOME", CACHE_DIR)

from cache_utils import cache_get, cache_set, generate_news_hash
from summarizer import extract_summary
from config import T5_MODEL_ID, T5_BATCH_SIZE, CACHE_LONG_TTL

logger = logging.getLogger("t5_summarizer")

_MODEL = None
_TOKENIZER = None
_MODEL_LOCK = threading.Lock()

# Pre-compiled regular expressions for tag stripping and language checks
_RE_MALAYALAM = re.compile(r'[\u0D00-\u0D7F]')
_RE_DATELINE = re.compile(r'^[A-Z\s]{2,16}\s*[:–—-]\s*')
_RE_AGENCY = re.compile(r'^(?:PTI|ANI|IANS|Reuters|Bloomberg|AFP)\s*[:–—-]\s*', flags=re.I)
_RE_LIVE = re.compile(r'^(?:Follow\s+)?L[IV]{1,2}E\s+(?:updates\s+)?(?:as\s+)?[:\-]?\s*', flags=re.I)
_RE_READ_MORE = re.compile(r'Read\s+more\s+at\s+.*$', flags=re.I)
_RE_TRAILING_PREP = re.compile(r'\s*\b(on|in|at|by|from|with|to|and|or)\s*$', flags=re.I)


def get_model_and_tokenizer() -> Tuple[Optional[Any], Optional[Any]]:
    """Thread-safe double-checked singleton initialization for T5 model & tokenizer."""
    global _MODEL, _TOKENIZER
    if _MODEL is not None and _TOKENIZER is not None:
        return _MODEL, _TOKENIZER

    with _MODEL_LOCK:
        if _MODEL is None or _TOKENIZER is None:
            try:
                import torch
                from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

                # Constrain PyTorch thread contention on memory-limited CPU dynos
                torch.set_num_threads(1)
                try:
                    torch.set_num_interop_threads(1)
                except Exception:
                    pass

                start_t = time.time()
                logger.info("Loading local T5 model '%s' from %s...", T5_MODEL_ID, CACHE_DIR)
                _TOKENIZER = AutoTokenizer.from_pretrained(T5_MODEL_ID, cache_dir=CACHE_DIR)
                _MODEL = AutoModelForSeq2SeqLM.from_pretrained(T5_MODEL_ID, cache_dir=CACHE_DIR)
                _MODEL.eval()
                elapsed = time.time() - start_t
                logger.info("Local T5 model loaded successfully in %.2fs.", elapsed)
            except Exception as e:
                logger.error("Failed to load local T5 model (%s): %s", T5_MODEL_ID, e)
                return None, None

    return _MODEL, _TOKENIZER


def is_malayalam(text: str) -> bool:
    """Checks if text contains Malayalam unicode characters."""
    if not text:
        return False
    return bool(_RE_MALAYALAM.search(text))


def clean_agency_tags(text: str) -> str:
    """Removes city datelines, news agency abbreviations, and live update tickers."""
    if not text:
        return ""
    t = text.strip()
    t = _RE_DATELINE.sub('', t)
    t = _RE_AGENCY.sub('', t)
    t = _RE_LIVE.sub('', t)
    t = _RE_READ_MORE.sub('', t)
    t = _RE_TRAILING_PREP.sub('.', t)
    return t.strip()


def t5_summarize_batch(texts: List[str], max_tokens: int = 65, min_tokens: int = 20) -> List[str]:
    """Generates abstractive summaries using google-t5/t5-small."""
    if not texts:
        return []

    model, tokenizer = get_model_and_tokenizer()
    if not model or not tokenizer:
        logger.warning("T5 model not available, falling back to prefix truncation.")
        return [clean_agency_tags(t[:250]) for t in texts]

    import torch

    prompts = [f"summarize: {clean_agency_tags(t)[:500]}" for t in texts]
    try:
        t0 = time.time()
        inputs = tokenizer(
            prompts,
            max_length=512,
            truncation=True,
            padding=True,
            return_tensors="pt"
        )
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                min_length=min_tokens,
                no_repeat_ngram_size=2,
                num_beams=2,
                early_stopping=True
            )
        raw_summaries = tokenizer.batch_decode(outputs, skip_special_tokens=True)
        cleaned_summaries = []
        for s in raw_summaries:
            s_clean = clean_agency_tags(s).capitalize()
            if s_clean and not s_clean.endswith((".", "!", "?")):
                s_clean += "."
            cleaned_summaries.append(s_clean)

        logger.debug("T5 batch summarized %d items in %.2fs", len(texts), time.time() - t0)
        return cleaned_summaries
    except Exception as e:
        logger.error("Error during local T5 batch summarization: %s", e)
        return [clean_agency_tags(t[:250]) for t in texts]


def summarize_with_t5(
    news_data: List[Dict[str, Any]],
    lang: str = "en",
    batch_size: int = T5_BATCH_SIZE
) -> List[Dict[str, str]]:
    """
    Standard news summarization pipeline:
    - google-t5/t5-small for English news.
    - Local extractive Luhn summarizer for Malayalam news.
    - Redis cached. Zero external API calls.
    """
    if not news_data:
        return []

    pipeline_start = time.time()
    results = []
    t5_candidates: List[str] = []
    t5_indices: List[int] = []

    cached_count = 0

    for i, item in enumerate(news_data):
        title = item.get("title", "")
        body = item.get("description", "").strip() or title
        item_hash = generate_news_hash(title + body)
        cache_key = f"summary:t5:norm:{lang}:{item_hash}"

        cached = cache_get(cache_key)
        if cached and isinstance(cached, str):
            results.append({"title": title, "summary": cached})
            cached_count += 1
        else:
            results.append({"title": title, "summary": ""})
            if lang == "ml" or is_malayalam(body) or is_malayalam(title):
                # Malayalam extractive summary
                summary = extract_summary(body, title=title)
                summary = clean_agency_tags(summary)
                if summary and not summary.endswith((".", "!", "?")):
                    summary += "."
                results[i]["summary"] = summary
                cache_set(cache_key, summary, ttl=CACHE_LONG_TTL)
            else:
                # English local T5 candidate
                clean_body = clean_agency_tags(body)
                clean_title = clean_agency_tags(title)
                input_text = f"{clean_title}. {clean_body}" if len(clean_body) < 180 else clean_body
                t5_candidates.append(input_text)
                t5_indices.append(i)

    logger.info(
        "Summarization cache: %d hit(s), %d new item(s) to process (%d T5 candidates).",
        cached_count, len(news_data) - cached_count, len(t5_candidates)
    )

    # Process T5 candidates in mini-batches
    if t5_candidates:
        model, _ = get_model_and_tokenizer()
        if model:
            for b in range(0, len(t5_candidates), batch_size):
                batch_texts = t5_candidates[b:b + batch_size]
                batch_summaries = t5_summarize_batch(batch_texts)
                for sub_i, t5_summary in enumerate(batch_summaries):
                    orig_idx = t5_indices[b + sub_i]
                    item = news_data[orig_idx]
                    title = item.get("title", "")
                    body = item.get("description", "").strip() or title

                    summary = t5_summary
                    if not summary or len(summary) < 25:
                        summary = extract_summary(body, title=title)
                        summary = clean_agency_tags(summary)

                    if summary and not summary.endswith((".", "!", "?")):
                        summary += "."

                    results[orig_idx]["summary"] = summary

                    item_hash = generate_news_hash(title + body)
                    cache_key = f"summary:t5:norm:{lang}:{item_hash}"
                    cache_set(cache_key, summary, ttl=CACHE_LONG_TTL)
        else:
            # Extractive fallback if PyTorch or weights could not be loaded
            logger.warning("Falling back to extractive summarizer for English news.")
            for orig_idx in t5_indices:
                item = news_data[orig_idx]
                title = item.get("title", "")
                body = item.get("description", "").strip() or title
                summary = extract_summary(body, title=title)
                results[orig_idx]["summary"] = clean_agency_tags(summary)

    # Fallback sanity check: guarantee no empty summary survives
    for i, item in enumerate(news_data):
        if not results[i]["summary"]:
            results[i]["summary"] = clean_agency_tags(extract_summary(
                item.get("description", "").strip() or item.get("title", ""),
                title=item.get("title", "")
            ))

    total_elapsed = time.time() - pipeline_start
    logger.info("Summarization pipeline completed for %d articles in %.2fs.", len(news_data), total_elapsed)
    return results
