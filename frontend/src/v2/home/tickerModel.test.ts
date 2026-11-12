import { describe, it, expect } from "vitest";
import type { TrendingData, TrendingItem } from "@/lib/api";
import { changeLabel, contextLine, engineLine, everyLabel, mergeTrending, sectorChips, selectedItems, shortDate, shownChange } from "./tickerModel";

const it_ = (symbol: string, change = 0.01, engine: TrendingItem["engine"] = null): TrendingItem =>
  ({ symbol, name: symbol, price: 10, change_pct: change, dollar_volume: 1, engine });
const keys = ["Information Technology", "Communication Services", "Consumer Discretionary", "Consumer Staples", "Health Care",
  "Financials", "Energy", "Industrials", "Materials", "Utilities", "Real Estate"];
const P = ["1D", "1S", "1M", "6M"] as const;
const empty = { most_traded: [], gainers: [], losers: [] };
const status = Object.fromEntries(keys.map((k) => [k, { label: k === "Energy" ? "Energía" : k, count: 7, available: k !== "Utilities", reason: k === "Utilities" ? "solo 4 valores" : null }]));
const data: TrendingData = {
  session: "2026-10-16", as_of: "2026-10-16T20:35:00Z", universe_date: "2026-10-17", count: 3, failed_batches: 0, note: null,
  periods: {
    "1D": { label: "1 día", sessions: 1, from: "2026-10-15", to: "2026-10-16", count: 3 },
    "1S": { label: "1 semana", sessions: 5, from: "2026-10-09", to: "2026-10-16", count: 3 },
    "1M": { label: "1 mes", sessions: 21, from: "2026-09-17", to: "2026-10-16", count: 3 },
    "6M": { label: "6 meses", sessions: 126, from: "2026-04-16", to: "2026-10-16", count: 3 },
  },
  lists: { "1D": { most_traded: [it_("MU"), it_("NVDA")], gainers: [it_("A")], losers: [it_("B", -0.02)] }, "1S": empty, "1M": empty,
    "6M": { most_traded: [it_("NVDA")], gainers: [it_("C", 0.4)], losers: [it_("COHR", -0.32)] } },
  list_notes: { "1D": { gainers: null, losers: null }, "1S": { gainers: null, losers: null }, "1M": { gainers: null, losers: null },
    "6M": { gainers: null, losers: "solo 1 valor del universo baja en 6 meses" } },
  sectors: Object.fromEntries(P.map((p) => [p, Object.fromEntries(keys.map((k) => [k, k === "Energy" ? [it_(p === "1D" ? "XOM" : "CVX")] : []]))])) as TrendingData["sectors"],
  sector_status: Object.fromEntries(P.map((p) => [p, status])) as TrendingData["sector_status"],
};

describe("cintillo (P8)", () => {
  it("una lista o un sector, en el periodo elegido; ocho sectores con chip y el resto en «Más»", () => {
    expect(selectedItems(data, { kind: "list", key: "most_traded" }, "1D").map((x) => x.symbol)).toEqual(["MU", "NVDA"]);
    expect(selectedItems(data, { kind: "list", key: "losers" }, "6M").map((x) => x.symbol)).toEqual(["COHR"]);
    expect(selectedItems(data, { kind: "sector", key: "Energy" }, "1D").map((x) => x.symbol)).toEqual(["XOM"]);
    expect(selectedItems(data, { kind: "sector", key: "Energy" }, "6M").map((x) => x.symbol)).toEqual(["CVX"]);
    const { primary, more } = sectorChips(data, "6M");
    expect(primary).toHaveLength(8);
    expect(more.map((x) => x.key)).toEqual(["Materials", "Utilities", "Real Estate"]);
    expect(more[1]).toMatchObject({ available: false, reason: "solo 4 valores" });
  });
  it("línea de contexto: la lista en el periodo, entre qué sesiones, el universo y cuántos; si la lista es corta, por qué", () => {
    expect(contextLine(data, { kind: "list", key: "losers" }, "6M", 1)).toBe(
      "Bajan más en 6 meses (del 16-abr-2026 al 16-oct-2026) · al cierre del 16-oct-2026 · universo: S&P 500 y ADR principales · 1 valor · " +
      "solo 1 valor del universo baja en 6 meses");
    expect(contextLine(data, { kind: "list", key: "most_traded" }, "1D", 30, 120)).toBe(
      "Más negociadas en 1 día (del 15-oct-2026 al 16-oct-2026) · al cierre del 16-oct-2026; con la bolsa de Nueva York " +
      "abierta se rehace cada 2 min · universo: S&P 500 y ADR principales · 30 valores");
    expect(contextLine(data, { kind: "sector", key: "Energy" }, "1M", 2)).toBe(
      "Energía, las más negociadas del sector, en 1 mes (del 17-sep-2026 al 16-oct-2026) · al cierre del 16-oct-2026 · " +
      "universo: S&P 500 y ADR principales · 2 valores");
    expect(shortDate("2026-01-05")).toBe("5-ene-2026");
  });
  it("cintillo en vivo: dice que es de hoy, a qué hora se actualizó y cada cuánto se rehace", () => {
    const live: TrendingData = { ...data, session: "2026-10-19", live: { session: "2026-10-19", at: "2026-10-19T15:02:00Z", refresh_s: 120 },
      periods: { ...data.periods, "1D": { ...data.periods["1D"], from: "2026-10-16", to: "2026-10-19" },
        "1S": { ...data.periods["1S"], from: "2026-10-12", to: "2026-10-19" } } };
    const clock = () => "11:02";
    expect(contextLine(live, { kind: "list", key: "gainers" }, "1D", 30, 120, clock)).toBe(
      "Suben más hoy, 19-oct-2026 (frente al cierre del 16-oct-2026) · en vivo: actualizado a las 11:02, se rehace cada 2 min " +
      "con la bolsa de Nueva York abierta · universo: S&P 500 y ADR principales · 30 valores");
    expect(contextLine(live, { kind: "list", key: "most_traded" }, "1S", 30, 120, clock)).toBe(
      "Más negociadas en 1 semana (del 12-oct-2026 a hoy, 19-oct-2026) · en vivo: actualizado a las 11:02, se rehace cada 2 min " +
      "con la bolsa de Nueva York abierta · universo: S&P 500 y ADR principales · 30 valores");
    expect(everyLabel(45)).toBe("cada 45 s");
  });
  it("variación con flecha; la de la tarjeta es la de su lista (la que la ordena)", () => {
    expect(changeLabel(0.0043)).toMatchObject({ arrow: "▲", text: "0.43%" });
    expect(changeLabel(-0.0563)).toMatchObject({ arrow: "▼", text: "5.63%" });
    expect(changeLabel(0)).toMatchObject({ arrow: "", text: "0.00%" });
    expect(shownChange(it_("COHR", -0.32))).toEqual({ value: -0.32, reason: null });
  });
  it("calidad y precio solo si el motor ya los tiene", () => {
    expect(engineLine(it_("A"))).toBeNull();
    expect(engineLine(it_("A", 0, { status: "en_cola", quality: null, price_score: null, reason: null }))).toBeNull();
    expect(engineLine(it_("A", 0, { status: "listo", quality: { score: 75.4, level: "sólida" }, price_score: { score: 15, level: "exigente" }, reason: null })))
      .toEqual({ quality: 75, price: 15 });
  });
});

describe("V6b (E11): la portada pide solo el periodo que enseña", () => {
  const base = (lists: Record<string, unknown>) => ({ session: "2026-10-16", as_of: "x", periods: {}, lists, list_notes: {},
    universe_date: null, count: 1, failed_batches: 0, note: null }) as unknown as TrendingData;
  it("lo de otros periodos se conserva y lo del nuevo se añade; lo demás es lo último", () => {
    const a = base({ "1D": { most_traded: [{ symbol: "AAPL" }] } });
    const b = { ...base({ "6M": { most_traded: [{ symbol: "MSFT" }] } }), count: 2 };
    const m = mergeTrending(a, b);
    expect(Object.keys(m.lists).sort()).toEqual(["1D", "6M"]);
    expect(m.count).toBe(2);
  });
  it("con otra sesión, solo lo nuevo (las listas de ayer no valen)", () => {
    const a = base({ "1D": { most_traded: [] } });
    const b = { ...base({ "6M": { most_traded: [] } }), session: "2026-10-17" };
    expect(Object.keys(mergeTrending(a, b).lists)).toEqual(["6M"]);
  });
});
