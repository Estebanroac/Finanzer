import { test, expect } from "@playwright/test";

/** V7 (nombres en español): la cabecera y la ficha usan el sector y la industria en español, en la web actual y en
 *  /v2 (display.profile, backend/lib/names.py). KO decía «opera en Beverages—Non-Alcoholic (Consumer Defensive)». */
test("sector e industria en español · KO", async ({ page }, info) => {
  test.skip(info.project.name !== "desktop", "el texto es el mismo en móvil");
  await page.goto("/v2/KO");
  await page.waitForSelector(".depth-body .dsec", { timeout: 60_000 });
  await expect(page.getByRole("region", { name: "Resumen de la empresa" })).toContainText("Consumo defensivo · Bebidas sin alcohol");
  await expect(page.locator("body")).toContainText("opera en bebidas sin alcohol (consumo defensivo)");
  await expect(page.locator("body")).not.toContainText("Non-Alcoholic");
  await expect(page.locator("body")).not.toContainText("Consumer Defensive");
  await page.goto("/stock/KO");
  await expect(page.locator("body")).toContainText("Consumo defensivo · Bebidas sin alcohol", { timeout: 60_000 });
  await expect(page.locator("body")).not.toContainText("Consumer Defensive");
});
