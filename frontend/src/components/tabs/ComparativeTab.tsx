"use client";

import { formatMultiple, formatPercent, formatNumber, getScoreColor, type StockAnalysis } from "@/lib/api";
import InfoTooltip from "@/components/InfoTooltip";
import { COMPARATIVE } from "@/lib/tooltips";
import { getSectorBenchmarks } from "@/lib/sectorBench";

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
      {/* Sector context */}
      <div className="rounded-xl border border-white/[0.06] bg-[#0a0a0d]/85 px-6 py-4 flex items-center gap-3">
        <div className="w-2.5 h-2.5 rounded-full bg-[#3b82f6]" />
        <div className="flex-1">
          <span className="text-sm text-white font-medium">{data.profile.name}</span>
          <span className="text-xs text-zinc-500 ml-2">vs Sector: {sector}</span>
        </div>
        <InfoTooltip content={COMPARATIVE.sector_comparison} size="md" />
      </div>

      {/* Comparison tables */}
      <ComparisonSection title="Valoración" subtitle="Múltiplos de precio vs promedio del sector" metrics={valuationMetrics} />
      <ComparisonSection title="Rentabilidad" subtitle="Retornos y márgenes vs promedio del sector" metrics={profitMetrics} />
      <ComparisonSection title="Solidez Financiera" subtitle="Liquidez y apalancamiento vs promedio del sector" metrics={healthMetrics} />
      <ComparisonSection title="Crecimiento" subtitle="Tasas de crecimiento vs promedio del sector" metrics={growthMetrics} />

      {/* Summary insight */}
      <ComparisonSummary valuationMetrics={valuationMetrics} profitMetrics={profitMetrics} healthMetrics={healthMetrics} />
    </div>
  );
}

function ComparisonSection({ title, subtitle, metrics }: { title: string; subtitle: string; metrics: CompMetric[] }) {
  return (
    <div>
      <div className="mb-3">
        <h4 className="text-xs text-zinc-500 uppercase tracking-widest font-medium">{title}</h4>
        <p className="text-[10px] text-zinc-600 mt-0.5">{subtitle}</p>
      </div>
      <div className="rounded-xl border border-white/[0.06] overflow-hidden bg-[#0a0a0d]/85">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/[0.06] bg-[#0a0a0d]/70">
              <th className="text-left px-3 py-3 sm:px-5 text-xs text-zinc-500 font-medium">Métrica</th>
              <th className="text-right px-3 py-3 sm:px-5 text-xs text-zinc-500 font-medium">Empresa</th>
              <th className="text-right px-3 py-3 sm:px-5 text-xs text-zinc-500 font-medium">Sector</th>
              <th className="text-right px-3 py-3 sm:px-5 text-xs text-zinc-500 font-medium w-16 sm:w-28">Relativo</th>
            </tr>
          </thead>
          <tbody>
            {metrics.map((m, i) => {
              const compVal = m.value;
              const sectorVal = m.sectorAvg;
              let relLabel = "—";
              let relColor = "#9ca3af";

              if (compVal != null && sectorVal != null && sectorVal !== 0) {
                const diff = ((compVal - sectorVal) / Math.abs(sectorVal)) * 100;
                const isBetter = m.higherIsBetter ? diff > 5 : diff < -5;
                const isWorse = m.higherIsBetter ? diff < -5 : diff > 5;
                relLabel = `${diff > 0 ? "+" : ""}${diff.toFixed(0)}%`;
                relColor = isBetter ? "#0cc06c" : isWorse ? "#ff4d4d" : "#fbbf24";
              }

              return (
                <tr key={i} className="border-b border-white/[0.04] last:border-0">
                  <td className="px-3 py-3 sm:px-5">
                    <span className="text-sm text-zinc-300">{m.label}</span>
                    {m.hint && <span className="block sm:inline text-[10px] text-zinc-600 sm:ml-1.5">{m.hint}</span>}
                  </td>
                  <td className="px-3 py-3 sm:px-5 text-right">
                    <span className={`text-sm font-semibold tabular-nums ${compVal == null ? "text-zinc-600" : "text-white"}`}>
                      {fmt(compVal, m.format)}
                    </span>
                  </td>
                  <td className="px-3 py-3 sm:px-5 text-right">
                    <span className="text-sm text-zinc-500 tabular-nums">
                      {fmt(sectorVal, m.format)}
                    </span>
                  </td>
                  <td className="px-3 py-3 sm:px-5 text-right">
                    <span className="text-xs font-semibold tabular-nums" style={{ color: relColor }}>
                      {relLabel}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
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
      const isBetter = m.higherIsBetter ? diff > 5 : diff < -5;
      const isWorse = m.higherIsBetter ? diff < -5 : diff > 5;
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
