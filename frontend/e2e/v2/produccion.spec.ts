import { test, expect } from "@playwright/test";

/**
 * Verificación de la v4 (V5 · producción simulada), solo contra el build servido por el backend (E2E_BUILD=1):
 * recarga directa en una URL profunda (el backend sirve la historia y la página lee la ruta) y rutas maliciosas → 404
 * sin servir archivos. Los recorridos crudos (%2e%2e, que un navegador normaliza antes de enviar) los prueba
 * backend/tests/test_v2_serving.py contra un uvicorn real.
 */
test.skip(process.env.E2E_BUILD !== "1", "solo contra el build servido por el backend (E2E_BUILD=1)");

for (const path of ["/v2/AAPL/valor", "/v2/AAPL/valor/", "/v2/JPM/calidad", "/v2/BRK-B"]) {
  test(`recarga directa en ${path}`, async ({ page }) => {
    const r = await page.goto(path);
    expect(r?.status()).toBe(200);
    expect(r?.headers()["content-type"]).toContain("text/html");
    if (!path.startsWith("/v2/BRK-B")) await expect(page.getByTestId("company-name")).not.toBeEmpty({ timeout: 30_000 });
  });
}

for (const path of ["/v2/..%2f..%2fbackend/main.py", "/v2/..%2fsecreto", "/v2/AAPL/..%2f..%2f..%2fbackend%2fmain.py",
  "/v2/..%5c..%5cbackend%5cmain.py"]) {
  test(`ruta maliciosa ${path} → 404`, async ({ request }) => {
    const r = await request.get(path);
    const body = await r.text();
    expect(r.status(), body.slice(0, 80)).toBe(404);
    expect(body).not.toContain("import ");
    expect(body).not.toContain("<html");
  });
}

// Revisión V6 (F13): las páginas de profundidad y las gráficas van en fragmentos propios (React.lazy dentro del
// fragmento de la historia). En `next dev`, Turbopack precarga en el HTML un fragmento que nunca genera cuando hay
// import() anidados (404 solo en desarrollo); en el build, todo lo que el HTML y la navegación piden existe.
for (const path of ["/v2", "/v2/AAPL", "/v2/AAPL/calidad", "/v2/AAPL/accion"]) {
  test(`sin fragmentos que falten en el build: ${path}`, async ({ page }) => {
    const bad: string[] = [];
    page.on("response", (r) => { if (r.url().includes("/_next/") && r.status() >= 400) bad.push(`${r.status()} ${r.url()}`); });
    await page.goto(path);
    await page.waitForLoadState("networkidle");
    expect(bad).toEqual([]);
  });
}

// Pre-pasada V4 (PM): robots.txt de verdad (frontend/public), no la página de la SPA. Permite todo; sin sitemap (no hay).
test("robots.txt: texto plano, permite todo, sin sitemap", async ({ request }, info) => {
  test.skip(info.project.name !== "desktop", "no depende del tamaño");
  const r = await request.get("/robots.txt");
  expect(r.status()).toBe(200);
  expect(r.headers()["content-type"]).toContain("text/plain");
  const body = await r.text();
  expect(body).toMatch(/^User-agent: \*$/m);
  expect(body).toMatch(/^Allow: \/$/m);
  expect(body).not.toMatch(/sitemap/i);
});


// E6 · paso 2: las rutas de transición. La v4 es la principal; la web actual, de respaldo durante la observación.
test("E6 · la raíz es la portada de la v4, en la misma URL", async ({ page }, info) => {
  test.skip(info.project.name !== "desktop", "no depende del tamaño");
  const r = await page.goto("/");
  expect(r?.status()).toBe(200);
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Entiende una empresa antes de invertir");
  // la portada exportada para /v2 se hidrata y funciona en /: el cintillo carga y una tarjeta lleva a su historia
  // (el cintillo avanza en continuo: con el ratón encima se para, y entonces el clic abre la tarjeta, como en home.spec)
  const card = page.getByTestId("ticker-item").first();
  await expect(card).toBeVisible({ timeout: 30_000 });
  const tape = page.getByTestId("ticker");
  await tape.hover();
  await expect(tape).toHaveAttribute("data-mode", "pausado");
  await card.click();
  await expect(page).toHaveURL(/\/v2\/[A-Z.\-]+\/?$/);
  await expect(page.getByTestId("company-name")).not.toBeEmpty({ timeout: 30_000 });
});

test("E6 · un símbolo en la raíz lleva a su historia de la v4", async ({ page, request }, info) => {
  test.skip(info.project.name !== "desktop", "no depende del tamaño");
  const r = await request.get("/AAPL", { maxRedirects: 0 });
  expect(r.status()).toBe(307);
  expect(r.headers()["location"]).toBe("/v2/AAPL");
  await page.goto("/AAPL");
  await expect(page).toHaveURL(/\/v2\/AAPL$/);
  await expect(page.getByTestId("company-name")).not.toBeEmpty({ timeout: 30_000 });
});

test("E6 · la web actual sigue de respaldo: /clasica y /stock/{T} con el aviso hacia la v4", async ({ page }, info) => {
  test.skip(info.project.name !== "desktop", "no depende del tamaño");
  await page.goto("/clasica");
  await expect(page).toHaveURL(/\/clasica\/?$/);
  await expect(page.locator("main, body").first()).not.toBeEmpty();
  await page.goto("/stock/AAPL");
  await expect(page.getByText("Apple Inc.").first()).toBeVisible({ timeout: 30_000 });
  const link = page.getByTestId("try-v4");
  await expect(link).toHaveText("Prueba la nueva versión →");
  await expect(link).toHaveAttribute("href", "/v2/AAPL");
  expect(await link.evaluate((e) => parseFloat(getComputedStyle(e).fontSize))).toBeGreaterThanOrEqual(12);
  await link.click();
  await expect(page).toHaveURL(/\/v2\/AAPL$/);
});
