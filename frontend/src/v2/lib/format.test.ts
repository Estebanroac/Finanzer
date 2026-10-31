import { describe, expect, it } from "vitest";
import { estimateCur, moneyCur, pct, perShareCur, signedPct, volume } from "./format";

describe("formato como el motor", () => {
  it("importes con unidad y moneda", () => {
    expect(moneyCur(394328000000)).toBe("$394.33B");
    expect(moneyCur(-147780000000)).toBe("−$147.78B");
    expect(moneyCur(41270000000, "GBP")).toBe("GBP 41.27B");
    expect(moneyCur(null)).toBe("—");
  });
  it("por acción y porcentajes", () => {
    expect(perShareCur(8.72)).toBe("$8.72");
    expect(pct(0.2762)).toBe("27.6%");
    expect(signedPct(-0.0213)).toBe("−2.1%");
    expect(signedPct(0.054)).toBe("+5.4%");
  });
});

// Revisión de COST (hallazgo 6): el valor del DCF con una sola cifra en la web y el PDF, la de numfmt.estimate
describe("estimateCur", () => {
  it("dos cifras significativas, como el motor", () => {
    expect(estimateCur(116.08)).toBe("$120");
    expect(estimateCur(468.41)).toBe("$470");
    expect(estimateCur(7.13)).toBe("$7.1");
    expect(estimateCur(403.87, "EUR")).toBe("EUR 400");
    expect(estimateCur(1234.5)).toBe("$1,200");
    expect(estimateCur(-8.4)).toBe("−$8.4");
    expect(estimateCur(0.0456)).toBe("$0.046");
    expect(estimateCur(0)).toBe("$0");
    expect(estimateCur(null)).toBe("—");
  });
});

describe("volume", () => {
  it("unidades del volumen", () => {
    expect(volume(1_234_000_000)).toBe("1.23 mil M");
    expect(volume(45_600_000)).toBe("45.6 M");
    expect(volume(null)).toBe("Sin dato");
  });
});
