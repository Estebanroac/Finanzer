"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter, usePathname } from "next/navigation";
import { searchStocks, SearchResult } from "@/lib/api";

export default function Navbar({ symbol }: { symbol?: string }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [selectedIdx, setSelectedIdx] = useState(-1);
  const [scrolled, setScrolled] = useState(false);
  const router = useRouter();
  const pathname = usePathname();
  const inputRef = useRef<HTMLInputElement>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<NodeJS.Timeout>(undefined);

  const isHome = pathname === "/";

  // Elevación del nav al scroll (el fondo/borde se intensifican)
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 10);
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    if (query.length < 1) { setResults([]); setShowDropdown(false); return; }
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      const r = await searchStocks(query);
      setResults(r);
      setShowDropdown(r.length > 0);
      setSelectedIdx(-1);
    }, 180);
    return () => clearTimeout(debounceRef.current);
  }, [query]);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  function navigate(symbol: string) {
    setShowDropdown(false);
    setQuery("");
    router.push(`/stock/${symbol}`);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIdx(i => Math.min(i + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIdx(i => Math.max(i - 1, -1));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (selectedIdx >= 0 && results[selectedIdx]) navigate(results[selectedIdx].ticker);
      else if (query.trim()) navigate(query.trim().toUpperCase());
    } else if (e.key === "Escape") {
      setShowDropdown(false);
      inputRef.current?.blur();
    }
  }

  // Don't render on home page (home has its own search)
  if (isHome) return null;

  return (
    <nav className={`sticky top-0 z-50 backdrop-blur-2xl transition-all duration-400 border-b ${
      scrolled
        ? "bg-[#050507]/90 border-white/[0.1] shadow-[0_10px_34px_rgba(0,0,0,0.4)]"
        : "bg-[#050507]/75 border-white/[0.04]"
    }`}>
      <div className="max-w-6xl mx-auto px-4 sm:px-6 h-14 flex items-center gap-4">
        {/* Volver al inicio */}
        <button
          onClick={() => router.push("/")}
          aria-label="Volver al inicio"
          title="Volver al inicio"
          className="press shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-[#a1a1a6]
            border border-white/[0.08] bg-white/[0.04] hover:bg-white/[0.09] hover:text-white
            hover:border-white/[0.15] transition-colors"
        >
          <svg className="w-[15px] h-[15px]" fill="none" stroke="currentColor" strokeWidth={2.4} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
        </button>

        {/* Logo */}
        <a href="/" className="shrink-0 group flex items-center gap-2">
          <img src="/logo.png" alt="Finanzer" className="h-7 w-auto" />
          <span className="text-[15px] font-bold text-white tracking-tight group-hover:text-[#0cc06c] transition-colors">
            Finanzer
          </span>
        </a>

        {/* Divider */}
        <div className="w-px h-5 bg-white/[0.06] max-[560px]:hidden" />

        {/* Search */}
        <div ref={wrapperRef} className="relative flex-1 max-w-md">
          <div className="relative">
            <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={e => setQuery(e.target.value)}
              onFocus={() => results.length > 0 && setShowDropdown(true)}
              onKeyDown={handleKeyDown}
              placeholder="Buscar por ticker o nombre (ej: AAPL, Tesla)..."
              className="w-full h-8 pl-9 pr-3 rounded-lg bg-white/[0.04] border border-white/[0.06] text-white text-sm placeholder-zinc-600 focus:outline-none focus:bg-white/[0.06] focus:border-white/[0.1] transition-all"
            />
          </div>

          {/* Dropdown */}
          {showDropdown && results.length > 0 && (
            <div className="absolute top-full left-0 right-0 mt-1.5 bg-[rgba(16,16,19,0.92)] backdrop-blur-2xl border border-white/[0.08] rounded-xl overflow-hidden shadow-2xl shadow-black/50">
              {results.map((r, i) => (
                <button
                  key={r.ticker}
                  onClick={() => navigate(r.ticker)}
                  className={`w-full px-3.5 py-2.5 flex items-center gap-3 text-left transition-colors ${
                    i === selectedIdx ? "bg-[#0cc06c]/10" : "hover:bg-white/[0.03]"
                  }`}
                >
                  <span className="text-[#0cc06c] font-mono font-semibold text-xs w-12">{r.ticker}</span>
                  <span className="text-zinc-400 text-sm truncate">{r.name}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Ticker actual (orientación) — oculto en móvil para no apretar */}
        {symbol && (
          <div className="ml-auto shrink-0 hidden min-[561px]:flex items-center gap-2 px-3 py-1.5 rounded-full
            border border-[#0cc06c]/25 bg-[#0cc06c]/[0.08]">
            <span className="w-1.5 h-1.5 rounded-full bg-[#0cc06c] shadow-[0_0_8px_#0cc06c]" />
            <span className="font-mono text-[12.5px] font-semibold tracking-[0.06em] text-[#0cc06c]">{symbol}</span>
          </div>
        )}
      </div>
    </nav>
  );
}
