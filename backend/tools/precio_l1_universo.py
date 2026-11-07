"""
F16: escribe config/precio_l1.toml (la referencia del universo para la etiqueta de precio L1, lib/precio_l1.py) con
el P/E que calcula el propio motor en cada empresa del universo (config/universe.tsv).

Dos pasos (con red el primero; el segundo, sin red):

    cd backend
    FINNHUB_API_KEY="$(security find-generic-password -s finanzer-finnhub -w)" \\
    SEC_EDGAR_USER_AGENT="$(security find-generic-password -s finanzer-sec-ua -w)" \\
        ../../../finanzer_next/.venv313/bin/python tools/universe_scan.py --no-pdf --cache <carpeta> --out <carpeta>
    ../../../finanzer_next/.venv313/bin/python tools/precio_l1_universo.py --cache <carpeta> [--out config/precio_l1.toml]

Lee <carpeta>/<SÍMBOLO>.analysis.json.gz (price_attractiveness.pe_ttm) y el sector GICS del universo. Termina con
error y NO escribe si menos del 85 % del universo tiene análisis o si quedan menos de 30 empresas con P/E.
Refresco: mensual, o tras cambiar el universo (las medianas y los cortes se mueven despacio; el P/E de cada empresa en
vivo usa su precio del día).
"""
import argparse
import datetime as dt
import gzip
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))

import precio_l1  # noqa: E402
import universe  # noqa: E402

MIN_COVERAGE = 0.85


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache", required=True, help="carpeta de tools/universe_scan.py con los análisis")
    ap.add_argument("--out", default=precio_l1.CONFIG)
    ap.add_argument("--as-of", default=dt.date.today().isoformat())
    a = ap.parse_args()
    rows, seen = [], 0
    for r in universe.load():
        p = os.path.join(a.cache, f"{r['symbol']}.analysis.json.gz")
        pe = None
        if os.path.isfile(p):
            an = json.load(gzip.open(p))
            an = an.get("analysis", an) if isinstance(an, dict) else {}     # universe_scan guarda {analysis, pdf_text}
            if "__http_error__" not in an:
                seen += 1
                pe = (an.get("price_attractiveness") or {}).get("pe_ttm")
        rows.append({"symbol": r["symbol"], "gics_sector": r.get("gics_sector"), "pe": pe})
    cov = seen / max(1, len(rows))
    if cov < MIN_COVERAGE:
        raise SystemExit(f"solo {seen} de {len(rows)} empresas con análisis ({cov:.0%} < {MIN_COVERAGE:.0%}): no se escribe")
    ref = precio_l1.build_reference(rows, a.as_of, f"P/E de lib/precio_l1 en el universo ({seen} análisis de "
                                                    f"tools/universe_scan.py)")
    precio_l1.write_reference(ref, a.out)
    print(f"{a.out}: {ref['n']} empresas con P/E de {len(rows)}; cortes {ref['cuts'][0]:.3f} y {ref['cuts'][1]:.3f}")
    for s, m in ref["sector_median"].items():
        print(f"  {s}: mediana {m:.1f} ({ref['n_sector'][s]})")


if __name__ == "__main__":
    main()
