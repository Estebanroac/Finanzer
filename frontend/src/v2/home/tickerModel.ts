import type { TrendingData, TrendingItem, TrendingSectorStatus } from "@/lib/api";
import type { SparkPeriod } from "@/v2/lib/sparklines";
import { SPARK_PERIODS } from "@/v2/lib/sparklines";
import type { ListKey } from "./trendingModel";

/** P8: lo que muestra el cintillo: una lista del día o la de un sector (una sola selección activa a la vez). */
export type Selection = { kind: "list"; key: ListKey } | { kind: "sector"; key: string };

export const DAY_LISTS: Array<{ key: ListKey; label: string; arrow: "up" | "down" | null; title: string }> = [
  { key: "most_traded", label: "Más negociadas", arrow: null, title: "Más negociadas" },
  { key: "gainers", label: "Suben más", arrow: "up", title: "Suben más" },
  { key: "losers", label: "Bajan más", arrow: "down", title: "Bajan más" },
];

/** Sectores con chip propio; el resto va en «Más ▾» (en el orden del backend). */
export const PRIMARY_SECTORS = 8;

export interface SectorChip { key: string; label: string; available: boolean; reason: string | null }

export function sectorChips(d: TrendingData | null, period: SparkPeriod): { primary: SectorChip[]; more: SectorChip[] } {
  const st: Record<string, TrendingSectorStatus> = d?.sector_status?.[period] ?? {};
  const all = Object.entries(st).map(([key, s]) => ({ key, label: s.label, available: s.available, reason: s.reason }));
  return { primary: all.slice(0, PRIMARY_SECTORS), more: all.slice(PRIMARY_SECTORS) };
}

/** V6b (E11): la portada pide solo el periodo que enseña (`/api/v2/trending?period=`). Lo que ya tenía de otros periodos
 *  se conserva al llegar uno nuevo (volver a un periodo ya visto no deja el cintillo vacío mientras pregunta); lo demás
 *  (fechas, universo, notas) es el de la respuesta nueva. */
const BY_PERIOD = ["lists", "list_notes", "sectors", "sector_status"] as const;
export function mergeTrending(prev: TrendingData | null, next: TrendingData): TrendingData {
  if (!prev || prev.session !== next.session) return next;
  const out = { ...next } as TrendingData;
  for (const k of BY_PERIOD) {
    const a = prev[k] as Record<string, unknown> | undefined, b = next[k] as Record<string, unknown> | undefined;
    if (a || b) (out as unknown as Record<string, unknown>)[k] = { ...(a ?? {}), ...Object.fromEntries(Object.entries(b ?? {}).filter(([, v]) => v != null)) };
  }
  return out;
}

/** P8b: las tarjetas de la lista o del sector elegidos, calculadas en el periodo elegido (el de las gráficas). */
export function selectedItems(d: TrendingData | null, sel: Selection, period: SparkPeriod): TrendingItem[] {
  if (!d) return [];
  if (sel.kind === "list") return d.lists[period]?.[sel.key] ?? [];
  return d.sectors?.[period]?.[sel.key] ?? [];
}

const MONTHS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];

/** «2026-04-16» → «16-abr-2026». */
export function shortDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  return `${d}-${MONTHS[m - 1]}-${y}`;
}

const periodLabel = (p: SparkPeriod) => SPARK_PERIODS.find((x) => x.key === p)?.label ?? p;

/** Línea de contexto bajo el cintillo: qué lista, en qué periodo y entre qué sesiones (las listas y las gráficas usan
 *  el mismo), el universo y cuántos valores; si «Suben más» o «Bajan más» no llegan, por qué. */
export function contextLine(d: TrendingData, sel: Selection, period: SparkPeriod, count: number): string {
  const what = sel.kind === "list"
    ? DAY_LISTS.find((x) => x.key === sel.key)!.title
    : `${d.sector_status?.[period]?.[sel.key]?.label ?? sel.key}, las más negociadas del sector,`;
  const info = d.periods?.[period];
  const span = info?.from ? ` (del ${shortDate(info.from)} al ${shortDate(info.to)})` : "";
  const note = sel.kind === "list" && sel.key !== "most_traded" ? d.list_notes?.[period]?.[sel.key] : null;
  return `${what} en ${periodLabel(period)}${span} · universo: S&P 500 y ADR principales · ` +
    `${count} valor${count === 1 ? "" : "es"}${note ? ` · ${note}` : ""}`;
}

const MINUS = "−";
const PCT = 100;
const PCT_DECIMALS = 2;

/** Variación mostrada en la tarjeta (P8b): la del periodo con la que se ordena su lista (backend
 *  lib/period_change.py, la misma de su mini-gráfica): la cifra nunca contradice al filtro. */
export function shownChange(item: TrendingItem): { value: number | null; reason: string | null } {
  return { value: item.change_pct, reason: null };
}

/** «▲ 0.43%», «▼ 5.63%», «0.00%»: flecha y color por el signo, cifras tabulares (CSS). */
export function changeLabel(c: number | null): { arrow: "▲" | "▼" | ""; text: string; sr: string } {
  if (c === null) return { arrow: "", text: "—", sr: "sin variación del periodo" };
  const v = `${(Math.abs(c) * PCT).toFixed(PCT_DECIMALS)}%`;
  if (c > 0) return { arrow: "▲", text: v, sr: `sube un ${v}` };
  if (c < 0) return { arrow: "▼", text: v, sr: `baja un ${v}` };
  return { arrow: "", text: v, sr: "sin cambios" };
}

/** Calidad y precio del motor, solo si están en caché (si no, la tarjeta no lleva esa línea). */
export function engineLine(item: TrendingItem): { quality: number; price: number } | null {
  const e = item.engine;
  if (!e || e.status !== "listo" || !e.quality || !e.price_score) return null;
  if (e.quality.score === null || e.price_score.score === null) return null;
  return { quality: Math.round(e.quality.score), price: Math.round(e.price_score.score) };
}

export { MINUS };

/** Un motivo del backend como frase: mayúscula inicial y punto final. */
export function sentence(t: string | null | undefined): string {
  const x = (t ?? "").trim();
  return x ? `${x.charAt(0).toUpperCase()}${x.slice(1)}${/[.…]$/.test(x) ? "" : "."}` : "";
}
