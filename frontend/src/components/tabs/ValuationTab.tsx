"use client";

import type { Display } from "@/lib/api";
import { Collapsible, DataTable, Help, Intro, Note, Panel, PanelTitle, Pill } from "../ui";

// Clase de cada una de las 5 bandas de color del grid (display.sensitivity: índice 0 = muy por
// encima del precio … 4 = muy por debajo). Solo traduce el índice del backend a una clase.
const GRID_CLASS = ["cell-strong-buy", "cell-buy", "cell-fair", "cell-sell", "cell-strong-sell"];

export default function ValuationTab({ display }: { display: Display }) {
  const V = display.sections.valuation;
  const tips = display.tooltips;
  const block = display.sections.institutional.breakdown?.categories.find((c) => c.group === "price");
  const sens = V.sensitivity;
  const conf = display.confidence;

  return (
    <div className="space-y-4">
      <Intro text={V.intro} />
      <Panel>
        <PanelTitle>Múltiplos frente a la referencia {display.benchmark.ref}</PanelTitle>
        <DataTable columns={V.columns} rows={V.rows} tooltips={tips} readings={display.readings} withBenchmark />
        <Note>{V.market_note}</Note>
        <Note>{V.provisional_note}</Note>
        <Note>{V.normalization_note}</Note>
      </Panel>

      {block && (
        <Panel>
          <PanelTitle aside={<Help k="multiples_block" title="Bloque de múltiplos" />}>
            Cómo puntúa Valoración · {block.conclusive ? `${block.score}/${block.max}` : "no concluyente"}
          </PanelTitle>
          <ul className="fz-adj-list">
            {block.items.map((it, i) => (
              <li key={i} className={it.in_block ? "is-member" : ""}>
                <span className="fz-adj-m">
                  {it.metric}{it.value && <span className="text-zinc-500"> ({it.value})</span>}
                  {it.in_block && <span className="fz-adj-tag">miembro del bloque</span>}
                </span>
                <span className={`fz-adj-s tone-${it.tone} fz-tone-fg`}>{it.sign}</span>
                <span className="fz-adj-r">{it.reason}</span>
              </li>
            ))}
          </ul>
          <Note>Los miembros del bloque muestran su ajuste individual entre paréntesis: puntúan a través del Bloque de múltiplos.</Note>
        </Panel>
      )}

      <Panel>
        <PanelTitle>Valor intrínseco</PanelTitle>
        <Intro text={V.intrinsic.intro} />
        <DataTable columns={["CONCEPTO", "VALOR", "LECTURA"]} rows={V.intrinsic.rows} tooltips={tips} />
        <Note>{V.intrinsic.graham_note}</Note>
        {V.dcf_params && <Note>{V.dcf_params}</Note>}
        {V.dcf_reliability && (
          <div className="mt-3 flex flex-wrap items-start gap-2">
            {V.dcf_reliability_tone && <Pill tone={V.dcf_reliability_tone}>Fiabilidad del DCF: {V.dcf_reliability_level}</Pill>}
            <p className="fz-note !mt-0 flex-1 min-w-[220px]">{V.dcf_reliability}</p>
          </div>
        )}
        <Note>{V.dcf_missing}</Note>
        <Note>{V.ke_note}</Note>
        {V.wacc_breakdown && (
          <div className="mt-3">
            <Collapsible summary="Desglose del WACC">
              <dl className="fz-kv">
                {V.wacc_breakdown.map((w) => (
                  <div key={w.label}><dt>{w.label}</dt><dd>{w.value}</dd></div>
                ))}
              </dl>
              <Note>{V.wacc_note}</Note>
            </Collapsible>
          </div>
        )}
      </Panel>

      {sens && (
        <Panel>
          <PanelTitle aside={<Help k="sensitivity" title="Sensibilidad del valor justo" />}>Sensibilidad del valor justo</PanelTitle>
          <p className="fz-note !mt-0 mb-3">{sens.intro}</p>
          <div className="overflow-x-auto -mx-1 px-1">
            <table className="fz-grid">
              <thead>
                <tr><th>{sens.corner}</th>{sens.columns.map((c) => <th key={c}>{c}</th>)}</tr>
              </thead>
              <tbody>
                {sens.rows.map((r) => (
                  <tr key={r.label}>
                    <th>{r.label}</th>
                    {r.cells.map((c, j) => (
                      <td key={j} className={`${c.band != null ? GRID_CLASS[c.band] : ""} ${c.base ? "is-base" : ""}`}>
                        {c.value}
                        {c.base && <span className="sr-only"> (escenario base)</span>}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="fz-grid-legend">
            {sens.band_labels.map((l, i) => (
              <span key={l}><i className={GRID_CLASS[i]} />{l}</span>
            ))}
            <span><i className="is-base-swatch" />Escenario base</span>
          </div>
          <Note>{sens.note}</Note>
        </Panel>
      )}

      {conf && (
        <Panel>
          <PanelTitle aside={<Help k="confidence" title="Confianza del veredicto" />}>Confianza del veredicto</PanelTitle>
          <div className="fz-conf">
            {conf.dimensions.map((d) => (
              <div key={d.key} className="fz-conf-row">
                <span className="fz-conf-l">{d.label}</span>
                <span className="fz-conf-lv">{d.level}</span>
                <span className="fz-conf-t">{d.text}</span>
              </div>
            ))}
          </div>
          <Note>{conf.summary}</Note>
        </Panel>
      )}
    </div>
  );
}
