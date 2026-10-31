"use client";

import React, { useEffect, useState, useMemo, useRef, forwardRef, useImperativeHandle } from "react";
import CardSwap, { Card, CardSwapHandle } from "./CardSwap";

export interface NewsArticle {
  title: string;
  source: string;
  link: string;
  summary: string;
  description?: string;
}

export interface NewsFlipCardProps {
  /**
   * News feed language: "en" for India National (English) or "ml" for Malayalam.
   * Defaults to "en".
   */
  lang?: "en" | "ml" | "malayalam";

  /**
   * Backend API base URL. Defaults to "http://127.0.0.1:8000" with automatic fallback to ":8001".
   */
  apiBaseUrl?: string;

  /**
   * Theme appearance: "dark" (obsidian/burgundy) or "light". Defaults to "dark".
   */
  theme?: "dark" | "light";

  /**
   * Auto-advance cards on timer. Defaults to false.
   */
  auto?: boolean;

  /**
   * Auto-advance interval in seconds. Defaults to 5.
   */
  every?: number;

  /**
   * Width of the outer stage in pixels. Optional.
   */
  width?: number;

  /**
   * Height of the outer stage in pixels. Optional.
   */
  height?: number;

  /**
   * Custom width of the news cards in pixels. Optional.
   */
  cardWidth?: number;

  /**
   * Custom height of the news cards in pixels. Optional.
   */
  cardHeight?: number;

  /**
   * Callback fired whenever the top visible card changes.
   */
  onCardChange?: (article: NewsArticle, index: number, remaining: number) => void;

  /**
   * Callback fired when all cards have been swiped.
   */
  onAllSeen?: () => void;

  /**
   * Custom CSS class name for the wrapper container.
   */
  className?: string;

  /**
   * Display non-blocking sync pill indicator. Defaults to true.
   */
  showSyncStatus?: boolean;
}

export interface NewsFlipCardHandle {
  swipeLeft: () => void;
  swipeRight: () => void;
  reset: () => void;
  refresh: () => Promise<void>;
}

export const NewsFlipCard = forwardRef<NewsFlipCardHandle, NewsFlipCardProps>(function NewsFlipCard(
  {
    lang = "en",
    apiBaseUrl,
    theme = "dark",
    auto = false,
    every = 5,
    width,
    height,
    cardWidth,
    cardHeight,
    onCardChange,
    onAllSeen,
    className = "",
    showSyncStatus = true,
  },
  ref
) {
  const isMalayalam = lang === "ml" || lang === "malayalam";
  const storageKey = `news_flipcard_cache_${isMalayalam ? "ml" : "en"}`;

  const [articles, setArticles] = useState<NewsArticle[]>([]);
  const [loading, setLoading] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const cardSwapRef = useRef<CardSwapHandle | null>(null);
  const pollTimerRef = useRef<NodeJS.Timeout | null>(null);

  // 1. Instant Cache Hydration: display cached feed immediately
  useEffect(() => {
    try {
      const cached = typeof window !== "undefined" ? localStorage.getItem(storageKey) : null;
      if (cached) {
        const parsed = JSON.parse(cached);
        if (Array.isArray(parsed) && parsed.length > 0) {
          setArticles(parsed);
          setLoading(false);
        }
      }
    } catch (_) {}
  }, [storageKey]);

  // Fetch news from API with automatic fallback
  const fetchNews = async (silent = false) => {
    if (!silent && articles.length === 0) {
      setLoading(true);
    }
    setIsSyncing(true);
    setError(null);

    const endpoint = isMalayalam ? "malayalam" : "news";

    const endpointsToTry: string[] = [];
    if (apiBaseUrl) {
      const cleanBase = apiBaseUrl.replace(/\/+$/, "");
      endpointsToTry.push(`${cleanBase}/${endpoint}`);
    } else {
      if (typeof window !== "undefined" && window.location.origin) {
        endpointsToTry.push(`/api/${endpoint}`);
      }
      endpointsToTry.push(`http://127.0.0.1:8001/${endpoint}`);
      endpointsToTry.push(`http://127.0.0.1:8000/${endpoint}`);
    }

    let successData: any = null;

    for (const url of endpointsToTry) {
      try {
        const res = await fetch(url, {
          headers: { Accept: "application/json" },
        });
        if (res.ok) {
          successData = await res.json();
          break;
        }
      } catch (_) {
        // Try next endpoint fallback
      }
    }

    try {
      if (successData && Array.isArray(successData.news) && successData.news.length > 0) {
        const incomingNews: NewsArticle[] = successData.news;

        setArticles((prev) => {
          const hasChanged =
            prev.length === 0 ||
            prev[0]?.title !== incomingNews[0]?.title ||
            prev.length !== incomingNews.length;

          if (hasChanged) {
            try {
              localStorage.setItem(storageKey, JSON.stringify(incomingNews));
            } catch (_) {}

            if (prev.length > 0) {
              setToast(isMalayalam ? "വാർത്തകൾ അപ്‌ഡേറ്റ് ചെയ്തു" : "Feed updated with latest news");
              setTimeout(() => setToast(null), 2800);
            }
            return incomingNews;
          }
          return prev;
        });

        if (successData.is_updating) {
          if (pollTimerRef.current) clearTimeout(pollTimerRef.current);
          pollTimerRef.current = setTimeout(() => {
            fetchNews(true);
          }, 4000);
        }
      } else if (articles.length === 0) {
        throw new Error("No news available");
      }
    } catch (err: any) {
      if (articles.length === 0) {
        setError(isMalayalam ? "വാർത്തകൾ ലോഡ് ചെയ്യുമ്പോൾ പിശക് സംഭവിച്ചു" : "Failed to load news feed. Please retry.");
      }
    } finally {
      setLoading(false);
      setIsSyncing(false);
    }
  };

  // Initial fetch and 3-minute background update poll
  useEffect(() => {
    fetchNews(articles.length > 0);

    const interval = setInterval(() => {
      fetchNews(true);
    }, 180000);

    return () => {
      clearInterval(interval);
      if (pollTimerRef.current) clearTimeout(pollTimerRef.current);
    };
  }, [lang, apiBaseUrl]);

  // Forward ref methods to parent
  useImperativeHandle(ref, () => ({
    swipeLeft: () => cardSwapRef.current?.swipeLeft(),
    swipeRight: () => cardSwapRef.current?.swipeRight(),
    reset: () => cardSwapRef.current?.reset(),
    refresh: () => fetchNews(false),
  }));

  // Format articles for CardSwap
  const cards: Card[] = useMemo(() => {
    return articles.map((article, index) => ({
      id: `article-${index}-${article.title.slice(0, 15)}`,
      title: article.title,
      source: article.source,
      summary: article.summary || article.description || "",
      link: article.link,
      description: article.description,
    }));
  }, [articles]);

  const handleCardChange = (frontCard: Card, index: number, remaining: number) => {
    if (onCardChange) {
      const match = articles.find((a) => a.title === frontCard.title);
      if (match) {
        onCardChange(match, index, remaining);
      }
    }
  };

  return (
    <div className={`relative flex flex-col items-center justify-center w-full select-none ${className}`}>
      {/* Non-blocking sync indicator */}
      {showSyncStatus && isSyncing && (
        <div className="absolute top-2 right-2 z-30 flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-zinc-900/90 border border-white/10 text-[9px] font-mono text-zinc-300 shadow-md animate-pulse pointer-events-none">
          <span className="w-1.5 h-1.5 rounded-full bg-[#9e3547]" />
          <span>{isMalayalam ? "അപ്ഡേറ്റ് പരിശോധിക്കുന്നു..." : "Updating..."}</span>
        </div>
      )}

      {/* Toast update notification */}
      {toast && (
        <div className="absolute bottom-4 z-40 px-3 py-1 bg-zinc-900 border border-zinc-700/60 text-zinc-200 text-[11px] font-mono rounded-full shadow-lg transition-opacity flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-[#9e3547]" />
          <span>{toast}</span>
        </div>
      )}

      {/* Loading state if no cached articles exist */}
      {loading && articles.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-3 p-8 text-center min-h-[340px]">
          <div className="w-8 h-8 border-2 border-white/20 border-t-[#9e3547] rounded-full animate-spin" />
          <p className="text-xs font-mono text-zinc-400">
            {isMalayalam ? "വാർത്തകൾ ലഭ്യമാക്കുന്നു..." : "Fetching news feed..."}
          </p>
        </div>
      ) : error && articles.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-3 p-6 bg-zinc-900/80 border border-white/10 rounded-xl max-w-sm text-center min-h-[300px]">
          <p className="text-xs text-red-400 font-mono">{error}</p>
          <button
            onClick={() => fetchNews(false)}
            className="px-4 py-1.5 rounded-md text-xs font-mono bg-white text-black font-semibold hover:bg-zinc-200 transition-colors cursor-pointer"
          >
            {isMalayalam ? "വീണ്ടും ശ്രമിക്കുക" : "Retry"}
          </button>
        </div>
      ) : cards.length > 0 ? (
        <CardSwap
          ref={cardSwapRef}
          cards={cards}
          auto={auto}
          every={every}
          theme={theme}
          width={width}
          height={height}
          cardWidth={cardWidth}
          cardHeight={cardHeight}
          onCardChange={handleCardChange}
          onAllSeen={onAllSeen}
        />
      ) : null}
    </div>
  );
});

export default NewsFlipCard;

