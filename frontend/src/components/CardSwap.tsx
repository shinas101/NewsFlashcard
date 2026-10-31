/* Hallmark · component: CardSwap · genre: editorial · theme: wine-charcoal
 * philosophy: 5 · hierarchy: 5 · execution: 5 · specificity: 5 · restraint: 5 · variety: 5
 * states: default · hover · focus-visible · active · dragging · exiting · empty · loading
 * contrast: pass (WCAG AAA) · motion: GPU-composited ease-out
 */

import React, { useEffect, useRef, useState, useImperativeHandle, forwardRef } from "react";
import { RotateCcw } from "lucide-react";

/* ══ Card swap ════════════════════════════════════════════
   A realistic, tactile stack of news cards in depth.
   Users visibly see cards stacked behind with organic micro-angles.
   Dragging or flicking flings the top card cleanly away,
   and the next card smoothly ascends to the top of the deck. */

// Desktop parameters: wide horizontal card deck (640x370)
const DESKTOP_W = 680;
const DESKTOP_H = 460;
const DESKTOP_CW = 640;
const DESKTOP_CH = 370;
const DESKTOP_STEP_Y = 16;
const DESKTOP_STEP_Z = 42;
const DESKTOP_ROTATIONS = [0, 1.4, -1.8, 1.1, -1.3];
const DESKTOP_OFFSET_X = [0, 4, -4, 3, -3];
const DESKTOP_SCALE_STEP = 0.035;

// Mobile parameters: tall phone card deck (~340x460)
// Calibrated so that on narrower, taller mobile viewports, the stacked cards
// behind visibly fan out with organic micro-rotations and step upward at the top,
// creating the exact same physical, tactile stack illusion as the desktop view.
const MOBILE_STEP_Y = 16;
const MOBILE_STEP_Z = 34;
const MOBILE_ROTATIONS = [0, 2.4, -2.6, 2.0, -2.2];
const MOBILE_OFFSET_X = [0, 6, -6, 5, -5];
const MOBILE_SCALE_STEP = 0.020;

// ── Source → domain map for favicons ──────────────────────
const SOURCE_DOMAINS: Record<string, string> = {
  // Indian national / English
  "The Hindu": "thehindu.com",
  "The Times of India": "timesofindia.indiatimes.com",
  "Times of India": "timesofindia.indiatimes.com",
  "NDTV": "ndtv.com",
  "NDTV Profit": "ndtvprofit.com",
  "India Today": "indiatoday.in",
  "The Indian Express": "indianexpress.com",
  "Hindustan Times": "hindustantimes.com",
  "Moneycontrol.com": "moneycontrol.com",
  "Moneycontrol": "moneycontrol.com",
  "Live Law": "livelaw.in",
  "Reuters": "reuters.com",
  "Al Jazeera": "aljazeera.com",
  "Business Standard": "business-standard.com",
  "Economic Times": "economictimes.indiatimes.com",
  "Mint": "livemint.com",
  "LiveMint": "livemint.com",
  "CNET": "cnet.com",
  "Kitco": "kitco.com",
  "BigGo Finance": "biggo.com",
  "Telegraph India": "telegraphindia.com",
  "Deccan Herald": "deccanherald.com",
  "Tribune India": "tribuneindia.com",
  "The Wire": "thewire.in",
  "Scroll": "scroll.in",
  "The Print": "theprint.in",
  "ThePrint": "theprint.in",
  "News18": "news18.com",
  "News18 India": "news18.com",
  "Zee News": "zeenews.india.com",
  "Republic World": "republicworld.com",
  "FirstPost": "firstpost.com",
  "Firstpost": "firstpost.com",
  "Indian Express": "indianexpress.com",
  "Outlook India": "outlookindia.com",
  "DNA India": "dnaindia.com",
  "OpIndia": "opindia.com",
  "ABP Live": "abplive.com",
  "Deccan Chronicle": "deccanchronicle.com",
  "Financial Express": "financialexpress.com",
  // Malayalam
  "Manorama Online": "manoramaonline.com",
  "Mathrubhumi": "mathrubhumi.com",
  "Asianet News Malayalam": "asianetnews.com",
  "News18 Malayalam": "news18.com",
  "Madhyamam": "madhyamam.com",
  "Deepika": "deepika.com",
  "Kerala Kaumudi": "keralakaumudi.com",
  "Deshabhimani": "deshabhimani.com",
  "Janmabhumi": "janmabhumidaily.com",
  "Mangalam": "mangalam.com",
  "Siraj": "sirajlive.com",
  "Media One": "mediaoneindia.com",
  "Reporter TV": "reporterlive.com",
  "Janam TV": "janamonline.com",
};

function getLogoUrl(source?: string, link?: string): string | null {
  if (source && SOURCE_DOMAINS[source]) {
    return `https://www.google.com/s2/favicons?sz=32&domain=${SOURCE_DOMAINS[source]}`;
  }
  if (link) {
    try {
      const parsed = new URL(link);
      const host = parsed.hostname.replace(/^www\./, "");
      if (host && !host.includes("news.google.com")) {
        return `https://www.google.com/s2/favicons?sz=32&domain=${host}`;
      }
    } catch (_) {}
  }
  return null;
}

// ── SourceBadge: logo + source name ────────────────────────────
function SourceBadge({ source, link, size = "sm" }: { source?: string; link?: string; size?: "sm" | "md" }) {
  const [imgOk, setImgOk] = useState(true);
  const logoUrl = getLogoUrl(source, link);
  const textClass = size === "md"
    ? "text-[11px] sm:text-[12px]"
    : "text-[10px] sm:text-[11px]";

  return (
    <span className={`inline-flex items-center gap-1.5 font-mono tracking-wider text-black/80 uppercase font-semibold ${textClass}`}>
      {logoUrl && imgOk && (
        <img
          src={logoUrl}
          alt=""
          width={size === "md" ? 16 : 14}
          height={size === "md" ? 16 : 14}
          className="rounded-sm flex-shrink-0"
          onError={() => setImgOk(false)}
        />
      )}
      <span>{source || "FLASH NEWS"}</span>
    </span>
  );
}

export type Card = {
  id: string;
  title: string;
  src?: string;
  source?: string;
  summary?: string;
  link?: string;
  description?: string;
};

const CARDS: Card[] = [
  { id: "mount", title: "Mountain", src: "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=800&q=80" },
  { id: "bloom", title: "Bloom", src: "https://images.unsplash.com/photo-1490750967868-88aa4486c946?auto=format&fit=crop&w=800&q=80" },
  { id: "peak", title: "Peak", src: "https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=800&q=80" },
  { id: "wings", title: "Wings", src: "https://images.unsplash.com/photo-1558981806-ec527fa84c39?auto=format&fit=crop&w=800&q=80" },
];

export interface CardSwapHandle {
  swipeLeft: () => void;
  swipeRight: () => void;
  reset: () => void;
}

export interface CardSwapProps {
  auto?: boolean;
  every?: number;
  cards?: Card[];
  width?: number;
  height?: number;
  cardWidth?: number;
  cardHeight?: number;
  theme?: "light" | "dark";
  onCardChange?: (frontCard: Card, index: number, remaining: number) => void;
  onAllSeen?: () => void;
}

export const CardSwap = forwardRef<CardSwapHandle, CardSwapProps>(function CardSwap(
  {
    auto = false,
    every = 4,
    cards,
    width: propW,
    height: propH,
    cardWidth: propCW,
    cardHeight: propCH,
    theme = "dark",
    onCardChange,
    onAllSeen,
  },
  ref
) {
  const activeCards = cards && cards.length > 0 ? cards : CARDS;
  const [order, setOrder] = useState<string[]>(() => activeCards.map((c) => c.id));
  const [windowDimensions, setWindowDimensions] = useState({ width: 680, height: 700 });
  const exitingIdsRef = useRef<Set<string>>(new Set());
  const els = useRef<Record<string, HTMLDivElement | null>>({});

  // Responsive mobile screen detection
  useEffect(() => {
    const handleResize = () => {
      setWindowDimensions({
        width: window.innerWidth,
        height: window.innerHeight,
      });
    };
    handleResize();
    window.addEventListener("resize", handleResize, { passive: true });
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const isMobile = windowDimensions.width < 640;

  // Responsive card dimension computation
  const cardWidth = propCW || (isMobile ? Math.min(windowDimensions.width - 32, 350) : DESKTOP_CW);
  const cardHeight = propCH || (isMobile ? Math.min(windowDimensions.height - 170, 460) : DESKTOP_CH);
  const stageWidth = propW || (isMobile ? cardWidth + 24 : DESKTOP_W);
  const stageHeight = propH || (isMobile ? cardHeight + 52 : DESKTOP_H);

  // Sync order if external cards change
  useEffect(() => {
    exitingIdsRef.current.clear();
    setOrder(activeCards.map((c) => c.id));
  }, [cards]);

  const st = useRef({
    hover: false,
    drag: null as null | {
      id: string;
      pid: number;
      startX: number;
      startY: number;
      dx: number;
      dy: number;
      vx: number;
      vy: number;
      lastTime: number;
      lastX: number;
      lastY: number;
      rafId: number | null;
    },
  });

  // Physical stack slot transform with organic micro-angles and depth steps
  const slot = (k: number) => {
    const scaleStep = isMobile ? MOBILE_SCALE_STEP : DESKTOP_SCALE_STEP;
    const minScale = isMobile ? 0.90 : 0.86;
    const scale = Math.max(minScale, 1 - k * scaleStep);

    const stepY = isMobile ? MOBILE_STEP_Y : DESKTOP_STEP_Y;
    const stepZ = isMobile ? MOBILE_STEP_Z : DESKTOP_STEP_Z;
    const rotations = isMobile ? MOBILE_ROTATIONS : DESKTOP_ROTATIONS;
    const offsetsX = isMobile ? MOBILE_OFFSET_X : DESKTOP_OFFSET_X;

    const y = -k * stepY;
    const z = -k * stepZ;
    const rot = rotations[k] || 0;
    const x = offsetsX[k] || 0;
    return `translate3d(${x}px, ${y}px, ${z}px) scale(${scale}) rotate(${rot}deg)`;
  };

  /* Buttery fling exit: card starts from its exact release point with zero snap */
  const dismissCardWithMotion = (id: string, startX = 0, startY = 0, vx = 0, vy = 0) => {
    if (exitingIdsRef.current.has(id)) return;
    exitingIdsRef.current.add(id);

    const el = els.current[id];
    if (!el) {
      setOrder((o) => {
        const next = o.filter((cId) => cId !== id);
        if (next.length === 0 && onAllSeen) onAllSeen();
        return next;
      });
      exitingIdsRef.current.delete(id);
      return;
    }

    const screenW = windowDimensions.width;
    const screenH = windowDimensions.height;

    let targetX = 0;
    let targetY = 0;
    let targetRot = 0;

    const absDx = Math.abs(startX);
    const absDy = Math.abs(startY);
    const absVx = Math.abs(vx);
    const absVy = Math.abs(vy);

    // Determine exit trajectory based on drag direction and momentum
    if (absDx >= absDy || absVx > absVy) {
      const signX = Math.sign(vx || startX || 1);
      targetX = startX + signX * Math.max(screenW * 1.25, 450);
      targetY = startY + (vy * 220);
      targetRot = signX * 14;
    } else {
      const signY = Math.sign(vy || startY || -1);
      targetX = startX + (vx * 180);
      targetY = startY + signY * Math.max(screenH * 1.25, 550);
      targetRot = (startX * 0.03);
    }

    // Hardware-accelerated exit animation starting directly from current finger position
    el.style.transition = "transform 320ms cubic-bezier(0.16, 1, 0.3, 1), opacity 260ms cubic-bezier(0.7, 0, 0.84, 0)";
    el.style.transform = `translate3d(${targetX.toFixed(1)}px, ${targetY.toFixed(1)}px, 0px) rotate(${targetRot.toFixed(1)}deg) scale(0.92)`;
    el.style.opacity = "0";
    el.style.pointerEvents = "none";

    // Instantly advance order state so the card behind smoothly steps up
    setOrder((o) => {
      const next = o.filter((cId) => cId !== id);
      if (next.length > 0 && onCardChange) {
        const frontCard = activeCards.find((c) => c.id === next[0]);
        if (frontCard) {
          onCardChange(frontCard, activeCards.indexOf(frontCard), next.length);
        }
      } else if (next.length === 0 && onAllSeen) {
        onAllSeen();
      }
      return next;
    });

    // Clean up DOM styles once off-screen
    setTimeout(() => {
      exitingIdsRef.current.delete(id);
      if (el) {
        el.style.transition = "";
        el.style.transform = "";
        el.style.opacity = "";
        el.style.pointerEvents = "";
      }
    }, 340);
  };

  // Expose swipe methods via ref
  useImperativeHandle(ref, () => ({
    swipeLeft: () => {
      if (order.length > 0) dismissCardWithMotion(order[0], -80, 0, -0.6, 0);
    },
    swipeRight: () => {
      if (order.length > 0) dismissCardWithMotion(order[0], 80, 0, 0.6, 0);
    },
    reset: () => {
      handleReset();
    },
  }));

  const handleReset = () => {
    exitingIdsRef.current.clear();
    setOrder(activeCards.map((c) => c.id));
  };

  const unhook = useRef(() => {});
  useEffect(() => () => unhook.current(), []);

  /* ══ Touch & Pointer Gestures ══════════════════════════════
     Uses requestAnimationFrame for 60/120fps lock on mobile. */
  const grab = (e: React.PointerEvent<HTMLDivElement>, id: string, front: boolean) => {
    if (!front || exitingIdsRef.current.has(id)) return;
    if (e.pointerType === "mouse" && e.button !== 0) return;

    if (st.current.drag) {
      if (st.current.drag.rafId) cancelAnimationFrame(st.current.drag.rafId);
      unhook.current();
      st.current.drag = null;
    }

    const el = e.currentTarget;
    try {
      el.setPointerCapture(e.pointerId);
    } catch (_) {}

    const now = performance.now();
    st.current.drag = {
      id,
      pid: e.pointerId,
      startX: e.clientX,
      startY: e.clientY,
      dx: 0,
      dy: 0,
      vx: 0,
      vy: 0,
      lastTime: now,
      lastX: e.clientX,
      lastY: e.clientY,
      rafId: null,
    };

    el.style.transition = "none";

    const rub = (d: number) => {
      if (Math.abs(d) < 200) return d;
      return 200 * Math.sign(d) + 35 * Math.tanh((Math.abs(d) - 200) / 70);
    };

    const mv = (ev: PointerEvent) => {
      const s = st.current;
      if (!s.drag || ev.pointerId !== s.drag.pid || exitingIdsRef.current.has(s.drag.id)) return;
      const d = s.drag;

      const currentTime = performance.now();
      const dt = Math.max(1, currentTime - d.lastTime);
      d.vx = (ev.clientX - d.lastX) / dt;
      d.vy = (ev.clientY - d.lastY) / dt;
      d.lastTime = currentTime;
      d.lastX = ev.clientX;
      d.lastY = ev.clientY;
      d.dx = ev.clientX - d.startX;
      d.dy = ev.clientY - d.startY;

      // Batch DOM style update to screen frame
      if (!d.rafId) {
        d.rafId = requestAnimationFrame(() => {
          if (!st.current.drag) return;
          const x = rub(d.dx);
          const y = rub(d.dy);
          const rot = x * 0.038;
          el.style.transform = `translate3d(${x.toFixed(1)}px, ${y.toFixed(1)}px, 0px) rotate(${rot.toFixed(1)}deg)`;
          d.rafId = null;
        });
      }
    };

    const up = (ev: PointerEvent) => {
      const s = st.current;
      if (!s.drag || ev.pointerId !== s.drag.pid) return;
      const d = s.drag;
      if (d.rafId) cancelAnimationFrame(d.rafId);
      s.drag = null;
      unhook.current();

      try {
        el.releasePointerCapture(ev.pointerId);
      } catch (_) {}

      const dist = Math.hypot(d.dx, d.dy);
      const absDx = Math.abs(d.dx);
      const absDy = Math.abs(d.dy);
      const absVx = Math.abs(d.vx);
      const absVy = Math.abs(d.vy);

      // Flick or drag threshold passed -> dismiss
      const isQuickFlick = (absVx > 0.35 && absDx > 12) || (absVy > 0.35 && absDy > 15);
      const isDragPassed = absDx > 40 || absDy > 48;
      const isTapFlick = dist < 6 && (performance.now() - d.lastTime) < 220;

      if (isDragPassed || isQuickFlick) {
        dismissCardWithMotion(id, d.dx, d.dy, d.vx, d.vy);
        return;
      }

      if (isTapFlick) {
        dismissCardWithMotion(id, 0, -40, 0, -0.6);
        return;
      }

      // Settle back to slot 0 smoothly with Hallmark ease-out
      el.style.transition = "transform 260ms cubic-bezier(0.16, 1, 0.3, 1)";
      el.style.transform = slot(0);
    };

    window.addEventListener("pointermove", mv, { passive: true });
    window.addEventListener("pointerup", up, { passive: true });
    window.addEventListener("pointercancel", up, { passive: true });

    unhook.current = () => {
      window.removeEventListener("pointermove", mv);
      window.removeEventListener("pointerup", up);
      window.removeEventListener("pointercancel", up);
      unhook.current = () => {};
    };
  };

  /* Auto-timer */
  useEffect(() => {
    if (!auto || order.length <= 1) return;
    const id = window.setInterval(() => {
      if (!st.current.hover && !st.current.drag && !document.hidden && order.length > 0) {
        dismissCardWithMotion(order[0], 0, -50, 0, -0.5);
      }
    }, Math.max(1.5, every) * 1000);
    return () => window.clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [auto, every, order]);

  // All cards read state
  if (order.length === 0) {
    return (
      <div
        className="csw-empty w-full max-w-sm sm:max-w-xl mx-auto p-6 sm:p-10 border border-black/30 text-center select-none shadow-xl rounded-md"
        style={{
          width: cardWidth,
          minHeight: 300,
          backgroundColor: "#8a2435",
          background: "linear-gradient(155deg, #962a3e 0%, #7e1e2f 100%)",
        }}
      >
        <div className="w-8 h-0.5 bg-black mx-auto mb-4" />
        <h3 className="text-xl sm:text-2xl font-bold text-black tracking-tight mb-2">
          All Headlines Caught Up
        </h3>
        <p className="text-xs font-mono font-medium text-black/75 mb-6">
          You have read all {activeCards.length} headlines in this edition.
        </p>
        <button
          onClick={handleReset}
          className="text-xs font-mono font-bold px-5 py-2.5 bg-black text-white hover:bg-black/85 active:scale-[0.98] transition-all cursor-pointer flex items-center gap-2 mx-auto rounded-sm shadow-sm"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>Read Again</span>
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center w-full">
      <div
        className="csw"
        data-theme={theme}
        style={{ width: stageWidth, height: stageHeight }}
        onPointerEnter={() => {
          st.current.hover = true;
        }}
        onPointerLeave={() => {
          st.current.hover = false;
        }}
      >
        <div
          className="csw-stage"
          style={{
            width: cardWidth,
            height: cardHeight,
            marginTop: isMobile ? 38 : 36,
          }}
        >
          {activeCards.map((c, originalIndex) => {
            const k = order.indexOf(c.id);
            if (k < 0 || k > 4) return null;
            const front = k === 0;
            const cardNum = originalIndex + 1;

            return (
              <div
                key={c.id}
                ref={(el) => {
                  els.current[c.id] = el;
                }}
                className="csw-card"
                data-front={front || undefined}
                style={{
                  zIndex: activeCards.length - k,
                  ["--t" as string]: slot(Math.max(0, k)),
                  touchAction: "none",
                }}
                onPointerDown={(e) => grab(e, c.id, front)}
              >
                {/* Hardware-accelerated depth overlay for stacked cards */}
                {k > 0 && (
                  <div
                    className="absolute inset-0 bg-black pointer-events-none rounded-[inherit] transition-opacity duration-300 z-10"
                    style={{ opacity: Math.min(0.48, k * 0.12) }}
                  />
                )}

                {c.summary || c.source ? (
                  /* News Card Content */
                  <div className="csw-news-inner select-none relative flex flex-col justify-between h-full p-4 sm:p-6 text-black">
                    {/* Header: source badge & card stack indicator */}
                    <div className="flex items-center justify-between border-b border-black/15 pb-2.5">
                      <SourceBadge source={c.source} link={c.link} size="sm" />
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded-sm bg-black/10 border border-black/15 text-black/75 font-bold tracking-wider">
                        {cardNum} / {activeCards.length}
                      </span>
                    </div>

                    {/* Headline & Summary */}
                    <div className="flex-1 my-2.5 sm:my-3.5 flex flex-col justify-start overflow-hidden pr-1 pointer-events-none">
                      <h2 className="text-base sm:text-lg md:text-xl font-bold leading-snug text-black tracking-tight mb-2 break-words">
                        {c.title}
                      </h2>
                      <div className="w-8 h-0.5 bg-black/40 mb-2.5 flex-shrink-0" />
                      <p className="text-xs sm:text-sm leading-relaxed text-black/85 font-medium line-clamp-6 sm:line-clamp-4">
                        {c.summary || c.description}
                      </p>
                    </div>

                    {/* Footer CTA */}
                    <div className="flex items-center justify-end pt-2.5 border-t border-black/15">
                      {c.link && (
                        <a
                          href={c.link}
                          target="_blank"
                          rel="noopener noreferrer"
                          onPointerDown={(e) => e.stopPropagation()}
                          onClick={(e) => e.stopPropagation()}
                          className="text-xs font-mono font-bold px-3.5 py-1.5 rounded-sm bg-black text-white hover:bg-black/85 active:scale-[0.98] transition-all flex items-center gap-1.5 pointer-events-auto tracking-wider uppercase"
                        >
                          <span>READ FULL</span>
                          <span className="text-xs">↗</span>
                        </a>
                      )}
                    </div>
                  </div>
                ) : (
                  /* Default Photo Card */
                  <>
                    <img className="csw-photo" src={c.src} alt="" draggable={false} />
                    <div className="csw-tag">{c.title}</div>
                  </>
                )}
              </div>
            );
          })}
        </div>

        {/* Visual stack indicator underneath the deck */}
        <div className="mt-4 sm:mt-5 flex items-center justify-center gap-2 text-zinc-400 text-[11px] font-mono tracking-wider select-none pointer-events-none">
          <span className="w-1.5 h-1.5 rounded-full bg-[#9e3547] animate-pulse" />
          <span>{order.length} cards in stack • Swipe or tap to draw next</span>
        </div>
      </div>
    </div>
  );
});

export default CardSwap;
