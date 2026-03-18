"use client";

import { formatPercent, formatNumber, type StockAnalysis } from "@/lib/api";
import InfoTooltip, { type TooltipContent } from "@/components/InfoTooltip";
import { PROFITABILITY } from "@/lib/tooltips";

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

export default function ProfitabilityTab({ data }: { data: StockAnalysis }) {
  const m = data.key_metrics;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
      {/* Returns */}
      <div>
        <h4 className="text-xs text-zinc-500 uppercase tracking-widest mb-3 font-medium">
          Retornos sobre capital
        </h4>
        <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] px-5">
          <Row label="ROE" value={formatPercent(m.roe)} tooltip={PROFITABILITY.roe} />
          <Row label="ROA" value={formatPercent(m.roa)} tooltip={PROFITABILITY.roa} />
          <Row label="ROIC" value={formatPercent(m.roic)} tooltip={PROFITABILITY.roic} />
          <Row label="EPS" value={m.eps != null ? `$${m.eps.toFixed(2)}` : "N/A"} tooltip={PROFITABILITY.eps} />
        </div>
      </div>

      {/* Margins */}
      <div>
        <h4 className="text-xs text-zinc-500 uppercase tracking-widest mb-3 font-medium">
          Márgenes
        </h4>
        <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] px-5">
          <Row label="Margen Bruto" value={formatPercent(m.gross_margin)} tooltip={PROFITABILITY.gross_margin} />
          <Row label="Margen Operativo" value={formatPercent(m.operating_margin)} tooltip={PROFITABILITY.operating_margin} />
          <Row label="Margen Neto" value={formatPercent(m.net_margin)} tooltip={PROFITABILITY.net_margin} />
          <Row label="Margen EBITDA" value={formatPercent(m.ebitda_margin)} tooltip={PROFITABILITY.ebitda_margin} />
        </div>
      </div>

      {/* Absolutes — full width */}
      <div className="md:col-span-2">
        <h4 className="text-xs text-zinc-500 uppercase tracking-widest mb-3 font-medium">
          Resultados
        </h4>
        <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] px-5">
          <div className="grid grid-cols-1 sm:grid-cols-3 divide-y sm:divide-y-0 sm:divide-x divide-white/[0.04]">
            <div className="py-4 sm:pr-6">
              <div className="text-xs text-zinc-500 mb-1">Revenue</div>
              <div className="text-xl font-bold text-white tabular-nums">{formatNumber(m.revenue)}</div>
            </div>
            <div className="py-4 sm:px-6">
              <div className="text-xs text-zinc-500 mb-1">EBITDA</div>
              <div className="text-xl font-bold text-white tabular-nums">{formatNumber(m.ebitda)}</div>
            </div>
            <div className="py-4 sm:pl-6">
              <div className="text-xs text-zinc-500 mb-1">Ingreso Neto</div>
              <div className="text-xl font-bold text-white tabular-nums">{formatNumber(m.net_income)}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
