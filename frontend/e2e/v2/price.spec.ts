import { test, expect } from "@playwright/test";

test("La acción dibuja la gráfica y cambia de periodo", async ({ page }) => {
  await page.goto("/v2/AAPL/accion");
  const chart = page.getByTestId("price-chart-full");
  await expect(chart.locator("canvas").first()).toBeVisible({ timeout: 30_000 });
  // Revisión V6 (F21): los periodos son botones con aria-pressed en un grupo
  await page.getByRole("button", { name: "5A" }).first().click();
  await expect(page.getByRole("button", { name: "5A" }).first()).toHaveAttribute("aria-pressed", "true");
});
