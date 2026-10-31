import type { Tone } from "@/lib/api";

export type VTone = "good" | "warn" | "bad" | "neutral";

/** Tono del motor (`display`) → tono visual de /v2. */
export const toVTone = (t: Tone | null | undefined): VTone =>
  t === "pos" ? "good" : t === "warn" ? "warn" : t === "neg" ? "bad" : "neutral";

/** Tono de cada banda de una tabla de sensibilidad (band_labels del motor: de muy por encima a muy por debajo del
 *  precio). Lo comparten la del informe y la del escenario. */
export const SENS_BAND_TONES: VTone[] = ["good", "good", "neutral", "warn", "bad"];
