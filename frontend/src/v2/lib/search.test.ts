import { afterEach, describe, expect, it, vi } from "vitest";
import { enterTarget, moveActive, searchV2, stockHref } from "./search";

const HITS = [
  { ticker: "AAPL", name: "Apple Inc.", exchange: "Nasdaq" },
  { ticker: "APLE", name: "Apple Hospitality REIT, Inc.", exchange: "NYSE" },
];
const NONE = -1;

afterEach(() => vi.unstubAllGlobals());

describe("buscador de /v2", () => {
  it("pide /api/v2/search con la consulta codificada y devuelve los resultados", async () => {
    const fn = vi.fn(async () => new Response(JSON.stringify({ results: HITS }), { status: 200 }));
    vi.stubGlobal("fetch", fn);
    expect(await searchV2("coca cola")).toEqual(HITS);
    const u = new URL(String((fn.mock.calls[0] as unknown[])[0]), "http://base.invalid");
    expect(u.pathname + u.search).toBe("/api/v2/search?q=coca%20cola");
  });

  it("un error del servidor es una lista vacía", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("x", { status: 500 })));
    expect(await searchV2("apple")).toEqual([]);
  });

  it("Enter: opción marcada, ticker exacto o lo que parece un ticker", () => {
    expect(enterTarget("apple", HITS, 1)).toBe("APLE");
    expect(enterTarget("aapl", HITS, NONE)).toBe("AAPL");
    expect(enterTarget("apple", HITS, NONE)).toBe(HITS[0].ticker);  // V7 · P6: nombre sin elegir → el primer resultado
    expect(enterTarget("brk.b", [], NONE)).toBe("BRK.B");
    expect(enterTarget("coca cola", [], NONE)).toBeNull();
  });

  it("↑ ↓ recorren las opciones y vuelven al texto", () => {
    expect(moveActive(NONE, HITS.length, 1)).toBe(0);
    expect(moveActive(0, HITS.length, 1)).toBe(1);
    expect(moveActive(1, HITS.length, 1)).toBe(NONE);
    expect(moveActive(NONE, HITS.length, -1)).toBe(1);
    expect(moveActive(0, HITS.length, -1)).toBe(NONE);
    expect(moveActive(NONE, 0, 1)).toBe(NONE);
  });

  it("la página de una empresa", () => {
    expect(stockHref("brk.b")).toBe("/v2/BRK.B");
  });
});
