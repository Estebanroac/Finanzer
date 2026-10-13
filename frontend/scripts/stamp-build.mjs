#!/usr/bin/env node
/**
 * Etapa 9b — sello del contrato en el build estático.
 * Escribe out/build-stamp.json con el SHA-256 de src/lib/api.ts (los tipos del
 * contrato con el backend). build.sh lo compara con el api.ts del commit: si
 * alguien cambia el contrato y no reconstruye frontend/out, el deploy falla.
 */
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const api = fs.readFileSync(path.join(ROOT, "src/lib/api.ts"));
const stamp = { contract_sha256: crypto.createHash("sha256").update(api).digest("hex") };
fs.writeFileSync(path.join(ROOT, "out/build-stamp.json"), JSON.stringify(stamp, null, 2) + "\n");
console.log(`build-stamp: contrato ${stamp.contract_sha256.slice(0, 12)}…`);
