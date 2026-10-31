// V7 (PM): «motor» no aparece en el texto que ve el lector de /v2. Recorre el código de /v2 (src/v2 y src/app/v2, sin
// tests, fixtures ni comentarios) y falla si encuentra la palabra. El texto que llega del backend se comprueba en el
// navegador (e2e/v2/vocabulario.spec.ts) y el del PDF nuevo en backend/tests/test_pdf_v2_contenido.py.
//   node scripts/check-v2-wording.mjs
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";

const ROOT = new URL("..", import.meta.url).pathname;
const DIRS = ["src/v2", "src/app/v2"];
const WORD = /\bmotor\b/;
// Pendiente de otra rama (vacío desde la fusión de P8b, que trajo la portada).
const PENDING = [];

const files = [];
const walk = (d) => {
  for (const f of readdirSync(d)) {
    const p = join(d, f);
    if (statSync(p).isDirectory()) { if (f !== "__fixtures__") walk(p); }
    else if (/\.(ts|tsx)$/.test(f) && !/\.test\.tsx?$/.test(f)) files.push(p);
  }
};
DIRS.forEach((d) => walk(join(ROOT, d)));

const hits = [], pending = [];
for (const f of files) {
  const rel = relative(ROOT, f);
  // sin comentarios de bloque ni de línea (los de línea, solo si no van dentro de una cadena con «://»)
  const src = readFileSync(f, "utf8").replace(/\/\*[\s\S]*?\*\//g, (m) => m.replace(/[^\n]/g, " "));
  src.split("\n").forEach((line, i) => {
    const code = line.replace(/(^|[^:])\/\/.*$/, "$1");
    if (WORD.test(code)) (PENDING.some((p) => rel.startsWith(p)) ? pending : hits).push(`  ${rel}:${i + 1}  ${code.trim().slice(0, 120)}`);
  });
}
if (pending.length) console.log(`check-v2-wording: ${pending.length} pendientes de la portada (P8b, E4)`);
if (hits.length) {
  console.error("«motor» en el texto de /v2 (dilo con «el análisis» o «Finanzer»):\n" + hits.join("\n"));
  process.exit(1);
}
console.log("check-v2-wording: sin «motor» en el texto de /v2");
