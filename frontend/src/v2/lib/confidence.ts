import type { StockAnalysis } from "@/lib/api";

/** V7 · P1: la línea bajo «Consistencia» (antes «Confianza del veredicto»; Fase 1 · pendientes, 7-nov-2026), la misma que el PDF (backend/lib/pdf_v2/cover.confidence_line)
 *  y que la página Conclusión (que enseña el resumen entero): el resumen del motor (M5 bis) sin su primera frase, que
 *  repite el nivel («Confianza del veredicto: alta.»). Dice qué no puntúa (el DCF directo descartado), cuánto contrae
 *  el precio y si contrae la calidad (F8 · E11: solo con confianza baja). */
export function confidenceLine(conf: StockAnalysis["display"]["confidence"] | null | undefined): string | null {
  const s = (conf?.summary ?? "").trim();
  const [first, ...rest] = s.split(/(?<=\.)\s+(?=[A-ZÁÉÍÓÚÑ¿¡])/);
  if (rest.length && (first.startsWith("Consistencia") || first.startsWith("Confianza del veredicto"))) return rest.join(" ");
  return s || null;
}
