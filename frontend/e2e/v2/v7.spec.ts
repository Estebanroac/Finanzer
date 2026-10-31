import { test, expect } from "@playwright/test";

// V7 · lectura de un usuario nuevo (presentación, P1–P6): cada arreglo con su prueba en el navegador.
const desktopOnly = (name: string) => test.skip(name !== "desktop", "el comportamiento no depende del tamaño");

test("P6 · buscar por nombre y pulsar Enter abre el primer resultado", async ({ page }, info) => {
  desktopOnly(info.project.name);
  await page.goto("/v2");
  const box = page.getByRole("combobox").first();
  await box.fill("apple");
  await expect(page.getByRole("option").first()).toBeVisible({ timeout: 30_000 });
  const first = await page.getByRole("option").first().locator(".r-meta").textContent();
  await box.press("Enter");
  await expect(page).toHaveURL(new RegExp(`/v2/${(first ?? "").split(" ")[0].replace(".", "\\.")}/?$`));
});

test("P6 · la sección Conclusión descarga el PDF (V4b: es la última, sin «Siguiente sección»)", async ({ page }, info) => {
  desktopOnly(info.project.name);
  await page.goto("/v2/AAPL/conclusion");
  const pdf = page.getByTestId("pdf");
  await expect(pdf).toHaveAttribute("href", /\/api\/v2\/pdf\/AAPL$/, { timeout: 30_000 });
  await expect(pdf).not.toHaveAttribute("data-nav", /.*/);
  await expect(page.getByTestId("next-section")).toHaveCount(0);
});

test("P6 · la cabecera fija (compacta, al bajar) mide menos del 60 % de la completa (también en móvil)", async ({ page }, info) => {
  test.skip(!["desktop", "mobile"].includes(info.project.name), "escritorio y móvil");
  await page.goto("/v2/AAPL/calidad");
  await page.waitForSelector(".depth-body .dsec", { timeout: 30_000 });
  const full = await page.locator(".company-header:not(.compact)").evaluate((e) => e.getBoundingClientRect().height);
  await page.evaluate(() => window.scrollTo(0, 3000));
  const head = page.locator(".stuck-head .company-header.compact");
  await expect(head).toBeVisible();
  const compact = await head.evaluate((e) => e.getBoundingClientRect().height);
  console.log(`cabecera ${info.project.name}: completa ${Math.round(full)} px, fija ${Math.round(compact)} px`);
  expect(compact).toBeLessThan(full * 0.6);
});

test("P5 · Rivales: la lectura con «agregado» y la mejor y la peor métrica, y el comparador debajo", async ({ page }, info) => {
  desktopOnly(info.project.name);
  // F10 · N2: AAPL es el 91 % de su industria y su referencia es la mediana de sus pares; el agregado, con JPM
  await page.goto("/v2/JPM/rivales");
  const intro = page.getByTestId("section-intro");
  await expect(intro.locator("h2")).toHaveText("Frente a sus rivales", { timeout: 30_000 });
  await expect(intro.locator(".lead")).toContainText("agregado");
  await expect(intro.locator(".lead")).not.toContainText("mediana");
  await expect(intro.locator(".figures")).toContainText(/Mejor · [^]*Peor · /);
  await expect(page.locator("#comparador").getByTestId("peers")).toBeVisible();
});

test("P5 · un P/E fuera de rango sale «n. s.» con su motivo en el comparador", async ({ page }, info) => {
  desktopOnly(info.project.name);
  const crwd = await (await page.request.get(`http://localhost:${process.env.REPLAY_PORT || 8767}/api/analysis/CRWD`)).json();
  const pe = crwd.display.charts.comparison.groups.flatMap((g: { items: Array<{ key: string; value_txt: string }> }) => g.items).find((i: { key: string }) => i.key === "pe");
  await page.route("**/api/v2/peers/SNOW**", async (route) => route.fulfill({ json: {
    status: "listo", symbol: "SNOW", source: "elegidos", max_symbols: 5, poll_s: 4, industry: "Software (System & Application)", note: null, company: null,
    rivals: [{ symbol: "CRWD", status: "listo", summary: { symbol: "CRWD", name: "CrowdStrike", price: 1, currency: "USD", confidence: "media",
      quality: { score: 60, level: "media" }, price_score: { score: 10, level: "muy exigente" }, reference: null,
      metrics: { pe: { value: 4366.3, value_txt: "n. s.", note: `P/E de ${pe.value_txt}: con un beneficio casi nulo no es significativo (por encima de 200x)` } } } }] } }));
  await page.goto("/v2/SNOW/rivales");
  const cell = page.locator("[data-testid=peers] tr[data-status=listo] td[data-label='P/E']");
  await expect(cell).toContainText("n. s.", { timeout: 30_000 });
  // V4b (nada oculto): el motivo, a la vista bajo la cifra (antes, al pasar el ratón)
  await expect(cell.locator(".metric-note")).toBeVisible();
  await expect(cell.locator(".metric-note")).toContainText(/4366\.35x: con un beneficio casi nulo no es significativo/);
});

test("P2 · «Banderas rojas del modelo: 0» en lugar de «Riesgos 0» (lectura y detalle de Riesgos)", async ({ page }, info) => {
  desktopOnly(info.project.name);
  // F8 · E8: AAPL tiene ya una bandera roja (su DCF puntúa con fiabilidad alta); JPM no tiene ninguna
  await page.goto("/v2/JPM/riesgos");
  const figs = page.getByTestId("section-intro").locator(".figures");
  await expect(figs).toContainText("Banderas rojas del modelo", { timeout: 30_000 });
  await expect(figs).not.toContainText(/^Riesgos/i);
  await expect(page.locator("#alertas")).toContainText("Banderas rojas del modelo: 0", { timeout: 30_000 });
  await expect(page.locator("#alertas")).toContainText("no quiere decir que no haya riesgos");
});

test("P2 · Concentración: el mayor segmento y la geografía que cae, como hechos, enlazados a Negocio", async ({ page }, info) => {
  desktopOnly(info.project.name);
  await page.goto("/v2/AAPL/riesgos");
  const box = page.getByTestId("concentration");
  await expect(box.getByTestId("concentration-top")).toHaveText("iPhone: 50% de los ingresos", { timeout: 30_000 });
  await expect(box.getByTestId("concentration-falling")).toHaveText("China −3.8% (zonas geográficas)");
  await expect(box).toContainText("FY2024 → FY2025");
  const link = box.getByRole("link", { name: "Ver los ingresos por segmento →" });
  await expect(link).toHaveAttribute("href", "/v2/AAPL/negocio#segmentos");
  // con cobertura parcial se dice (BCS: solo comisiones)
  await page.goto("/v2/BCS/riesgos");
  await expect(page.getByTestId("concentration")).toContainText("cubren el 38%", { timeout: 30_000 });
});

test("P4 · Cómo gana dinero: la lectura sale de los segmentos (producto y geografía), con su detalle debajo", async ({ page }, info) => {
  desktopOnly(info.project.name);
  await page.goto("/v2/AAPL/negocio");
  await expect(page.getByTestId("section-intro").getByTestId("segments-lead")).toHaveText(
    "En FY2025, iPhone aporta el 50% de sus ingresos, seguido de Service (26%) y Wearables, Home and Accessories (8.6%). " +
    "Por zonas geográficas: Other Countries 48%, United States 36%, China 15%.", { timeout: 30_000 });
  await expect(page.locator("#segmentos")).toContainText("iPhone");
  await expect(page.locator(".depth")).not.toContainText("DuPont");
});

test("P4 · sin segmentos, la lectura de Cómo gana dinero vuelve a la de rentabilidad", async ({ page }, info) => {
  desktopOnly(info.project.name);
  await page.route("**/api/v2/segments/AAPL**", (route) => route.fulfill({ json: {
    symbol: "AAPL", status: "sin_dato", segments: [], reason: "el emisor no publica segmentos" } }));
  await page.goto("/v2/AAPL/negocio");
  const lead = page.getByTestId("segments-lead");
  await expect(lead).toBeVisible({ timeout: 30_000 });
  await expect(lead).not.toContainText("aporta el", { timeout: 15_000 });
  await expect(lead).not.toBeEmpty();
});

test("P4 · el DuPont está en Calidad y no se repite en Negocio", async ({ page }, info) => {
  desktopOnly(info.project.name);
  await page.goto("/v2/AAPL/calidad");
  await expect(page.locator("h4", { hasText: "DuPont del ROE" })).toBeVisible({ timeout: 30_000 });
  await page.goto("/v2/AAPL/negocio");
  await expect(page.locator("h4", { hasText: "Margen FCF con tendencia" })).toBeVisible({ timeout: 30_000 });
  await expect(page.locator("h4", { hasText: "DuPont" })).toHaveCount(0);
});

test("P3 · «?» en las etiquetas del desglose de las puntuaciones («La empresa»), también en el móvil (V4b: a la vista)", async ({ page }, info) => {
  test.skip(!["desktop", "mobile"].includes(info.project.name), "escritorio y móvil");
  await page.goto("/v2/AAPL");
  await expect(page.getByTestId("desglose-quality")).toBeVisible({ timeout: 30_000 });
  // F8 · E8: en AAPL puntúa el DCF directo; el «?» del DCF inverso se prueba en DOW, al final
  for (const key of ["cat_solidez", "cat_calidad_ganancias", "multiples_block", "conf_convergence", "conf_stability"])
    await expect(page.locator(`#desglose [data-tip="${key}"]`)).toHaveCount(1);
  await page.locator('#desglose [data-tip="cat_calidad_ganancias"]').click();
  const box = page.locator(".tip-box:not([data-state=closed])");     // en un portal (Floating, V7): fuera de la cabecera
  await expect(box).toContainText("si el beneficio contable se convierte en caja");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.keyboard.press("Escape");
  await expect(box).toHaveCount(0);
  await page.goto("/v2/DOW");
  await expect(page.locator('#desglose [data-tip="reverse_dcf"]')).toHaveCount(1, { timeout: 30_000 });
});
test("P3 · «?» en las cifras de La acción y en el ETF del sector (XLK) de la rentabilidad por periodo", async ({ page }, info) => {
  desktopOnly(info.project.name);
  await page.goto("/v2/AAPL/accion");
  const intro = page.getByTestId("section-intro");
  for (const key of ["momentum", "trend", "pos52"])
    await expect(intro.locator(`.figures [data-tip="${key}"]`)).toHaveCount(1, { timeout: 30_000 });
  await intro.locator('.figures [data-tip="momentum"]').click();
  await expect(page.locator(".tip-box:not([data-state=closed])")).toContainText("sin contar el último mes");   // portal (Floating)
  await page.keyboard.press("Escape");
  const etf = page.getByTestId("returns-by-period").locator('[data-tip="sector_etf"]');
  await expect(etf).toHaveAccessibleName("Qué es XLK (ETF del sector)", { timeout: 30_000 });
  await etf.click();
  const box = page.locator(".tip-box:not([data-state=closed])");
  await expect(box).toContainText("XLK, tecnología");
  // el popover no se sale por la derecha
  const r = await box.boundingBox();
  expect((r?.x ?? 0) + (r?.width ?? 0)).toBeLessThanOrEqual(1440);
});

test("P1 · «?» en las tres puntuaciones (cabecera completa y compacta), sin abrir la tarjeta en el móvil", async ({ page }, info) => {
  test.skip(!["desktop", "mobile"].includes(info.project.name), "escritorio y móvil");
  await page.goto("/v2/AAPL");
  for (const [id, key] of [["score-quality", "quality"], ["score-price", "price"], ["confidence", "confidence"]] as const)
    await expect(page.getByTestId(id).locator(`.eyebrow [data-tip="${key}"]`)).toHaveCount(1, { timeout: 30_000 });
  await page.getByTestId("confidence").locator('.eyebrow [data-tip="confidence"]').click();
  await expect(page.getByRole("dialog", { name: "Confianza del veredicto" })).toContainText("cuánto fiarse del veredicto");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.keyboard.press("Escape");
});

test("P1 · la línea bajo «Confianza del veredicto»: la de la página Conclusión, en la tarjeta", async ({ page }, info) => {
  desktopOnly(info.project.name);
  // F8 · E8: el caso del DCF directo descartado es DOW (antes, AAPL); la línea puede empezar por lo que contrae
  await page.goto("/v2/DOW");
  const line = page.getByTestId("desglose-confidence-line");
  await expect(line).toHaveText(/El DCF directo, de fiabilidad baja, no puntúa ni cuenta para la convergencia/, { timeout: 30_000 });
  const txt = (await line.textContent())!;
  await page.goto("/v2/DOW/conclusion");
  await expect(page.locator("#confianza")).toContainText(txt, { timeout: 30_000 });
});
