"""
Fixtures de la serie diaria del análisis (fase 2b, lib/price_history.py): juego SEPARADO del panel.

    tests/fixtures/history/metadata.json      fecha de la captura, fuente, versiones y resumen por símbolo
    tests/fixtures/history/series/<SYM>.json  precios sin ajustar (apertura, máximo, mínimo, cierre), cierre ajustado,
                                              volumen, dividendos y splits de 2 años

Replay sin red (`replay_fetcher`): devuelve la serie con la forma de yfinance `history` CORTADA en una fecha (la de
captura del ticker analizado), así el análisis ve lo que habría descargado ese día.
"""
import json
import os
import sys

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(TESTS_DIR)
for _p in (BACKEND_DIR, os.path.join(BACKEND_DIR, "lib"), TESTS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

HISTORY_DIR = os.path.join(TESTS_DIR, "fixtures", "history")
TZ = "America/New_York"
COLS = (("Open", "open"), ("High", "high"), ("Low", "low"), ("Close", "close"), ("Adj Close", "adj_close"),
        ("Volume", "volume"), ("Dividends", "dividend"), ("Stock Splits", "split"))


def series_file(symbol, base=HISTORY_DIR):
    return os.path.join(base, "series", symbol.upper().replace("^", "IDX_") + ".json")


def available(base=HISTORY_DIR):
    return os.path.isfile(os.path.join(base, "metadata.json"))


def frame_to_obj(symbol, frame):
    """Serie normalizada de price_history → objeto JSON sin redondear (los eventos, como mapa fecha → valor)."""
    obj = {"symbol": symbol, "tz": TZ, "dates": [d.strftime("%Y-%m-%d") for d in frame.index]}
    for _, c in COLS:
        if c in ("dividend", "split"):
            obj[c] = {d.strftime("%Y-%m-%d"): float(v) for d, v in frame[c].items() if v}
        else:
            obj[c] = [None if v != v else float(v) for v in frame[c].tolist()]
    return obj


def save(symbol, frame, base=HISTORY_DIR):
    obj = frame_to_obj(symbol, frame)
    os.makedirs(os.path.dirname(series_file(symbol, base)), exist_ok=True)
    with open(series_file(symbol, base), "w", encoding="utf-8") as fh:
        json.dump(obj, fh, separators=(",", ":"))
        fh.write("\n")


def load_frame(symbol, until=None, base=HISTORY_DIR):
    """La serie con la forma de yfinance `history` (columnas de COLS, índice con la zona de la bolsa), cortada en
    `until` (fecha ISO, incluida)."""
    path = series_file(symbol, base)
    if not os.path.isfile(path):
        raise KeyError(f"símbolo no grabado en los fixtures del historial: {symbol}")
    with open(path, encoding="utf-8") as fh:
        obj = json.load(fh)
    return obj_to_history(obj, until)


def obj_to_history(obj, until=None):
    import pandas as pd
    dates = obj["dates"]
    keep = [i for i, d in enumerate(dates) if until is None or d <= until]
    data = {}
    for yname, c in COLS:
        if c in ("dividend", "split"):
            ev = obj.get(c) or {}
            data[yname] = [ev.get(dates[i], 0.0) for i in keep]
        else:
            data[yname] = [float("nan") if obj[c][i] is None else obj[c][i] for i in keep]
    idx = pd.DatetimeIndex(pd.to_datetime([dates[i] for i in keep])).tz_localize(obj.get("tz", TZ))
    idx.name = "Date"
    return pd.DataFrame(data, index=idx)
