"use client";

import type { Display } from "@/lib/api";
import { Note, Panel, PanelTitle } from "../ui";

/** Fase 5 (D5): contexto de mercado y lectura conductual. No puntúa: describe cómo se ha movido la acción, no qué
 *  hará; mismo tono neutro sea la señal buena o mala (efecto marco). */
export default function MarketTab({ display }: { display: Display }) {
  const M = display.sections.market;
  if (!M) {
    return <Panel><p className="fz-note">Sin serie de precios para el contexto de mercado.</p></Panel>;
  }
  return (
    <div className="space-y-4">
      <Panel>
        <PanelTitle>{M.title}</PanelTitle>
        <p className="fz-note !mt-0">{M.note}</p>
        {M.status_note && <p className="fz-note">{M.status_note}</p>}
        <dl className="mt-3 divide-y divide-white/[0.06]">
          {M.rows.map((r) => (
            <div key={r.key} className="py-2.5 grid grid-cols-1 sm:grid-cols-[13rem_6rem_1fr] gap-x-4 gap-y-1">
              <dt className="text-sm text-zinc-300">{r.label}</dt>
              <dd className="text-sm font-semibold text-white tabular-nums">{r.value}</dd>
              <dd className="text-[13px] text-zinc-400 leading-relaxed">{r.text}</dd>
            </div>
          ))}
        </dl>
      </Panel>
      {M.behavioral.length > 0 && (
        <Panel>
          <PanelTitle>{M.behavioral_title}</PanelTitle>
          <ul className="list-disc pl-5 space-y-1.5">
            {M.behavioral.map((t, i) => <li key={i} className="text-[13.5px] text-zinc-300 leading-relaxed">{t}</li>)}
          </ul>
        </Panel>
      )}
      {M.news.length > 0 && (
        <Panel>
          <PanelTitle>Titulares recientes</PanelTitle>
          <ul className="space-y-1.5">
            {M.news.map((n, i) => (
              <li key={i} className="text-[13px] text-zinc-400 leading-relaxed">
                <span className="text-zinc-500 tabular-nums">{n.date}</span> · {n.source}:{" "}
                {n.url ? <a href={n.url} target="_blank" rel="noopener noreferrer nofollow"
                  className="text-zinc-300 underline decoration-white/20 hover:decoration-white/60">{n.headline}</a>
                  : <span className="text-zinc-300">{n.headline}</span>}
              </li>
            ))}
          </ul>
        </Panel>
      )}
      {M.news_note && <Note>{M.news_note}</Note>}
      <Note>{M.pead_note} {M.source}</Note>
    </div>
  );
}
