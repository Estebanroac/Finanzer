import { describe, it, expect } from "vitest";
import { buildScale, buildLevelScale } from "./scale";

describe("buildScale", () => {
  it("calidad 79: cuatro tramos con las bandas del motor y la marca en 79", () => {
    const m = buildScale("quality", 79, "sólida");
    expect(m.segments.map((s) => s.label)).toEqual(["débil", "media", "sólida", "excelente"]);
    // Anchos como cadena: el guardián de literales (que también recorre los tests de /v2) prohíbe arrays de números.
    expect(m.segments.map((s) => s.widthPct).join(" ")).toBe("45 20 20 15");
    expect(m.pinPct).toBe(79);
    expect(m.segments.reduce((a, s) => a + s.widthPct, 0)).toBe(100);
  });
  it("precio 10 (F16, regla L1): exigente a la izquierda, razonable neutro, atractivo a la derecha", () => {
    const m = buildScale("price", 10, "exigente");
    expect(m.segments.map((s) => s.label)).toEqual(["exigente", "razonable", "atractivo"]);
    expect(m.segments.map((s) => s.widthPct).join(" ")).toBe("34 33 33");
    expect(m.segments.map((s) => s.tone).join(" ")).toBe("bad neutral good");
  });
  it("sin puntuación: sin marca", () => {
    expect(buildScale("quality", null, null).pinPct).toBeNull();
  });
  it("cada tramo lleva su rango del motor, también los intermedios", () => {
    expect(buildScale("quality", 79, "sólida").segments.map((s) => `${s.label} ${s.range}`).join(" | "))
      .toBe("débil <45 | media 45–65 | sólida 65–85 | excelente 85+");
    expect(buildScale("price", 10, "exigente").segments.map((s) => `${s.label} ${s.range}`).join(" | "))
      .toBe("exigente <34 | razonable 34–67 | atractivo 67+");
  });
});

describe("buildLevelScale (confianza)", () => {
  it("tres tramos iguales de peor a mejor y la marca en el centro del nivel", () => {
    const m = buildLevelScale("confidence", "alta");
    expect(m.segments.map((s) => s.label).join(" ")).toBe("baja media alta");
    expect(m.segments.every((s) => s.range === "")).toBe(true);     // niveles sin rango numérico
    expect(m.segments.map((s) => s.tone).join(" ")).toBe("warn neutral good");
    const alta = m.segments[m.segments.length - 1];
    expect(m.pinPct).toBeCloseTo((alta.from + alta.to) / 2);
    expect(m.segments.reduce((a, s) => a + s.widthPct, 0)).toBeCloseTo(100);
  });
  it("nivel desconocido: sin marca", () => {
    expect(buildLevelScale("confidence", null).pinPct).toBeNull();
  });
});
