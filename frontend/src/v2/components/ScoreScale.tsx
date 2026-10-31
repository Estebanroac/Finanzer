"use client";
import type { ScaleModel } from "@/v2/lib/scale";
import type { VTone } from "@/v2/lib/tone";
import MetricTip, { LabelTip } from "./depth/MetricTip";

/** `term`: la definición que explica la fila (V7 · P3), con su «?». */
export interface BreakdownRow { name: string; value: string; tone?: VTone; term?: string }
/** `after`: filas que van tras el total (el ajuste por confianza del precio, que se aplica al total). */
export interface Breakdown { title: string; rows: BreakdownRow[]; total?: BreakdownRow; after?: BreakdownRow[]; notes: string[] }

/** «?» dentro de una tarjeta. */
export function TipHost({ term, label }: { term: string; label: string }) {
  return <span className="tip-host"><MetricTip metricKey={term} label={label} /></span>;
}

/** Una puntuación con su escala, su base y cómo se calcula. V4b (literal del usuario: «no quiero subsecciones ocultas,
 *  las quiero fijas»): el desglose va siempre a la vista, en la tarjeta (antes salía al pasar el ratón y, en el móvil,
 *  en una hoja tras «Ver detalle»). Los «?» siguen siendo ayuda: abren su definición. */
export default function ScoreScale({ model, fit, title, question, display, suffix, tone, levelTone, base, line, breakdown, testId, term }: {
  model: ScaleModel; title: string; question: string; display: string; suffix: string | null; tone: VTone;
  /** Ancho (rem) por debajo del cual las marcas pasan a leyenda (`ticksFitAttr`, el mismo para las tres tarjetas). */
  fit: string;
  /** V7 · P1: la definición de la puntuación («?» junto al título). */
  term?: string;
  /** V7 · P1: una línea bajo la base (la confianza: qué no puntúa y qué contrae; `confidenceLine`). */
  line?: string | null;
  /** Tono del motor para el tramo en que cae el valor (por defecto, el de la cifra). */
  levelTone?: VTone;
  base: string; breakdown: Breakdown | null; testId: string;
}) {
  // minmax(0, …): las columnas guardan la proporción de la escala aunque una marca sea más ancha.
  const cols = model.segments.map((s) => `minmax(0, ${s.widthPct}fr)`).join(" ");
  const current = (label: string) => label === model.level?.toLowerCase();
  const segClass = (s: ScaleModel["segments"][number]) => current(s.label) ? `seg on ${levelTone ?? tone}` : `seg ${s.tone}`;
  return (
    <div className="score surface" data-testid={testId}>
      <div className="eyebrow">{term ? <LabelTip text={title}><TipHost term={term} label={title} /></LabelTip> : title}<span className="q"> · {question}</span></div>
      <div className="score-value"><span className={`big num tone-${tone}`}>{display}</span>
        {suffix && <span className="muted"> {suffix}</span>}</div>
      <div className="scale" style={{ gridTemplateColumns: cols }}>
        {model.segments.map((s) => <div key={s.label} data-segment className={segClass(s)} />)}
        {model.pinPct !== null && <span className="pin" style={{ left: `${model.pinPct}%` }} aria-hidden />}
      </div>
      {/* Bajo sus tramos, o en leyenda si no caben (v2.css: consulta de contenedor sobre `data-fit`; el contenedor es
          .ticks-wrap y no la tarjeta, que perdería su subgrid). La muestra de color solo se ve en la leyenda: es el
          tramo de la barra que nombra la fila. */}
      <div className="ticks-wrap">
        <div className="ticks num" data-fit={fit} style={{ "--cols": cols } as React.CSSProperties}>
          {model.segments.map((s) => (
            <span key={s.label} className={current(s.label) ? "on" : undefined}>
              <i className={segClass(s)} aria-hidden /><span className="tick-name">{s.label}</span>
              {s.range && <span className="range">{s.range}</span>}
            </span>))}
        </div>
      </div>
      {/* Base y desglose comparten la última fila: la lista reparte el alto que sobra entre sus filas, así una nota
          más larga en la tarjeta vecina no deja un bloque vacío en esta. */}
      <div className="foot">
        <div className="muted base">{base}</div>
        {line && <div className="muted base-line" data-testid={`${testId}-line`}>{line}</div>}
        {breakdown && (
          <div className="bd" data-testid={`breakdown-${model.kind}`}>
            <div className="eyebrow bd-title">{breakdown.title}</div>
            <ul className="mini num fill">
              {breakdown.rows.map((r) => (
                <li key={r.name} data-cat><span>{r.term ? <LabelTip text={r.name}><TipHost term={r.term} label={r.name.split(" · ")[0]} /></LabelTip> : r.name}</span>
                  <b className={r.tone ? `tone-${r.tone}` : undefined}>{r.value}</b></li>))}
            </ul>
            {[...(breakdown.total ? [breakdown.total] : []), ...(breakdown.after ?? [])].map((r) => (
              <p key={r.name} className="bd-total num"><span>{r.term ? <LabelTip text={r.name}><TipHost term={r.term} label={r.name} /></LabelTip> : r.name}</span>
                <b className={r.tone ? `tone-${r.tone}` : undefined}>{r.value}</b></p>))}
            {breakdown.notes.map((n) => <p key={n} className="muted bd-note">{n}</p>)}
          </div>
        )}
      </div>
    </div>
  );
}
