import { beforeEach, describe, expect, it, vi } from "vitest";
import type { StockAnalysis } from "@/lib/api";
import { ANALYSIS_TTL_MS, MAX_CACHED, readCached, writeCached } from "./analysisCache";

// Revisión V6 (F14): sessionStorage con tope, versión y purga de lo caducado.
const a = (s: string) => ({ symbol: s }) as unknown as StockAnalysis;
const ours = () => Object.keys(sessionStorage).filter((k) => k.startsWith("finanzer.v2.analysis."));

describe("caché del análisis en la sesión", () => {
  beforeEach(() => sessionStorage.clear());

  it("lee lo fresco y no lo caducado", () => {
    writeCached("AAPL", a("AAPL"), 1000);
    expect(readCached("AAPL", 1000 + ANALYSIS_TTL_MS - 1)).toEqual(a("AAPL"));
    expect(readCached("AAPL", 1000 + ANALYSIS_TTL_MS)).toBeNull();
  });
  it(`como mucho ${MAX_CACHED} empresas: sale la más antigua`, () => {
    const syms = ["A", "B", "C", "D", "E", "F", "G"];
    syms.forEach((s, i) => writeCached(s, a(s), 1000 + i));
    expect(ours()).toHaveLength(MAX_CACHED);
    expect(readCached("A", 2000)).toBeNull();
    expect(readCached("G", 2000)).toEqual(a("G"));
  });
  it("purga lo caducado y lo de otra versión al escribir; lo de otra versión no se lee", () => {
    sessionStorage.setItem("finanzer.v2.analysis.OLD", JSON.stringify({ t: 1000, data: a("OLD") }));   // sin versión (E3)
    writeCached("X", a("X"), 1000);
    expect(readCached("OLD", 1000)).toBeNull();
    writeCached("Y", a("Y"), 1000 + ANALYSIS_TTL_MS + 1);
    expect(ours()).toEqual(["finanzer.v2.analysis.Y"]);
  });
  it("almacenamiento lleno: vacía lo suyo y lo intenta una vez más; bloqueado: no lanza", () => {
    writeCached("X", a("X"), 1000);
    const real = Storage.prototype.setItem;
    let calls = 0;
    const spy = vi.spyOn(Storage.prototype, "setItem").mockImplementation(function (this: Storage, k: string, v: string) {
      if (calls++ === 0) throw new DOMException("lleno", "QuotaExceededError");
      return real.call(this, k, v);
    });
    writeCached("Y", a("Y"), 1001);
    expect(readCached("Y", 1001)).toEqual(a("Y"));
    spy.mockImplementation(() => { throw new Error("bloqueado"); });
    expect(() => writeCached("Z", a("Z"), 1002)).not.toThrow();
    spy.mockRestore();
  });
});
