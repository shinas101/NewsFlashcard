"use client";

import React, { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import NewsFlipCard from "@/components/NewsFlipCard";

function EmbedContent() {
  const searchParams = useSearchParams();

  const langParam = searchParams.get("lang") || "en";
  const lang = langParam === "ml" || langParam === "malayalam" ? "ml" : "en";
  const theme = (searchParams.get("theme") === "light" ? "light" : "dark") as "light" | "dark";
  const auto = searchParams.get("auto") === "true";
  const every = Number(searchParams.get("every")) || 5;
  const apiBaseUrl = searchParams.get("api") || undefined;
  const bg = searchParams.get("bg") || "transparent";

  return (
    <div
      className={`w-full min-h-screen flex items-center justify-center p-2 sm:p-4 overflow-hidden select-none ${
        bg === "transparent" ? "bg-transparent" : theme === "light" ? "bg-zinc-100" : "bg-black"
      }`}
    >
      <NewsFlipCard
        lang={lang}
        theme={theme}
        auto={auto}
        every={every}
        apiBaseUrl={apiBaseUrl}
        showSyncStatus={false}
      />
    </div>
  );
}

export default function EmbedPage() {
  return (
    <main className="w-full min-h-screen bg-transparent overflow-hidden">
      <Suspense
        fallback={
          <div className="w-full min-h-screen flex items-center justify-center bg-transparent">
            <div className="w-8 h-8 border-2 border-white/20 border-t-[#9e3547] rounded-full animate-spin" />
          </div>
        }
      >
        <EmbedContent />
      </Suspense>
    </main>
  );
}

