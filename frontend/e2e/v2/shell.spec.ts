import { test, expect } from "@playwright/test";

test("la página /v2 de AAPL carga el nombre de la empresa en tema claro", async ({ page }) => {
  await page.goto("/v2/AAPL");
  await expect(page.getByTestId("company-name")).toHaveText("Apple Inc.", { timeout: 30_000 });
  const bg = await page.locator(".fz2").evaluate((el) => getComputedStyle(el).backgroundColor);
  expect(bg).toBe("rgb(247, 246, 242)");
});

test("el conmutador cambia a oscuro", async ({ page }) => {
  await page.goto("/v2/AAPL");
  // E4: con el build, la historia se hidrata un instante después de cargar (su código va aparte del de la portada):
  // se espera a que la página haya pedido y pintado el análisis, señal de que ya responde.
  await expect(page.getByTestId("company-name")).toHaveText("Apple Inc.", { timeout: 30_000 });
  await page.getByRole("button", { name: "Modo oscuro" }).click();
  await expect(page.locator(".fz2")).toHaveAttribute("data-theme", "dark");
});
