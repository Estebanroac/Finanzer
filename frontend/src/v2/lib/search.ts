import type { SearchHit, SearchResponse } from "@/lib/api";
import { isAbort, requestJSON } from "./http";

/** Espera tras la última tecla antes de buscar (una petición por pausa al escribir, no por letra). */
export const SEARCH_DEBOUNCE_MS = 200;
import { TICKER_LIKE } from "./routes";

/** Buscador de /v2 (rediseño E4): solo acciones, con su bolsa. Un fallo es una lista vacía; una búsqueda cancelada
 *  (`signal`, al escribir otra cosa) lanza AbortError para que nadie pinte resultados viejos. */
export async function searchV2(q: string, signal?: AbortSignal): Promise<SearchHit[]> {
  try {
    const body = await requestJSON<SearchResponse>(`/api/v2/search?q=${encodeURIComponent(q)}`, "los resultados", { signal });
    return body.results;
  } catch (e) {
    if (isAbort(e)) throw e;
    return [];
  }
}

export function stockHref(ticker: string): string {
  return `/v2/${encodeURIComponent(ticker.toUpperCase())}`;
}

/** Destino de Enter: la opción marcada; si no, el resultado cuyo ticker es exactamente lo escrito; si no, el primer
 *  resultado (V7 · P6: buscar por nombre y pulsar Enter abre la empresa, como en cualquier buscador); sin resultados,
 *  lo escrito si parece un ticker. null: Enter no hace nada. */
export function enterTarget(q: string, results: SearchHit[], active: number): string | null {
  if (active >= 0 && active < results.length) return results[active].ticker;
  const t = q.trim().toUpperCase();
  const exact = results.find((r) => r.ticker.toUpperCase() === t);
  if (exact) return exact.ticker;
  if (results.length) return results[0].ticker;
  return TICKER_LIKE.test(q.trim()) ? t : null;
}

/** ↑ ↓ con vuelta: −1 = ninguna opción marcada (el foco sigue en el texto). */
export function moveActive(active: number, count: number, dir: 1 | -1): number {
  if (count === 0) return -1;
  if (active < 0) return dir === 1 ? 0 : count - 1;
  const next = active + dir;
  return next < 0 || next >= count ? -1 : next;
}
