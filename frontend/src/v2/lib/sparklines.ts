/** P8: mini-gráficas del cintillo de la portada (GET /api/v2/sparklines, backend/lib/sparklines.py). Los puntos ya
 *  llegan reducidos (LTTB en el backend); aquí solo se dibujan: curva suave (Catmull-Rom → Bézier), relleno bajo la
 *  curva, línea de referencia (cierre anterior en 1D, primer cierre en el resto) y el último precio. */

export type SparkPeriod = "1D" | "1S" | "1M" | "6M";
export const SPARK_PERIODS: Array<{ key: SparkPeriod; label: string }> = [
  { key: "1D", label: "1 día" }, { key: "1S", label: "1 semana" }, { key: "1M", label: "1 mes" }, { key: "6M", label: "6 meses" },
];

export interface SparkItem {
  status: "ok" | "sin_dato";
  reason: string | null;
  /** [índice de la barra original, cierre]; `n` barras en total (el eje x es el índice). */
  points?: Array<[number, number]>;
  n?: number;
  ref?: number;
  ref_basis?: "cierre anterior" | "primer cierre";
  last?: number;
  change_pct?: number;
  first_t?: string;
  last_t?: string;
  /** Portada rápida: pasada su vida en caché, el servidor la sirve al momento mientras la refresca. */
  stale?: boolean;
}

export interface SparkResponse {
  period: SparkPeriod;
  label: string;
  interval: string;
  as_of: string | null;
  items: Record<string, SparkItem>;
}

// Misma regla que API_BASE de @/lib/api (no se exporta allí y la web actual no se toca).
const API_BASE = process.env.NEXT_PUBLIC_API_URL ||
  (typeof window !== "undefined" && window.location.port === "3000" ? "http://localhost:8000" : "");

/** Como mucho 40 símbolos por petición (backend [sparklines] max_symbols): se parte en tandas. */
const MAX_PER_REQUEST = 40;

export async function fetchSparklines(symbols: string[], period: SparkPeriod, signal?: AbortSignal): Promise<SparkResponse> {
  const out: SparkResponse = { period, label: "", interval: "", as_of: null, items: {} };
  for (let i = 0; i < symbols.length; i += MAX_PER_REQUEST) {
    const q = encodeURIComponent(symbols.slice(i, i + MAX_PER_REQUEST).join(","));
    const res = await fetch(`${API_BASE}/api/v2/sparklines?symbols=${q}&period=${period}`, { signal });
    if (!res.ok) throw new Error(`mini-gráficas: HTTP ${res.status}`);
    const r: SparkResponse = await res.json();
    Object.assign(out.items, r.items);
    out.label = r.label;
    out.interval = r.interval;
    if (r.as_of && (!out.as_of || r.as_of > out.as_of)) out.as_of = r.as_of;
  }
  return out;
}

/** Portada rápida: las mini-gráficas que llegaron caducadas (`stale`) se vuelven a pedir una vez, cuando el servidor ya
 *  las ha refrescado; `asked` («periodo:símbolo») recuerda las ya repetidas para no pedirlas en bucle. */
export function staleToRefresh(items: Record<string, SparkItem>, asked: ReadonlySet<string>, period: SparkPeriod): string[] {
  return Object.entries(items).filter(([s, it]) => it.stale && !asked.has(`${period}:${s}`)).map(([s]) => s);
}

/** Tamaño de la mini-gráfica (viewBox) y márgenes: a la derecha cabe el halo del último punto; arriba y abajo, el trazo. */
export const SPARK_W = 136;
export const SPARK_H = 52;
const PAD_RIGHT = 6;
const PAD_Y = 4;
const HALF = 0.5;
const SIXTH = 6;
const DECIMALS = 1;
/** Con menos de dos puntos no hay línea. */
const MIN_POINTS = 2;

export interface SparkGeometry {
  line: string;          // trazo
  area: string;          // relleno bajo la curva hasta la base
  refY: number;          // línea de referencia
  dot: { x: number; y: number };
  tone: "good" | "bad" | "neutral";
}

const f = (v: number) => v.toFixed(DECIMALS);

/** Curva Catmull-Rom (uniforme) por los puntos, como Bézier cúbicas: pasa por todos y sin picos artificiales. */
export function smoothPath(pts: Array<{ x: number; y: number }>): string {
  if (pts.length === 0) return "";
  let d = `M${f(pts[0].x)},${f(pts[0].y)}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[Math.max(0, i - 1)], p1 = pts[i], p2 = pts[i + 1], p3 = pts[Math.min(pts.length - 1, i + 2)];
    const c1 = { x: p1.x + (p2.x - p0.x) / SIXTH, y: p1.y + (p2.y - p0.y) / SIXTH };
    const c2 = { x: p2.x - (p3.x - p1.x) / SIXTH, y: p2.y - (p3.y - p1.y) / SIXTH };
    d += ` C${f(c1.x)},${f(c1.y)} ${f(c2.x)},${f(c2.y)} ${f(p2.x)},${f(p2.y)}`;
  }
  return d;
}

/** Signo de la variación del periodo: verde si sube, teja si baja, neutro si es 0. */
export function changeTone(c: number | null | undefined): "good" | "bad" | "neutral" {
  return c === null || c === undefined || c === 0 ? "neutral" : c > 0 ? "good" : "bad";
}

/** Geometría de la mini-gráfica: la escala vertical incluye siempre la referencia; sin ejes ni etiquetas. */
export function sparkGeometry(item: SparkItem, w = SPARK_W, h = SPARK_H): SparkGeometry | null {
  const pts = item.points ?? [];
  if (item.status !== "ok" || pts.length < MIN_POINTS || item.ref === undefined) return null;
  const n = Math.max(item.n ?? pts.length, MIN_POINTS);
  const ys = pts.map((p) => p[1]).concat(item.ref);
  let lo = Math.min(...ys), hi = Math.max(...ys);
  if (hi === lo) { lo -= HALF; hi += HALF; }
  const x = (i: number) => (i / (n - 1)) * (w - PAD_RIGHT);
  const y = (v: number) => PAD_Y + (1 - (v - lo) / (hi - lo)) * (h - 2 * PAD_Y);
  const xy = pts.map(([i, v]) => ({ x: x(i), y: y(v) }));
  const line = smoothPath(xy);
  const end = xy[xy.length - 1];
  return {
    line,
    area: `${line} L${f(end.x)},${f(h)} L${f(xy[0].x)},${f(h)} Z`,
    refY: Number(f(y(item.ref))),
    dot: { x: Number(f(end.x)), y: Number(f(end.y)) },
    tone: changeTone(item.change_pct),
  };
}
