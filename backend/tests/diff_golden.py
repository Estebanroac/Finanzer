"""
Diferencias entre el comportamiento ACTUAL (desde fixtures) y los golden.

    cd finanzer_next/backend
    python3 tests/diff_golden.py                  # los 6 tickers, entorno local
    python3 tests/diff_golden.py --env panel      # panel de referencia (ruta de producción)
    python3 tests/diff_golden.py NFLX SNOW        # algunos
    python3 tests/diff_golden.py --full           # sin recortar listas/diff de PDF
    python3 tests/diff_golden.py --regenerate     # reescribe golden (pide confirmación)
    python3 tests/diff_golden.py --regenerate --yes NFLX

Por ticker muestra `campo: anterior → nuevo`, agrupado por bloque (score,
Piotroski, Altman, DCF, grid, alertas, métricas, otros) y el diff del texto
del PDF. Código de salida 1 si hay diferencias (útil en CI), 0 si no.

Los golden describen el comportamiento ACTUAL (con sus bugs), no el correcto.
Regenerarlos es una decisión explícita: nunca ocurre de forma automática.
"""
import argparse
import difflib
import json
import logging
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fixture_backend as fb  # noqa: E402

BLOCKS = [
    ("score", ("score", "company_type", "is_growth", "financial_health")),
    ("piotroski", ("piotroski_f",)),
    ("altman", ("altman_z",)),
    ("dcf", ("dcf", "graham_number", "graham_margin")),
    ("grid", ("sensitivity",)),
    ("alertas", ("alerts",)),
    ("métricas", ("key_metrics", "ratios")),
]
_BLOCK_OF = {k: name for name, keys in BLOCKS for k in keys}
_MISSING = "∅"


def _flatten(obj, prefix=""):
    out = {}
    if isinstance(obj, dict):
        if not obj and prefix:
            out[prefix] = {}
        for k, v in obj.items():
            out.update(_flatten(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(obj, list):
        if not obj and prefix:
            out[prefix] = []
        for i, v in enumerate(obj):
            out.update(_flatten(v, f"{prefix}[{i}]"))
    else:
        out[prefix] = obj
    return out


def _fmt(v, full):
    s = _MISSING if v is _MISSING else json.dumps(v, ensure_ascii=False)
    return s if full or len(s) <= 90 else s[:87] + "..."


def diff_analysis(old, new):
    """{bloque: [(ruta, anterior, nuevo)]} sobre valores ya normalizados."""
    fo, fn = _flatten(old), _flatten(new)
    groups = {}
    for path in sorted(set(fo) | set(fn)):
        a, b = fo.get(path, _MISSING), fn.get(path, _MISSING)
        if a == b:
            continue
        top = path.split(".", 1)[0].split("[", 1)[0]
        groups.setdefault(_BLOCK_OF.get(top, "otros"), []).append((path, a, b))
    return groups


def diff_text(old, new, full, limit=60):
    lines = list(difflib.unified_diff(old.splitlines(), new.splitlines(),
                                      "golden", "actual", n=0, lineterm=""))
    if not full and len(lines) > limit:
        lines = lines[:limit] + [f"... ({len(lines) - limit} líneas más; usa --full)"]
    return lines


def load_golden(sym, golden_dir):
    jpath, tpath = fb.golden_paths(sym, golden_dir)
    if not os.path.isfile(jpath):
        return None, None
    with open(jpath, encoding="utf-8") as fh:
        gj = json.load(fh)
    with open(tpath, encoding="utf-8") as fh:
        gt = fh.read()
    return gj, gt


def write_golden(sym, analysis, text, golden_dir):
    os.makedirs(golden_dir, exist_ok=True)
    jpath, tpath = fb.golden_paths(sym, golden_dir)
    with open(jpath, "w", encoding="utf-8") as fh:
        fh.write(fb.stable_json(analysis))
    with open(tpath, "w", encoding="utf-8") as fh:
        fh.write(text)
    return jpath, tpath


def report(sym, gj, gt, analysis, text, full):
    """Imprime las diferencias de un ticker; devuelve True si hay alguna."""
    print(f"\n{'═' * 70}\n {sym}\n{'═' * 70}")
    if gj is None:
        print("  (sin golden: ejecuta con --regenerate para crearlo)")
        return True
    new = json.loads(fb.stable_json(analysis))
    groups = diff_analysis(gj, new)
    pdf_lines = diff_text(gt, text, full)
    if not groups and not pdf_lines:
        print("  sin cambios")
        return False
    order = [name for name, _ in BLOCKS] + ["otros"]
    for name in order:
        items = groups.get(name)
        if not items:
            continue
        print(f"\n  [{name}] {len(items)} cambio(s)")
        shown = items if full else items[:40]
        for path, a, b in shown:
            print(f"    {path}: {_fmt(a, full)} → {_fmt(b, full)}")
        if len(shown) < len(items):
            print(f"    ... ({len(items) - len(shown)} más; usa --full)")
    if pdf_lines:
        print(f"\n  [pdf] texto del informe")
        for line in pdf_lines:
            if not line.startswith(("---", "+++")):
                print(f"    {line}")
    return True


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tickers", nargs="*")
    ap.add_argument("--full", action="store_true", help="no recortar listados")
    ap.add_argument("--regenerate", action="store_true", help="reescribir los golden (explícito)")
    ap.add_argument("--yes", action="store_true", help="confirmar --regenerate sin preguntar")
    ap.add_argument("--env", default=fb.DEFAULT_ENV, choices=fb.ENVS + (fb.PANEL_ENV,), help="juego de fixtures/golden")
    args = ap.parse_args(argv)
    logging.disable(logging.CRITICAL)

    syms = [t.upper() for t in args.tickers] or fb.env_tickers(args.env)
    gdir = fb.golden_dir(args.env)
    outputs = fb.compute_outputs(syms, fb.fixtures_dir(args.env))
    print(f"entorno: {args.env}")
    any_diff = False
    current = {}
    for sym in syms:
        analysis, pdf = outputs[sym]
        text = fb.pdf_text(pdf)
        current[sym] = (analysis, text)
        gj, gt = load_golden(sym, gdir)
        any_diff |= report(sym, gj, gt, analysis, text, args.full)

    if args.regenerate:
        if not args.yes:
            ans = input(f"\n¿Reescribir los golden [{args.env}] de {', '.join(syms)} con el comportamiento actual? "
                        "Escribe SI para confirmar: ")
            if ans.strip() != "SI":
                print("Cancelado: no se escribió nada.")
                return 2
        for sym in syms:
            jpath, tpath = write_golden(sym, *current[sym], gdir)
            print(f"golden escrito: {os.path.relpath(jpath)} , {os.path.relpath(tpath)}")
        return 0

    print("\nResultado:", "HAY diferencias" if any_diff else "sin diferencias")
    return 1 if any_diff else 0


if __name__ == "__main__":
    sys.exit(main())
