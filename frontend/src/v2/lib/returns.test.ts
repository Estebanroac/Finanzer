import { describe, it, expect } from "vitest";
import { chartPoints, returnOf, sessionsOf, windowOf } from "./returns";
import { marksOf } from "./chartEvents";
import type { PricesPayload, SeriesPayload } from "./prices";

// Revisión V6 (F1): el backend manda la base 100 (por serie, desde su índice i0), las rentabilidades y las marcas; el
// cliente solo las coloca en su sesión.
// Listas de números como texto: el guardián de literales prohíbe arrays de números en /v2.
const nums = (t: string) => t.split(" ").map(Number);
const day = (i: number) => new Date(Date.UTC(2026, 0, 5 + i)).toISOString().slice(0, 10);
const serie = (n: number): SeriesPayload => ({ symbol: "X", status: "ok", events: [],
  points: Array.from({ length: n }, (_, i) => ({ t: day(i), c: i, a: i, v: null })) });
const ret = { price: 0.1, total: 0.12, price_txt: "+10.0%", total_txt: "+12.0%", price_tone: "pos", tone: "pos" };
const data: PricesPayload = {
  symbol: "X", as_of: day(9),
  company: { ...serie(10), returns: { "1S": ret } }, market: serie(8),
  sector: { symbol: null, status: "sin_dato", points: [], events: [] },
  ranges: [{ key: "1S", label: "1 semana" }, { key: "1M", label: "1 mes" }],
  chart: {
    "1S": { status: "ok", reason: null, covered: true, start: day(6), end: day(9),
      series: { company: { i0: 6, values: nums("100 101 102.5 103") }, market: { i0: 4, values: nums("100 99") } },
      marks: [{ t: day(7), kind: "dividend", label: "Dividendo" }] },
    "1M": { status: "sin_dato", reason: "la serie no cubre el periodo", covered: false, start: null, end: null, series: {}, marks: [] },
  },
};

describe("returns (solo pinta)", () => {
  it("la base 100 de cada serie va en la fecha de su sesión (cada una con su calendario)", () => {
    expect(chartPoints(data, "company", "1S").map((p) => `${p.time}=${p.value}`).join(" "))
      .toBe(`${day(6)}=100 ${day(7)}=101 ${day(8)}=102.5 ${day(9)}=103`);
    expect(chartPoints(data, "market", "1S").map((p) => p.time).join(" ")).toBe(`${day(4)} ${day(5)}`);
    expect(sessionsOf(data, "company", "1S").has(day(5))).toBe(false);
  });
  it("sin ventana, sin serie o sin periodo: nada que pintar", () => {
    expect(chartPoints(data, "company", "1M")).toEqual([]);
    expect(chartPoints(data, "sector", "1S")).toEqual([]);
    expect(windowOf(data, "5A")).toBeNull();
    expect(chartPoints({ ...data, chart: undefined }, "company", "1S")).toEqual([]);
  });
  it("la rentabilidad, tal cual la manda el backend; sin dato, «—»", () => {
    expect(returnOf(data, "company", "1S").total_txt).toBe("+12.0%");
    expect(returnOf(data, "market", "1S").total_txt).toBe("—");
    expect(returnOf(data, "company", "3A").price).toBeNull();
  });
  it("las marcas del periodo, las del backend", () => {
    expect(marksOf(data, "1S").map((m) => `${m.kind}@${m.t}`).join(" ")).toBe(`dividend@${day(7)}`);
    expect(marksOf(data, "1M")).toEqual([]);
  });
  it("un índice fuera de la serie no pinta puntos sueltos", () => {
    const bad = { ...data, chart: { "1S": { ...data.chart!["1S"], series: { company: { i0: 8, values: nums("100 101 102") } } } } };
    expect(chartPoints(bad, "company", "1S").length).toBe(2);
  });
});
