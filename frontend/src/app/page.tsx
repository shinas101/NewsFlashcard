"use client";

import React, { useEffect, useState, useMemo, useRef } from "react";
import Link from "next/link";
import CardSwap, { Card } from "@/components/CardSwap";
import { EmbedModal } from "@/components/EmbedModal";
import { Code } from "lucide-react";

interface NewsArticle {
  title: string;
  source: string;
  link: string;
  summary: string;
  description?: string;
}

const STORAGE_KEY = "news_cache_v2_en";

export default function Home() {
  const [articles, setArticles] = useState<NewsArticle[]>([]);
  const [loading, setLoading] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [isEmbedOpen, setIsEmbedOpen] = useState(false);
  const pollTimerRef = useRef<NodeJS.Timeout | null>(null);

  // 1. Instant Cache Hydration: show cached articles immediately on mount
  useEffect(() => {
    try {
      const cached = localStorage.getItem(STORAGE_KEY);
      if (cached) {
        const parsed = JSON.parse(cached);
        if (Array.isArray(parsed) && parsed.length > 0) {
          setArticles(parsed);
          setLoading(false);
        }
      }
    } catch (_) {}
  }, []);

  const fetchNews = async (silent = false) => {
    if (!silent && articles.length === 0) {
      setLoading(true);
    }
    setIsSyncing(true);
    setError(null);

    try {
      const isLocalhost =
        typeof window !== "undefined" &&
        (window.location.hostname === "localhost" ||
          window.location.hostname === "127.0.0.1");

      const endpoints = ["/api/news?lang=en", "/api/news"];
      if (isLocalhost) {
        endpoints.push("http://127.0.0.1:8000/api/news?lang=en");
        endpoints.push("http://127.0.0.1:8000/api/news");
      }

      let data: any = null;
      for (const endpoint of endpoints) {
        try {
          const res = await fetch(endpoint, {
            headers: { Accept: "application/json" },
          });
          const contentType = res.headers.get("content-type") || "";
          if (res.ok && contentType.includes("application/json")) {
            data = await res.json();
            if (data && Array.isArray(data.news) && data.news.length > 0) {
              break;
            }
          }
        } catch (_) {
          continue;
        }
      }
      if (data && Array.isArray(data.news) && data.news.length > 0) {
        const incomingNews: NewsArticle[] = data.news;

        // Check if incoming news has changed
        setArticles((prev) => {
          const hasChanged =
            prev.length === 0 ||
            prev[0]?.title !== incomingNews[0]?.title ||
            prev.length !== incomingNews.length;

          if (hasChanged) {
            try {
              localStorage.setItem(STORAGE_KEY, JSON.stringify(incomingNews));
            } catch (_) {}

            if (prev.length > 0) {
              setToast("Feed updated with latest headlines");
              setTimeout(() => setToast(null), 2800);
            }
            return incomingNews;
          }
          return prev;
        });

        // If backend is still refreshing in background, poll again soon
        if (data.is_updating) {
          if (pollTimerRef.current) clearTimeout(pollTimerRef.current);
          pollTimerRef.current = setTimeout(() => {
            fetchNews(true);
          }, 4000);
        }
      } else if (articles.length === 0) {
        throw new Error("No news returned");
      }
    } catch (err: any) {
      console.error("Fetch error:", err);
      if (articles.length === 0) {
        setError("Failed to load news feed. Please retry.");
      }
    } finally {
      setLoading(false);
      setIsSyncing(false);
    }
  };

  // Initial fetch and 3-minute background polling
  useEffect(() => {
    fetchNews(articles.length > 0);

    const interval = setInterval(() => {
      fetchNews(true);
    }, 180000); // 3 minutes

    return () => {
      clearInterval(interval);
      if (pollTimerRef.current) clearTimeout(pollTimerRef.current);
    };
  }, []);

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

  return (
    <main className="h-[100dvh] min-h-[100dvh] w-full bg-[#0b0b0d] text-zinc-100 flex items-center justify-center p-3 sm:p-4 relative overflow-hidden select-none touch-none">
      {/* Top Header Bar: Language switch + Live sync status */}
      <div className="absolute top-3 sm:top-4 inset-x-3 sm:inset-x-4 max-w-2xl mx-auto flex items-center justify-between z-30 pointer-events-auto">
        <div className="flex items-center gap-1.5 sm:gap-2">
          <span className="text-[11px] font-mono uppercase tracking-wider text-white font-bold bg-[#9e3547] px-2.5 py-1 border border-[#b03d52]/60 rounded-full">
            India National
          </span>
          <Link
            href="/malayalam"
            className="text-[11px] font-mono uppercase tracking-wider text-zinc-400 hover:text-white px-2.5 py-1 transition-colors"
          >
            മലയാളം →
          </Link>
          <button
            onClick={() => setIsEmbedOpen(true)}
            className="flex items-center gap-1 text-[11px] font-mono uppercase tracking-wider text-zinc-400 hover:text-white px-2 py-1 transition-colors rounded-full hover:bg-white/5 border border-transparent hover:border-white/10 cursor-pointer"
            title="Embed on external website"
          >
            <Code className="w-3.5 h-3.5 text-[#e67385]" />
            <span className="hidden xs:inline">Embed</span>
          </button>
        </div>

        {/* Non-blocking sync indicator */}
        {isSyncing && (
          <div className="flex items-center gap-2 px-2.5 py-1 rounded-full bg-zinc-900 border border-white/10 text-[10px] font-mono text-zinc-300">
            <span className="w-1.5 h-1.5 rounded-full bg-[#9e3547] animate-pulse" />
            <span className="hidden sm:inline">Checking updates...</span>
            <span className="sm:hidden">Syncing</span>
          </div>
        )}
      </div>

      {/* Toast Notification when new news arrives */}
      {toast && (
        <div className="absolute bottom-6 z-40 px-3.5 py-1.5 bg-zinc-900 border border-zinc-700/60 text-zinc-200 text-xs font-mono rounded-full shadow-lg transition-opacity flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-[#9e3547]" />
          <span>{toast}</span>
        </div>
      )}

      {/* Initial load only if NO cached articles exist */}
      {loading && articles.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-3 text-center z-10">
          <div className="w-8 h-8 border-2 border-white/20 border-t-[#9e3547] rounded-full animate-spin" />
          <p className="text-xs font-mono text-zinc-400 tracking-wider">
            Loading Headlines...
          </p>
        </div>
      ) : error && articles.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-3 text-center p-6 bg-zinc-900 border border-white/10 rounded-lg max-w-sm z-10">
          <p className="text-xs text-red-400 font-mono">{error}</p>
          <button
            onClick={() => fetchNews(false)}
            className="px-4 py-2 rounded-sm text-xs font-mono bg-white text-black font-semibold hover:bg-zinc-200 transition-colors"
          >
            Retry
          </button>
        </div>
      ) : cards.length > 0 ? (
        <div className="relative flex items-center justify-center w-full z-10">
          <CardSwap
            cards={cards}
            auto={false}
            theme="dark"
          />
        </div>
      ) : null}

      {/* Embed on External Website Modal */}
      <EmbedModal
        isOpen={isEmbedOpen}
        onClose={() => setIsEmbedOpen(false)}
        defaultLang="en"
      />
    </main>
  );
}
