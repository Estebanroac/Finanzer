// Tokens de marca (--brand-*) del logo del usuario: la familia menta y esmeralda del original, en los dos temas (el
// usuario: «el verde definitivo es el de la versión oscura… tanto para tono claro como oscuro»). No sustituyen a los
// verdes de lectura de la web (--good y familia). Reglas de uso:
//  · el menta, como relleno, con el texto en tinta oscura (la noche del logo);
//  · en claro, el menta frente al papel no llega a 3:1: el relleno lleva un filo del verde de la familia que sí llega;
//  · el texto de marca sobre papel claro, en el tono de la familia que llega a 4,5:1;
//  · el color nunca va solo: el botón dice lo que hace.
import { BRAND, contrast } from "./usuario.mjs";
import { fileURLToPath } from "url";

const NIGHT = "#071311";   // la placa del logo: la noche del original (#030A0A) un paso más clara
export const TOKENS = {
  claro: { "--brand": BRAND["mint-300"], "--brand-on": BRAND.night, "--brand-edge": BRAND["green-600"],
    "--brand-ink": BRAND["green-700"], "--brand-accent": BRAND["green-600"], "--brand-night": NIGHT },
  oscuro: { "--brand": BRAND["mint-300"], "--brand-on": BRAND.night, "--brand-edge": BRAND["mint-300"],
    "--brand-ink": BRAND["mint-300"], "--brand-accent": BRAND["mint-300"], "--brand-night": NIGHT },
};
export const PALETA = Object.fromEntries(Object.entries(BRAND).map(([k, v]) => [`--brand-${k}`, v]));
const SUP = { claro: { paper: "#F7F6F2", surface: "#FFFFFF" }, oscuro: { paper: "#16181B", surface: "#1E2124" } };

/** Los pares que tienen que cumplir: [qué, primer plano, fondo, mínimo]. */
export function pares() {
  return Object.entries(TOKENS).flatMap(([tema, t]) => [
    [`${tema} · texto del botón (tinta) sobre el menta`, t["--brand-on"], t["--brand"], 4.5],
    [`${tema} · el botón (su filo) frente a la cabecera`, t["--brand-edge"], SUP[tema].surface, 3],
    [`${tema} · texto de marca sobre el papel`, t["--brand-ink"], SUP[tema].paper, 4.5],
    [`${tema} · texto de marca sobre la superficie`, t["--brand-ink"], SUP[tema].surface, 4.5],
    [`${tema} · acento gráfico sobre el papel`, t["--brand-accent"], SUP[tema].paper, 3],
  ]).map(([q, a, b, min]) => ({ q, a, b, c: +contrast(a, b).toFixed(2), min }));
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  console.log(TOKENS);
  for (const r of pares()) console.log(`${r.c >= r.min ? "ok " : "NO "} ${r.c.toFixed(2).padStart(5)}:1 (≥ ${r.min})  ${r.q}  ${r.a} / ${r.b}`);
}
