import { test, expect } from "@playwright/test";

// Revisión V6 (frontend): cada arreglo con su prueba en el navegador. Las de los cálculos (F1) y la caché (F12, F14)
// tienen además sus pruebas unitarias (Vitest) y del backend (tests/test_price_returns.py).
const desktopOnly = (name: string) => test.skip(name !== "desktop", "el comportamiento no depende del tamaño");

test("F2 · error al cargar: el motivo en español y «Volver a intentarlo» lo vuelve a pedir (V4: estado de error)", async ({ page }, info) => {
  desktopOnly(info.project.name);
  let calls = 0;
  await page.route("**/api/analysis/AAPL", async (route) => {
    calls++;
    if (calls === 1) return route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "Service Unavailable" }) });
    return route.continue();
  });
  await page.goto("/v2/AAPL");
  const err = page.getByTestId("load-error");
  await expect(err.getByRole("alert")).toContainText("No se pudo analizar AAPL ahora mismo");
  await expect(err.getByRole("alert")).not.toContainText(/HTTP|Failed|Service Unavailable/);
  await err.getByRole("button", { name: "Volver a intentarlo" }).click();
  await page.waitForSelector(".depth-body .dsec", { timeout: 30_000 });
  expect(calls).toBe(2);
});

test("F6 · un símbolo que no es un ticker: «Ticker no válido», sin pedir el análisis", async ({ page }, info) => {
  desktopOnly(info.project.name);
  const asked: string[] = [];
  page.on("request", (r) => { if (r.url().includes("/api/analysis/")) asked.push(r.url()); });
  await page.goto("/v2/%3Cscript%3E/calidad");
  await expect(page.getByTestId("invalid-ticker")).toContainText("Ticker no válido");
  await expect(page.getByTestId("invalid-ticker").getByRole("link", { name: "Volver a la portada" })).toBeVisible();
  await expect(page).toHaveTitle("Ticker no válido · Finanzer");
  expect(asked).toEqual([]);
});

test("F7 · título por sección y empresa, y el foco al título al cambiar de sección", async ({ page }, info) => {
  desktopOnly(info.project.name);
  await page.goto("/v2/AAPL");
  await page.waitForSelector(".depth-body .dsec", { timeout: 30_000 });
  await expect(page).toHaveTitle("La empresa · Apple Inc. (AAPL) · Finanzer");
  await page.locator("nav.chapterbar").getByRole("link", { name: "Calidad", exact: true }).click();
  await page.waitForSelector(".depth[data-chapter=calidad] .depth-body .dsec", { timeout: 30_000 });
  await expect(page).toHaveTitle("Calidad · Apple Inc. (AAPL) · Finanzer");
  await expect(page.locator("[data-page-title]")).toBeFocused();
  await expect(page.locator(":focus")).toHaveText("Qué tan buena es la empresa");
});

test("F4 · rivales: dos «Quitar» seguidos no se pisan, y un 502 pasajero del sondeo se reintenta", async ({ page }, info) => {
  desktopOnly(info.project.name);
  let failed = 0;
  const asked: string[] = [];
  await page.route("**/api/v2/peers/AAPL**", async (route) => {
    asked.push(new URL(route.request().url()).search);
    if (failed === 0) { failed++; return route.fulfill({ status: 502, body: "Bad Gateway" }); }
    return route.continue();
  });
  await page.goto("/v2/AAPL/rivales");
  const rows = page.locator("[data-testid=peers] tbody tr[data-status]");
  await expect(rows.first()).toBeVisible({ timeout: 30_000 });     // tras el 502, el reintento llegó
  expect(failed).toBe(1);
  const syms = await rows.locator("th .metric-name").allTextContents();
  expect(syms.length).toBeGreaterThan(2);
  // Dos clics seguidos, sin esperar la respuesta del primero
  await page.getByRole("button", { name: `Quitar ${syms[0]}` }).click();
  await page.getByRole("button", { name: `Quitar ${syms[1]}` }).click();
  await expect(rows).toHaveCount(syms.length - 2, { timeout: 30_000 });
  const last = decodeURIComponent(asked[asked.length - 1]);
  expect(last).not.toContain(syms[0]);
  expect(last).not.toContain(syms[1]);
});

test("F5 · buscador de rivales: /api/v2/search, y una respuesta vieja no pisa a la nueva", async ({ page }, info) => {
  desktopOnly(info.project.name);
  const searched: string[] = [];
  await page.route("**/api/search**", (route) => route.abort());          // la búsqueda de la web actual, no
  await page.route("**/api/v2/search**", async (route) => {
    const q = new URL(route.request().url()).searchParams.get("q") ?? "";
    searched.push(q);
    const body = { results: [{ ticker: q === "mi" ? "VIEJO" : "MSFT", name: `Resultado de ${q}`, exchange: "Nasdaq" }] };
    if (q === "mi") await new Promise((r) => setTimeout(r, 1500));   // la primera tarda más que la segunda
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
  });
  await page.goto("/v2/AAPL/rivales");
  const input = page.locator("#peer-search");
  // Con el cupo de rivales lleno el buscador se desactiva: se quita uno para poder añadir
  const first = page.locator("[data-testid=peers] tbody tr[data-status] button[aria-label^=Quitar]").first();
  await expect(first).toBeVisible({ timeout: 30_000 });
  if (await input.isDisabled()) await first.click();
  await expect(input).toBeEnabled({ timeout: 30_000 });
  await input.fill("mi");
  await page.waitForTimeout(400);           // pasa la espera: sale la búsqueda de «mi»
  await input.fill("micro");
  await expect(page.locator(".peer-hits")).toContainText("MSFT");
  await page.waitForTimeout(1800);          // llega tarde la de «mi»: no se pinta
  await expect(page.locator(".peer-hits")).not.toContainText("VIEJO");
  await expect(page.locator(".peer-hits")).not.toHaveAttribute("role", "listbox");
  expect(searched).toContain("micro");
});

test("F5 · precio de la cabecera en la moneda de la cotización (MC.PA en EUR; AAPL en $)", async ({ page }, info) => {
  desktopOnly(info.project.name);
  await page.goto("/v2/MC.PA");
  await expect(page.getByTestId("price")).toHaveText(/^EUR \d/, { timeout: 30_000 });
  await page.goto("/v2/AAPL");
  await expect(page.getByTestId("price")).toHaveText(/^\$\d/, { timeout: 30_000 });
});

test("F8 · «?» en móvil: hoja modal (Tab atrapado, fondo quieto) y, al tocar fuera, el foco vuelve al «?»", async ({ page }, info) => {
  test.skip(info.project.name !== "mobile", "la hoja inferior es del móvil");
  await page.goto("/v2/AAPL/calidad");
  const q = page.locator("button.tip-btn").first();
  await q.scrollIntoViewIfNeeded({ timeout: 30_000 });
  await q.click();
  const sheet = page.locator(".tip-box.sheet");
  await expect(sheet).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.style.overflow)).toBe("hidden");
  for (let i = 0; i < 4; i++) {
    await page.keyboard.press("Tab");
    expect(await sheet.evaluate((b) => b.contains(document.activeElement))).toBe(true);
  }
  await page.locator(".tip-backdrop").dispatchEvent("pointerdown");
  await expect(sheet).toBeHidden();
  await expect(q).toBeFocused();
  expect(await page.evaluate(() => document.documentElement.style.overflow)).toBe("");
});

test("F8 · «?» en escritorio: el popover no atrapa Tab ni bloquea el desplazamiento", async ({ page }, info) => {
  desktopOnly(info.project.name);
  await page.goto("/v2/AAPL/calidad");
  const q = page.locator("button.tip-btn").first();
  await q.click({ timeout: 30_000 });
  const box = page.locator(".tip-box");
  await expect(box).toBeVisible();
  await expect(box.getByRole("button", { name: "Cerrar" })).toBeFocused();     // el foco entra al abrir
  expect(await page.evaluate(() => document.documentElement.style.overflow)).toBe("");
  const n = await box.locator("button, a[href]").count();
  for (let i = 0; i < n; i++) await page.keyboard.press("Tab");
  // V6b (E1): Tab pasado el último control no queda atrapado: el panel se cierra y el foco vuelve al «?», desde donde
  // sigue el orden de la página
  await expect(page.locator(".tip-box:not([data-state=closed])")).toHaveCount(0);
  await expect(q).toBeFocused();
});

test("F11 · buscador: al escribir se desmarca la opción y Enter no abre un resultado de la búsqueda anterior", async ({ page }, info) => {
  desktopOnly(info.project.name);
  await page.route("**/api/v2/search**", async (route) => {
    const q = new URL(route.request().url()).searchParams.get("q") ?? "";
    if (q !== "apple") await new Promise((r) => setTimeout(r, 2500));    // la nueva búsqueda tarda
    const results = q === "apple" ? [{ ticker: "AAPL", name: "Apple Inc.", exchange: "Nasdaq" }] : [];
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ results }) });
  });
  await page.goto("/v2");
  const box = page.getByRole("combobox").first();
  await box.fill("apple");
  await expect(page.getByRole("option", { name: /Apple Inc\./ })).toBeVisible();
  await box.press("ArrowDown");
  await expect(page.getByRole("option", { name: /Apple Inc\./ })).toHaveAttribute("aria-selected", "true");
  await box.press("End");
  await box.pressSequentially(" corp");          // ya no es «apple»: la lista vieja se oculta y nada queda marcado
  await expect(page.getByRole("listbox")).toHaveCount(0);
  await expect(box).not.toHaveAttribute("aria-activedescendant", /.+/);
  await box.press("Enter");
  await page.waitForTimeout(500);
  await expect(page).toHaveURL(/\/v2\/?$/);       // no fue a AAPL
});

// F15 · datos raros: el análisis y la serie con huecos, fechas rotas y listas vacías no tumban ninguna página (ni el
// límite de error de /v2): cada bloque dice que le falta el dato.
const PAGES = ["", "empresa", "negocio", "accion", "calidad", "valor", "rivales", "riesgos", "actualidad", "conclusion"];
type Json = Record<string, unknown>;
function mangle(a: Json): Json {
  const d = a.display as Json;
  const ext = (d.extended ?? {}) as Json;
  ext.news = [{ date: "no-es-fecha", source: null, headline: "Sin fecha", url: "javascript:alert(1)", image: null },
    { date: null, source: "X", headline: "Sin nada", url: null }];
  ext.history_10y = { status: "ok", rows: [], currency: null, source: null };
  ext.next_earnings = { status: "ok", date: "2026-99-99", date_txt: null, kind: null };
  d.extended = ext;
  const sec = d.sections as Json;
  (sec.valuation as Json).rows = [];
  (sec.valuation as Json).reverse_dcf = null;
  (sec.solvency as Json).rows = [];
  (sec.growth as Json).range52 = null;
  const charts = d.charts as Json;
  (charts.comparison as Json).rows = [];
  return a;
}
for (const mode of ["serie-vacia", "fechas-rotas", "listas-vacias"] as const) {
  test(`F15 · datos raros (${mode}): ninguna página se cae`, async ({ page }, info) => {
    desktopOnly(info.project.name);
    test.setTimeout(180_000);
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(String(e)));
    page.on("console", (m) => { if (m.type() === "warning" && m.text().startsWith("v2:")) errors.push(m.text().slice(0, 300)); });
    await page.route("**/api/analysis/AAPL", async (route) => {
      const res = await route.fetch();
      return route.fulfill({ response: res, json: mangle(await res.json()) });
    });
    if (mode === "listas-vacias") {
      await page.route("**/api/analysis/AAPL", async (route) => {
        const res = await route.fetch();
        const a = mangle(await res.json());
        const d = a.display as Json;
        (d.cover as Json).kpis = [];
        (d.cover as Json).highlights = [];
        d.tooltips = {};
        const market = (d.sections as Json).market as Json | null;
        if (market) market.rows = [];
        return route.fulfill({ response: res, json: a });
      });
      await page.route("**/api/v2/segments/AAPL", (route) => route.fulfill({ json: { status: "ok", fiscal_years: [], axes: [], segments: [], rows: [] } }));
      await page.route("**/api/v2/peers/AAPL**", (route) => route.fulfill({ json: { status: "listo", symbol: "AAPL", max_symbols: 6, poll_s: 3,
        company: null, rivals: [{ symbol: "MSFT", status: "listo", summary: null }, { symbol: "X", status: "raro" }] } }));
    }
    await page.route("**/api/v2/prices/AAPL**", async (route) => {
      const res = await route.fetch();
      const p = await res.json();
      if (mode === "serie-vacia") {
        p.company = { ...p.company, status: "ok", points: [], events: [], returns: {} };
        p.chart = {};
      } else {
        p.company.points = p.company.points.map((x: Json, i: number) => (i % 50 === 0 ? { ...x, t: "nunca" } : x));
        p.company.events = [{ t: "nunca", kind: "dividend", value: null, label: "roto" }];
        p.chart = { "1A": { status: "ok", covered: true, start: null, end: null, reason: null, series: { company: { i0: 99999, values: [100] } }, marks: [{ t: "nunca", kind: "split", label: "x" }] } };
      }
      return route.fulfill({ response: res, json: p });
    });
    for (const pg of PAGES) {
      await page.goto(`/v2/AAPL${pg ? `/${pg}` : ""}`);
      await page.waitForSelector(".depth-body .dsec, [data-testid=v2-error]", { timeout: 30_000 });
      await page.waitForTimeout(800);
      await expect(page.getByTestId("v2-error"), `${pg || "empresa"}: límite de error · ${errors.join(" | ")}`).toHaveCount(0);
    }
    expect(errors).toEqual([]);
  });
}

test("F16 · portada: con la pestaña oculta no sondea; al volver sigue, y los fallos esperan cada vez más", async ({ page }, info) => {
  desktopOnly(info.project.name);
  test.setTimeout(120_000);
  const at: number[] = [];
  await page.route("**/api/v2/trending*", (route) => { at.push(Date.now()); return route.fulfill({ status: 503, body: "" }); });
  await page.clock.install();
  await page.goto("/v2");
  await expect.poll(() => at.length).toBe(1);
  await page.clock.runFor(5_100);                 // 1.er reintento: 5 s
  await expect.poll(() => at.length).toBe(2);
  await page.clock.runFor(9_000);                 // el 2.º espera 10 s: aún no
  expect(at.length).toBe(2);
  await page.clock.runFor(1_200);
  await expect.poll(() => at.length).toBe(3);
  // Pestaña oculta: pasa el plazo del 3.er reintento (20 s) y no pregunta; al volver, sí
  await page.evaluate(() => {
    Object.defineProperty(document, "hidden", { configurable: true, get: () => true });
    document.dispatchEvent(new Event("visibilitychange"));
  });
  await page.clock.runFor(25_000);
  expect(at.length).toBe(3);
  await page.evaluate(() => {
    Object.defineProperty(document, "hidden", { configurable: true, get: () => false });
    document.dispatchEvent(new Event("visibilitychange"));
  });
  await expect.poll(() => at.length).toBe(4);
});

test("F17 · escenario: el color de cada celda y su leyenda vienen del motor, y un 422 enseña su motivo", async ({ page }, info) => {
  desktopOnly(info.project.name);
  let reply422 = false;
  let bands: Array<Array<number | null>> = [];
  await page.route("**/api/v2/scenario", async (route) => {
    if (reply422) return route.fulfill({ status: 422, contentType: "application/json", body: JSON.stringify({ detail: "el crecimiento a largo plazo debe quedar por debajo del coste del capital" }) });
    const res = await route.fetch();
    const body = await res.json();
    bands = body.sensitivity.bands;
    return route.fulfill({ response: res, json: body });
  });
  await page.goto("/v2/AAPL/valor");
  const table = page.getByTestId("scenario-sensitivity");
  await expect(table).toBeVisible({ timeout: 30_000 });
  const TONES = ["good", "good", "neutral", "warn", "bad"];
  const classes = await table.locator("tbody td").evaluateAll((tds) => tds.map((td) => td.className));
  expect(classes).toEqual(bands.flat().map((b) => `num band-${b == null ? "none" : TONES[b]}`));
  await expect(page.getByTestId("scenario").locator(".legend span")).toHaveCount(5);
  reply422 = true;
  await page.getByRole("button", { name: "Optimista" }).click();
  await expect(page.getByTestId("scenario")).toContainText("el crecimiento a largo plazo debe quedar por debajo del coste del capital");
  await expect(page.getByTestId("scenario")).not.toContainText(/HTTP|422/);
});

test("F25 · botón de tema sin parpadeo: en oscuro, el primer fotograma ya dice «Modo claro»", async ({ page }, info) => {
  desktopOnly(info.project.name);
  await page.addInitScript(() => {
    localStorage.setItem("finanzer.v2.theme", "dark");
    const w = window as unknown as { __labels?: string[] };
    w.__labels = [];
    const seen = () => {
      const b = [...document.querySelectorAll<HTMLButtonElement>("header button")].find((x) => /Modo/.test(x.textContent ?? ""));
      const txt = b?.innerText.trim();
      if (txt && w.__labels![w.__labels!.length - 1] !== txt) w.__labels!.push(txt);
    };
    new MutationObserver(seen).observe(document, { childList: true, subtree: true, characterData: true, attributes: true });
    document.addEventListener("DOMContentLoaded", seen);
  });
  await page.goto("/v2/AAPL");
  await page.waitForSelector(".depth-body .dsec", { timeout: 30_000 });
  const labels = await page.evaluate(() => (window as unknown as { __labels: string[] }).__labels);
  expect(labels).toEqual(["Modo claro"]);
  await page.getByRole("button", { name: "Modo claro" }).click();
  await expect(page.getByRole("button", { name: "Modo oscuro" })).toBeVisible();
});

test("F12 · la serie de precios se pide una vez al volver a «La acción» (caché del módulo)", async ({ page }, info) => {
  desktopOnly(info.project.name);
  const asked: string[] = [];
  page.on("request", (r) => { if (r.url().includes("/api/v2/prices/")) asked.push(r.url()); });
  await page.goto("/v2/AAPL/accion");
  await page.waitForSelector("[data-testid=price-chart-full] canvas", { timeout: 30_000 });
  const tabs = page.locator("nav.chapterbar");
  await tabs.getByRole("link", { name: "Calidad", exact: true }).click();
  await page.waitForSelector(".depth[data-chapter=calidad] .depth-body .dsec", { timeout: 30_000 });
  await tabs.getByRole("link", { name: "La acción", exact: true }).click();
  await page.waitForSelector("[data-testid=price-chart-full] canvas", { timeout: 30_000 });
  expect(asked).toHaveLength(1);
});

test("F13 · cada sección pinta con su código: Calidad no espera a la gráfica ni a las demás, que llegan después (V4b · 3)", async ({ page }, info) => {
  desktopOnly(info.project.name);
  test.skip(process.env.E2E_BUILD === "1", "en el build los fragmentos llevan hash: se comprueba con next dev (nombre del módulo)");
  // el instante en que se pinta el detalle de la sección
  await page.addInitScript(() => {
    new MutationObserver((_, mo) => {
      if (document.querySelector(".depth-body .dsec")) { (window as unknown as { __painted: number }).__painted = performance.now(); mo.disconnect(); }
    }).observe(document, { childList: true, subtree: true });
  });
  await page.goto("/v2/AAPL/calidad");
  await page.waitForSelector(".depth-body .dsec", { timeout: 30_000 });
  await page.waitForLoadState("networkidle");
  const scripts = await page.evaluate(() => {
    const at = (window as unknown as { __painted: number }).__painted;
    const all = performance.getEntriesByType("resource").filter((e) => (e as PerformanceResourceTiming).initiatorType === "script");
    return { before: all.filter((e) => e.startTime < at).map((e) => e.name).join(" "), after: all.filter((e) => e.startTime >= at).map((e) => e.name).join(" ") };
  });
  expect(scripts.before).toMatch(/pages_Calidad/);
  expect(scripts.before).not.toMatch(/PriceChartFull|pages_Accion|pages_Rivales|pages_Valor/);
  // V4b · 3: con la sección pintada, las demás y sus gráficas se descargan en un momento libre (cambiar de pestaña no
  // espera a la red ni a Suspense)
  await expect.poll(async () => page.evaluate(() => performance.getEntriesByType("resource").map((e) => e.name).join(" ")), { timeout: 15_000 })
    .toMatch(/pages_Accion[^ ]*[\s\S]*|PriceChartFull/);
  const later = await page.evaluate(() => performance.getEntriesByType("resource").map((e) => e.name).join(" "));
  for (const m of ["pages_Accion", "pages_Rivales", "pages_Valor", "PriceChartFull"]) expect(later).toContain(m);
});
test("F21 · periodos: un grupo de botones con aria-pressed (sin tablist a medias)", async ({ page }, info) => {
  desktopOnly(info.project.name);
  await page.goto("/v2/AAPL/accion");
  const group = page.getByRole("group", { name: "Periodo" });
  await expect(group).toBeVisible({ timeout: 30_000 });
  await expect(page.getByRole("tablist")).toHaveCount(0);
  await expect(group.getByRole("button", { name: "1A", pressed: true })).toBeVisible();
  await group.getByRole("button", { name: "5A" }).click();
  await expect(group.getByRole("button", { name: "5A", pressed: true })).toBeVisible();
  await expect(group.getByRole("button", { name: "1A", pressed: false })).toBeVisible();
});

test("F24 · noticia: imagen decorativa, aviso de pestaña nueva y, sin enlace válido, un <article>", async ({ page }, info) => {
  desktopOnly(info.project.name);
  await page.route("**/api/analysis/AAPL", async (route) => {
    const res = await route.fetch();
    const a = await res.json();
    a.display.extended = { ...(a.display.extended ?? {}), news: [
      { date: "2026-10-14", source: "Reuters", headline: "Con enlace", url: "https://www.reuters.com/x", image: "https://example.com/i.jpg", summary: "s" },
      { date: "2026-10-13", source: "Rara", headline: "Enlace malo", url: "javascript:alert(1)", image: null, summary: "s" }] };
    return route.fulfill({ response: res, json: a });
  });
  await page.route("https://example.com/**", (route) => route.abort());
  await page.goto("/v2/AAPL/actualidad");
  const good = page.locator("a.news-card", { hasText: "Con enlace" });
  await expect(good).toHaveAttribute("href", "https://www.reuters.com/x", { timeout: 30_000 });
  await expect(good).toHaveAttribute("target", "_blank");
  await expect(good.locator(".sr-only")).toHaveText("(se abre en una pestaña nueva)");
  await expect(good.locator("img")).toHaveAttribute("alt", "");
  const bad = page.locator(".news-card", { hasText: "Enlace malo" });
  expect(await bad.evaluate((e) => e.tagName)).toBe("ARTICLE");
  await expect(page.locator("a[href^='javascript:']")).toHaveCount(0);
});

test("F6 · si una página no sabe pintar los datos, el límite de error de /v2 lo dice con «Reintentar» y la portada", async ({ page }, info) => {
  desktopOnly(info.project.name);
  await page.route("**/api/analysis/AAPL", async (route) => {
    const res = await route.fetch();
    const a = await res.json();
    a.display.sections = null;                       // ninguna página puede pintar sin secciones
    return route.fulfill({ response: res, json: a });
  });
  await page.goto("/v2/AAPL/calidad");
  const box = page.getByTestId("v2-error");
  await expect(box).toBeVisible({ timeout: 30_000 });
  await expect(box.getByRole("heading")).toHaveText("Algo falló al mostrar esta página");
  await expect(box.getByRole("button", { name: "Reintentar" })).toBeVisible();
  await expect(box.getByRole("link", { name: "Volver a la portada" })).toHaveAttribute("href", /^\/v2\/?$/);
});

// Prueba V2 (fuentes reales): «Descargar PDF» solo con un análisis válido cargado. SPY es un ETF (422), ZZZZZ no existe
// (404) y SIVB está deslistada (404 con el motivo del backend; el replay no la tiene, se simula su respuesta).
for (const [sym, status, detail] of [["SPY", 0, ""], ["ZZZZZ", 0, ""],
  ["SIVB", 404, "No se encontraron datos de SIVB: puede que haya dejado de cotizar."]] as const) {
  test(`sin análisis no hay «Descargar PDF» · ${sym}`, async ({ page }, info) => {
    desktopOnly(info.project.name);
    if (status) await page.route(`**/api/analysis/${sym}`, (route) =>
      route.fulfill({ status, contentType: "application/json", body: JSON.stringify({ detail }) }));
    await page.goto(`/v2/${sym}`);
    await expect(page.getByTestId("load-error").getByRole("alert")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByRole("link", { name: "Descargar PDF" })).toHaveCount(0);
  });
}

test("«Descargar PDF» no sale mientras carga y sí con el análisis (AAPL)", async ({ page }, info) => {
  desktopOnly(info.project.name);
  let release: () => void = () => {};
  const gate = new Promise<void>((r) => { release = r; });
  await page.route("**/api/analysis/AAPL", async (route) => { await gate; return route.continue(); });
  await page.goto("/v2/AAPL");
  await expect(page.getByTestId("analyze-loading")).toBeVisible();      // V4: la pantalla de carga
  await expect(page.getByRole("link", { name: "Descargar PDF" })).toHaveCount(0);
  release();
  await page.waitForSelector(".depth-body .dsec", { timeout: 30_000 });
  await expect(page.getByRole("link", { name: "Descargar PDF" })).toHaveAttribute("href", /\/api\/v2\/pdf\/AAPL$/);
});
