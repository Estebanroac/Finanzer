"use client";

import InfoTooltip from "./InfoTooltip";
import { SCORE_TOOLTIP } from "@/lib/tooltips";

interface ScoreCardProps {
  score: number;
  maxScore: number;
  level: string;
  companyType: string;
  isGrowth: boolean;
}

function getScoreColor(pct: number): string {
  if (pct >= 80) return "#00d632";
  if (pct >= 65) return "#4ade80";
  if (pct >= 50) return "#fbbf24";
  if (pct >= 35) return "#f97316";
  return "#ff4d4d";
}

function getScoreLabel(pct: number): string {
  if (pct >= 80) return "Excelente";
  if (pct >= 65) return "Favorable";
  if (pct >= 50) return "Neutral";
  if (pct >= 35) return "Precaución";
  return "Evitar";
}

function getScoreBg(pct: number): string {
  if (pct >= 80) return "rgba(0, 214, 50, 0.04)";
  if (pct >= 65) return "rgba(74, 222, 128, 0.04)";
  if (pct >= 50) return "rgba(251, 191, 36, 0.04)";
  if (pct >= 35) return "rgba(249, 115, 22, 0.04)";
  return "rgba(255, 77, 77, 0.04)";
}

export default function ScoreCard({ score, maxScore, level, companyType, isGrowth }: ScoreCardProps) {
  const pct = Math.round((score / maxScore) * 100);
  const color = getScoreColor(pct);
  const label = getScoreLabel(pct);

  return (
    <div
      className="relative rounded-2xl border border-white/[0.06] p-6 overflow-hidden"
      style={{ background: getScoreBg(pct) }}
    >
      {/* Glow */}
      <div
        className="absolute -top-20 -right-20 w-40 h-40 rounded-full blur-[60px] opacity-20 pointer-events-none"
        style={{ background: color }}
      />

      <div className="relative flex items-center gap-5">
        {/* Score */}
        <div className="shrink-0">
          <div className="flex items-start gap-1.5">
            <div className="text-5xl font-black tabular-nums" style={{ color }}>
              {pct}
            </div>
            <InfoTooltip content={SCORE_TOOLTIP} size="md" />
          </div>
          <div className="text-[11px] text-zinc-500 uppercase tracking-widest mt-0.5">/ 100</div>
        </div>

        <div className="w-px h-14 bg-white/[0.06]" />

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="text-sm font-semibold" style={{ color }}>{label}</div>
          <div className="text-xs text-zinc-500 mt-1">{score} de {maxScore} pts</div>

          <div className="flex gap-1.5 mt-2.5 flex-wrap">
            {isGrowth && (
              <span className="px-2 py-0.5 rounded-md text-[10px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                Growth
              </span>
            )}
            <span className="px-2 py-0.5 rounded-md text-[10px] font-medium bg-white/[0.04] text-zinc-400 border border-white/[0.06]">
              {companyType}
            </span>
          </div>
        </div>
      </div>

      {/* Progress bar */}
      <div className="mt-5 h-1.5 bg-white/[0.04] rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-1000 ease-out"
          style={{ width: `${pct}%`, background: `linear-gradient(90deg, ${color}cc, ${color})` }}
        />
      </div>
    </div>
  );
}
