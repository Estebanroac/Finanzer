"use client";

import { formatNumber, formatPercent, formatMultiple } from "@/lib/api";
import InfoTooltip, { type TooltipContent } from "@/components/InfoTooltip";
import { METRICS } from "@/lib/tooltips";

interface MetricsGridProps {
  metrics: Record<string, number | null>;
}

function Stat({ label, value, accent, tooltip }: { label: string; value: string; accent?: boolean; tooltip?: TooltipContent }) {
  return (
    <div className="flex flex-col gap-0.5">
      <div className="flex items-center gap-1.5">
        <span className="text-[11px] text-zinc-500 uppercase tracking-wider">{label}</span>
        {tooltip && <InfoTooltip content={tooltip} />}
      </div>
      <span className={`text-lg font-semibold tabular-nums ${accent ? "text-[#0cc06c]" : "text-white"}`}>
        {value}
      </span>
    </div>
  );
}

export default function MetricsGrid({ metrics }: MetricsGridProps) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-x-8 gap-y-5 py-5 px-6 rounded-2xl border border-white/[0.06] bg-[#0a0a0d]/85">
      <Stat label="Market Cap" value={formatNumber(metrics.market_cap)} accent tooltip={METRICS.market_cap} />
      <Stat label="P/E Ratio" value={formatMultiple(metrics.pe)} tooltip={METRICS.pe_ratio} />
      <Stat label="ROE" value={formatPercent(metrics.roe)} tooltip={METRICS.roe} />
      <Stat label="D/E" value={formatMultiple(metrics.de)} tooltip={METRICS.de_ratio} />
      <Stat label="Margen Neto" value={formatPercent(metrics.net_margin)} tooltip={METRICS.net_margin} />
      <Stat label="FCF Yield" value={formatPercent(metrics.fcf_yield)} tooltip={METRICS.fcf_yield} />
      <Stat label="EV/EBITDA" value={formatMultiple(metrics.ev_ebitda)} tooltip={METRICS.ev_ebitda} />
      <Stat label="Beta" value={metrics.beta != null ? metrics.beta.toFixed(2) : "N/A"} tooltip={METRICS.beta} />
    </div>
  );
}
