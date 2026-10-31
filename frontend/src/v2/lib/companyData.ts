import type { PeersResponse, ScenarioRequest, ScenarioResponse, SegmentsResponse, TrendingResponse } from "@/lib/api";
import { cachedJSON, requestJSON } from "./http";

// Revisión V6 (F12): caché en el módulo con TTL; la página cancela lo suyo con `signal` al desmontarse.
const MINUTE_MS = 60_000;
export const SEGMENTS_TTL_MS = 30 * MINUTE_MS;     // los segmentos salen del último informe anual: cambian poco
export const PEERS_TTL_MS = 10 * MINUTE_MS;

/** Ingresos por segmento del último informe anual en la SEC (E2b). */
export function fetchSegments(symbol: string, signal?: AbortSignal): Promise<SegmentsResponse> {
  return cachedJSON(`/api/v2/segments/${encodeURIComponent(symbol)}`, `los segmentos de ${symbol}`, SEGMENTS_TTL_MS, { signal });
}

/** Rivales (automáticos, o los elegidos en `symbols`); repetir cada `poll_s` mientras `status` sea "calculando" (esas
 *  respuestas no se guardan en la caché: la siguiente consulta vuelve a preguntar). */
export function fetchPeers(symbol: string, symbols?: string[], signal?: AbortSignal): Promise<PeersResponse> {
  const q = symbols && symbols.length ? `?symbols=${encodeURIComponent(symbols.join(","))}` : "";
  return cachedJSON<PeersResponse>(`/api/v2/peers/${encodeURIComponent(symbol)}${q}`, `los rivales de ${symbol}`, PEERS_TTL_MS,
    { signal, keep: (r) => r.status !== "calculando" });
}

/** Tendencias del día sobre el S&P 500 y los ADR principales (sin caché: la portada sondea mientras se calculan). Con
 *  `period`, solo las listas de ese periodo (V6b, E11: la portada pide el que enseña; un cuarto del peso). */
export function fetchTrending(period?: string, signal?: AbortSignal): Promise<TrendingResponse> {
  const q = period ? `?period=${encodeURIComponent(period)}` : "";
  return requestJSON(`/api/v2/trending${q}`, "las tendencias del día", { signal });
}

/** Escenario del usuario (E2a/E3): el mismo DCF del motor con sus supuestos; no cambia el veredicto. Un 422 trae el
 *  motivo del backend (`detail`), que se enseña tal cual. */
export function postScenario(req: ScenarioRequest, signal?: AbortSignal): Promise<ScenarioResponse> {
  return requestJSON("/api/v2/scenario", "el escenario", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(req), signal,
  });
}
