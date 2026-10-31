import type { ScaleModel } from "./scale";

/** Las marcas de las escalas (encargo del PM tras la pre-pasada V4): bajo sus tramos, en proporción, mientras quepan;
 *  si no caben (la tarjeta de unos 229 px del iPad, cuatro marcas a 12 px), una leyenda de una fila por tramo. El corte
 *  sale de las bandas y de los nombres, así vale con cualquier juego de umbrales (80 o 85 para «excelente»). Lo aplica
 *  una consulta de contenedor en CSS (v2.css, `data-fit`): sin medir en el navegador ni mover nada tras pintar. */

/** Anchos de Geist en em (medidos en Chromium a 12 px; WebKit da lo mismo). Los que no están cuentan como un dígito. */
const GLYPH_EM: Record<string, number> = {
  a: 0.551, b: 0.586, c: 0.537, d: 0.586, e: 0.552, f: 0.316, g: 0.585, h: 0.575, i: 0.225, j: 0.251, k: 0.543,
  l: 0.258, m: 0.858, n: 0.562, o: 0.564, p: 0.586, q: 0.586, r: 0.341, s: 0.511, t: 0.329, u: 0.575, v: 0.536,
  w: 0.819, x: 0.547, y: 0.537, z: 0.522, á: 0.551, é: 0.552, í: 0.225, ó: 0.564, ú: 0.575, ñ: 0.562, ü: 0.575,
  "–": 0.591, "-": 0.419, "+": 0.558, "<": 0.544, ">": 0.544, "≥": 0.575, " ": 0.25, ".": 0.201,
};
const DIGIT_EM = 0.6;
/** Margen sobre la medida (redondeo y motor). */
const SAFETY = 1.02;
/** Letra de las marcas (--fs-label), hueco entre tramos de la barra (2 px) y separación mínima entre dos marcas
 *  vecinas, en rem. */
const LABEL_REM = 0.75;
const BAR_GAP_REM = 0.125;
const MIN_SEP_REM = 0.25;
/** Una marca de un extremo puede salirse de su tramo hacia el relleno de la tarjeta hasta esto (rem, por lado). */
const EDGE_REM = 0.5;
/** Cortes de la consulta de contenedor en v2.css (`width < N rem`, de medio en medio rem): por debajo de FIT_MIN_REM,
 *  nunca leyenda; por encima de FIT_MAX_REM, siempre. */
export const FIT_MIN_REM = 12;
export const FIT_MAX_REM = 32;
const FIT_STEP_REM = 0.5;

/** Ancho de un texto de las marcas, en em de su letra. */
export function textEm(text: string): number {
  return [...text.toLowerCase()].reduce((sum, ch) => sum + (GLYPH_EM[ch] ?? DIGIT_EM), 0);
}

/** Ancho mínimo del contenido de la tarjeta (rem) para que las marcas de esta escala quepan bajo sus tramos: cada
 *  marca (nombre sobre rango) centrada en su columna, sin pisar a la vecina y sin salirse de la tarjeta. */
export function ticksFitRem(model: ScaleModel): number {
  const segs = model.segments;
  const gaps = Math.max(segs.length - 1, 0) * BAR_GAP_REM;
  const label = segs.map((s) => Math.max(textEm(s.label), textEm(s.range)) * LABEL_REM * SAFETY);
  const share = segs.map((s) => s.widthPct / 100);
  const needs: number[] = [];
  segs.forEach((_, i) => {
    // Extremos: la marca puede asomar EDGE_REM por fuera de su tramo (va centrada: el doble en total).
    if (i === 0 || i === segs.length - 1) needs.push(Math.max(label[i] - 2 * EDGE_REM, 0) / share[i] + gaps);
    // Vecinas: la distancia entre centros cubre media marca de cada una y la separación.
    if (i + 1 < segs.length) needs.push((label[i] + label[i + 1] + 2 * MIN_SEP_REM) / (share[i] + share[i + 1]) + gaps);
  });
  return Math.max(...needs);
}

/** El corte de la fila de tarjetas (las tres cambian a la vez, por simetría): el `data-fit` que lee v2.css. */
export function ticksFitAttr(models: ScaleModel[]): string {
  const need = Math.max(...models.map(ticksFitRem));
  if (need > FIT_MAX_REM) return "always";
  return String(Math.max(Math.ceil(need / FIT_STEP_REM) * FIT_STEP_REM, FIT_MIN_REM));
}
