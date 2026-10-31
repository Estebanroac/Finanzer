import { test, expect } from "@playwright/test";
import { openSection, symmetryProblems } from "./checks";

const TICKERS = ["AAPL", "JPM", "O", "NEE", "XOM", "PLTR", "RIVN", "BCS"];

// V4b: /v2/{T} abre «La empresa» con la cabecera completa (las tres puntuaciones con su desglose). Las nueve secciones,
// cada una con su simetría, en depth.spec.ts.
for (const t of TICKERS) {
  test(`simetría y escala de espaciado · ${t}`, async ({ page }) => {
    await openSection(page, t);
    await page.waitForTimeout(300);
    expect(await symmetryProblems(page)).toEqual([]);
  });
}
