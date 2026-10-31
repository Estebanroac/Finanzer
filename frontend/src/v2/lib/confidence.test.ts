import { describe, expect, it } from "vitest";
import type { StockAnalysis } from "@/lib/api";
import { confidenceLine } from "./confidence";

const conf = async (t: string) => ((await import(`@/v2/__fixtures__/${t}.json`)).default as unknown as StockAnalysis).display.confidence;

// V7 · P1: la línea bajo «Confianza del veredicto» (la misma que el PDF: cover.confidence_line, test_pdf_v2_report.py)
describe("confidenceLine", () => {
  // F8 · E8: la fiabilidad del DCF va por sus insumos; el caso del directo descartado es DOW (antes, AAPL).
  it("DOW: el DCF directo descartado no puntúa, y el que puntúa (F8 · E11: con confianza baja contrae la calidad)", async () => {
    expect(confidenceLine(await conf("DOW"))).toMatch(new RegExp("^(Contrae el atractivo del precio hacia 50: de \\d+ a \\d+\\. )?El DCF directo, de fiabilidad baja, no puntúa ni "
      + "cuenta para la convergencia; en Valoración puntúa el DCF inverso \\([+−]\\d+ puntos?\\)\\. (La calidad del negocio no "
      + "se contrae|Contrae también la calidad del negocio hacia 50: de \\d+ a \\d+)\\.$"));
  });
  // F8 · E3: O pasó a confianza alta (FFO según Nareit): la contracción se probaba con BCS. F9 (fusión de R3 y R4): BCS
  // sube a confianza media (P/B del balance más reciente y sin el −2 del margen neto bancario) y ya no contrae la
  // calidad; la contracción de los dos se prueba con NEE (baja).
  it("NEE: lo que contrae el precio y la calidad (F8 · E11: con confianza baja; la primera frase, con su techo, es el nivel que ya enseña la tarjeta)", async () => {
    expect(confidenceLine(await conf("NEE"))).toBe("Contrae el atractivo del precio hacia 50: de 45 a 48. Contrae también la calidad del negocio hacia 50: de 56 a 55.");
  });
  // F10 · B2: BCS pasa a confianza baja (beneficio del ordinario, sin cupones AT1: convergencia baja) y contrae también
  // la calidad; F10 · N2: JPM sube a alta. El caso de confianza media que solo contrae el precio es O.
  it("O: con confianza media contrae el precio y no la calidad", async () => {
    expect(confidenceLine(await conf("O"))).toBe("Contrae el atractivo del precio hacia 50: de 75 a 69. La calidad del negocio no se contrae.");
  });
  it("es el final del resumen que enseña la página Conclusión, sin nada más", async () => {
    for (const t of ["AAPL", "JPM", "O", "NEE", "XOM", "PLTR", "RIVN", "BCS", "DOW"]) {
      const c = await conf(t);
      expect(c!.summary.endsWith(confidenceLine(c)!), t).toBe(true);
    }
    expect(confidenceLine(null)).toBeNull();
  });
});
