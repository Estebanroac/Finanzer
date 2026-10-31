import { TickMarkType, isBusinessDay, isUTCTimestamp, type Time } from "lightweight-charts";

const MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];
const MS_PER_S = 1000;

/** Fecha de la gráfica (día hábil, marca de tiempo o "AAAA-MM-DD") → año, mes (0–11) y día. */
function parts(t: Time): { y: number; m: number; d: number } {
  if (isBusinessDay(t)) return { y: t.year, m: t.month - 1, d: t.day };
  const date = isUTCTimestamp(t) ? new Date(t * MS_PER_S) : new Date(`${t}T00:00:00Z`);
  return { y: date.getUTCFullYear(), m: date.getUTCMonth(), d: date.getUTCDate() };
}

/** Rótulo de las marcas del eje temporal, en español (el formateador por defecto usa el idioma del navegador). */
export function tickLabel(t: Time, type: TickMarkType): string {
  const { y, m, d } = parts(t);
  if (type === TickMarkType.Year) return String(y);
  if (type === TickMarkType.Month) return MESES[m];
  return `${d} ${MESES[m]}`;
}

/** Fecha completa para la etiqueta del cursor: "14 May 2026". */
export function crosshairLabel(t: Time): string {
  const { y, m, d } = parts(t);
  return `${d} ${MESES[m]} ${y}`;
}
