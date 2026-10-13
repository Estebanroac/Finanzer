"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import StockHeader from "@/components/StockHeader";
import SummarySection from "@/components/SummarySection";
import TabsSection from "@/components/TabsSection";
import AnalyzeOverlay from "@/components/AnalyzeOverlay";
import { analyzeStock, type StockAnalysis } from "@/lib/api";
import { recallName } from "@/lib/stockNames";

const noop = () => () => {};

/** Símbolo desde la URL (/stock/AAPL): funciona en el export estático. */
function symbolFromPath(path: string): string {
  const [head, sym] = path.split("/").filter(Boolean);
  return head === "stock" && sym ? sym.toUpperCase() : "";
}

type Result = { symbol: string; data?: StockAnalysis; error?: string };

export default function StockPageClient() {
  const symbol = useSyncExternalStore(noop, () => symbolFromPath(window.location.pathname), () => "");
  // Nombre conocido al instante (búsqueda previa o mapa local) para el overlay.
  const knownName = symbol ? recallName(symbol) : null;
  const [result, setResult] = useState<Result | null>(null);
  const [overlayDoneFor, setOverlayDoneFor] = useState<string | null>(null);

  useEffect(() => {
    if (!symbol) return;
    let alive = true;
    analyzeStock(symbol)
      .then((data) => { if (alive) setResult({ symbol, data }); })
      .catch((err: Error) => { if (alive) setResult({ symbol, error: err.message }); });
    return () => { alive = false; };
  }, [symbol]);

  const current = result?.symbol === symbol ? result : null;
  const data = current?.data ?? null;
  const error = current?.error ?? null;

  // Overlay de análisis: se disuelve cuando los datos están pintados debajo.
  const overlay = overlayDoneFor !== symbol && !error && (
    <AnalyzeOverlay
      key={symbol || "init"}
      symbol={symbol}
      companyName={data?.profile?.name ?? knownName}
      done={!!data}
      onFinished={() => setOverlayDoneFor(symbol)}
    />
  );

  return (
    <>
      {overlay}
      {error ? (
        <ErrorView symbol={symbol} error={error} />
      ) : data ? (
        <AnalysisContent data={data} />
      ) : (
        <div className="min-h-screen bg-[#050507]" />
      )}
    </>
  );
}

function AnalysisContent({ data }: { data: StockAnalysis }) {
  const D = data.display;
  return (
    <div className="min-h-screen relative">
      <div className="fixed inset-0 -z-10 bg-[#050507] bg-cover bg-center" style={{ backgroundImage: "url(/bg-analysis.webp)" }} />
      <div className="fixed inset-0 -z-10 bg-[#050507]/70 pointer-events-none" />
      <Navbar symbol={data.symbol} />

      <main className="max-w-6xl mx-auto px-4 sm:px-6 pt-8 pb-16">
        <StockHeader data={data} />
        <h2 className="fz-section-title fade-up delay-3">Resumen ejecutivo</h2>
        <SummarySection display={D} />
        <div className="fade-up delay-4">
          <TabsSection data={data} />
        </div>

        {data.errors.length > 0 && (
          <div className="mt-8 rounded-xl border border-amber-500/20 bg-amber-500/5 px-5 py-4">
            <h4 className="text-xs text-amber-400 font-medium uppercase tracking-wider mb-2">Advertencias del análisis</h4>
            <ul className="space-y-1">
              {data.errors.map((err, i) => <li key={i} className="text-xs text-zinc-400">{err}</li>)}
            </ul>
          </div>
        )}
      </main>

      <footer className="border-t border-white/[0.04] py-6 px-4 text-center text-xs text-zinc-600 space-y-2">
        <p className="max-w-3xl mx-auto leading-relaxed">
          <b className="text-zinc-500">Metodología.</b> Ratios TTM y del último ejercicio con {D.methodology.models_text} y
          dos puntuaciones de 0 a 100: calidad del negocio y atractivo del precio (contraído hacia 50 según la confianza
          del veredicto). Las lecturas salen del mismo motor que el informe PDF.
        </p>
        <p>Datos: Yahoo Finance · No es asesoría financiera</p>
      </footer>
    </div>
  );
}

function ErrorView({ symbol, error }: { symbol: string; error: string }) {
  return (
    <div className="min-h-screen relative">
      <div className="fixed inset-0 -z-10 bg-[#09090b] bg-cover bg-center" style={{ backgroundImage: "url(/bg-analysis.webp)" }} />
      <Navbar />
      <div className="max-w-lg mx-auto px-4 py-32 text-center">
        <div className="w-16 h-16 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center mx-auto mb-6">
          <svg className="w-7 h-7 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
        </div>
        <h2 className="text-xl font-bold text-white mb-2">No se pudo analizar {symbol}</h2>
        <p className="text-sm text-zinc-500 mb-8">{error}</p>
        <Link href="/" prefetch={false} className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium text-white bg-white/[0.04] border border-white/[0.06] hover:bg-white/[0.08] transition-colors">
          Volver al inicio
        </Link>
      </div>
    </div>
  );
}
