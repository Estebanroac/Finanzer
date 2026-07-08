"use client";

import { formatMultiple, formatPercent, formatNumber, getScoreColor, type StockAnalysis } from "@/lib/api";
import InfoTooltip from "@/components/InfoTooltip";
import { COMPARATIVE } from "@/lib/tooltips";
import { getSectorBenchmarks } from "@/lib/sectorBench";
import { useGrow } from "@/lib/useGrow";

interface CompMetric {
  label: string;
  value: number | null;
  sectorAvg: number | null;
  format: "multiple" | "percent" | "number";
  higherIsBetter: boolean;
  hint?: string;
}

function fmt(val: number | null, format: string): string {
  if (val == null) return "N/A";
  if (format === "multiple") return formatMultiple(val);
  if (format === "percent") return formatPercent(val);
  return formatNumber(val);
}

export default function ComparativeTab({ data }: { data: StockAnalysis }) {
  const m = data.key_metrics;
  const sector = data.sector_info?.sector || data.profile.sector || "N/A";

  // Sector average benchmarks (approximate industry averages)
  const sectorBenchmarks = getSectorBenchmarks(data.sector_info?.mapped_sector || "default");

  const valuationMetrics: CompMetric[] = [
    { label: "P/E (TTM)", value: m.pe, sectorAvg: sectorBenchmarks.pe, format: "multiple", higherIsBetter: false, hint: "Precio / Beneficio" },
    { label: "Forward P/E", value: m.forward_pe, sectorAvg: sectorBenchmarks.forward_pe, format: "multiple", higherIsBetter: false, hint: "Estimado" },
    { label: "P/B", value: m.pb, sectorAvg: sectorBenchmarks.pb, format: "multiple", higherIsBetter: false, hint: "Precio / Valor en Libros" },
    { label: "EV/EBITDA", value: m.ev_ebitda, sectorAvg: sectorBenchmarks.ev_ebitda, format: "multiple", higherIsBetter: false },
    { label: "P/FCF", value: m.pfcf, sectorAvg: sectorBenchmarks.pfcf, format: "multiple", higherIsBetter: false },
    { label: "PEG", value: m.peg, sectorAvg: sectorBenchmarks.peg, format: "multiple", higherIsBetter: false },
  ];

  const profitMetrics: CompMetric[] = [
    { label: "ROE", value: m.roe, sectorAvg: sectorBenchmarks.roe, format: "percent", higherIsBetter: true },
    { label: "ROA", value: m.roa, sectorAvg: sectorBenchmarks.roa, format: "percent", higherIsBetter: true },
    { label: "ROIC", value: m.roic, sectorAvg: sectorBenchmarks.roic, format: "percent", higherIsBetter: true },
    { label: "Margen Neto", value: m.net_margin, sectorAvg: sectorBenchmarks.net_margin, format: "percent", higherIsBetter: true },
    { label: "Margen Operativo", value: m.operating_margin, sectorAvg: sectorBenchmarks.operating_margin, format: "percent", higherIsBetter: true },
    { label: "Margen Bruto", value: m.gross_margin, sectorAvg: sectorBenchmarks.gross_margin, format: "percent", higherIsBetter: true },
  ];

  const healthMetrics: CompMetric[] = [
    { label: "Current Ratio", value: m.current_ratio, sectorAvg: sectorBenchmarks.current_ratio, format: "multiple", higherIsBetter: true },
    { label: "D/E", value: m.de, sectorAvg: sectorBenchmarks.de, format: "multiple", higherIsBetter: false },
    { label: "Cobertura Intereses", value: m.interest_coverage, sectorAvg: sectorBenchmarks.interest_coverage, format: "multiple", higherIsBetter: true },
    { label: "FCF Yield", value: m.fcf_yield, sectorAvg: sectorBenchmarks.fcf_yield, format: "percent", higherIsBetter: true },
  ];

  const growthMetrics: CompMetric[] = [
    { label: "Crec. Revenue", value: m.revenue_growth, sectorAvg: sectorBenchmarks.revenue_growth, format: "percent", higherIsBetter: true },
    { label: "Crec. Earnings", value: m.earnings_growth, sectorAvg: sectorBenchmarks.earnings_growth, format: "percent", higherIsBetter: true },
  ];

  return (
    <div className="space-y-8">
      {/* Contexto + leyenda del eje */}
      <div className="rounded-xl border border-white/[0.06] bg-[#0a0a0d]/85 px-6 py-4">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-2.5 h-2.5 rounded-full bg-[#0cc06c]" />
          <div className="flex-1">
            <span className="text-sm text-white font-medium">{data.profile.name}</span>
            <span className="text-xs text-zinc-500 ml-2">vs sector: {sector}</span>
          </div>
          <InfoTooltip content={COMPARATIVE.sector_comparison} size="md" />
        </div>
        <div className="cmp-legend !mb-0">
          <span className="cmp-lg cmp-lg-neg"><i />Peor</span>
          <span className="cmp-axis-label">Sector · 0%</span>
          <span className="cmp-lg cmp-lg-pos"><i />Mejor</span>
        </div>
      </div>

      {/* Barras divergentes por sección */}
      <ComparisonSection title="Valoración" subtitle="Múltiplos de precio vs mediana del sector" metrics={valuationMetrics} />
      <ComparisonSection title="Rentabilidad" subtitle="Retornos y márgenes vs mediana del sector" metrics={profitMetrics} />
      <ComparisonSection title="Solidez Financiera" subtitle="Liquidez y apalancamiento vs mediana del sector" metrics={healthMetrics} />
      <ComparisonSection title="Crecimiento" subtitle="Tasas de crecimiento vs mediana del sector" metrics={growthMetrics} />

      {/* Summary insight */}
      <ComparisonSummary valuationMetrics={valuationMetrics} profitMetrics={profitMetrics} healthMetrics={healthMetrics} />
    </div>
  );
}

/* Barras divergentes: el eje central = el sector; mejor crece a la derecha
   (verde), peor a la izquierda (rojo). |desviación| 60% llena el semieje
   (cap); piso de 6% para que toda desviación no nula sea visible. */
const CAP = 60;
const FLOOR = 6;

function ComparisonSection({ title, subtitle, metrics }: { title: string; subtitle: string; metrics: CompMetric[] }) {
  const grown = useGrow();
  const rows = metrics.filter(m => m.value != null);
  if (rows.length === 0) return null;

  return (
    <div>
      <div className="mb-3">
        <h4 className="text-xs text-zinc-500 uppercase tracking-widest font-medium">{title}</h4>
        <p className="text-[10px] text-zinc-600 mt-0.5">{subtitle}</p>
      </div>
      <div className="rounded-xl border border-white/[0.06] bg-[#0a0a0d]/85 px-5 py-2 divide-y divide-white/[0.04]">
        {rows.map((m, i) => {
          const hasBench = m.sectorAvg != null && m.sectorAvg !== 0;
          if (!hasBench) {
            return (
              <div key={i} className="cmp-row">
                <div className="cmp-head">
                  <span className="cmp-k">{m.label}</span>
                  <span className="cmp-val">{fmt(m.value, m.format)}</span>
                </div>
              </div>
            );
          }
          const diff = ((m.value! - m.sectorAvg!) / Math.abs(m.sectorAvg!)) * 100;
          // En métricas donde MENOR es mejor (P/E, P/B, EV/EBITDA, P/FCF, PEG, D/E), un
          // valor <= 0 (EPS/FCF/crecimiento/equity negativos) da un diff muy negativo que
          // goodness=-diff pintaría VERDE ("más barato/mejor") — engañoso: un múltiplo
          // negativo es MALO. Forzamos señal negativa (roja) antes del cálculo de goodness.
          const negMultiple = !m.higherIsBetter && m.value! <= 0;
          const goodness = m.higherIsBetter ? diff : -diff;   // + = mejor que el sector
          const isBetter = negMultiple ? false : goodness >= 0;
          const dev = Math.abs(goodness);
          let barPct = negMultiple ? FLOOR : Math.min(100, (dev / CAP) * 100);
          if (!negMultiple && dev > 0.5) barPct = Math.max(FLOOR, barPct);
          const note = negMultiple
            ? "múltiplo negativo"
            : m.higherIsBetter
            ? (diff >= 0 ? "por encima del sector" : "por debajo del sector")
            : (diff >= 0 ? "más caro que el sector" : "más barato que el sector");

          return (
            <div key={i} className="cmp-row">
              <div className="cmp-head">
                <span className="cmp-k">{m.label}</span>
                <span>
                  <span className="cmp-val">{fmt(m.value, m.format)}</span>
                  <span className="cmp-vs">vs {fmt(m.sectorAvg, m.format)}</span>
                </span>
              </div>
              <div className="cmp-track">
                <div
                  className={`cmp-bar ${isBetter ? "cmp-pos" : "cmp-neg"}`}
                  style={{ width: grown ? `${barPct / 2}%` : 0 }}
                />
                <div className="cmp-mid" />
              </div>
              <span className={`cmp-dev ${isBetter ? "pos" : "neg"}`}>
                {diff >= 0 ? "+" : "−"}{Math.abs(diff).toFixed(0)}%{" "}
                <span className="cmp-dev-note">{note}</span>
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ComparisonSummary({ valuationMetrics, profitMetrics, healthMetrics }: {
  valuationMetrics: CompMetric[];
  profitMetrics: CompMetric[];
  healthMetrics: CompMetric[];
}) {
  const allMetrics = [...valuationMetrics, ...profitMetrics, ...healthMetrics];
  let better = 0, worse = 0, total = 0;

  allMetrics.forEach(m => {
    if (m.value != null && m.sectorAvg != null && m.sectorAvg !== 0) {
      total++;
      const diff = ((m.value - m.sectorAvg) / Math.abs(m.sectorAvg)) * 100;
      // Un múltiplo negativo (lower-is-better con value <= 0) NO supera al sector:
      // el diff negativo lo contaría como "mejor". Se cuenta como peor.
      const negMultiple = !m.higherIsBetter && m.value <= 0;
      const isBetter = negMultiple ? false : (m.higherIsBetter ? diff > 5 : diff < -5);
      const isWorse = negMultiple ? true : (m.higherIsBetter ? diff < -5 : diff > 5);
      if (isBetter) better++;
      if (isWorse) worse++;
    }
  });

  if (total === 0) return null;

  const pct = Math.round((better / total) * 100);
  const color = getScoreColor(pct);

  return (
    <div className="rounded-xl border border-white/[0.06] bg-[#0a0a0d]/85 px-6 py-5">
      <h4 className="text-xs text-zinc-500 uppercase tracking-widest mb-3 font-medium">
        Resumen comparativo
      </h4>
      <div className="flex items-center gap-4 mb-3">
        <div className="text-3xl font-black tabular-nums" style={{ color }}>
          {better}/{total}
        </div>
        <div>
          <p className="text-sm text-zinc-300">métricas superan al sector</p>
          <p className="text-xs text-zinc-500 mt-0.5">
            {better > worse
              ? "La empresa muestra ventajas competitivas frente a su sector."
              : better === worse
              ? "Rendimiento en línea con el promedio sectorial."
              : "Varias métricas están por debajo del promedio del sector."}
          </p>
        </div>
      </div>
      <div className="h-1.5 bg-white/[0.04] rounded-full overflow-hidden">
        <div className="h-full rounded-full" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
    </div>
  );
}
