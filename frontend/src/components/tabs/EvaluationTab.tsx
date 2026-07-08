"use client";

import type { StockAnalysis } from "@/lib/api";
import { getScoreColor } from "@/lib/api";
import InfoTooltip from "@/components/InfoTooltip";
import { EVALUATION } from "@/lib/tooltips";
import { useGrow } from "@/lib/useGrow";

export default function EvaluationTab({ data }: { data: StockAnalysis }) {
  const alerts = data.alerts;
  const score = data.score;
  const altmanZ = data.altman_z;
  const piotroskiF = data.piotroski_f;
  const finHealth = data.financial_health;
  const grown = useGrow();

  return (
    <div className={`space-y-8 ${grown ? "viz-in" : ""}`}>
      {/* Radar del perfil + desglose compacto */}
      {score?.breakdown && Object.keys(score.breakdown).length >= 3 && (
        <div className="grid grid-cols-1 md:grid-cols-[minmax(0,300px)_1fr] gap-4 items-stretch">
          <div className="rounded-xl border border-white/[0.06] bg-[#0a0a0d]/85 p-5 flex flex-col">
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-1.5">
                <h4 className="text-xs text-zinc-500 uppercase tracking-widest font-medium">
                  Perfil del análisis
                </h4>
                <InfoTooltip content={EVALUATION.score_category} />
              </div>
              <span className="pf-hint">forma de fortalezas</span>
            </div>
            <div className="flex-1 grid place-items-center py-2">
              <CategoryRadar breakdown={score.breakdown} />
            </div>
          </div>

          <div className="rounded-xl border border-white/[0.06] bg-[#0a0a0d]/85 p-5">
            <h4 className="text-xs text-zinc-500 uppercase tracking-widest mb-4 font-medium">
              Desglose del score · {score.total_score} / {score.max_score}
            </h4>
            <div className="space-y-3.5">
              {Object.entries(score.breakdown).map(([key, cat]) => {
                const pct = cat.max > 0 ? (cat.score / cat.max) * 100 : 0;
                const color = getScoreColor(pct);
                return (
                  <div key={key}>
                    <div className="flex items-baseline justify-between mb-1.5">
                      <span className="text-sm text-zinc-300">{key}</span>
                      <span className="text-sm font-semibold tabular-nums" style={{ color }}>
                        {cat.score} <span className="text-zinc-600 font-normal">/ {cat.max}</span>
                      </span>
                    </div>
                    <div className="h-1.5 bg-white/[0.05] rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: grown ? `${pct}%` : 0,
                          background: color,
                          transition: "width 1s cubic-bezier(0.16,1,0.3,1)",
                        }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Institutional metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {finHealth && <FinancialHealthCard data={finHealth} />}
        {altmanZ && <ZScoreCard data={altmanZ} />}
        {piotroskiF && <FScoreCard data={piotroskiF} />}
      </div>

      {/* Detailed Score breakdown with adjustments */}
      {score?.breakdown && Object.keys(score.breakdown).length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-4">
            <h4 className="text-xs text-zinc-500 uppercase tracking-widest font-medium">
              Desglose detallado — {score.total_score}/{score.max_score} pts
            </h4>
            <InfoTooltip content={EVALUATION.score_breakdown} />
          </div>
          <div className="space-y-3">
            {Object.entries(score.breakdown).map(([key, cat]) => {
              const pct = cat.max > 0 ? (cat.score / cat.max) * 100 : 0;
              const color = getScoreColor(pct);
              const adjustments = cat.adjustments || [];

              return (
                <div key={key} className="rounded-xl border border-white/[0.06] bg-[#0a0a0d]/85 overflow-hidden">
                  {/* Category header */}
                  <div className="px-5 py-4 flex items-center justify-between">
                    <div>
                      <span className="text-sm text-zinc-200 font-medium capitalize">{key}</span>
                      <div className="mt-1 h-1 w-24 bg-white/[0.04] rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full"
                          style={{ width: `${pct}%`, backgroundColor: color }}
                        />
                      </div>
                    </div>
                    <span className="text-lg font-bold tabular-nums" style={{ color }}>
                      {cat.score}<span className="text-xs text-zinc-600 font-normal">/{cat.max}</span>
                    </span>
                  </div>

                  {/* Adjustments detail */}
                  {adjustments.length > 0 && (
                    <div className="border-t border-white/[0.04] px-5 py-3 space-y-2">
                      {adjustments.map((adj, i) => {
                        const sevColor = adj.severity === "excellent" || adj.severity === "good"
                          ? "#0cc06c"
                          : adj.severity === "severe" || adj.severity === "critical"
                          ? "#ff4d4d"
                          : "#fbbf24";
                        return (
                          <div key={i} className="flex items-start gap-3 text-xs">
                            <div
                              className="w-1.5 h-1.5 rounded-full mt-1.5 shrink-0"
                              style={{ background: sevColor }}
                            />
                            <div className="flex-1">
                              <span className="text-zinc-300 font-medium">{adj.metric}</span>
                              {adj.value && (
                                <span className="text-zinc-500 ml-1.5">{adj.value}</span>
                              )}
                              <p className="text-zinc-500 mt-0.5">{adj.reason}</p>
                            </div>
                            <span
                              className="shrink-0 tabular-nums font-semibold text-[11px]"
                              style={{ color: sevColor }}
                            >
                              {adj.adjustment > 0 ? `+${adj.adjustment}` : adj.adjustment}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Alerts */}
      {alerts && (
        <div>
          {/* Summary pills */}
          <div className="flex items-center gap-3 mb-5">
            <Pill count={alerts.red_flags?.length || 0} label="Riesgos" color="#ff4d4d" />
            <Pill count={alerts.warnings?.length || 0} label="Advertencias" color="#fbbf24" />
            <Pill count={alerts.strengths?.length || 0} label="Fortalezas" color="#0cc06c" />
            <InfoTooltip content={EVALUATION.alerts} />
          </div>

          {alerts.red_flags && alerts.red_flags.length > 0 && (
            <AlertGroup title="Riesgos" color="#ff4d4d" items={alerts.red_flags} />
          )}
          {alerts.warnings && alerts.warnings.length > 0 && (
            <AlertGroup title="Advertencias" color="#fbbf24" items={alerts.warnings} />
          )}
          {alerts.strengths && alerts.strengths.length > 0 && (
            <AlertGroup title="Fortalezas" color="#0cc06c" items={alerts.strengths} />
          )}

          {(alerts.red_flags?.length || 0) === 0 &&
           (alerts.warnings?.length || 0) === 0 &&
           (alerts.strengths?.length || 0) === 0 && (
            <p className="text-sm text-zinc-500 italic">
              Las alertas detalladas se encuentran en el desglose del score arriba.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

/* ── Radar: los 5 ejes = categorías del score (0..20) ── */
function CategoryRadar({ breakdown }: { breakdown: NonNullable<StockAnalysis["score"]>["breakdown"] }) {
  const PREFERRED = ["Valoración", "Rentabilidad", "Solidez Financiera", "Calidad de Ganancias", "Crecimiento"];
  const entries = Object.entries(breakdown);
  const ordered = [
    ...PREFERRED.map(name => entries.find(([k]) => k === name)).filter(Boolean) as typeof entries,
    ...entries.filter(([k]) => !PREFERRED.includes(k)),
  ].slice(0, 5);
  if (ordered.length < 3) return null;

  const CX = 110, CY = 104, R = 74;
  const n = ordered.length;
  const angle = (i: number) => (-90 + (i * 360) / n) * (Math.PI / 180);
  const pt = (i: number, r: number) => [CX + r * Math.cos(angle(i)), CY + r * Math.sin(angle(i))] as const;
  const poly = (r: number) => ordered.map((_, i) => pt(i, r).map(v => v.toFixed(1)).join(",")).join(" ");

  const SHORT: Record<string, string> = {
    "Valoración": "Valoración", "Rentabilidad": "Rentabilidad", "Solidez Financiera": "Solidez",
    "Calidad de Ganancias": "Calidad", "Crecimiento": "Crecimiento",
  };

  const areaPoints = ordered
    .map(([, cat], i) => {
      const frac = cat.max > 0 ? Math.max(0.04, cat.score / cat.max) : 0.04;
      return pt(i, R * frac).map(v => v.toFixed(1)).join(",");
    })
    .join(" ");

  return (
    <svg viewBox="0 0 220 208" className="radar-svg">
      <g>
        {[0.25, 0.5, 0.75, 1].map(k => (
          <polygon key={k} className="rd-ring" points={poly(R * k)} />
        ))}
        {ordered.map((_, i) => {
          const [x, y] = pt(i, R);
          return <line key={i} className="rd-axis" x1={CX} y1={CY} x2={x} y2={y} />;
        })}
      </g>
      <polygon className="rd-area" points={areaPoints} />
      {ordered.map(([, cat], i) => {
        const frac = cat.max > 0 ? Math.max(0.04, cat.score / cat.max) : 0.04;
        const [x, y] = pt(i, R * frac);
        return <circle key={i} className="rd-dot" cx={x} cy={y} r={3} />;
      })}
      <g>
        {ordered.map(([key], i) => {
          const [x, y] = pt(i, R + 22);
          const cos = Math.cos(angle(i));
          const anchor = Math.abs(cos) < 0.3 ? "middle" : cos > 0 ? "start" : "end";
          return (
            <text key={key} className="rd-lab" x={x.toFixed(1)} y={(y + 3).toFixed(1)} textAnchor={anchor}>
              {SHORT[key] || key}
            </text>
          );
        })}
      </g>
    </svg>
  );
}

/* ── Salud financiera (sector financiero: reemplaza al Altman) ── */
function FinancialHealthCard({ data }: { data: { score: number; level: string; interpretation?: string } }) {
  const color = data.level === "STRONG" || data.level === "GOOD" ? "#0cc06c"
    : data.level === "NEUTRAL" ? "#fbbf24" : "#ff4d4d";
  const label = data.level === "STRONG" ? "Muy sólida" : data.level === "GOOD" ? "Buena"
    : data.level === "NEUTRAL" ? "Neutral" : "Débil";
  return (
    <div className="rounded-xl border border-white/[0.06] bg-[#0a0a0d]/85 p-5">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-1.5">
          <span className="text-sm text-zinc-400 font-medium">Salud Financiera · sector financiero</span>
          <InfoTooltip content={EVALUATION.financial_health} value={data.score} valueLabel={`${data.score}/10`} />
        </div>
        <span
          className="text-[10px] font-semibold px-2 py-0.5 rounded-md"
          style={{ background: `${color}15`, color, border: `1px solid ${color}25` }}
        >
          {label}
        </span>
      </div>
      <div className="text-4xl font-black tabular-nums mb-2" style={{ color }}>
        {data.score}<span className="text-lg text-zinc-600 font-normal">/10</span>
      </div>
      {data.interpretation && (
        <p className="text-xs text-zinc-500 leading-relaxed">{data.interpretation}</p>
      )}
      <p className="text-[10px] text-zinc-600 mt-2">
        Evalúa ROA/ROE bancarios, apalancamiento, crecimiento del valor en libros y dividendo.
      </p>
    </div>
  );
}

function ZScoreCard({ data }: { data: { z_score: number; zone: string; interpretation: string; model?: string; details?: Record<string, unknown> } }) {
  const details = data.details || {};
  const isNotApplicable = (details.reason as string) === "financial_sector";
  const warnings = (details.warnings as string[]) || [];

  if (isNotApplicable) {
    return (
      <div className="rounded-xl border border-white/[0.06] bg-[#0a0a0d]/85 p-5">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="text-sm text-zinc-400 font-medium">Altman Z-Score</span>
            <InfoTooltip content={EVALUATION.altman_z} />
          </div>
          <span
            className="text-[10px] font-semibold px-2 py-0.5 rounded-md"
            style={{ background: "#6b728015", color: "#a1a1aa", border: "1px solid #6b728025" }}
          >
            No Aplicable
          </span>
        </div>
        <div className="text-4xl font-black tabular-nums mb-2 text-zinc-600">
          N/A
        </div>
        <p className="text-xs text-zinc-500 leading-relaxed">{data.interpretation}</p>
        {warnings.length > 0 && (
          <div className="mt-3 space-y-1 bg-zinc-900/50 rounded-lg p-3">
            {warnings.map((w, i) => (
              <p key={i} className="text-[10px] text-zinc-400 leading-relaxed">• {w}</p>
            ))}
          </div>
        )}
      </div>
    );
  }

  const color = data.zone === "safe" ? "#0cc06c" : data.zone === "grey" ? "#fbbf24" : "#ff4d4d";
  const zoneLabel = data.zone === "safe" ? "Zona Segura" : data.zone === "grey" ? "Zona Gris" : "Zona Riesgo";
  const safeT = (details.safe_threshold as number) || 2.99;
  const greyT = (details.grey_threshold as number) || 1.81;

  return (
    <div className="rounded-xl border border-white/[0.06] bg-[#0a0a0d]/85 p-5">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-sm text-zinc-400 font-medium">Altman Z-Score</span>
          <InfoTooltip content={EVALUATION.altman_z} value={data.z_score} valueLabel={data.z_score.toFixed(2)} />
        </div>
        <span
          className="text-[10px] font-semibold px-2 py-0.5 rounded-md"
          style={{ background: `${color}15`, color, border: `1px solid ${color}25` }}
        >
          {zoneLabel}
        </span>
      </div>
      <div className="text-4xl font-black tabular-nums mb-2" style={{ color }}>
        {data.z_score.toFixed(2)}
      </div>
      {data.model && (
        <p className="text-[10px] text-zinc-500 font-medium mb-1">{data.model}</p>
      )}
      <p className="text-xs text-zinc-500 leading-relaxed">{data.interpretation}</p>
      <p className="text-[10px] text-zinc-600 mt-2">
        {data.zone === "safe" ? `Z > ${safeT} = bajo riesgo de bancarrota` :
         data.zone === "grey" ? `${greyT} < Z < ${safeT} = zona de incertidumbre` :
         `Z < ${greyT} = alto riesgo de bancarrota`}
      </p>
      {warnings.length > 0 && (
        <div className="mt-2 space-y-0.5">
          {warnings.map((w, i) => (
            <p key={i} className="text-[10px] text-amber-500/70">⚠ {w}</p>
          ))}
        </div>
      )}
    </div>
  );
}

function FScoreCard({ data }: { data: { score: number; max_score: number; level: string; interpretation: string; details?: Record<string, { passed: boolean; detail: string }>; fiscal_year?: string } }) {
  const color =
    data.score >= 8 ? "#0cc06c" :
    data.score >= 6 ? "#22c55e" :
    data.score >= 4 ? "#fbbf24" :
    data.score >= 2 ? "#f97316" :
    "#ff453a";
  const details = data.details;

  return (
    <div className="rounded-xl border border-white/[0.06] bg-[#0a0a0d]/85 p-5">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-sm text-zinc-400 font-medium">Piotroski F-Score</span>
          <InfoTooltip content={EVALUATION.piotroski} value={data.score} valueLabel={`${data.score}/${data.max_score}`} />
        </div>
        <div className="flex items-center gap-2">
          {data.fiscal_year && (
            <span className="text-[9px] text-zinc-500 tabular-nums">{data.fiscal_year}</span>
          )}
          <span
            className="text-[10px] font-semibold px-2 py-0.5 rounded-md"
            style={{ background: `${color}15`, color, border: `1px solid ${color}25` }}
          >
            {data.level}
          </span>
        </div>
      </div>
      <div className="text-4xl font-black tabular-nums mb-2" style={{ color }}>
        {data.score}<span className="text-lg text-zinc-600 font-normal">/{data.max_score}</span>
      </div>
      <p className="text-xs text-zinc-500 leading-relaxed">{data.interpretation}</p>
      <p className="text-[10px] text-zinc-600 mt-2">
        {data.score >= 8 ? "8-9 = fortaleza financiera excelente" :
         data.score >= 6 ? "6-7 = empresa fuerte" :
         data.score >= 4 ? "4-5 = neutral" :
         data.score >= 2 ? "2-3 = señales de debilidad" :
         "0-1 = deterioro severo"}
      </p>

      {/* Criteria breakdown */}
      {details && Object.keys(details).length > 0 && (
        <div className="mt-4 pt-3 border-t border-white/[0.04] space-y-1.5">
          {Object.entries(details).map(([key, criterion]) => (
            <div key={key} className="flex items-start gap-2 text-[11px]">
              <span className={`shrink-0 mt-0.5 ${criterion.passed ? "text-green-400" : "text-red-400"}`}>
                {criterion.passed ? "✓" : "✗"}
              </span>
              <span className="text-zinc-400">{criterion.detail || key}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function Pill({ count, label, color }: { count: number; label: string; color: string }) {
  return (
    <div
      className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium"
      style={{ background: `${color}08`, border: `1px solid ${color}20`, color }}
    >
      <span className="text-sm font-bold tabular-nums">{count}</span>
      <span>{label}</span>
    </div>
  );
}

function AlertGroup({ title, color, items }: {
  title: string;
  color: string;
  items: Array<{ category: string; reason: string; detail: string }>;
}) {
  return (
    <div className="mb-6 last:mb-0">
      <h5 className="text-xs font-medium mb-3" style={{ color }}>{title}</h5>
      <div className="space-y-1.5">
        {items.map((alert, i) => (
          <div
            key={i}
            className="rounded-lg px-4 py-3"
            style={{ background: `${color}06`, border: `1px solid ${color}12` }}
          >
            <div className="text-sm text-zinc-200 font-medium">
              {alert.category}: {alert.reason}
            </div>
            <p className="text-xs text-zinc-500 mt-0.5">{alert.detail}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
