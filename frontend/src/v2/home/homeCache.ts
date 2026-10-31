import type { TrendingData } from "@/lib/api";
import type { SparkItem } from "@/v2/lib/sparklines";

/** Portada rápida (decisión del PM, Render gratuito): la última portada buena de la vista inicial (1D: listas y
 *  mini-gráficas), guardada en este navegador. Al volver se enseña al momento, con su hora, mientras llega la del
 *  servidor; nunca sustituye a una más reciente. Sin almacenamiento (modo privado, cuota llena), la portada funciona
 *  igual: cada lectura y escritura va con try/catch. */

const KEY = "finanzer.v2.portada";
const VERSION = 1;
export const CACHED_PERIOD = "1D";
const NY = "America/New_York";

export interface CachedHome {
  data: TrendingData;
  sparks: Record<string, SparkItem>;
}

function valid(v: unknown): v is CachedHome & { v: number } {
  const c = v as { v?: number; data?: TrendingData; sparks?: unknown } | null;
  return !!c && c.v === VERSION && typeof c.data?.as_of === "string" && !!c.data.lists?.[CACHED_PERIOD] &&
    typeof c.sparks === "object" && c.sparks !== null;
}

export function loadHome(): CachedHome | null {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return null;
    const c: unknown = JSON.parse(raw);
    return valid(c) ? { data: c.data, sparks: c.sparks } : null;
  } catch {
    return null;
  }
}

/** Solo el periodo de la vista inicial (las listas pesan por periodo) y, de sus mini-gráficas, las buenas, sin la
 *  marca `stale` (al volver se piden igual). */
function slim(data: TrendingData, sparks: Record<string, SparkItem>): CachedHome {
  const one = <T,>(r: Record<string, T> | undefined) => (r && CACHED_PERIOD in r ? { [CACHED_PERIOD]: r[CACHED_PERIOD] } : r);
  const ok = Object.fromEntries(Object.entries(sparks).filter(([, it]) => it.status === "ok")
    .map(([s, it]) => [s, { ...it, stale: undefined }]));          // JSON no guarda los undefined
  return {
    data: { ...data, lists: one(data.lists)!, list_notes: one(data.list_notes)!, sectors: one(data.sectors),
      sector_status: one(data.sector_status) } as TrendingData,
    sparks: ok,
  };
}

/** Guarda la portada si trae la vista inicial y no es más antigua que la guardada. Devuelve si la guardó. */
export function saveHome(data: TrendingData, sparks: Record<string, SparkItem>): boolean {
  if (!data.lists?.[CACHED_PERIOD]) return false;
  try {
    const prev = loadHome();
    if (prev && prev.data.as_of > data.as_of) return false;
    localStorage.setItem(KEY, JSON.stringify({ v: VERSION, ...slim(data, sparks) }));
    return true;
  } catch {
    return false;
  }
}

/** «datos de las 14:05 (Nueva York)»; de otro día, «datos del 27 de octubre a las 14:05 (Nueva York)». */
export function cachedLabel(asOf: string, now: Date): string {
  const at = new Date(asOf);
  const day = (d: Date) => new Intl.DateTimeFormat("en-CA", { timeZone: NY, year: "numeric", month: "2-digit",
    day: "2-digit" }).format(d);
  const time = new Intl.DateTimeFormat("es-ES", { timeZone: NY, hour: "2-digit", minute: "2-digit", hour12: false }).format(at);
  if (day(at) === day(now)) return `datos de las ${time} (Nueva York)`;
  const date = new Intl.DateTimeFormat("es-ES", { timeZone: NY, day: "numeric", month: "long" }).format(at);
  return `datos del ${date} a las ${time} (Nueva York)`;
}
