import { test, expect } from "@playwright/test";

/** PDF rápido: el primer PDF de una empresa espera a sus comparables. El botón no debe parecer colgado: dice que se
 *  está preparando y por qué, la página sigue respondiendo y la descarga sale sola al terminar. */
test("Descargar PDF: «Preparando el PDF…» con su motivo, sin bloquear la página, y la descarga al llegar", async ({ page }) => {
  let release: () => void = () => {};
  const held = new Promise<void>((r) => { release = r; });
  await page.route("**/api/v2/pdf/**", async (r) => { await held; await r.fallback(); });
  await page.goto("/v2/AAPL/conclusion");
  const btn = page.getByTestId("pdf");
  await expect(btn).toHaveText("Descargar PDF", { timeout: 30_000 });
  await btn.click();
  await expect(btn).toHaveText("Preparando el PDF…");
  await expect(btn).toHaveAttribute("aria-busy", "true");
  const status = page.getByTestId("pdf-status");
  await expect(status).toBeVisible();
  await expect(status).toHaveText("Preparando el PDF de AAPL: espera a que estén las comparables de su industria. Se descargará solo.");
  await expect(status).toHaveAttribute("aria-live", "polite");
  expect(await status.evaluate((e) => parseFloat(getComputedStyle(e).fontSize))).toBeGreaterThanOrEqual(12);
  // la página no se bloquea: otra pulsación del mismo botón no pide otro PDF y el resto responde
  await btn.click();
  await page.locator(".topbar .btn[aria-pressed]").click();
  await expect(page.locator("html")).toHaveAttribute("data-v2theme", /dark|light/);
  const download = page.waitForEvent("download");
  release();
  const file = await download;
  expect(file.suggestedFilename()).toMatch(/^Informe Finanzer AAPL .*\.pdf$/);
  await expect(btn).toHaveText("Descargar PDF");
  await expect(btn).not.toHaveAttribute("aria-busy", /.*/);
  await expect(status).toHaveText("");                       // la región sigue en el DOM (aria-live), vacía y sin mostrar
  await expect(status).not.toHaveClass(/\bon\b/);
});

test("Descargar PDF: si falla, lo dice con su motivo y se puede volver a intentar", async ({ page }) => {
  await page.route("**/api/v2/pdf/**", (r) => r.fulfill({ status: 503, body: "" }));
  await page.goto("/v2/AAPL/conclusion");
  const btn = page.getByTestId("pdf");
  await expect(btn).toHaveText("Descargar PDF", { timeout: 30_000 });
  await btn.click();
  const status = page.getByTestId("pdf-status");
  await expect(status).toHaveText("No se pudo preparar el PDF de AAPL (HTTP 503). Vuelve a intentarlo.");
  await expect(status).toBeVisible();
  await expect(btn).toHaveText("Descargar PDF");
  await expect(btn).toHaveAttribute("href", /\/api\/v2\/pdf\/AAPL$/);      // sigue siendo el enlace al PDF
});
