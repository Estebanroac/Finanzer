import type { StockAnalysis } from "@/lib/api";

// Un análisis por símbolo en sessionStorage: al recargar una página de profundidad o abrirla desde la historia no se
// repite /api/analysis mientras siga fresco (el backend guarda los datos 5 min: `data.yahoo.cache_ttl_s`).
// Revisión V6 (F14): con versión (un análisis de otra forma no se lee), como mucho MAX_CACHED empresas y sin lo
// caducado (se purga al escribir; si el almacenamiento está lleno, se vacía lo nuestro y se reintenta una vez).
const KEY = "finanzer.v2.analysis.";
export const CACHE_VERSION = 2;
export const ANALYSIS_TTL_MS = 5 * 60 * 1000;
export const MAX_CACHED = 5;

interface Entry { v: number; t: number; data: StockAnalysis }

function parse(raw: string | null): Entry | null {
  try {
    const e = raw ? (JSON.parse(raw) as Entry) : null;
    return e && e.v === CACHE_VERSION && typeof e.t === "number" && e.data ? e : null;
  } catch {
    return null;
  }
}

const fresh = (e: Entry | null, now: number): e is Entry => !!e && now - e.t < ANALYSIS_TTL_MS && e.t <= now;

function ourKeys(): string[] {
  const out: string[] = [];
  for (let i = 0; i < sessionStorage.length; i++) {
    const k = sessionStorage.key(i);
    if (k && k.startsWith(KEY)) out.push(k);
  }
  return out;
}

export function readCached(symbol: string, now = Date.now()): StockAnalysis | null {
  try {
    const e = parse(sessionStorage.getItem(KEY + symbol));
    return fresh(e, now) ? e.data : null;
  } catch {
    return null;   // almacenamiento bloqueado: se pide de nuevo
  }
}

/** Quita lo caducado o de otra versión y, si siguen sin caber, los más antiguos hasta dejar sitio para uno más. */
function purge(now: number, keep: string): void {
  const live: Array<{ k: string; t: number }> = [];
  for (const k of ourKeys()) {
    const e = parse(sessionStorage.getItem(k));
    if (fresh(e, now)) { if (k !== keep) live.push({ k, t: e.t }); } else sessionStorage.removeItem(k);
  }
  live.sort((a, b) => a.t - b.t);
  while (live.length >= MAX_CACHED) sessionStorage.removeItem(live.shift()!.k);
}

export function writeCached(symbol: string, data: StockAnalysis, now = Date.now()): void {
  const key = KEY + symbol, value = JSON.stringify({ v: CACHE_VERSION, t: now, data } satisfies Entry);
  try {
    purge(now, key);
    sessionStorage.setItem(key, value);
  } catch {
    try {   // lleno: fuera todo lo nuestro y un intento más
      ourKeys().forEach((k) => sessionStorage.removeItem(k));
      sessionStorage.setItem(key, value);
    } catch {
      /* sin almacenamiento: no pasa nada, solo se volverá a pedir */
    }
  }
}
