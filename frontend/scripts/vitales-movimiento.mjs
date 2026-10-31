// v4.1 (movimiento): INP y CLS de laboratorio en los recorridos de navegación interna, para comparar antes y después.
//   node scripts/vitales-movimiento.mjs http://localhost:8768 <salida.json> [repeticiones=3]
// Recorridos (escritorio 1280 y móvil 390 con la CPU ×4, como un iPhone medio):
//   portada: lista → periodo → sector → tocar el cintillo (entra a la acción);
//   acción: capítulos de la barra (3), píldoras de sección (2), abrir y cerrar una ayuda «?», modo oscuro y vuelta.
// INP: la interacción más lenta (Event Timing, por interactionId; con tan pocas, el p98 es el máximo).
// CLS: la peor ventana de sesión de layout-shift sin entrada reciente (≤ 5 s, huecos < 1 s), como web-vitals.
import fs from "fs";
import { chromium, devices } from "../node_modules/playwright/index.mjs";

const [BASE = "http://localhost:8768", OUT = "vitales.json", REPS = "3"] = process.argv.slice(2);
const OBS = () => {
  window.__v = { shifts: [], inter: new Map() };
  new PerformanceObserver((l) => { for (const e of l.getEntries()) if (!e.hadRecentInput) window.__v.shifts.push([e.startTime, e.value]); })
    .observe({ type: "layout-shift", buffered: true });
  new PerformanceObserver((l) => { for (const e of l.getEntries()) if (e.interactionId)
    window.__v.inter.set(e.interactionId, Math.max(window.__v.inter.get(e.interactionId) ?? 0, e.duration)); })
    .observe({ type: "event", buffered: true, durationThreshold: 16 });
};
const read = (page) => page.evaluate(() => {
  let worst = 0, cur = 0, start = -1, last = -1;
  for (const [t, v] of window.__v.shifts) {
    if (start < 0 || t - last > 1000 || t - start > 5000) { start = t; cur = 0; }
    cur += v; last = t; worst = Math.max(worst, cur);
  }
  const d = [...window.__v.inter.values()];
  return { cls: +worst.toFixed(4), inp: d.length ? Math.max(...d) : 0, n: d.length };
});

async function portada(page) {
  await page.goto(`${BASE}/v2`);
  await page.getByTestId("ticker-item").first().waitFor({ timeout: 60_000 });
  for (const sel of ["[data-testid^=list-]:nth-child(2)", "[data-testid^=period-]:nth-child(2)", "[data-testid^=sector-]:not([data-testid=sector-more])"]) {
    await page.locator(sel).first().click(); await page.waitForTimeout(600);
  }
  const r = await read(page);
  await page.getByTestId("ticker-item").first().click({ force: true });   // el cintillo avanza solo: nunca «estable»
  await page.locator(".company-header").first().waitFor({ timeout: 90_000 });
  await page.waitForTimeout(800);
  return r;
}
async function accion(page) {
  await page.goto(`${BASE}/v2/NVDA`);
  await page.locator(".chapterbar a").first().waitFor({ timeout: 90_000 });
  await page.waitForTimeout(500);
  const ch = page.locator(".chapterbar a");
  for (const i of [2, 4, 6]) { await ch.nth(i).click(); await page.waitForTimeout(700); }
  const pills = page.locator(".pillindex a");
  for (const i of [1, 2]) if (await pills.count() > i) { await pills.nth(i).click(); await page.waitForTimeout(600); }
  const tip = page.locator(".depth-body .tip-btn:visible").first();
  if (await tip.count()) { await tip.click(); await page.waitForTimeout(500); await page.keyboard.press("Escape"); await page.waitForTimeout(400); }
  const th = page.locator(".topbar .btn").first();
  await th.click(); await page.waitForTimeout(400); await th.click(); await page.waitForTimeout(400);
  return read(page);
}

const b = await chromium.launch();
const res = {};
for (const [disp, opts, cpu] of [["escritorio", { viewport: { width: 1280, height: 800 } }, 1], ["movil", { ...devices["iPhone 13"], viewport: { width: 390, height: 844 } }, 4]]) {
  for (const [name, fn] of [["portada", portada], ["accion", accion]]) {
    const runs = [];
    for (let k = 0; k < +REPS; k++) {
      const ctx = await b.newContext(opts); const page = await ctx.newPage();
      const cdp = await ctx.newCDPSession(page); await cdp.send("Emulation.setCPUThrottlingRate", { rate: cpu });
      await page.addInitScript(OBS);
      runs.push(await fn(page)); await ctx.close();
    }
    const med = (k) => runs.map((r) => r[k]).sort((a, z) => a - z)[Math.floor(runs.length / 2)];
    res[`${disp}/${name}`] = { inp_ms: med("inp"), cls: med("cls"), runs };
    console.log(disp, name, "INP", med("inp"), "ms · CLS", med("cls"));
  }
}
await b.close();
fs.writeFileSync(OUT, JSON.stringify(res, null, 2));
