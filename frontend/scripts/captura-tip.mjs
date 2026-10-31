// Captura del «?» de «Crecimiento» en la cabecera de AAPL a 1440 × 900 (V7: el panel frente a la barra de capítulos).
//   node scripts/captura-tip.mjs <salida.png> [base]
import { chromium } from "@playwright/test";
const [out, base = "http://localhost:3001"] = process.argv.slice(2);
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
await page.goto(`${base}/v2/AAPL`);
await page.waitForSelector("[data-testid=score-quality] .mini [data-tip=cat_crecimiento]", { timeout: 60_000 });
await page.waitForTimeout(1500);
await page.locator("[data-testid=score-quality] .mini [data-tip=cat_crecimiento]").click();
await page.waitForTimeout(500);
await page.screenshot({ path: out });
await browser.close();
