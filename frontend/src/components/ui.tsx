"use client";

import type { ReactNode } from "react";
import type { MetricBands, Row, RowState, Tone } from "@/lib/api";
import { STATE_LABELS } from "@/lib/generated/backendConfig";
import { definitionFor } from "@/lib/tooltips";
import InfoTooltip from "./InfoTooltip";

/* Primitivas de presentación. El tono y el estado llegan del backend (display):
   aquí solo se traducen a clases; ningún componente decide una lectura. */

export function toneClass(tone: Tone | null | undefined): string {
  return tone ? `tone-${tone}` : "tone-none";
}

/** Rótulo de estado en TEXTO (no solo color): "Sin dato", "No aplica a …", "No significativo". */
export function StateTag({ state, text }: { state: RowState; text?: string | null }) {
  if (state === "con_dato") return null;
  const label = text && text !== "—" ? text : STATE_LABELS[state];
  return <span className={`state-tag state-${state}`}>{label}</span>;
}

export function Pill({ tone, children }: { tone: Tone | null; children: ReactNode }) {
  return <span className={`fz-pill ${toneClass(tone)}`}>{children}</span>;
}

export function Panel({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`fz-panel ${className}`}>{children}</section>;
}

export function PanelTitle({ children, aside }: { children: ReactNode; aside?: ReactNode }) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <h3 className="fz-kicker">{children}</h3>
      {aside}
    </div>
  );
}

export function Intro({ text }: { text: string | null | undefined }) {
  if (!text) return null;
  return <p className="text-[15px] leading-relaxed text-zinc-300 mb-5">{text}</p>;
}

export function Note({ children, tone }: { children: ReactNode; tone?: Tone }) {
  if (!children) return null;
  return <p className={`fz-note ${tone ? toneClass(tone) : ""}`}>{children}</p>;
}

export function Collapsible({ summary, children }: { summary: string; children: ReactNode }) {
  return (
    <details className="fz-details">
      <summary>{summary}</summary>
      <div className="pt-3">{children}</div>
    </details>
  );
}

/** Botón "?" de una métrica: definición + bandas aplicadas + lectura del backend. */
export function Help({ k, title, bands, value, reading, readingAlt, text }: {
  k: string; title: string; bands?: MetricBands; value?: string; reading?: { label: string; tone: Tone | null } | null;
  readingAlt?: string | null; text?: string | null;
}) {
  const def = definitionFor(k, title);
  if (!def.description && !bands && !text) return null;
  return <InfoTooltip def={def} bands={bands} value={value} reading={reading} activeLabels={[reading?.label, readingAlt]}
    text={text} />;
}

/** Celda de lectura: la lectura del backend con su tono, o el estado en texto. */
export function ReadingCell({ row }: { row: Row }) {
  if (row.state !== "con_dato") return <StateTag state={row.state} text={row.reading} />;
  if (!row.reading || row.reading === "—") return <span className="text-zinc-600">—</span>;
  return <Pill tone={row.tone}>{row.reading}</Pill>;
}

/**
 * Tabla de sección (mismas filas que el PDF). Escritorio: columnas; móvil: cada fila
 * es una tarjeta (métrica y valor arriba, lectura y referencia debajo).
 */
export function DataTable({ columns, rows, tooltips, readings, withBenchmark = false }: {
  columns: string[]; rows: Row[]; tooltips: Record<string, MetricBands>;
  readings?: Record<string, { label: string } | null>;
  /** Tabla con columnas de referencia y brecha (múltiplos, rentabilidad). */
  withBenchmark?: boolean;
}) {
  const wide = withBenchmark;
  return (
    <div className={`fz-table ${wide ? "fz-table-5" : "fz-table-3"}`} role="table">
      <div className="fz-tr fz-th" role="row">
        {columns.map((c, i) => <span key={i} role="columnheader">{c}</span>)}
      </div>
      {rows.map((r, i) => (
        <div key={`${r.key}-${i}`} className={`fz-tr fz-row-${r.state}`} role="row">
          <span className="fz-td-label" role="cell">
            {r.label}
            <Help k={r.key} title={r.label} bands={tooltips[r.key]} value={r.value}
              reading={r.state === "con_dato" && r.reading !== "—" ? { label: r.reading, tone: r.tone } : null}
              readingAlt={readings?.[r.key]?.label} text={r.text} />
          </span>
          <span className="fz-td-value" role="cell">{r.value}</span>
          {wide && (
            <span className="fz-td-bench" role="cell">
              <span className="fz-mobile-k">{columns[2]} </span>{r.bench ?? "—"}
            </span>
          )}
          {wide && (
            <span className="fz-td-gap" role="cell">
              <span className="fz-mobile-k">{columns[3]} </span>{r.gap ?? "—"}
            </span>
          )}
          <span className="fz-td-read" role="cell"><ReadingCell row={r} /></span>
        </div>
      ))}
    </div>
  );
}

/** Barra horizontal simple con el tono del backend. */
export function ToneBar({ pct, tone, thin }: { pct: number; tone: Tone | null; thin?: boolean }) {
  return (
    <div className={`fz-bar ${thin ? "fz-bar-thin" : ""}`}>
      <div className={`fz-bar-fill ${toneClass(tone)}`} style={{ width: `${Math.max(0, Math.min(100, pct))}%` }} />
    </div>
  );
}
