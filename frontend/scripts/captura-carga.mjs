// Capturas de la carga del análisis (V4, encargo del PM): el estado de error y la pantalla de carga.
//   node scripts/captura-carga.mjs <directorio> [base]
// Escribe V4_carga_error.png (escritorio, 404 del replay con HD) y, si la pantalla de carga existe, V4_carga_*.png.
import { chromium, devices } from "@playwright/test";
const [dir, base = "http://localhost:3001"] = process.argv.slice(2);
const browser = await chromium.launch();

async function shot(name, ctxOpts, prep) {
  const ctx = await browser.newContext(ctxOpts);
  const page = await ctx.newPage();
  await prep(page);
  await page.screenshot({ path: `${dir}/${name}.png` });
  await ctx.close();
}

await shot("V4_carga_error", { viewport: { width: 1440, height: 900 } }, async (page) => {
  await page.goto(`${base}/v2/HD/`);
  await page.getByTestId("load-error").waitFor({ timeout: 60_000 });
  await page.waitForTimeout(300);
});

// La pantalla de carga: la petición del análisis se retiene para fotografiarla a mitad de camino.
const hold = async (page, theme) => {
  await page.route("**/api/analysis/AAPL", () => new Promise(() => {}));
  if (theme) await page.addInitScript((t) => localStorage.setItem("finanzer.v2.theme", t), theme);
  await page.goto(`${base}/v2/AAPL`);
  await page.locator("[data-testid=analyze-loading]").waitFor({ timeout: 60_000 }).catch(() => {});
  // en la cuarta estación (Valoración), como la maqueta, con su fundido ya terminado
  await page.locator("[data-testid=analyze-loading][data-station='3']").waitFor({ timeout: 10_000 }).catch(() => {});
  await page.waitForTimeout(300);
};
if (process.argv.includes("--loading")) {
  await shot("V4_carga_escritorio", { viewport: { width: 1440, height: 900 } }, (p) => hold(p));
  await shot("V4_carga_oscuro", { viewport: { width: 1440, height: 900 }, colorScheme: "dark" }, (p) => hold(p, "dark"));
  await shot("V4_carga_movil", { ...devices["Pixel 7"] }, (p) => hold(p));
}
await browser.close();
