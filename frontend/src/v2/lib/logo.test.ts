import { API_BASE } from "@/v2/lib/http";
import { describe, expect, it } from "vitest";
import { analysisLogo, logoInitials, logoSrc } from "./logo";
import type { StockAnalysis } from "@/lib/api";

describe("logoInitials", () => {
  it("la inicial de las dos primeras palabras con sentido", () => {
    expect(logoInitials("Home Depot", "HD")).toBe("HD");
    expect(logoInitials("Bank of America Corporation", "BAC")).toBe("BA");
    expect(logoInitials("JPMorgan Chase & Co.", "JPM")).toBe("JC");
    expect(logoInitials("The Coca-Cola Company", "KO")).toBe("CC");
    expect(logoInitials("Netflix Inc.", "NFLX")).toBe("N");
    expect(logoInitials("LVMH Moët Hennessy Louis Vuitton SE", "MC.PA")).toBe("LM");
    expect(logoInitials("Ørsted A/S", "ORSTED.CO")).toBe("ØA");
  });
  it("sin nombre, el ticker sin su bolsa", () => {
    expect(logoInitials(null, "MC.PA")).toBe("MC");
    expect(logoInitials("", "BRK-B")).toBe("BR");
    expect(logoInitials(undefined, "v")).toBe("V");
  });
});

describe("logoSrc", () => {
  it("la URL versionada del análisis, la del endpoint en las listas y ninguna si no hay", () => {
    expect(logoSrc("NFLX", { url: "/api/v2/logo/NFLX?v=abc", source: "Parqet" })).toBe(`${API_BASE}/api/v2/logo/NFLX?v=abc`);
    expect(logoSrc("brk-b")).toBe(`${API_BASE}/api/v2/logo/BRK-B`);
    expect(logoSrc("MC.PA", undefined)).toBe(`${API_BASE}/api/v2/logo/MC.PA`);
    expect(logoSrc("ZZZZ", null)).toBeNull();
  });
});

describe("analysisLogo", () => {
  it("lee el logotipo que añade el endpoint, sin exigirlo", () => {
    const a = { symbol: "NFLX" } as unknown as StockAnalysis;
    expect(analysisLogo(a)).toBeUndefined();
    expect(analysisLogo({ ...a, logo: null } as unknown as StockAnalysis)).toBeNull();
  });
});
