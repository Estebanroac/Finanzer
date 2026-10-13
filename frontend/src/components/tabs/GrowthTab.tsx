"use client";

import type { Display, Range52 } from "@/lib/api";
import { DataTable, Help, Intro, Note, Panel, PanelTitle } from "../ui";

export default function GrowthTab({ display }: { display: Display }) {
  const G = display.sections.growth;
  return (
    <div className="space-y-4">
      <Intro text={G.intro} />
      <Panel>
        <PanelTitle>Crecimiento y retorno al accionista</PanelTitle>
        <DataTable columns={G.columns} rows={G.rows} tooltips={display.tooltips} readings={display.readings} />
        <Note>{G.eps_vs_revenue_note}</Note>
      </Panel>
      {G.score_components.length > 0 && (
        <Panel>
          <PanelTitle>Lo que puntúa Crecimiento</PanelTitle>
          <ul className="fz-adj-list">
            {G.score_components.map((c, i) => (
              <li key={i}>
                <span className="fz-adj-m">{c.metric}{c.value && <span className="text-zinc-500"> ({c.value})</span>}</span>
                <span className="fz-adj-r">{c.reason}</span>
              </li>
            ))}
          </ul>
        </Panel>
      )}
      {G.range52 && <Range52View r={G.range52} bands={display.tooltips.pos52} />}
    </div>
  );
}

/** Rango de 52 semanas: contexto de mercado, tramos en grises, sin juicio de precio. */
function Range52View({ r, bands }: { r: Range52; bands: Display["tooltips"][string] | undefined }) {
  return (
    <Panel>
      <PanelTitle aside={<Help k="pos52" title="Rango de 52 semanas" bands={bands} value={`${Math.round(r.pos)}%`}
        reading={r.reading ? { label: r.reading.label, tone: r.reading.tone } : null} />}>
        Rango de precio · 52 semanas
      </PanelTitle>
      <p className="fz-note !mt-0 mb-4"><b className="text-zinc-300">Contexto</b> · {r.axis}</p>
      {r.reading && <p className="text-[15px] text-zinc-300 mb-4">{r.reading.text[0].toUpperCase() + r.reading.text.slice(1)}.</p>}
      <div className="fz-r52">
        <div className="fz-r52-track">
          {r.zones.map((z, i) => (
            <span key={i} className={`fz-r52-zone ${i % 2 ? "is-mid" : ""}`} style={{ width: `${z.to - z.from}%` }} />
          ))}
          <span className="fz-r52-marker" style={{ left: `${r.pos}%` }} aria-label={`Posición ${Math.round(r.pos)}%`} />
        </div>
        <div className="flex justify-between text-[12px] tabular-nums text-zinc-500 mt-2">
          <span>{r.low}</span><span>{r.high}</span>
        </div>
      </div>
      <p className="text-center text-[13px] text-zinc-400 mt-3">
        {r.caption}{r.reading && <b className="text-zinc-200 ml-2">{r.reading.label}</b>}
      </p>
      <p className="text-center text-[11px] text-zinc-600 mt-1">{r.zones_note}</p>
    </Panel>
  );
}
