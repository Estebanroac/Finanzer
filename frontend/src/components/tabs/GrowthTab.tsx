"use client";

import type { Display } from "@/lib/api";
import { useGrow } from "@/lib/useGrow";
import { ChartPanel, GrowthBars, Range52Bar, ReadingLines } from "../charts";
import { Collapsible, DataTable, Help, Note } from "../ui";

/** Crecimiento: CAGR que puntúan y el rango de 52 semanas (contexto); tabla y componentes a demanda. */
export default function GrowthTab({ display }: { display: Display }) {
  const G = display.sections.growth;
  const grown = useGrow();
  const r = G.range52;

  return (
    <div className="space-y-4">
      <ChartPanel grown={grown} title="Crecimiento anual compuesto · 3 años">
        <GrowthBars bars={display.charts.growth} grown={grown} />
        <ReadingLines lines={[G.intro]} />
        <Note>{G.eps_vs_revenue_note}</Note>
      </ChartPanel>

      {r && (
        <ChartPanel grown={grown}
          title={<>Rango de precio · 52 semanas<Help k="pos52" title="Rango de 52 semanas" bands={display.tooltips.pos52}
            value={`${Math.round(r.pos)}%`} reading={r.reading ? { label: r.reading.label, tone: r.reading.tone } : null} /></>}
          aside={r.reading ? <span className="cz-price-chip">{r.reading.label}</span> : undefined}>
          <Range52Bar r={r} grown={grown} />
          <p className="mt-3 text-[13px] text-zinc-400">{r.caption}</p>
          <ReadingLines lines={[r.reading ? `${r.reading.text}.` : null, `Contexto: ${r.axis}`]} />
          <p className="fz-note">{r.zones_note}</p>
        </ChartPanel>
      )}

      <div className="cz-more">
        <Collapsible summary="Tabla de crecimiento y retorno al accionista">
          <DataTable columns={G.columns} rows={G.rows} tooltips={display.tooltips} readings={display.readings} />
        </Collapsible>
        {G.score_components.length > 0 && (
          <Collapsible summary="Lo que puntúa Crecimiento">
            <ul className="fz-adj-list">
              {G.score_components.map((c, i) => (
                <li key={i}>
                  <span className="fz-adj-m">{c.metric}{c.value && <span className="text-zinc-500"> ({c.value})</span>}</span>
                  <span className="fz-adj-r">{c.reason}</span>
                </li>
              ))}
            </ul>
          </Collapsible>
        )}
      </div>
    </div>
  );
}
