"use client";

import React, { useState } from "react";
import { Code, Copy, Check, X, ExternalLink } from "lucide-react";

interface EmbedModalProps {
  isOpen: boolean;
  onClose: () => void;
  defaultLang?: "en" | "ml";
}

export function EmbedModal({ isOpen, onClose, defaultLang = "en" }: EmbedModalProps) {
  const [lang, setLang] = useState<"en" | "ml">(defaultLang);
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const [auto, setAuto] = useState(false);
  const [activeTab, setActiveTab] = useState<"iframe" | "script" | "react">("iframe");
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const origin = typeof window !== "undefined" ? window.location.origin : "http://localhost:3000";

  const queryParams = [
    `lang=${lang}`,
    `theme=${theme}`,
    auto ? "auto=true" : null,
  ].filter(Boolean).join("&");

  const embedUrl = `${origin}/embed?${queryParams}`;

  const iframeCode = `<iframe
  src="${embedUrl}"
  width="100%"
  height="540"
  frameborder="0"
  style="border:none; border-radius:12px; overflow:hidden;"
  allow="clipboard-write"
  title="News FlipCard Widget"
></iframe>`;

  const scriptCode = `<!-- News FlipCard Widget -->
<div
  id="news-flipcard"
  data-lang="${lang}"
  data-theme="${theme}"
  ${auto ? 'data-auto="true"' : ""}
  data-height="540px"
></div>
<script src="${origin}/embed.js" async></script>`;

  const reactCode = `import { NewsFlipCard } from "@/components/NewsFlipCard";

export default function MyPage() {
  return (
    <div style={{ maxWidth: 700, margin: "0 auto" }}>
      <NewsFlipCard
        lang="${lang}"
        theme="${theme}"
        auto={${auto}}
      />
    </div>
  );
}`;

  const activeSnippet =
    activeTab === "iframe" ? iframeCode : activeTab === "script" ? scriptCode : reactCode;

  const handleCopy = () => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(activeSnippet);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
      <div
        className="w-full max-w-xl bg-zinc-900 border border-zinc-700/80 rounded-2xl shadow-2xl overflow-hidden flex flex-col text-white"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800 bg-zinc-900/50">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-[#9e3547]/20 text-[#e67385] border border-[#9e3547]/30">
              <Code className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white tracking-tight">
                Embed this feed
              </h3>
              <p className="text-xs text-zinc-400">
                Add these news cards to your site.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Configuration Options */}
        <div className="p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            {/* Language Selector */}
            <div>
              <label className="block text-xs font-mono text-zinc-400 uppercase tracking-wider mb-1.5">
                Language
              </label>
              <div className="grid grid-cols-2 gap-1.5 bg-zinc-950 p-1 rounded-lg border border-zinc-800">
                <button
                  type="button"
                  onClick={() => setLang("en")}
                  className={`py-1.5 text-xs font-medium rounded-md transition-colors ${
                    lang === "en"
                      ? "bg-[#9e3547] text-white font-bold"
                      : "text-zinc-400 hover:text-white"
                  }`}
                >
                  English
                </button>
                <button
                  type="button"
                  onClick={() => setLang("ml")}
                  className={`py-1.5 text-xs font-medium rounded-md transition-colors ${
                    lang === "ml"
                      ? "bg-[#9e3547] text-white font-bold"
                      : "text-zinc-400 hover:text-white"
                  }`}
                >
                  മലയാളം
                </button>
              </div>
            </div>

            {/* Theme Selector */}
            <div>
              <label className="block text-xs font-mono text-zinc-400 uppercase tracking-wider mb-1.5">
                Theme
              </label>
              <div className="grid grid-cols-2 gap-1.5 bg-zinc-950 p-1 rounded-lg border border-zinc-800">
                <button
                  type="button"
                  onClick={() => setTheme("dark")}
                  className={`py-1.5 text-xs font-medium rounded-md transition-colors ${
                    theme === "dark"
                      ? "bg-[#9e3547] text-white font-bold"
                      : "text-zinc-400 hover:text-white"
                  }`}
                >
                  Dark
                </button>
                <button
                  type="button"
                  onClick={() => setTheme("light")}
                  className={`py-1.5 text-xs font-medium rounded-md transition-colors ${
                    theme === "light"
                      ? "bg-[#9e3547] text-white font-bold"
                      : "text-zinc-400 hover:text-white"
                  }`}
                >
                  Light
                </button>
              </div>
            </div>
          </div>

          {/* Auto advance toggle */}
          <div className="flex items-center justify-between p-3 rounded-lg bg-zinc-950/60 border border-zinc-800">
            <div>
              <span className="text-xs font-medium text-white block">Advance cards automatically</span>
              <span className="text-[11px] text-zinc-400">Show the next card every 5 seconds.</span>
            </div>
            <button
              type="button"
              onClick={() => setAuto(!auto)}
              className={`w-10 h-6 flex items-center rounded-full p-1 transition-colors cursor-pointer ${
                auto ? "bg-[#9e3547]" : "bg-zinc-700"
              }`}
            >
              <div
                className={`bg-white w-4 h-4 rounded-full shadow-md transform transition-transform ${
                  auto ? "translate-x-4" : "translate-x-0"
                }`}
              />
            </button>
          </div>

          {/* Format Tabs */}
          <div className="flex border-b border-zinc-800 gap-4 text-xs font-mono">
            <button
              onClick={() => setActiveTab("iframe")}
              className={`pb-2 transition-colors cursor-pointer ${
                activeTab === "iframe"
                  ? "text-[#e67385] border-b-2 border-[#9e3547] font-bold"
                  : "text-zinc-400 hover:text-white"
              }`}
            >
              HTML Iframe
            </button>
            <button
              onClick={() => setActiveTab("script")}
              className={`pb-2 transition-colors cursor-pointer ${
                activeTab === "script"
                  ? "text-[#e67385] border-b-2 border-[#9e3547] font-bold"
                  : "text-zinc-400 hover:text-white"
              }`}
            >
              Drop-in Script
            </button>
            <button
              onClick={() => setActiveTab("react")}
              className={`pb-2 transition-colors cursor-pointer ${
                activeTab === "react"
                  ? "text-[#e67385] border-b-2 border-[#9e3547] font-bold"
                  : "text-zinc-400 hover:text-white"
              }`}
            >
              React Component
            </button>
          </div>

          {/* Code Output Box */}
          <div className="relative">
            <pre className="p-4 bg-zinc-950 border border-zinc-800 rounded-xl text-xs font-mono text-emerald-400 overflow-x-auto max-h-44">
              <code>{activeSnippet}</code>
            </pre>
            <button
              onClick={handleCopy}
              className="absolute top-2.5 right-2.5 px-3 py-1.5 rounded-md bg-zinc-800 hover:bg-zinc-700 text-white text-xs font-mono flex items-center gap-1.5 transition-colors shadow cursor-pointer"
            >
              {copied ? (
                <>
                  <Check className="w-3.5 h-3.5 text-emerald-400" />
                  <span className="text-emerald-400">Copied</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5" />
                  <span>Copy</span>
                </>
              )}
            </button>
          </div>

          {/* Preview Link */}
          <div className="flex items-center justify-between text-xs text-zinc-400 pt-1">
            <span>Preview the embed</span>
            <a
              href={embedUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-[#e67385] hover:underline"
            >
              <span>Open preview</span>
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 bg-zinc-950/80 border-t border-zinc-800 text-[11px] text-zinc-400 flex items-center justify-between">
          <span>Add it to a WordPress, Shopify, Webflow, React, Vue, PHP, or HTML site.</span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-white font-medium transition-colors cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
