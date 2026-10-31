import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchPeers, fetchSegments, fetchTrending } from "./companyData";
import { clearHttpCache } from "./http";

function stubFetch(status = 200, body: unknown = { status: "ok" }) {
  const fn = vi.fn<(url: string) => Promise<Response>>(async () => new Response(JSON.stringify(body), { status }));
  vi.stubGlobal("fetch", fn);
  return fn;
}

afterEach(() => { vi.unstubAllGlobals(); clearHttpCache(); });

describe("clientes de los datos de E2b", () => {
  it("piden las rutas /api/v2 con el símbolo codificado", async () => {
    const fn = stubFetch();
    await fetchSegments("BRK.B");
    await fetchPeers("AAPL");
    await fetchPeers("AAPL", ["MSFT", "DELL"]);
    await fetchTrending("6M");
    // Sin la base (depende del puerto del entorno de pruebas): ruta y consulta.
    const paths = fn.mock.calls.map((c) => {
      const u = new URL(String(c[0]), "http://base.invalid");
      return u.pathname + u.search;
    });
    expect(paths).toEqual([
      "/api/v2/segments/BRK.B",
      "/api/v2/peers/AAPL",
      "/api/v2/peers/AAPL?symbols=MSFT%2CDELL",
      "/api/v2/trending?period=6M",
    ]);
  });

  it("un error HTTP es una excepción con el motivo del backend, en español (revisión V6, F18)", async () => {
    stubFetch(422, { detail: "lista de rivales no válida" });
    await expect(fetchPeers("AAPL", ["A;B"])).rejects.toThrow("lista de rivales no válida");
    stubFetch(502, {});
    await expect(fetchSegments("AAPL")).rejects.toThrow("No se pudieron cargar los segmentos de AAPL ahora mismo");
  });
});
