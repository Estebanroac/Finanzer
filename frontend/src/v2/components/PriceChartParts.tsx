"use client";
// Piezas de las gráficas de precio que no necesitan Lightweight Charts: así el esqueleto de carga (revisión V6, F13:
// la librería va en su propio fragmento, con next/dynamic) tiene el mismo alto y los mismos botones.
import { useTheme as useThemeStore } from "@/v2/lib/theme";
import type { PricesPayload } from "@/v2/lib/prices";
import { DEFAULT_RANGE, type RangeKey } from "@/v2/lib/returns";
import { EVENT_KINDS, type EventKind } from "@/v2/lib/chartEvents";

export const css = (el: Element, v: string) => getComputedStyle(el).getPropertyValue(v).trim();
export const MOBILE_QUERY = "(max-width: 47.9375em)";   // el mismo corte que v2.css
export const AXIS_PX = 12;
export const AXIS_PX_MOBILE = 13;
/** Solo para el esqueleto de carga (mismo alto y mismos botones): los periodos de verdad llegan con la serie. */
export const SKELETON_RANGES = ["1S", "1M", "3M", "6M", "YTD", "1A", "3A", "5A"];
export const fmtDate = (iso: string) => iso.split("-").reverse().join("/");

/** Botones de periodo (revisión V6, F21): un grupo de botones con aria-pressed, no un tablist a medias. */
export function RangeButtons({ data, range, onPick }: { data: PricesPayload | null; range: RangeKey; onPick?: (k: RangeKey) => void }) {
  const keys = data?.ranges?.map((r) => r) ?? SKELETON_RANGES.map((key) => ({ key, label: key }));
  return (
    <div role="group" aria-label="Periodo" className="range-tabs">
      {keys.map((r) => (
        <button key={r.key} type="button" aria-pressed={range === r.key} title={r.label}
          className={range === r.key ? "on" : ""} disabled={!onPick} onClick={() => onPick?.(r.key)}>{r.key}</button>
      ))}
    </div>
  );
}
/** Color de cada marca (tokens de /v2, sin neón): resultados en tinta, dividendos en verde, splits en ámbar. */
export const MARK_COLOR: Record<EventKind, string> = { earnings: "--text-2", dividend: "--good", split: "--warn" };
export const MARK_SIZE = 0.75;   // discretas: tres cuartos del tamaño por defecto de la librería

/** Tema actual de /v2 (almacén del tema): la gráfica se repinta con los tokens al cambiar. */
export function useTheme(): string {
  return useThemeStore() ?? "light";
}

/** Leyenda de las marcas de eventos (resultados, dividendos, splits) con su color. */
export function Marks({ kinds }: { kinds: typeof EVENT_KINDS }) {
  return <span className="marks muted" aria-hidden>{kinds.map((k) => <span key={k.kind}><span className={`mark ${k.kind}`} />{k.label}</span>)}</span>;
}

/** La gráfica del capítulo mientras llega (su código o la serie): la misma estructura y el mismo alto, sin saltos, y el
 *  capítulo mide bien. */
export function PriceChartSkeleton({ range = DEFAULT_RANGE }: { range?: RangeKey }) {
  return (
    <div className="pricechart" aria-busy="true">
      <div className="ranges"><RangeButtons data={null} range={range} />
        <Marks kinds={EVENT_KINDS} /></div>
      <div className="chart-skeleton" />
      <table className="returns-table num"><thead><tr><th scope="col">—</th>{["a", "b", "c"].map((k) => <th key={k} scope="col">—</th>)}</tr></thead>
        <tbody>{["Precio", "Con dividendos"].map((k) => <tr key={k}><th scope="row">{k}</th><td>—</td><td>—</td><td>—</td></tr>)}</tbody></table>
      <p className="attribution muted">Gráfica: TradingView Lightweight Charts™</p>
    </div>);
}

/** v4.1 (movimiento): la gráfica completa de La acción mientras llega su fragmento: la misma estructura y el mismo alto
 *  (26 rem; 20 en el móvil), así lo de debajo no salta al llegar. */
export function PriceChartFullSkeleton() {
  return (
    <div className="pricechart full card surface" aria-busy="true">
      <div className="ranges"><RangeButtons data={null} range={DEFAULT_RANGE} /><Marks kinds={EVENT_KINDS} /></div>
      <p className="cursor-read num muted">Cargando la gráfica…</p>
      <div className="chart-skeleton chart-full" />
      <p className="legend muted">Base 100 al inicio del periodo, con dividendos</p>
    </div>);
}
