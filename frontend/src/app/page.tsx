"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { searchStocks, type SearchResult } from "@/lib/api";
import { rememberName } from "@/lib/stockNames";

const TRENDING = ["AAPL", "NVDA", "MSFT", "TSLA", "GOOGL", "AMZN", "META", "JPM"];

export default function Home() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [open, setOpen] = useState(false);
  const [selectedIdx, setSelectedIdx] = useState(-1);
  const timer = useRef<NodeJS.Timeout>(undefined);

  useEffect(() => {
    if (query.length < 1) { setResults([]); setOpen(false); return; }
    clearTimeout(timer.current);
    timer.current = setTimeout(async () => {
      const r = await searchStocks(query);
      setResults(r);
      setOpen(r.length > 0);
      setSelectedIdx(-1);
    }, 150);
  }, [query]);

  const go = (s: string, name?: string) => {
    rememberName(s, name); // el overlay mostrará el nombre al instante tras la nav
    setOpen(false); setQuery(""); router.push(`/stock/${s}`);
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 relative overflow-hidden bg-[#050507]">
      {/* Fondo + velo para contraste */}
      <div
        className="absolute inset-0 bg-cover bg-center pointer-events-none"
        style={{ backgroundImage: "url(/bg-home.webp)" }}
      />
      <div className="absolute inset-0 bg-[#050507]/30 pointer-events-none" />

      <div className="relative z-10 w-full max-w-2xl text-center">
        {/* Marca */}
        <div className="mb-9 fade-up">
          <img
            src="/logo.png"
            alt="Finanzer"
            className="h-20 sm:h-24 w-auto mx-auto mb-5"
            style={{ filter: "drop-shadow(0 8px 32px rgba(12,192,108,0.35))" }}
          />
          <h1 className="text-5xl sm:text-7xl font-extrabold tracking-[-0.03em] text-[#f5f5f7]">
            Finanzer
          </h1>
          <p className="mt-3 text-[#6e6e73] text-lg">
            Análisis fundamental inteligente
          </p>
        </div>

        {/* Búsqueda */}
        <div className="relative z-20 fade-up delay-1">
          <div className="relative">
            <svg
              className="absolute left-5 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-[#6e6e73] pointer-events-none"
              fill="none" stroke="currentColor" viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              type="text"
              value={query}
              onChange={e => setQuery(e.target.value)}
              onFocus={() => results.length > 0 && setOpen(true)}
              onKeyDown={e => {
                if (e.key === "ArrowDown") { e.preventDefault(); setSelectedIdx(i => Math.min(i + 1, results.length - 1)); }
                else if (e.key === "ArrowUp") { e.preventDefault(); setSelectedIdx(i => Math.max(i - 1, -1)); }
                else if (e.key === "Enter" && selectedIdx >= 0 && results[selectedIdx]) go(results[selectedIdx].ticker, results[selectedIdx].name);
                else if (e.key === "Enter" && query.trim()) go(query.trim().toUpperCase());
                else if (e.key === "Escape") setOpen(false);
              }}
              placeholder="Buscar por ticker o nombre (ej: AAPL, Tesla, Nvidia)…"
              enterKeyHint="search"
              className="w-full h-14 pl-13 pr-6 rounded-[18px] text-[17px] text-[#f5f5f7] placeholder:text-[#6e6e73]
                bg-[rgba(20,20,23,0.72)] border border-white/[0.08] backdrop-blur-2xl
                focus:outline-none focus:border-[#0cc06c]/50 focus:ring-4 focus:ring-[#0cc06c]/[0.12]
                focus:bg-[rgba(24,24,28,0.85)] transition-all duration-300"
              autoFocus
            />
          </div>
          {open && (
            <div className="absolute top-full left-0 right-0 mt-2 rounded-2xl overflow-hidden shadow-2xl shadow-black/60 z-50
              bg-[rgba(16,16,19,0.9)] border border-white/[0.08] backdrop-blur-2xl">
              {results.map((r, i) => (
                <button
                  key={r.ticker}
                  onClick={() => go(r.ticker, r.name)}
                  className={`press w-full px-5 py-3.5 flex items-center gap-4 text-left transition-colors ${
                    i === selectedIdx ? "bg-[#0cc06c]/10" : "hover:bg-white/[0.05]"
                  }`}
                >
                  <span className="text-[#0cc06c] font-mono font-semibold text-sm w-14 shrink-0">{r.ticker}</span>
                  <span className="text-[#a1a1a6] text-sm truncate">{r.name}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Trending — oculto mientras el dropdown está abierto para no chocar */}
        {!open && (
          <div className="mt-10 fade-up delay-2">
            <p className="text-[#6e6e73] text-[11px] uppercase tracking-[0.18em] mb-4 font-semibold">Trending</p>
            <div className="flex flex-wrap justify-center gap-2">
              {TRENDING.map(t => (
                <button
                  key={t}
                  onClick={() => go(t)}
                  className="press px-4 py-2.5 rounded-xl text-sm font-mono text-[#a1a1a6] border border-white/[0.06]
                    bg-white/[0.03] hover:text-white hover:bg-white/[0.07] hover:border-white/[0.12]
                    hover:-translate-y-0.5 transition-all duration-200"
                >
                  {t}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      <p className="absolute bottom-6 text-[#48484d] text-xs">
        Datos: Yahoo Finance · No es asesoría financiera
      </p>
    </div>
  );
}
