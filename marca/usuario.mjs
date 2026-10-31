// El logo del usuario en vector (fiel a logo-usuario-original.webp; solo el logo, sin el fondo). Geometría medida y
// ajustada en usuario_medir.py (usuario.json); aquí, sus colores. Coordenadas del original (viewBox ajustado al logo).
//  · oscuro: los degradados del original, muestreados pieza a pieza;
//  · claro: la misma estructura de degradado en tonos más profundos de la misma familia: cada parada se oscurece
//    (misma tonalidad, saturación algo menor) hasta un contraste ≥ 3:1 con el papel (#F7F6F2) y el blanco.
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
const D = path.dirname(fileURLToPath(import.meta.url));
const M = JSON.parse(fs.readFileSync(path.join(D, "usuario.json"), "utf8")).piezas;
export const VIEWBOX = "668 236 398 443";

// ── paleta del original (tokens de marca) ──
export const BRAND = {
  "mint-100": "#AEFBB9", "mint-200": "#9FF4B0", "mint-300": "#94E8A5", "mint-400": "#6DD592",
  "green-500": "#52B47B", "green-600": "#3E9666", "green-700": "#2A6849", "green-800": "#1A513B", "green-900": "#0C3425",
  "fold": "#6EC289", "night": "#030A0A",
};

// ── utilidades de color ──
const hex2rgb = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16) / 255);
const rgb2hex = (c) => "#" + c.map((v) => Math.round(Math.max(0, Math.min(1, v)) * 255).toString(16).padStart(2, "0")).join("").toUpperCase();
const lin = (v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4);
export const lum = (h) => { const [r, g, b] = hex2rgb(h).map(lin); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
export const contrast = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };
function rgb2hsl([r, g, b]) { const mx = Math.max(r, g, b), mn = Math.min(r, g, b), l = (mx + mn) / 2; let h = 0, s = 0;
  if (mx !== mn) { const d = mx - mn; s = l > 0.5 ? d / (2 - mx - mn) : d / (mx + mn);
    h = mx === r ? (g - b) / d + (g < b ? 6 : 0) : mx === g ? (b - r) / d + 2 : (r - g) / d + 4; h /= 6; } return [h, s, l]; }
function hsl2rgb([h, s, l]) { if (!s) return [l, l, l]; const q = l < 0.5 ? l * (1 + s) : l + s - l * s, p = 2 * l - q;
  const f = (t) => { t = (t + 1) % 1; return t < 1 / 6 ? p + (q - p) * 6 * t : t < 1 / 2 ? q : t < 2 / 3 ? p + (q - p) * (2 / 3 - t) * 6 : p; };
  return [f(h + 1 / 3), f(h), f(h - 1 / 3)]; }
/** Tono profundo para fondo claro: luminosidad reescalada de [0,12 … 0,83] a [0,17 … 0,35], saturación × 0,62 (con la
 *  del menta original salía chillón) y la tonalidad 11° hacia el esmeralda (el «menta y esmeralda» del original; sin
 *  ese giro, el menta oscurecido tira a verde hierba). */
export function deep(hexc) {
  const [h, s, l] = rgb2hsl(hex2rgb(hexc));
  const L = 0.17 + ((Math.min(Math.max(l, 0.12), 0.83) - 0.12) / (0.83 - 0.12)) * (0.35 - 0.17);
  return rgb2hex(hsl2rgb([(h + 0.03) % 1, s * 0.62, L]));
}

// ── degradados de cada pieza (paradas muestreadas del original) ──
export const GRAD = {
  // a lo largo de la cinta: del pie (sombra) a la punta de la flecha (menta claro)
  cinta: { x1: 680, y1: 610, x2: 1050, y2: 320, stops: [[0, "#317A58"], [0.08, "#3E9666"], [0.15, "#52B47B"], [0.27, "#6DD592"], [0.35, "#8FE6A2"],
    [0.45, "#94E8A5"], [0.62, "#8EE6A4"], [0.75, "#93EEA7"], [0.85, "#9FF4B0"], [1, "#AEFBB9"]] },
  // barras: del techo biselado a la sombra que les hace la cinta
  b1: { x1: 0, y1: 372, x2: 6, y2: 522, stops: [[0, "#2F815A"], [0.13, "#297753"], [0.32, "#1F6146"], [0.52, "#174D39"], [0.72, "#113B2D"], [1, "#0C3425"]] },
  b2: { x1: 0, y1: 318, x2: 6, y2: 432, stops: [[0, "#4CB97E"], [0.24, "#42AD75"], [0.46, "#338D62"], [0.68, "#276C4F"], [0.85, "#1B573E"], [1, "#154A35"]] },
  b3: { x1: 0, y1: 262, x2: 6, y2: 420, stops: [[0, "#60D08B"], [0.18, "#55C684"], [0.37, "#3D9E6B"], [0.56, "#287353"], [0.75, "#184A37"], [0.94, "#0E2F26"], [1, "#0C2B20"]] },
  // cara del asta: oscura arriba a la izquierda, la luz se junta en la esquina de abajo a la derecha
  asta: { x1: 712, y1: 552, x2: 769, y2: 668, stops: [[0, "#1A513B"], [0.45, "#1E5940"], [0.72, "#3E8E62"], [1, "#6ED08E"]] },
  // brazo inferior: sombra junto al asta, menta en el remate
  brazo: { x1: 772, y1: 0, x2: 944, y2: 0, stops: [[0, "#2A6849"], [0.16, "#408E64"], [0.34, "#5FB97F"], [0.57, "#80DB98"], [0.74, "#93EBA5"], [1, "#9CF2AC"]] },
};
const gradDef = (id, g, tema) => `<linearGradient id="${id}" gradientUnits="userSpaceOnUse" x1="${g.x1}" y1="${g.y1}" x2="${g.x2}" y2="${g.y2}">${g.stops
  .map(([o, c]) => `<stop offset="${o}" stop-color="${tema === "claro" ? deep(c) : c}"/>`).join("")}</linearGradient>`;

/** El logo: `tema` oscuro (original) o claro (tonos profundos); `id` hace únicos los id en una página. */
export function logo(tema = "oscuro", id = "fz") {
  const fold = tema === "claro" ? deep("#5DB077") : "#5DB077";
  const PL = M.pliegue_linea;
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${VIEWBOX}" role="img" aria-label="Finanzer">
  <defs>
    ${Object.entries(GRAD).map(([k, g]) => gradDef(`${id}-${k}`, g, tema)).join("\n    ")}
    <linearGradient id="${id}-pl" gradientUnits="userSpaceOnUse" x1="${(PL[0][0] + PL[1][0]) / 2}" y1="${(PL[0][1] + PL[1][1]) / 2}" x2="${(PL[0][0] + PL[1][0]) / 2 - 34}" y2="${(PL[0][1] + PL[1][1]) / 2 - 22}">
      <stop offset="0" stop-color="${fold}" stop-opacity=".95"/><stop offset=".55" stop-color="${fold}" stop-opacity=".45"/><stop offset="1" stop-color="${fold}" stop-opacity="0"/></linearGradient>
    <clipPath id="${id}-cc"><path d="${M.cinta}"/></clipPath>
  </defs>
  <path d="${M.b1}" fill="url(#${id}-b1)"/>
  <path d="${M.b2}" fill="url(#${id}-b2)"/>
  <path d="${M.b3}" fill="url(#${id}-b3)"/>
  <path d="${M.asta}" fill="url(#${id}-asta)"/>
  <path d="${M.brazo}" fill="url(#${id}-brazo)"/>
  <path d="${M.cinta}" fill="url(#${id}-cinta)"/>
  <path d="${M.pliegue}" fill="url(#${id}-pl)" clip-path="url(#${id}-cc)"/>
</svg>
`;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  fs.writeFileSync(path.join(D, "usuario-oscuro.svg"), logo("oscuro"));
  fs.writeFileSync(path.join(D, "usuario-claro.svg"), logo("claro"));
  const paper = "#F7F6F2";
  const all = [...new Set(Object.values(GRAD).flatMap((g) => g.stops.map(([, c]) => c)))];
  const worst = all.map((c) => [c, deep(c), contrast(deep(c), paper)]).sort((a, b) => a[2] - b[2]);
  console.log("claro: peor contraste con el papel", worst[0], "· mejor", worst[worst.length - 1]);
}
