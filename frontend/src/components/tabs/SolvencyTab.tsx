"use client";

import type { Display } from "@/lib/api";
import { DataTable, Intro, Note, Panel, PanelTitle } from "../ui";

export default function SolvencyTab({ display }: { display: Display }) {
  const S = display.sections.solvency;
  return (
    <div className="space-y-4">
      <Intro text={S.intro} />
      <Panel>
        <PanelTitle>Solidez financiera</PanelTitle>
        <DataTable columns={S.columns} rows={S.rows} tooltips={display.tooltips} readings={display.readings} />
        <Note>{S.balance}</Note>
      </Panel>
    </div>
  );
}
