import { SCORE_BANDS } from "@/lib/generated/backendConfig";

export type ScaleKind = "quality" | "price" | "confidence";
export type ScaleTone = "good" | "warn" | "bad" | "neutral";
/** `range`: el rango del motor en texto ("<45", "45–65", "85+"); vacío en las escalas por niveles. */
export interface ScaleSegment { label: string; range: string; from: number; to: number; widthPct: number; tone: ScaleTone }
export interface ScaleModel { kind: ScaleKind; score: number | null; level: string | null; segments: ScaleSegment[]; pinPct: number | null }

const FULL = 100;

/** Tono de cada tramo, del peor (índice 0) al mejor (último). */
function toneFor(index: number, count: number): ScaleTone {
  if (index === 0) return "bad";
  if (index === count - 1) return "good";
  // F16: con 3 tramos (precio L1) el segundo es el central, neutro; con 4, el segundo peor va en aviso
  return index === 1 && index !== count - 2 ? "warn" : "neutral";
}

/** Bandas de una puntuación: cortes de mayor a menor (≥) y nombres de mejor a peor, como en SCORE_BANDS. */
export interface ScoreBands { bands: readonly number[]; labels: readonly string[] }

/** Puntuación 0–100 con las bandas del motor (calidad o precio). `cfg`: otras bandas (los tests de las marcas). */
export function buildScale(kind: "quality" | "price", score: number | null, level: string | null,
                           cfg: ScoreBands = SCORE_BANDS[kind]): ScaleModel {
  const { bands, labels } = cfg;
  // bands: de mayor a menor (≥); labels: de mejor a peor. Se recorren de peor a mejor.
  const cuts = [...bands].reverse();            // ascendente
  const names = [...labels].reverse();           // de peor a mejor
  const edges = [0, ...cuts, FULL];
  const last = names.length - 1;
  const segments: ScaleSegment[] = names.map((label, i) => ({
    label,
    // Rango de cada tramo con las bandas del motor: "<45", "45–65", "65–85", "85+".
    range: i === 0 ? `<${edges[i + 1]}` : i === last ? `${edges[i]}+` : `${edges[i]}–${edges[i + 1]}`,
    from: edges[i],
    to: edges[i + 1],
    widthPct: edges[i + 1] - edges[i],
    tone: toneFor(i, names.length),
  }));
  return { kind, score, level, segments, pinPct: score === null ? null : Math.min(Math.max(score, 0), FULL) };
}

/** Escala por niveles sin puntuación (confianza del veredicto): tramos iguales, marca en el centro del nivel. */
export function buildLevelScale(kind: "confidence", level: string | null): ScaleModel {
  const names = [...SCORE_BANDS[kind].labels].reverse();   // de peor a mejor
  const width = FULL / names.length;
  const last = names.length - 1;
  const segments: ScaleSegment[] = names.map((label, i) => ({
    label, range: "", from: i * width, to: (i + 1) * width, widthPct: width,
    // La confianza baja no es "mala" sino incierta: atención, no alarma.
    tone: i === 0 ? "warn" : i === last ? "good" : "neutral",
  }));
  const hit = segments.find((s) => s.label === level?.toLowerCase());
  return { kind, score: null, level, segments, pinPct: hit ? (hit.from + hit.to) / 2 : null };
}
