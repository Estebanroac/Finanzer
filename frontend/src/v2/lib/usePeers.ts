import { useEffect, useState } from "react";
import type { PeersResponse } from "@/lib/api";
import { fetchPeers } from "./companyData";
import { WEB } from "@/lib/generated/backendConfig";
import { backoffMs, isAbort, isTransient } from "./http";

const SECOND_MS = 1000;
// Revisión V6 (F4): un fallo pasajero del sondeo (502 al reiniciarse el servidor, sin conexión) se reintenta con
// espera creciente en lugar de dejar la tabla parada; tras RETRIES seguidos, se dice.
const RETRIES = 4;
const RETRY_BASE_MS = 2 * SECOND_MS;
const RETRY_CAP_MS = 30 * SECOND_MS;

/** El sondeo terminó sin rivales (V6b, E7: tope de data.toml [web] peers_poll_max_s). */
export const PEERS_TOO_SLOW = "los rivales están tardando más de lo normal; vuelve a cargar la página para seguir esperando.";

/** Los rivales de `symbol` (automáticos, o los elegidos en `chosen`), preguntando cada `poll_s` mientras se calculan,
 *  con tope de tiempo y en pausa con la pestaña oculta (V6b, E7).
 *  Lo comparten el comparador de la página Rivales y el capítulo 6 de la historia (V7 · P5): una sola petición
 *  (caché del módulo) y el mismo sondeo. */
export function usePeers(symbol: string, chosen: string[] | null = null): { data: PeersResponse | null; error: string | null } {
  const [data, setData] = useState<PeersResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    const ac = new AbortController();
    let t: ReturnType<typeof setTimeout> | null = null;
    let failures = 0;
    let pending = false;
    const started = Date.now();
    // la siguiente consulta: no con la pestaña oculta (sigue al volver) ni pasado el tope
    const later = (ms: number) => {
      t = setTimeout(() => {
        if (Date.now() - started > WEB.peersPollMaxMs) { setError(PEERS_TOO_SLOW); return; }
        if (document.hidden) pending = true; else load();
      }, ms);
    };
    const load = (): void => { pending = false; fetchPeers(symbol, chosen ?? undefined, ac.signal).then((r) => {
      failures = 0;
      setData(r); setError(null);
      if (r.status === "calculando") later(r.poll_s * SECOND_MS);
    }).catch((e: Error) => {
      if (isAbort(e)) return;
      if (isTransient(e) && failures < RETRIES) { later(backoffMs(failures++, RETRY_BASE_MS, RETRY_CAP_MS)); return; }
      setError(e.message);
    }); };
    const onVisible = () => { if (!document.hidden && pending) load(); };
    document.addEventListener("visibilitychange", onVisible);
    load();
    return () => { ac.abort(); if (t) clearTimeout(t); document.removeEventListener("visibilitychange", onVisible); };
  }, [symbol, chosen]);
  return { data, error };
}
