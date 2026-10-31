// Verificación V1: junta los resultados de e2e/v1 (un JSON por ticker × proyecto × tema, en v1-results/) en la matriz
// ticker × página × navegador × tamaño × tema de docs/rediseno/verificacion/V1_matriz.md.
// Uso: node scripts/v1-matriz.mjs [carpeta de resultados] [archivo de salida]
import * as fs from "node:fs";
import * as path from "node:path";

const dir = process.argv[2] || "v1-results";
const out = process.argv[3] || "../docs/rediseno/verificacion/V1_matriz.md";
const PAGES = ["historia", "empresa", "negocio", "accion", "calidad", "valor", "rivales", "riesgos", "actualidad", "conclusion"];
// La portada (e2e/v1/portada.spec.ts): sus filas son las 3 listas × 4 periodos del cintillo.
const HOME = "PORTADA";
const HOME_PAGES = ["1D", "1S", "1M", "6M"].flatMap((p) => ["most_traded", "gainers", "losers"].map((l) => `${l}·${p}`));
const pagesOf = (t) => (t === HOME ? HOME_PAGES : PAGES);
const BROWSERS = ["chromium", "webkit", "firefox"], SIZES = ["1440", "1024", "768", "375"], THEMES = ["light", "dark"];
const COLS = BROWSERS.flatMap((b) => SIZES.map((s) => `${b}-${s}`)).flatMap((p) => THEMES.map((t) => [p, t]));

const runs = fs.readdirSync(dir).filter((f) => f.endsWith(".json")).map((f) => JSON.parse(fs.readFileSync(path.join(dir, f), "utf8")));
const cell = new Map();      // `${ticker}|${page}|${project}|${theme}` → resultado de la página
const blockedHosts = new Map();
for (const r of runs) for (const p of r.results) {
  cell.set(`${r.ticker}|${p.page}|${r.project}|${r.theme}`, p);
  for (const h of p.blocked) blockedHosts.set(h, (blockedHosts.get(h) ?? 0) + 1);
}
const tickers = [...new Set(runs.map((r) => r.ticker))].sort();
// Navegadores sin ningún resultado: «—» en la matriz y su motivo (V1_NO_EJECUTADO="firefox: motivo; …").
const notRun = BROWSERS.filter((b) => !runs.some((r) => r.project.startsWith(`${b}-`)));
const notRunWhy = Object.fromEntries((process.env.V1_NO_EJECUTADO ?? "").split(";").filter((x) => x.includes(":"))
  .map((x) => [x.slice(0, x.indexOf(":")).trim(), x.slice(x.indexOf(":") + 1).trim()]));
const nPages = tickers.reduce((n, t) => n + pagesOf(t).length, 0);
const total = nPages * COLS.length;
const done = [...cell.values()];
const fails = [...cell.entries()].filter(([, p]) => !p.ok);

const L = [];
L.push("# V1 · panel completo sin red: matriz", "");
L.push(`*Generada por \`frontend/scripts/v1-matriz.mjs\` a partir de \`e2e/v1/panel.spec.ts\` (\`playwright.v1.config.ts\`), ${new Date().toISOString().slice(0, 10)}.*`, "");
L.push(`Build de producción servido por el replay (fixtures del panel, sin red: toda petición fuera de localhost se corta). ${tickers.filter((t) => t !== HOME).length} tickers × ${PAGES.length} páginas (la historia y las 9 de profundidad)${tickers.includes(HOME) ? ` y la portada (${HOME_PAGES.length} combinaciones de lista y periodo del cintillo)` : ""} × 3 navegadores (Chromium, WebKit, Firefox) × 4 anchos (1440, 1024, 768, 375 px) × 2 temas = **${total} páginas**.`, "");
L.push("Por página: sin errores de consola, sin excepciones no capturadas, sin peticiones fallidas inesperadas (a localhost), simetría con huecos internos y desbordamiento (también dentro de tarjetas y tablas), letra ≥ 12 px y axe (WCAG 2 A/AA) sin infracciones graves ni críticas. SPY (ETF): cada página muestra el motivo del motor; su 422 del análisis es la respuesta esperada.", "");
L.push("## Resumen", "");
const runnable = nPages * COLS.filter(([p]) => !notRun.some((b) => p.startsWith(`${b}-`))).length;
L.push(`- Páginas comprobadas: **${done.length} de ${total}**${notRun.length ? ` (${runnable} en los navegadores ejecutados)` : ""}`);
L.push(`- Correctas: **${done.filter((p) => p.ok).length}** · con fallos: **${fails.length}**`);
const byCheck = {};
for (const [, p] of fails) for (const k of Object.keys(p.problems)) byCheck[k] = (byCheck[k] ?? 0) + 1;
if (Object.keys(byCheck).length) L.push(`- Fallos por comprobación: ${Object.entries(byCheck).map(([k, v]) => `${k} ${v}`).join(" · ")}`);
if (notRun.length) L.push(`- Sin ejecutar: ${notRun.map((b) => `**${b}** (${notRunWhy[b] ?? "sin resultados"})`).join("; ")}. Sus columnas van con «—».`);
L.push(`- Peticiones externas cortadas (sin red), por host: ${blockedHosts.size ? [...blockedHosts.entries()].sort((a, b) => b[1] - a[1]).map(([h, n]) => `${h} (${n})`).join(", ") : "ninguna"}`, "");

L.push("## Matriz", "");
L.push("✓ correcta · ✗ con fallos (detalle abajo) · «·» falta el resultado · «—» navegador sin ejecutar. Columnas: navegador (C Chromium, W WebKit, F Firefox) y ancho; en cada celda, claro y oscuro.", "");
const head = BROWSERS.flatMap((b) => SIZES.map((s) => `${b[0].toUpperCase()}${s}`));
for (const t of tickers) {
  L.push(`### ${t}`, "");
  L.push(`| página | ${head.join(" | ")} |`);
  L.push(`|---|${head.map(() => ":-:").join("|")}|`);
  for (const pg of pagesOf(t)) {
    const cells = BROWSERS.flatMap((b) => SIZES.map((s) => THEMES.map((th) => {
      const p = cell.get(`${t}|${pg}|${b}-${s}|${th}`);
      return notRun.includes(b) ? "—" : p ? (p.ok ? "✓" : "✗") : "·";
    }).join("")));
    L.push(`| ${pg} | ${cells.join(" | ")} |`);
  }
  L.push("");
}

L.push("## Fallos", "");
if (!fails.length) L.push("Ninguno.");
for (const [k, p] of fails.sort()) {
  const [t, pg, proj, th] = k.split("|");
  L.push(`- **${t} · ${pg} · ${proj} · ${th}**`);
  for (const [c, list] of Object.entries(p.problems)) L.push(`  - ${c}: ${list.slice(0, 5).map((x) => `\`${String(x).replace(/`/g, "'")}\``).join("; ")}`);
}
fs.mkdirSync(path.dirname(out), { recursive: true });
fs.writeFileSync(out, L.join("\n") + "\n");
console.log(`${out}: ${done.length}/${total} páginas, ${fails.length} con fallos`);
