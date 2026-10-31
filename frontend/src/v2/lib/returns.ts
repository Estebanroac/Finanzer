import type { ChartWindow, PricesPayload, RangeReturn, SeriesRole } from "./prices";

/** Revisión V6 (F1): la rentabilidad por periodo, la base 100 y las marcas las calcula el backend (/api/v2/prices,
 *  lib/price_returns.py, las mismas que el PDF). Aquí solo se leen para pintarlas: el guardián prohíbe operar. */
export type RangeKey = string;
export const DEFAULT_RANGE: RangeKey = "1A";

const NO_RETURN: RangeReturn = { price: null, total: null, price_txt: "—", total_txt: "—", price_tone: "neutral", tone: "neutral" };

/** Rentabilidad de una serie en un periodo, tal como la manda el backend (sin dato si falta). */
export function returnOf(data: PricesPayload, role: SeriesRole, key: RangeKey): RangeReturn {
  return data[role]?.returns?.[key] ?? NO_RETURN;
}

/** Ventana del periodo (base 100 y marcas) o null. */
export function windowOf(data: PricesPayload, key: RangeKey): ChartWindow | null {
  const w = data.chart?.[key];
  return w && w.status === "ok" ? w : null;
}

/** Puntos de la gráfica de una serie: la base 100 del backend con la fecha de su sesión (cada serie, su calendario). */
export function chartPoints(data: PricesPayload, role: SeriesRole, key: RangeKey): Array<{ time: string; value: number }> {
  const w = windowOf(data, key)?.series[role];
  const pts = data[role]?.points ?? [];
  if (!w) return [];
  return w.values.flatMap((value, i) => {
    const p = pts[w.i0 + i];
    return p ? [{ time: p.t, value }] : [];
  });
}

/** Fechas de las sesiones del periodo de una serie (para el volumen de la gráfica completa). */
export function sessionsOf(data: PricesPayload, role: SeriesRole, key: RangeKey): Set<string> {
  return new Set(chartPoints(data, role, key).map((p) => p.time));
}
