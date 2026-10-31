import type { ChartMark, PriceEvent, PricesPayload } from "./prices";
import { windowOf, type RangeKey } from "./returns";

export type EventKind = PriceEvent["kind"];
/** Orden y rótulo de cada tipo de evento en la leyenda de la gráfica. */
export const EVENT_KINDS: Array<{ kind: EventKind; label: string }> = [
  { kind: "earnings", label: "Resultados" }, { kind: "dividend", label: "Dividendos" }, { kind: "split", label: "Splits" },
];

/** Marcas de eventos del periodo, ya colocadas por el backend en su sesión (revisión V6, F1): solo se pintan. */
export function marksOf(data: PricesPayload, key: RangeKey): ChartMark[] {
  return (windowOf(data, key)?.marks ?? []).filter((m) => EVENT_KINDS.some((k) => k.kind === m.kind));
}
