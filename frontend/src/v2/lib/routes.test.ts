import { describe, expect, it } from "vitest";
import { CHAPTER_SLUGS, chapterHref, parseV2Path } from "./routes";

describe("rutas de /v2", () => {
  it("historia y profundidad", () => {
    expect(parseV2Path("/v2/aapl/")).toEqual({ symbol: "AAPL", chapter: null, invalid: false });
    expect(parseV2Path("/v2/AAPL/calidad")).toEqual({ symbol: "AAPL", chapter: "calidad", invalid: false });
    expect(parseV2Path("/v2/BRK-B/Valor")).toEqual({ symbol: "BRK-B", chapter: "valor", invalid: false });
    expect(parseV2Path("/v2/MC.PA/rivales/")).toEqual({ symbol: "MC.PA", chapter: "rivales", invalid: false });
  });
  it("un capítulo desconocido muestra la historia; sin símbolo, nada", () => {
    expect(parseV2Path("/v2/AAPL/inventado")).toEqual({ symbol: "AAPL", chapter: null, invalid: false });
    expect(parseV2Path("/v2/")).toEqual({ symbol: null, chapter: null, invalid: false });
  });
  it("revisión V6 (F6): una ruta mal codificada no lanza y un símbolo que no es un ticker no se pide", () => {
    expect(() => parseV2Path("/v2/%E0%A4%A")).not.toThrow();
    expect(parseV2Path("/v2/%E0%A4%A")).toEqual({ symbol: null, chapter: null, invalid: true });
    expect(parseV2Path("/v2/AAPL/%E0%A4%A")).toEqual({ symbol: "AAPL", chapter: null, invalid: false });
    for (const bad of ["/v2/%3Cscript%3E", "/v2/..%2F..%2Fapi", "/v2/AAAAAAAAAAAA", "/v2/A%20B", "/v2/1234"]) {
      expect(parseV2Path(bad).invalid).toBe(true);
    }
  });
  it("enlaces con y sin ancla", () => {
    expect(chapterHref("AAPL")).toBe("/v2/AAPL");
    expect(chapterHref("AAPL", "calidad")).toBe("/v2/AAPL/calidad");
    expect(chapterHref("AAPL", "calidad", "piotroski")).toBe("/v2/AAPL/calidad#piotroski");
    expect(CHAPTER_SLUGS).toHaveLength(9);
  });
});
