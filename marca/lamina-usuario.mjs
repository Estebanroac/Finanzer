// Lámina del logo del usuario: su original frente al vector, claro y oscuro, tamaños pequeños, lockups, cabeceras reales,
// PDF y una fila de propuesta con el color de marca en la web.
//   node marca/lamina-usuario.mjs <original.webp> <capturas> <salida.png>
//   <capturas>: las de la propuesta (cabeceras de /v2 con el logo puesto encima) y pdf-p1.png / pdf-p2.png (cabecera del PDF con el logo, recortada)
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { chromium } from "../frontend/node_modules/playwright/index.mjs";
import { logo, BRAND, contrast, deep } from "./usuario.mjs";
import { svgPixel, PLACA } from "./usuario-pixel.mjs";
const svgU16 = () => svgPixel(16);
import { TOKENS, PALETA, pares } from "./tokens-usuario.mjs";

const D = path.dirname(fileURLToPath(import.meta.url));
const [ORIG, CAP, OUT] = process.argv.slice(2);
const FONT = process.env.MANROPE ?? path.join(D, "..", "backend", "assets", "fonts", "Manrope-Bold.ttf");
const b64 = (buf, type) => `data:${type};base64,${Buffer.from(buf).toString("base64")}`;
const svg = (s) => b64(s, "image/svg+xml");
const png = (f) => b64(fs.readFileSync(path.join(CAP, f)), "image/png");
const LO = svg(logo("oscuro", "lo")), LC = svg(logo("claro", "lc"));
const CROP = [650, 225, 1080, 690];   // el recorte del original que mide usuario_medir.py
const K = 400 / (CROP[3] - CROP[1]);   // la misma escala para el original, el vector y su diferencia

const fig = (img, cap, bg = "transparent", extra = "") => `<figure style="background:${bg};${extra}">${img}<figcaption>${cap}</figcaption></figure>`;
const lockH = (src, ink, bg, fs_ = 52) => `<div class="lock" style="background:${bg};color:${ink}"><span class="lh" style="font-size:${fs_}px"><img src="${src}" style="height:1.5em"><span>Finanzer</span></span></div>`;
const lockV = (src, ink, bg) => `<div class="lock" style="background:${bg};color:${ink}"><span class="lv"><img src="${src}" style="height:118px"><span>Finanzer</span></span></div>`;
const tab = (bg, fg, act, src16) => `<div class="tabbar" style="background:${bg}"><span class="tab" style="background:${act};color:${fg}"><img src="${src16}" width="16" height="16">NVIDIA · Finanzer<span class="x">×</span></span><span class="tab ghost" style="color:${fg}">Nueva pestaña</span></div>`;
const swatch = (k, v, note) => `<div class="sw"><i style="background:${v}"></i><b>${k}</b><code>${v}</code>${note ? `<em>${note}</em>` : ""}</div>`;

const html = (r32) => `<!doctype html><html><head><meta charset="utf-8"><style>
@font-face { font-family: "FzBrand"; src: url(${b64(fs.readFileSync(FONT), "font/ttf")}) format("truetype"); font-weight: 700; }
* { box-sizing: border-box; } body { margin: 0; width: 1800px; background: #EDEBE6; color: #1B1D1F; font: 15px/1.45 -apple-system, "Helvetica Neue", sans-serif; }
header.t { padding: 36px 48px 8px; } header.t h1 { font: 700 30px/1.2 "FzBrand"; margin: 0 0 6px; } header.t p { margin: 0; color: #55595D; max-width: 1300px; }
section { margin: 22px 48px; background: #fff; border-radius: 14px; padding: 22px 24px 24px; }
section h2 { margin: 0 0 4px; font-size: 18px; } section > p { margin: 0 0 16px; color: #55595D; max-width: 1400px; }
.row { display: flex; gap: 18px; align-items: flex-start; flex-wrap: wrap; }
figure { margin: 0; border-radius: 10px; overflow: hidden; } figcaption { font-size: 12.5px; color: #6B6F73; padding: 7px 2px 0; background: #fff; }
.cell { width: 400px; height: 400px; display: flex; align-items: center; justify-content: center; }
.cell img { height: 330px; }
.box { position: relative; width: ${K * (CROP[2] - CROP[0])}px; height: 400px; overflow: hidden; }
.box > img { position: absolute; left: ${(668 - CROP[0]) * K}px; top: ${(236 - CROP[1]) * K}px; width: ${398 * K}px; height: ${443 * K}px; }
.orig { background: url(${b64(fs.readFileSync(ORIG), "image/webp")}) no-repeat; background-size: ${1671 * K}px auto; background-position: -${CROP[0] * K}px -${CROP[1] * K}px; }
.lock { border-radius: 10px; display: flex; align-items: center; justify-content: center; width: 398px; height: 230px; }
.lh { display: inline-flex; align-items: center; gap: .3em; font: 700 52px/1 "FzBrand"; letter-spacing: -.01em; }
.lv { display: inline-flex; flex-direction: column; align-items: center; gap: 14px; font: 700 40px/1 "FzBrand"; letter-spacing: -.01em; }
.tabbar { display: flex; align-items: flex-end; gap: 4px; padding: 8px 10px 0; border-radius: 10px 10px 0 0; width: 420px; }
.tab { display: inline-flex; align-items: center; gap: 8px; font: 12.5px system-ui; padding: 8px 12px; border-radius: 9px 9px 0 0; width: 220px; }
.tab .x { margin-left: auto; opacity: .55; } .tab.ghost { background: transparent; opacity: .7; width: 150px; }
.px img { image-rendering: pixelated; display: block; }
.shot { display: block; border: 1px solid #E2E0DA; border-radius: 8px; }
.sw { display: grid; grid-template-columns: 34px 1fr; column-gap: 10px; align-items: center; width: 270px; font-size: 13px; }
.sw i { grid-row: span 3; width: 34px; height: 34px; border-radius: 8px; border: 1px solid rgba(0,0,0,.12); } .sw code { color: #55595D; font-size: 12px; } .sw em { font-style: normal; color: #6B6F73; font-size: 12px; }
table.c { border-collapse: collapse; font-size: 13px; width: auto; } table.c td:first-child { width: 44px; white-space: nowrap; } table.c td { padding: 3px 12px 3px 0; } table.c td.n { font-variant-numeric: tabular-nums; text-align: right; font-weight: 600; }
.chip { display: inline-block; width: 14px; height: 14px; border-radius: 3px; vertical-align: -2px; border: 1px solid rgba(0,0,0,.15); margin-right: 3px; }
.pill { display: inline-block; font-size: 11px; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; background: #FFF4D6; color: #6B4E00; padding: 2px 8px; border-radius: 99px; margin-left: 8px; vertical-align: 2px; }
</style></head><body>
<header class="t"><h1>Finanzer · el logo del usuario, en vector</h1>
<p>Solo el logo y su color: el fondo del original (líneas y puntos) se descarta. Contorno a subpíxel, rectas exactas, curvas de Bézier ajustadas (error medio del borde exterior 1,2 px sobre 443) y los degradados medidos pieza a pieza. Nada reinterpretado.</p></header>

<section><h2>1 · El original frente al vector</h2><p>Mismo encuadre y misma escala. La tercera es la diferencia de las dos (negro = idéntico): solo quedan el suavizado del borde y el ruido de compresión del original.</p>
<div class="row">${fig(`<div class="box orig"></div>`, "Su imagen original, recortada (fondo incluido, tal como la trajo)")}
${fig(`<div class="box" style="background:${BRAND.night}"><img src="${LO}"></div>`, "El vector, sobre la noche del original (#030A0A)")}
${fig(`<div class="box orig"><img src="${LO}" style="mix-blend-mode:difference"></div>`, "Diferencia original − vector")}
</div></section>

<section><h2>2 · Oscuro y claro</h2><p>Oscuro: los colores del original. Claro: la misma estructura de degradados en tonos más profundos de la misma familia (menta → esmeralda); la parada más clara queda a ${contrast(deep(BRAND["mint-100"]), "#F7F6F2").toFixed(2)}:1 del papel y ${contrast(deep(BRAND["mint-100"]), "#FFFFFF").toFixed(2)}:1 del blanco (mínimo pedido 3:1).</p>
<div class="row">${[["#030A0A", LO, "Oscuro · noche del original"], ["#16181B", LO, "Oscuro · papel de la web en oscuro"], ["#F7F6F2", LC, "Claro · papel de la web"], ["#FFFFFF", LC, "Claro · blanco (PDF)"]]
  .map(([bg, src, c]) => fig(`<div class="cell" style="background:${bg};width:398px;height:330px"><img src="${src}" style="height:260px"></div>`, c)).join("")}</div></section>

<section><h2>3 · Tamaños pequeños: pestaña, 16, 32 y 180</h2><p>El 16 está dibujado píxel a píxel: la forma sale de la cobertura real del vector a esa escala (las barras, a 2 px con 1 px de junta) y cada píxel lleva el color del degradado de su pieza. Va sobre una placa en la noche del logo (${PLACA}) porque el logo está diseñado sobre oscuro: sin ella, sus barras bajas se pierden en una pestaña clara. El 32 y el 180 son el vector sobre la misma placa.</p>
<div class="row" style="align-items:flex-end">
${fig(`<div style="display:flex;flex-direction:column;gap:10px">${tab("#DEE1E6", "#202124", "#FFFFFF", svg(svgU16()))}${tab("#202124", "#E8EAED", "#35363A", svg(svgU16()))}</div>`, "Pestaña, a tamaño real (16 px) · claro y oscuro")}
${fig(`<div class="px" style="display:flex;gap:14px;align-items:flex-end"><img src="${svg(svgU16())}" width="16" height="16"><img src="${svg(svgU16())}" width="208" height="208"></div>`, "16 · real y ×13")}
${fig(`<div class="px" style="display:flex;gap:14px;align-items:flex-end"><img src="${r32}" width="32" height="32"><img src="${r32}" width="208" height="208"></div>`, "32 · real y ×6,5")}
${fig(`<div style="display:flex;gap:18px;align-items:flex-end;background:linear-gradient(135deg,#6B8BA4,#C9B49A);padding:22px;border-radius:10px">
  <span style="display:inline-flex;width:180px;height:180px;border-radius:40px;background:${PLACA};align-items:center;justify-content:center"><img src="${LO}" style="height:146px"></span>
  <span style="display:inline-flex;flex-direction:column;align-items:center;gap:6px;color:#fff;font:12px system-ui"><span style="display:inline-flex;width:64px;height:64px;border-radius:14px;background:${PLACA};align-items:center;justify-content:center"><img src="${LO}" style="height:52px"></span>Finanzer</span></div>`, "180 (apple-touch-icon) y en la pantalla de inicio")}
</div></section>

<section><h2>4 · Lockups · «Finanzer» en Manrope 700</h2><p>Horizontal: el logo a 1,5 veces el cuerpo del nombre y 0,3 de aire. Vertical: el logo sobre el nombre. Claro: logo profundo y nombre en tinta; oscuro: logo original y nombre en blanco verdoso.</p>
<div class="row">${lockH(LC, "#1B1D1F", "#F7F6F2")}${lockH(LO, "#E6F5EA", BRAND.night)}${lockV(LC, "#1B1D1F", "#FFFFFF; border: 1px solid #E2E0DA")}${lockV(LO, "#E6F5EA", "#16181B")}</div></section>

<section><h2>5 · Cabeceras reales (/v2) con el logo</h2><p>Capturas de la web compilada con el lockup puesto en la cabecera; los colores de la web, los de hoy.</p>
<div class="row"><img class="shot" src="${png("escritorio-claro-actual.png")}" width="1240"><img class="shot" src="${png("escritorio-oscuro-actual.png")}" width="1240"></div>
<div class="row" style="margin-top:14px"><img class="shot" src="${png("iphone-claro-actual.png")}" width="440"><img class="shot" src="${png("iphone-oscuro-actual.png")}" width="440"></div></section>

<section><h2>6 · PDF</h2><p>Cabecera de la portada y de las páginas interiores del informe real (NVDA), con el logo profundo (el PDF es blanco) y el nombre en Manrope 700.</p>
<div class="row"><img class="shot" src="${png("pdf-p1.png")}" width="830"><img class="shot" src="${png("pdf-p2.png")}" width="830"></div></section>

<section style="outline:2px dashed #C9A227;outline-offset:-2px"><h2>7 · El color nuevo en la web <span class="pill">solo propuesta</span></h2><p>La cabecera en la noche del logo (el logo vive sobre su fondo original, en los dos temas) y «Descargar PDF» como botón principal en menta. El resto de la página no cambia: los verdes de lectura (--good) siguen como están hasta que decidas.</p>
<div class="row"><img class="shot" src="${png("escritorio-claro-marca.png")}" width="1240"><img class="shot" src="${png("escritorio-oscuro-marca.png")}" width="1240"></div>
<div class="row" style="margin-top:14px"><img class="shot" src="${png("iphone-claro-marca.png")}" width="440"><img class="shot" src="${png("iphone-oscuro-marca.png")}" width="440">
<div style="display:flex;flex-direction:column;gap:14px;margin-left:12px">
<div class="row" style="gap:10px">${Object.entries(PALETA).map(([k, v]) => swatch(k, v)).join("")}</div>
<div class="row" style="gap:10px">${Object.entries(TOKENS.claro).slice(0, 3).map(([k, v]) => swatch(`${k} · claro`, v)).join("")}${Object.entries(TOKENS.oscuro).slice(0, 3).map(([k, v]) => swatch(`${k} · oscuro`, v)).join("")}</div>
<table class="c">${pares().filter((r) => r.min > 1).map((r) => `<tr><td><span class="chip" style="background:${r.a}"></span><span class="chip" style="background:${r.b}"></span></td><td>${r.q}</td><td class="n">${r.c.toFixed(2)}:1</td><td style="color:#6B6F73">≥ ${r.min}</td></tr>`).join("")}</table>
</div></div></section>
<div style="height:26px"></div></body></html>`;

const br = await chromium.launch();
const p = await br.newPage({ viewport: { width: 1800, height: 1000 }, deviceScaleFactor: 2 });
// el 32: el vector rasterizado a 32 px exactos sobre su placa
const r32 = await p.evaluate(async ({ src, placa }) => {
  const im = new Image(); im.src = src; await im.decode();
  const c = document.createElement("canvas"); c.width = c.height = 32; const x = c.getContext("2d");
  x.fillStyle = placa; x.beginPath(); x.roundRect(0, 0, 32, 32, 6); x.fill();
  const h = 27, w = h * 398 / 443; x.drawImage(im, (32 - w) / 2, (32 - h) / 2, w, h); return c.toDataURL();
}, { src: LO, placa: PLACA });
await p.setContent(html(r32), { waitUntil: "load" });
await p.evaluate(() => document.fonts.ready);
await p.waitForTimeout(400);
await p.screenshot({ path: OUT, fullPage: true });
await br.close();
console.log("lámina:", OUT);
