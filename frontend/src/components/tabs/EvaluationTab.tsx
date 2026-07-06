"use client";

import type { StockAnalysis } from "@/lib/api";
import { getScoreColor } from "@/lib/api";
import InfoTooltip from "@/components/InfoTooltip";
import { EVALUATION } from "@/lib/tooltips";

export default function EvaluationTab({ data }: { data: StockAnalysis }) {
  const alerts = data.alerts;
  const score = data.score;
  const altmanZ = data.altman_z;
  const piotroskiF = data.piotroski_f;

  return (
    <div className="space-y-8">
      {/* Institutional metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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
                              className="shrink-0 font-mono font-semibold text-[11px]"
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
          <InfoTooltip content={EVALUATION.altman_z} />
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
  const color = data.score >= 7 ? "#0cc06c" : data.score >= 4 ? "#fbbf24" : "#ff4d4d";
  const details = data.details;

  return (
    <div className="rounded-xl border border-white/[0.06] bg-[#0a0a0d]/85 p-5">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-sm text-zinc-400 font-medium">Piotroski F-Score</span>
          <InfoTooltip content={EVALUATION.piotroski} />
        </div>
        <div className="flex items-center gap-2">
          {data.fiscal_year && (
            <span className="text-[9px] text-zinc-500 font-mono">{data.fiscal_year}</span>
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
        {data.score >= 7 ? "7-9 = fortaleza financiera" :
         data.score >= 4 ? "4-6 = neutral" :
         "0-3 = señales de debilidad"}
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
