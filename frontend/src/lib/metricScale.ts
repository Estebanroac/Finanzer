/**
 * Tono de CALIDAD de un valor según sus umbrales ABSOLUTOS.
 *
 * Espeja los `thresholds` de src/lib/tooltips.ts (la fuente de verdad de los
 * criterios) para que el COLOR de un valor cuadre siempre con los "rangos de
 * referencia" que muestra su tarjeta explicativa. Antes los colores eran
 * estáticos (accent hardcodeado) y no correspondían al umbral (ej. FCF Yield
 * 1.28% se pintaba verde cuando <3% es "Bajo").
 *
 * Unidades canónicas del frontend: los PORCENTAJES llegan como DECIMAL
 * (0.15 = 15%); los RATIOS como número crudo (pe = 25, de = 0.98).
 */
import { METRIC_SCALE_HIGHER, METRIC_SCALE_LOWER, METRIC_SCALE_SPECIAL } from "./generated/backendConfig";

export type Scale = "good" | "ok" | "bad" | "neutral";

export const SCALE_COLOR: Record<Scale, string> = {
  good: "#0cc06c", // verde marca
  ok: "#fbbf24",   // ámbar
  bad: "#ff453a",  // rojo
  neutral: "#e4e4e7", // zinc-200 — sin juicio de valor
};

type Rule = (v: number) => Scale;

// mayor es mejor: >=good → good, >=ok → ok, resto → bad
const higher = (good: number, ok: number): Rule => (v) => (v >= good ? "good" : v >= ok ? "ok" : "bad");
// menor es mejor: <=good → good, <=ok → ok, resto → bad
const lower = (good: number, ok: number): Rule => (v) => (v <= good ? "good" : v <= ok ? "ok" : "bad");

// Umbrales GENERADOS desde backend/config/thresholds.toml [ui.metric_scale]
// (backend/tools/gen_frontend_config.py). La lógica de cada regla sigue aquí.
const SP = METRIC_SCALE_SPECIAL;
const RULES: Record<string, Rule> = {
  ...Object.fromEntries(Object.entries(METRIC_SCALE_HIGHER).map(([k, [g, o]]) => [k, higher(g, o)])),
  ...Object.fromEntries(Object.entries(METRIC_SCALE_LOWER).map(([k, [g, o]]) => [k, lower(g, o)])),

  // ── especiales ──
  // sin dividendo NO es "malo" (muchas tech no reparten) → neutral
  dividend_yield: (v) => (v >= SP.dividend_yield[0] ? "good" : v >= SP.dividend_yield[1] ? "ok" : "neutral"),
  // payout: reinvertir mucho (neutral), equilibrado (bueno), alto (ok), insostenible (malo)
  payout_ratio: (v) => (v < SP.payout_ratio[0] ? "neutral" : v <= SP.payout_ratio[1] ? "good" : v <= SP.payout_ratio[2] ? "ok" : "bad"),
  // retorno al accionista: positivo bueno, dilución mala, ~cero neutral
  buyback_yield: (v) => (v > SP.buyback_yield[0] ? "good" : v < SP.buyback_yield[1] ? "bad" : "neutral"),
  shareholder_yield: (v) => (v > SP.shareholder_yield[0] ? "good" : v < SP.shareholder_yield[1] ? "bad" : "neutral"),
  // beta: rango normal de mercado ~verde; extremos amarillo/rojo; defensiva neutral
  beta: (v) => (v < SP.beta[0] ? "neutral" : v <= SP.beta[1] ? "good" : v <= SP.beta[2] ? "ok" : "bad"),
};

/** Escala de calidad de `value` para la métrica `key`, o null si no aplica. */
export function metricScale(key: string, value: number | null | undefined): Scale | null {
  if (value == null || !Number.isFinite(value)) return null;
  const rule = RULES[key];
  return rule ? rule(value) : null;
}

/** Color hex de calidad para `value`, o null si la métrica no tiene escala. */
export function scaleColor(key: string, value: number | null | undefined): string | null {
  const s = metricScale(key, value);
  return s ? SCALE_COLOR[s] : null;
}

/**
 * Índice de la banda de `thresholds` en la que cae `value` (para resaltar la
 * fila activa en la tarjeta explicativa), o -1 si no aplica.
 *
 * Parsea los strings de umbral (">8%", "5–8%", "<3%", "10B–200B", ">2.0") y
 * convierte `value` a la unidad del umbral: % → ×100 (value decimal), B/T →
 * /1e9 (market cap en dólares), resto → tal cual. Separador-agnóstico.
 */
export function activeBandIndex(
  thresholds: { value: string }[] | undefined,
  value: number | null | undefined,
): number {
  if (value == null || !Number.isFinite(value) || !thresholds || thresholds.length === 0) return -1;
  const first = thresholds[0].value;
  const v = /%/.test(first) ? value * 100 : /[BT]/.test(first) ? value / 1e9 : value;
  const bounds = (s: string): [number, number] => {
    const nums = (s.replace(/,/g, "").match(/\d+\.?\d*/g) || []).map(Number);
    if (nums.length === 0) return [NaN, NaN];
    if (s.includes(">")) return [nums[0], Infinity];
    if (s.includes("<")) return [-Infinity, nums[0]];
    if (nums.length >= 2) return [nums[0], nums[1]]; // rango: "5–8", "10B–200B"
    return [nums[0], nums[0]];
  };
  for (let i = 0; i < thresholds.length; i++) {
    const [min, max] = bounds(thresholds[i].value);
    if (v >= min && v < max) return i;
  }
  return -1;
}
