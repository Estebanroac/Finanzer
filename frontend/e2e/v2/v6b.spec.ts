import { test, expect, type Page } from "@playwright/test";

// V6b (revisión de código y seguridad del delta final, docs/rediseno/verificacion/V6b_delta_final.md): los hallazgos de
// E3 que se ven en el navegador. E2, E3, E4, E8 y E9 tienen su prueba en src/v2/components/v6b.test.tsx. E5 y E6 (el
// desglose al pasar el ratón y su «Ver detalle» en el móvil) dejaron de existir con V4b · 2: el desglose está siempre a la
// vista (nada-oculto.spec.ts).
const desktopOnly = (name: string) => test.skip(name !== "desktop", "en escritorio");
const PANEL = ".tip-box:not([data-state=closed])";

async function story(page: Page, path = "/v2/AAPL/calidad") {
  await page.goto(path);
  await page.waitForSelector(".depth-body .dsec", { timeout: 60_000 });
}

test.describe("E1 · foco y Escape del panel del «?» (escritorio)", () => {
  test("Tab al final del panel lo cierra y el foco vuelve al «?»; Shift+Tab al principio, igual", async ({ page }, info) => {
    desktopOnly(info.project.name);
    await story(page);
    const q = page.locator("button.tip-btn").first();
    await q.click();
    const panel = page.locator(PANEL);
    await expect(panel.getByRole("button", { name: "Cerrar" })).toBeFocused();
    const n = await panel.locator("button, a[href]").count();
    for (let i = 0; i < n; i++) await page.keyboard.press("Tab");          // el último Tab sale del borde
    await expect(page.locator(PANEL)).toHaveCount(0);
    await expect(q).toBeFocused();
    await q.press("Enter");
    await expect(panel.getByRole("button", { name: "Cerrar" })).toBeFocused();
    await page.keyboard.press("Shift+Tab");
    await expect(page.locator(PANEL)).toHaveCount(0);
    await expect(q).toBeFocused();
  });

  test("el panel se cierra cuando el foco se va a otro sitio, y Escape fuera de él no es suyo", async ({ page }, info) => {
    desktopOnly(info.project.name);
    await story(page);
    const q = page.locator("button.tip-btn").first();
    await q.click();
    await expect(page.locator(PANEL)).toHaveCount(1);
    const search = page.locator(".topbar").getByRole("combobox", { name: "Buscar empresa o ticker" });
    await search.focus();
    await expect(page.locator(PANEL)).toHaveCount(0);
    await page.keyboard.press("Escape");
    await expect(search).toBeFocused();                                     // el foco no vuelve al «?»
  });

  test("con el teclado no quedan dos «?» abiertos a la vez", async ({ page }, info) => {
    desktopOnly(info.project.name);
    await story(page);
    const qs = page.locator("button.tip-btn");
    await qs.nth(0).focus();
    await page.keyboard.press("Enter");
    await expect(page.locator(PANEL)).toHaveCount(1);
    await qs.nth(1).focus();
    await page.keyboard.press("Enter");
    await expect(page.locator(PANEL)).toHaveCount(1);
    await expect(qs.nth(1)).toHaveAttribute("aria-expanded", "true");
    await expect(qs.nth(0)).toHaveAttribute("aria-expanded", "false");
  });
});

test("E7 · el sondeo de rivales tiene tope: pasado, lo dice en lugar de preguntar sin fin", async ({ page }, info) => {
  desktopOnly(info.project.name);
  let asked = 0;
  await page.route("**/api/v2/peers/AAPL**", (r) => { asked++; return r.fulfill({ json: {
    status: "calculando", symbol: "AAPL", source: "auto", max_symbols: 5, poll_s: 4, industry: null, note: null, company: null, rivals: [] } }); });
  await page.clock.install();
  await story(page, "/v2/AAPL/rivales");
  await page.clock.runFor(601_000);
  await expect(page.getByTestId("peers")).toContainText("tardando más de lo normal");
  const n = asked;
  await page.clock.runFor(60_000);
  expect(asked).toBe(n);                                                  // ya no pregunta
});

test("E11 · la portada pide las tendencias solo del periodo que enseña", async ({ page }, info) => {
  desktopOnly(info.project.name);
  const asked: string[] = [];
  page.on("request", (r) => { if (r.url().includes("/api/v2/trending")) asked.push(new URL(r.url()).search); });
  await page.goto("/v2");
  await expect(page.getByTestId("ticker-item").first()).toBeVisible({ timeout: 60_000 });
  expect(asked[0]).toBe("?period=1D");
  await page.getByTestId("period-6M").click();
  await expect.poll(() => asked).toContain("?period=6M");
  await expect(page.getByTestId("ticker-context")).toContainText("6 meses");
  // volver a un periodo ya visto enseña su lista enseguida (lo que ya se tenía), mientras vuelve a preguntar
  await page.getByTestId("period-1D").click();
  await expect(page.getByTestId("ticker-item").first()).toBeVisible();
  await expect(page.getByTestId("ticker-context")).toContainText("1 día");
});
