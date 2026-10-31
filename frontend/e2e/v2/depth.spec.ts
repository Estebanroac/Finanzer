import { test, expect } from "@playwright/test";
import { collectConsoleErrors, smallTexts, symmetryProblems } from "./checks";

// E3 (Tasks 3–11): las nueve páginas de profundidad en los 8 tickers del panel. Cada una carga sin errores de consola,
// cada píldora lleva a su sección, la rejilla es simétrica sin huecos, ningún texto baja de 12 px y no queda ninguna
// página provisional. Un dato ausente es una línea (`[data-missing]`), nunca una caja vacía.
const TICKERS = ["AAPL", "JPM", "O", "NEE", "XOM", "PLTR", "RIVN", "BCS"];
const CHAPTERS = ["empresa", "negocio", "accion", "calidad", "valor", "rivales", "riesgos", "actualidad", "conclusion"];

for (const ch of CHAPTERS) {
  for (const t of TICKERS) {
    test(`profundidad · ${ch} · ${t}`, async ({ page }) => {
      const errors = collectConsoleErrors(page);
      await page.goto(`/v2/${t}/${ch}`);
      await page.waitForSelector(".depth-body .dsec", { timeout: 30_000 });
      await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => {});
      await page.waitForTimeout(500);
      await expect(page.locator(".depth-body")).not.toContainText("Página en construcción");

      // Píldoras: cada una apunta a una sección que existe y, al pulsarla, la deja arriba
      const pills = page.locator("nav.pillindex a.pillnav");
      const n = await pills.count();
      expect(n).toBeGreaterThan(0);
      for (let i = 0; i < n; i++) {
        const id = (await pills.nth(i).getAttribute("href"))!.slice(1);
        await expect(page.locator(`[id="${id}"]`), `sección #${id}`).toHaveCount(1);
      }
      const last = pills.nth(n - 1);
      await last.click();
      await expect(last).toHaveAttribute("aria-current", "location");

      // Ninguna caja vacía: toda tarjeta tiene texto
      const empty = await page.$$eval(".depth-body .card", (cs) => cs.filter((c) => !c.textContent?.trim()).length);
      expect(empty, "tarjetas vacías").toBe(0);

      expect(await symmetryProblems(page)).toEqual([]);
      expect(await smallTexts(page)).toEqual([]);
      expect(errors).toEqual([]);
    });
  }
}

test("las pestañas cambian de sección sin volver a pedir el análisis (y atrás también)", async ({ page }) => {
  const calls: string[] = [];
  page.on("request", (r) => { if (/\/api\/analysis\//.test(r.url())) calls.push(r.url()); });
  await page.goto("/v2/AAPL");
  await page.waitForSelector(".depth[data-chapter=empresa] .depth-body .dsec", { timeout: 30_000 });
  await page.locator("nav.chapterbar").getByRole("link", { name: "Calidad", exact: true }).click();
  await expect(page).toHaveURL(/\/v2\/AAPL\/calidad\/?$/);
  await page.waitForSelector(".depth[data-chapter=calidad] .depth-body .dsec");
  await page.goBack();
  await expect(page).toHaveURL(/\/v2\/AAPL\/?$/);
  await page.waitForSelector(".depth[data-chapter=empresa] .depth-body .dsec");
  expect(calls).toHaveLength(1);
});

test("el tooltip «?» se abre, dice el valor de la empresa y se cierra con Esc", async ({ page }) => {
  await page.goto("/v2/AAPL/calidad");
  await page.waitForSelector(".depth-body .dsec", { timeout: 30_000 });
  const btn = page.locator(".techtable .tip-btn").first();
  await btn.scrollIntoViewIfNeeded();
  await btn.click();
  const dlg = page.locator('[role="dialog"]').first();
  await expect(dlg).toBeVisible();
  await expect(dlg).toContainText("Tu valor");
  await page.keyboard.press("Escape");
  await expect(dlg).toBeHidden();
  await expect(btn).toBeFocused();
});

test("«Descargar PDF» lleva al informe nuevo (/api/v2/pdf) y devuelve un PDF", async ({ page }, info) => {
  test.skip(info.project.name !== "desktop", "mismo enlace en móvil");
  test.setTimeout(120_000);
  await page.goto("/v2/AAPL/conclusion");
  await page.waitForSelector(".depth-body .dsec", { timeout: 30_000 });
  const hrefs = await page.$$eval("a", (as) => as.filter((a) => a.textContent?.includes("Descargar PDF")).map((a) => a.getAttribute("href")!));
  expect(hrefs.length).toBe(2);                                   // la barra superior y la página Conclusión
  hrefs.forEach((h) => expect(h).toMatch(/\/api\/v2\/pdf\/AAPL$/));
  const res = await page.request.get(hrefs[0], { timeout: 110_000 });
  expect(res.status()).toBe(200);
  expect(res.headers()["content-type"]).toContain("application/pdf");
  expect((await res.body()).subarray(0, 4).toString()).toBe("%PDF");
});

for (const [t, ch] of [["AAPL", "rivales"], ["AAPL", "calidad"], ["JPM", "calidad"], ["AAPL", "valor"]] as const) {
  test(`tablas apiladas con las columnas alineadas y sin «— —» · ${t}/${ch}`, async ({ page }, info) => {
    test.skip(info.project.name !== "desktop", "en móvil la tabla técnica se apila en fichas");
    await page.goto(`/v2/${t}/${ch}`);
    await page.waitForSelector(".depth-body .dsec", { timeout: 30_000 });
    await page.waitForTimeout(500);
    const r = await page.evaluate(() => {
      const cols = (sel: string) => [...document.querySelectorAll<HTMLTableElement>(sel)].map((tb) =>
        [...(tb.tHead?.rows[0].cells ?? [])].map((c) => Math.round(c.getBoundingClientRect().left - tb.getBoundingClientRect().left)).join(","));
      const dashes = [...document.querySelectorAll(".depth table.techtable.metrics tbody tr")].filter((tr) =>
        [...tr.querySelectorAll("td")].slice(-2).map((td) => td.textContent?.trim()).join("|") === "—|—").length;   // Brecha | Lectura
      return { metrics: cols(".depth table.techtable.metrics"), breakdown: cols(".depth table.techtable.bdtable"), dashes };
    });
    // V4b · 4: hay tablas de cinco columnas y de tres (sin referencia); cada forma, alineada, y en todas Métrica y
    // Empresa en el mismo sitio
    const byShape = (n: number) => new Set(r.metrics.filter((c) => c.split(",").length === n));
    expect(byShape(5).size).toBeLessThanOrEqual(1);
    expect(byShape(3).size).toBeLessThanOrEqual(1);
    expect(new Set(r.metrics.map((c) => c.split(",").slice(0, 2).join(","))).size).toBeLessThanOrEqual(1);
    expect(new Set(r.breakdown).size).toBeLessThanOrEqual(1);
    expect(r.dashes, "«— —» en Brecha y Lectura").toBe(0);
  });
}

// Rediseño v4 (PM): el país del emisor en español, de la tabla de nombres del backend (config/names.toml [countries])
for (const [t, country] of [["AAPL", "Estados Unidos"], ["TSM", "Taiwán"], ["ASML", "Países Bajos"]] as const) {
  test(`La empresa: el país en español · ${t}`, async ({ page }, info) => {
    test.skip(info.project.name !== "desktop", "el texto no depende del tamaño");
    await page.goto(`/v2/${t}/empresa`);
    const row = page.locator(".kv-row").filter({ has: page.locator("dt", { hasText: /^País$/ }) });
    await expect(row.locator("dd")).toHaveText(country, { timeout: 30_000 });
  });
}
