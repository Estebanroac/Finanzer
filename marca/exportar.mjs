// Exporta los activos de la marca (el logo del usuario) a la web y al PDF desde una sola fuente: usuario.mjs (vector)
// y usuario-pixel.mjs (16 y 32 dibujados). Una sola forma de marca, como la imagen del usuario: el logo en sus colores
// originales (menta y esmeralda) sobre su placa nocturna redondeada, en los dos temas, en el PDF y en los iconos.
// Uso (desde la raíz): node marca/exportar.mjs   — necesita el Playwright del frontend para rasterizar.
//   frontend/public/brand/  finanzer-logo.svg (el logo en su placa), finanzer-logo.png (el mismo, para el PDF),
//                           icon-16.png, icon-32.png, apple-touch-icon.png, icon-192.png, icon-512.png,
//                           icon-maskable-512.png
//   frontend/public/manifest.webmanifest
//   frontend/src/app/favicon.ico (16 y 32, dibujados píxel a píxel)
import { chromium } from "../frontend/node_modules/playwright/index.mjs";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { logo, VIEWBOX } from "./usuario.mjs";
import { svgPixel, PLACA } from "./usuario-pixel.mjs";
import { TOKENS } from "./tokens-usuario.mjs";

const D = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(D, "..");
const PUB = path.join(ROOT, "frontend", "public");
const BRAND = path.join(PUB, "brand");
export const THEME_COLOR = TOKENS.claro["--brand"];
const [VX, VY, VW, VH] = VIEWBOX.split(" ").map(Number);

/** El logo en su placa nocturna: cuadrada, con el logo a `escala` del lado y las esquinas a `radio` del lado (sin
 *  radio, a sangre: iOS y Android redondean ellos). */
export function logoPlaca({ escala = 0.8, radio = 0.22, id = "fz" } = {}) {
  const L = Math.max(VW, VH) / escala, x0 = VX + VW / 2 - L / 2, y0 = VY + VH / 2 - L / 2;
  const inner = logo("oscuro", id).replace(/^<svg[^>]*>/, "").replace(/<\/svg>\s*$/, "");
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${x0} ${y0} ${L} ${L}" role="img" aria-label="Finanzer">
  <rect x="${x0}" y="${y0}" width="${L}" height="${L}" rx="${radio * L}" fill="${PLACA}"/>${inner}</svg>
`;
}

// ICO con imágenes PNG (16 y 32)
function ico(pngs) {
  const head = Buffer.alloc(6); head.writeUInt16LE(0, 0); head.writeUInt16LE(1, 2); head.writeUInt16LE(pngs.length, 4);
  let offset = 6 + 16 * pngs.length; const dir = [];
  for (const { size, data } of pngs) {
    const e = Buffer.alloc(16); e.writeUInt8(size, 0); e.writeUInt8(size, 1); e.writeUInt8(0, 2); e.writeUInt8(0, 3);
    e.writeUInt16LE(1, 4); e.writeUInt16LE(32, 6); e.writeUInt32LE(data.length, 8); e.writeUInt32LE(offset, 12);
    dir.push(e); offset += data.length;
  }
  return Buffer.concat([head, ...dir, ...pngs.map((p) => p.data)]);
}

async function main() {
  fs.mkdirSync(BRAND, { recursive: true });
  for (const f of fs.readdirSync(BRAND)) fs.rmSync(path.join(BRAND, f));
  const placa = logoPlaca(), sangre = logoPlaca({ radio: 0, id: "fzs" });
  fs.writeFileSync(path.join(BRAND, "finanzer-logo.svg"), placa);
  const b = await chromium.launch();
  const page = await b.newPage();
  /** SVG → PNG de n × n (contenido escalado al lado), con o sin suavizado. */
  const png = async (svg, n, { smooth = true } = {}) => {
    const url = await page.evaluate(async ([svg, n, smooth]) => {
      const img = new Image(); img.src = "data:image/svg+xml;base64," + btoa(unescape(encodeURIComponent(svg))); await img.decode();
      const c = document.createElement("canvas"); c.width = c.height = n; const g = c.getContext("2d");
      g.imageSmoothingEnabled = smooth; g.drawImage(img, 0, 0, n, n);
      return c.toDataURL("image/png");
    }, [svg, n, smooth]);
    return Buffer.from(url.split(",")[1], "base64");
  };
  const sized = (svg, n) => svg.replace("<svg ", `<svg width="${n}" height="${n}" `);
  const p16 = await png(svgPixel(16), 16, { smooth: false });
  const p32 = await png(svgPixel(32), 32, { smooth: false });
  fs.writeFileSync(path.join(BRAND, "icon-16.png"), p16);
  fs.writeFileSync(path.join(BRAND, "icon-32.png"), p32);
  fs.writeFileSync(path.join(ROOT, "frontend", "src", "app", "favicon.ico"), ico([{ size: 16, data: p16 }, { size: 32, data: p32 }]));
  // iOS y manifiesto: a sangre (iOS rellena de negro lo transparente y redondea él las esquinas)
  for (const n of [180, 192, 512]) fs.writeFileSync(path.join(BRAND, n === 180 ? "apple-touch-icon.png" : `icon-${n}.png`), await png(sized(sangre, n), n));
  // maskable: el logo dentro de la zona segura (círculo del 80 %)
  fs.writeFileSync(path.join(BRAND, "icon-maskable-512.png"), await png(sized(logoPlaca({ escala: 0.62, radio: 0, id: "fzm" }), 512), 512));
  // el logo en su placa en PNG para los PDF (reportlab no dibuja SVG): 512 px, esquinas transparentes
  fs.writeFileSync(path.join(BRAND, "finanzer-logo.png"), await png(sized(placa, 512), 512));
  await b.close();
  const manifest = {
    name: "Finanzer", short_name: "Finanzer", description: "Entiende una empresa antes de invertir",
    start_url: "/", scope: "/", display: "standalone", lang: "es", background_color: PLACA, theme_color: THEME_COLOR,
    icons: [
      { src: "/brand/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/brand/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/brand/icon-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
      { src: "/brand/finanzer-logo.svg", sizes: "any", type: "image/svg+xml", purpose: "any" },
    ],
  };
  fs.writeFileSync(path.join(PUB, "manifest.webmanifest"), JSON.stringify(manifest, null, 2) + "\n");
  console.log("marca exportada:", fs.readdirSync(BRAND).join(", "), "· theme-color", THEME_COLOR);
}
if (process.argv[1] === fileURLToPath(import.meta.url)) await main();
