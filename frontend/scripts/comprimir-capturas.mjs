#!/usr/bin/env node
/**
 * npm run capturas:comprimir [-- carpeta…]
 * Comprime a WebP (scripts/capturas-lib.mjs) todas las capturas PNG/JPG de docs/rediseno/capturas-* (o de las carpetas
 * dadas), borra los originales y cambia sus referencias en los .md de docs/. Idempotente: un .webp ya comprimido y
 * por debajo del tope no se toca.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { compress, MAX_BYTES } from "./capturas-lib.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const DOCS = path.join(ROOT, "docs");
const args = process.argv.slice(2);
const dirs = args.length ? args.map((d) => path.resolve(d))
  : fs.readdirSync(path.join(DOCS, "rediseno")).filter((d) => d.startsWith("capturas-")).map((d) => path.join(DOCS, "rediseno", d));

const renamed = new Map();
let before = 0, after = 0, n = 0, over = [];
for (const dir of dirs) {
  if (!fs.existsSync(dir)) continue;
  for (const f of fs.readdirSync(dir)) {
    const p = path.join(dir, f);
    const ext = path.extname(f).toLowerCase();
    if (![".png", ".jpg", ".jpeg", ".webp"].includes(ext)) continue;
    const size = fs.statSync(p).size;
    if (ext === ".webp" && size <= MAX_BYTES) continue;
    const { buffer, width, quality } = await compress(p);
    const out = p.slice(0, -ext.length) + ".webp";
    fs.writeFileSync(out, buffer);
    if (out !== p) { fs.unlinkSync(p); renamed.set(f, path.basename(out)); }
    before += size; after += buffer.length; n++;
    if (buffer.length > MAX_BYTES) over.push(`${path.relative(ROOT, out)} (${Math.round(buffer.length / 1024)} KB)`);
    console.log(`${path.relative(ROOT, out)}: ${Math.round(size / 1024)} KB → ${Math.round(buffer.length / 1024)} KB (${width} px, q${quality})`);
  }
}
// Referencias en los .md de docs/
const walk = (d) => fs.readdirSync(d, { withFileTypes: true }).flatMap((e) => e.isDirectory() ? walk(path.join(d, e.name)) : [path.join(d, e.name)]);
let refs = 0;
for (const md of walk(DOCS).filter((f) => f.endsWith(".md"))) {
  let t = fs.readFileSync(md, "utf8"), changed = false;
  for (const [from, to] of renamed) if (t.includes(from)) { t = t.split(from).join(to); changed = true; refs++; }
  if (changed) fs.writeFileSync(md, t);
}
console.log(`capturas:comprimir: ${n} imágenes, ${Math.round(before / 1048576)} MB → ${Math.round(after / 1048576)} MB; ${refs} referencias cambiadas`);
if (over.length) console.log(`por encima de ${MAX_BYTES / 1024} KB:\n  ${over.join("\n  ")}`);
