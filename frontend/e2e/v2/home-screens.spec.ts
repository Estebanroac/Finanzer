import { test, expect } from "@playwright/test";
import { capture } from "./capture";

// Rediseño E4: capturas de la portada (claro y oscuro × escritorio y móvil) para el registro de la etapa.
for (const theme of ["light", "dark"] as const) {
  test(`captura portada · ${theme}`, async ({ page }, info) => {
    await page.addInitScript((th) => localStorage.setItem("finanzer.v2.theme", th), theme);
    await page.goto("/v2");
    // P8: el cintillo con sus 30 valores y sus mini-gráficas.
    await expect(page.getByTestId("ticker-item")).toHaveCount(30, { timeout: 30_000 });
    await expect(page.getByTestId("ticker-item").getByTestId("spark")).toHaveCount(30, { timeout: 30_000 });
    await capture(page, `portada-${theme}-${info.project.name}`);
  });
}
