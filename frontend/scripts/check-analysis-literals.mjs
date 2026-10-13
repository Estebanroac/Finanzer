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
];

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

export function scan() {
  const problems = [];
  const used = new Set();
  for (const rel of [...new Set(SCOPE.flatMap(files))]) {
    const src = fs.readFileSync(path.join(ROOT, rel), "utf8");
    const sf = ts.createSourceFile(rel, src, ts.ScriptTarget.Latest, true,
      rel.endsWith(".tsx") ? ts.ScriptKind.TSX : ts.ScriptKind.TS);
    const report = (node, n, why) => {
      const key = `${rel}:${n.text}`;
      if (EXCEPTIONS[key]) { used.add(key); return; }
      const { line } = sf.getLineAndCharacterOfPosition(node.getStart());
      problems.push(`${rel}:${line + 1}  ${why}: ${node.getText()}`);
    };
    const visit = (node) => {
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
