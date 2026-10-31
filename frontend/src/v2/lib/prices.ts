import { cachedJSON } from "./http";

/** Revisión V6 (F12): la serie se comparte entre la historia y la página de la acción (caché del módulo). */
export const PRICES_TTL_MS = 600_000;   // 10 minutos

/** Punto de la serie (E2a): `c` cierre sin ajustar por dividendos (rentabilidad de precio), `a` ajustado (total). */
export interface PricePoint { t: string; c: number; a: number; v: number | null }
export interface PriceEvent { t: string; kind: "dividend" | "split" | "earnings"; value: number | null; label: string }
/** Revisión V6 (F1): rentabilidad de un periodo calculada por el backend (lib/price_returns.py): de precio (cierre sin
 *  ajustar) y total (con dividendos), con su texto y su tono. Sin dato: null y "—". */
export interface RangeReturn { price: number | null; total: number | null; price_txt: string; total_txt: string; price_tone: string; tone: string }
export interface SeriesPayload {
  symbol: string | null; status: string; reason?: string; points: PricePoint[]; events: PriceEvent[];
  events_reason?: string | null;
  returns?: Record<string, RangeReturn>;
  /** V7 (M7), solo el mercado: el índice no reparte dividendos; `a` lleva la rentabilidad total de la serie de
   *  `total_symbol` (SPY ajustado, en config). Sin ella, `total_status` "sin_dato" y `total_note` dice por qué. */
  total_status?: string; total_symbol?: string | null; total_note?: string | null;
}
export type SeriesRole = "company" | "market" | "sector";
export interface ChartMark { t: string; kind: PriceEvent["kind"]; label: string }
/** Un periodo de la gráfica: cada serie en base 100 desde su punto `i0` (sus `values`), y las marcas de eventos. */
export interface ChartWindow {
  status: string; reason: string | null; covered: boolean; start: string | null; end: string | null;
  series: Partial<Record<SeriesRole, { i0: number; values: number[] }>>; marks: ChartMark[];
}
export interface PricesPayload {
  symbol: string; as_of: string | null; company: SeriesPayload; market: SeriesPayload; sector: SeriesPayload;
  /** V7 (M7): de dónde sale la serie y su periodo real ("Serie diaria de Yahoo Finance de 5 años…"). */
  source?: string | null;
  ranges?: Array<{ key: string; label: string }>; chart?: Record<string, ChartWindow>;
}

/** Serie diaria de la empresa, del S&P 500 y del ETF de su sector (el backend lo resuelve desde `sector`). */
export function fetchPrices(symbol: string, sector: string | null, signal?: AbortSignal): Promise<PricesPayload> {
  const q = sector ? `?sector=${encodeURIComponent(sector)}` : "";
  return cachedJSON(`/api/v2/prices/${encodeURIComponent(symbol)}${q}`, `los precios de ${symbol}`, PRICES_TTL_MS, { signal });
}
