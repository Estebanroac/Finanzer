#!/usr/bin/env node
/**
 * Etapa 9b — ningún umbral numérico literal en los componentes de análisis.
 *
 * Las lecturas (tono, banda, estado) llegan del backend en `display`; un componente
 * que compare un valor contra un número fijo (`pe > 25`, `pct >= 60`) estaría
 * decidiendo una lectura por su cuenta y podría contradecir al PDF. Este script
 * recorre el AST (compilador de TypeScript) de los archivos de análisis y falla si
 * encuentra:
 *   · un literal numérico como operando de <, <=, >, >= (salvo 0: signo/vacío);
 *   · un literal numérico en ===, !== distinto de 0 y 1 (1 = plural gramatical);
 *   · un array literal con dos o más números (una lista de cortes encubierta).
 * Revisión V6 (F1): en los archivos que solo pintan la serie de precios (PAINT_ONLY), además, ningún cálculo:
 *   · ni ×, ÷, % ni potencias (la rentabilidad, la base 100 y el tono los manda /api/v2/prices);
 *   · ni Math.* ni toFixed (redondear o formatear una cifra es del backend o de lib/format).
 * Las excepciones van en EXCEPTIONS con su justificación.
 *
 *   node scripts/check-analysis-literals.mjs        (lo ejecuta `npm run check`)
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

// Archivos de análisis: todo lo que pinta el análisis de una acción.
const SCOPE = [
  "src/app/stock",
  "src/components/StockHeader.tsx",
  "src/components/SummarySection.tsx",
  "src/components/TabsSection.tsx",
  "src/components/InfoTooltip.tsx",
  "src/components/ui.tsx",
  "src/components/charts.tsx",
  "src/lib/useGrow.ts",
  "src/components/tabs",
  "src/lib/api.ts",
  "src/lib/tooltips.ts",
  "src/app/v2",
  "src/v2/lib",
  "src/v2/components",
  "src/v2/home",             // E4: portada
  "src/v2/pages",            // E3: páginas de profundidad
];

// Revisión V6 (F1): solo pintan lo que manda /api/v2/prices (lib/price_returns.py, lo mismo que el PDF).
export const PAINT_ONLY = [
  "src/v2/lib/returns.ts",
  "src/v2/lib/chartEvents.ts",
  "src/v2/lib/prices.ts",
  "src/v2/components/PriceChart.tsx",
  "src/v2/components/PriceChartFull.tsx",
  "src/v2/components/PriceChartParts.tsx",
  "src/v2/pages/Accion.tsx",
];
const ARITHMETIC = new Set([
  ts.SyntaxKind.AsteriskToken, ts.SyntaxKind.SlashToken, ts.SyntaxKind.PercentToken, ts.SyntaxKind.AsteriskAsteriskToken,
  ts.SyntaxKind.AsteriskEqualsToken, ts.SyntaxKind.SlashEqualsToken,
]);

// "archivo:valor" -> justificación. Fuera de SCOPE quedan la portada de búsqueda, la
// barra de navegación y el overlay de carga (animación), que no leen el análisis.
const EXCEPTIONS = {
  // Vacío: hoy ningún literal necesita excepción. Formato: "ruta:valor": "justificación".
};

const RELATIONAL = new Set([
  ts.SyntaxKind.LessThanToken, ts.SyntaxKind.LessThanEqualsToken,
  ts.SyntaxKind.GreaterThanToken, ts.SyntaxKind.GreaterThanEqualsToken,
]);
const EQUALITY = new Set([
  ts.SyntaxKind.EqualsEqualsEqualsToken, ts.SyntaxKind.ExclamationEqualsEqualsToken,
  ts.SyntaxKind.EqualsEqualsToken, ts.SyntaxKind.ExclamationEqualsToken,
]);

function files(p) {
  const abs = path.join(ROOT, p);
  if (!fs.existsSync(abs)) return [];
  if (fs.statSync(abs).isFile()) return [p];
  return fs.readdirSync(abs).flatMap((f) => files(path.join(p, f)))
    .filter((f) => /\.(ts|tsx)$/.test(f));
}

function numValue(node) {
  // -5 llega como PrefixUnaryExpression(-, 5)
  if (ts.isNumericLiteral(node)) return { text: node.text, value: Number(node.text) };
  if (ts.isPrefixUnaryExpression(node) && node.operator === ts.SyntaxKind.MinusToken && ts.isNumericLiteral(node.operand)) {
    return { text: `-${node.operand.text}`, value: -Number(node.operand.text) };
  }
  return null;
}

/** Problemas de un archivo (`rel`, relativo a frontend/) con su código fuente `src`; `used` anota las excepciones usadas. */
export function scanSource(rel, src, used = new Set()) {
  const problems = [];
  const sf = ts.createSourceFile(rel, src, ts.ScriptTarget.Latest, true,
    rel.endsWith(".tsx") ? ts.ScriptKind.TSX : ts.ScriptKind.TS);
  const at = (node) => sf.getLineAndCharacterOfPosition(node.getStart()).line + 1;
  const report = (node, n, why) => {
    const key = `${rel}:${n.text}`;
    if (EXCEPTIONS[key]) { used.add(key); return; }
    problems.push(`${rel}:${at(node)}  ${why}: ${node.getText()}`);
  };
  const paintOnly = PAINT_ONLY.includes(rel.split(path.sep).join("/"));
  const calc = (node, why) => problems.push(`${rel}:${at(node)}  ${why}: ${node.getText().slice(0, 80)}`);
  const visit = (node) => {
    if (paintOnly && ts.isBinaryExpression(node) && ARITHMETIC.has(node.operatorToken.kind)) calc(node, "cálculo en un archivo que solo pinta");
    if (paintOnly && ts.isPropertyAccessExpression(node) && (node.getText().startsWith("Math.") || node.name.text === "toFixed"))
      calc(node, "cálculo o redondeo en un archivo que solo pinta");
    if (ts.isBinaryExpression(node)) {
      const op = node.operatorToken.kind;
      for (const side of [node.left, node.right]) {
        const n = numValue(side);
        if (!n) continue;
        if (RELATIONAL.has(op) && n.value !== 0) report(node, n, "umbral literal en una comparación");
        if (EQUALITY.has(op) && n.value !== 0 && n.value !== 1) report(node, n, "valor literal en una igualdad");
      }
    }
    if (ts.isArrayLiteralExpression(node)) {
      const nums = node.elements.map(numValue).filter(Boolean);
      if (nums.length >= 2) report(node, nums[0], "lista de números literales (¿cortes de banda?)");
    }
    ts.forEachChild(node, visit);
  };
  visit(sf);
  return problems;
}

export function scan() {
  const problems = [];
  const used = new Set();
  for (const rel of [...new Set(SCOPE.flatMap(files))]) {
    problems.push(...scanSource(rel, fs.readFileSync(path.join(ROOT, rel), "utf8"), used));
  }
  const stale = Object.keys(EXCEPTIONS).filter((k) => !used.has(k));
  return { problems, stale };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const { problems, stale } = scan();
  if (problems.length) {
    console.error("Umbrales numéricos literales en componentes de análisis (deben venir de display):");
    for (const p of problems) console.error("  " + p);
  }
  if (stale.length) {
    console.error("Excepciones que ya no corresponden a ningún literal (bórralas):");
    for (const k of stale) console.error("  " + k);
  }
  if (problems.length || stale.length) process.exit(1);
  console.log("check-analysis-literals: sin umbrales literales en los componentes de análisis");
}
