"use client";

import type { Display } from "@/lib/api";
import { Panel, toneClass } from "../ui";

export default function AlertsTab({ display }: { display: Display }) {
  const A = display.sections.alerts;
  const empty = A.groups.every((g) => g.items.length === 0);
  return (
    <div className="space-y-4">
      <p className="text-[15px]">
        <b className="tone-neg fz-tone-fg">{A.counts.red_flags}</b> riesgo{A.counts.red_flags !== 1 && "s"} ·{" "}
        <b className="tone-warn fz-tone-fg">{A.counts.warnings}</b> advertencia{A.counts.warnings !== 1 && "s"} ·{" "}
        <b className="tone-pos fz-tone-fg">{A.counts.strengths}</b> fortaleza{A.counts.strengths !== 1 && "s"}
      </p>
      {empty && <Panel><p className="text-zinc-400 text-sm">No se detectaron alertas significativas.</p></Panel>}
      {A.groups.filter((g) => g.items.length > 0).map((g) => (
        <Panel key={g.key} className={toneClass(g.tone)}>
          <h3 className="fz-tone-fg font-semibold mb-3">{g.title}</h3>
          <ul className="fz-alerts">
            {g.items.map((a, i) => (
              <li key={i}>
                <span className="fz-alert-dot fz-tone-bg" aria-hidden="true" />
                <div>
                  <p className="text-zinc-100 text-[14px] font-medium">{a.category}: {a.reason}</p>
                  {a.detail && <p className="text-zinc-500 text-[12.5px] mt-0.5">{a.detail}</p>}
                </div>
              </li>
            ))}
          </ul>
        </Panel>
      ))}
    </div>
  );
}
