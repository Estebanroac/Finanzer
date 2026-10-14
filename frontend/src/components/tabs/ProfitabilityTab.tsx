"use client";

import type { Display } from "@/lib/api";
import { useGrow } from "@/lib/useGrow";
import { BenchList, ChartPanel, FlowCards, MarginLadder, NotApplicable, ReadingLines } from "../charts";
import { Collapsible, DataTable, Help, Note, toneClass } from "../ui";

/** Rentabilidad: retornos frente al sector, cascada de márgenes y flujo de resultados; tablas a demanda. */
export default function ProfitabilityTab({ display }: { display: Display }) {
  const P = display.sections.profitability;
  const C = display.charts.profitability;
  const tips = display.tooltips;
  const grown = useGrow();
  const refShort = display.benchmark.profile === "market" ? "mercado" : "sector";
  const sp = C.spread;

  return (
    <div className="space-y-4">
      <div className="cz-grid2">
        <ChartPanel grown={grown} title="Retornos sobre el capital">
          <BenchList items={C.returns} grown={grown} tips={tips} refShort={refShort} />
          <div className="mt-3">
            {sp.state === "con_dato" ? (
              <div className={`cz-g-note ${toneClass(sp.tone)}`}>
                <span className="fz-tone-fg font-bold tabular-nums whitespace-nowrap">{sp.value_txt}</span>
                <span>
                  <b className="text-zinc-200">ROIC − WACC</b>
                  <Help k="roic_wacc_spread" title="ROIC − WACC" bands={tips.roic_wacc_spread} value={sp.value_txt}
                    reading={sp.reading ? { label: sp.reading, tone: sp.tone ?? null } : null} text={sp.text} />
                  {sp.reading && <> · <span className="fz-tone-fg font-semibold">{sp.reading}</span></>}
                </span>
              </div>
            ) : (
              <NotApplicable inline state={sp.state} title="ROIC − WACC" text={sp.text} />
            )}
          </div>
        </ChartPanel>

        <ChartPanel grown={grown} title="Márgenes" aside={<span className="cz-hint">de cada $1 de ingreso</span>}>
          <MarginLadder revenueTxt={C.margin_ladder.revenue_txt} steps={C.margin_ladder.steps} grown={grown} tips={tips} />
        </ChartPanel>
      </div>

      <ChartPanel grown={grown} title="Flujo de resultados · últimos doce meses">
        <FlowCards flows={display.charts.results_flow} grown={grown} />
        <ReadingLines lines={[P.intro]} />
        <Note>{P.divergence_note}</Note>
      </ChartPanel>

      <div className="cz-more">
        <Collapsible summary={`Márgenes frente a la referencia del ${refShort}`}>
          <BenchList items={C.margins} grown={grown} tips={tips} refShort={refShort} />
        </Collapsible>
        <Collapsible summary="Tabla de rentabilidad y eficiencia">
          <DataTable columns={P.columns} rows={P.rows} tooltips={tips} readings={display.readings} withBenchmark />
        </Collapsible>
        <Collapsible summary="Cifras del ejercicio">
          <dl className="fz-kv">
            {P.figures.flatMap((row) => [[row[0], row[1]], [row[2], row[3]]]).map(([k, v]) => (
              <div key={k}><dt>{k}</dt><dd>{v}</dd></div>
            ))}
          </dl>
        </Collapsible>
      </div>
    </div>
  );
}
