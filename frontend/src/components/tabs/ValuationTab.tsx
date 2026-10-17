"use client";

import type { Display } from "@/lib/api";
import { useGrow } from "@/lib/useGrow";
import { ChartPanel, DcfComposition, FairValueScale, MultiplesView, ReadingLines } from "../charts";
import { Collapsible, DataTable, Help, Note, Pill } from "../ui";

// Clase de cada una de las 5 bandas de color del grid (display.sensitivity: índice 0 = muy por
// encima del precio … 4 = muy por debajo). Solo traduce el índice del backend a una clase.
const GRID_CLASS = ["cell-strong-buy", "cell-buy", "cell-fair", "cell-sell", "cell-strong-sell"];

/**
 * Valoración: primero la respuesta visual (precio frente al valor razonable con sus
 * zonas y los múltiplos frente a la referencia), después 2–3 líneas de lectura y,
 * desplegado a demanda, el detalle técnico (tablas, bloque, DCF, sensibilidad).
 */
export default function ValuationTab({ display }: { display: Display }) {
  const V = display.sections.valuation;
  const C = display.charts.valuation;
  const tips = display.tooltips;
  const grown = useGrow();
  const block = display.sections.institutional.breakdown?.categories.find((c) => c.group === "price");
  const sens = V.sensitivity;
  const conf = display.confidence;
  const refShort = display.benchmark.short;

  return (
    <div className="space-y-4">
      <ChartPanel tone={C.fair_value.badge?.tone ?? null} grown={grown}>
        <FairValueScale fv={C.fair_value} grown={grown} tips={tips} />
        {C.dcf_composition && (
          <div className="mt-6">
            <div className="cz-head !mb-2">
              <span className="cz-title">De dónde sale el valor razonable</span>
              <span className="cz-hint">explícito frente a terminal</span>
            </div>
            <DcfComposition comp={C.dcf_composition} grown={grown} />
          </div>
        )}
        <ReadingLines lines={[V.intrinsic.intro]} />
      </ChartPanel>

      <ChartPanel grown={grown} title={<>Múltiplos frente a la referencia {display.benchmark.ref}</>}>
        <MultiplesView items={C.multiples} block={C.block} scored={C.scored} grown={grown} tips={tips} refShort={refShort} />
        <ReadingLines lines={[V.intro]} />
        <Note>{V.market_note}</Note>
        <Note>{V.reference_note}</Note>
      </ChartPanel>

      <div className="cz-more">
        <Collapsible summary="Tabla de múltiplos">
          <DataTable columns={V.columns} rows={V.rows} tooltips={tips} readings={display.readings} withBenchmark />
          <Note>{V.normalization_note}</Note>
        </Collapsible>

        {block && (
          <Collapsible summary={`Cómo puntúa Valoración · ${block.conclusive ? `${block.score}/${block.max}` : "no concluyente"}`}>
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
          </Collapsible>
        )}

        {V.reverse_dcf && (
          <div className="mt-4">
            <div className="fz-kicker mb-1">{V.reverse_dcf.title}</div>
            {V.reverse_dcf.lines.map((ln, i) => (
              <div key={i} className="mt-2 flex flex-wrap items-start gap-2">
                {ln.label && <Pill tone={ln.tone}>{ln.label}</Pill>}
                <p className="fz-note !mt-0 flex-1 min-w-[220px]">{ln.text}</p>
              </div>
            ))}
            <Note>{V.reverse_dcf.role} {V.reverse_dcf.method}</Note>
          </div>
        )}

        {V.premortem && (
          <div className="mt-4">
            <div className="fz-kicker mb-1">{V.premortem.title}</div>
            <ul className="list-disc pl-5 space-y-1">
              {V.premortem.items.map((t, i) => (
                <li key={i} className="fz-note !mt-0">{t}</li>
              ))}
            </ul>
            <Note>{V.premortem.note}</Note>
          </div>
        )}

        <Collapsible summary="Valor intrínseco: cifras y supuestos">
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
              <div className="fz-kicker mb-1">Desglose del WACC</div>
              <dl className="fz-kv">
                {V.wacc_breakdown.map((w) => (
                  <div key={w.label}><dt>{w.label}</dt><dd>{w.value}</dd></div>
                ))}
              </dl>
              <Note>{V.wacc_note}</Note>
            </div>
          )}
        </Collapsible>

        {sens && (
          <Collapsible summary="Sensibilidad del valor justo">
            <p className="fz-note !mt-0 mb-3 flex items-center gap-1">{sens.intro}<Help k="sensitivity" title="Sensibilidad del valor justo" /></p>
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
          </Collapsible>
        )}

        {conf && (
          <Collapsible summary="Confianza del veredicto">
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
          </Collapsible>
        )}
      </div>
    </div>
  );
}
