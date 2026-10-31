import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

/**
 * Verificación de la v4 (V2 · fuentes reales): para cada ticker de FR_SYMBOLS, la historia (/v2/{T}) y las 9 páginas
 * de profundidad contra un backend real ya en marcha (FR_BASE, p. ej. tools/load_server.py en 8771, con la web
 * compilada y las claves en su entorno). Sin errores de consola ni de página y sin respuestas 5xx; un 4xx se anota
 * (ZZZZZ, SPY: el análisis dice por qué) pero no es un fallo. Resultado por página en test-results/fuentes-reales/.
 *   FR_BASE=http://127.0.0.1:8771 FR_SYMBOLS=AAPL,JPM npx playwright test -c playwright.fuentes.config.ts
 */
const SYMBOLS = (process.env.FR_SYMBOLS ?? "AAPL").split(",").map((x) => x.trim()).filter(Boolean);
const CHAPTERS = ["", "empresa", "negocio", "accion", "calidad", "valor", "rivales", "riesgos", "actualidad", "conclusion"];
const OUT = path.join(__dirname, "..", "..", "test-results", "fuentes-reales");

for (const sym of SYMBOLS) {
  test(`páginas sin errores · ${sym}`, async ({ page }) => {
    const rows: Array<Record<string, unknown>> = [];
    for (const ch of CHAPTERS) {
      const url = `/v2/${sym}${ch ? `/${ch}` : ""}`;
      const errors: string[] = [];
      const server5xx: string[] = [];
      const client4xx: string[] = [];
      const onConsole = (m: import("@playwright/test").ConsoleMessage) => {
        if (m.type() === "error" && !/Failed to load resource: the server responded with a status of 4\d\d/.test(m.text()))
          errors.push(m.text().slice(0, 300));
      };
      const onPageError = (e: Error) => errors.push(`pageerror: ${e.message.slice(0, 300)}`);
      const onResponse = (r: import("@playwright/test").Response) => {
        if (r.status() >= 500) server5xx.push(`${r.status()} ${r.url()}`);
        else if (r.status() >= 400) client4xx.push(`${r.status()} ${new URL(r.url()).pathname}`);
      };
      page.on("console", onConsole);
      page.on("pageerror", onPageError);
      page.on("response", onResponse);
      const t0 = Date.now();
      const res = await page.goto(url);
      await page.waitForLoadState("networkidle", { timeout: 120_000 }).catch(() => errors.push("networkidle: tiempo agotado"));
      await page.waitForTimeout(500);
      const text = (await page.locator("body").innerText()).replace(/\s+/g, " ");
      rows.push({ url, status: res?.status(), ms: Date.now() - t0, errors, server5xx, client4xx: [...new Set(client4xx)],
                  undefined_or_nan: /\bundefined\b|\bNaN\b|\[object Object\]/.test(text), text: text.slice(0, 400) });
      page.off("console", onConsole);
      page.off("pageerror", onPageError);
      page.off("response", onResponse);
    }
    fs.mkdirSync(OUT, { recursive: true });
    fs.writeFileSync(path.join(OUT, `${sym}.json`), JSON.stringify(rows, null, 1));
    const bad = rows.filter((r) => (r.errors as string[]).length || (r.server5xx as string[]).length || r.undefined_or_nan);
    expect(bad.map((r) => ({ url: r.url, errors: r.errors, server5xx: r.server5xx, raro: r.undefined_or_nan }))).toEqual([]);
  });
}
