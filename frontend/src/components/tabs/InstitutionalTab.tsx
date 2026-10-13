"use client";

import type { Display } from "@/lib/api";
import { Help, Note, Panel, PanelTitle, Pill, StateTag, ToneBar, toneClass } from "../ui";

export default function InstitutionalTab({ display }: { display: Display }) {
  const I = display.sections.institutional;
  const tips = display.tooltips;
  return (
    <div className="space-y-4">
      {I.cards.map((c) => (
        <div key={c.key} className={`fz-model ${toneClass(c.state === "con_dato" ? c.tone : null)}`}>
          <div className="fz-model-score">
            <span className="fz-model-v fz-tone-fg">{c.value}</span>
            {c.state === "con_dato" ? <Pill tone={c.tone}>{c.subtitle}</Pill> : <StateTag state={c.state} text={c.subtitle} />}
          </div>
          <div className="min-w-0">
            <h3 className="text-white font-semibold flex items-center gap-2">
              {c.title}
              <Help k={c.key} title={c.title} bands={c.state === "con_dato" ? tips[c.key] : undefined}
                value={c.state === "con_dato" ? c.value : undefined}
                reading={c.state === "con_dato" ? { label: c.subtitle, tone: c.tone } : null} />
            </h3>
            <p className="mt-1 text-[13.5px] leading-relaxed text-zinc-400">{c.body}</p>
          </div>
        </div>
      ))}

      {I.piotroski_criteria.length > 0 && (
        <Panel>
          <PanelTitle>Criterios del Piotroski F-Score</PanelTitle>
          <ul className="fz-crit">
            {I.piotroski_criteria.map((c) => (
              <li key={c.key}>
                <span className="fz-crit-l">{c.label}</span>
                <span className="fz-crit-d">{c.detail}</span>
                <Pill tone={c.tone}>{c.status}</Pill>
              </li>
            ))}
          </ul>
        </Panel>
      )}

      {I.breakdown && (
        <Panel>
          <PanelTitle aside={<Help k="breakdown" title="Desglose por categoría" bands={tips.category} />}>
            Desglose por categoría
          </PanelTitle>
          <p className="fz-note !mt-0 mb-4">
            {I.breakdown.intro}{I.breakdown.coverage_notes.length > 0 && ` ${I.breakdown.coverage_notes.join(" · ")}.`}
          </p>
          <div className="space-y-5">
            {I.breakdown.categories.map((cat) => (
              <div key={cat.name}>
                <div className="fz-bd-head">
                  <span className="text-white font-semibold">{cat.name}</span>
                  {cat.conclusive ? (
                    <>
                      <ToneBar pct={cat.pct} tone={cat.tone} />
                      <span className={`fz-bd-score ${toneClass(cat.tone)} fz-tone-fg`}>{cat.score}/{cat.max}</span>
                    </>
                  ) : (
                    <>
                      <span className="state-tag state-sin_dato">{cat.text}</span>
                      <span className="fz-bd-score">n/c</span>
                    </>
                  )}
                </div>
                <ul className="fz-adj-list">
                  {cat.items.map((it, i) => (
                    <li key={i} className={it.in_block ? "is-member" : ""}>
                      <span className="fz-adj-m">
                        {it.metric}{it.value && <span className="text-zinc-500"> ({it.value})</span>}
                      </span>
                      <span className={`fz-adj-s tone-${it.tone} fz-tone-fg`}>
                        {it.state === "no_aplica" ? <StateTag state="no_aplica" /> : it.sign}
                      </span>
                      <span className="fz-adj-r">{it.reason}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
          <Note>Entre paréntesis: ajuste individual de un miembro del Bloque de múltiplos (puntúa a través del bloque).</Note>
        </Panel>
      )}
    </div>
  );
}
