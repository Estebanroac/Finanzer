"""
F8 (auditoría externa del 26-oct-2026): evidencia propia con datos reales. Analiza en vivo, con el backend local y las
claves del Llavero, los tickers de la auditoría (o los que se pidan) y guarda cada análisis comprimido en
docs/fiabilidad/f8_evidencia/<rama>/<T>.json.gz, para leer de ahí las cifras de cada error (E1…E11) antes y después de
corregirlo. Las claves llegan por el entorno de la orden y no se escriben:

    cd backend
    FINNHUB_API_KEY="$(security find-generic-password -s finanzer-finnhub -w)" \\
    SEC_EDGAR_USER_AGENT="$(security find-generic-password -s finanzer-sec-ua -w)" \\
        ../../finanzer_next/.venv313/bin/python tools/f8_evidencia.py --tag antes [AWK XOM CB]

    ../../finanzer_next/.venv313/bin/python tools/f8_evidencia.py --tag antes --show AWK wacc.ke wacc.kd beta

Con --show solo lee lo guardado (sin red): imprime los campos pedidos (rutas con puntos) de cada ticker.
"""
import argparse
import gzip
import json
import logging
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
OUT = os.path.normpath(os.path.join(BACKEND, "..", "docs", "fiabilidad", "f8_evidencia"))
AUDIT = ["MSFT", "NVDA", "LLY", "UNH", "JPM", "CB", "AMZN", "MCD", "GOOGL", "VZ", "CAT", "UNP", "KO", "WMT", "XOM",
         "KMI", "NEE", "AWK", "PLD", "O", "LIN", "FCX", "ASML", "SAP", "MRNA", "BA"]


def _path(tag, sym):
    return os.path.join(OUT, tag, f"{sym}.json.gz")


def load(tag, sym):
    with gzip.open(_path(tag, sym), "rt", encoding="utf-8") as fh:
        return json.load(fh)


def get(obj, dotted):
    for k in dotted.split("."):
        if isinstance(obj, list):
            try:
                obj = obj[int(k)]
            except (ValueError, IndexError):
                return None
        elif isinstance(obj, dict):
            obj = obj.get(k)
        else:
            return None
    return obj


def run(tag, syms):
    sys.path[:0] = [BACKEND, os.path.join(BACKEND, "lib")]
    if not os.environ.get("FINNHUB_API_KEY") or not os.environ.get("SEC_EDGAR_USER_AGENT"):
        sys.exit("faltan FINNHUB_API_KEY o SEC_EDGAR_USER_AGENT en el entorno (ver el uso)")
    logging.disable(logging.WARNING)
    import main
    os.makedirs(os.path.join(OUT, tag), exist_ok=True)
    for s in syms:
        t0 = time.time()
        try:
            a = main._compute_analysis(s)
        except Exception as e:  # noqa: BLE001 — se anota y se sigue con el resto
            a = {"__error__": f"{type(e).__name__}: {getattr(e, 'detail', e)}"}
        a["__f8__"] = {"tag": tag, "at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                       "seconds": round(time.time() - t0, 1)}
        with gzip.open(_path(tag, s), "wt", encoding="utf-8") as fh:
            json.dump(a, fh, ensure_ascii=False, sort_keys=True, default=str)
        print(f"[{s}] {a.get('__error__') or 'ok'} ({a['__f8__']['seconds']} s)", flush=True)


def main_cli(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("symbols", nargs="*")
    ap.add_argument("--tag", required=True, help="carpeta de la corrida (antes, e1, …)")
    ap.add_argument("--show", nargs="+", metavar="CAMPO", help="sin red: imprime estos campos de lo guardado")
    args = ap.parse_args(argv)
    syms = [s.upper() for s in args.symbols] or AUDIT
    if args.show:
        for s in syms:
            try:
                a = load(args.tag, s)
            except FileNotFoundError:
                print(f"{s}: sin corrida «{args.tag}»")
                continue
            print(s, " · ".join(f"{f}={json.dumps(get(a, f), ensure_ascii=False, default=str)}" for f in args.show))
        return 0
    run(args.tag, syms)
    return 0


if __name__ == "__main__":
    sys.exit(main_cli())
