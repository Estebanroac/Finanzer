"""
Escaneo de comprobación de `fiabilidad/f10-margen-op` frente a la puerta de la v4 (los dos con tools/universe_scan.py
sobre las 543, el mismo día). Sin red: lee los análisis guardados de las dos cachés.

    cd backend
    ../../finanzer_next/.venv313/bin/python tools/f10_margen_op_comprobacion.py PUERTA_DIR RAMA_DIR [--json out.json]

Mide: tipos y niveles de calidad y de precio que cambian; el margen operativo que puntúa (fila de Rentabilidad); el
estado de la comprobación con Yahoo (`earnings_normalization.operating.check.status`), por qué y en cuántas; las
violaciones de cada regla en las dos.
"""
import argparse
import gzip
import json
import os
from collections import Counter


def _load(d, s):
    with gzip.open(os.path.join(d, f"{s}.analysis.json.gz"), "rt", encoding="utf-8") as fh:
        return json.load(fh)["analysis"]


def _summary(d, s):
    with open(os.path.join(d, f"{s}.json"), encoding="utf-8") as fh:
        return json.load(fh)


def _levels(a):
    c = (a.get("display") or {}).get("cover") or {}
    return ((c.get("quality") or {}).get("level"), (c.get("quality") or {}).get("score"),
            (c.get("price") or {}).get("level"), (c.get("price") or {}).get("score"))


def _op_row(a):
    return next(((x.get("metric"), x.get("value"), x.get("adjustment"))
                 for x in ((a.get("score") or {}).get("breakdown") or {}).get("Rentabilidad", {}).get("adjustments", [])
                 if str(x.get("metric") or "").startswith("Margen operativo")), None)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("before")
    ap.add_argument("after")
    ap.add_argument("--json")
    args = ap.parse_args(argv)
    syms = sorted({f[:-len(".analysis.json.gz")] for f in os.listdir(args.after) if f.endswith(".analysis.json.gz")}
                  & {f[:-len(".analysis.json.gz")] for f in os.listdir(args.before) if f.endswith(".analysis.json.gz")})
    cnt, rows, checks, rules = Counter(), [], Counter(), {}
    for s in syms:
        a, b = _load(args.before, s), _load(args.after, s)
        sa, sb = _summary(args.before, s), _summary(args.after, s)
        for k, r in (sb.get("results") or {}).items():
            rules.setdefault(k, Counter())["despues_" + r.get("state", "?")] += 1
        for k, r in (sa.get("results") or {}).items():
            rules.setdefault(k, Counter())["antes_" + r.get("state", "?")] += 1
        if "score" not in a or "score" not in b:
            continue
        la, lb = _levels(a), _levels(b)
        op = ((b.get("earnings_normalization") or {}).get("operating") or {})
        st = (op.get("check") or {}).get("status")
        checks[st or "sin bloque"] += 1
        d = {"symbol": s, "type": ((a.get("classification") or {}).get("archetype"),
                                   (b.get("classification") or {}).get("archetype")),
             "quality": (la[0], la[1], lb[0], lb[1]), "price": (la[2], la[3], lb[2], lb[3]),
             "op_row": (_op_row(a), _op_row(b)), "check": st, "gap": (op.get("check") or {}).get("gap"),
             "pieces_source": op.get("source"), "yahoo_quarterly": op.get("yahoo_quarterly"),
             "edgar": (b.get("data_provenance") or {}).get("edgar", {}).get("status")}
        cnt["empresas"] += 1
        cnt["tipo"] += d["type"][0] != d["type"][1]
        cnt["nivel_calidad"] += la[0] != lb[0]
        cnt["nivel_precio"] += la[2] != lb[2]
        cnt["fila_margen_operativo"] += d["op_row"][0] != d["op_row"][1]
        rows.append(d)
    print(json.dumps({"recuentos": dict(cnt), "comprobacion": dict(checks)}, ensure_ascii=False, indent=1))
    print("\nReglas (violaciones antes → después):")
    for k, c in sorted(rules.items()):
        print(f"  {k:28} {c.get('antes_violacion', 0):>3} → {c.get('despues_violacion', 0):>3}")
    print("\nCambios de nivel:")
    for d in rows:
        if d["quality"][0] != d["quality"][2] or d["price"][0] != d["price"][2] or d["type"][0] != d["type"][1]:
            print(f"  {d['symbol']:6} tipo {d['type'][0]}→{d['type'][1]} · calidad {d['quality'][1]} {d['quality'][0]} → "
                  f"{d['quality'][3]} {d['quality'][2]} · precio {d['price'][1]} {d['price'][0]} → {d['price'][3]} "
                  f"{d['price'][2]} · margen {d['op_row'][0]} → {d['op_row'][1]} · comprobación {d['check']}")
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump({"counts": dict(cnt), "checks": dict(checks), "rules": {k: dict(v) for k, v in rules.items()},
                       "companies": rows}, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
