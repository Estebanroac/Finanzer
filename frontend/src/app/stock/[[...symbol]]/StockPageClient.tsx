"use client";

import { useEffect, useState } from "react";
import Navbar from "@/components/Navbar";
import ScoreCard from "@/components/ScoreCard";
import MetricsGrid from "@/components/MetricsGrid";
import TabsSection from "@/components/TabsSection";
import AnalyzeOverlay from "@/components/AnalyzeOverlay";
import { analyzeStock, formatPrice, getScoreColor, type StockAnalysis } from "@/lib/api";
import { recallName } from "@/lib/stockNames";

// PDF download URL helper — misma regla que api.ts: solo el dev server de
// Next (puerto 3000) apunta a localhost:8000; el resto es same-origin.
const getPdfUrl = (sym: string) =>
  `${typeof window !== "undefined" && window.location.port === "3000" ? "http://localhost:8000" : ""}/api/pdf/${sym}`;

export default function StockPageClient() {
  const [symbol, setSymbol] = useState<string>("");
  const [data, setData] = useState<StockAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // Nombre conocido al instante (sessionStorage de la búsqueda o mapa local),
  // para que el overlay muestre "Microsoft Corporation" desde el PRIMER FRAME
  // en vez de esperar la respuesta del API. Inicializador lazy = síncrono en el
  // mount, antes del primer paint.
  const [knownName] = useState<string | null>(() => {
    if (typeof window === "undefined") return null;
    const parts = window.location.pathname.split("/").filter(Boolean);
    return parts.length >= 2 && parts[0] === "stock" ? recallName(parts[1].toUpperCase()) : null;
  });

  // Extract symbol from URL pathname (works reliably in static export)
  useEffect(() => {
    const path = window.location.pathname; // e.g. /stock/AAPL or /stock/AAPL/
    const parts = path.split("/").filter(Boolean); // ["stock", "AAPL"]
    if (parts.length >= 2 && parts[0] === "stock") {
      setSymbol(parts[1].toUpperCase());
    }
  }, []);

  useEffect(() => {
    if (!symbol) return;
    setLoading(true);
    setError(null);
    analyzeStock(symbol)
      .then(setData)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, [symbol]);

  // Overlay de análisis: aparece exactamente al entrar/buscar y se disuelve
  // cuando los datos del backend están listos Y pintados debajo. key por
  // símbolo para que una nueva búsqueda reinicie la secuencia; posición
  // estable (primer hijo del fragment) para que la transición carga->contenido
  // no lo re-monte a mitad de animación.
  const [overlayGone, setOverlayGone] = useState(false);
  useEffect(() => { setOverlayGone(false); }, [symbol]);

  const overlay = !overlayGone && !error && (
    <AnalyzeOverlay
      key={symbol || "init"}
      symbol={symbol}
      companyName={data?.profile?.name ?? knownName}
      done={!!data && !loading}
      onFinished={() => setOverlayGone(true)}
    />
  );

  return (
    <>
      {overlay}
      {error ? (
        <ErrorView symbol={symbol} error={error} />
      ) : data ? (
        <AnalysisContent data={data} symbol={symbol} />
      ) : (
        <div className="min-h-screen bg-[#050507]" />
      )}
    </>
  );
}

/* ── Contenido del análisis (pinta bajo el overlay antes de la disolución) ── */
function AnalysisContent({ data, symbol }: { data: StockAnalysis; symbol: string }) {
  const m = data.key_metrics || {};
  const hi52 = m.price_52w_high;
  const lo52 = m.price_52w_low;
  const price = data.price;

  // 52-week position (0-100%)
  let range52pct = 50;
  if (hi52 && lo52 && price && hi52 !== lo52) {
    range52pct = Math.max(0, Math.min(100, ((price - lo52) / (hi52 - lo52)) * 100));
  }

  return (
    <div className="min-h-screen relative">
      {/* Analysis background + velo: el arte del fondo (gráfico con glow) no
          debe competir con los datos — se atenúa y se deja respirar en bordes */}
      <div
        className="fixed inset-0 -z-10 bg-[#050507] bg-cover bg-center"
        style={{ backgroundImage: "url(/bg-analysis.webp)" }}
      />
      <div className="fixed inset-0 -z-10 bg-[#050507]/60 pointer-events-none" />
      <Navbar symbol={symbol} />

      <main className="max-w-6xl mx-auto px-4 sm:px-6 pt-8 pb-16">
        {/* ── Header ── */}
        <header className="mb-8 fade-up">
          <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
            <div>
              <div className="flex items-center gap-3 mb-1">
                <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
                  {data.profile.name}
                </h1>
                <span className="px-2 py-0.5 rounded-md text-[11px] font-mono font-semibold text-[#0cc06c] bg-[#0cc06c]/10 border border-[#0cc06c]/20">
                  {symbol}
                </span>
              </div>
              <p className="text-sm text-zinc-500">
                {data.profile.sector} · {data.profile.industry}
                {data.profile.country && data.profile.country !== "Unknown" && ` · ${data.profile.country}`}
              </p>
            </div>

            <div className="sm:text-right flex flex-col items-end gap-2">
              <div>
                <div className="text-3xl font-bold text-white tabular-nums">
                  {formatPrice(price)}
                </div>
                <div className="text-xs text-zinc-500 mt-0.5">
                  {data.profile.currency} · {data.profile.exchange}
                </div>
              </div>
              <a
                href={getPdfUrl(symbol)}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-zinc-300 bg-white/[0.04] border border-white/[0.08] hover:bg-white/[0.08] transition-colors"
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                Descargar PDF
              </a>
            </div>
          </div>
        </header>

        {/* ── 52-Week Range ── */}
        {hi52 && lo52 && (
          <div className="fade-up delay-1 mb-8 rounded-xl border border-white/[0.06] bg-[#0a0a0d]/85 px-5 py-4">
            <div className="flex items-center justify-between text-xs text-zinc-500 mb-2">
              <span>Rango 52 semanas</span>
              <span>
                {formatPrice(lo52)} — {formatPrice(hi52)}
              </span>
            </div>
            <div className="relative h-1.5 bg-white/[0.06] rounded-full">
              <div
                className="absolute top-0 left-0 h-full rounded-full"
                style={{
                  width: `${range52pct}%`,
                  background: range52pct > 70 ? "#0cc06c" :
                             range52pct < 30 ? "linear-gradient(90deg, #ff4d4d, #f97316)" :
                             "linear-gradient(90deg, #fbbf24, #f59e0b)",
                }}
              />
              <div
                className="absolute top-1/2 -translate-y-1/2 w-3 h-3 rounded-full bg-white border-2 border-zinc-800 shadow-lg"
                style={{ left: `${range52pct}%`, marginLeft: "-6px" }}
              />
            </div>
            <div className="flex justify-between text-[10px] text-zinc-600 mt-1">
              <span>Mínimo</span>
              <span className="text-zinc-400 font-medium">
                {range52pct > 70 ? "Cerca del máximo" : range52pct < 30 ? "Cerca del mínimo" : "Rango medio"}
              </span>
              <span>Máximo</span>
            </div>
          </div>
        )}

        {/* ── Score + Key Metrics ── */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 mb-6 fade-up delay-2">
          <div>
            {data.score ? (
              <ScoreCard
                score={data.score.total_score}
                maxScore={data.score.max_score}
                companyType={data.company_type}
                isGrowth={data.is_growth}
              />
            ) : (
              <div className="rounded-2xl border border-white/[0.06] bg-[#0a0a0d]/85 flex items-center justify-center h-36 text-zinc-600 text-sm">
                Score no disponible
              </div>
            )}
          </div>
          <div className="lg:col-span-2">
            {data.key_metrics && (
              <MetricsGrid metrics={data.key_metrics} sector={data.sector_info?.mapped_sector} />
            )}
          </div>
        </div>

        {/* ── Score Breakdown (if available) — quick summary ── */}
        {data.score?.breakdown && Object.keys(data.score.breakdown).length > 0 && (
          <div className="mb-10 fade-up delay-3">
            <h3 className="text-xs text-zinc-500 uppercase tracking-widest mb-3 font-medium">
              Desglose del score
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
              {Object.entries(data.score.breakdown).map(([key, cat]) => {
                const pct = cat.max > 0 ? (cat.score / cat.max) * 100 : 0;
                const color = getScoreColor(pct);
                return (
                  <div key={key} className="rounded-xl border border-white/[0.06] bg-[#0a0a0d]/85 p-3">
                    <div className="text-[10px] text-zinc-500 uppercase tracking-wider mb-1 truncate">
                      {key}
                    </div>
                    <div className="flex items-baseline gap-1">
                      <span className="text-lg font-bold tabular-nums" style={{ color }}>
                        {cat.score}
                      </span>
                      <span className="text-xs text-zinc-600">/{cat.max}</span>
                    </div>
                    <div className="mt-2 h-1 bg-white/[0.04] rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full"
                        style={{ width: `${pct}%`, backgroundColor: color }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* ── Quick Summary Box ── */}
        <QuickSummary data={data} />

        {/* ── Tabs ── */}
        <div className="fade-up delay-4">
          <TabsSection data={data} />
        </div>

        {/* ── Errors from backend ── */}
        {Array.isArray(data.errors) && data.errors.length > 0 && (
          <div className="mt-8 rounded-xl border border-amber-500/20 bg-amber-500/5 px-5 py-4">
            <h4 className="text-xs text-amber-400 font-medium uppercase tracking-wider mb-2">
              Advertencias del análisis
            </h4>
            <ul className="space-y-1">
              {data.errors.map((err, i) => (
                <li key={i} className="text-xs text-zinc-400">{err}</li>
              ))}
            </ul>
          </div>
        )}
      </main>

      <footer className="border-t border-white/[0.04] py-6 text-center text-xs text-zinc-700">
        Datos: Yahoo Finance · No es asesoría financiera
      </footer>
    </div>
  );
}

/* ── Resumen del análisis: bloques etiquetados adaptativos (como el PDF) ── */
function QuickSummary({ data }: { data: StockAnalysis }) {
  const m = data.key_metrics || {};
  const price = data.price;
  const dcf = data.dcf;
  const score = data.score;
  const alerts = data.alerts;

  const items: Array<{ label: string; text: React.ReactNode }> = [];

  if (score) {
    const pct = Math.round((score.total_score / score.max_score) * 100);
    items.push({
      label: "Puntuación",
      text: <>Obtiene <b className="text-white">{pct}/100</b>{" "}
        {pct >= 75 ? "— fundamentos sólidos en la mayoría de categorías."
          : pct >= 50 ? "— fundamentos aceptables con áreas de mejora."
          : "— se identifican varios frentes de riesgo."}</>,
    });
  }

  if (m.pe && m.pe > 0) {
    items.push({
      label: "Valoración",
      text: <>El mercado paga <b className="text-white">{m.pe.toFixed(1)}x</b> beneficios
        {m.pe > 40 ? " — expectativas de crecimiento muy exigentes."
          : m.pe > 20 ? " — valoración moderada." : " — valoración atractiva."}</>,
    });
  }

  if (m.roic_wacc_spread != null) {
    const sp = m.roic_wacc_spread * 100;
    items.push({
      label: "Creación de valor",
      text: <>ROIC − WACC de{" "}
        <b style={{ color: sp >= 0 ? "#0cc06c" : "#ff453a" }}>{sp >= 0 ? "+" : ""}{sp.toFixed(1)} pp</b>
        {sp >= 3 ? " — cada dólar reinvertido crea valor." : sp >= 0 ? " — apenas cubre su costo de capital." : " — no cubre su costo de capital."}</>,
    });
  } else if (m.net_margin != null && m.net_margin > 0.1) {
    items.push({
      label: "Rentabilidad",
      text: <>Margen neto {m.net_margin > 0.3 ? "excepcional" : "sólido"} del{" "}
        <b className="text-white">{(m.net_margin * 100).toFixed(1)}%</b>.</>,
    });
  }

  if (dcf?.fair_value && price) {
    const upside = ((dcf.fair_value - price) / price) * 100;
    items.push({
      label: "Valor intrínseco",
      text: upside > 15
        ? <>El DCF estima <b className="text-white">{formatPrice(dcf.fair_value)}</b> — un potencial teórico de <b style={{ color: "#0cc06c" }}>+{upside.toFixed(0)}%</b>.</>
        : upside < -15
        ? <>El precio supera el valor justo estimado de <b className="text-white">{formatPrice(dcf.fair_value)}</b> — el DCF exige escenarios optimistas.</>
        : <>Cotiza en torno a su valor justo estimado (<b className="text-white">{formatPrice(dcf.fair_value)}</b>).</>,
    });
  }

  const nRed = alerts?.red_flags?.length || 0;
  const nWarn = alerts?.warnings?.length || 0;
  const nStr = alerts?.strengths?.length || 0;
  if (nRed + nWarn + nStr > 0) {
    items.push({
      label: "Balance de señales",
      text: <>
        <b style={{ color: "#0cc06c" }}>{nStr}</b> fortaleza{nStr !== 1 && "s"} ·{" "}
        <b style={{ color: "#ffd60a" }}>{nWarn}</b> advertencia{nWarn !== 1 && "s"} ·{" "}
        <b style={{ color: "#ff453a" }}>{nRed}</b> riesgo{nRed !== 1 && "s"}
      </>,
    });
  }

  if (items.length === 0) return null;

  return (
    <div className="mb-10 rounded-xl border border-white/[0.06] bg-[#0a0a0d]/85 px-6 py-5 fade-up delay-3">
      <h3 className="text-xs text-zinc-500 uppercase tracking-widest mb-4 font-medium">
        Resumen del análisis
      </h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-10 gap-y-4">
        {items.map(({ label, text }) => (
          <div key={label}>
            <div className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#0cc06c] mb-1">
              {label}
            </div>
            <p className="text-sm text-zinc-300 leading-relaxed">{text}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Error view ── */
function ErrorView({ symbol, error }: { symbol: string; error: string }) {
  return (
    <div className="min-h-screen relative">
      {/* Analysis background */}
      <div
        className="fixed inset-0 -z-10 bg-[#09090b] bg-cover bg-center"
        style={{ backgroundImage: "url(/bg-analysis.webp)" }}
      />
      <Navbar />
      <div className="max-w-lg mx-auto px-4 py-32 text-center">
        <div className="w-16 h-16 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center mx-auto mb-6">
          <svg className="w-7 h-7 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
        </div>
        <h2 className="text-xl font-bold text-white mb-2">No se pudo analizar {symbol}</h2>
        <p className="text-sm text-zinc-500 mb-8">{error}</p>
        <a
          href="/"
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium text-white bg-white/[0.04] border border-white/[0.06] hover:bg-white/[0.08] transition-colors"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          Volver al inicio
        </a>
      </div>
    </div>
  );
}
