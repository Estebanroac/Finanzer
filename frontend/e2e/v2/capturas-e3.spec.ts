import { test } from "@playwright/test";
import { captureElement } from "./capture";

// Capturas de la etapa E3, solo con CAPTURE_E3=1: a test-results/capturas; se versionan comprimidas con
// `npm run capturas:etapa -- e3 e3-` (docs/rediseno/capturas-e3): por página, AAPL, JPM, O y BCS en
// claro escritorio y oscuro móvil; los 8 tickers en Cuánto vale y Rivales. WebP comprimido (≤ 300 KB) para no inflar el repo.
const CHAPTERS = ["empresa", "negocio", "accion", "calidad", "valor", "rivales", "riesgos", "actualidad", "conclusion"];
const BASE = ["AAPL", "JPM", "O", "BCS"];
const ALL = ["AAPL", "JPM", "O", "NEE", "XOM", "PLTR", "RIVN", "BCS"];
const RUN = !!process.env.CAPTURE_E3;

for (const ch of CHAPTERS) {
  for (const t of ["valor", "rivales"].includes(ch) ? ALL : BASE) {
    test(`captura E3 · ${ch} · ${t}`, async ({ page }, info) => {
      test.skip(!RUN, "solo con CAPTURE_E3=1");
      const theme = info.project.name === "desktop" ? "light" : "dark";
      await page.addInitScript((th) => localStorage.setItem("finanzer.v2.theme", th), theme);
      await page.goto(`/v2/${t}/${ch}`);
      await page.waitForSelector(".depth-body .dsec", { timeout: 30_000 });
      await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => {});
      // Barras fijas en su sitio: si no, la captura de un elemento alto las repite en mitad de la imagen
      await page.addStyleTag({ content: "nextjs-portal { display: none !important; } .chapterbar, .pillindex, .topbar { position: static !important; }" });
      await page.waitForTimeout(1200);
      await captureElement(page, ".depth", `e3-${ch}-${t}-${theme}-${info.project.name}`);
    });
  }
}
