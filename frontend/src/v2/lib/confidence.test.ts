import { describe, expect, it } from "vitest";
import type { StockAnalysis } from "@/lib/api";
import { confidenceLine } from "./confidence";

const conf = async (t: string) => ((await import(`@/v2/__fixtures__/${t}.json`)).default as unknown as StockAnalysis).display.consistency;

// V7 · P1: la línea bajo «Consistencia» (antes «Confianza del veredicto») (la misma que el PDF: cover.confidence_line, test_pdf_v2_report.py)
describe("confidenceLine", () => {
  // Fase 1 · pendientes (7-nov-2026): la consistencia (antes, la confianza); ya no contrae el precio ni la calidad.
  it("DOW: el DCF directo descartado no puntúa, y el que puntúa", async () => {
    expect(confidenceLine(await conf("DOW"))).toBe("No es una probabilidad de acierto. El DCF "
      + "directo, de fiabilidad baja, no puntúa ni cuenta para la convergencia; en Valoración puntúa el DCF inverso "
      + "(−2 puntos).");
  });
  it("O: consistente, sin ninguna frase de contracción", async () => {
    const line = confidenceLine(await conf("O"))!;
    expect(line).toMatch(/^No es una probabilidad de acierto/);
    expect(line).not.toMatch(/Contrae|contrae/);
  });
  it("es el final del resumen que enseña la página Conclusión, sin nada más", async () => {
    for (const t of ["AAPL", "JPM", "O", "NEE", "XOM", "PLTR", "RIVN", "BCS", "DOW"]) {
      const c = await conf(t);
      expect(c!.summary.endsWith(confidenceLine(c)!), t).toBe(true);
    }
    expect(confidenceLine(null)).toBeNull();
  });
});
