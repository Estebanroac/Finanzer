// V4b (punto 2): recuento de la información que falta en la web. Recorre /v2 en el replay con el build actual, ticker a
// ticker y página a página, y anota cada marca de ausencia con su contexto: «Sin dato», «—», «n. d.», celdas vacías y
// bloques con motivo de ausencia. La clasificación (a/b/c/presentación) la hace backend/tools/auditoria_faltantes.py.
//
//   (replay en marcha: backend/tests/replay_server.py --env panel --port 8767)
//   node scripts/auditoria-faltantes.mjs <salida.json> [AAPL,JPM,…]      BASE=http://localhost:8767 PAR=4
import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const OUT = process.argv[2];
if (!OUT) { console.error("uso: node scripts/auditoria-faltantes.mjs <salida.json> [TICKERS]"); process.exit(2); }
const BASE = process.env.BASE ?? "http://localhost:8767";
const PAR = Number(process.env.PAR ?? 4);
const HERE = path.dirname(fileURLToPath(import.meta.url));
const PANEL = path.join(HERE, "../../backend/tests/fixtures/panel");
const TICKERS = process.argv[3]?.split(",") ?? fs.readdirSync(PANEL).filter((d) => fs.statSync(path.join(PANEL, d)).isDirectory()).sort();
// Las nueve secciones (V4b: ya no hay página-historia; /v2/{T} abre «La empresa»).
const PAGES = ["empresa", "negocio", "accion", "calidad", "valor", "rivales", "riesgos", "actualidad", "conclusion"];

/** Se ejecuta en la página: cada marca de ausencia dentro de <main>. */
function marks() {
  const MARK = /^(—|–|-|Sin dato|sin dato|n\. ?d\.|N\/D|n\/d|—\s*%|NaN|undefined|null|Sin datos)$/;
  const txt = (e) => (e?.textContent ?? "").replace(/\s+/g, " ").trim();
  const heading = (el) => {
    for (let e = el; e && e.tagName !== "MAIN"; e = e.parentElement) {
      let s = e.previousElementSibling;
      while (s) {
        if (/^H[1-4]$/.test(s.tagName)) return txt(s);
        const h = s.querySelector?.("h1,h2,h3,h4");
        if (h) return txt(h);
        s = s.previousElementSibling;
      }
      const own = e.querySelector?.(":scope > h1, :scope > h2, :scope > h3, :scope > header h2, :scope > header h3");
      if (own && own !== el) return txt(own);
    }
    return "";
  };
  const where = (el) => {
    const tr = el.closest("tr");
    if (tr) {
      const table = tr.closest("table");
      const cells = [...tr.children];
      const cell = el.closest("td,th");
      const i = cells.indexOf(cell);
      const head = table?.querySelector("thead tr");
      const col = cell?.getAttribute("data-label") || (head && i >= 0 ? txt(head.children[i]) : "");
      const first = cells[0];
      const row = txt(first?.querySelector(".metric-name") ?? first);
      return { row: row.slice(0, 80), col, key: tr.getAttribute("data-key") ?? "" };
    }
    const dd = el.closest("dd");
    if (dd) return { row: txt(dd.previousElementSibling).slice(0, 80), col: "", key: "" };
    const tile = el.closest(".tile, .card");
    if (tile) return { row: txt(tile.querySelector(".muted, .small, dt, span")).slice(0, 80), col: "", key: "" };
    return { row: "", col: "", key: "" };
  };
  const out = [];
  for (const el of document.querySelectorAll("main *")) {
    if (el.closest("[aria-hidden='true'], .sr-only, [hidden]")) continue;
    const full = txt(el);
    const leaf = el.children.length === 0;
    // Celdas de maquetación de las gráficas (lightweight-charts dibuja en una tabla con lienzos): no son datos.
    const chartCell = el.tagName === "TD" && !!el.closest("table")?.querySelector("canvas");
    const emptyCell = el.tagName === "TD" && full === "" && el.children.length === 0 && !chartCell;
    // La celda «Quitar» de la fila de la propia empresa en Rivales no lleva botón: no es un dato.
    if (emptyCell && el.getAttribute("data-label") === "Quitar") continue;
    if ((leaf && MARK.test(full)) || emptyCell) {
      out.push({ kind: emptyCell ? "celda vacía" : full, text: "", ...where(el), sec: heading(el) });
    } else if (/\bmissing\b|row-missing|\bstate\b/.test(typeof el.className === "string" ? el.className : "") || el.hasAttribute("data-missing")) {
      // «el modelo no marca ninguna», «no detecta ninguno»: afirman que no hay, no son una ausencia
      if (/ning[uú]n|: 0\b|no deja notas/i.test(full)) continue;
      out.push({ kind: "bloque", text: full.slice(0, 240), ...where(el), sec: heading(el) });
    } else if (leaf && /^Sin dato\b/.test(full) && full.length > 8) {
      out.push({ kind: "motivo", text: full.slice(0, 240), ...where(el), sec: heading(el) });
    }
  }
  return out;
}

const browser = await chromium.launch();
const result = {};
const queue = [...TICKERS];
async function worker() {
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  for (let t; (t = queue.shift()); ) {
    result[t] = {};
    for (const p of PAGES) {
      const key = p || "historia";
      try {
        await page.goto(`${BASE}/v2/${t}${p ? "/" + p : ""}`, { waitUntil: "networkidle", timeout: 90_000 });
        await page.waitForSelector("main[aria-busy='false']", { timeout: 60_000 }).catch(() => {});
        // Rivales: espera a que no quede ninguno «en cola» ni «analizando» (el replay los calcula uno a uno).
        if (p === "rivales" || p === "") {
          await page.waitForFunction(() => !/En cola|Analizando…|Buscando rivales…/.test(document.querySelector("main")?.innerText ?? ""),
            null, { timeout: 120_000 }).catch(() => {});
        }
        if (p === "valor") {
          await page.waitForFunction(() => !/Calculando…/.test(document.querySelector("main")?.innerText ?? ""), null, { timeout: 30_000 }).catch(() => {});
        }
        await page.waitForTimeout(800);
        result[t][key] = await page.evaluate(marks);
      } catch (e) {
        result[t][key] = { error: String(e).slice(0, 200) };
      }
    }
    const n = Object.values(result[t]).reduce((s, v) => s + (Array.isArray(v) ? v.length : 0), 0);
    console.log(`${t}: ${n} marcas`);
  }
  await page.close();
}
await Promise.all(Array.from({ length: PAR }, worker));
await browser.close();
const ordered = Object.fromEntries(Object.keys(result).sort().map((k) => [k, result[k]]));
fs.writeFileSync(OUT, JSON.stringify(ordered, null, 1));
const total = Object.values(ordered).flatMap((pg) => Object.values(pg)).reduce((s, v) => s + (Array.isArray(v) ? v.length : 0), 0);
console.log(`${Object.keys(ordered).length} tickers, ${total} marcas → ${OUT}`);
