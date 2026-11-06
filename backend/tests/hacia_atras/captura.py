"""
Prueba hacia atrás · captura al corte (5-nov-2025) de las empresas de la muestra, con los mismos 4 pasos que el banco
de F13 (tests/f13_banco110.py --capture), cada uno en su proceso y con el modo «fecha de corte» instalado
(tests/hacia_atras/corte_run.py). Reanudable.

    cd backend
    HACIA_ATRAS_PYLIB=<carpeta con time_machine> \\
    FINNHUB_API_KEY="$(security find-generic-password -s finanzer-finnhub -w)" \\
    SEC_EDGAR_USER_AGENT="$(security find-generic-password -s finanzer-sec-ua -w)" \\
        ../../../finanzer_next/.venv313/bin/python tests/hacia_atras/captura.py --dir <carpeta> [TICKERS | --list f]

Recalcular sin red con una versión del motor (su propio tests/f13_banco110.py --run) y el reloj congelado:

    python <árbol de la versión>/backend/tests/hacia_atras/corte_run.py --solo-reloj \\
        <árbol>/backend/tests/f13_banco110.py --run --dir <carpeta> --out <salida> --list <lista>
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = os.path.dirname(HERE)
sys.path.insert(0, TESTS)
import f13_banco110 as B  # noqa: E402

RUN = os.path.join(HERE, "corte_run.py")
_orig_step = B._step


def _step(cmd, log):
    # [python, tests/capture_x.py, args…] → [python, corte_run.py, tests/capture_x.py, args…]
    return _orig_step([cmd[0], RUN] + cmd[1:], log)


B._step = _step


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tickers", nargs="*")
    ap.add_argument("--dir", required=True)
    ap.add_argument("--list")
    a = ap.parse_args()
    ts = [t.upper() for t in a.tickers] or B.load_tickers(a.list)
    return B.do_capture(ts, os.path.abspath(a.dir))


if __name__ == "__main__":
    sys.exit(main())
