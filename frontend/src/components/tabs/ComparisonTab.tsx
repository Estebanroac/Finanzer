"use client";

import type { ComparisonItem, Display } from "@/lib/api";
import { useGrow } from "@/lib/useGrow";
import { ChartPanel, NotApplicable, Ring } from "../charts";
import { Help, Note, toneClass } from "../ui";

/**
 * Comparativa con la referencia (sector o mercado): solo las métricas que aplican al
 * arquetipo y tienen referencia (display.charts.comparison). Cada barra parte del eje de
 * la referencia hacia el lado "mejor" o "peor" según la dirección de la métrica; la
 * lectura y el tono son los de las tablas. Las medianas son provisionales: se avisa.
 */
export default function ComparisonTab({ display }: { display: Display }) {
  const C = display.charts.comparison;
  const grown = useGrow();
  const tips = display.tooltips;
  // Escala común: la mayor brecha (en %) ocupa media pista.
  const peak = Math.max(...C.groups.flatMap((g) => g.items.map((i) => Math.abs(i.gap_pct))), 0) || 1;
  const ringTone = C.groups.flatMap((g) => g.items).length ? "pos" : null;

  return (
    <div className="space-y-4">
      <ChartPanel grown={grown}>
        <div className="cz-cmp-sum">
          <Ring value={C.better} max={C.total || 1} tone={ringTone} size={116} caption={`de ${C.total}`} />
          <div className="min-w-0 flex-1">
            <div className="cz-title mb-1">Frente a la referencia {C.ref}</div>
            <p className="text-[17px] font-semibold text-white leading-snug">
              {C.better} de {C.total} métricas con lectura favorable frente a la referencia
            </p>
            {C.note && (
              <div className="mt-3 cz-g-note tone-warn">
                <span className="fz-tone-fg font-bold" aria-hidden="true">!</span>
                <span>{C.note}</span>
              </div>
            )}
            {C.market_note && <Note>{C.market_note}</Note>}
          </div>
        </div>
      </ChartPanel>

      {C.groups.length === 0 && (
        <NotApplicable state="sin_dato" title="Comparativa" text="ninguna métrica aplicable a este tipo de empresa tiene referencia" />
      )}

      {C.groups.map((g) => (
        <ChartPanel key={g.title} grown={grown} title={g.title}
          aside={<span className="cz-hint">{g.items.filter((i) => i.tone === "pos").length} de {g.items.length} favorables</span>}>
          <div className="cz-cmp-axis" aria-hidden="true"><span>◀ peor</span><b>Referencia</b><span>mejor ▶</span></div>
          {g.items.map((i) => <CmpRow key={i.key} i={i} peak={peak} grown={grown} tips={tips} />)}
        </ChartPanel>
      ))}
    </div>
  );
}

function CmpRow({ i, peak, grown, tips }: { i: ComparisonItem; peak: number; grown: boolean; tips: Display["tooltips"] }) {
  // Lado "mejor": brecha positiva si más es mejor, negativa si menos es mejor (dirección, no umbral).
  const better = (i.higher_is_better ? i.gap_pct : -i.gap_pct) > 0;
  const w = (Math.min(Math.abs(i.gap_pct), peak) / peak) * 50;
  return (
    <div className={`cz-cmp-row ${toneClass(i.tone)}`}>
      <div className="cz-cmp-head">
        <span className="cz-cmp-k inline-flex items-center">
          {i.label}
          <Help k={i.key} title={i.label} bands={tips[i.key]} value={i.value_txt} reading={{ label: i.reading, tone: i.tone }} text={i.text} />
        </span>
        <span>
          <span className="cz-cmp-v">{i.value_txt}</span>
          <span className="cz-cmp-vs">vs {i.bench_txt}</span>
        </span>
      </div>
      <div className="cz-cmp-track" role="img" aria-label={`${i.label}: ${i.gap_txt ?? ""} frente a la referencia, ${i.reading}`}>
        <span className="cz-cmp-mid" aria-hidden="true" />
        <span className={`cz-cmp-bar ${better ? "is-right" : "is-left"}`} style={{ width: grown ? `${w}%` : 0 }} />
      </div>
      <div className="flex justify-between gap-3 text-[12px]">
        <span className="text-zinc-500 tabular-nums">{i.gap_txt}</span>
        <b className="fz-tone-fg font-semibold">{i.reading}</b>
      </div>
    </div>
  );
}
