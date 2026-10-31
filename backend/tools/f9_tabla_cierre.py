"""
F9 · cierre: NU y las empresas de la auditoría antes de F9 (`f9_antes`, rediseno/v4-f8 en 21d76d63) y después (la
fusión de f9-motor y f9-coherencia), en vivo y guardadas por f8_evidencia. Sin red.

    python tools/f9_tabla_cierre.py <tag_antes> <tag_despues> SYM [SYM …]

Columnas: Ke, β del Ke, prima de riesgo país, calidad, precio (con la confianza) y veredicto. En negrita, lo que cambia
de nivel.
"""
import gzip
import json
import os
import sys

EV = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "docs", "fiabilidad",
                  "f8_evidencia")


def load(tag, sym):
    p = os.path.join(EV, tag, f"{sym}.json.gz")
    if not os.path.exists(p):
        return None
    d = json.load(gzip.open(p))
    return d.get("analysis", d)


def _row(a):
    if not a:
        return None
    q, p = a.get("quality") or {}, a.get("price_attractiveness") or {}
    ce, w = a.get("cost_of_equity") or {}, a.get("wacc") or {}
    beta = w.get("beta") if w.get("beta") is not None else (a.get("key_metrics") or {}).get("beta_ke") or (
        (a.get("beta") or {}).get("adjusted"))
    return {"ke": ce.get("value"), "beta": beta, "crp": (a.get("country_risk") or {}).get("crp"),
            "q": q.get("score"), "ql": q.get("level"), "p": p.get("score"), "pl": p.get("level"),
            "conf": (a.get("confidence") or {}).get("level"), "verdict": (a.get("verdict") or {}).get("text")}


def _pct(x):
    return "—" if x is None else f"{x * 100:.2f} %"


def _num(x):
    return "—" if x is None else f"{x:.2f}"


def main(tag_a, tag_b, *syms):
    print("| Empresa | Ke | β del Ke | Prima país | Calidad | Precio | Confianza |")
    print("|---|---|---|---|---|---|---|")
    for s in syms:
        a, b = _row(load(tag_a, s)), _row(load(tag_b, s))
        if not (a and b):
            print(f"| {s} | sin corrida | | | | | |")
            continue
        f = lambda u, v, bold=False: u if u == v else (f"{u} → **{v}**" if bold else f"{u} → {v}")
        print(f"| {s} | {f(_pct(a['ke']), _pct(b['ke']))} | {f(_num(a['beta']), _num(b['beta']))} | "
              f"{f(_pct(a['crp'] or 0), _pct(b['crp'] or 0))} | "
              f"{f(str(a['q']), str(b['q']))} {f(a['ql'], b['ql'], True)} | "
              f"{f(str(a['p']), str(b['p']))} {f(a['pl'], b['pl'], True)} | {f(a['conf'], b['conf'])} |")


if __name__ == "__main__":
    main(*sys.argv[1:])
