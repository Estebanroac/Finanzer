import type { StockAnalysis } from "@/lib/api";

import { WEB } from "@/lib/generated/backendConfig";
import { API_BASE, NETWORK_TEXT, isAbort } from "./http";

/** Verificación de la v4 (V3): el análisis para /v2 con el motivo del backend cuando no lo hay. `analyzeStock` de
 *  @/lib/api (la web actual) solo lo usa con el 422 y si no dice "Failed to analyze AAPL: 404": con Yahoo caído, /v2
 *  enseñaba eso en lugar de "la fuente de datos de mercado no responde…". Para StoryPageClient (E3). */
export async function fetchAnalysisV2(symbol: string, signal?: AbortSignal,
  timeoutMs: number = WEB.analysisTimeoutMs): Promise<StockAnalysis> {
  // V4 (PM): con un presupuesto de espera (data.toml [web]); sin él, un backend que no responde dejaba la página en
  // «Analizando…» para siempre. Cancelar (el `signal` de quien llama) sigue siendo un AbortError.
  const ac = new AbortController();
  let timedOut = false;
  const timer = setTimeout(() => { timedOut = true; ac.abort(); }, timeoutMs);
  const onAbort = () => ac.abort();
  if (signal?.aborted) ac.abort(); else signal?.addEventListener("abort", onAbort, { once: true });
  try {
    let res: Response;
    try {
      res = await fetch(`${API_BASE}/api/analysis/${encodeURIComponent(symbol)}`, { signal: ac.signal });
    } catch (e) {
      if (timedOut) throw new Error(timeoutText(symbol));
      if (isAbort(e)) throw e;
      throw new Error(NETWORK_TEXT);
    }
    if (res.ok) {
      try { return await res.json(); }
      catch (e) { if (timedOut) throw new Error(timeoutText(symbol)); throw e; }
    }
    throw new Error(analysisErrorText(symbol, res.status, await detailOf(res)));
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener("abort", onAbort);
  }
}

async function detailOf(res: Response): Promise<string | null> {
  try {
    const body = await res.json();
    return typeof body?.detail === "string" ? body.detail : null;
  } catch {
    return null;                                    // respuesta sin JSON
  }
}

/** El análisis no llegó dentro del presupuesto de espera. */
export const timeoutText = (symbol: string) =>
  `El análisis de ${symbol} está tardando más de lo normal. Vuelve a intentarlo en unos minutos.`;

const NOT_FOUND = 404;
const CLIENT_ERROR = 400;
const SERVER_ERROR = 500;

/** Texto del error en español: el motivo del backend si lo da (salvo el genérico en inglés de un símbolo inexistente). */
export function analysisErrorText(symbol: string, status: number, detail: string | null): string {
  if (detail && !/^No data found/i.test(detail) && status >= CLIENT_ERROR && status < SERVER_ERROR) return detail;
  if (status === NOT_FOUND) return `No hay datos de ${symbol}: comprueba el ticker (por ejemplo, AAPL o BRK-B).`;
  return `No se pudo analizar ${symbol} ahora mismo. Vuelve a intentarlo en unos minutos.`;   // sin el código HTTP a la vista (V6, F18)
}
