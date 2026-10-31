"""
F10 · B3: efecto de leer las alertas con la referencia de su fila, sobre los golden (replay de fixtures, sin red). Por
empresa: si cambia alguna puntuación (no debería) y qué alertas entran y salen.

    cd backend && ../../finanzer_next/.venv313/bin/python tools/f10_b3_efecto.py [--env panel|local]
"""
import argparse
import json
import logging
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tests"))
sys.path.insert(0, HERE)
import fixture_backend as fb  # noqa: E402
from f10_b3_tono import contradictions  # noqa: E402


def _al(a):
    al = a.get("alerts") or {}
    return {(k, x.get("reason")) for k in ("strengths", "warnings", "red_flags") for x in al.get(k) or []}


def _score(a):
    return ((a.get("price_attractiveness") or {}).get("score"), (a.get("quality") or {}).get("score"),
            (a.get("confidence") or {}).get("level"), (a.get("score") or {}).get("total_score"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", default=fb.PANEL_ENV)
    a = ap.parse_args()
    logging.disable(logging.CRITICAL)
    syms = fb.env_tickers(a.env)
    out = fb.compute_outputs(syms, fb.fixtures_dir(a.env))
    moved = 0
    for s in syms:
        with open(os.path.join(fb.golden_dir(a.env), f"{s}.json"), encoding="utf-8") as fh:
            g = json.load(fh)
        n = out[s][0]
        if _score(g) != _score(n):
            moved += 1
            print(f"{s}: PUNTUACIÓN {_score(g)} → {_score(n)}")
        gone, new = sorted(_al(g) - _al(n)), sorted(_al(n) - _al(g))
        for k, r in gone:
            print(f"{s:6} − {k:10} {r}")
        for k, r in new:
            print(f"{s:6} + {k:10} {r}")
        for c in contradictions(n):
            print(f"{s:6} ! contradicción: {c}")
    print(f"{moved} empresas con la puntuación movida")


if __name__ == "__main__":
    main()
