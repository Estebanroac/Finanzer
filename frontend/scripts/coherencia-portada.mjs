// Coherencia web ↔ PDF de las cifras de portada (V2 con fuentes reales; F9 · R3, «una sola verdad por cifra»).
// Paso 1 de 2: lee lo que la web enseña de verdad (el DOM de /v2/{T}: precio, variación, conclusión, las tres
// puntuaciones y las cifras clave de «La empresa»), guarda el análisis que pidió la propia página y descarga el PDF del
// mismo servidor justo después. El paso 2 (backend/tools/coherencia_portada.py) extrae la portada del PDF y compara.
//   node scripts/coherencia-portada.mjs <base> <carpeta> NU,VZ,PLD,...
// <base>: el backend con la web compilada (tools/load_server.py con fuentes reales, o el replay del panel).
import fs from "node:fs";
import path from "node:path";
import { chromium } from "@playwright/test";

const [base, dir, list] = process.argv.slice(2);
if (!base || !dir || !list) {
  console.error("uso: node scripts/coherencia-portada.mjs <base> <carpeta> T1,T2,...");
  process.exit(2);
}
fs.mkdirSync(dir, { recursive: true });
const browser = await chromium.launch();
const out = {};
for (const sym of list.split(",").map((s) => s.trim()).filter(Boolean)) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const analysis = page.waitForResponse((r) => r.url().includes(`/api/analysis/${encodeURIComponent(sym)}`), { timeout: 240_000 });
  await page.goto(`${base}/v2/${sym}`);
  const res = await analysis;
  if (!res.ok()) {
    out[sym] = { error: `análisis ${res.status()}` };
    console.log(sym, "análisis", res.status());
    await page.close();
    continue;
  }
  fs.writeFileSync(path.join(dir, `${sym}.analysis.json`), await res.body());
  await page.waitForSelector(".company-header:not(.compact) [data-testid=price]", { timeout: 60_000 });
  await page.waitForSelector(".tiles.flow .tile", { timeout: 60_000 });
  const web = await page.evaluate(() => {
    const head = document.querySelector(".company-header:not(.compact)");
    const txt = (el) => (el?.textContent ?? "").replace(/\s+/g, " ").trim() || null;
    // Texto propio de la ficha, sin el «?» de la ayuda
    const own = (el) => [...(el?.childNodes ?? [])].filter((n) => n.nodeType === Node.TEXT_NODE).map((n) => n.textContent).join("").trim();
    return {
      price: txt(head.querySelector("[data-testid=price]")),
      day_change: txt(head.querySelector("[data-testid=day-change]")),
      verdict: txt(head.querySelector("[data-testid=verdict] .verdict-text")),
      quality: txt(head.querySelector("[data-testid=score-quality] .score-value")),
      price_score: txt(head.querySelector("[data-testid=score-price] .score-value")),
      confidence: txt(head.querySelector("[data-testid=confidence] .score-value")),
      kpis: [...document.querySelectorAll(".tiles.flow .tile")].map((t) => ({
        label: txt(t.querySelector(".tile-label")), value: own(t.querySelector(".tile-value")) })),
    };
  });
  const pdf = await page.request.get(`${base}/api/v2/pdf/${encodeURIComponent(sym)}`, { timeout: 240_000 });
  if (pdf.ok()) fs.writeFileSync(path.join(dir, `${sym}.pdf`), await pdf.body());
  out[sym] = { web, pdf_status: pdf.status() };
  console.log(sym, "web", Object.keys(web).length, "campos ·", web.kpis.length, "cifras · pdf", pdf.status());
  await page.close();
}
await browser.close();
fs.writeFileSync(path.join(dir, "web.json"), JSON.stringify(out, null, 1));
