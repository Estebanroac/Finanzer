"use client";

import { formatMultiple, formatPercent, formatNumber, type StockAnalysis } from "@/lib/api";
import InfoTooltip, { type TooltipContent } from "@/components/InfoTooltip";
import { HEALTH } from "@/lib/tooltips";

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

export default function HealthTab({ data }: { data: StockAnalysis }) {
  const m = data.key_metrics;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
      {/* Liquidity */}
      <div>
        <h4 className="text-xs text-zinc-500 uppercase tracking-widest mb-3 font-medium">
          Liquidez
        </h4>
        <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] px-5">
          <Row label="Current Ratio" value={formatMultiple(m.current_ratio)} tooltip={HEALTH.current_ratio} />
          <Row label="Quick Ratio" value={formatMultiple(m.quick_ratio)} tooltip={HEALTH.quick_ratio} />
          <Row label="Efectivo" value={formatNumber(m.cash)} tooltip={HEALTH.cash} />
          <Row label="Free Cash Flow" value={formatNumber(m.free_cash_flow)} tooltip={HEALTH.fcf} />
        </div>
      </div>

      {/* Leverage */}
      <div>
        <h4 className="text-xs text-zinc-500 uppercase tracking-widest mb-3 font-medium">
          Apalancamiento
        </h4>
        <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] px-5">
          <Row label="Deuda / Equity" value={formatMultiple(m.de)} tooltip={HEALTH.de_ratio} />
          <Row label="Deuda / Activos" value={formatPercent(m.debt_to_assets)} tooltip={HEALTH.debt_to_assets} />
          <Row label="Deuda Total" value={formatNumber(m.total_debt)} />
          <Row label="Total Equity" value={formatNumber(m.total_equity)} />
        </div>
      </div>

      {/* Coverage — full width */}
      <div className="md:col-span-2">
        <h4 className="text-xs text-zinc-500 uppercase tracking-widest mb-3 font-medium">
          Cobertura y distribución
        </h4>
        <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] px-5">
          <div className="grid grid-cols-1 sm:grid-cols-3 divide-y sm:divide-y-0 sm:divide-x divide-white/[0.04]">
            <div className="py-4 sm:pr-6">
              <div className="flex items-center gap-1.5 mb-1">
                <span className="text-xs text-zinc-500">Cobertura de Intereses</span>
                <InfoTooltip content={HEALTH.interest_coverage} />
              </div>
              <div className="text-xl font-bold text-white tabular-nums">{formatMultiple(m.interest_coverage)}</div>
            </div>
            <div className="py-4 sm:px-6">
              <div className="text-xs text-zinc-500 mb-1">Dividend Yield</div>
              <div className="text-xl font-bold text-white tabular-nums">{formatPercent(m.dividend_yield)}</div>
            </div>
            <div className="py-4 sm:pl-6">
              <div className="flex items-center gap-1.5 mb-1">
                <span className="text-xs text-zinc-500">Payout Ratio</span>
                <InfoTooltip content={HEALTH.payout_ratio} />
              </div>
              <div className="text-xl font-bold text-white tabular-nums">{formatPercent(m.payout_ratio)}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
