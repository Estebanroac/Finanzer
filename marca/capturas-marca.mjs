// Capturas de la marca ya implantada (sin inyectar nada): cabecera de /v2 en escritorio e iPhone, claro y oscuro; la
// pestaña con el favicon real (16 y 32 del build) y el apple-touch.
//   node marca/capturas-marca.mjs http://localhost:8768 <carpeta>   (replay con la web compilada)
import fs from "fs";
import path from "path";
import { chromium, devices } from "../frontend/node_modules/playwright/index.mjs";

const [BASE = "http://localhost:8768", OUT = "capturas-marca"] = process.argv.slice(2);
fs.mkdirSync(OUT, { recursive: true });
const b = await chromium.launch();
for (const [disp, o, h] of [["escritorio", { viewport: { width: 1280, height: 720 }, deviceScaleFactor: 2 }, 150],
  ["iphone", { ...devices["iPhone 15 Pro Max"], viewport: { width: 440, height: 956 } }, 200]]) {
  for (const tema of ["claro", "oscuro"]) {
    const ctx = await b.newContext({ ...o, colorScheme: tema === "oscuro" ? "dark" : "light" });
    const p = await ctx.newPage();
    await p.goto(`${BASE}/v2/NVDA`);
    await p.locator(".topbar .pdf-btn").waitFor({ timeout: 90_000 });
    await p.evaluate(() => document.fonts.ready);
    await p.waitForTimeout(300);
    await p.screenshot({ path: path.join(OUT, `cabecera-${disp}-${tema}.png`), clip: { x: 0, y: 0, width: p.viewportSize().width, height: h } });
    await ctx.close();
  }
}
// la pestaña: los PNG que sirve la web, a su tamaño (16 a 1×, 32 a 2×), en una barra clara y una oscura
const get = async (u) => Buffer.from(await (await fetch(BASE + u)).arrayBuffer()).toString("base64");
const [i16, i32, apple] = await Promise.all(["/brand/icon-16.png", "/brand/icon-32.png", "/brand/apple-touch-icon.png"].map(get));
const tab = (bar, act, fg, src, dpr) => `<div style="background:${bar};padding:8px 10px 0;display:flex;gap:4px;width:460px">
  <span style="display:inline-flex;align-items:center;gap:8px;background:${act};color:${fg};font:12.5px system-ui;padding:8px 12px;border-radius:9px 9px 0 0;width:230px">
  <img src="data:image/png;base64,${src}" width="16" height="16">NVIDIA · Finanzer<span style="margin-left:auto;opacity:.5">×</span></span>
  <span style="color:${fg};opacity:.7;font:12.5px system-ui;padding:8px 12px">Nueva pestaña</span></div>`;
for (const [dpr, src] of [[1, i16], [2, i32]]) {
  const p = await b.newPage({ viewport: { width: 760, height: 150 }, deviceScaleFactor: dpr });
  await p.setContent(`<body style="margin:12px;display:flex;gap:18px;align-items:flex-start;background:#fff">
    <div style="display:flex;flex-direction:column;gap:10px">${tab("#DEE1E6", "#FFFFFF", "#202124", src)}${tab("#202124", "#35363A", "#E8EAED", src)}</div>
    ${dpr === 2 ? `<img src="data:image/png;base64,${apple}" width="90" height="90" style="border-radius:20px">` : ""}</body>`);
  await p.screenshot({ path: path.join(OUT, `pestana-${dpr === 1 ? "16" : "32-y-180"}.png`) });
  await p.close();
}
await b.close();
console.log("capturas en", OUT);
