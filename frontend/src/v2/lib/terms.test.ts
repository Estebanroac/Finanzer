import { describe, expect, it } from "vitest";
import { DEFINITIONS } from "@/lib/tooltips";
import { categoryTerm, confidenceTerm, definitionKey, marketTerm, priceRowTerm } from "./terms";

// V7 · P3: cada etiqueta del motor que sale en el bloque superior y en el capítulo 3 tiene su definición.
describe("terms", () => {
  it("las cinco categorías, las filas del precio del panel y las dimensiones de la confianza", () => {
    for (const c of ["Solidez Financiera", "Rentabilidad", "Calidad de Ganancias", "Crecimiento", "Valoración"])
      expect(categoryTerm(c)).toBeTruthy();
    // etiquetas de M5 (qué puntúa de verdad)
    for (const r of ["Bloque de múltiplos · 5 múltiplos", "DCF directo (valor frente al precio) · -31%", "DCF directo: no puntúa",
      "DCF inverso (lo que exige el precio) · 25%", "Bloque P/B y P/TBV · 1.9x", "P/FFO (REIT) · 14x",
      "DCF inverso (FFO) · 3%", "DCF inverso (flujo de mantenimiento)", "Rentabilidad por dividendo (utility)",
      "P/B frente al ROE regulado", "EV/Ventas · 4x", "Regla de 40 · 52", "Ajuste por confianza"])
      expect(priceRowTerm(r), r).toBeTruthy();
    expect(priceRowTerm("DCF inverso (FFO)")).toBe("reverse_dcf");
    expect(priceRowTerm("DCF directo (valor frente al precio)")).toBe("dcf_upside");
    expect(priceRowTerm("DCF inverso (lo que exige el precio)")).toBe("reverse_dcf");
    for (const k of ["convergence", "coverage", "source", "stability", "fuente_oficial"]) expect(confidenceTerm(k)).toBeTruthy();
    for (const k of ["momentum", "trend", "volatility", "drawdown", "volume", "pead", "relative_strength", "pos52"])
      expect(marketTerm(k)).toBeTruthy();
  });

  it("v4: la ayuda de la beta es la de la cifra de la tarjeta (las tres etiquetas del motor)", () => {
    expect(DEFINITIONS[definitionKey("beta", "Beta ajustada (Blume)")].title).toBe("Beta ajustada (Blume)");
    expect(DEFINITIONS[definitionKey("beta", "Beta de la industria")].title).toBe("Beta de la industria");
    expect(definitionKey("beta", "Beta bruta")).toBe("beta");
    expect(definitionKey("roe", "Beta ajustada (Blume)")).toBe("roe");
  });

  it("sin definición, nada (no un «?» vacío)", () => {
    expect(categoryTerm("Otra")).toBeUndefined();
    expect(priceRowTerm("Algo nuevo")).toBeUndefined();
    expect(marketTerm("nueva_señal")).toBeUndefined();
  });
});
