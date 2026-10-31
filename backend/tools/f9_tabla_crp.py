"""
F9 · R1: tabla de la prima de riesgo país por empresa, con su fuente (país, región, sede o no atribuido) y lo que
cambia en el Ke, el precio y la confianza entre dos corridas guardadas por f8_evidencia. Sin red.

    python tools/f9_tabla_crp.py <tag_antes> <tag_despues> SYM [SYM …]
"""
import gzip
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "lib"))
import country_risk as cr  # noqa: E402

EV = os.path.join(ROOT, "..", "docs", "fiabilidad", "f8_evidencia")


def load(tag, sym):
    p = os.path.join(EV, tag, f"{sym}.json.gz")
    if not os.path.exists(p):
        return None
    d = json.load(gzip.open(p))
    return d.get("analysis", d)


def _pct(x):
    return "—" if x is None else f"{x * 100:.2f} %"


def main(tag_a, tag_b, *syms):
    print("| Empresa | Fuente de la prima | Prima país | Detalle | Ke (antes → después) | Precio (antes → después) "
          "| Confianza |")
    print("|---|---|---|---|---|---|---|")
    for s in syms:
        a, b = load(tag_a, s), load(tag_b, s)
        if b is None:
            print(f"| {s} | sin corrida | | | | | |")
            continue
        e = b.get("country_risk")
        src = cr.source_label(e) or "—"
        if e and e.get("unattributed") and e["unattributed"]["share"] > 0:
            src += f" (no atribuido {e['unattributed']['share']:.0%})"
        det = cr.text(e) or "sin prima (EE. UU. o Aaa)"
        ke = lambda x: (x or {}).get("cost_of_equity", {}).get("value") if x else None
        pr = lambda x: (f"{(x.get('price_attractiveness') or {}).get('score')} "
                        f"{(x.get('price_attractiveness') or {}).get('level')}") if x else "—"
        cf = lambda x: (x.get("confidence") or {}).get("level") if x else "—"
        f = lambda u, v: u if u == v else f"{u} → **{v}**"
        print(f"| {s} | {src} | {(e or {}).get('crp', 0) * 100:.2f} pp | {det} | {f(_pct(ke(a)), _pct(ke(b)))} | "
              f"{f(pr(a), pr(b))} | {f(cf(a), cf(b))} |")


if __name__ == "__main__":
    main(*sys.argv[1:])
