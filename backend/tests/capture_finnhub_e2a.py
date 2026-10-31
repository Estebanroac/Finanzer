"""
Rediseño E2a (T8): graba en los fixtures de un juego (panel por defecto) los titulares de Finnhub (/company-news) y el
calendario de resultados hacia delante (/calendar/earnings), para que el replay enseñe las noticias en tarjetas y los
próximos resultados de /v2.

  · /company-news: de `news_days` días antes de la captura del ticker hasta el día siguiente a la captura (V4b: Finnhub
    devuelve solo los más recientes de la ventana; hasta hoy, en las empresas con muchos titulares todos eran
    posteriores a la captura y el corte los quitaba todos); se guardan solo los publicados hasta la hora de la captura
    (lo que se sabía ese día; el replay corta igual).
  · /calendar/earnings: de la fecha de captura del ticker a hoy + `next_earnings_days`, sin las cifras reales de lo
    publicado después de la captura (calendar_until_capture).

Se añaden a <juego>/<T>/finnhub.json como las demás respuestas grabadas ({path, params, response}), sustituyendo las
anteriores de esas dos rutas; los parámetros nunca llevan la clave (finnhub_fallback la añade solo a la URL). La clave
se lee del entorno, del Llavero en el mismo comando, y nunca se imprime:

    cd finanzer_next/backend
    FINNHUB_API_KEY="$(security find-generic-password -s finanzer-finnhub -w)" \\
        ../.venv313/bin/python tests/capture_finnhub_e2a.py AAPL JPM O NEE XOM PLTR RIVN BCS
"""
import argparse
import datetime as _dt
import json
import os
import sys
import time

import fixture_backend as fb
import finnhub_fallback
from settings import cfg

PATHS = ("/company-news", "/calendar/earnings")


def until_capture(news, meta):
    """Solo los titulares publicados hasta la captura del ticker: el replay no sirve otros (lo que se sabía ese día)."""
    cut = int(_dt.datetime.fromisoformat(meta["captured_at_utc"]).timestamp())
    return [x for x in news if int(x.get("datetime") or 0) <= cut]


ACTUALS = ("epsActual", "revenueActual")


def calendar_until_capture(resp, meta):
    """V4b: el calendario tal como se conocía en la captura del ticker. Una publicación posterior a la captura (otro
    día, o el mismo día después del cierre, "amc", o sin hora) queda con su fecha y la estimación, pero sin las cifras
    reales: si no, el replay vería resultados que el análisis de ese día no tenía (sec_edgar.pending_from_calendar)."""
    if not isinstance(resp, dict) or not isinstance(resp.get("earningsCalendar"), list):
        return resp
    day = _dt.datetime.fromisoformat(meta["captured_at_utc"]).date().isoformat()

    def known(e):
        d = str(e.get("date") or "")
        return d < day or (d == day and e.get("hour") == "bmo")
    return {**resp, "earningsCalendar": [e if known(e) else {**e, **{k: None for k in ACTUALS if k in e}}
                                         for e in resp["earningsCalendar"]]}


def capture(sym, base, today):
    d = os.path.join(base, sym)
    meta_path, fh_path = os.path.join(d, "metadata.json"), os.path.join(d, "finnhub.json")
    meta = json.load(open(meta_path, encoding="utf-8"))
    calls = json.load(open(fh_path, encoding="utf-8"))
    d0 = _dt.date.fromisoformat(meta["captured_at_utc"][:10])
    C = cfg("market.context")
    wanted = [("/company-news", {"symbol": finnhub_fallback.provider_symbol(sym), "from": (d0 - _dt.timedelta(days=C["news_days"])).isoformat(),
                                 "to": (d0 + _dt.timedelta(days=1)).isoformat()}),
              ("/calendar/earnings", {"symbol": sym, "from": d0.isoformat(),
                                      "to": (today + _dt.timedelta(days=C["next_earnings_days"])).isoformat()})]
    calls = [c for c in calls if c["path"] not in PATHS]
    report = {}
    for path, params in wanted:
        resp = finnhub_fallback._get(path, params)
        if resp is None:
            report[path] = "sin respuesta"
            continue
        if path == "/company-news" and isinstance(resp, list):
            resp = until_capture(resp, meta)
        if path == "/calendar/earnings":
            resp = calendar_until_capture(resp, meta)
        calls.append({"path": path, "params": params, "response": resp})
        report[path] = (len(resp) if isinstance(resp, list) else len((resp or {}).get("earningsCalendar") or []))
        time.sleep(1.1)          # Finnhub: ≤ 55 peticiones por minuto
    with open(fh_path, "w", encoding="utf-8") as fh:
        json.dump(calls, fh, sort_keys=True, ensure_ascii=False)     # el formato compacto de estos fixtures
    meta.setdefault("finnhub", {})["calls"] = len(calls)
    meta["finnhub"]["e2a_capture_utc"] = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    meta["finnhub"]["e2a_paths"] = list(PATHS)
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=1, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("symbols", nargs="+")
    ap.add_argument("--env", default=fb.PANEL_ENV)
    args = ap.parse_args(argv)
    if not finnhub_fallback.is_enabled():
        ap.error("falta FINNHUB_API_KEY en el entorno (ver el uso)")
    base = fb.fixtures_dir(args.env)
    today = _dt.date.today()
    for s in [x.upper() for x in args.symbols]:
        print(f"[{s}] {capture(s, base, today)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
