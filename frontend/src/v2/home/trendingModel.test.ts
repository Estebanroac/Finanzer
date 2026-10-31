import { describe, expect, it } from "vitest";
import type { TrendingData, TrendingEngine, TrendingResponse } from "@/lib/api";
import { cardAction, changeText, engineView, footerText, listTitle, priceText, shouldPoll } from "./trendingModel";

const READY: TrendingEngine = { status: "listo", quality: { score: 79, level: "sólida" }, price_score: { score: 10, level: "muy exigente" }, reason: null };
const item = (engine: TrendingEngine | null) => ({ symbol: "AAPL", name: "Apple", price: 1, change_pct: 0, dollar_volume: 1, engine });

function data(engine: TrendingEngine | null): TrendingData {
  return { session: "2026-10-16", as_of: "2026-10-16T20:35:00Z", universe_date: "2026-10-17", count: 500, failed_batches: 0,
    note: null, periods: {} as TrendingData["periods"], list_notes: {} as TrendingData["list_notes"],
    lists: { "1D": { most_traded: [], gainers: [], losers: [] }, "1S": { most_traded: [], gainers: [], losers: [] },
      "1M": { most_traded: [], gainers: [], losers: [] }, "6M": { most_traded: [item(engine)], gainers: [], losers: [] } } };
}
const resp = (over: Partial<TrendingResponse>): TrendingResponse =>
  ({ status: "listo", data: data(READY), refreshing: false, reason: null, poll_s: 5, ...over });

describe("tendencias de la portada", () => {
  it("las listas se titulan por lo que miden; «hoy» solo con la sesión de hoy", () => {
    const friday = new Date("2026-10-16T21:00:00Z");
    const sunday = new Date("2026-10-18T15:00:00Z");
    expect(listTitle("most_traded", "2026-10-16", friday)).toBe("Más negociadas hoy");
    expect(listTitle("gainers", "2026-10-16", sunday)).toBe("Mayores subidas");
    expect(listTitle("losers", "2026-10-16", friday)).toBe("Mayores caídas hoy");
  });

  it("pie con fecha y hora de Nueva York y la fecha del universo", () => {
    expect(footerText(data(READY))).toBe("Sesión del 16 de octubre de 2026 · Actualizado el 16 de octubre de 2026 a las " +
      "16:35 (Nueva York) · universo: S&P 500 y ADR principales (17 de octubre de 2026)");
  });

  it("precio y variación", () => {
    expect(priceText(1234.5)).toBe("$1,234.50");
    expect(changeText(0.01234)).toBe("+1.23%");
    expect(changeText(-0.2)).toBe("−20.00%");
    expect(changeText(0)).toBe("0.00%");
  });

  it("vuelve a preguntar mientras calcula, refresca o el motor analiza alguna tarjeta", () => {
    expect(shouldPoll(null)).toBe(true);
    expect(shouldPoll(resp({ status: "calculando", data: null }))).toBe(true);
    expect(shouldPoll(resp({ refreshing: true }))).toBe(true);
    expect(shouldPoll(resp({}))).toBe(false);
    expect(shouldPoll(resp({ data: data({ status: "en_cola", quality: null, price_score: null, reason: null }) }))).toBe(true);
    expect(shouldPoll(resp({ data: data(null) }))).toBe(false);
    expect(shouldPoll(resp({ status: "sin_dato", data: null, reason: "x" }))).toBe(false);
  });

  it("el motor de la tarjeta: puntuaciones, esqueleto o «sin dato» con el motivo", () => {
    const fail = (reason: string): TrendingEngine => ({ status: "fallo", quality: null, price_score: null, reason });
    expect(engineView(READY)).toMatchObject({ kind: "ready", status: "Analizada por Finanzer" });
    expect(engineView({ status: "analizando", quality: null, price_score: null, reason: null }))
      .toEqual({ kind: "pending", status: "Analizando…" });
    expect(engineView(null)).toEqual({ kind: "missing", status: "Sin análisis por ahora" });
    expect(engineView(fail("TSLA: sin fixtures en el replay")))
      .toEqual({ kind: "missing", status: "Sin fixtures en el replay" });
    expect(engineView(fail("No incluido en la demo con datos grabados; con datos reales se analiza al momento")))
      .toEqual({ kind: "missing", status: "No incluido en la demo" });
    expect(engineView(fail("Failed to analyze XYZ: 500"))).toEqual({ kind: "missing", status: "Finanzer no pudo analizarla" });
    expect(cardAction(engineView(READY))).toBe("Ver el análisis →");
    expect(cardAction(engineView(null))).toBe("Abrir el análisis →");
  });
});
