"""
Complementa los fixtures LOCALES con los estados trimestrales de yfinance
(quarterly_income_stmt, quarterly_balance_sheet, quarterly_cashflow), que el
pipeline lee desde la etapa 7 para construir el TTM.

Se añaden SOLO esos tres atributos a los fixtures existentes, en lugar de
recapturarlo todo: una recaptura completa cambiaría también precios, perfil y
estados anuales, y el diff de la etapa no distinguiría el efecto del TTM del
efecto del paso del tiempo. Se marca en metadata.supplements (fecha de captura
de los trimestrales). Los fixtures de PROD no se complementan: en replay caen al
anual con el flag (la verificación del TTM en prod queda para la recaptura de
la etapa 11).

    cd finanzer_next/backend
    ../.venv313/bin/python tests/supplement_local_quarterly.py [TICKERS] [--force]
"""
import argparse
import datetime as _dt
import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fixture_backend as fb  # noqa: E402

ATTRS = ("quarterly_income_stmt", "quarterly_balance_sheet", "quarterly_cashflow")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tickers", nargs="*", default=fb.TICKERS)
    ap.add_argument("--force", action="store_true", help="reemplazar trimestrales ya presentes")
    args = ap.parse_args()
    logging.disable(logging.WARNING)
    import yfinance as yf

    for sym in [t.upper() for t in args.tickers]:
        d = os.path.join(fb.fixtures_dir("local"), sym)
        path_yf, path_meta = os.path.join(d, "yfinance.json"), os.path.join(d, "metadata.json")
        with open(path_yf, encoding="utf-8") as fh:
            yfd = json.load(fh)
        with open(path_meta, encoding="utf-8") as fh:
            meta = json.load(fh)
        if all(a in yfd for a in ATTRS) and not args.force:
            print(f"[{sym}] ya tiene trimestrales; usa --force")
            continue
        t = yf.Ticker(sym)
        for a in ATTRS:
            yfd[a] = fb.df_to_obj(getattr(t, a))
        now = _dt.datetime.now().astimezone()
        meta.setdefault("supplements", {})["quarterly_statements"] = {
            "captured_at_utc": now.astimezone(_dt.timezone.utc).isoformat(timespec="seconds"),
            "attributes": list(ATTRS),
            "note": "trimestrales añadidos en la etapa 7 sin recapturar el resto del fixture",
            "versions": fb.environment_info(),
        }
        for path, payload in ((path_yf, yfd), (path_meta, meta)):
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=1, sort_keys=True, ensure_ascii=False)
                fh.write("\n")
        cols = yfd["quarterly_income_stmt"].get("columns", [])
        print(f"[{sym}] trimestrales: {len(cols)} columnas ({cols[0][:10] if cols else '-'} …)")


if __name__ == "__main__":
    main()
