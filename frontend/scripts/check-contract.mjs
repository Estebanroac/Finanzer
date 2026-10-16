#!/usr/bin/env node
/**
 * Etapa 9b — test de contrato: falla si el frontend lee un campo que el backend no expone.
 *
 * La web solo puede leer lo que declaran los tipos de src/lib/api.ts (tsc en modo
 * strict impide leer cualquier otra cosa). Este script recorre el tipo
 * `StockAnalysis` con el type checker de TypeScript y lo contrasta con salidas
 * REALES del backend (JSON de /api/analysis):
 *   · cada propiedad obligatoria debe estar en todas las muestras;
 *   · cada propiedad opcional debe aparecer en alguna muestra (si no, la web lee
 *     un campo que el backend nunca expone);
 *   · el tipo de cada valor debe encajar (string, number, boolean, literales como
 *     los tonos y estados, arrays, objetos, Record, null).
 *
 *   node scripts/check-contract.mjs [--strict-unions] [dir-con-json ...]
 * --strict-unions exige además que las muestras cubran cada caso de las uniones
 * discriminadas (el pytest añade una muestra forzada con categoría no concluyente).
 * Sin argumentos usa los golden del backend (backend/tests/golden/{local,panel}; fase 1: D8 retiró prod) y las
 * muestras forzadas (backend/tests/golden/forzados, tests/contract_forced.py).
 * backend/tests/test_frontend_contract.py lo ejecuta sobre las salidas actuales.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const API = path.join(ROOT, "src/lib/api.ts");
const ROOT_TYPE = "StockAnalysis";

function loadSamples(dirs) {
  const out = [];
  for (const d of dirs) {
    for (const f of fs.readdirSync(d).filter((x) => x.endsWith(".json")).sort()) {
      const value = JSON.parse(fs.readFileSync(path.join(d, f), "utf8"));
      if (value.__http_error__) continue;   // petición rechazada (SPY): no es un análisis
      out.push({ name: `${path.basename(d)}/${f}`, value });
    }
  }
  return out;
}

export function check(dirs, { strictUnions = false } = {}) {
  const program = ts.createProgram([API], { strict: true, target: ts.ScriptTarget.ES2020, noEmit: true });
  const checker = program.getTypeChecker();
  const sf = program.getSourceFile(API);
  const decl = sf.statements.find((s) => ts.isInterfaceDeclaration(s) && s.name.text === ROOT_TYPE);
  if (!decl) throw new Error(`no encuentro ${ROOT_TYPE} en ${API}`);
  const rootType = checker.getTypeAtLocation(decl.name);
  const samples = loadSamples(dirs);
  if (!samples.length) throw new Error(`sin muestras JSON en ${dirs.join(", ")}`);

  const errors = [];
  const notes = [];
  const err = (p, msg) => errors.push(`${p}: ${msg}`);
  const F = ts.TypeFlags;

  function parts(t) { return t.isUnion() ? t.types : [t]; }

  function walk(type, vals, p) {
    // vals: [{v, from}] valores reales en esta ruta
    if (!vals.length) return;
    const members = parts(type);
    const allowsNull = members.some((m) => m.flags & F.Null);
    const nonNull = members.filter((m) => !(m.flags & (F.Null | F.Undefined)));
    for (const { v, from } of vals) {
      if (v === null) {
        if (!allowsNull) err(p, `null en ${from}, pero el tipo no admite null`);
        continue;
      }
      if (!nonNull.some((m) => accepts(m, v))) {
        err(p, `valor ${JSON.stringify(v).slice(0, 60)} (${from}) no encaja en ${checker.typeToString(type)}`);
      }
    }
    // Recursión en arrays y objetos con el miembro que corresponde
    const arrMember = nonNull.find((m) => checker.isArrayType(m));
    if (arrMember) {
      const elem = checker.getTypeArguments(arrMember)[0];
      walk(elem, vals.filter((x) => Array.isArray(x.v)).flatMap((x) => x.v.map((e) => ({ v: e, from: x.from }))), `${p}[]`);
    }
    const objMembers = nonNull.filter((m) => (m.flags & (F.Object | F.Intersection)) && !checker.isArrayType(m));
    if (objMembers.length) {
      const objs = vals.filter((x) => x.v && typeof x.v === "object" && !Array.isArray(x.v));
      if (objMembers.length === 1) {
        walkObject(objMembers[0], objs, p);
      } else {
        // Unión discriminada: cada valor va al primer miembro que encaja (campos
        // obligatorios presentes y discriminantes literales iguales).
        const groups = objMembers.map(() => []);
        for (const o of objs) {
          const i = objMembers.findIndex((m) => fits(m, o.v));
          if (i < 0) err(p, `valor (${o.from}) no encaja en ningún miembro de ${checker.typeToString(type)}`);
          else groups[i].push(o);
        }
        objMembers.forEach((m, i) => {
          if (!groups[i].length) {
            (strictUnions ? err : (q, msg) => notes.push(`${q}: ${msg}`))(
              p, `ninguna muestra cubre el caso ${checker.typeToString(m)}`);
          }
          walkObject(m, groups[i], p);
        });
      }
    }
  }

  function fits(m, v) {
    for (const prop of checker.getPropertiesOfType(m)) {
      const name = prop.getName();
      const has = Object.prototype.hasOwnProperty.call(v, name);
      if (!(prop.flags & ts.SymbolFlags.Optional) && !has) return false;
      const lits = parts(checker.getTypeOfSymbol(prop)).filter((t) => t.flags & F.StringLiteral);
      if (has && lits.length && !lits.some((t) => t.value === v[name])) return false;
    }
    return true;
  }

  function accepts(m, v) {
    if (m.flags & (F.Any | F.Unknown)) return true;
    if (m.flags & F.StringLiteral) return v === m.value;
    if (m.flags & F.NumberLiteral) return v === m.value;
    if (m.flags & F.BooleanLiteral) return v === (checker.typeToString(m) === "true");
    if (m.flags & F.String) return typeof v === "string";
    if (m.flags & F.Number) return typeof v === "number";
    if (m.flags & F.Boolean) return typeof v === "boolean";
    if (checker.isArrayType(m)) return Array.isArray(v);
    if (m.flags & (F.Object | F.Intersection)) return typeof v === "object" && !Array.isArray(v);
    return false;
  }

  function walkObject(type, objs, p) {
    if (!objs.length) return;
    const index = checker.getIndexInfosOfType(type).find((i) => i.keyType.flags & F.String);
    if (index) {
      walk(index.type, objs.flatMap((o) => Object.entries(o.v).map(([k, v]) => ({ v, from: `${o.from} (${k})` }))),
        `${p}{}`);
    }
    for (const prop of checker.getPropertiesOfType(type)) {
      const name = prop.getName();
      const optional = !!(prop.flags & ts.SymbolFlags.Optional);
      const ptype = checker.getTypeOfSymbol(prop);
      const present = objs.filter((o) => Object.prototype.hasOwnProperty.call(o.v, name));
      const where = `${p}.${name}`;
      if (!optional && present.length !== objs.length) {
        const miss = objs.filter((o) => !Object.prototype.hasOwnProperty.call(o.v, name)).map((o) => o.from);
        err(where, `campo obligatorio ausente en ${miss.slice(0, 3).join(", ")}${miss.length > 3 ? "…" : ""}`);
      }
      if (optional && !present.length) err(where, "el backend nunca expone este campo (declarado opcional)");
      walk(ptype, present.map((o) => ({ v: o.v[name], from: o.from })), where);
    }
  }

  walk(rootType, samples.map((s) => ({ v: s.value, from: s.name })), ROOT_TYPE);
  return { errors: [...new Set(errors)], notes: [...new Set(notes)], samples: samples.length };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const strictUnions = process.argv.includes("--strict-unions");
  const args = process.argv.slice(2).filter((a) => !a.startsWith("--"));
  // Fase 2b: con los golden van las muestras forzadas de los casos que ningún ticker cubre (tests/contract_forced.py).
  const dirs = args.length ? args : ["local", "panel", "forzados"].map((e) => path.join(ROOT, "..", "backend", "tests", "golden", e));
  const { errors, notes, samples } = check(dirs, { strictUnions });
  for (const n of notes) console.warn("aviso: " + n);
  if (errors.length) {
    console.error(`Contrato roto (${errors.length}) — el frontend declara campos que el backend no expone así:`);
    for (const e of errors.slice(0, 80)) console.error("  " + e);
    process.exit(1);
  }
  console.log(`check-contract: ${ROOT_TYPE} encaja con ${samples} salidas del backend`);
}
