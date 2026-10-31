import type { TrendingData, TrendingEngine, TrendingItem, TrendingResponse } from "@/lib/api";

export type ListKey = "most_traded" | "gainers" | "losers";
export const LIST_KEYS: ListKey[] = ["most_traded", "gainers", "losers"];

const NY = "America/New_York";
const MINUS = "−";
const PCT = 100;
const PCT_DECIMALS = 2;

/** Fecha de Nueva York (AAAA-MM-DD) de un instante. */
export function nyDate(d: Date): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: NY, year: "numeric", month: "2-digit", day: "2-digit" }).format(d);
}

/** Conductual (spec §3.5): cada lista se titula por lo que mide; "hoy" solo si la sesión es la de hoy. */
export function listTitle(key: ListKey, session: string | null, now: Date): string {
  const today = session !== null && session === nyDate(now);
  if (key === "most_traded") return today ? "Más negociadas hoy" : "Más negociadas";
  if (key === "gainers") return today ? "Mayores subidas hoy" : "Mayores subidas";
  return today ? "Mayores caídas hoy" : "Mayores caídas";
}

/** Qué mide cada lista, en una frase (debajo de las pestañas). */
export function listMeasure(key: ListKey): string {
  if (key === "most_traded") return "Por dinero negociado en la sesión (precio de cierre × acciones negociadas).";
  if (key === "gainers") return "Por subida del precio de cierre frente a la sesión anterior.";
  return "Por caída del precio de cierre frente a la sesión anterior.";
}

function longDate(iso: string): string {
  // Mediodía UTC: la fecha del calendario no cambia con la zona horaria.
  return new Intl.DateTimeFormat("es-ES", { timeZone: "UTC", day: "numeric", month: "long", year: "numeric" })
    .format(new Date(`${iso}T12:00:00Z`));
}

/** "Sesión del 16 de octubre de 2026 · Actualizado el 17 de octubre de 2026 a las 16:35 (Nueva York) · universo: …". */
export function footerText(d: TrendingData): string {
  const at = new Date(d.as_of);
  const day = new Intl.DateTimeFormat("es-ES", { timeZone: NY, day: "numeric", month: "long", year: "numeric" }).format(at);
  const time = new Intl.DateTimeFormat("es-ES", { timeZone: NY, hour: "2-digit", minute: "2-digit", hour12: false }).format(at);
  const universe = d.universe_date ? ` (${longDate(d.universe_date)})` : "";
  return `Sesión del ${longDate(d.session)} · Actualizado el ${day} a las ${time} (Nueva York) · ` +
    `universo: S&P 500 y ADR principales${universe}`;
}

export function priceText(p: number): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(p);
}

export function changeText(c: number): string {
  const v = (Math.abs(c) * PCT).toFixed(PCT_DECIMALS);
  return `${c > 0 ? "+" : c < 0 ? MINUS : ""}${v}%`;
}

export function changeTone(c: number): "good" | "bad" | "neutral" {
  return c > 0 ? "good" : c < 0 ? "bad" : "neutral";
}

const pending = (e: TrendingEngine | null) => e !== null && (e.status === "en_cola" || e.status === "analizando");

/** Hay que volver a preguntar: las listas se calculan, se refrescan o alguna tarjeta tiene el motor en marcha. */
export function shouldPoll(r: TrendingResponse | null): boolean {
  if (r === null) return true;
  if (r.status === "calculando" || r.refreshing) return true;
  if (r.status !== "listo" || !r.data) return false;
  // P8b: las listas van por periodo; cualquier tarjeta de cualquier periodo con el motor en marcha
  return Object.values(r.data.lists).some((L) => LIST_KEYS.some((k) => L[k].some((x: TrendingItem) => pending(x.engine))));
}

/** En el replay de pruebas, el motor falla con este texto para las empresas sin fixtures (tests/replay_server.py). */
const REPLAY_NO_FIXTURES = /sin fixtures en el replay/;
/** V4b: en la cola de fondo del replay, la empresa sin datos grabados no es un fallo (con datos reales se analiza). */
const REPLAY_NOT_IN_DEMO = /^No incluido en la demo/;

/** Estado del motor en la tarjeta. Las tres formas tienen el mismo esquema (dos filas de escala y una línea de estado):
 *  puntuaciones, esqueleto mientras analiza o «sin dato» con el motivo. */
export type EngineView =
  | { kind: "ready"; engine: TrendingEngine; status: string }
  | { kind: "pending"; status: string }
  | { kind: "missing"; status: string };

export function engineView(e: TrendingEngine | null): EngineView {
  if (e === null) return { kind: "missing", status: "Sin análisis por ahora" };
  if (e.status === "listo" && e.quality && e.price_score) return { kind: "ready", engine: e, status: "Analizada por Finanzer" };
  if (pending(e)) return { kind: "pending", status: e.status === "analizando" ? "Analizando…" : "En cola para analizar…" };
  if (e.reason && REPLAY_NOT_IN_DEMO.test(e.reason)) return { kind: "missing", status: "No incluido en la demo" };
  if (e.reason && REPLAY_NO_FIXTURES.test(e.reason)) return { kind: "missing", status: "Sin fixtures en el replay" };
  return { kind: "missing", status: "Finanzer no pudo analizarla" };
}

/** Texto del enlace de la tarjeta (toda la tarjeta lleva a /v2/{T}; allí se analiza de nuevo si hace falta). */
export function cardAction(v: EngineView): string {
  return v.kind === "ready" ? "Ver el análisis →" : "Abrir el análisis →";
}
