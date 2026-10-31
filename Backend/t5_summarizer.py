import os
import re
import logging
from typing import List, Dict, Any

# Ensure Hugging Face cache uses D: if available to save C: drive space
if os.path.exists("D:\\"):
    CACHE_DIR = "D:/huggingface_cache"
else:
    CACHE_DIR = os.path.expanduser("~/.cache/huggingface")

os.environ.setdefault("HF_HOME", CACHE_DIR)

from cache_utils import cache_get, cache_set, generate_news_hash
from summarizer import extract_summary

logger = logging.getLogger("t5_summarizer")

_MODEL = None
_TOKENIZER = None


def get_model_and_tokenizer():
    global _MODEL, _TOKENIZER
    if _MODEL is None or _TOKENIZER is None:
        try:
            import torch
            from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

            model_id = "google-t5/t5-small"
            logger.info(f"Loading local T5 model {model_id} from {CACHE_DIR}...")
            _TOKENIZER = AutoTokenizer.from_pretrained(model_id, cache_dir=CACHE_DIR)
            _MODEL = AutoModelForSeq2SeqLM.from_pretrained(model_id, cache_dir=CACHE_DIR)
            _MODEL.eval()
            logger.info("Local T5 model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load local T5 model: {e}")
            return None, None
    return _MODEL, _TOKENIZER


def is_malayalam(text: str) -> bool:
    """Checks if text contains Malayalam characters."""
    return bool(re.search(r'[\u0D00-\u0D7F]', text))


def clean_agency_tags(text: str) -> str:
    """Removes city datelines, news agency abbreviations, and live update tickers."""
    if not text:
        return ""
    t = text.strip()
    # Strip leading city/datelines like "BENGALURU:", "NEW DELHI --"
    t = re.sub(r'^[A-Z\s]{2,16}\s*[:–—-]\s*', '', t)
    # Strip news agency tags
    t = re.sub(r'^(?:PTI|ANI|IANS|Reuters|Bloomberg|AFP)\s*[:–—-]\s*', '', t, flags=re.I)
    # Strip "Follow LIVE updates as..."
    t = re.sub(r'^(?:Follow\s+)?L[IV]{1,2}E\s+(?:updates\s+)?(?:as\s+)?[:\-]?\s*', '', t, flags=re.I)
    # Strip "Read more at..."
    t = re.sub(r'Read\s+more\s+at\s+.*$', '', t, flags=re.I)
    # Strip trailing broken prepositions
    t = re.sub(r'\s*\b(on|in|at|by|from|with|to|and|or)\s*$', '.', t)
    return t.strip()


def t5_summarize_batch(texts: List[str], max_tokens: int = 65, min_tokens: int = 20) -> List[str]:
    """Generates normal abstractive summaries using google-t5/t5-small."""
    model, tokenizer = get_model_and_tokenizer()
    if not model or not tokenizer:
        return [clean_agency_tags(t[:250]) for t in texts]

    import torch

    prompts = [f"summarize: {clean_agency_tags(t)[:500]}" for t in texts]
    try:
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
        summaries = tokenizer.batch_decode(outputs, skip_special_tokens=True)
        cleaned_summaries = []
        for s in summaries:
            s_clean = clean_agency_tags(s).capitalize()
            if s_clean and not s_clean.endswith((".", "!", "?")):
                s_clean += "."
            cleaned_summaries.append(s_clean)
        return cleaned_summaries
    except Exception as e:
        logger.error(f"Error during local T5 batch summarization: {e}")
        return [clean_agency_tags(t[:250]) for t in texts]


def summarize_with_t5(news_data: List[Dict[str, Any]], lang: str = "en", batch_size: int = 6) -> List[Dict[str, str]]:
    """
    Standard normal news summarization using google-t5/t5-small for English news,
    and local extractive summarizer for Malayalam news.
    Cached in Redis. Zero external LLM calls.
    """
    if not news_data:
        return []

    results = []
    t5_candidates = []
    t5_indices = []

    for i, item in enumerate(news_data):
        title = item.get("title", "")
        body = item.get("description", "").strip() or title
        item_hash = generate_news_hash(title + body)
        cache_key = f"summary:t5:norm:{lang}:{item_hash}"

        cached = cache_get(cache_key)
        if cached and isinstance(cached, str):
            results.append({"title": title, "summary": cached})
        else:
            results.append({"title": title, "summary": ""})
            if lang == "ml" or is_malayalam(body) or is_malayalam(title):
                # Malayalam extractive summary
                summary = extract_summary(body, title=title)
                summary = clean_agency_tags(summary)
                if summary and not summary.endswith((".", "!", "?")):
                    summary += "."
                results[i]["summary"] = summary
                cache_set(cache_key, summary, ttl=86400 * 7)
            else:
                # English local T5 candidate
                clean_body = clean_agency_tags(body)
                clean_title = clean_agency_tags(title)
                input_text = f"{clean_title}. {clean_body}" if len(clean_body) < 180 else clean_body
                t5_candidates.append(input_text)
                t5_indices.append(i)

    # Process T5 candidates in batches
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
                    cache_set(cache_key, summary, ttl=86400 * 7)
        else:
            # Fallback if model could not be loaded
            for orig_idx in t5_indices:
                item = news_data[orig_idx]
                title = item.get("title", "")
                body = item.get("description", "").strip() or title
                summary = extract_summary(body, title=title)
                results[orig_idx]["summary"] = clean_agency_tags(summary)

    # Sanity check: fill any remaining empty summaries
    for i, item in enumerate(news_data):
        if not results[i]["summary"]:
            results[i]["summary"] = clean_agency_tags(extract_summary(
                item.get("description", "").strip() or item.get("title", ""),
                title=item.get("title", "")
            ))

    return results
