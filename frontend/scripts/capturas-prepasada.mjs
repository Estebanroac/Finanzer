// Capturas de los arreglos de la pre-pasada final de la v4 (docs/rediseno/V4_PREPASADA.md): el elemento arreglado,
// al ancho y en el motor donde fallaba (1440 px y Chromium si no se dice), comprimido a WebP como las demás capturas.
//   node scripts/capturas-prepasada.mjs [base]        (base: http://localhost:3001; el replay del panel en marcha)
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium, webkit, devices } from "@playwright/test";
import { compress } from "./capturas-lib.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const OUT = path.join(ROOT, "docs/rediseno/capturas-v4-prepasada");
const base = process.argv[2] || "http://localhost:3001";

/** Cada captura: nombre, ruta, el elemento (la tarjeta que contiene `has`, o `sel` tal cual), ancho o dispositivo, y motor. */
const SHOTS = [
  { name: "1-pais-TSM", url: "/v2/TSM/empresa", sel: ".card", has: "dt:text-is('País')" },
  { name: "1-pais-ASML", url: "/v2/ASML/empresa", sel: ".card", has: "dt:text-is('País')" },
  { name: "2-anexo-HSBC-375", url: "/v2/HSBC/conclusion", sel: "[data-testid=annex]", w: 375 },
  { name: "3-cabecera-MCPA-375-webkit", url: "/v2/MC.PA/empresa", sel: ".company-header:not(.compact)", w: 375, engine: "webkit" },
  { name: "4-cabecera-MCPA-ipad", url: "/v2/MC.PA/empresa", sel: ".company-header:not(.compact) .ident", device: "iPad Mini", engine: "webkit" },
];

fs.mkdirSync(OUT, { recursive: true });
const browsers = { chromium: await chromium.launch(), webkit: await webkit.launch() };
for (const s of SHOTS) {
  const page = await browsers[s.engine ?? "chromium"].newPage(s.device ? devices[s.device] : { viewport: { width: s.w ?? 1440, height: 900 } });
  await page.goto(base + s.url);
  await page.waitForSelector(".depth-body .dsec", { timeout: 60_000 });
  await page.waitForTimeout(800);
  const el = s.has ? page.locator(s.sel).filter({ has: page.locator(s.has) }).first() : page.locator(s.sel).first();
  await el.scrollIntoViewIfNeeded();
  // La cabecera y la barra fijas taparían parte de un elemento más alto que la pantalla
  await page.evaluate(() => document.querySelectorAll("body *").forEach((n) => {
    if (/sticky|fixed/.test(getComputedStyle(n).position)) n.style.visibility = "hidden";
  }));
  const png = await el.screenshot();
  const { buffer } = await compress(png);
  fs.writeFileSync(path.join(OUT, `${s.name}.webp`), buffer);
  console.log(`${s.name}.webp`);
  await page.close();
}
for (const b of Object.values(browsers)) await b.close();
