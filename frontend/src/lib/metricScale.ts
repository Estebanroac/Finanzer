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

const RULES: Record<string, Rule> = {
  // ── % (decimal), mayor es mejor ──
  roe: higher(0.15, 0.1),
  roa: higher(0.08, 0.05),
  roic: higher(0.12, 0.08),
  gross_margin: higher(0.4, 0.2),
  operating_margin: higher(0.15, 0.1),
  net_margin: higher(0.1, 0.05),
  ebitda_margin: higher(0.15, 0.1),
  fcf_yield: higher(0.05, 0.03),
  earnings_yield: higher(0.06, 0.03),
  // crecimiento YoY: fuerte >=8%, débil/estancado 2-8% (ámbar), contracción <2% (rojo)
  revenue_growth: higher(0.08, 0.02),
  earnings_growth: higher(0.08, 0.02),
  // sin dividendo NO es "malo" (muchas tech no reparten) → neutral
  dividend_yield: (v) => (v >= 0.02 ? "good" : v >= 0.01 ? "ok" : "neutral"),

  // ── ratios crudos, menor es mejor ──
  pe: lower(15, 25),
  forward_pe: lower(15, 25),
  pb: lower(1, 3),
  ps: lower(2, 5),
  pfcf: lower(15, 25),
  p_fcf: lower(15, 25),
  ev_ebitda: lower(10, 15),
  peg: lower(1, 1.5),
  de: lower(0.5, 1.0),
  debt_to_assets: lower(0.3, 0.5),
  net_debt_to_ebitda: lower(1.5, 3.0),

  // ── ratios crudos, mayor es mejor ──
  current_ratio: higher(1.5, 1.0),
  quick_ratio: higher(1.0, 0.5),
  cash_ratio: higher(0.5, 0.2),
  interest_coverage: higher(5, 2),

  // ── especiales ──
  // payout: reinvertir mucho (neutral), equilibrado (bueno), alto (ok), insostenible (malo)
  payout_ratio: (v) => (v < 0.3 ? "neutral" : v <= 0.6 ? "good" : v <= 0.8 ? "ok" : "bad"),
  // retorno al accionista: positivo bueno, dilución mala, ~cero neutral
  buyback_yield: (v) => (v > 0.005 ? "good" : v < -0.005 ? "bad" : "neutral"),
  shareholder_yield: (v) => (v > 0.01 ? "good" : v < 0 ? "bad" : "neutral"),
  // beta: rango normal de mercado ~verde; extremos amarillo/rojo; defensiva neutral
  beta: (v) => (v < 0.8 ? "neutral" : v <= 1.2 ? "good" : v <= 1.5 ? "ok" : "bad"),
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
