"use client";

import { useEffect, useState } from "react";
import InfoTooltip from "./InfoTooltip";
import { SCORE_TOOLTIP } from "@/lib/tooltips";
import { getScoreColor, getScoreLabel } from "@/lib/api";

interface ScoreCardProps {
  score: number;
  maxScore: number;
  companyType: string;
  isGrowth: boolean;
}

export default function ScoreCard({ score, maxScore, companyType, isGrowth }: ScoreCardProps) {
  const pct = Math.round((score / maxScore) * 100);
  const color = getScoreColor(pct);
  const label = getScoreLabel(pct);

  // Gauge radial: el arco se dibuja (dashoffset 100 -> 100-pct) y el número
  // cuenta hacia arriba. Fallbacks por si la pestaña está en segundo plano.
  const [drawn, setDrawn] = useState(false);
  const [num, setNum] = useState(0);

  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) {
      setDrawn(true);
      setNum(pct);
      return;
    }
    const raf = requestAnimationFrame(() => setDrawn(true));
    const t0 = performance.now();
    const dur = 1200;
    let rid = 0;
    const tick = (now: number) => {
      const p = Math.min(1, (now - t0) / dur);
      const e = 1 - Math.pow(1 - p, 3);
      setNum(Math.round(pct * e));
      if (p < 1) rid = requestAnimationFrame(tick);
    };
    rid = requestAnimationFrame(tick);
    const safety = setTimeout(() => { setNum(pct); setDrawn(true); }, dur + 500);
    return () => {
      cancelAnimationFrame(raf);
      cancelAnimationFrame(rid);
      clearTimeout(safety);
    };
  }, [pct]);

  return (
    <div className="relative rounded-2xl border border-white/[0.06] bg-[#0a0a0d]/85 p-6 overflow-hidden h-full">
      {/* Glow del color del score */}
      <div
        className="absolute -top-[30%] -right-[20%] w-56 h-56 rounded-full blur-[70px] opacity-[0.13] pointer-events-none"
        style={{ background: color }}
      />

      <div className="relative flex items-center gap-6">
        {/* Gauge radial */}
        <div className="relative w-[150px] h-[150px] shrink-0">
          <svg width="150" height="150" viewBox="0 0 150 150" className="-rotate-90 overflow-visible">
            <circle cx="75" cy="75" r="62" fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="11" />
            <circle
              cx="75" cy="75" r="62" fill="none"
              stroke={color} strokeWidth="11" strokeLinecap="round"
              pathLength={100}
              strokeDasharray={100}
              strokeDashoffset={drawn ? 100 - pct : 100}
              style={{
                transition: "stroke-dashoffset 1.3s cubic-bezier(0.16,1,0.3,1)",
                filter: `drop-shadow(0 0 8px ${color}66)`,
              }}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <div className="text-[44px] font-bold leading-none tracking-[-0.04em] tabular-nums" style={{ color }}>
              {num}
            </div>
            <div className="text-[11px] text-[#6e6e73] uppercase tracking-[0.1em] mt-1">/ 100</div>
          </div>
        </div>

        {/* Nivel + tipo */}
        <div className="flex-1 min-w-0">
          {/* Etiqueta de EJE: deja explícito que este score mide CALIDAD
              FUNDAMENTAL (¿buena empresa?), distinto del precio (¿cara o barata?). */}
          <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 mb-2">
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold uppercase tracking-wider text-zinc-300 bg-white/[0.05] border border-white/[0.1]">
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" /></svg>
              Calidad fundamental
            </span>
            <span className="text-[11px] text-zinc-500">¿Es buena la empresa?</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-[17px] font-semibold" style={{ color }}>{label}</span>
            <InfoTooltip content={SCORE_TOOLTIP} size="md" />
          </div>
          <div className="text-xs text-zinc-500 mt-1">{score} de {maxScore} pts</div>

          <div className="flex gap-1.5 mt-3 flex-wrap">
            {isGrowth && (
              <span className="px-2 py-0.5 rounded-md text-[10px] font-medium bg-[#0cc06c]/10 text-[#0cc06c] border border-[#0cc06c]/20">
                Growth
              </span>
            )}
            <span className="px-2 py-0.5 rounded-md text-[10px] font-medium bg-white/[0.04] text-zinc-400 border border-white/[0.06]">
              {companyType}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
