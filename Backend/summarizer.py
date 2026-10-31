import re
from collections import Counter
from cache_utils import generate_news_hash

STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "if", "because", "as", "what",
    "which", "this", "that", "these", "those", "then", "just", "so", "than",
    "such", "both", "through", "about", "for", "is", "of", "while", "during",
    "to", "from", "in", "out", "on", "off", "again", "further", "then", "once",
    "here", "there", "when", "where", "why", "how", "all", "any", "both",
    "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not",
    "only", "own", "same", "so", "than", "too", "very", "can", "will", "just",
    "should", "now", "be", "been", "being", "have", "has", "had", "do", "does",
    "did", "doing", "i", "you", "he", "she", "it", "we", "they", "them", "their",
    "his", "her", "its", "our", "with", "at", "by", "into", "up", "after", "before"
}


def extract_summary(text: str, title: str = "", max_words: int = 60) -> str:
    """
    Extractive summarization using Luhn word-frequency scoring + Title keyword overlap.
    Runs locally in ~1ms with zero dependencies, 0 API tokens, and 100% uptime.
    """
    if not text:
        return title or ""

    clean_text = text.replace("\r\n", " ").replace("\n", " ")
    raw_sentences = re.split(r'(?<=[.!?])\s+', clean_text)
    sentences = [s.strip() for s in raw_sentences if len(s.strip()) >= 25]

    if not sentences:
        return text[:250].strip()

    total_words = sum(len(s.split()) for s in sentences)
    if total_words <= max_words:
        return " ".join(sentences)

    words = re.findall(r'[\u0D00-\u0D7F\w]{3,}', clean_text.lower())
    content_words = [w for w in words if w not in STOP_WORDS]
    if not content_words:
        return " ".join(sentences[:2])

    freq = Counter(content_words)
    title_words = set(re.findall(r'[\u0D00-\u0D7F\w]{3,}', title.lower())) - STOP_WORDS

    scored = []
    for idx, sentence in enumerate(sentences):
        sent_words = re.findall(r'[\u0D00-\u0D7F\w]{3,}', sentence.lower())
        if not sent_words:
            continue

        score = sum(freq.get(w, 0) for w in sent_words if w not in STOP_WORDS)
        title_matches = sum(1 for w in sent_words if w in title_words)
        score += title_matches * 3.0

        pos_weight = 1.4 if idx == 0 else (1.2 if idx == 1 else 1.0)
        final_score = (score / (max(1, len(sent_words)) ** 0.6)) * pos_weight
        scored.append((idx, final_score, sentence))

    scored.sort(key=lambda x: x[1], reverse=True)

    selected = []
    word_count = 0
    for idx, _, sentence in scored:
        s_words = len(sentence.split())
        if word_count + s_words <= max_words or not selected:
            selected.append((idx, sentence))
            word_count += s_words
        if word_count >= max_words * 0.75:
            break

    selected.sort(key=lambda x: x[0])
    return " ".join(s[1] for s in selected)


def summarize_news(news_data):
    """
    Summarizes news articles locally using extractive frequency scoring.
    Replaces external LLM calls with instant local processing.
    """
    summaries = []
    for item in news_data:
        title = item.get("title", "")
        body = item.get("description", "").strip() or title
        summary = extract_summary(body, title=title)
        summaries.append({
            "title": title,
            "summary": summary
        })
    return summaries

