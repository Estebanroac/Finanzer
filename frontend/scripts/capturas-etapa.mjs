#!/usr/bin/env node
/**
 * Versiona las capturas de la última pasada del e2e para una etapa del rediseño:
 * copia frontend/test-results/capturas/*.png (o solo las que empiezan por <prefijo>) a docs/rediseno/capturas-<etapa>/,
 * comprimidas a WebP (≤ 300 KB).
 *
 *   npx playwright test e2e/v2/home-screens.spec.ts && npm run capturas:etapa -- e4 portada
 *
 * El e2e nunca escribe en archivos versionados: las capturas de cada pasada quedan en test-results (ignorada).
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { compress } from "./capturas-lib.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const [etapa, prefix = ""] = process.argv.slice(2);
if (!etapa || !/^[a-z0-9-]+$/i.test(etapa)) {
  console.error("uso: npm run capturas:etapa -- <etapa> [prefijo]   (p. ej. e4 portada)");
  process.exit(2);
}
const src = path.join(ROOT, "test-results", "capturas");
const dst = path.join(ROOT, "..", "docs", "rediseno", `capturas-${etapa.toLowerCase()}`);
const files = fs.existsSync(src) ? fs.readdirSync(src).filter((f) => f.endsWith(".png") && f.startsWith(prefix)) : [];
if (!files.length) {
  console.error(`sin capturas en ${path.relative(ROOT, src)}${prefix ? ` que empiecen por «${prefix}»` : ""}: ejecuta antes el e2e`);
  process.exit(1);
}
fs.mkdirSync(dst, { recursive: true });
// Comprimidas al copiar (revisión del PM: ninguna captura pesada en el repositorio): WebP ≤ 300 KB
// (scripts/capturas-lib.mjs). Un prefijo acabado en «-» (p. ej. «e3-») no pasa al nombre versionado.
let bytes = 0;
for (const f of files) {
  const name = (prefix.endsWith("-") ? f.slice(prefix.length) : f).replace(/\.png$/, ".webp");
  const { buffer } = await compress(path.join(src, f));
  fs.writeFileSync(path.join(dst, name), buffer);
  bytes += buffer.length;
}
console.log(`capturas:etapa: ${files.length} capturas → ${path.relative(path.join(ROOT, ".."), dst)} (WebP, ${Math.round(bytes / 1024)} KB en total)`);
