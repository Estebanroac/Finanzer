"use client";

import type { Display } from "@/lib/api";
import { useGrow } from "@/lib/useGrow";
import { BalanceDonut, ChartPanel, GaugeView, NotApplicable, ReadingLines, RunwayView, groupNa } from "../charts";
import { Collapsible, DataTable, Note } from "../ui";

/** Solidez: medidores con las zonas de cada lectura y la estructura del balance; tabla a demanda. */
export default function SolvencyTab({ display }: { display: Display }) {
  const S = display.sections.solvency;
  const C = display.charts.solvency;
  const tips = display.tooltips;
  const grown = useGrow();

  return (
    <div className="space-y-4">
      <div className="cz-grid2">
        <ChartPanel grown={grown} title="Liquidez y deuda">
          {C.runway && (
            <div className="mb-2">
              <RunwayView rw={C.runway} grown={grown} tips={tips} />
            </div>
          )}
          {C.gauges.filter((g) => g.state === "con_dato").map((g) => <GaugeView key={g.key} g={g} grown={grown} tips={tips} />)}
          {/* Los que no aplican o no son significativos, agrupados por motivo (sin repetir el aviso). */}
          {groupNa(C.gauges.filter((g) => g.state !== "con_dato")).map((n) => (
            <div key={n.labels.join()} className="mt-3">
              <NotApplicable inline state={n.state} title={n.labels.join(", ")} text={n.text} />
            </div>
          ))}
          <ReadingLines lines={[S.intro]} />
        </ChartPanel>
        <ChartPanel grown={grown} title="Estructura del balance">
          <BalanceDonut s={C.structure} grown={grown} />
          <Note>{S.balance}</Note>
        </ChartPanel>
      </div>
      <div className="cz-more">
        <Collapsible summary="Tabla de solidez financiera">
          <DataTable columns={S.columns} rows={S.rows} tooltips={tips} readings={display.readings} />
        </Collapsible>
      </div>
    </div>
  );
}
