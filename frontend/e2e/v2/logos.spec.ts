import { test, expect, type Page, type Locator } from "@playwright/test";

/**
 * Logotipos de las empresas (backend/lib/logos.py, GET /api/v2/logo/{símbolo}; web: CompanyLogo). En el replay salen
 * los grabados (backend/tests/fixtures/logos); los demás, la placa con las iniciales.
 *  · El logotipo aparece en la cabecera de la acción, el cintillo de la portada, el buscador y los rivales.
 *  · Sin logotipo, o si la imagen falla al cargar, la placa con las iniciales: nunca un hueco ni una imagen rota.
 *  · El sitio está reservado desde el principio: la placa mide lo mismo cargando, con logotipo y con iniciales.
 */

const REM = 16;
const SIZE = { sm: 1.75 * REM, md: 2.25 * REM, lg: 3 * REM };
/** El corte de móvil de la web (47,9375 em): por debajo, la placa pequeña en el cintillo (deja sitio a la gráfica). */
const PHONE_MAX = 767;
const stripSide = (page: Page) => (page.viewportSize()!.width <= PHONE_MAX ? SIZE.sm : SIZE.md);

/** Estado de una placa (loading, ok o fail), su tamaño y si su imagen está cargada de verdad. */
async function plate(l: Locator) {
  return l.evaluate((e) => {
    const r = e.getBoundingClientRect();
    const img = e.querySelector("img");
    return { state: (e as HTMLElement).dataset.state, w: Math.round(r.width), h: Math.round(r.height), text: e.textContent,
      img: img ? { src: img.getAttribute("src"), loaded: img.complete && img.naturalWidth > 0 } : null };
  });
}

/** Ninguna imagen rota en la página: toda <img> cargada tiene píxeles. */
async function brokenImages(page: Page) {
  return page.evaluate(() => [...document.images].filter((i) => i.complete && i.naturalWidth === 0).map((i) => i.src));
}

test("el logotipo aparece en la cabecera, el cintillo, el buscador y los rivales", async ({ page }) => {
  await page.goto("/v2");
  // Cintillo: cada tarjeta lleva su logotipo (la vista inicial está grabada entera)
  const card = page.locator("[data-testid=ticker-item][data-symbol=AAPL]");
  const aapl = card.getByTestId("company-logo");
  await expect(aapl).toHaveAttribute("data-state", "ok", { timeout: 30_000 });
  const a = await plate(aapl);
  expect(a.img?.src).toMatch(/\/api\/v2\/logo\/AAPL$/);
  expect(a.img?.loaded).toBe(true);
  const side = stripSide(page);
  expect([a.w, a.h]).toEqual([side, side]);
  await expect(page.locator("[data-testid=ticker] .run:not([data-copy]) [data-testid=company-logo][data-state=ok]"))
    .toHaveCount(30, { timeout: 30_000 });

  // Buscador: cada resultado con su logotipo
  const q = page.getByRole("combobox", { name: "Buscar empresa o ticker" }).first();
  await q.fill("apple");
  const hit = page.getByRole("option").filter({ hasText: "AAPL" }).first();
  await expect(hit.getByTestId("company-logo")).toHaveAttribute("data-state", "ok", { timeout: 15_000 });
  expect((await plate(hit.getByTestId("company-logo"))).w).toBe(SIZE.sm);

  // Cabecera de la acción: el logotipo versionado que trae el análisis
  await page.goto("/v2/NFLX");
  const head = page.locator(".company-header:not(.compact)").getByTestId("company-logo");
  await expect(head).toHaveAttribute("data-state", "ok", { timeout: 30_000 });
  const h = await plate(head);
  expect(h.img?.src).toMatch(/\/api\/v2\/logo\/NFLX\?v=[0-9a-f]{12}$/);
  expect([h.w, h.h]).toEqual([SIZE.lg, SIZE.lg]);
  // la cabecera fija es solo visual: su placa no lleva identificador de prueba
  await expect(page.getByTestId("company-logo")).toHaveCount(1);

  // Rivales: con logotipo los grabados; DIS no lo está y lleva su placa
  await page.goto("/v2/NFLX/rivales");
  const peers = page.getByTestId("peers");
  await expect(peers.locator("tr[data-status] [data-testid=company-logo][data-symbol=TKO]"))
    .toHaveAttribute("data-state", "ok", { timeout: 60_000 });
  const dis = peers.locator("[data-testid=company-logo][data-symbol=DIS]");
  await expect(dis).toHaveAttribute("data-state", "fail");
  expect((await plate(dis)).text).toMatch(/^[A-Z]{1,2}$/);
  expect(await brokenImages(page)).toEqual([]);
});

test("sin logotipo o si la imagen falla: la placa con las iniciales, del mismo tamaño y sin imagen rota", async ({ page }) => {
  // las imágenes de logotipo fallan (no es un PNG) y el análisis dice que NFLX no tiene logotipo
  await page.route("**/api/v2/logo/**", (route) => route.fulfill({ status: 200, contentType: "image/png", body: "no es un png" }));
  await page.route("**/api/analysis/NFLX", async (route) => {
    const res = await route.fetch();
    return route.fulfill({ response: res, json: { ...(await res.json()), logo: null } });
  });

  await page.goto("/v2");
  const cards = page.locator("[data-testid=ticker] .run:not([data-copy]) [data-testid=company-logo]");
  await expect(cards).toHaveCount(30, { timeout: 30_000 });
  await expect(page.locator("[data-testid=ticker] .run:not([data-copy]) [data-testid=company-logo][data-state=fail]"))
    .toHaveCount(30, { timeout: 15_000 });
  const side = stripSide(page);
  for (const sym of ["AAPL", "META", "NVDA"]) {
    const p = await plate(page.locator(`[data-testid=ticker-item][data-symbol=${sym}]`).getByTestId("company-logo"));
    expect(p.img, sym).toBeNull();
    expect(p.text, sym).toMatch(/^[A-Z0-9]{1,2}$/);
    expect([p.w, p.h], sym).toEqual([side, side]);
  }
  expect(await page.locator("[data-testid=ticker-item][data-symbol=AAPL] .co-logo-ph").evaluate((e) =>
    parseFloat(getComputedStyle(e).fontSize))).toBeGreaterThanOrEqual(12);   // nada baja de 12 px
  expect(await brokenImages(page)).toEqual([]);

  // Cabecera: el análisis dice que no hay logotipo → la placa, sin imagen que pedir
  await page.goto("/v2/NFLX");
  const head = page.locator(".company-header:not(.compact)").getByTestId("company-logo");
  await expect(head).toHaveAttribute("data-state", "fail", { timeout: 30_000 });
  const h = await plate(head);
  expect(h.img).toBeNull();
  expect(h.text).toBe("N");                                     // Netflix Inc. → N (sin la forma jurídica)
  expect([h.w, h.h]).toEqual([SIZE.lg, SIZE.lg]);
  expect(await brokenImages(page)).toEqual([]);
});

test("el hueco del logotipo está reservado: la tarjeta no cambia de tamaño al llegar la imagen", async ({ page }) => {
  // la imagen tarda: se mide la tarjeta cargando y ya con el logotipo
  let release: () => void = () => {};
  const gate = new Promise<void>((r) => { release = r; });
  await page.route("**/api/v2/logo/AAPL", async (route) => { await gate; await route.continue(); });
  await page.goto("/v2");
  const card = page.locator("[data-testid=ticker-item][data-symbol=AAPL]");
  const logo = card.getByTestId("company-logo");
  await expect(logo).toHaveAttribute("data-state", "loading", { timeout: 30_000 });
  const box = async () => card.evaluate((e) => { const r = e.getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height)]; });
  const before = await box();
  const sym = await card.locator(".tk-sym").evaluate((e) => Math.round(e.getBoundingClientRect().left - e.parentElement!.getBoundingClientRect().left));
  release();
  await expect(logo).toHaveAttribute("data-state", "ok", { timeout: 15_000 });
  expect(await box()).toEqual(before);
  expect(await card.locator(".tk-sym").evaluate((e) => Math.round(e.getBoundingClientRect().left - e.parentElement!.getBoundingClientRect().left))).toBe(sym);
});

test("tema oscuro: el logotipo va sobre su placa blanca, con el filo del tema", async ({ page }) => {
  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto("/v2/NFLX");
  const head = page.locator(".company-header:not(.compact)").getByTestId("company-logo");
  await expect(head).toHaveAttribute("data-state", "ok", { timeout: 30_000 });
  const look = await head.evaluate((e) => ({
    plate: getComputedStyle(e.querySelector("img")!).backgroundColor,
    edge: getComputedStyle(e, "::after").boxShadow,
    theme: document.querySelector(".fz2")?.getAttribute("data-theme") ?? document.documentElement.getAttribute("data-v2theme"),
  }));
  expect(look.theme).toBe("dark");
  expect(look.plate).toBe("rgb(255, 255, 255)");                // un logotipo transparente se lee en oscuro
  expect(look.edge).toContain("inset");
});

test("noticias sin foto: la portada lleva el logotipo de la empresa y el medio, y mide lo mismo", async ({ page }) => {
  // TM: con los datos grabados ninguna de sus noticias trae foto propia (todas, portada)
  await page.goto("/v2/TM/actualidad");
  const covers = page.locator(".depth .news-card .news-img-empty");
  await expect(covers.first()).toBeVisible({ timeout: 30_000 });
  const n = await covers.count();
  expect(n).toBe(await page.locator(".depth .news-card").count());
  await expect(page.locator(".depth .news-img-empty [data-testid=news-logo][data-state=ok]")).toHaveCount(n, { timeout: 15_000 });
  const first = covers.first();
  await expect(first.locator(".news-ph-src")).not.toBeEmpty();
  expect(await first.locator("[data-testid=news-logo] img").getAttribute("src")).toMatch(/\/api\/v2\/logo\/TM\?v=[0-9a-f]{12}$/);
  const hs = await page.locator(".depth .news-card .news-img").evaluateAll((els) => els.map((e) => Math.round(e.getBoundingClientRect().height)));
  expect(new Set(hs)).toEqual(new Set([7 * REM]));              // la portada sigue en 7 rem, como la foto
  expect((await plate(first.getByTestId("news-logo"))).w).toBe(SIZE.lg);
  expect(await brokenImages(page)).toEqual([]);
});
