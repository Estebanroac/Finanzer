"""
F9 · R1c: la compresión del forward P/E en tres estados, antes de R1c, con la forma binaria y con la continua (BPA
forward creíble), y lo que cambia en el precio. Sin red.

    python tools/f9_tabla_r1c.py vivo <tag_antes> <tag_binario> <tag_continuo> SYM [SYM …]
    python tools/f9_tabla_r1c.py golden <ref_antes> <ref_binario>        # el continuo es el disco

Solo imprime las filas en las que algo cambia entre los tres estados.
"""
import glob
import gzip
import json
import os
import subprocess
import sys

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(BACKEND)
EV = os.path.join(REPO, "docs", "fiabilidad", "f8_evidencia")


def _tag(tag, sym):
    p = os.path.join(EV, tag, f"{sym}.json.gz")
    if not os.path.exists(p):
        return None
    d = json.load(gzip.open(p))
    return d.get("analysis", d)


def _ref(ref, rel):
    if ref is None:
        with open(os.path.join(REPO, rel)) as fh:
            return json.load(fh)
    r = subprocess.run(["git", "show", f"{ref}:{rel}"], cwd=REPO, capture_output=True, text=True)
    return json.loads(r.stdout) if r.returncode == 0 else None


def _row(a):
    if not a:
        return None
    v = ((a.get("score") or {}).get("breakdown") or {}).get("Valoración") or {}
    f = next((x for x in v.get("adjustments") or [] if x.get("metric") == "Forward P/E"), None)
    p = a.get("price_attractiveness") or {}
    return {"adj": f and f["adjustment"], "impl": f and f.get("implied_eps_growth"), "hist": f and f.get("eps_growth_3y"),
            "fwd": f and f["value"], "cred": f and f.get("credible_forward_pe"), "price": p.get("score"),
            "level": p.get("level")}


def _cause(r):
    if r["adj"] is None:
        return "sin forward"
    if r["hist"] is None:
        return f"implica {r['impl']:+.0%}; sin CAGR a 3 años"
    if r["cred"]:
        return f"implica {r['impl']:+.0%} frente al {r['hist']:+.0%} anual: {r['fwd']} → {r['cred']:.1f}x creíble"
    return f"implica {r['impl']:+.0%}, respaldado ({r['hist']:+.0%} anual)"


def _print(rows):
    print("| Caso | Compresión (antes · binario · continuo) | Causa (continuo) | Precio (antes · binario · continuo) |")
    print("|---|---|---|---|")
    for name, (a, b, c) in rows:
        if not (a and b and c):
            continue
        if (a["adj"], a["price"], a["level"]) == (b["adj"], b["price"], b["level"]) == (c["adj"], c["price"], c["level"]):
            continue
        lv = lambda r: f"{r['price']} {r['level']}"
        print(f"| {name} | {a['adj']} · {b['adj']} · {c['adj']} | {_cause(c)} | {lv(a)} · {lv(b)} · {lv(c)} |")


def main(mode, *args):
    if mode == "vivo":
        t0, t1, t2, *syms = args
        _print([(s, tuple(_row(_tag(t, s)) for t in (t0, t1, t2))) for s in syms])
    else:
        r0, r1 = args
        rels = sorted(os.path.relpath(p, REPO) for p in glob.glob(os.path.join(BACKEND, "tests", "golden", "*", "*.json"))
                      if "/forzados/" not in p)
        _print([(f"{os.path.basename(os.path.dirname(r))}/{os.path.basename(r)[:-5]}",
                 tuple(_row(_ref(ref, r)) for ref in (r0, r1, None))) for r in rels])


if __name__ == "__main__":
    main(*sys.argv[1:])
