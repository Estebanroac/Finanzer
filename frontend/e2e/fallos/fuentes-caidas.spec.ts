import { test, expect, type Page } from "@playwright/test";
import { symmetryProblems } from "../v2/checks";

/**
 * Verificación de la v4 (V3 · fuentes caídas). Con cada fallo de backend/tests/faults.py activo en el servidor de
 * replay, la portada y las secciones de AAPL cargan sin errores de consola ni respuestas 5xx, con los motivos en su
 * sitio y sin huecos (simetría en verde).
 *
 * Páginas: la portada, /v2/AAPL (abre «La empresa») y, con V2_PAGES=negocio,accion,…, las demás secciones
 * /v2/AAPL/{sección}.
 */
const SYMBOL = "AAPL";
const REPLAY = `http://localhost:${process.env.REPLAY_PORT || 8767}`;
const ALL_FAULTS = ["none", "yahoo_down", "yahoo_401", "edgar_no_ua", "edgar_slow", "finnhub_no_key", "finnhub_429",
  "prices_empty", "sector_etf_down", "spy_down", "logos_down"] as const;
type Fault = (typeof ALL_FAULTS)[number];

const DEPTH = (process.env.V2_PAGES ?? "").split(",").map((x) => x.trim()).filter(Boolean);
const PAGES = ["/v2", `/v2/${SYMBOL}`, ...DEPTH.map((p) => `/v2/${SYMBOL}/${p}`)];
const SERVER_ERROR = 500;

/** Lo que cada fallo debe dejar escrito en las secciones donde se muestra ese dato (E3; V4b: /v2/AAPL es «La empresa»). */
const DEPTH_TEXT: Partial<Record<Fault, Record<string, RegExp>>> = {
  edgar_no_ua: { empresa: /sin User-Agent de la SEC/i, negocio: /sin User-Agent de la SEC/i },
  edgar_slow: { empresa: /EDGAR no respondió a tiempo/, negocio: /EDGAR no respondió a tiempo/ },
  finnhub_no_key: { actualidad: /Noticias: sin clave de Finnhub/ },
  finnhub_429: { actualidad: /Noticias: sin titulares de Finnhub \(no disponibles o sin respuesta\)/ },
  prices_empty: { accion: /Yahoo no devolvió la serie de precios/ },
  spy_down: { accion: /S&P 500 con dividendos: sin la serie con dividendos/ },
};
/** Errores de consola que no son de la página: el indicador de recarga de `next dev`. */
const NOISE = [/webpack-hmr/, /\[HMR\]/, /Download the React DevTools/];

async function setFault(page: Page, fault: Fault) {
  const r = await page.request.post(`${REPLAY}/__replay/fault?name=${fault}`);
  expect(r.ok(), `activar ${fault}`).toBe(true);
  expect((await r.json()).fault).toBe(fault === "none" ? null : fault);
}

/** La página terminó de cargar: la historia con sus capítulos (y la gráfica o su motivo) o su mensaje de error; la
 *  portada con las tendencias (tarjetas o su motivo). */
async function settled(page: Page, path: string) {
  if (path === "/v2") {
    // P8: el cintillo (sus valores, con o sin mini-gráfica) o su motivo.
    await expect(page.locator("[data-testid=ticker-item], .ticker .state").first()).toBeVisible({ timeout: 60_000 });
    await expect(page.locator(".tape.skeleton")).toHaveCount(0, { timeout: 60_000 });
  } else {
    // V4: la pantalla de carga aparece a los 300 ms y sus párrafos también son «main p»: lo que dice que la página está
    // montada (o su error) es <main aria-busy="false">
    await expect(page.locator("main")).toHaveAttribute("aria-busy", "false", { timeout: 90_000 });
    await expect(page.locator(".depth, main p").first()).toBeVisible({ timeout: 60_000 });
    // la gráfica llega después (con la serie caída, Yahoo reintenta): se mide con ella pintada, como en V1
    if (path.endsWith("/accion"))
      await page.waitForSelector("[data-testid=price-chart-full] canvas", { timeout: 30_000 }).catch(() => undefined);
    await page.waitForLoadState("networkidle");
  }
  await page.waitForTimeout(500);
}

// En orden y con un solo worker (playwright.fallos.config.ts): cada prueba activa su fallo antes de cargar la página.
test.afterAll(async ({ request }) => {
  await request.post(`${REPLAY}/__replay/fault?name=none`);
});

for (const fault of ALL_FAULTS) {
  for (const path of PAGES) {
    test(`${fault} · ${path}`, async ({ page }) => {
      const story = path !== "/v2";
      // StoryPageClient pide el análisis con fetchAnalysisV2 (src/v2/lib/analysis.ts): con Yahoo caído enseña el
      // motivo del backend en español (antes, "Failed to analyze AAPL: 404"; era un fallo esperado hasta E3).
      await setFault(page, fault);
      const consoleErrors: string[] = [];
      const pageErrors: string[] = [];
      const server5xx: string[] = [];
      page.on("console", (m) => {
        if (m.type() === "error" && !NOISE.some((n) => n.test(m.text()))) consoleErrors.push(m.text().slice(0, 200));
      });
      page.on("pageerror", (e) => pageErrors.push(String(e).slice(0, 200)));
      page.on("response", (r) => { if (r.status() >= SERVER_ERROR) server5xx.push(`${r.status()} ${r.url()}`); });

      await page.goto(path);
      await settled(page, path);

      expect(server5xx, "respuestas 5xx").toEqual([]);
      expect(pageErrors, "excepciones de la página").toEqual([]);
      // Con Yahoo caído, la petición del análisis responde 404 (la fuente no responde): el navegador lo anota.
      const expected404 = fault === "yahoo_down" && story ? [/status of 404/] : [];
      expect(consoleErrors.filter((t) => !expected404.some((x) => x.test(t))), "errores de consola").toEqual([]);
      expect(await symmetryProblems(page), "simetría").toEqual([]);

      const text = await page.locator("body").innerText();
      if (!story) {
        await expect(page.getByRole("heading", { level: 1 })).toHaveText("Entiende una empresa antes de invertir");
        if (fault === "yahoo_down") expect(text).toMatch(/No hay valores de la sesión ahora mismo\. No se pudieron calcular las tendencias: Yahoo no devolvió/);
        else expect(await page.getByTestId("ticker-item").count()).toBeGreaterThan(0);
        // Logotipos caídos: cada tarjeta con la placa de sus iniciales (nunca un hueco ni una imagen rota)
        if (fault === "logos_down") {
          await expect(page.locator("[data-testid=ticker-item] [data-testid=company-logo]:not([data-state=fail])")).toHaveCount(0);
          await expect(page.locator("[data-testid=ticker-item] [data-testid=company-logo] .co-logo-ph").first()).toHaveText(/^[A-Z0-9]{1,2}$/);
        }
        return;
      }
      if (fault === "yahoo_down") {
        expect(text).toContain("la fuente de datos de mercado no responde");
        return;
      }
      await expect(page.getByTestId("company-name")).toHaveText("Apple Inc.");
      const logo = page.locator(".company-header:not(.compact)").getByTestId("company-logo");
      await expect(logo).toHaveAttribute("data-state", fault === "logos_down" ? "fail" : "ok");
      const section = path.split("/").filter(Boolean)[2] ?? "empresa";
      await expect(page.locator(`.depth[data-chapter=${section}]`)).toHaveCount(1);
      const want = DEPTH_TEXT[fault]?.[section];
      if (want) expect(text).toMatch(want);
      // La gráfica se dibuja siempre que haya algo que dibujar (sin la serie de la empresa, el mercado de referencia).
      if (section === "accion") await expect(page.locator("[data-testid=price-chart-full] canvas").first()).toBeVisible();
    });
  }
}
