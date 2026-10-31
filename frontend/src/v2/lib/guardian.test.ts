import { describe, it, expect } from "vitest";
import { scanSource, PAINT_ONLY } from "../../../scripts/check-analysis-literals.mjs";

// Revisión V6 (F1): el guardián prohíbe calcular en los archivos que solo pintan la serie de precios.
describe("guardián de literales y cálculos", () => {
  it("returns.ts y chartEvents.ts están entre los que solo pintan", () => {
    expect(PAINT_ONLY).toContain("src/v2/lib/returns.ts");
    expect(PAINT_ONLY).toContain("src/v2/lib/chartEvents.ts");
  });
  it("una división, un Math.* o un toFixed en un archivo que solo pinta es un error", () => {
    for (const code of ["const r = last / first;", "const x = Math.abs(v);", "const t = v.toFixed(1);", "const y = v * k;"]) {
      expect(scanSource("src/v2/lib/returns.ts", code).length).toBeGreaterThan(0);
    }
  });
  it("fuera de esos archivos, o sumando índices, no", () => {
    expect(scanSource("src/v2/lib/format.ts", "const r = last / first;")).toEqual([]);
    expect(scanSource("src/v2/lib/returns.ts", "const p = pts[w.i0 + i];")).toEqual([]);
  });
});
