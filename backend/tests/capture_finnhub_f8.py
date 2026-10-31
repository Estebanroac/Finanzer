"""
F8 · E3: graba en los fixtures de un juego (panel por defecto) los estados presentados por el emisor de Finnhub
(/stock/financials-reported, anual y trimestral), de los que lib/reit_ffo.py saca los ajustes del FFO según Nareit.

  · Solo los filings presentados hasta el día de la captura del ticker (lo que se sabía ese día; el replay corta igual).
  · De cada filing, solo el estado de flujos y en él solo las partidas que podrían ser ajustes del FFO, el resultado de
    participadas y el flujo de operaciones (la respuesta entera pesa ~1 MB por llamada).

Se añaden a <juego>/<T>/finnhub.json como las demás respuestas grabadas ({path, params, response}), sustituyendo las
anteriores de esa ruta; los parámetros nunca llevan la clave. La clave se lee del entorno, del Llavero en el mismo
comando, y nunca se imprime:

    cd finanzer_next/backend
    FINNHUB_API_KEY="$(security find-generic-password -s finanzer-finnhub -w)" \\
        ../.venv313/bin/python tests/capture_finnhub_f8.py O PLD AMT
"""
import argparse
import datetime as _dt
import json
import os
import re
import sys
import time

import fixture_backend as fb
import finnhub_fallback

PATH = "/stock/financials-reported"
# Más amplio que las reglas de config/data.toml [reit_ffo], para poder afinarlas sin volver a grabar.
BROAD = re.compile(r"gain|loss|impair|straightline|improvement|leasing|equitymethod|equityinearnings|"
                   r"NetCashProvidedByUsedInOperatingActivities", re.I)


def until_capture(resp, meta):
    """Los filings presentados hasta el día de la captura, con solo el estado de flujos y sus partidas útiles."""
    day = str(meta["captured_at_local"])[:10]
    rows = [r for r in (resp or {}).get("data") or [] if str(r.get("filedDate") or "")[:10] <= day]
    return {**resp, "data": [{**{k: v for k, v in r.items() if k != "report"},
                              "report": {"cf": [it for it in (r.get("report") or {}).get("cf") or []
                                                if BROAD.search(str(it.get("concept") or ""))]}} for r in rows]}


def capture(sym, base):
    d = os.path.join(base, sym)
    meta_path, fh_path = os.path.join(d, "metadata.json"), os.path.join(d, "finnhub.json")
    meta = json.load(open(meta_path, encoding="utf-8"))
    calls = [c for c in json.load(open(fh_path, encoding="utf-8")) if c["path"] != PATH]
    report = {}
    for freq in ("annual", "quarterly"):
        params = {"symbol": finnhub_fallback.provider_symbol(sym), "freq": freq}
        resp = finnhub_fallback._get(PATH, params)
        if not isinstance(resp, dict):
            report[freq] = "sin respuesta"
            continue
        resp = until_capture(resp, meta)
        calls.append({"path": PATH, "params": params, "response": resp})
        report[freq] = len(resp["data"])
        time.sleep(1.1)          # Finnhub: ≤ 55 peticiones por minuto
    with open(fh_path, "w", encoding="utf-8") as fh:
        json.dump(calls, fh, sort_keys=True, ensure_ascii=False)
    meta.setdefault("finnhub", {})["calls"] = len(calls)
    meta["finnhub"]["f8_capture_utc"] = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    meta["finnhub"]["f8_paths"] = [PATH]
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=1, sort_keys=True, ensure_ascii=False)
    return report


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("tickers", nargs="+")
    ap.add_argument("--env", default=fb.PANEL_ENV)
    args = ap.parse_args(argv)
    if not finnhub_fallback.is_enabled():
        sys.exit("falta FINNHUB_API_KEY en el entorno")
    base = fb.fixtures_dir(args.env)
    for sym in args.tickers:
        print(sym, capture(sym.upper(), base))


if __name__ == "__main__":
    main()
