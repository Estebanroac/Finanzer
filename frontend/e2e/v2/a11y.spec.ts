import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { openSection, SECTIONS } from "./checks";

// E2a: los 8 tickers (E1 lo comprobaba en AAPL y, a mano, en los demás), con la gráfica y las tarjetas de noticias ya
// pintadas. V4b: las nueve secciones de cada uno.
const TICKERS = ["AAPL", "JPM", "O", "NEE", "XOM", "PLTR", "RIVN", "BCS"];

for (const t of TICKERS) {
  for (const theme of ["light", "dark"] as const) {
    test(`sin infracciones de accesibilidad graves · ${t} · ${theme}`, async ({ page }) => {
      await page.addInitScript((th) => localStorage.setItem("finanzer.v2.theme", th), theme);
      test.setTimeout(240_000);
      const serious: string[] = [];
      for (const s of SECTIONS) {
        await openSection(page, t, s);
        const res = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
        serious.push(...res.violations.filter((v) => v.impact === "serious" || v.impact === "critical").map((v) => `${s} · ${v.id}: ${v.nodes.length}`));
      }
      expect(serious).toEqual([]);
    });
  }
}
