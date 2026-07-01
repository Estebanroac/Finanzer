"use client";

import { formatMultiple, formatPercent, type StockAnalysis } from "@/lib/api";
import InfoTooltip, { type TooltipContent } from "@/components/InfoTooltip";
import { VALUATION } from "@/lib/tooltips";

function Row({ label, value, hint, tooltip }: { label: string; value: string; hint?: string; tooltip?: TooltipContent }) {
  const isNA = value === "N/A";
  return (
    <div className="flex items-center justify-between py-3 border-b border-white/[0.04] last:border-0">
      <div className="flex items-center gap-1.5">
        <span className="text-sm text-zinc-300">{label}</span>
        {hint && <span className="text-xs text-zinc-600">{hint}</span>}
        {tooltip && <InfoTooltip content={tooltip} />}
      </div>
      <span className={`text-sm font-semibold tabular-nums ${isNA ? "text-zinc-600" : "text-white"}`}>
        {value}
      </span>
    </div>
  );
}

export default function ValuationTab({ data }: { data: StockAnalysis }) {
  const m = data.key_metrics;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
      {/* Price multiples */}
      <div>
        <h4 className="text-xs text-zinc-500 uppercase tracking-widest mb-3 font-medium">
          Múltiplos de precio
        </h4>
        <div className="rounded-xl border border-white/[0.06] bg-[#0a0a0d]/85 px-5">
          <Row label="P/E (TTM)" value={formatMultiple(m.pe)} tooltip={VALUATION.pe_trailing} />
          <Row label="Forward P/E" value={formatMultiple(m.forward_pe)} tooltip={VALUATION.pe_forward} />
          <Row label="P/B" value={formatMultiple(m.pb)} tooltip={VALUATION.pb} />
          <Row label="P/S" value={formatMultiple(m.ps)} tooltip={VALUATION.ps} />
          <Row label="PEG" value={m.peg != null ? m.peg.toFixed(2) : "N/A"} tooltip={VALUATION.peg} />
        </div>
      </div>

      {/* Enterprise multiples */}
      <div>
        <h4 className="text-xs text-zinc-500 uppercase tracking-widest mb-3 font-medium">
          Múltiplos enterprise
        </h4>
        <div className="rounded-xl border border-white/[0.06] bg-[#0a0a0d]/85 px-5">
          <Row label="EV/EBITDA" value={formatMultiple(m.ev_ebitda)} tooltip={VALUATION.ev_ebitda} />
          <Row label="P/FCF" value={formatMultiple(m.pfcf)} tooltip={VALUATION.pfcf} />
          <Row label="FCF Yield" value={formatPercent(m.fcf_yield)} tooltip={VALUATION.fcf_yield_val} />
          <Row label="Dividend Yield" value={formatPercent(m.dividend_yield)} tooltip={VALUATION.dividend_yield} />
        </div>
      </div>
    </div>
  );
}
