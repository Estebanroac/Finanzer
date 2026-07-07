"use client";

import { formatNumber, formatPercent, formatPrice, type StockAnalysis } from "@/lib/api";
import InfoTooltip from "@/components/InfoTooltip";
import { HISTORICAL } from "@/lib/tooltips";

export default function HistoricalTab({ data }: { data: StockAnalysis }) {
  const m = data.key_metrics;
  const price = data.price;

  // Build a financial snapshot
  const revenue = m.revenue;
  const netIncome = m.net_income;
  const ebitda = m.ebitda;
  const fcf = m.free_cash_flow;
  const ocf = m.operating_cash_flow;

  // Key ratios for radar-style display
  const metrics = [
    { label: "Crec. Revenue", value: m.revenue_growth, format: "percent" as const },
    { label: "Crec. Earnings", value: m.earnings_growth, format: "percent" as const },
    { label: "Margen Neto", value: m.net_margin, format: "percent" as const },
    { label: "Margen Operativo", value: m.operating_margin, format: "percent" as const },
    { label: "ROE", value: m.roe, format: "percent" as const },
    { label: "ROA", value: m.roa, format: "percent" as const },
    { label: "ROIC", value: m.roic, format: "percent" as const },
  ];

  return (
    <div className="space-y-8">
      {/* 52-Week Price Context */}
      <PriceContext
        price={price}
        high={m.price_52w_high}
        low={m.price_52w_low}
        beta={m.beta}
      />

      {/* Income Waterfall */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <h4 className="text-xs text-zinc-500 uppercase tracking-widest font-medium">
            Flujo de resultados (TTM)
          </h4>
          <InfoTooltip content={HISTORICAL.waterfall} />
        </div>
        <p className="text-[10px] text-zinc-600 mb-4">
          Cómo el revenue se transforma en beneficio neto y flujo de caja libre.
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
          <WaterfallBlock label="Revenue" value={revenue} color="#a1a1a6" />
          <WaterfallBlock label="EBITDA" value={ebitda} color="#6ee7b4" pct={revenue && ebitda ? ebitda / revenue : null} />
          <WaterfallBlock label="Op. Income" value={m.operating_income} color="#0cc06c" pct={revenue && m.operating_income ? m.operating_income / revenue : null} />
          <WaterfallBlock label="Net Income" value={netIncome} color={netIncome && netIncome > 0 ? "#0cc06c" : "#ff4d4d"} pct={revenue && netIncome ? netIncome / revenue : null} />
          <WaterfallBlock label="Free Cash Flow" value={fcf} color={fcf && fcf > 0 ? "#0cc06c" : "#ff4d4d"} pct={revenue && fcf ? fcf / revenue : null} />
        </div>
      </div>

      {/* Cash Flow Analysis */}
      <div>
        <h4 className="text-xs text-zinc-500 uppercase tracking-widest mb-3 font-medium">
          Análisis de flujo de caja
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <CashFlowCard
            title="Cash Flow Operativo"
            value={ocf}
            description="Efectivo generado por las operaciones del negocio"
            isPositive={ocf != null && ocf > 0}
          />
          <CashFlowCard
            title="Free Cash Flow"
            value={fcf}
            description="Efectivo disponible después de inversiones (CAPEX)"
            isPositive={fcf != null && fcf > 0}
          />
          <CashFlowCard
            title="FCF Yield"
            value={m.fcf_yield}
            format="percent"
            description="Rendimiento del FCF respecto al market cap"
            isPositive={m.fcf_yield != null && m.fcf_yield > 0.03}
          />
        </div>
      </div>

      {/* Growth indicators */}
      <div>
        <h4 className="text-xs text-zinc-500 uppercase tracking-widest mb-3 font-medium">
          Indicadores de crecimiento y eficiencia
        </h4>
        <div className="rounded-xl border border-white/[0.06] overflow-hidden bg-[#0a0a0d]/85">
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7">
            {metrics.map((item, i) => {
              const val = item.value;
              const displayVal = val != null
                ? item.format === "percent"
                  ? formatPercent(val)
                  : `${val.toFixed(2)}`
                : "N/A";

              let barPct = 50;
              let barColor = "#9ca3af";
              if (val != null) {
                const absVal = Math.abs(val);
                const normalized = item.format === "percent"
                  ? Math.min(absVal * 100, 100) // already decimal
                  : Math.min(absVal, 100);
                barPct = Math.max(5, Math.min(95, normalized));
                barColor = val > 0 ? "#0cc06c" : "#ff4d4d";
              }

              return (
                <div
                  key={i}
                  className={`px-4 py-4 text-center ${i > 0 ? "border-l border-white/[0.04]" : ""} bg-[#0a0a0d]/85`}
                >
                  <div className="text-[10px] text-zinc-500 uppercase tracking-wider mb-2 truncate">
                    {item.label}
                  </div>
                  <div className={`text-base font-bold tabular-nums ${val == null ? "text-zinc-600" : "text-white"}`}>
                    {displayVal}
                  </div>
                  <div className="mt-2 h-1 bg-white/[0.04] rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{ width: `${barPct}%`, backgroundColor: barColor }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Yearly Revenue & Earnings Chart */}
      {data.yearly_financials && data.yearly_financials.length > 0 && (
        <YearlyChart data={data.yearly_financials} />
      )}

      {/* Balance Sheet Snapshot */}
      <BalanceSheetSnapshot data={data} />

      {/* Per-Share Data */}
      <div>
        <h4 className="text-xs text-zinc-500 uppercase tracking-widest mb-3 font-medium">
          Datos por acción
        </h4>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <PerShareCard label="Precio" value={formatPrice(price)} />
          <PerShareCard label="EPS (TTM)" value={m.eps != null ? `$${m.eps.toFixed(2)}` : "N/A"} />
          <PerShareCard label="Book Value" value={m.book_value_per_share != null ? `$${m.book_value_per_share.toFixed(2)}` : "N/A"} />
          <PerShareCard
            label="FCF / Acción"
            value={fcf != null && m.shares_outstanding ? `$${(fcf / m.shares_outstanding).toFixed(2)}` : "N/A"}
          />
        </div>
      </div>
    </div>
  );
}

function PriceContext({ price, high, low, beta }: {
  price: number | null;
  high: number | null;
  low: number | null;
  beta: number | null;
}) {
  let pct = 50;
  if (price && high && low && high !== low) {
    pct = Math.max(0, Math.min(100, ((price - low) / (high - low)) * 100));
  }
  const position = pct > 70 ? "Cerca del máximo" : pct < 30 ? "Cerca del mínimo" : "Rango medio";
  const posColor = pct > 70 ? "#0cc06c" : pct < 30 ? "#ff4d4d" : "#fbbf24";

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div className="rounded-xl border border-white/[0.06] bg-[#0a0a0d]/85 p-5">
        <div className="flex items-center gap-2 mb-3">
          <span className="text-xs text-zinc-500 uppercase tracking-wider">Posición en 52 semanas</span>
          <InfoTooltip content={HISTORICAL.price_range} />
        </div>
        <div className="flex items-center justify-between text-xs text-zinc-500 mb-2">
          <span>{formatPrice(low)}</span>
          <span className="font-medium" style={{ color: posColor }}>{position}</span>
          <span>{formatPrice(high)}</span>
        </div>
        <div className="relative h-2 bg-white/[0.06] rounded-full">
          <div
            className="absolute top-0 left-0 h-full rounded-full"
            style={{
              width: `${pct}%`,
              background: `linear-gradient(90deg, ${pct < 30 ? "#ff4d4d" : pct > 70 ? "#0cc06c" : "#fbbf24"}, ${pct < 30 ? "#f97316" : pct > 70 ? "#4ade80" : "#f59e0b"})`,
            }}
          />
          <div
            className="absolute top-1/2 -translate-y-1/2 w-3.5 h-3.5 rounded-full bg-white border-2 border-zinc-800 shadow-lg"
            style={{ left: `${pct}%`, marginLeft: "-7px" }}
          />
        </div>
        <div className="text-center mt-3">
          <span className="text-2xl font-bold text-white tabular-nums">{formatPrice(price)}</span>
        </div>
      </div>

      <div className="rounded-xl border border-white/[0.06] bg-[#0a0a0d]/85 p-5">
        <div className="flex items-center gap-2 mb-3">
          <span className="text-xs text-zinc-500 uppercase tracking-wider">Volatilidad</span>
          <InfoTooltip content={HISTORICAL.beta_hist} />
        </div>
        <div className="flex items-baseline gap-2 mb-2">
          <span className="text-3xl font-black text-white tabular-nums">
            {beta != null ? beta.toFixed(2) : "N/A"}
          </span>
          <span className="text-xs text-zinc-500">Beta</span>
        </div>
        <p className="text-xs text-zinc-500 leading-relaxed">
          {beta == null
            ? "Beta no disponible."
            : beta > 1.5
            ? `Beta de ${beta.toFixed(2)} indica alta volatilidad — se mueve significativamente más que el mercado.`
            : beta > 1.0
            ? `Beta de ${beta.toFixed(2)} indica volatilidad ligeramente superior al mercado general.`
            : beta > 0.7
            ? `Beta de ${beta.toFixed(2)} indica volatilidad similar al mercado general.`
            : `Beta de ${beta.toFixed(2)} indica baja volatilidad — acción defensiva.`}
        </p>
        {price && high && low && (
          <div className="mt-3 text-xs text-zinc-600">
            Rango anual: {formatPrice(low)} — {formatPrice(high)} ({((high - low) / low * 100).toFixed(0)}% amplitud)
          </div>
        )}
      </div>
    </div>
  );
}

function WaterfallBlock({ label, value, color, pct }: {
  label: string;
  value: number | null;
  color: string;
  pct?: number | null;
}) {
  return (
    <div className="rounded-xl border border-white/[0.06] bg-[#0a0a0d]/85 p-4 text-center">
      <div className="text-[10px] text-zinc-500 uppercase tracking-wider mb-2">{label}</div>
      <div className="text-lg font-bold tabular-nums" style={{ color }}>
        {formatNumber(value)}
      </div>
      {pct != null && (
        <div className="text-[10px] text-zinc-500 mt-1">
          {(pct * 100).toFixed(1)}% del revenue
        </div>
      )}
    </div>
  );
}

function CashFlowCard({ title, value, format, description, isPositive }: {
  title: string;
  value: number | null;
  format?: "percent";
  description: string;
  isPositive: boolean;
}) {
  const color = value == null ? "#9ca3af" : isPositive ? "#0cc06c" : "#ff4d4d";
  const displayVal = value == null ? "N/A"
    : format === "percent" ? formatPercent(value)
    : formatNumber(value);

  return (
    <div className="rounded-xl border border-white/[0.06] bg-[#0a0a0d]/85 p-5">
      <div className="text-xs text-zinc-500 mb-2">{title}</div>
      <div className="text-2xl font-bold tabular-nums mb-2" style={{ color }}>
        {displayVal}
      </div>
      <p className="text-[10px] text-zinc-600 leading-relaxed">{description}</p>
    </div>
  );
}

function BalanceSheetSnapshot({ data }: { data: StockAnalysis }) {
  const m = data.key_metrics;
  const totalAssets = m.total_assets;
  const totalEquity = m.total_equity;
  const totalDebt = m.total_debt;
  const cash = m.cash;

  if (!totalAssets && !totalEquity && !totalDebt) return null;

  // Calculate composition
  const items: { label: string; value: number; color: string }[] = [];
  if (totalEquity && totalEquity > 0) items.push({ label: "Equity", value: totalEquity, color: "#0cc06c" });
  if (totalDebt && totalDebt > 0) items.push({ label: "Deuda", value: totalDebt, color: "#ff4d4d" });
  if (cash && cash > 0) items.push({ label: "Efectivo", value: cash, color: "#0cc06c" });

  const total = items.reduce((sum, i) => sum + i.value, 0);

  return (
    <div>
      <h4 className="text-xs text-zinc-500 uppercase tracking-widest mb-3 font-medium">
        Estructura del balance
      </h4>
      <div className="rounded-xl border border-white/[0.06] bg-[#0a0a0d]/85 p-5">
        {/* Stacked bar */}
        {total > 0 && (
          <div className="flex h-3 rounded-full overflow-hidden mb-4">
            {items.map((item, i) => (
              <div
                key={i}
                className="h-full first:rounded-l-full last:rounded-r-full"
                style={{ width: `${(item.value / total) * 100}%`, backgroundColor: item.color }}
              />
            ))}
          </div>
        )}

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <BalanceItem label="Total Assets" value={totalAssets} color="#9ca3af" />
          <BalanceItem label="Equity" value={totalEquity} color="#0cc06c" />
          <BalanceItem label="Deuda Total" value={totalDebt} color="#ff4d4d" />
          <BalanceItem label="Efectivo" value={cash} color="#0cc06c" />
        </div>

        {/* Net debt */}
        {totalDebt != null && cash != null && (
          <div className="mt-4 pt-4 border-t border-white/[0.04] flex items-center justify-between">
            <span className="text-xs text-zinc-500">Deuda Neta (Deuda - Efectivo)</span>
            <span className={`text-sm font-bold tabular-nums ${totalDebt - cash > 0 ? "text-red-400" : "text-green-400"}`}>
              {formatNumber(totalDebt - cash)}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

function BalanceItem({ label, value, color }: { label: string; value: number | null; color: string }) {
  return (
    <div>
      <div className="flex items-center gap-1.5 mb-1">
        <div className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
        <span className="text-[10px] text-zinc-500 uppercase tracking-wider">{label}</span>
      </div>
      <div className="text-sm font-bold text-white tabular-nums">{formatNumber(value)}</div>
    </div>
  );
}

function YearlyChart({ data: yearly }: { data: Array<{ year: number; revenue: number | null; earnings: number | null }> }) {
  // Sort ascending by year
  const sorted = [...yearly].sort((a, b) => a.year - b.year);
  const maxRev = Math.max(...sorted.map(y => y.revenue || 0));

  return (
    <div>
      <h4 className="text-xs text-zinc-500 uppercase tracking-widest mb-3 font-medium">
        Evolución anual — Revenue & Earnings
      </h4>
      <div className="rounded-xl border border-white/[0.06] bg-[#0a0a0d]/85 p-5">
        <div className="space-y-4">
          {sorted.map((y, i) => {
            const revPct = maxRev > 0 && y.revenue ? (y.revenue / maxRev) * 100 : 0;
            const earnPct = maxRev > 0 && y.earnings ? (Math.abs(y.earnings) / maxRev) * 100 : 0;
            const revGrowth = i > 0 && sorted[i-1].revenue && y.revenue
              ? ((y.revenue - sorted[i-1].revenue!) / Math.abs(sorted[i-1].revenue!)) * 100
              : null;

            return (
              <div key={y.year}>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-sm text-white font-medium tabular-nums">{y.year}</span>
                  <div className="flex items-center gap-4">
                    <span className="text-xs text-zinc-400">
                      Rev: <span className="text-white font-semibold">{formatNumber(y.revenue)}</span>
                    </span>
                    <span className="text-xs text-zinc-400">
                      Earn: <span className={`font-semibold ${y.earnings && y.earnings > 0 ? "text-green-400" : "text-red-400"}`}>
                        {formatNumber(y.earnings)}
                      </span>
                    </span>
                    {revGrowth !== null && (
                      <span className={`text-[10px] font-semibold tabular-nums ${revGrowth > 0 ? "text-green-400" : "text-red-400"}`}>
                        {revGrowth > 0 ? "+" : ""}{revGrowth.toFixed(0)}%
                      </span>
                    )}
                  </div>
                </div>
                <div className="space-y-1">
                  <div className="h-2 bg-white/[0.04] rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full bg-blue-500/80"
                      style={{ width: `${revPct}%` }}
                    />
                  </div>
                  <div className="h-1.5 bg-white/[0.04] rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${earnPct}%`,
                        backgroundColor: y.earnings && y.earnings > 0 ? "#0cc06c" : "#ff4d4d"
                      }}
                    />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
        <div className="flex gap-4 mt-4 pt-3 border-t border-white/[0.04] text-[10px] text-zinc-500">
          <span className="flex items-center gap-1.5"><span className="w-2.5 h-1.5 rounded-sm bg-blue-500/80" /> Revenue</span>
          <span className="flex items-center gap-1.5"><span className="w-2.5 h-1.5 rounded-sm bg-green-500" /> Earnings</span>
        </div>
      </div>
    </div>
  );
}

function PerShareCard({ label, value }: { label: string; value: string }) {
  const isNA = value === "N/A";
  return (
    <div className="rounded-xl border border-white/[0.06] bg-[#0a0a0d]/85 p-4 text-center">
      <div className="text-[10px] text-zinc-500 uppercase tracking-wider mb-1">{label}</div>
      <div className={`text-lg font-bold tabular-nums ${isNA ? "text-zinc-600" : "text-white"}`}>{value}</div>
    </div>
  );
}
