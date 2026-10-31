import { test, expect } from "@playwright/test";

// Rediseño E2a: noticias en tarjetas (sección Actualidad, V4b), en filas completas de la rejilla (de 2 en 2 a dos
// columnas) y todas del mismo alto.
test("AAPL: tarjetas de noticias en filas completas, del mismo alto, con medio, fecha, resumen e idioma", async ({ page }, info) => {
  await page.goto("/v2/AAPL/actualidad");
  const cards = page.locator(".depth .news-card");
  await expect(cards.first()).toBeVisible({ timeout: 30_000 });
  const n = await cards.count();
  expect(n).toBeGreaterThan(0);
  if (info.project.name === "desktop") expect(n % 2).toBe(0);
  // V4b (nada oculto): titular y resumen enteros, así que cada fila mide lo que su tarjeta más larga; dentro de una
  // fila, todas iguales
  const boxes = await cards.evaluateAll((els) => els.map((e) => { const r = e.getBoundingClientRect(); return { top: Math.round(r.top), h: Math.round(r.height) }; }));
  const rows = new Map<number, number[]>();
  for (const b of boxes) rows.set(b.top, [...(rows.get(b.top) ?? []), b.h]);
  for (const hs of rows.values()) expect(Math.max(...hs) - Math.min(...hs)).toBeLessThanOrEqual(1);
  await expect(cards.first().locator(".news-title")).toHaveCSS("-webkit-line-clamp", "none");
  for (let i = 0; i < n; i++) {
    const c = cards.nth(i);
    await expect(c.locator(".eyebrow")).toHaveText(/\d{2}\/\d{2}\/\d{4} · \S/);
    await expect(c.locator(".news-title")).not.toBeEmpty();
    await expect(c.locator(".news-sum")).not.toBeEmpty();
    await expect(c.locator(".news-lang")).toHaveText("En inglés");
    const img = c.locator("img.news-img");
    // Revisión V6 (F24): la imagen es decorativa (alt vacío): el titular ya es el texto de la tarjeta
    if (await img.count()) expect(await img.getAttribute("alt")).toBe("");
  }
  await expect(page.getByTestId("section-intro")).toContainText("Próximos resultados");
});

test("AAPL: variación del día junto al precio y ficha de EDGAR en «La empresa»", async ({ page }) => {
  await page.goto("/v2/AAPL");
  await expect(page.getByTestId("day-change")).toHaveText(/^[+−]\$\d+\.\d{2} \([+−]\d+\.\d{2}%\)$/, { timeout: 30_000 });
  const [p, d] = await Promise.all([page.getByTestId("price").boundingBox(), page.getByTestId("day-change").boundingBox()]);
  expect(Math.abs((p!.y + p!.height) - (d!.y + d!.height))).toBeLessThan(12);   // en la misma línea que el precio
  await expect(page.locator(".depth[data-chapter=empresa]")).toContainText("3571 · Electronic Computers");
  await expect(page.locator(".depth[data-chapter=empresa]")).toContainText("SEC EDGAR");
});
