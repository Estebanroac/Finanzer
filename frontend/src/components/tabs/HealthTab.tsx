"use client";

import { formatNumber, formatMultiple, type StockAnalysis } from "@/lib/api";
import { scaleColor } from "@/lib/metricScale";
import InfoTooltip from "@/components/InfoTooltip";
import { HEALTH } from "@/lib/tooltips";
import { useGrow } from "@/lib/useGrow";

type Tone = "pos" | "warn" | "neg";
const GV: Record<Tone, string> = { pos: "var(--pos)", warn: "var(--warn)", neg: "var(--neg)" };

function worst(...tones: (Tone | null)[]): Tone {
  const t = tones.filter(Boolean) as Tone[];
  if (t.includes("neg")) return "neg";
  if (t.includes("warn")) return "warn";
  return "pos";
}

/** Gauge horizontal contra un umbral marcado en la pista. */
function Gauge({ label, value, tone, scaleMax, mark, markLabel, grown, tooltip }: {
  label: string;
  value: number | null;
  tone: Tone;
  scaleMax: number;
  mark: number;
  markLabel: string;
  grown: boolean;
  tooltip?: (typeof HEALTH)[keyof typeof HEALTH];
}) {
  if (value == null) return null;
  const fillPct = Math.min(100, Math.max(0, (value / scaleMax) * 100));
  const markPct = Math.min(100, (mark / scaleMax) * 100);
  return (
    <div className="gau">
      <div className="gau-top">
        <span className="gau-lab flex items-center gap-1.5">
          {label}
          {tooltip && <InfoTooltip content={tooltip} />}
        </span>
        <span className={`gau-val ${tone}`}>
          {value.toFixed(2)}<span className="gau-x">x</span>
        </span>
      </div>
      <div className="gau-track">
        <div className="gau-fill" style={{ width: grown ? `${fillPct}%` : 0, "--gv": GV[tone] } as React.CSSProperties} />
        <div className="gau-mark" style={{ left: `${markPct}%` }}>
          <span className="gau-mark-lab">{markLabel}</span>
        </div>
      </div>
    </div>
  );
}

export default function HealthTab({ data }: { data: StockAnalysis }) {
  const m = data.key_metrics;
  const grown = useGrow();

  // ── veredictos de liquidez ──
  const curTone: Tone | null = m.current_ratio == null ? null
    : m.current_ratio >= 1.5 ? "pos" : m.current_ratio >= 1 ? "warn" : "neg";
  const quickTone: Tone | null = m.quick_ratio == null ? null
    : m.quick_ratio >= 1 ? "pos" : m.quick_ratio >= 0.5 ? "warn" : "neg";
  const cashTone: Tone | null = m.cash_ratio == null ? null
    : m.cash_ratio >= 0.5 ? "pos" : m.cash_ratio >= 0.2 ? "warn" : "neg";
  const liqTone = worst(curTone, quickTone, cashTone);
  const liqLabel = liqTone === "pos" ? "Sólida" : liqTone === "warn" ? "Ajustada" : "Tensión";

  // ── apalancamiento ──
  const da = m.debt_to_assets;
  const daTone: Tone | null = da == null ? null : da <= 0.3 ? "pos" : da <= 0.5 ? "warn" : "neg";
  const icTone: Tone | null = m.interest_coverage == null ? null
    : m.interest_coverage >= 5 ? "pos" : m.interest_coverage >= 2 ? "warn" : "neg";
  const nde = m.net_debt_to_ebitda;
  const ndeTone: Tone | null = nde == null ? null : nde < 1 ? "pos" : nde < 2.5 ? "warn" : "neg";
  const levTone = worst(daTone, icTone, ndeTone);
  const levLabel = levTone === "pos" ? "Sólido" : levTone === "warn" ? "Moderado" : "Elevado";

  // donut deuda/activos
  const C = 2 * Math.PI * 52;
  const daPct = da != null ? Math.min(1, Math.max(0, da)) : null;
  const equityPct = m.total_equity != null && m.total_assets != null && m.total_assets > 0
    ? m.total_equity / m.total_assets : null;

  const ic = m.interest_coverage;
  const cappedIC = ic != null ? Math.min(ic, 10) : null;

  return (
    <div className={`space-y-6 ${grown ? "viz-in" : ""}`}>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-start">
        {/* ── Liquidez: gauges vs umbral 1.0x ── */}
        <div className="rounded-xl border border-white/[0.06] bg-[#0a0a0d]/85 px-5 py-4">
          <div className="flex items-center justify-between gap-3 mb-1">
            <h4 className="text-xs text-zinc-500 uppercase tracking-widest font-medium">Liquidez</h4>
            <span className={`sol-tag shrink-0 ${liqTone}`}>{liqLabel}</span>
          </div>
          <Gauge label="Current Ratio" value={m.current_ratio} tone={curTone ?? "warn"}
            scaleMax={2} mark={1} markLabel="1.0" grown={grown} tooltip={HEALTH.current_ratio} />
          <Gauge label="Quick Ratio" value={m.quick_ratio} tone={quickTone ?? "warn"}
            scaleMax={2} mark={1} markLabel="1.0" grown={grown} tooltip={HEALTH.quick_ratio} />
          <Gauge label="Cash Ratio" value={m.cash_ratio} tone={cashTone ?? "warn"}
            scaleMax={2} mark={1} markLabel="1.0" grown={grown} />
          <div className="gau-legend">
            <span className="gau-dotm" />
            Umbral de solvencia 1.0x — debajo, los pasivos corrientes superan al activo líquido disponible.
          </div>
        </div>

        {/* ── Apalancamiento: donut + cobertura + deuda neta ── */}
        <div className="rounded-xl border border-white/[0.06] bg-[#0a0a0d]/85 px-5 py-4">
          <div className="flex items-center justify-between gap-3 mb-1">
            <h4 className="text-xs text-zinc-500 uppercase tracking-widest font-medium">Apalancamiento</h4>
            <span className={`sol-tag shrink-0 ${levTone}`}>{levLabel}</span>
          </div>

          {daPct != null && (
            <div className="lev-split">
              <div className="donut">
                <svg viewBox="0 0 120 120" className="donut-svg" aria-hidden="true">
                  <circle className="donut-bg" cx="60" cy="60" r="52" />
                  <circle
                    className="donut-val" cx="60" cy="60" r="52"
                    strokeDasharray={C}
                    strokeDashoffset={grown ? C * (1 - daPct) : C}
                    style={{ stroke: scaleColor("debt_to_assets", da) ?? undefined }}
                  />
                </svg>
                <div className="donut-center">
                  <span className="donut-num">{(daPct * 100).toFixed(0)}<span className="donut-u">%</span></span>
                  <span className="donut-cap">Deuda / Activos</span>
                </div>
              </div>
              <div className="lev-key">
                <div className="lev-key-row">
                  <span className="lev-sw" style={{ background: "var(--t2)" }} />
                  <span className="lev-k">Deuda</span>
                  <span className="lev-v">{(daPct * 100).toFixed(0)}%</span>
                </div>
                <div className="lev-key-row">
                  <span className="lev-sw" style={{ background: "var(--brand)" }} />
                  <span className="lev-k">Patrimonio</span>
                  <span className="lev-v">{equityPct != null && equityPct >= 0 ? `${(equityPct * 100).toFixed(0)}%` : "—"}</span>
                </div>
                <div className="lev-key-row">
                  <span className="lev-k flex items-center gap-1.5">
                    Deuda / Patrimonio <InfoTooltip content={HEALTH.de_ratio} />
                  </span>
                  <span className="lev-v" style={{ color: scaleColor("de", m.de) ?? undefined }}>{formatMultiple(m.de)}</span>
                </div>
              </div>
            </div>
          )}

          {/* Cobertura de intereses: escala saturada a 10x */}
          {cappedIC != null && ic != null && (
            <div className="sat">
              <div className="gau-top">
                <span className="gau-lab flex items-center gap-1.5">
                  Cobertura de Intereses <InfoTooltip content={HEALTH.interest_coverage} />
                </span>
                <span className={`gau-val ${icTone ?? "warn"}`}>
                  {ic.toFixed(1)}<span className="gau-x">x</span>
                </span>
              </div>
              <div className="gau-track sat-track">
                <div className="sat-fill" style={{ width: grown ? `${(cappedIC / 10) * 100}%` : 0, background: GV[icTone ?? "warn"] }} />
                <div className="gau-mark sat-mark" style={{ left: "30%" }}>
                  <span className="gau-mark-lab">3x mín.</span>
                </div>
              </div>
              {ic > 10 && (
                <div className="sat-foot">
                  El beneficio operativo paga los intereses <b>{ic.toFixed(0)} veces</b>.
                  Escala saturada: &gt;10x = blindado.
                </div>
              )}
            </div>
          )}

          {/* Deuda neta / EBITDA */}
          {nde != null && (
            <div style={{ marginTop: 10 }}>
              {nde >= 0 ? (
                <Gauge label="Deuda Neta / EBITDA" value={nde} tone={ndeTone ?? "warn"}
                  scaleMax={3} mark={2.5} markLabel="2.5x" grown={grown} />
              ) : (
                <div className="gau">
                  <div className="gau-top">
                    <span className="gau-lab">Deuda Neta / EBITDA</span>
                    <span className="gau-val pos">Caja neta</span>
                  </div>
                  <p className="text-[11px] text-zinc-500 leading-relaxed">
                    La caja supera a la deuda total: posición financiera neta positiva.
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* ── Balance ── */}
      <div className="rounded-xl border border-white/[0.06] bg-[#0a0a0d]/85 px-5">
        <div className="grid grid-cols-2 sm:grid-cols-4 divide-y sm:divide-y-0 sm:divide-x divide-white/[0.04]">
          {([
            ["Deuda total", m.total_debt],
            ["Efectivo", m.cash],
            ["Deuda neta", m.net_debt],
            ["Patrimonio", m.total_equity],
          ] as Array<[string, number | null]>).map(([label, val], i) => (
            <div key={label} className={`py-4 ${i > 0 ? "sm:px-6" : "sm:pr-6"}`}>
              <div className="text-xs text-zinc-500 mb-1">{label}</div>
              <div className="text-lg font-bold text-white tabular-nums">{formatNumber(val)}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
