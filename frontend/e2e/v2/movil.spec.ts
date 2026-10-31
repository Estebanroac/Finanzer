import { test, expect } from "@playwright/test";

// E4 Task 3: móvil al mismo nivel. Zoom en iPhone (petición del usuario): la meta viewport no limita la escala y
// ningún elemento impide pellizcar (touch-action sin pinch-zoom); controles táctiles de ≥ 44 px; la cabecera compacta
// enseña el desglose de las puntuaciones a la vista (V4b); la barra de secciones deja la activa a la vista.
const PAGES = ["/v2/AAPL", "/v2/AAPL/accion", "/v2/AAPL/valor", "/v2/JPM/calidad"];
const touchy = (name: string) => name !== "desktop";

for (const url of PAGES) {
  test(`el zoom con los dedos no se bloquea · ${url}`, async ({ page }, info) => {
    test.skip(!touchy(info.project.name), "pantallas táctiles");
    await page.goto(url);
    await page.waitForSelector(".depth-body .dsec", { timeout: 30_000 });
    await page.waitForTimeout(800);
    const r = await page.evaluate(() => ({
      meta: document.querySelector('meta[name="viewport"]')?.getAttribute("content") ?? "",
      blocked: [...document.querySelectorAll("*")].map((e) => getComputedStyle(e).touchAction)
        .filter((t) => t && t !== "auto" && t !== "manipulation" && !t.includes("pinch-zoom")),
    }));
    expect(r.meta).not.toMatch(/maximum-scale|user-scalable\s*=\s*no|minimum-scale/);
    expect([...new Set(r.blocked)]).toEqual([]);
  });
}

test("escenarios con el pulgar: controles de 44 px o más", async ({ page }, info) => {
  test.skip(!touchy(info.project.name), "pantallas táctiles");
  await page.goto("/v2/AAPL/valor");
  await page.waitForSelector("[data-testid=scenario-value]", { timeout: 30_000 });
  const small = await page.$$eval(".presets .btn, .ctl input", (els) =>
    els.map((e) => [e.getAttribute("aria-label") ?? e.textContent ?? (e as HTMLInputElement).type, e.getBoundingClientRect().height] as const)
      .filter(([, h]) => h < 44));
  expect(small).toEqual([]);
});

test("las tres puntuaciones, una debajo de otra: en la cabecera, una línea cada una; en «La empresa», con su desglose", async ({ page }, info) => {
  test.skip(!["mobile", "mobile-webkit"].includes(info.project.name), "teléfonos");
  await page.goto("/v2/AAPL");
  await page.waitForSelector(".depth-body .dsec", { timeout: 30_000 });
  for (const sel of [".company-header .scores .score", "#desglose .scores .score"]) {
    const boxes = await page.$$eval(sel, (els) => els.map((e) => { const r = e.getBoundingClientRect(); return { top: r.top, bottom: r.bottom }; }));
    expect(boxes).toHaveLength(3);
    for (let i = 1; i < boxes.length; i++) expect(boxes[i].top).toBeGreaterThanOrEqual(boxes[i - 1].bottom);
  }
  // PM: la cabecera del móvil, lo justo (antes, con los tres desgloses, ~1.590 px)
  expect(await page.locator(".company-header:not(.compact)").evaluate((e) => e.getBoundingClientRect().height)).toBeLessThan(600);
  for (const id of ["breakdown-quality", "breakdown-price", "breakdown-confidence"]) await expect(page.locator("#desglose").getByTestId(id)).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});
test("la barra de capítulos deja a la vista el capítulo activo", async ({ page }, info) => {
  test.skip(!["mobile", "mobile-webkit"].includes(info.project.name), "teléfonos");
  await page.goto("/v2/AAPL/conclusion");
  await page.waitForSelector(".depth-body .dsec", { timeout: 30_000 });
  await page.waitForTimeout(800);
  const r = await page.evaluate(() => {
    const bar = document.querySelector<HTMLElement>(".chapterbar-grid")!, a = bar.querySelector<HTMLElement>("[aria-current=page]")!;
    const b = bar.getBoundingClientRect(), x = a.getBoundingClientRect();
    return { inside: x.left >= b.left - 1 && x.right <= b.right + 1, scrolls: bar.scrollWidth > bar.clientWidth };
  });
  expect(r.scrolls).toBe(true);
  expect(r.inside).toBe(true);
});
