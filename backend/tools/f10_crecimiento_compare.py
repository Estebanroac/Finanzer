"""
F10 · crecimiento desde una base anómala: antes y después sobre los análisis guardados de dos escaneos
(tools/universe_scan.py --cache), la base (8df00bdb) y la rama, corridos uno detrás del otro sobre las mismas empresas
para que el mercado se mueva lo menos posible entre los dos. Sin red: lee los <SÍMBOLO>.analysis.json.gz.

    cd backend
    ../../finanzer_next/.venv313/bin/python tools/f10_crecimiento_compare.py ANTES_DIR DESPUES_DIR [--sets sets.json]

Por empresa: tipo, nivel y puntos de calidad y de precio, las filas de Crecimiento (y la del valor en libros) y la
regla «crecimiento_robusto». `--sets` (json con listas de símbolos por grupo) separa las afectadas del control.
"""
import argparse
import gzip
import json
import os
from collections import Counter

GROWTH_CATS = ("Crecimiento", "Calidad de Ganancias")


def _load(d, sym):
    p = os.path.join(d, f"{sym}.analysis.json.gz")
    if not os.path.isfile(p):
        return None
    with gzip.open(p, "rt", encoding="utf-8") as fh:
        return json.load(fh).get("analysis")


def _violations(d, sym):
    p = os.path.join(d, f"{sym}.json")
    if not os.path.isfile(p):
        return None
    with open(p, encoding="utf-8") as fh:
        s = json.load(fh)
    return sorted(k for k, r in (s.get("results") or {}).items() if (r or {}).get("state") == "violacion")


def summary(a):
    cov = (a.get("display") or {}).get("cover") or {}
    q, p = cov.get("quality") or {}, cov.get("price") or {}
    rows = {}
    for cat in GROWTH_CATS:
        for x in ((a.get("score") or {}).get("breakdown") or {}).get(cat, {}).get("adjustments", []):
            m = x.get("metric") or ""
            if cat == "Crecimiento" or "valor en libros" in m:
                rows[m] = (x.get("value"), x.get("adjustment"))
    gb = a.get("growth_basis") or {}
    return {"type": (a.get("classification") or {}).get("archetype"),
            "q": q.get("score"), "ql": q.get("label") or q.get("level"),
            "p": p.get("score"), "pl": p.get("label") or p.get("level"),
            "rows": rows,
            "eps": (gb.get("eps_cagr") or {}).get("method"), "rev": (gb.get("revenue_cagr") or {}).get("method"),
            "fcf": (gb.get("fcf_cagr") or {}).get("method")}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("before")
    ap.add_argument("after")
    ap.add_argument("--sets")
    ap.add_argument("--json", help="escribe aquí el detalle por empresa")
    args = ap.parse_args(argv)
    sets = json.load(open(args.sets)) if args.sets else {}
    group = {}
    for g in ("bpa", "rev", "fcf", "growth_types", "control"):
        for s in sets.get(g, []):
            group.setdefault(s, []).append(g)
    syms = sorted({f.split(".")[0] for f in os.listdir(args.after) if f.endswith(".analysis.json.gz")}
                  & {f.split(".")[0] for f in os.listdir(args.before) if f.endswith(".analysis.json.gz")})
    out, cnt = [], Counter()
    for s in syms:
        a, b = _load(args.before, s), _load(args.after, s)
        if not a or not b or "score" not in a or "score" not in b:
            continue
        x, y = summary(a), summary(b)
        rows = {m: (x["rows"].get(m), y["rows"].get(m)) for m in sorted(set(x["rows"]) | set(y["rows"]))
                if x["rows"].get(m) != y["rows"].get(m)}
        va, vb = _violations(args.before, s), _violations(args.after, s)
        ctrl_only = group.get(s) == ["control"]
        d = {"symbol": s, "groups": group.get(s, []), "before": x, "after": y, "rows": rows,
             "robusto_before": "crecimiento_robusto" in (va or []), "robusto_after": "crecimiento_robusto" in (vb or []),
             "type_changed": x["type"] != y["type"], "quality_level_changed": x["ql"] != y["ql"],
             "price_level_changed": x["pl"] != y["pl"], "quality_points": (y["q"] or 0) - (x["q"] or 0),
             "growth_rows_changed": bool(rows)}
        out.append(d)
        cnt["empresas"] += 1
        cnt["control"] += ctrl_only
        for k in ("type_changed", "quality_level_changed", "price_level_changed", "growth_rows_changed",
                  "robusto_before", "robusto_after"):
            cnt[k] += bool(d[k])
            if ctrl_only:
                cnt[k + "_control"] += bool(d[k])
        cnt["calidad_cambia_puntos"] += x["q"] != y["q"]
        cnt["precio_cambia_puntos"] += x["p"] != y["p"]
        # Un nivel que cambia sin que cambie ninguna fila de crecimiento es del mercado (o de otro dato), no de la regla.
        cnt["niveles_sin_filas"] += bool((d["quality_level_changed"] or d["price_level_changed"]) and not rows)
    print(json.dumps(dict(cnt), ensure_ascii=False, indent=1))
    for d in out:
        if d["type_changed"] or d["quality_level_changed"] or d["price_level_changed"]:
            x, y = d["before"], d["after"]
            print(f"{d['symbol']:6} {','.join(d['groups']):18} tipo {x['type']}→{y['type']} · calidad {x['q']} {x['ql']}"
                  f" → {y['q']} {y['ql']} · precio {x['p']} {x['pl']} → {y['p']} {y['pl']}"
                  + ("" if d["growth_rows_changed"] else " · (sin cambio en las filas de crecimiento)"))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump({"counts": dict(cnt), "companies": out}, fh, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
