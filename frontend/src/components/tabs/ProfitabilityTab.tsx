"use client";

import { formatPercent, formatNumber, type StockAnalysis } from "@/lib/api";
import InfoTooltip from "@/components/InfoTooltip";
import { PROFITABILITY, HEALTH } from "@/lib/tooltips";
import { getSectorBenchmarks } from "@/lib/sectorBench";
import { useGrow } from "@/lib/useGrow";
import { scaleColor } from "@/lib/metricScale";

/** Retorno de la empresa vs el sector: barra de marca + fantasma del sector. */
function RetRow({ label, value, bench, grown, tooltip, metricKey }: {
  label: string;
  value: number | null;
  bench: number | null;
  grown: boolean;
  tooltip?: (typeof PROFITABILITY)[keyof typeof PROFITABILITY];
  metricKey: string;
}) {
  if (value == null) return null;
  const negative = value < 0;
  const hasBench = bench != null && bench > 0;
  const scale = Math.max(Math.abs(value), hasBench ? bench : 0) * 1.05 || 1;
  const fillPct = negative ? 0 : Math.min(100, (value / scale) * 100);
  const secPct = hasBench ? Math.min(100, (bench / scale) * 100) : 0;
  const mult = hasBench && !negative && bench > 0 ? value / bench : null;
  // Color por BANDA ABSOLUTA de la métrica (value en decimal, igual que el umbral).
  const color = scaleColor(metricKey, value);

  return (
    <div className="pf-ret">
      <div className="pf-ret-top">
        <span className="lab flex items-center gap-1.5">
          {label}
          {tooltip && <InfoTooltip content={tooltip} value={value} valueLabel={formatPercent(value)} />}
        </span>
        <span className="cmp">
          <b className={negative ? "neg" : ""} style={color ? { color } : undefined}>{formatPercent(value)}</b>
          {mult != null && <span className="mult">{mult.toFixed(1)}× sector</span>}
          {negative && <span className="mult">equity negativo por recompras</span>}
        </span>
      </div>
      <div className="pf-ret-track">
        {hasBench && <div className="pf-ret-sector" style={{ width: grown ? `${secPct}%` : 0 }} />}
        <div className="pf-ret-fill" style={{ width: grown ? `${fillPct}%` : 0, ...(color ? { background: color } : {}) }} />
        {hasBench && (
          <span className="pf-ret-secmark" style={{ left: `${secPct}%` }}>
            {(bench * 100).toFixed(0)}%
          </span>
        )}
      </div>
    </div>
  );
}

/** Paso de la cascada: % del ingreso que sobrevive + monto $ + franja perdida. */
function FallStep({ label, amount, pct, prevPct, grown, isBase, isNet, fillColor, tooltip, tooltipValue }: {
  label: string;
  amount: number | null;
  pct: number;          // 0..100
  prevPct: number | null;
  grown: boolean;
  isBase?: boolean;
  isNet?: boolean;
  fillColor?: string | null;   // color por BANDA ABSOLUTA del margen (null = base/neutro)
  tooltip?: (typeof PROFITABILITY)[keyof typeof PROFITABILITY];
  tooltipValue?: number | null;
}) {
  const lost = prevPct != null && prevPct > pct ? prevPct - pct : 0;
  return (
    <div className={`pf-step ${isNet ? "pf-step--net" : ""}`}>
      <div className="pf-step-top">
        <span className="lab flex items-center gap-1.5">
          {label}
          {tooltip && <InfoTooltip content={tooltip} value={tooltipValue} valueLabel={`${pct.toFixed(1)}%`} />}
        </span>
        <span className="v" style={isNet ? { color: fillColor ?? "var(--brand)" } : undefined}>
          {amount != null && <span className="pf-amt">{formatNumber(amount)}</span>}
          {pct.toFixed(1)}%
        </span>
      </div>
      <div className="pf-step-track">
        {lost > 0 && <div className="pf-lost" style={{ left: `${pct}%`, width: `${lost}%` }} />}
        <div
          className={`pf-step-fill ${isBase ? "pf-step-fill--base" : ""}`}
          style={{
            width: grown ? `${pct}%` : 0,
            ...(fillColor
              ? { background: fillColor }
              : isNet
                ? { background: "linear-gradient(90deg, var(--brand), #35d68f)" }
                : {}),
          }}
        />
      </div>
    </div>
  );
}

export default function ProfitabilityTab({ data }: { data: StockAnalysis }) {
  const m = data.key_metrics;
  const b = getSectorBenchmarks(data.sector_info?.mapped_sector || "default");
  const grown = useGrow();

  const rev = m.revenue;
  // pasos de la cascada (solo los que tienen margen disponible), orden de erosión
  const steps: Array<{ label: string; metricKey: string; margin: number | null; amount: number | null }> = [
    { label: "Margen Bruto", metricKey: "gross_margin", margin: m.gross_margin, amount: rev != null && m.gross_margin != null ? rev * m.gross_margin : null },
    { label: "Margen EBITDA", metricKey: "ebitda_margin", margin: m.ebitda_margin, amount: m.ebitda ?? (rev != null && m.ebitda_margin != null ? rev * m.ebitda_margin : null) },
    { label: "Margen Operativo", metricKey: "operating_margin", margin: m.operating_margin, amount: m.operating_income ?? (rev != null && m.operating_margin != null ? rev * m.operating_margin : null) },
    { label: "Margen Neto", metricKey: "net_margin", margin: m.net_margin, amount: m.net_income },
  ].filter(s => s.margin != null);

  const spread = m.roic_wacc_spread;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-start">
      {/* Retornos sobre el capital vs sector */}
      <div className={`rounded-xl border border-white/[0.06] bg-[#0a0a0d]/85 px-5 py-4 ${grown ? "viz-in" : ""}`}>
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-xs text-zinc-500 uppercase tracking-widest font-medium">
            Retornos sobre el capital
          </h4>
          <span className="pf-legend">
            <i className="pf-swatch pf-swatch--co" />{data.symbol || "Empresa"}
            <i className="pf-swatch pf-swatch--sec" />Sector
          </span>
        </div>
        <RetRow label="ROE" value={m.roe} bench={b.roe} grown={grown} tooltip={PROFITABILITY.roe} metricKey="roe" />
        <RetRow label="ROIC" value={m.roic} bench={b.roic} grown={grown} tooltip={PROFITABILITY.roic} metricKey="roic" />
        <RetRow label="ROA" value={m.roa} bench={b.roa} grown={grown} tooltip={PROFITABILITY.roa} metricKey="roa" />

        {/* Creación de valor: ROIC vs costo de capital */}
        {spread != null && m.wacc != null && (
          <div
            className="mt-3 flex items-center gap-2.5 rounded-lg px-3.5 py-2.5 text-xs"
            style={{
              background: spread >= 0 ? "rgba(12,192,108,0.07)" : "rgba(255,69,58,0.07)",
              border: `1px solid ${spread >= 0 ? "rgba(12,192,108,0.2)" : "rgba(255,69,58,0.2)"}`,
            }}
          >
            <span
              className="w-1.5 h-1.5 rounded-full shrink-0"
              style={{ background: spread >= 0 ? "var(--pos)" : "var(--neg)" }}
            />
            <span className="text-zinc-400">
              <span className="inline-flex items-center gap-1.5 align-middle">
                ROIC − WACC:
                <InfoTooltip
                  content={PROFITABILITY.roic_wacc_spread}
                  value={spread}
                  valueLabel={`${spread >= 0 ? "+" : ""}${(spread * 100).toFixed(1)} pp`}
                />
              </span>{" "}
              <b style={{ color: spread >= 0 ? "var(--pos)" : "var(--neg)" }}>
                {spread >= 0 ? "+" : ""}{(spread * 100).toFixed(1)} pp
              </b>{" "}
              {spread >= 0.03 ? "— crea valor sobre su costo de capital" :
               spread >= 0 ? "— apenas cubre su costo de capital" :
               "— no cubre su costo de capital"}
              {" "}
              <span className="text-zinc-600 inline-flex items-center gap-1.5 align-middle">
                <span>(WACC {(m.wacc * 100).toFixed(1)}%)</span>
                <InfoTooltip
                  content={PROFITABILITY.wacc}
                  value={m.wacc}
                  valueLabel={`${(m.wacc * 100).toFixed(1)}%`}
                />
              </span>
            </span>
          </div>
        )}
      </div>

      {/* Cascada de márgenes con montos $ */}
      <div className={`rounded-xl border border-white/[0.06] bg-[#0a0a0d]/85 px-5 py-4 ${grown ? "viz-in" : ""}`}>
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-xs text-zinc-500 uppercase tracking-widest font-medium">Márgenes</h4>
          <span className="pf-hint">de cada $1 de ingreso</span>
        </div>
        <div className="pf-fall">
          <FallStep label="Ingreso" amount={rev} pct={100} prevPct={null} grown={grown} isBase />
          {steps.map((s, i) => (
            <FallStep
              key={s.label}
              label={s.label}
              amount={s.amount}
              pct={(s.margin as number) * 100}
              prevPct={i === 0 ? 100 : (steps[i - 1].margin as number) * 100}
              grown={grown}
              isNet={i === steps.length - 1}
              fillColor={scaleColor(s.metricKey, s.margin)}
              tooltip={PROFITABILITY[s.metricKey]}
              tooltipValue={s.margin}
            />
          ))}
        </div>
      </div>

      {/* Resultados absolutos */}
      <div className="md:col-span-2 rounded-xl border border-white/[0.06] bg-[#0a0a0d]/85 px-5">
        <div className="grid grid-cols-2 sm:grid-cols-4 divide-y sm:divide-y-0 sm:divide-x divide-white/[0.04]">
          <div className="py-4 sm:pr-6">
            <div className="text-xs text-zinc-500 mb-1">Revenue</div>
            <div className="text-lg font-bold text-white tabular-nums">{formatNumber(m.revenue)}</div>
          </div>
          <div className="py-4 sm:px-6">
            <div className="text-xs text-zinc-500 mb-1">EBITDA</div>
            <div className="text-lg font-bold text-white tabular-nums">{formatNumber(m.ebitda)}</div>
          </div>
          <div className="py-4 sm:px-6">
            <div className="text-xs text-zinc-500 mb-1">Ingreso Neto</div>
            <div className="text-lg font-bold text-white tabular-nums">{formatNumber(m.net_income)}</div>
          </div>
          <div className="py-4 sm:pl-6">
            <div className="text-xs text-zinc-500 mb-1 flex items-center gap-1">
              Free Cash Flow
              <InfoTooltip content={HEALTH.fcf} value={m.free_cash_flow} valueLabel={formatNumber(m.free_cash_flow)} />
            </div>
            <div className="text-lg font-bold text-white tabular-nums">{formatNumber(m.free_cash_flow)}</div>
          </div>
        </div>
      </div>
    </div>
  );
}
