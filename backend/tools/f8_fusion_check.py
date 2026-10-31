"""
F8 (fusión de f8-auditoria y f8-independientes): ¿cada cambio de veredicto de los golden es la suma de los de las dos
ramas? Compara, campo a campo, la base común, las dos ramas y el resultado de la fusión (los golden del disco):

- un campo que solo cambia en una rama debe quedar como en esa rama;
- un número que cambia en las dos debe quedar en base + (A − base) + (B − base);
- un texto o nivel que cambia en las dos, o cualquier valor distinto del esperado, es una interacción: necesita causa.

    python tools/f8_fusion_check.py <base> <rama_a> <rama_b>
"""
import json
import os
import subprocess
import sys
from glob import glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIELDS = ["quality.score", "quality.level", "price_attractiveness.score", "price_attractiveness.score_raw",
          "price_attractiveness.level", "price_attractiveness.confidence", "verdict.text", "verdict.quality_level",
          "verdict.price_level", "verdict.confidence", "confidence.level"]


def get(d, path):
    for k in path.split("."):
        d = (d or {}).get(k) if isinstance(d, dict) else None
    return d


def at(ref, rel):
    try:
        return json.loads(subprocess.check_output(["git", "-C", ROOT, "show", f"{ref}:backend/{rel}"],
                                                  stderr=subprocess.DEVNULL))
    except subprocess.CalledProcessError:
        return None


def main(base, a, b):
    inter, n = [], 0
    for p in sorted(glob(os.path.join(ROOT, "tests", "golden", "*", "*.json"))):
        rel = os.path.relpath(p, ROOT)
        if "/forzados/" in rel:
            continue
        docs = [at(base, rel), at(a, rel), at(b, rel), json.load(open(p))]
        if any(d is None for d in docs):
            print(f"{rel}: falta en alguna versión")
            continue
        n += 1
        for f in FIELDS:
            v0, va, vb, vm = (get(d, f) for d in docs)
            if va == v0:
                exp = vb
            elif vb == v0 or va == vb:
                exp = va
            elif all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in (v0, va, vb)):
                exp = v0 + (va - v0) + (vb - v0)
            else:
                exp = "?"
            if vm != exp:
                inter.append((rel, f, v0, va, vb, vm, exp))
    print(f"{n} golden × {len(FIELDS)} campos; interacciones: {len(inter)}")
    for rel, f, v0, va, vb, vm, exp in inter:
        print(f"  {rel} · {f}: base {v0!r} · {a[:8]} {va!r} · {b[:8]} {vb!r} · fusión {vm!r} (suma {exp!r})")


if __name__ == "__main__":
    main(*sys.argv[1:4])
