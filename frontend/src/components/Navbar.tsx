"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter, usePathname } from "next/navigation";
import { searchStocks, SearchResult } from "@/lib/api";

export default function Navbar() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [selectedIdx, setSelectedIdx] = useState(-1);
  const router = useRouter();
  const pathname = usePathname();
  const inputRef = useRef<HTMLInputElement>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<NodeJS.Timeout>(undefined);

  const isHome = pathname === "/";

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
    <nav className="sticky top-0 z-50 backdrop-blur-2xl bg-[#09090b]/80 border-b border-white/[0.04]">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 h-14 flex items-center gap-5">
        {/* Logo */}
        <a href="/" className="shrink-0 group flex items-center gap-2">
          <span className="text-[15px] font-bold text-white tracking-tight group-hover:text-[#00d632] transition-colors">
            Finanzer
          </span>
        </a>

        {/* Divider */}
        <div className="w-px h-5 bg-white/[0.06]" />

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
            <div className="absolute top-full left-0 right-0 mt-1.5 bg-[#111113] border border-white/[0.08] rounded-xl overflow-hidden shadow-2xl shadow-black/50">
              {results.map((r, i) => (
                <button
                  key={r.ticker}
                  onClick={() => navigate(r.ticker)}
                  className={`w-full px-3.5 py-2.5 flex items-center gap-3 text-left transition-colors ${
                    i === selectedIdx ? "bg-white/[0.06]" : "hover:bg-white/[0.03]"
                  }`}
                >
                  <span className="text-[#00d632] font-mono font-semibold text-xs w-12">{r.ticker}</span>
                  <span className="text-zinc-400 text-sm truncate">{r.name}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </nav>
  );
}
