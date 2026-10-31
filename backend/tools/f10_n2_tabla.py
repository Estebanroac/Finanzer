"""
F10 · N2: tabla de la referencia de la industria con y sin la propia empresa, de la evidencia en vivo
(docs/fiabilidad/f8_evidencia/<tag>/): método, peso, P/E y EV/EBITDA de referencia, bloque de múltiplos, precio y nivel.

    cd backend && ../../finanzer_next/.venv313/bin/python tools/f10_n2_tabla.py f10_n4 f10_n2 [--md]
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from f8_evidencia import AUDIT, load  # noqa: E402

SYMS = ["NVDA"] + [s for s in AUDIT if s != "NVDA"] + ["NU"]


def _a(tag, s):
    d = load(tag, s)
    return d.get("analysis", d)


def _block(a):
    v = ((a.get("score") or {}).get("breakdown") or {}).get("Valoración") or {}
    return next((x.get("adjustment") for x in v.get("adjustments", []) if x.get("metric") == "Bloque de múltiplos"),
                None)


def _f(x, d=1):
    return f"{x:.{d}f}".replace(".", ",") if isinstance(x, (int, float)) else "—"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("before")
    ap.add_argument("after")
    ap.add_argument("--md", action="store_true")
    a = ap.parse_args()
    head = ["Empresa", "Referencia", "Peso", "P/E ref.", "EV/EBITDA ref.", "Bloque", "Precio", "Nivel"]
    print("| " + " | ".join(head) + " |\n|" + "---|" * len(head))
    for s in SYMS:
        try:
            o, n = _a(a.before, s), _a(a.after, s)
        except FileNotFoundError:
            print(f"| {s} | falta | | | | | | |")
            continue
        ob, nb = (o.get("benchmark") or {}), (n.get("benchmark") or {})
        se = (nb.get("industry") or {}).get("self_exclusion") or {}
        meth = {"sin_empresa": "sin ella", "mediana_pares": f"mediana de {se.get('n_peers')} pares",
                "no_figura": "no figura"}.get(se.get("method"), "—")
        w = f"{se['weight'] * 100:.0f} %" if se.get("weight") is not None else "—"
        ov, nv = ob.get("values") or {}, nb.get("values") or {}
        op, np_ = o.get("price_attractiveness") or {}, n.get("price_attractiveness") or {}
        lvl = (op.get("level") or "—") + ("" if op.get("level") == np_.get("level") else f" → **{np_.get('level')}**")
        print(f"| {s} | {meth} | {w} | {_f(ov.get('pe'))} → {_f(nv.get('pe'))} | "
              f"{_f(ov.get('ev_ebitda'))} → {_f(nv.get('ev_ebitda'))} | {_block(o)} → {_block(n)} | "
              f"{op.get('score')} → {np_.get('score')} | {lvl} |")


if __name__ == "__main__":
    main()
