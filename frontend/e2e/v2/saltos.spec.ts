import { test, expect } from "@playwright/test";

// Cierre de la v4 (Lighthouse, /v2/AAPL en escritorio: CLS 0,104): mientras llega el fragmento de la sección, el paso a
// la siguiente («Siguiente sección») quedaba a la vista bajo «Cargando la sección…» y el contenido lo empujaba fuera.
// Al cargar una sección, la suma de los saltos de maquetación queda muy por debajo del umbral de «bueno» (0,1).
// La API de layout-shift solo existe en Chromium (escritorio y móvil).
const MAX_CLS = 0.02;

for (const path of ["/v2/AAPL", "/v2/AAPL/valor", "/v2/JPM/calidad", "/v2/AAPL/conclusion"]) {
  test(`sin saltos al cargar ${path}`, async ({ page, browserName }) => {
    test.skip(browserName !== "chromium", "layout-shift solo en Chromium");
    await page.addInitScript(() => {
      (window as unknown as { __cls: number }).__cls = 0;
      new PerformanceObserver((l) => {
        for (const e of l.getEntries() as Array<PerformanceEntry & { value: number; hadRecentInput: boolean }>)
          if (!e.hadRecentInput) (window as unknown as { __cls: number }).__cls += e.value;
      }).observe({ type: "layout-shift", buffered: true });
    });
    await page.goto(path);
    await page.waitForSelector(".depth-body .dsec", { timeout: 30_000 });
    await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => undefined);
    await page.waitForTimeout(500);
    expect(await page.evaluate(() => (window as unknown as { __cls: number }).__cls)).toBeLessThan(MAX_CLS);
  });
}
