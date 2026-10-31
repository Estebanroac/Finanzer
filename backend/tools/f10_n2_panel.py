"""
F10 · N2: la referencia de la industria sin la propia empresa en el panel (replay de fixtures, sin red). Imprime, por
empresa, el método, el peso y las columnas que puntúan antes y después, y el bloque de múltiplos y el precio.

    cd backend && ../../finanzer_next/.venv313/bin/python tools/f10_n2_panel.py [--env panel] [NVDA AAPL …]
"""
import argparse
import json
import logging
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tests"))
import fixture_backend as fb  # noqa: E402


def block(a):
    v = ((a.get("score") or {}).get("breakdown") or {}).get("Valoración") or {}
    b = next((x for x in v.get("adjustments", []) if x.get("metric") == "Bloque de múltiplos"), {})
    return b.get("adjustment")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tickers", nargs="*")
    ap.add_argument("--env", default=fb.PANEL_ENV)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    logging.disable(logging.CRITICAL)
    syms = [t.upper() for t in a.tickers] or fb.env_tickers(a.env)
    out = fb.compute_outputs(syms, fb.fixtures_dir(a.env))
    rows = {}
    for s in syms:
        an = out[s][0]
        b = an.get("benchmark") or {}
        ind = b.get("industry") or {}
        se = ind.get("self_exclusion") or {}
        pa = an.get("price_attractiveness") or {}
        rows[s] = {"method": se.get("method"), "weight": se.get("weight"), "industry": ind.get("damodaran"),
                   "region": ind.get("region"), "declaration": se.get("declaration"),
                   "pe": (ind.get("published") or {}).get("pe"), "pe_new": (b.get("values") or {}).get("pe"),
                   "ev": (ind.get("published") or {}).get("ev_ebitda"),
                   "ev_new": (b.get("values") or {}).get("ev_ebitda"), "block": block(an),
                   "price": pa.get("score"), "level": pa.get("level"), "cut": se.get("cut"),
                   "figures": se.get("figures")}
    if a.json:
        print(json.dumps(rows, ensure_ascii=False, indent=1, default=str))
        return
    for s, r in rows.items():
        w = f"{r['weight']:.1%}" if r["weight"] is not None else "—"
        f = lambda x: f"{x:.2f}" if isinstance(x, (int, float)) else "—"  # noqa: E731
        print(f"{s:6} {str(r['method']):13} peso {w:>6}  P/E {f(r['pe'])}→{f(r['pe_new'])}  "
              f"EV/EBITDA {f(r['ev'])}→{f(r['ev_new'])}  bloque {r['block']}  precio {r['price']} {r['level']}")
        print(f"       {r['declaration']}")


if __name__ == "__main__":
    main()
