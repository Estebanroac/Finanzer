"use client";

import type { ReactNode } from "react";
import type { Display } from "@/lib/api";
import { ChartPanel, IconAlert, IconCheck, IconWarn, NotApplicable } from "../charts";
import { toneClass } from "../ui";

// Icono de cada grupo de alertas (la clave y el tono llegan del backend).
const ICON: Record<string, () => ReactNode> = { red_flags: IconAlert, warnings: IconWarn, strengths: IconCheck };

export default function AlertsTab({ display }: { display: Display }) {
  const A = display.sections.alerts;
  const empty = A.groups.every((g) => g.items.length === 0);
  return (
    <div className="space-y-4">
      <div className="cz-counts">
        {A.groups.map((g) => {
          const Ic = ICON[g.key] ?? IconWarn;
          const n = g.items.length;
          return (
            <div key={g.key} className={`cz-count ${toneClass(g.tone)}`}>
              <span className="cz-count-n">{n}</span>
              <span className="cz-count-l"><span className="cz-ic !w-5 !h-5 !rounded-md" aria-hidden="true"><Ic /></span>{g.title}</span>
            </div>
          );
        })}
      </div>
      {empty && <NotApplicable state="sin_dato" title="Alertas" text="no se detectaron alertas significativas" />}
      {A.groups.filter((g) => g.items.length > 0).map((g) => {
        const Ic = ICON[g.key] ?? IconWarn;
        return (
          <ChartPanel key={g.key} tone={g.tone} title={<span className={`${toneClass(g.tone)} fz-tone-fg`}>{g.title}</span>}
            aside={<span className="cz-hint">{g.items.length}</span>}>
            <ul>
              {g.items.map((a, i) => (
                <li key={i} className={`cz-alert ${toneClass(g.tone)}`}>
                  <span className="cz-ic" aria-hidden="true"><Ic /></span>
                  <div className="min-w-0">
                    <p className="text-zinc-100 text-[14px] font-medium">{a.category}: {a.reason}</p>
                    {a.detail && <p className="text-zinc-500 text-[12.5px] mt-0.5">{a.detail}</p>}
                  </div>
                </li>
              ))}
            </ul>
          </ChartPanel>
        );
      })}
    </div>
  );
}
