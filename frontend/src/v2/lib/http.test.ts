import { afterEach, describe, expect, it, vi } from "vitest";
import { cachedJSON, clearHttpCache, HttpError, httpErrorText, isAbort, NETWORK_TEXT, requestJSON } from "./http";

// Revisión V6: F12 (caché en el módulo con TTL y cancelación por consumidor) y F18 (errores en español).
afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers(); clearHttpCache(); });

function stub(responses: Array<() => Response | Promise<Response>>) {
  let i = 0;
  const fn = vi.fn(async () => responses[Math.min(i++, responses.length - 1)]());
  vi.stubGlobal("fetch", fn);
  return fn;
}
const json = (body: unknown, status = 200) => () => new Response(JSON.stringify(body), { status });

describe("errores en español", () => {
  it("nunca «Failed to fetch» ni «HTTP 500» a la vista", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new TypeError("Failed to fetch"); }));
    await expect(requestJSON("/x", "los datos")).rejects.toThrow(NETWORK_TEXT);
    stub([json({ detail: "Internal Server Error" }, 500)]);
    const e = (await requestJSON("/x", "los datos").catch((x) => x)) as HttpError;
    expect(e).toBeInstanceOf(HttpError);
    expect(e.status).toBe(500);
    expect(e.message).not.toMatch(/HTTP|500|Internal|Failed/);
  });
  it("un 4xx enseña el motivo del backend; 404 y 429, un texto propio", () => {
    expect(httpErrorText("el escenario", 422, "la tasa de descuento debe ser mayor que el crecimiento")).toBe("la tasa de descuento debe ser mayor que el crecimiento");
    expect(httpErrorText("los rivales de X", 404, null)).toBe("No se encontraron los rivales de X.");
    expect(httpErrorText("los precios", 429, null)).toMatch(/^Demasiadas peticiones/);
  });
});

describe("caché del módulo", () => {
  it("la misma ruta dentro del TTL se pide una vez (también en vuelo)", async () => {
    const fn = stub([json({ n: 1 })]);
    const [a, b] = await Promise.all([cachedJSON("/p", "x", 1000), cachedJSON("/p", "x", 1000)]);
    await cachedJSON("/p", "x", 1000);
    expect(fn).toHaveBeenCalledTimes(1);
    expect(a).toEqual(b);
  });
  it("pasado el TTL vuelve a pedir", async () => {
    vi.useFakeTimers();
    const fn = stub([json({ n: 1 }), json({ n: 2 })]);
    await cachedJSON("/p", "x", 1000);
    vi.advanceTimersByTime(1001);
    expect(await cachedJSON("/p", "x", 1000)).toEqual({ n: 2 });
    expect(fn).toHaveBeenCalledTimes(2);
  });
  it("los fallos y lo que `keep` rechaza no se guardan", async () => {
    const fn = stub([json({}, 503), json({ status: "calculando" }), json({ status: "listo" })]);
    await expect(cachedJSON("/p", "x", 1000)).rejects.toBeInstanceOf(HttpError);
    const keep = (r: { status: string }) => r.status !== "calculando";
    expect(await cachedJSON("/p", "x", 1000, { keep })).toEqual({ status: "calculando" });
    await Promise.resolve();
    expect(await cachedJSON("/p", "x", 1000, { keep })).toEqual({ status: "listo" });
    expect(fn).toHaveBeenCalledTimes(3);
  });
  it("cancelar a un consumidor no corta la petición de los demás", async () => {
    let release: (r: Response) => void = () => {};
    stub([() => new Promise<Response>((r) => { release = r; })]);
    const ac = new AbortController();
    const mine = cachedJSON("/p", "x", 1000, { signal: ac.signal });
    const other = cachedJSON("/p", "x", 1000);
    ac.abort();
    await expect(mine).rejects.toSatisfy(isAbort);
    release(new Response(JSON.stringify({ ok: true })));
    expect(await other).toEqual({ ok: true });
  });
});
