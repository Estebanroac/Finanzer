"""
F8: corre en replay (panel + fixtures F8, sin red) los tickers pedidos y guarda cada análisis comprimido en
<salida>/<T>.json.gz, para comparar un error antes y después sin datos en vivo:

    cd backend
    ../../finanzer_next/.venv313/bin/python tools/f8_replay_dump.py <salida> VZ GOOGL AMZN

Los análisis se leen igual que la evidencia en vivo (tools/f8_evidencia.py --show con --dir).
"""
import gzip
import json
import logging
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
sys.path[:0] = [BACKEND, os.path.join(BACKEND, "lib"), os.path.join(BACKEND, "tests")]


def main(argv):
    out, syms = argv[0], argv[1:]
    logging.disable(logging.WARNING)
    import fixture_backend as fb
    panel = fb.fixtures_dir("panel")
    f8 = os.path.join(os.path.dirname(panel), "f8")
    os.makedirs(out, exist_ok=True)
    for s in syms:
        base = panel if os.path.isdir(os.path.join(panel, s)) else f8
        with fb.replay(base, extra_dirs=(f8,)) as store:
            a = fb.run_analysis(s, store)
        with gzip.open(os.path.join(out, f"{s}.json.gz"), "wt", encoding="utf-8") as fh:
            json.dump(a, fh, ensure_ascii=False, default=str)
        print(s, (a.get("verdict") or {}).get("text"), (a.get("verdict") or {}).get("confidence"))


if __name__ == "__main__":
    main(sys.argv[1:])
