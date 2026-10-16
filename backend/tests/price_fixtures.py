"""
Fixtures de series de precios (preparación de las fases 2b y 5): juego SEPARADO del panel.

    tests/fixtures/prices/metadata.json      fecha y hora de la captura, fuente, versiones, sector y ETF de
                                             cada ticker, latencia medida y comprobaciones de la captura
    tests/fixtures/prices/series/<SYM>.json  cierre ajustado, volumen y splits declarados de cada símbolo, una vez
                                             (empresas, ^GSPC y ETF de sector)

Replay sin red: `replay_fetcher()` sirve las series grabadas con la misma forma que yfinance `history`
(columnas Close y Volume, índice con la zona horaria de la bolsa), así que price_series recorre exactamente
el mismo camino que con la red. `no_network()` bloquea los sockets como el replay del panel.
"""
import contextlib
import json
import os
import socket
import sys

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(TESTS_DIR)
for _p in (BACKEND_DIR, os.path.join(BACKEND_DIR, "lib"), TESTS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

PRICES_DIR = os.path.join(TESTS_DIR, "fixtures", "prices")
# Panel ampliado de la fase 2 (BITACORA, fila "Nuevo (proceso)"): los 32 de fixture_backend.PANEL_TICKERS
# (31 + BCS) más los cuatro emisores con otra moneda y otro factor ADR. Aquí se capturan aunque aún no estén
# en el panel.
EXTRA_TICKERS = ["HSBC", "SHEL", "UL", "TM"]
TZ = "America/New_York"


# Grupos del panel añadidos después de capturar este juego (2026-10-15, F5prep): sus series no están aquí. El juego es
# una medida de una sola sesión; se amplía recapturándolo entero, no añadiendo un ticker de otro día.
LATER_GROUPS = ("Sin CIK (fase 2b)",)


def panel_tickers():
    import fixture_backend as fb
    later = {t for g in LATER_GROUPS for t in fb.PANEL_GROUPS.get(g, [])}
    base = [t for t in fb.PANEL_TICKERS if t not in later]
    return base + [t for t in EXTRA_TICKERS if t not in base]


def series_file(symbol, base=PRICES_DIR):
    return os.path.join(base, "series", symbol.replace("^", "IDX_") + ".json")


def available(base=PRICES_DIR):
    return os.path.isfile(os.path.join(base, "metadata.json"))


def metadata(base=PRICES_DIR):
    with open(os.path.join(base, "metadata.json"), encoding="utf-8") as fh:
        return json.load(fh)


def frame_to_obj(symbol, frame):
    """Serie normalizada de price_series (fechas de sesión, `close`, `volume`) → objeto JSON sin redondear."""
    return {"symbol": symbol, "tz": TZ, "dates": [d.strftime("%Y-%m-%d") for d in frame.index],
            "close": [float(v) for v in frame["close"].tolist()],
            "volume": [None if v != v else float(v) for v in frame["volume"].tolist()],
            "splits": {d.strftime("%Y-%m-%d"): float(x) for d, x in frame["split"].items() if x != 0}}


def obj_to_frame(obj):
    """Inverso de frame_to_obj, con la forma de yfinance `history`."""
    import pandas as pd
    idx = pd.DatetimeIndex(pd.to_datetime(obj["dates"])).tz_localize(obj.get("tz", TZ))
    idx.name = "Date"
    splits = obj.get("splits") or {}
    return pd.DataFrame({"Close": [float("nan") if v is None else v for v in obj["close"]],
                         "Volume": [float("nan") if v is None else v for v in obj["volume"]],
                         "Stock Splits": [splits.get(d, 0.0) for d in obj["dates"]]}, index=idx)


def load_obj(symbol, base=PRICES_DIR):
    with open(series_file(symbol, base), encoding="utf-8") as fh:
        return json.load(fh)


def replay_fetcher(base=PRICES_DIR, overrides=None):
    """Descargador sin red: las series grabadas. `overrides` {símbolo: DataFrame | Exception} para casos límite."""
    meta = metadata(base)
    overrides = overrides or {}

    def fetch(symbol, period, interval):
        assert (period, interval) == (meta["period"], meta["interval"]), (
            f"la config pide {period}/{interval} y los fixtures son {meta['period']}/{meta['interval']}")
        if symbol in overrides:
            o = overrides[symbol]
            if isinstance(o, Exception):
                raise o
            return o
        if not os.path.isfile(series_file(symbol, base)):
            raise KeyError(f"símbolo no grabado en los fixtures de precios: {symbol}")
        return obj_to_frame(load_obj(symbol, base))
    return fetch


def _block(*_a, **_kw):
    raise RuntimeError("Red bloqueada en el replay de precios: llamada no grabada")


@contextlib.contextmanager
def no_network():
    saved = (socket.socket.connect, socket.socket.connect_ex, socket.create_connection)
    socket.socket.connect = _block
    socket.socket.connect_ex = _block
    socket.create_connection = _block
    try:
        yield
    finally:
        socket.socket.connect, socket.socket.connect_ex, socket.create_connection = saved


def replay_series(ticker, base=PRICES_DIR, overrides=None):
    """price_series.fetch_price_series de un ticker desde los fixtures, sin red ni pausas."""
    import price_series
    meta = metadata(base)
    with no_network():
        return price_series.fetch_price_series(ticker, meta["tickers"][ticker]["sector"],
                                               fetcher=replay_fetcher(base, overrides), sleep=lambda _s: None)
