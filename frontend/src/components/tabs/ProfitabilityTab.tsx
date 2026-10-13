"use client";

import type { Display } from "@/lib/api";
import { DataTable, Intro, Note, Panel, PanelTitle } from "../ui";

export default function ProfitabilityTab({ display }: { display: Display }) {
  const P = display.sections.profitability;
  return (
    <div className="space-y-4">
      <Intro text={P.intro} />
      <Panel>
        <PanelTitle>Rentabilidad y eficiencia</PanelTitle>
        <DataTable columns={P.columns} rows={P.rows} tooltips={display.tooltips} readings={display.readings} withBenchmark />
        <Note>{P.divergence_note}</Note>
      </Panel>
      <Panel>
        <PanelTitle>Cifras del ejercicio</PanelTitle>
        <dl className="fz-kv">
          {P.figures.flatMap((row) => [[row[0], row[1]], [row[2], row[3]]]).map(([k, v]) => (
            <div key={k}><dt>{k}</dt><dd>{v}</dd></div>
          ))}
        </dl>
      </Panel>
    </div>
  );
}
