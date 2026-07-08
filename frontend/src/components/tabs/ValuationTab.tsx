"use client";

import { formatMultiple, formatPercent, type StockAnalysis } from "@/lib/api";
import InfoTooltip, { type TooltipContent } from "@/components/InfoTooltip";
import { VALUATION } from "@/lib/tooltips";
import { getSectorBenchmarks } from "@/lib/sectorBench";
import { scaleColor } from "@/lib/metricScale";
import { useGrow } from "@/lib/useGrow";

type Tone = "pos" | "warn" | "neg" | "neu";

/** Veredicto vs mediana sectorial para múltiplos (menor = mejor). */
function multTone(diffPct: number): Tone {
  if (diffPct <= -10) return "pos";
  if (diffPct < 10) return "neu";
  if (diffPct < 35) return "warn";
  return "neg";
}

const FILL: Record<Tone, string> = {
  pos: "var(--pos)",
  neu: "rgba(255,255,255,0.4)",
  warn: "var(--warn)",
  neg: "var(--neg)",
};

/** Fila termómetro: pista barato→caro, tick = mediana del sector, fill = empresa. */
function MultRow({ label, value, bench, grown, tooltip }: {
  label: string;
  value: number | null;
  bench: number | null;
  grown: boolean;
  tooltip?: TooltipContent;
}) {
  const hasBar = value != null && value > 0 && bench != null && bench > 0;
  const diff = hasBar ? ((value - bench) / bench) * 100 : 0;
  const tone = hasBar ? multTone(diff) : "neu";
  // escala 0→1.3×max para que tanto el fill como el tick queden dentro
  const scale = hasBar ? Math.max(value, bench) * 1.3 : 1;
  const fillPct = hasBar ? Math.min(100, (value / scale) * 100) : 0;
  const tickPct = hasBar ? Math.min(100, (bench / scale) * 100) : 0;

  return (
    <div className="mval">
      <div className="mval-top">
        <span className="k flex items-center gap-1.5">
          {label}
          {tooltip && <InfoTooltip content={tooltip} />}
        </span>
        <span className="mval-r">
          {hasBar && (
            <span className={`pill ${tone}`}>
              {diff > 0 ? "+" : ""}{diff.toFixed(0)}% vs sector
            </span>
          )}
          <span className="v">{formatMultiple(value)}</span>
        </span>
      </div>
      {hasBar && (
        <div className="mval-track">
          <i className="mval-tick" style={{ left: `${tickPct}%` }} />
          <div
            className="mval-fill"
            style={{ width: grown ? `${fillPct}%` : 0, "--fill": FILL[tone] } as React.CSSProperties}
          />
        </div>
      )}
    </div>
  );
}

function YieldRow({ label, value, metricKey, raw, tooltip }: {
  label: string;
  value: string;
  metricKey?: string;   // clave en metricScale para colorear por su banda
  raw?: number | null;  // valor numérico crudo (decimal para %) para evaluar el umbral
  tooltip?: TooltipContent;
}) {
  const isNA = value === "N/A";
  // Color según la banda ABSOLUTA de la métrica (espeja el tooltip); si no hay
  // escala definida o el dato falta, queda blanco/neutro.
  const color = !isNA && metricKey ? scaleColor(metricKey, raw) : null;
  return (
    <div className="flex items-center justify-between py-3 border-b border-white/[0.04] last:border-0">
      <div className="flex items-center gap-1.5">
        <span className="text-sm text-zinc-300">{label}</span>
        {tooltip && <InfoTooltip content={tooltip} />}
      </div>
      <span
        className={`text-sm font-semibold tabular-nums ${isNA ? "text-zinc-600" : "text-white"}`}
        style={color ? { color } : undefined}
      >
        {value}
      </span>
    </div>
  );
}

export default function ValuationTab({ data }: { data: StockAnalysis }) {
  const m = data.key_metrics;
  const b = getSectorBenchmarks(data.sector_info?.mapped_sector || "default");
  const grown = useGrow();

  const buyback = m.buyback_yield;
  const shareholder = m.shareholder_yield;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-start">
      {/* Múltiplos como termómetro barato→caro */}
      <div className={`rounded-xl border border-white/[0.06] bg-[#0a0a0d]/85 px-5 py-4 ${grown ? "viz-in" : ""}`}>
        <h4 className="text-xs text-zinc-500 uppercase tracking-widest mb-3 font-medium">
          Múltiplos de valoración
        </h4>
        <div className="mval-legend">
          <span className="mval-scale-lbl">Barato</span>
          <span className="mval-ticknote"><i />Mediana sector</span>
          <span className="mval-scale-lbl">Caro</span>
        </div>
        <MultRow label="P/E (TTM)" value={m.pe} bench={b.pe} grown={grown} tooltip={VALUATION.pe_trailing} />
        <MultRow label="Forward P/E" value={m.forward_pe} bench={b.forward_pe} grown={grown} tooltip={VALUATION.pe_forward} />
        <MultRow label="PEG" value={m.peg} bench={b.peg} grown={grown} tooltip={VALUATION.peg} />
        <MultRow label="P/B" value={m.pb} bench={b.pb} grown={grown} tooltip={VALUATION.pb} />
        <MultRow label="EV/EBITDA" value={m.ev_ebitda} bench={b.ev_ebitda} grown={grown} tooltip={VALUATION.ev_ebitda} />
        <MultRow label="P/FCF" value={m.pfcf} bench={b.pfcf} grown={grown} tooltip={VALUATION.pfcf} />
      </div>

      {/* Rendimientos para el accionista */}
      <div className="rounded-xl border border-white/[0.06] bg-[#0a0a0d]/85 px-5 py-4">
        <h4 className="text-xs text-zinc-500 uppercase tracking-widest mb-1 font-medium">
          Rendimientos
        </h4>
        <YieldRow label="FCF Yield" value={formatPercent(m.fcf_yield)} metricKey="fcf_yield" raw={m.fcf_yield} tooltip={VALUATION.fcf_yield_val} />
        <YieldRow label="Earnings Yield" value={formatPercent(m.earnings_yield)} metricKey="earnings_yield" raw={m.earnings_yield} />
        <YieldRow label="Dividend Yield" value={formatPercent(m.dividend_yield)} metricKey="dividend_yield" raw={m.dividend_yield} tooltip={VALUATION.dividend_yield} />
        <YieldRow label="Payout Ratio" value={formatPercent(m.payout_ratio)} metricKey="payout_ratio" raw={m.payout_ratio} />
        <YieldRow
          label="Buyback Yield"
          value={buyback != null ? formatPercent(buyback) : "N/A"}
          metricKey="buyback_yield"
          raw={buyback}
        />
        <YieldRow
          label="Shareholder Yield"
          value={shareholder != null ? formatPercent(shareholder) : "N/A"}
          metricKey="shareholder_yield"
          raw={shareholder}
        />
        <YieldRow label="P/S" value={formatMultiple(m.ps)} metricKey="ps" raw={m.ps} tooltip={VALUATION.ps} />
      </div>
    </div>
  );
}
