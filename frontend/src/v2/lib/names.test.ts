import { describe, expect, it } from "vitest";
import type { StockAnalysis } from "@/lib/api";
import { inline, profileNames } from "@/lib/names";

const analysis = (display: object, profile: object) => ({ display, profile } as unknown as StockAnalysis);

describe("nombres en español (V7)", () => {
  it("usa display.profile y, sin él, el perfil de la fuente", () => {
    const es = analysis({ profile: { sector: "Consumo defensivo", industry: "Bebidas sin alcohol", country: "Estados Unidos" } },
      { sector: "Consumer Defensive", industry: "Beverages—Non-Alcoholic", country: "United States" });
    expect(profileNames(es)).toEqual({ sector: "Consumo defensivo", industry: "Bebidas sin alcohol", country: "Estados Unidos" });
    const old = analysis({}, { sector: "Consumer Defensive", industry: "Beverages—Non-Alcoholic", country: "United States" });
    expect(profileNames(old)).toEqual({ sector: "Consumer Defensive", industry: "Beverages—Non-Alcoholic", country: "United States" });
  });
  it("a mitad de frase, en minúscula salvo las siglas", () => {
    expect(inline("Electrónica de consumo")).toBe("electrónica de consumo");
    expect(inline("REIT de locales comerciales")).toBe("REIT de locales comerciales");
    expect(inline(null)).toBe("");
  });
});
