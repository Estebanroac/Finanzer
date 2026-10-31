import { test } from "@playwright/test";
import { capture } from "./capture";
import { openSection, SECTIONS } from "./checks";

const TICKERS = ["AAPL", "JPM", "O", "NEE", "XOM", "PLTR", "RIVN", "BCS"];

for (const t of TICKERS) {
  for (const theme of ["light", "dark"] as const) {
    test(`captura ${t} · ${theme}`, async ({ page }, info) => {
      await page.addInitScript((th) => localStorage.setItem("finanzer.v2.theme", th), theme);
      test.setTimeout(240_000);
      // V4b: las nueve secciones de AAPL; de los demás, la primera y la de la gráfica
      for (const s of t === "AAPL" ? SECTIONS : (["empresa", "accion"] as const)) {
        await openSection(page, t, s);
        await page.waitForTimeout(500);
        await capture(page, `${t}-${s}-${theme}-${info.project.name}`);
      }
    });
  }
}
