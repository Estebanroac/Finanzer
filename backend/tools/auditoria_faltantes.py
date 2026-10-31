"""
V4b (punto 2 del encargo del PM): clasificación de la información que falta en /v2 (el recuento lo hace
frontend/scripts/auditoria-faltantes.mjs sobre el replay y el build) y tablas para
docs/rediseno/verificacion/V4b_datos_faltantes.md.

    cd backend && ../.venv313/bin/python tools/auditoria_faltantes.py <antes.json[.gz]> <despues.json[.gz]> [--md salida.md]

Los recuentos de la revisión V4b están en docs/rediseno/verificacion/V4b_datos_faltantes/ (antes.json.gz,
despues.json.gz).

Cada marca (un «—», «Sin dato», «n. d.», celda vacía o bloque con motivo de ausencia) cae en una clase:
  · a  la fuente no lo publica o no aplica a este tipo de empresa: correcto, con el motivo;
  · b  el dato o su motivo existe en el análisis o en una fuente que ya usamos y se perdía (arreglo en el motor);
  · c  falta en los fixtures del replay pero el backend real lo trae (recaptura);
  · no es una ausencia: un bloque informativo o una celda de maquetación que el recuento recoge por su forma.
Y, aparte, «presentación»: el motor tiene el motivo y la página no lo pinta en su sitio (para E3, vía el PM).
Las reglas son explícitas (RULES, en orden); lo que ninguna cubre sale como «sin clasificar» para revisarlo a mano.
"""
import argparse
import collections
import functools
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

PAGES = ["historia", "empresa", "negocio", "accion", "calidad", "valor", "rivales", "riesgos", "actualidad",
         "conclusion"]
CLASSES = ["a", "b", "c", "no es una ausencia", "sin clasificar"]
# Sin SEC ni Finnhub por diseño (clase a): MC.PA no presenta en la SEC y Finnhub gratuito no cubre París; SPY es un ETF.
NO_SEC = {"MC.PA", "SPY"}
# Métricas con referencia de industria de Damodaran (config/industries.toml): las demás van sin ella (clase a).
DAMODARAN = {"pe", "ev_ebitda", "pb", "roe", "roic", "gross_margin", "operating_margin", "net_margin",
             "interest_coverage", "de"}

Rule = Tuple[str, str, Optional[bool], str]     # (clase, regla, presentación, por qué)
GOLDEN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "golden", "panel")


@functools.lru_cache(maxsize=None)
def _rows_after(sym: str) -> Dict[str, Dict[str, Any]]:
    """Filas de las tablas del golden del panel de la rama (después de los arreglos): para saber si una referencia de
    industria existe (b, se perdía) o no (a)."""
    path = os.path.join(GOLDEN, f"{sym}.json")
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        a = json.load(fh)
    return {r["key"]: r for s in ("valuation", "profitability", "solvency", "growth")
            for r in (((a.get("display") or {}).get("sections") or {}).get(s) or {}).get("rows") or []}


def _m(pat: str, s: str) -> bool:
    return re.search(pat, s or "", re.I) is not None


def classify(t: str, page: str, m: Dict[str, Any], phase: str = "despues") -> Rule:
    """(clase, nombre de la regla, ¿presentación?, explicación) de una marca. `phase` («antes» o «despues») solo
    cuenta en lo que un arreglo de esta rama cambió de clase (el motivo que faltaba ya está y queda la presentación)."""
    kind, text, row, col, key, sec = (m.get(k) or "" for k in ("kind", "text", "row", "col", "key", "sec"))
    blk = kind == "bloque" or kind == "motivo"
    # ── no es una ausencia ──
    if kind == "celda vacía" and col == "Quitar":
        return ("no es una ausencia", "rivales: celda «Quitar» de la propia empresa", None, "sin botón: no es un dato")
    if blk and _m(r"^(Cobertura: |Bloque de múltiplos|Fiabilidad |BPA frente a ingresos: |Eje descartado)", text):
        return ("no es una ausencia", "bloque informativo", None, "explica una cifra que está")
    if blk and _m(r"ning[uú]n|cobertura baja en", text):
        return ("no es una ausencia", "bloque informativo", None, "afirma que no hay (cero señales) o avisa")
    if blk and _m(r" · (Favorable|Desfavorable|Exigente|Atractivo|Muy caro|Prima|Descuento|En línea|Aceptable)|"
                  r" frente a ROTE \d| frente a ROE \d", text):
        return ("no es una ausencia", "bloque informativo", None, "lectura de un múltiplo de la rama")
    if kind == "motivo" and text.strip() == "Sin dato:":
        return ("no es una ausencia", "rótulo «Sin dato:» de un motivo", None, "el motivo va a continuación")
    # ── c: fixtures del replay ──
    if _m(r"sin fixtures en el replay", text):
        return ("c", "rivales sin fixtures en el replay", None, "el backend real analiza el rival en vivo")
    if _m(r"No incluido en la demo con datos grabados", text):
        return ("c", "rival fuera de la demo grabada (propio del replay)", False,
                "con datos reales se analiza al momento; el motivo lo dice")
    if _m(r"Yahoo no respondió", text):
        return ("c", "serie de 5 años sin fixture", None, "gráfica y rentabilidad por periodo")
    if _m(r"sin titulares de Finnhub", text):
        return (("a", "Finnhub gratuito no cubre la bolsa", False, "403 de Finnhub para MC.PA") if t == "MC.PA" else
                ("c", "titulares y calendario sin fixture", None, "Finnhub /company-news"))
    if _m(r"no presenta estados en la SEC|no presenta en la SEC", text):
        return (("a", "el emisor no presenta en la SEC", False, "sin 10-K/20-F") if t in NO_SEC else
                ("c", "segmentos sin fixture", None, "EDGAR (índice del 10-K/20-F)"))
    if page == "accion" and sec.startswith("Rentabilidad por periodo") and kind == "Sin dato" and t == "RIVN":
        return ("a", "cotiza desde hace menos del periodo", False, "RIVN salió a bolsa el 10-nov-2021: sin 5 años")
    if page == "accion" and sec.startswith("Rentabilidad por periodo") and kind == "Sin dato":
        return ("c", "serie de 5 años corta en el replay", None,
                "capturada 12 días después de la fecha de corte: no cubría 5 años antes de ella")
    if _m(r"serie del sector es sin dato", text):
        return (("b", "motivo perdido: serie del sector", True, "market_context sabía el porqué (cotiza en EUR)")
                if t == "MC.PA" else ("c", "ETF de sector sin fixture", None, "serie del ETF"))
    if page == "historia" and not row and not col and kind in ("—", "Sin dato") and \
            (sec.startswith("Frente a sus rivales") or sec.startswith("Qué puede salir mal")):
        return ("a", "cifra de relleno de la historia", True,
                "la fila de cifras del capítulo se completa con una caja «— / Sin dato» cuando hay menos cifras")
    if page == "historia" and sec.startswith("Frente a sus rivales") and col == "Calidad" and kind == "—":
        return ("a", "sin rivales propuestos (sin industria de referencia)", True,
                "V: referencia del mercado por política (benchmark.reason); el resumen de rivales pinta «—»")
    # ── b: el dato o su motivo existía y se perdía ──
    if page == "rivales" and kind == "Sin dato":
        return ("b", "rivales: motivo perdido en el resumen", None,
                "no aplica / no significativo se veía como «Sin dato» (analysis_queue.summary)")
    if kind in ("—", "celda vacía") and col in ("Industria", "Brecha") and key in ("de", "interest_coverage") \
            and _rows_after(t).get(key, {}).get("bench") not in (None, "—"):
        return ("b", "referencia de industria de D/E y cobertura sin cablear", None,
                "Damodaran la publica y el análisis la tiene (benchmark.values)")
    if _m(r"^(BPA|FCF): Sin dato$", text):
        return ("b", "motivo perdido: crecimiento sin tasa", None, "base ≤ 0 en la cobertura del score")
    if sec.startswith("ROIC − WACC") and _m(r"^Sin dato$", text or kind):
        return (("b", "motivo perdido: tarjeta ROIC − WACC", True, "no aplica al arquetipo (classify)")
                if phase == "antes" else
                ("a", "tarjeta ROIC − WACC que no aplica", True,
                 "charts.profitability.spread.text tiene el porqué (V4b); la tarjeta pinta «Sin dato»"))
    if re.search(r"descartados por ser de otro periodo: .*[a-z][A-Z]", text or ""):
        return ("b", "nombres internos de Yahoo en el aviso", None, "capitalLeaseObligations, commercialPaper")
    if blk and text.strip() in ("No aplica", "No aplica."):
        return ("b", "motivo perdido: «No aplica» sin porqué", None, "classify lo tenía (display._na_why)")
    # ── a: la fuente no lo publica o no aplica ──
    if blk and _m(r"^(BPA|FCF|Ingresos): (?!Sin dato$)|^Señales parciales: sin la serie", text):
        return ("a", "la fuente no lo publica", False, "con el motivo en su sitio")
    if blk and _m(r"No aplica|no aplica", text):
        return ("a", "no aplica a este tipo de empresa", False, "con el porqué en su sitio")
    if blk and _m(r"No significativ|no significativ|inicial ≤ 0|no es significativ", text):
        return ("a", "no significativo", False, "con el porqué en su sitio")
    if blk and _m(r"no desglosa ingresos por segmento|sin dos ejercicios comparables|sin ingresos consolidados|"
                  r"el proveedor no lo da|la fuente no lo devolvió|descartados por ser de otro periodo|"
                  r"sin industria de referencia|"
                  r"Sin dato: ", text):
        return ("a", "la fuente no lo publica", False, "con el motivo en su sitio")
    if kind in ("—", "celda vacía") and col in ("Industria", "Brecha", "Lectura", "Mercado"):
        why = ("Damodaran no publica referencia de industria de esta métrica" if key not in DAMODARAN else
               "referencia de industria sin dato para esta industria (Damodaran) o fila sin lectura")
        return ("a", "sin referencia de industria", True, why + "; la celda no lo dice")
    if page in ("calidad", "valor") and kind == "Sin dato" and row == "No aplica" and col == "Valor":
        return ("a", "ajuste del score que no aplica", True, "la tabla pinta «Sin dato» en el valor de un ajuste n/a")
    if page in ("valor",) and col == "Empresa" and (kind == "—" or (blk and text.strip() == "—")):
        return ("a", "múltiplo que no aplica (sin cifra por decisión)", False, "la fila dice «No aplica a …»")
    if page == "valor" and sec.startswith("Sensibilidad"):
        return ("a", "sensibilidad: columna de WACC recortada", True,
                "sensitivity.trimmed.note lo explica («WACC recortado en [6%, 20%]»); la tabla pinta la columna con «—»")
    if page == "negocio" and col == "CAGR" and kind == "celda vacía":
        return ("a", "margen sin CAGR (no se compone)", True, "celda vacía sin motivo")
    if page == "negocio" and col == "CAGR" and kind == "—":
        return ("a", "CAGR con base ≤ 0", True, "«—» sin motivo")
    if page == "negocio" and sec.startswith("Ejercicio") and kind == "—":
        return ("a", "EDGAR sin el concepto estándar (ficha del ejercicio)", True,
                "el motor da el porqué en display.extended.history_10y.rows[].reasons (V4b); la ficha no lo pinta")
    if page == "conclusion" and kind == "Sin dato":
        return ("a", "tarjeta de la conclusión que no aplica", True,
                "display.summary.cards: state no_aplica y el motivo en «bench»; la tarjeta pinta «Sin dato»")
    if page == "calidad" and sec.startswith("ROCE") and _m(r"^Sin dato$", text or kind):
        return ("a", "tarjeta ROCE que no aplica", True, "charts.profitability.roce.text tiene el porqué")
    if page == "calidad" and kind == "Sin dato" and sec.startswith("Reducción de deuda"):
        return ("a", "criterio de Piotroski sin deuda previa", False, "el detalle lo dice")
    return ("sin clasificar", "—", None, "")


def _walk(o, path, out):
    if isinstance(o, dict):
        st = o.get("state")
        if st in ("sin_dato", "no_aplica", "no_significativo"):
            why = o.get("text") or o.get("reason") or o.get("bench") or o.get("body") or o.get("note")
            out.append((path, st, bool(why)))
        for k, v in o.items():
            _walk(v, f"{path}.{k}", out)
    elif isinstance(o, list):
        for v in o:
            _walk(v, f"{path}[]", out)


def _nulls(o, path, out):
    if isinstance(o, dict):
        for k, v in o.items():
            if v is None:
                out.append(f"{path}.{k}")
            else:
                _nulls(v, f"{path}.{k}", out)
    elif isinstance(o, list):
        for v in o:
            _nulls(v, f"{path}[]", out)


def engine_counts(load) -> Dict[str, collections.Counter]:
    """Por bloque de display (sections.X, charts.X, extended.X, …): estados sin dato / no aplica / no significativo,
    los que no traen motivo, y los campos null de display.extended. `load(sym)` da el análisis (golden) o None."""
    out = collections.defaultdict(collections.Counter)
    for f in sorted(os.listdir(GOLDEN)):
        if not f.endswith(".json"):
            continue
        a = load(f[:-5])
        d = (a or {}).get("display")
        if not d:
            continue
        found = []
        _walk(d, "display", found)
        for path, st, why in found:
            blk = ".".join(path.replace("[]", "").split(".")[:3])
            out[blk][st] += 1
            if not why:
                out[blk][f"{st} sin motivo"] += 1
        nulls = []
        _nulls(d.get("extended") or {}, "display.extended", nulls)
        for n in nulls:
            out[".".join(n.replace("[]", "").split(".")[:3])]["null"] += 1
    return out


def tally(data: Dict[str, Any], phase: str):
    by_page = collections.defaultdict(collections.Counter)
    by_rule = collections.Counter()
    pres = collections.Counter()
    examples: Dict[Tuple[str, str], List[str]] = collections.defaultdict(list)
    unclassified = []
    for t, pages in data.items():
        for page, marks in pages.items():
            if not isinstance(marks, list):
                continue
            for m in marks:
                cls, rule, is_pres, why = classify(t, page, m, phase)
                by_page[page][cls] += 1
                by_rule[(cls, rule, why)] += 1
                if is_pres:
                    pres[(page, rule, why)] += 1
                ex = examples[(cls, rule)]
                if len(ex) < 3:
                    ex.append(f"{t} /{page}: {m.get('row') or m.get('sec')}{' · ' + m['col'] if m.get('col') else ''}"
                              f" «{(m.get('text') or m.get('kind'))[:90]}»")
                if cls == "sin clasificar":
                    unclassified.append((t, page, m))
    return by_page, by_rule, pres, examples, unclassified


def _table(before, after) -> List[str]:
    out = ["| Sección | " + " | ".join(f"{c} (antes → después)" for c in CLASSES) + " | Total |",
           "|---|" + "---:|" * (len(CLASSES) + 1)]
    tot_b, tot_a = collections.Counter(), collections.Counter()
    for p in PAGES:
        b, a = before.get(p, collections.Counter()), after.get(p, collections.Counter())
        tot_b.update(b)
        tot_a.update(a)
        out.append(f"| {p} | " + " | ".join(f"{b[c]} → {a[c]}" for c in CLASSES)
                   + f" | {sum(b.values())} → {sum(a.values())} |")
    out.append("| **Total** | " + " | ".join(f"**{tot_b[c]} → {tot_a[c]}**" for c in CLASSES)
               + f" | **{sum(tot_b.values())} → {sum(tot_a.values())}** |")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("antes")
    ap.add_argument("despues")
    ap.add_argument("--md", help="escribe las tablas en Markdown aquí")
    ap.add_argument("--ref", default="HEAD", help="los golden de «antes» (git show <ref>:…); los de «después», del disco")
    args = ap.parse_args(argv)
    import gzip

    def _load(path):
        with (gzip.open(path, "rt", encoding="utf-8") if path.endswith(".gz") else open(path, encoding="utf-8")) as fh:
            return json.load(fh)
    before, after = _load(args.antes), _load(args.despues)
    pb, rb, presb, exb, unb = tally(before, "antes")
    pa, ra, presa, exa, una = tally(after, "despues")
    lines = ["### Por sección y clase", ""] + _table(pb, pa) + ["", "### Por regla", "",
                                                                "| Clase | Regla | Antes | Después | Por qué |",
                                                                "|---|---|---:|---:|---|"]
    rules = sorted(set(rb) | set(ra), key=lambda k: (CLASSES.index(k[0]), -rb.get(k, 0), -ra.get(k, 0), k[1], k[2]))
    for k in rules:
        lines.append(f"| {k[0]} | {k[1]} | {rb.get(k, 0)} | {ra.get(k, 0)} | {k[2]} |")
    lines += ["", "### Ejemplos (antes)", ""]
    for (cls, rule), ex in sorted(exb.items(), key=lambda x: CLASSES.index(x[0][0])):
        lines.append(f"- **{cls} · {rule}**: " + "; ".join(ex))
    lines += ["", "### Presentación (después): el motor tiene el motivo y la página no lo pinta", "",
              "| Página | Regla | Marcas | Detalle |", "|---|---|---:|---|"]
    for (page, rule, why), n in sorted(presa.items(), key=lambda x: (-x[1], x[0])):
        lines.append(f"| {page} | {rule} | {n} | {why} |")
    import subprocess

    def at_ref(sym):
        r = subprocess.run(["git", "show", f"{args.ref}:backend/tests/golden/panel/{sym}.json"],
                           cwd=os.path.dirname(os.path.dirname(GOLDEN)), capture_output=True, text=True)
        return json.loads(r.stdout) if r.returncode == 0 else None

    def on_disk(sym):
        with open(os.path.join(GOLDEN, f"{sym}.json"), encoding="utf-8") as fh:
            return json.load(fh)
    eb, ea = engine_counts(at_ref), engine_counts(on_disk)
    cols = ["sin_dato", "sin_dato sin motivo", "no_aplica", "no_aplica sin motivo", "no_significativo",
            "no_significativo sin motivo", "null"]
    lines += ["", f"### Motor: display y display.extended de los {sum(f.endswith('.json') for f in os.listdir(GOLDEN))} golden del panel "
                  f"({args.ref} → rama)", "",
              "| Bloque | " + " | ".join(cols) + " |", "|---|" + "---:|" * len(cols)]
    for blk in sorted(set(eb) | set(ea)):
        b, a = eb.get(blk, collections.Counter()), ea.get(blk, collections.Counter())
        if not any(b[c] or a[c] for c in cols):
            continue
        lines.append(f"| {blk} | " + " | ".join(f"{b[c]} → {a[c]}" if b[c] != a[c] else f"{b[c]}" for c in cols) + " |")
    tb = collections.Counter(); ta = collections.Counter()
    for c in eb.values():
        tb.update(c)
    for c in ea.values():
        ta.update(c)
    lines.append("| **Total** | " + " | ".join(f"**{tb[c]} → {ta[c]}**" for c in cols) + " |")
    md = "\n".join(lines) + "\n"
    if args.md:
        with open(args.md, "w", encoding="utf-8") as fh:
            fh.write(md)
    else:
        sys.stdout.write(md)
    for name, un in (("antes", unb), ("después", una)):
        if un:
            print(f"\n{len(un)} sin clasificar ({name}):", file=sys.stderr)
            seen = collections.Counter((p, m.get("kind"), m.get("row"), m.get("col"), (m.get("text") or "")[:60],
                                        (m.get("sec") or "")[:30]) for _t, p, m in un)
            for k, n in seen.most_common(30):
                print(f"  {n} {k}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
