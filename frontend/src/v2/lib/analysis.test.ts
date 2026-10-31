import { afterEach, describe, expect, it, vi } from "vitest";
import { analysisErrorText, fetchAnalysisV2, timeoutText } from "./analysis";
import { WEB } from "@/lib/generated/backendConfig";

afterEach(() => vi.unstubAllGlobals());
const json = (status: number, body: unknown) => vi.fn(async () => new Response(JSON.stringify(body), { status }));
const UNAVAILABLE = "No se pudieron obtener los datos de AAPL: la fuente de datos de mercado no responde ahora mismo. " +
  "Vuelve a intentarlo en unos minutos.";

describe("análisis de /v2 con el motivo del backend", () => {
  it("fuente caída: el motivo del backend tal cual", async () => {
    vi.stubGlobal("fetch", json(404, { detail: UNAVAILABLE }));
    await expect(fetchAnalysisV2("AAPL")).rejects.toThrow(UNAVAILABLE);
  });

  it("ETF (422): el motivo del backend", async () => {
    vi.stubGlobal("fetch", json(422, { detail: "SPY es un ETF: Finanzer analiza acciones." }));
    await expect(fetchAnalysisV2("SPY")).rejects.toThrow("SPY es un ETF");
  });

  it("símbolo inexistente y errores del servidor: en español", () => {
    expect(analysisErrorText("ZZZZZ", 404, "No data found for ZZZZZ")).toBe("No hay datos de ZZZZZ: comprueba el ticker (por ejemplo, AAPL o BRK-B).");
    expect(analysisErrorText("AAPL", 503, "x")).toBe("No se pudo analizar AAPL ahora mismo. Vuelve a intentarlo en unos minutos.");
  });

  it("sin red: lo dice", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new TypeError("Failed to fetch"); }));
    await expect(fetchAnalysisV2("AAPL")).rejects.toThrow("No se pudo contactar con el servidor");
  });

  // V4 (PM): un backend que no responde ya no deja la página en «Analizando…» para siempre
  const hanging = () => vi.fn((_url: string, init?: RequestInit) => new Promise<Response>((_, reject) => {
    init?.signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")));
  }));
  it("sin respuesta dentro del presupuesto de espera: «tarda más de lo normal»", async () => {
    vi.stubGlobal("fetch", hanging());
    await expect(fetchAnalysisV2("AAPL", undefined, 20)).rejects.toThrow(timeoutText("AAPL"));
    expect(timeoutText("AAPL")).toContain("tardando más de lo normal");
    expect(WEB.analysisTimeoutMs).toBeGreaterThan(0);                 // de la config (data.toml [web])
  });

  it("cancelar no es un error de tiempo: sigue siendo AbortError", async () => {
    vi.stubGlobal("fetch", hanging());
    const ac = new AbortController();
    const p = fetchAnalysisV2("AAPL", ac.signal, 10_000);
    ac.abort();
    await expect(p).rejects.toMatchObject({ name: "AbortError" });
  });

  it("con análisis: lo devuelve", async () => {
    vi.stubGlobal("fetch", json(200, { symbol: "AAPL" }));
    await expect(fetchAnalysisV2("AAPL")).resolves.toEqual({ symbol: "AAPL" });
  });
});
