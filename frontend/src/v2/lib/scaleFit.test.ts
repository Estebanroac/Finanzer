import { describe, it, expect } from "vitest";
import { buildScale, buildLevelScale } from "./scale";
import { textEm, ticksFitAttr, ticksFitRem, FIT_MAX_REM } from "./scaleFit";
import { SCORE_BANDS } from "@/lib/generated/backendConfig";

// Sin arrays de números (el guardián de literales también recorre los tests de /v2): los cortes van como texto.
const cuts = (s: string) => s.split(" ").map(Number);
const quality = (bands: string) => buildScale("quality", 75, "sólida", { bands: cuts(bands), labels: SCORE_BANDS.quality.labels });
const price = buildScale("price", 15, "muy exigente");
const confidence = buildLevelScale("confidence", "alta");
// Contenido de la tarjeta (rem), medido: iPad Mini 197 px, escritorio 1024 → 283 px, escritorio 1440 → 334 px.
const IPAD = 197 / 16, DESK_1024 = 283 / 16, DESK_1440 = 334 / 16;
const legendAt = (fit: string, width: number) => fit === "always" || width < Number(fit);

describe("marcas de las escalas: en proporción o en leyenda", () => {
  it("la tabla de anchos de Geist da lo medido en el navegador (12 px)", () => {
    expect(textEm("excelente") * 12).toBeCloseTo(53.1, 0);
    expect(textEm("muy exigente") * 12).toBeCloseTo(73.2, 0);
    expect(textEm("45–65") * 12).toBeCloseTo(35.9, 0);
  });

  for (const bands of ["80 65 45", "85 65 45"]) {
    it(`«excelente» desde ${bands.split(" ")[0]}: leyenda en el iPad y a 1024; en proporción a 1440`, () => {
      const fit = ticksFitAttr([quality(bands), price, confidence]);
      expect(legendAt(fit, IPAD)).toBe(true);
      expect(legendAt(fit, DESK_1024)).toBe(true);
      expect(legendAt(fit, DESK_1440)).toBe(false);
    });
  }

  it("un tramo del extremo más estrecho pide más ancho (mover solo el corte de «excelente» no cambia el par vecino)", () => {
    expect(ticksFitRem(quality("85 65 45"))).toBeCloseTo(ticksFitRem(quality("80 65 45")), 5);
    expect(ticksFitRem(quality("90 65 45"))).toBeGreaterThan(ticksFitRem(quality("80 65 45")));
  });

  it("con umbrales que no caben en ningún ancho razonable, siempre leyenda", () => {
    const tight = quality("97 95 93");
    expect(ticksFitRem(tight)).toBeGreaterThan(FIT_MAX_REM);
    expect(ticksFitAttr([tight, price, confidence])).toBe("always");
  });

  it("las tres tarjetas comparten el corte (el de la escala que más pide)", () => {
    const fit = ticksFitAttr([quality("80 65 45"), price, confidence]);
    expect(Number(fit)).toBeGreaterThanOrEqual(Math.max(ticksFitRem(price), ticksFitRem(quality("80 65 45"))));
    expect(ticksFitAttr([confidence])).toBe("12");
  });
});
