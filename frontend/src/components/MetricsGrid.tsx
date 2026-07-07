"use client";

import { formatNumber, formatPercent, formatMultiple } from "@/lib/api";
import InfoTooltip, { type TooltipContent } from "@/components/InfoTooltip";
import { METRICS } from "@/lib/tooltips";
import { getSectorBenchmarks } from "@/lib/sectorBench";

interface MetricsGridProps {
  metrics: Record<string, number | null>;
  sector?: string;
}

type Tone = "pos" | "warn" | "neg";

const DOT: Record<Tone, string> = {
  pos: "bg-[#0cc06c] shadow-[0_0_6px_rgba(12,192,108,0.55)]",
  warn: "bg-[#ffd60a] shadow-[0_0_6px_rgba(255,214,10,0.5)]",
  neg: "bg-[#ff453a] shadow-[0_0_6px_rgba(255,69,58,0.5)]",
};
const CHIP: Record<Tone, string> = {
  pos: "text-[#0cc06c] bg-[#0cc06c]/[0.08] border-[#0cc06c]/20",
  warn: "text-[#ffd60a] bg-[#ffd60a]/[0.07] border-[#ffd60a]/20",
  neg: "text-[#ff453a] bg-[#ff453a]/[0.08] border-[#ff453a]/20",
};

/** Tono según qué tan lejos está del benchmark sectorial (±10% = en línea). */
function toneFor(value: number, bench: number, higherIsBetter: boolean): Tone {
  const diff = (value - bench) / Math.abs(bench);
  const better = higherIsBetter ? diff : -diff;
  if (better > 0.1) return "pos";
  if (better < -0.1) return "neg";
  return "warn";
}

function Stat({
  label, value, tooltip, accent, index,
  raw, bench, higherIsBetter, benchFmt,
}: {
  label: string;
  value: string;
  tooltip?: TooltipContent;
  accent?: boolean;
  index: number;
  raw?: number | null;
  bench?: number | null;
  higherIsBetter?: boolean;
  benchFmt?: (v: number) => string;
}) {
  const hasContext = raw != null && bench != null && bench !== 0 && higherIsBetter !== undefined;
  const tone = hasContext ? toneFor(raw, bench, higherIsBetter) : null;
  const above = hasContext ? raw >= bench : null;

  return (
    <div className="flex flex-col gap-1 fade-up" style={{ animationDelay: `${0.1 + index * 0.045}s`, opacity: 0 }}>
      <div className="flex items-center gap-1.5">
        {tone && <span className={`w-[7px] h-[7px] rounded-full shrink-0 ${DOT[tone]}`} />}
        <span className="text-[11px] text-zinc-500 uppercase tracking-wider">{label}</span>
        {tooltip && <InfoTooltip content={tooltip} />}
      </div>
      <div className="flex items-baseline gap-2 flex-wrap">
        <span className={`text-xl font-semibold tabular-nums ${accent ? "text-[#0cc06c]" : "text-white"}`}>
          {value}
        </span>
        {tone && benchFmt && bench != null && (
          <span className={`px-1.5 py-px rounded-md border text-[10px] font-medium tabular-nums ${CHIP[tone]}`}>
            {above ? "▲" : "▼"} vs {benchFmt(bench)}
          </span>
        )}
      </div>
    </div>
  );
}

export default function MetricsGrid({ metrics, sector }: MetricsGridProps) {
  const b = getSectorBenchmarks(sector || "default");
  const pctFmt = (v: number) => `${(v * 100).toFixed(0)}%`;
  const multFmt = (v: number) => `${v.toFixed(0)}x`;

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-x-8 gap-y-5 py-5 px-6 rounded-2xl border border-white/[0.06] bg-[#0a0a0d]/85 h-full content-center">
      <Stat index={0} label="Market Cap" value={formatNumber(metrics.market_cap)} accent tooltip={METRICS.market_cap} />
      <Stat index={1} label="P/E Ratio" value={formatMultiple(metrics.pe)} tooltip={METRICS.pe_ratio}
        raw={metrics.pe} bench={b.pe} higherIsBetter={false} benchFmt={multFmt} />
      <Stat index={2} label="ROE" value={formatPercent(metrics.roe)} tooltip={METRICS.roe}
        raw={metrics.roe} bench={b.roe} higherIsBetter={true} benchFmt={pctFmt} />
      <Stat index={3} label="D/E" value={formatMultiple(metrics.de)} tooltip={METRICS.de_ratio}
        raw={metrics.de} bench={b.de} higherIsBetter={false} benchFmt={multFmt} />
      <Stat index={4} label="Margen Neto" value={formatPercent(metrics.net_margin)} tooltip={METRICS.net_margin}
        raw={metrics.net_margin} bench={b.net_margin} higherIsBetter={true} benchFmt={pctFmt} />
      <Stat index={5} label="FCF Yield" value={formatPercent(metrics.fcf_yield)} tooltip={METRICS.fcf_yield}
        raw={metrics.fcf_yield} bench={b.fcf_yield} higherIsBetter={true} benchFmt={pctFmt} />
      <Stat index={6} label="EV/EBITDA" value={formatMultiple(metrics.ev_ebitda)} tooltip={METRICS.ev_ebitda}
        raw={metrics.ev_ebitda} bench={b.ev_ebitda} higherIsBetter={false} benchFmt={multFmt} />
      <Stat index={7} label="Beta" value={metrics.beta != null ? metrics.beta.toFixed(2) : "N/A"} tooltip={METRICS.beta} />
    </div>
  );
}
