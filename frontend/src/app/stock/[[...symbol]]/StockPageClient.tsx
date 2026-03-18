"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Navbar from "@/components/Navbar";
import ScoreCard from "@/components/ScoreCard";
import MetricsGrid from "@/components/MetricsGrid";
import TabsSection from "@/components/TabsSection";
import { analyzeStock, formatPrice, formatNumber, formatPercent, getScoreColor, type StockAnalysis } from "@/lib/api";

// PDF download URL helper
const getPdfUrl = (sym: string) =>
  `${typeof window !== "undefined" && window.location.hostname !== "localhost" ? "" : "http://localhost:8000"}/api/pdf/${sym}`;

export default function StockPageClient() {
  const params = useParams();
  const symbol = (params.symbol as string)?.toUpperCase();
  const [data, setData] = useState<StockAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!symbol) return;
    setLoading(true);
    setError(null);
    analyzeStock(symbol)
      .then(setData)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, [symbol]);

  if (loading) return <LoadingSkeleton symbol={symbol} />;
  if (error) return <ErrorView symbol={symbol} error={error} />;
  if (!data) return null;

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
    <div className="min-h-screen bg-[#09090b]">
      <Navbar />

      <main className="max-w-6xl mx-auto px-4 sm:px-6 pt-8 pb-16">
        {/* ── Header ── */}
        <header className="mb-8 fade-up">
          <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
            <div>
              <div className="flex items-center gap-3 mb-1">
                <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
                  {data.profile.name}
                </h1>
                <span className="px-2 py-0.5 rounded-md text-[11px] font-mono font-semibold text-[#00d632] bg-[#00d632]/10 border border-[#00d632]/20">
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
          <div className="fade-up delay-1 mb-8 rounded-xl border border-white/[0.06] bg-white/[0.02] px-5 py-4">
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
                  background: range52pct > 70 ? "linear-gradient(90deg, #00d632, #4ade80)" :
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
                level={data.score.level}
                companyType={data.company_type}
                isGrowth={data.is_growth}
              />
            ) : (
              <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] flex items-center justify-center h-36 text-zinc-600 text-sm">
                Score no disponible
              </div>
            )}
          </div>
          <div className="lg:col-span-2">
            {data.key_metrics && <MetricsGrid metrics={data.key_metrics} />}
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
                  <div key={key} className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3">
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
        {data.errors && data.errors.length > 0 && (
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

/* ── Quick Summary — narrative explanation ── */
function QuickSummary({ data }: { data: StockAnalysis }) {
  const m = data.key_metrics || {};
  const price = data.price;
  const dcf = data.dcf;
  const score = data.score;
  const alerts = data.alerts;

  const insights: string[] = [];

  // Score insight
  if (score) {
    const pct = Math.round((score.total_score / score.max_score) * 100);
    if (pct >= 75) insights.push(`Obtiene una puntuación de ${pct}/100, indicando fundamentos sólidos.`);
    else if (pct >= 50) insights.push(`Puntuación de ${pct}/100 — fundamentos aceptables con áreas de mejora.`);
    else insights.push(`Puntuación baja de ${pct}/100 — se identifican varios riesgos.`);
  }

  // Valuation
  if (m.pe && m.pe > 0) {
    if (m.pe > 40) insights.push(`Cotiza a ${m.pe.toFixed(1)}x beneficios, lo que refleja altas expectativas de crecimiento.`);
    else if (m.pe > 20) insights.push(`P/E de ${m.pe.toFixed(1)}x — valoración moderada.`);
    else insights.push(`P/E de ${m.pe.toFixed(1)}x — valoración atractiva respecto al mercado.`);
  }

  // Profitability
  if (m.net_margin != null && m.net_margin > 0) {
    const nm = m.net_margin * 100;
    if (nm > 30) insights.push(`Margen neto excepcional del ${nm.toFixed(1)}%, superior al promedio del mercado.`);
    else if (nm > 10) insights.push(`Margen neto sólido del ${nm.toFixed(1)}%.`);
  }

  // DCF
  if (dcf?.fair_value && price) {
    const upside = ((dcf.fair_value - price) / price) * 100;
    if (upside > 15) insights.push(`El modelo DCF sugiere un valor justo de ${formatPrice(dcf.fair_value)}, un ${upside.toFixed(0)}% por encima del precio actual.`);
    else if (upside < -15) insights.push(`Según el DCF, el precio actual supera el valor justo estimado de ${formatPrice(dcf.fair_value)}.`);
  }

  // Risk count
  if (alerts) {
    const riskCount = (alerts.red_flags?.length || 0);
    const strengthCount = (alerts.strengths?.length || 0);
    if (riskCount > 0 && strengthCount > 0) {
      insights.push(`Se identifican ${riskCount} riesgo${riskCount > 1 ? "s" : ""} y ${strengthCount} fortaleza${strengthCount > 1 ? "s" : ""}.`);
    } else if (strengthCount > 3) {
      insights.push(`Se destacan ${strengthCount} fortalezas sin señales de riesgo significativas.`);
    }
  }

  if (insights.length === 0) return null;

  return (
    <div className="mb-10 rounded-xl border border-white/[0.06] bg-white/[0.015] px-6 py-5 fade-up delay-3">
      <h3 className="text-xs text-zinc-500 uppercase tracking-widest mb-3 font-medium">
        Resumen del análisis
      </h3>
      <div className="space-y-2">
        {insights.map((text, i) => (
          <p key={i} className="text-sm text-zinc-300 leading-relaxed">{text}</p>
        ))}
      </div>
    </div>
  );
}

/* ── Loading skeleton ── */
function LoadingSkeleton({ symbol }: { symbol: string }) {
  return (
    <div className="min-h-screen bg-[#09090b]">
      <Navbar />
      <main className="max-w-6xl mx-auto px-4 sm:px-6 pt-8 pb-16">
        <div className="flex justify-between mb-8">
          <div>
            <div className="skeleton h-8 w-56 mb-2" />
            <div className="skeleton h-4 w-40" />
          </div>
          <div className="text-right">
            <div className="skeleton h-8 w-28 mb-2 ml-auto" />
            <div className="skeleton h-3 w-20 ml-auto" />
          </div>
        </div>

        <div className="skeleton h-12 rounded-xl mb-8" />

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 mb-10">
          <div className="skeleton h-36 rounded-2xl" />
          <div className="lg:col-span-2 skeleton h-36 rounded-2xl" />
        </div>

        <div className="grid grid-cols-5 gap-2 mb-10">
          {[1,2,3,4,5].map(i => <div key={i} className="skeleton h-20 rounded-xl" />)}
        </div>

        <div className="flex gap-4 border-b border-white/[0.06] mb-8 pb-3">
          {[80, 96, 72, 104, 88].map((w, i) => (
            <div key={i} className="skeleton h-4 rounded" style={{ width: w }} />
          ))}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div className="skeleton h-48 rounded-xl" />
          <div className="skeleton h-48 rounded-xl" />
        </div>

        <div className="text-center py-12">
          <div className="inline-flex items-center gap-3 text-zinc-500">
            <svg className="w-4 h-4 animate-spin text-[#00d632]" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            <span className="text-sm">Analizando {symbol}...</span>
          </div>
        </div>
      </main>
    </div>
  );
}

/* ── Error view ── */
function ErrorView({ symbol, error }: { symbol: string; error: string }) {
  return (
    <div className="min-h-screen bg-[#09090b]">
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
