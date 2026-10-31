import { test, expect } from "@playwright/test";
import { capture } from "./capture";

// P8b: «Bajan más · 6 meses» antes y después de calcular las listas en el periodo elegido (docs/rediseno/capturas-p8,
// `npm run capturas:etapa -- p8 p8b-`). CAPTURA_P8B=antes|despues pone el nombre. Escritorio, claro.
test("captura P8b · Bajan más · 6 meses", async ({ page }, info) => {
  test.skip(info.project.name !== "desktop" || !process.env.CAPTURA_P8B, "solo a mano, en escritorio");
  await page.addInitScript(() => localStorage.setItem("finanzer.v2.theme", "light"));
  await page.emulateMedia({ reducedMotion: "reduce" });       // el cintillo quieto, para una captura estable
  await page.goto("/v2");
  await expect(page.getByTestId("ticker-item")).toHaveCount(30, { timeout: 30_000 });
  await page.getByRole("button", { name: /Bajan más/ }).first().click();
  await page.getByRole("button", { name: "6 meses", exact: true }).click();
  await expect(page.getByTestId("ticker-item").getByTestId("spark")).not.toHaveCount(0, { timeout: 30_000 });
  await page.waitForTimeout(1500);
  await capture(page, `p8b-bajan-6m-${process.env.CAPTURA_P8B}`);
});
