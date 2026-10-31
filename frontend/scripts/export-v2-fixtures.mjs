#!/usr/bin/env node
// Exporta el análisis completo de los 8 tickers de verificación desde el servidor de replay
// (backend/tests/replay_server.py --env panel --port 8767) a src/v2/__fixtures__/.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const OUT = path.join(ROOT, "src/v2/__fixtures__");
const BASE = process.env.REPLAY_URL || "http://localhost:8767";
// F8 · E8: DOW es el caso del DCF directo de fiabilidad baja (con E8, AAPL ya no lo es: su DCF puntúa con fiabilidad alta)
const TICKERS = ["AAPL", "JPM", "O", "NEE", "XOM", "PLTR", "RIVN", "BCS", "DOW"];

fs.mkdirSync(OUT, { recursive: true });
for (const t of TICKERS) {
  const res = await fetch(`${BASE}/api/analysis/${t}`);
  if (!res.ok) throw new Error(`${t}: HTTP ${res.status}`);
  fs.writeFileSync(path.join(OUT, `${t}.json`), JSON.stringify(await res.json(), null, 1));
  console.log(`ok ${t}`);
}
