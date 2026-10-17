"use client";

import type { QualityReading } from "@/lib/api";
import { ChartPanel } from "./charts";

/** Fase 3 (T6): lecturas de calidad que informan y no puntúan (DuPont, margen FCF, regla de 40, cobertura…). */
export default function QualityReadings({ items, grown, title }: { items?: QualityReading[]; grown: boolean; title: string }) {
  if (!items || items.length === 0) return null;
  return (
    <ChartPanel grown={grown} title={title}>
      <ul className="space-y-2">
        {items.map((q) => (
          <li key={q.key} className="fz-note !mt-0">
            <span className={`font-medium tone-${q.tone} fz-tone-fg`}>{q.label}.</span> {q.text}
          </li>
        ))}
      </ul>
    </ChartPanel>
  );
}
