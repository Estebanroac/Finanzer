// Formato (no lecturas): el mismo estilo que el motor (backend/lib/numfmt.py y display._money_cur) para los datos
// brutos que el cliente pinta (historia de 10 años, segmentos). Sin umbrales ni juicios.
const UNITS: Array<[number, string]> = [[1e12, "T"], [1e9, "B"], [1e6, "M"]];
const MINUS = "−";

/** $45.18B · −$147.78B · GBP 41.27B (la moneda de los estados, si no es USD). */
export function moneyCur(v: number | null | undefined, cur?: string | null): string {
  if (v == null || !Number.isFinite(v)) return "—";
  const a = Math.abs(v);
  const sign = v < 0 ? MINUS : "";
  const sym = !cur || cur === "USD" ? "$" : `${cur} `;
  for (const [div, suffix] of UNITS) if (a >= div) return `${sign}${sym}${(a / div).toFixed(2)}${suffix}`;
  return `${sign}${sym}${a.toLocaleString("en-US", { maximumFractionDigits: 0 })}`;
}

/** Importe por acción: $8.72 · GBP 0.31. */
export function perShareCur(v: number | null | undefined, cur?: string | null, dec = 2): string {
  if (v == null || !Number.isFinite(v)) return "—";
  const sym = !cur || cur === "USD" ? "$" : `${cur} `;
  return `${v < 0 ? MINUS : ""}${sym}${Math.abs(v).toFixed(dec)}`;
}

/** Valor estimado (el valor justo de un modelo) a dos cifras significativas, como numfmt.estimate (F8 · P3; revisión
 *  de COST: una sola cifra del DCF en la web y el PDF): $116.08 → $120, $7.13 → $7.1, EUR 403.87 → EUR 400. */
export function estimateCur(v: number | null | undefined, cur?: string | null): string {
  if (v == null || !Number.isFinite(v)) return "—";
  const sym = !cur || cur === "USD" ? "$" : `${cur} `;
  if (v === 0) return `${sym}0`;
  const d = Math.floor(Math.log10(Math.abs(v)));
  const dec = Math.max(0, 1 - d);
  const step = 10 ** (d - 1);
  const r = dec > 0 ? Number(Math.abs(v).toFixed(dec)) : Math.round(Math.abs(v) / step) * step;
  const txt = r.toLocaleString("en-US", { minimumFractionDigits: dec, maximumFractionDigits: dec });
  return `${v < 0 && r !== 0 ? MINUS : ""}${sym}${txt}`;
}

/** Fracción → porcentaje con un decimal: 0.276 → 27.6%. */
export function pct(v: number | null | undefined, dec = 1): string {
  if (v == null || !Number.isFinite(v)) return "—";
  const s = (Math.abs(v) * 100).toFixed(dec);
  return `${v < 0 ? MINUS : ""}${s}%`;
}

/** Fracción con signo: +5.4% · −2.1%. */
export function signedPct(v: number | null | undefined, dec = 1): string {
  if (v == null || !Number.isFinite(v)) return "—";
  return `${v > 0 ? "+" : v < 0 ? MINUS : ""}${(Math.abs(v) * 100).toFixed(dec)}%`;
}

const VOLUME_UNITS: Array<[number, string]> = [[1e9, "mil M"], [1e6, "M"]];
const VOLUME_DECIMALS: Record<string, number> = { "mil M": 2, M: 1 };
/** Volumen de acciones de una sesión: "1.23 mil M", "45.6 M" o el número entero. */
export function volume(v: number | null | undefined): string {
  if (v == null || !Number.isFinite(v)) return "Sin dato";
  for (const [div, suffix] of VOLUME_UNITS) if (Math.abs(v) >= div) return `${(v / div).toFixed(VOLUME_DECIMALS[suffix])} ${suffix}`;
  return v.toLocaleString("es-ES");
}

/** Mayúscula inicial para un título que el motor da en minúscula (lo usa también a mitad de frase): "zonas
 *  geográficas" -> "Zonas geográficas". */
export function capFirst(t: string): string {
  return t ? t.charAt(0).toUpperCase() + t.slice(1) : t;
}
