import { test } from "@playwright/test";
import { capture } from "./capture";

// Capturas de E4 (Tasks 3 y 4), solo con CAPTURE_E4=1: a test-results/capturas; se versionan comprimidas con
// `npm run capturas:etapa -- e4 movil-` (docs/rediseno/capturas-e4): tres páginas en el iPhone
// (WebKit) y en la tableta, en claro y oscuro, a pantalla completa.
const PAGES = [["empresa", "/v2/AAPL"], ["calidad", "/v2/AAPL/calidad"], ["valor", "/v2/AAPL/valor"]] as const;

for (const [name, url] of PAGES) {
  for (const theme of ["light", "dark"] as const) {
    test(`captura E4 · ${name} · ${theme}`, async ({ page }, info) => {
      test.skip(!process.env.CAPTURE_E4 || !["mobile-webkit", "tablet"].includes(info.project.name), "solo con CAPTURE_E4=1, iPhone y tableta");
      await page.addInitScript((th) => localStorage.setItem("finanzer.v2.theme", th), theme);
      await page.goto(url);
      await page.waitForSelector(".depth-body .dsec", { timeout: 30_000 });
      await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => {});
      await page.waitForTimeout(1200);
      await capture(page, `movil-${info.project.name}-${name}-${theme}`);
    });
  }
}
