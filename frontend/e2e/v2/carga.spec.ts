import { test, expect, type Page } from "@playwright/test";
import { WEB } from "../../src/lib/generated/backendConfig";

// V4 (PM): la carga del análisis. Cualquier error (404 del replay, 5xx, sin red o fuera del presupuesto de espera) lleva
// a un estado de error claro en menos de 2 s: el ticker, el motivo y dos salidas («Volver a intentarlo» y «Buscar otra
// empresa», con el buscador enfocado). Sin errores sin capturar ni avisos de precarga sin usar.

/** Errores sin capturar y avisos de la consola que no deben salir. */
function watch(page: Page) {
  const problems: string[] = [];
  page.on("pageerror", (e) => problems.push(`pageerror: ${e.message}`));
  page.on("console", (m) => { if (/preloaded using link preload but not used/.test(m.text()) && /bg-home/.test(m.text())) problems.push(m.text()); });
  return problems;
}

const CASES: Array<{ name: string; sym: string; route?: { status: number; detail: string }; reason: RegExp }> = [
  // el replay no tiene HD: 404 con su motivo («HD: sin fixtures en el replay»), como un ticker válido que no conoce
  { name: "404 del replay", sym: "HD", reason: /HD: sin fixtures en el replay/ },
  { name: "5xx", sym: "AAPL", route: { status: 503, detail: "Service Unavailable" }, reason: /No se pudo analizar AAPL ahora mismo/ },
  // el backend real con un ticker inexistente: 404 «No data found for ZZZZZ» (verificación V2 con fuentes reales)
  { name: "404 de un ticker inexistente", sym: "ZZZZZ", route: { status: 404, detail: "No data found for ZZZZZ" }, reason: /No hay datos de ZZZZZ: comprueba el ticker/ },
];

for (const c of CASES) {
  test(`estado de error en menos de 2 s · ${c.name}`, async ({ page }) => {
    const problems = watch(page);
    if (c.route) await page.route(`**/api/analysis/${c.sym}`, (r) =>
      r.fulfill({ status: c.route!.status, contentType: "application/json", body: JSON.stringify({ detail: c.route!.detail }) }));
    const answered = page.waitForResponse((r) => r.url().includes(`/api/analysis/${c.sym}`), { timeout: 60_000 });
    await page.goto(`/v2/${c.sym}/`);
    await answered;
    const t0 = Date.now();
    const err = page.getByTestId("load-error");
    await expect(err.getByRole("alert")).toHaveText(c.reason, { timeout: 2_000 });
    expect(Date.now() - t0).toBeLessThan(2_000);
    await expect(err.getByRole("heading", { level: 1 })).toHaveText(c.sym);
    await expect(err.getByRole("alert")).not.toHaveText(/HTTP|Failed|Service Unavailable|No data found/);
    await expect(page.getByText(/^Analizando/)).toHaveCount(0);
    await expect(err.getByRole("button", { name: "Volver a intentarlo" })).toBeVisible();
    await err.getByRole("button", { name: "Buscar otra empresa" }).click();
    await expect(err.getByRole("combobox", { name: "Buscar empresa o ticker" })).toBeFocused();
    await page.waitForTimeout(3_500);                 // el aviso de precarga sin usar llega a los ~3 s de cargar
    expect(problems).toEqual([]);
  });
}

test("sin respuesta del backend: el estado de error al agotar el presupuesto de espera", async ({ page }, info) => {
  test.skip(info.project.name !== "desktop", "no depende del tamaño");
  // la petición queda colgada; el presupuesto se acorta en la página (la config dice 2 minutos)
  await page.route("**/api/analysis/AAPL", () => new Promise(() => {}));
  await page.clock.install();
  await page.goto("/v2/AAPL");
  await expect(page.getByTestId("analyze-loading")).toBeVisible({ timeout: 30_000 });
  await page.clock.runFor(121_000);
  await expect(page.getByTestId("load-error").getByRole("alert")).toContainText("está tardando más de lo normal");
});

test("«Volver a intentarlo» vuelve a pedir el análisis y la página carga", async ({ page }, info) => {
  test.skip(info.project.name !== "desktop", "no depende del tamaño");
  let calls = 0;
  await page.route("**/api/analysis/AAPL", (r) => (++calls === 1
    ? r.fulfill({ status: 502, contentType: "application/json", body: "{}" }) : r.continue()));
  await page.goto("/v2/AAPL");
  await page.getByTestId("load-error").getByRole("button", { name: "Volver a intentarlo" }).click();
  await page.waitForSelector(".depth-body .dsec", { timeout: 30_000 });
  expect(calls).toBe(2);
});

// ── La pantalla de carga (V4, PM, maqueta aprobada): anillo, «Analizando», nombre y ticker, la tarjeta con cinco
//    estaciones iguales y el pie; textos y tiempos de data.toml [web] (backendConfig.ts) ──
const L = WEB.loading;
const D = L.expectedMs / L.titles.length;

/** Retiene la respuesta del análisis de `sym` hasta llamar a la función devuelta. */
async function holdAnalysis(page: Page, sym: string) {
  let release: () => void = () => {};
  const gate = new Promise<void>((r) => { release = r; });
  await page.route(`**/api/analysis/${sym}`, async (route) => { await gate; return route.continue(); });
  return () => release();
}

test("la pantalla de carga: anillo, «Analizando», nombre corto y ticker, la tarjeta, el pie y el paso para lectores", async ({ page }) => {
  const problems = watch(page);
  const release = await holdAnalysis(page, "AAPL");
  await page.goto("/v2/AAPL");
  const box = page.getByTestId("analyze-loading");
  await expect(box).toBeVisible({ timeout: 30_000 });
  await expect(box.locator(".al-ring img[src='/brand/finanzer-logo.svg']")).toBeVisible();   // marca
  await expect(box.locator(".al-eyebrow")).toHaveText("Analizando");
  await expect(box.locator(".al-who")).toHaveText("AppleAAPL");              // sin la forma jurídica (P8)
  await expect(box.locator(".al-labels span")).toHaveText([...L.labels]);
  await expect(box.locator(".al-seg i")).toHaveCount(5);
  await expect(box.locator(".al-foot")).toHaveText(/^Suele tardar entre \d+ y \d+ segundos la primera vez; después, al instante\.$/);
  await expect(box.locator(".al-now small")).toHaveText(/^Paso [1-5] de 5$/);
  const step = Number(await box.getAttribute("data-station"));
  await expect(box.locator(".al-title")).toHaveText(L.titles[step]);
  await expect(box.locator(".al-phrase")).toHaveText(L.phrases[step]);
  await expect(box.getByRole("status")).toContainText("Analizando AAPL: ");
  // bajo la barra superior, que sigue a la vista
  const r = await page.evaluate(() => ({
    top: document.querySelector("[data-testid=analyze-loading]")!.getBoundingClientRect().top,
    bar: document.querySelector(".topbar")!.getBoundingClientRect().bottom,
  }));
  expect(Math.abs(r.top - r.bar)).toBeLessThanOrEqual(1);
  // letra mínima de 12 px
  const small = await box.evaluate((el) => [...el.querySelectorAll<HTMLElement>("*")]
    .filter((e) => e.childElementCount === 0 && (e.textContent ?? "").trim() && !e.closest(".sr-only"))
    .map((e) => parseFloat(getComputedStyle(e).fontSize)).filter((px) => px < 12));
  expect(small).toEqual([]);
  // la tarjeta no pasa de 520 px y en el móvil deja 16 px a cada lado
  const card = await box.locator(".al-card").boundingBox();
  const vw = page.viewportSize()!.width;
  expect(card!.width).toBeLessThanOrEqual(520.5);
  if (vw < 560) { expect(Math.round(card!.x)).toBe(16); expect(Math.round(vw - card!.x - card!.width)).toBe(16); }
  // al llegar el análisis, las que faltan pasan rápidas, se disuelve y queda la página (una sola capa)
  release();
  await page.waitForSelector(".depth-body .dsec", { timeout: 15_000 });
  await expect(box).toHaveCount(0);
  expect(problems).toEqual([]);
});

test("cinco estaciones iguales: con el replay retardado, cada cambio de estación llega a d de la anterior", async ({ page }, info) => {
  test.skip(info.project.name !== "desktop", "el ritmo no depende del tamaño");
  const release = await holdAnalysis(page, "AAPL");
  // cada cambio de estación, con su hora, desde la propia página
  await page.addInitScript(() => {
    const w = window as unknown as { __stations: Array<[number, number]> };
    w.__stations = [];
    new MutationObserver(() => {
      const el = document.querySelector("[data-testid=analyze-loading]");
      const st = el ? Number(el.getAttribute("data-station")) : NaN;
      const last = w.__stations[w.__stations.length - 1];
      if (!Number.isNaN(st) && (!last || last[0] !== st)) w.__stations.push([st, performance.now()]);
    }).observe(document, { subtree: true, childList: true, attributes: true, attributeFilter: ["data-station"] });
  });
  await page.goto("/v2/AAPL");
  await expect(page.getByTestId("analyze-loading")).toBeVisible({ timeout: 30_000 });
  // hasta la última y un poco más: sin datos, la quinta se queda en el 95 % con «Últimos ajustes…»
  await expect(page.getByTestId("analyze-loading")).toHaveAttribute("data-station", "4", { timeout: 15_000 });
  await page.waitForTimeout(D + 400);
  await expect(page.locator(".al-title")).toHaveText(L.stallTitle);
  const width = await page.locator(".al-seg i").nth(4).locator("span").evaluate((s) => s.style.width);
  expect(parseFloat(width)).toBeCloseTo(L.stallFill * 100, 1);
  const marks = await page.evaluate(() => (window as unknown as { __stations: Array<[number, number]> }).__stations);
  const gaps = marks.slice(1).map(([, t], i) => t - marks[i][1]).slice(1);   // la primera aparece a mitad (300 ms)
  expect(gaps.length).toBeGreaterThanOrEqual(3);
  for (const g of gaps) expect(Math.abs(g - D), `cambios cada ${gaps.map(Math.round).join(", ")} ms; d = ${Math.round(D)}`).toBeLessThan(120);
  release();
  await page.waitForSelector(".depth-body .dsec", { timeout: 15_000 });
});

test("del análisis en caché (menos de 300 ms) se entra directo, sin pantalla de carga", async ({ page }, info) => {
  test.skip(info.project.name !== "desktop", "no depende del tamaño");
  await page.goto("/v2/AAPL");
  await page.waitForSelector(".depth-body .dsec", { timeout: 60_000 });
  // desde aquí, ¿aparece en algún momento? (también un instante)
  await page.addInitScript(() => {
    new MutationObserver(() => {
      if (document.querySelector("[data-testid=analyze-loading]")) (window as unknown as { __loading: boolean }).__loading = true;
    }).observe(document, { childList: true, subtree: true });
  });
  await page.reload();
  await page.waitForSelector(".depth-body .dsec", { timeout: 60_000 });
  await page.waitForTimeout(500);
  expect(await page.evaluate(() => (window as unknown as { __loading?: boolean }).__loading ?? false)).toBe(false);
});

// v4.1 (movimiento): con «reducir movimiento» nada gira ni se desplaza; los fundidos se quedan, breves (≤ 150 ms)
test("con «reducir movimiento»: sin giro, fundidos breves y sin llenado; las estaciones cambian a saltos", async ({ page }, info) => {
  test.skip(info.project.name !== "desktop", "no depende del tamaño");
  await page.emulateMedia({ reducedMotion: "reduce" });
  await holdAnalysis(page, "AAPL");
  await page.goto("/v2/AAPL");
  const box = page.getByTestId("analyze-loading");
  await expect(box).toBeVisible({ timeout: 30_000 });
  const anim = (sel: string) => box.locator(sel).evaluate((c) => {
    const s = getComputedStyle(c);
    return { name: s.animationName, ms: parseFloat(s.animationDuration) * 1000, n: s.animationIterationCount };
  });
  const ring = await anim(".al-ring .d1");
  expect(ring.name === "none" || (ring.ms <= 1 && ring.n === "1"), `sin giro: ${JSON.stringify(ring)}`).toBe(true);
  const title = await anim(".al-title");
  expect(title.name === "none" || title.ms <= 150, `fundido breve: ${JSON.stringify(title)}`).toBe(true);
  await expect(box).toHaveAttribute("data-station", "2", { timeout: 10_000 });
  // el tramo en curso no se llena poco a poco; los anteriores, enteros
  const widths = await box.locator(".al-seg i span").evaluateAll((els) => els.map((e) => (e as HTMLElement).style.width));
  expect(widths).toEqual(["100%", "100%", "0%", "0%", "0%"]);
});

test("un error con la pantalla de carga a la vista: el estado de error sale enseguida", async ({ page }, info) => {
  test.skip(info.project.name !== "desktop", "no depende del tamaño");
  await page.route("**/api/analysis/AAPL", async (route) => {
    await new Promise((r) => setTimeout(r, 1_000));
    return route.fulfill({ status: 500, contentType: "application/json", body: "{}" });
  });
  await page.goto("/v2/AAPL");
  await expect(page.getByTestId("analyze-loading")).toBeVisible({ timeout: 30_000 });
  await page.waitForResponse((r) => r.url().includes("/api/analysis/AAPL"));
  const t0 = Date.now();
  await expect(page.getByTestId("load-error").getByRole("alert")).toBeVisible({ timeout: 2_000 });
  expect(Date.now() - t0).toBeLessThan(2_000);
  await expect(page.getByTestId("analyze-loading")).toHaveCount(0);
});

test("al cambiar de empresa desde el buscador de la cabecera, la pantalla de carga con su nombre corto", async ({ page }, info) => {
  test.skip(info.project.name !== "desktop", "el buscador de la cabecera es de escritorio");
  await page.goto("/v2/AAPL");
  await page.waitForSelector(".depth-body .dsec", { timeout: 60_000 });
  await holdAnalysis(page, "MSFT");
  const q = page.locator(".topbar").getByRole("combobox", { name: "Buscar empresa o ticker" });
  await q.fill("Microsoft");
  const opt = page.getByRole("option").filter({ hasText: "MSFT" }).first();
  await expect(opt).toBeVisible({ timeout: 30_000 });
  await opt.click();
  await page.waitForURL(/\/v2\/MSFT\/?$/, { waitUntil: "commit" });
  const box = page.getByTestId("analyze-loading");
  await expect(box).toBeVisible({ timeout: 30_000 });
  await expect(box.locator(".al-who")).toHaveText("MicrosoftMSFT");
});

test("desde el cintillo de la portada, la pantalla de carga con el nombre corto de la empresa", async ({ page }, info) => {
  test.skip(info.project.name !== "desktop", "no depende del tamaño");
  await page.goto("/v2");
  const item = page.getByTestId("ticker-item").first();
  await expect(item).toBeVisible({ timeout: 60_000 });
  const sym = (await item.getAttribute("data-symbol"))!;
  const name = (await item.locator(".tk-name").innerText()).trim();
  await holdAnalysis(page, sym);
  // el cintillo se mueve solo: el clic va al enlace directamente (el mismo manejador y la misma navegación)
  await item.evaluate((a) => (a as HTMLAnchorElement).click());
  const box = page.getByTestId("analyze-loading");
  await expect(box).toBeVisible({ timeout: 30_000 });
  await expect(box.locator(".al-who")).toContainText(sym);
  if (name !== sym) await expect(box.locator(".al-who")).toContainText(name.replace(/,?\s+(Inc\.?|Corp\.?|Corporation|Ltd\.?|plc)$/i, ""));
});
