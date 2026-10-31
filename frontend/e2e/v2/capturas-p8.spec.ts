import { test, expect } from "@playwright/test";
import { capture } from "./capture";

// P8: capturas de la portada con el cintillo (escritorio y móvil, claro y oscuro) para docs/rediseno/capturas-p8
// (`npm run capturas:etapa -- p8 p8-`). Con «reducir movimiento» el cintillo no avanza: la captura es estable.
for (const theme of ["light", "dark"] as const) {
  test(`captura P8 portada · ${theme}`, async ({ page }, info) => {
    test.skip(!["desktop", "mobile"].includes(info.project.name), "escritorio y móvil");
    await page.addInitScript((th) => localStorage.setItem("finanzer.v2.theme", th), theme);
    await page.emulateMedia({ reducedMotion: "reduce" });     // P8b: el cintillo quieto, para una captura estable
    await page.goto("/v2");
    await expect(page.getByTestId("ticker-item")).toHaveCount(30, { timeout: 30_000 });
    await expect(page.getByTestId("ticker-item").getByTestId("spark")).toHaveCount(30, { timeout: 30_000 });
    await expect(page.locator("[data-testid=ticker-item][data-symbol=AAPL] .tk-eng")).toHaveText(/^Calidad /, { timeout: 90_000 });
    await capture(page, `p8-portada-${theme}-${info.project.name}`);
  });
}
