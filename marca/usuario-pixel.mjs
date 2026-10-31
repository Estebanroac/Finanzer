// El logo del usuario a 16 y 32 px, dibujado píxel a píxel. La forma sale de la cobertura real del vector a cada escala
// (escala elegida para que el paso de las barras sea un número entero de píxeles: 3 a 16 px — 2 de barra y 1 de junta —
// y 6 a 32 px — 5 y 1 —) y cada píxel toma el color del degradado de su pieza en el centro del píxel: es el mismo logo,
// no un dibujo aparte. Ajustes de oficio, los mínimos: los techos de las barras siguen la diagonal del original; la
// flecha conserva la punta y la muesca de su barba izquierda; el pliegue de la cinta va un tono más oscuro.
// Color: los colores originales del logo (menta y esmeralda), sobre su placa nocturna, como toda la marca.
import { GRAD } from "./usuario.mjs";

// 1 2 3 barras · C cinta · f pliegue (cinta con la sombra del pliegue) · a cara del asta · r brazo · . placa
const U16 = [
  // 0123456789ABCDEF
  "................",
  ".........3......",
  "........33......",
  "......2.33...C..",
  "...1.22.33.CCC..",
  "..11.22.33..CC..",
  "..11.22.33.fC...",
  "..11CCCCCCfC....",
  "..1CCCCCCfC.....",
  "..CCC...........",
  "..CCarrrrr......",
  "..Caarrrrr......",
  "..Caa...........",
  "...aa...........",
  "....a...........",
  "................",
];
const U32 = [
  "................................",
  "................................",
  "................................",
  ".................333............",
  "................3333............",
  "...............33333............",
  "............22.33333............",
  "..........2222.33333......C.....",
  ".........22222.33333....CCC.....",
  "......11.22222.33333..CCCCC.....",
  "....1111.22222.33333...CCCC.....",
  "...11111.22222.33333..CCCCC.....",
  "...11111.22222.33333.CCCCCC.....",
  "...11111.22222.3333.CCCC........",
  "...11111CCCCCCCCCffCCCC.........",
  "...111CCCCCCCCCCCfCCCC..........",
  "...11CCCCCCCCCCCffCCC...........",
  "...11CCCCCCCCCCCfCC.............",
  "...1CCCCC.......................",
  "...1CCCCa.......................",
  "...CCCaaarrrrrrrrrr.............",
  "...CCCaaarrrrrrrrrr.............",
  "...CCaaaarrrrrrrrr..............",
  "...Caaaaarrrrrrrr...............",
  "...aaaaaa.......................",
  "....aaaaa.......................",
  ".....aaaa.......................",
  "......aaa.......................",
  ".......aa.......................",
  "................................",
  "................................",
  "................................",
];
// del píxel a las coordenadas del original (paso de las barras, 96,6 u = 3 o 6 px; la barra 1 empieza en x 2 o 3)
const mapa = (n, paso, x1) => { const S = paso / 96.6; return { S, OX: x1 - (675.87 - 668) * S, OY: (n - 443 * S) / 2 }; };
export const PIXEL = { 16: { grid: U16, ...mapa(16, 3, 2) }, 32: { grid: U32, ...mapa(32, 6, 3) } };
export const PLACA = "#071311";                    // la placa: la noche del original, un paso más clara
const PIEZA = { 1: "b1", 2: "b2", 3: "b3", C: "cinta", f: "cinta", a: "asta", r: "brazo" };
const FOLD = "#5DB077";

const hex = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
const toHex = (c) => "#" + c.map((v) => Math.round(v).toString(16).padStart(2, "0")).join("").toUpperCase();
const mix = (a, b, t) => toHex(hex(a).map((v, i) => v + (hex(b)[i] - v) * t));
function sample(g, x, y) {
  const dx = g.x2 - g.x1, dy = g.y2 - g.y1;
  const t = Math.max(0, Math.min(1, ((x - g.x1) * dx + (y - g.y1) * dy) / (dx * dx + dy * dy)));
  const k = g.stops.findIndex(([o]) => o >= t);
  if (k <= 0) return g.stops[Math.max(k, 0)][1];
  const [[o0, c0], [o1, c1]] = [g.stops[k - 1], g.stops[k]];
  return mix(c0, c1, (t - o0) / (o1 - o0));
}
/** Color del píxel (i, j) de la retícula de `n` px, o null si es placa. */
export function colorPixel(n, ch, i, j) {
  if (!PIEZA[ch]) return null;
  const { S, OX, OY } = PIXEL[n];
  const c = sample(GRAD[PIEZA[ch]], 668 + (i + 0.5 - OX) / S, 236 + (j + 0.5 - OY) / S);
  return ch === "f" ? mix(c, FOLD, 0.85) : c;
}
/** El icono de `n` px (16 o 32) en SVG, sobre su placa (esquinas de n/5,3 px). */
export function svgPixel(n) {
  const rects = PIXEL[n].grid.flatMap((row, j) => [...row].map((ch, i) => { const c = colorPixel(n, ch, i, j);
    return c ? `<rect x="${i}" y="${j}" width="1" height="1" fill="${c}"/>` : ""; })).join("");
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${n} ${n}" width="${n}" height="${n}" shape-rendering="crispEdges" role="img" aria-label="Finanzer"><rect width="${n}" height="${n}" rx="${n === 16 ? 3 : 6}" fill="${PLACA}"/>${rects}</svg>\n`;
}
