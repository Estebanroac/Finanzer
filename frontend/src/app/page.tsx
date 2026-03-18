"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { searchStocks, type SearchResult } from "@/lib/api";

const TRENDING = ["AAPL", "NVDA", "MSFT", "TSLA", "GOOGL", "AMZN", "META", "JPM"];

export default function Home() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [open, setOpen] = useState(false);
  const timer = useRef<NodeJS.Timeout>(undefined);

  useEffect(() => {
    if (query.length < 1) { setResults([]); setOpen(false); return; }
    clearTimeout(timer.current);
    timer.current = setTimeout(async () => {
      const r = await searchStocks(query);
      setResults(r);
      setOpen(r.length > 0);
    }, 150);
  }, [query]);

  const go = (s: string) => { setOpen(false); setQuery(""); router.push(`/stock/${s}`); };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 relative overflow-hidden">
      {/* Subtle gradient orb */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full bg-[#00d632]/[0.03] blur-[120px] pointer-events-none" />

      <div className="relative z-10 w-full max-w-2xl text-center">
        {/* Logo */}
        <div className="mb-8 fade-up">
          <h1 className="text-5xl sm:text-7xl font-extrabold tracking-tight text-white">
            Finanzer
          </h1>
          <p className="mt-3 text-zinc-500 text-lg">
            Análisis fundamental inteligente
          </p>
        </div>

        {/* Search */}
        <div className="relative fade-up delay-1">
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onFocus={() => results.length > 0 && setOpen(true)}
            onKeyDown={e => {
              if (e.key === "Enter" && query.trim()) go(query.trim().toUpperCase());
              if (e.key === "Escape") setOpen(false);
            }}
            placeholder="Buscar por ticker o nombre (ej: AAPL, Tesla, Nvidia)..."
            className="w-full h-14 px-6 rounded-2xl bg-zinc-900 border border-zinc-800 text-white text-lg placeholder:text-zinc-600 focus:outline-none focus:border-zinc-600 focus:ring-1 focus:ring-zinc-700 transition-all"
            autoFocus
          />
          {open && (
            <div className="absolute top-full left-0 right-0 mt-2 bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden shadow-2xl z-50">
              {results.map(r => (
                <button key={r.ticker} onClick={() => go(r.ticker)}
                  className="w-full px-6 py-3.5 flex items-center gap-4 hover:bg-zinc-800/60 transition-colors text-left">
                  <span className="text-[#00d632] font-mono font-bold text-sm w-14">{r.ticker}</span>
                  <span className="text-zinc-300 text-sm truncate">{r.name}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Trending */}
        <div className="mt-10 fade-up delay-2">
          <p className="text-zinc-600 text-xs uppercase tracking-widest mb-4">Trending</p>
          <div className="flex flex-wrap justify-center gap-2">
            {TRENDING.map(t => (
              <button key={t} onClick={() => go(t)}
                className="px-4 py-2 rounded-lg text-sm font-mono text-zinc-400 hover:text-white hover:bg-zinc-800/60 border border-transparent hover:border-zinc-700/50 transition-all duration-200">
                {t}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Footer */}
      <p className="absolute bottom-6 text-zinc-700 text-xs">
        Datos: Yahoo Finance · No es asesoría financiera
      </p>
    </div>
  );
}
