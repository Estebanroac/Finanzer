import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { TrendingData } from "@/lib/api";
import { cachedLabel, loadHome, saveHome } from "./homeCache";

const item = (symbol: string) => ({ symbol, name: symbol, price: 1, sector: null, change_pct: 0.01, dollar_volume: 1,
  engine: null });
const lists = (s: string) => ({ most_traded: [item(s)], gainers: [], losers: [] });
const data = (asOf: string): TrendingData => ({
  session: "2026-10-27", as_of: asOf, periods: {} as TrendingData["periods"],
  lists: { "1D": lists("AAA"), "6M": lists("ZZZ") } as unknown as TrendingData["lists"],
  list_notes: { "1D": { gainers: null, losers: null }, "6M": { gainers: null, losers: null } } as TrendingData["list_notes"],
  universe_date: null, count: 1, failed_batches: 0, note: null,
});
/** Un punto [índice, cierre] (helper: el control de literales de análisis no lee los datos de prueba como bandas). */
const P = (i: number, v: number): [number, number] => [i, v];
const spark = { status: "ok" as const, reason: null, points: [P(0, 1), P(1, 2)], n: 2, ref: 1 };

describe("portada guardada en el navegador (portada rápida)", () => {
  beforeEach(() => localStorage.clear());
  afterEach(() => vi.restoreAllMocks());

  it("guarda solo la vista inicial (1D) y la devuelve igual", () => {
    expect(saveHome(data("2026-10-28T18:05:00Z"), { AAA: { ...spark, stale: true },
      BBB: { status: "sin_dato", reason: "x" } })).toBe(true);
    const c = loadHome()!;
    expect(Object.keys(c.data.lists)).toEqual(["1D"]);
    expect(c.data.lists["1D"].most_traded[0].symbol).toBe("AAA");
    expect(Object.keys(c.sparks)).toEqual(["AAA"]);               // solo las buenas...
    expect(c.sparks.AAA.stale).toBeUndefined();                   // ...y sin la marca de caducada
  });

  it("nunca sustituye a una más reciente", () => {
    expect(saveHome(data("2026-10-28T18:05:00Z"), {})).toBe(true);
    expect(saveHome(data("2026-10-28T17:00:00Z"), {})).toBe(false);
    expect(loadHome()!.data.as_of).toBe("2026-10-28T18:05:00Z");
    expect(saveHome(data("2026-10-28T19:00:00Z"), {})).toBe(true);
    expect(loadHome()!.data.as_of).toBe("2026-10-28T19:00:00Z");
  });

  it("sin la vista inicial no guarda; con algo ilegible o de otra versión, no hay portada guardada", () => {
    const d = data("2026-10-28T18:05:00Z");
    expect(saveHome({ ...d, lists: { "6M": lists("ZZZ") } as unknown as TrendingData["lists"] }, {})).toBe(false);
    localStorage.setItem("finanzer.v2.portada", "{no es json");
    expect(loadHome()).toBeNull();
    localStorage.setItem("finanzer.v2.portada", JSON.stringify({ v: 0, data: d, sparks: {} }));
    expect(loadHome()).toBeNull();
  });

  it("sin almacenamiento (modo privado, cuota llena) no falla", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => { throw new Error("SecurityError"); });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("QuotaExceededError"); });
    expect(loadHome()).toBeNull();
    expect(saveHome(data("2026-10-28T18:05:00Z"), {})).toBe(false);
  });

  it("dice la hora de los datos (Nueva York) y el día si no es hoy", () => {
    const now = new Date("2026-10-28T19:00:00Z");
    expect(cachedLabel("2026-10-28T18:05:00Z", now)).toBe("datos de las 14:05 (Nueva York)");
    expect(cachedLabel("2026-10-27T20:35:00Z", now)).toBe("datos del 27 de octubre a las 16:35 (Nueva York)");
  });
});
