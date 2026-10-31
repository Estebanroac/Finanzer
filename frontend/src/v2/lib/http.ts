// Revisión V6: peticiones de /v2 en un solo sitio.
//  - F18: errores en español, con el motivo del backend (`detail`) si lo da; nunca «Failed to fetch» ni «HTTP 500».
//  - F12: caché en el módulo con TTL (la misma petición, en vuelo o reciente, se comparte entre montajes: navegar entre
//    páginas no la repite) y cancelación por consumidor (AbortSignal) sin cortar la petición compartida.

// Misma regla que API_BASE de @/lib/api (no se exporta allí y la web actual no se toca).
export const API_BASE = process.env.NEXT_PUBLIC_API_URL ||
  (typeof window !== "undefined" && window.location.port === "3000" ? "http://localhost:8000" : "");

export const NETWORK_TEXT = "No se pudo contactar con el servidor. Comprueba la conexión y vuelve a intentarlo.";
const CLIENT_ERROR = 400;
const SERVER_ERROR = 500;
const TOO_MANY = 429;
const NOT_FOUND = 404;

/** Error de una petición de /v2: `message` en español para enseñarlo tal cual; `status` 0 = sin conexión. */
export class HttpError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "HttpError";
    this.status = status;
  }
}

/** Texto del error en español: el motivo del backend en un 4xx; si no, uno genérico de `what` (p. ej. «los rivales»). */
export function httpErrorText(what: string, status: number, detail: string | null): string {
  if (status === TOO_MANY) return `Demasiadas peticiones seguidas: espera un momento y vuelve a cargar ${what}.`;
  if (detail && status >= CLIENT_ERROR && status < SERVER_ERROR) return detail;
  if (status === NOT_FOUND) return `No se encontraron ${what}.`;
  if (status >= SERVER_ERROR) return `No se pudieron cargar ${what} ahora mismo. Vuelve a intentarlo en unos minutos.`;
  return `No se pudieron cargar ${what}.`;
}

export const isAbort = (e: unknown): boolean => (e as { name?: string } | null)?.name === "AbortError";

async function detailOf(res: Response): Promise<string | null> {
  try {
    const body = await res.json();
    return typeof body?.detail === "string" ? body.detail : null;
  } catch {
    return null;
  }
}

/** GET o POST con JSON; lanza HttpError con el texto en español (o el AbortError tal cual). */
export async function requestJSON<T>(path: string, what: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, init);
  } catch (e) {
    if (isAbort(e)) throw e;
    throw new HttpError(NETWORK_TEXT, 0);
  }
  if (!res.ok) throw new HttpError(httpErrorText(what, res.status, await detailOf(res)), res.status);
  return res.json() as Promise<T>;
}

/** La promesa `p`, que se rechaza con AbortError si `signal` se aborta antes (la petición de fondo sigue para los demás). */
export function abortable<T>(p: Promise<T>, signal?: AbortSignal): Promise<T> {
  if (!signal) return p;
  if (signal.aborted) return Promise.reject(new DOMException("Aborted", "AbortError"));
  return new Promise<T>((resolve, reject) => {
    const onAbort = () => reject(new DOMException("Aborted", "AbortError"));
    signal.addEventListener("abort", onAbort, { once: true });
    p.then((v) => { signal.removeEventListener("abort", onAbort); resolve(v); },
      (e) => { signal.removeEventListener("abort", onAbort); reject(e); });
  });
}

const cache = new Map<string, { at: number; p: Promise<unknown> }>();

/** GET con caché en el módulo: dentro de `ttlMs`, la misma ruta devuelve la misma promesa (en vuelo o resuelta). Los
 *  fallos no se guardan, y `keep` decide qué respuestas sí (p. ej. los rivales solo cuando ya no están «calculando»). */
export function cachedJSON<T>(path: string, what: string, ttlMs: number, opts?: { signal?: AbortSignal; keep?: (v: T) => boolean }): Promise<T> {
  const now = Date.now();
  const hit = cache.get(path);
  if (hit && now - hit.at < ttlMs) return abortable(hit.p as Promise<T>, opts?.signal);
  const p = requestJSON<T>(path, what);
  const entry = { at: now, p };
  cache.set(path, entry);
  p.then((v) => { if (opts?.keep && !opts.keep(v) && cache.get(path) === entry) cache.delete(path); },
    () => { if (cache.get(path) === entry) cache.delete(path); });
  return abortable(p, opts?.signal);
}

/** Revisión V6 (F4, F16): espera del reintento `attempt` (0, 1, 2…) de un sondeo: `baseMs` × 2^attempt, como mucho
 *  `capMs`. */
export function backoffMs(attempt: number, baseMs: number, capMs: number): number {
  return Math.min(capMs, baseMs * 2 ** attempt);
}

/** ¿Merece la pena reintentar? Sin conexión, 429 o un 5xx pasajero sí; un 4xx (petición mala) no. */
export function isTransient(e: unknown): boolean {
  if (isAbort(e)) return false;
  if (!(e instanceof HttpError)) return true;
  return e.status === 0 || e.status === TOO_MANY || e.status >= SERVER_ERROR;
}

/** Vacía la caché (pruebas). */
export function clearHttpCache(): void {
  cache.clear();
}
