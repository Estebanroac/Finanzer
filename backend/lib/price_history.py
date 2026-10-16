"""
Serie diaria de precios en el camino del análisis (fase 2b; D5: solo contexto).

De la serie solo entran en el motor tres cosas, cada una con su tarea de la 2b:
  · los dividendos pagados por el propio título (T2: el indicado en la moneda y la clase del precio);
  · el rango de 52 semanas de la misma sesión que el precio (T6);
  · la beta propia frente al S&P 500 (T6).
Las señales técnicas (lib/market_signals.py, fase 5) no se calculan aquí.

Una descarga por análisis: `history(period, interval, auto_adjust=False, actions=True)` de yfinance, que trae el
cierre, el máximo y el mínimo reales (sin ajustar por dividendos; sí por splits), el cierre ajustado y los eventos
(dividendos y splits). El S&P 500 se descarga aparte y se cachea por proceso (market_cache_ttl_s).

Nunca bloquea el análisis: la descarga corre en un hilo desde el inicio de get_ticker_info (en paralelo con los
estados) y, si falla o tarda más que `wait_timeout_s`, el análisis sigue sin serie y lo dice (`status`, `reason`).

El descargador es inyectable (`FETCHER`): en producción, yfinance; en los tests, el replay de los fixtures.
"""
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional

import pandas as pd

from settings import cfg

Fetcher = Callable[[str, str, str], Any]
logger = logging.getLogger(__name__)


def yfinance_fetcher(symbol: str, period: str, interval: str):
    """Descarga real: precios sin ajustar por dividendos, cierre ajustado aparte y eventos."""
    import yfinance as yf
    return yf.Ticker(symbol).history(period=period, interval=interval, auto_adjust=False, actions=True,
                                     timeout=cfg("data.yahoo.http_timeout_s"))


FETCHER: Fetcher = yfinance_fetcher

_cache: Dict[str, tuple] = {}          # símbolo -> (ts, resultado)
_lock = threading.Lock()
_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="price_history")


def normalize(raw) -> Optional[pd.DataFrame]:
    """DataFrame de yfinance → columnas open/high/low/close (sin ajustar), adj_close, volume, dividend, split;
    índice de fechas de sesión (sin zona ni hora). Filas sin cierre se descartan."""
    if raw is None or getattr(raw, "empty", True) or "Close" not in raw:
        return None
    idx = pd.DatetimeIndex(raw.index)
    if idx.tz is not None:
        idx = idx.tz_localize(None)

    def col(name, fill=float("nan")):
        if name in raw:
            return pd.to_numeric(raw[name], errors="coerce").to_numpy(dtype=float)
        return pd.Series(fill, index=raw.index).to_numpy(dtype=float)

    close = col("Close")
    df = pd.DataFrame({"open": col("Open"), "high": col("High"), "low": col("Low"), "close": close,
                       "adj_close": col("Adj Close") if "Adj Close" in raw else close,
                       "volume": col("Volume"), "dividend": col("Dividends", 0.0), "split": col("Stock Splits", 0.0)},
                      index=idx.normalize())
    df[["dividend", "split"]] = df[["dividend", "split"]].fillna(0.0)
    df.index.name = "date"
    df = df[~df.index.duplicated(keep="last")].sort_index()
    df = df[df["close"].notna()]
    return None if df.empty else df


def _download(symbol: str, fetcher: Fetcher, sleep=time.sleep, clock=time.perf_counter) -> Dict[str, Any]:
    H = cfg("market.history")
    t0, reason, attempts = clock(), None, 0
    for attempt in range(H["max_attempts"]):
        if attempt:
            sleep(H["retry_pause_s"] * attempt)
        attempts += 1
        try:
            frame = normalize(fetcher(symbol, H["period"], H["interval"]))
        except Exception as e:  # la fuente falla de muchas maneras: se registra el tipo y el mensaje
            reason = f"{type(e).__name__}: {e}"
            continue
        if frame is not None:
            lat = clock() - t0
            logger.info(f"[PRICE_HISTORY] {symbol}: {len(frame)} sesiones en {lat:.2f}s ({attempts} intento/s)")
            return {"symbol": symbol, "frame": frame, "attempts": attempts, "latency_s": lat, "reason": None}
        reason = "respuesta vacía"
    return {"symbol": symbol, "frame": None, "attempts": attempts, "latency_s": clock() - t0,
            "reason": f"sin serie tras {attempts} intentos ({reason})"}


def _cached(key: str, ttl: float, make: Callable[[], Dict[str, Any]]) -> Dict[str, Any]:
    now = time.time()
    with _lock:
        ent = _cache.get(key)
        if ent and now - ent[0] < ttl and ent[1]["frame"] is not None:
            return ent[1]
    res = make()
    with _lock:
        _cache[key] = (now, res)
    return res


def company(symbol: str) -> Dict[str, Any]:
    """Serie diaria del título (caché de `cache_ttl_s`)."""
    H = cfg("market.history")
    return _cached(symbol.upper(), H["cache_ttl_s"], lambda: _download(symbol.upper(), FETCHER))


def market() -> Dict[str, Any]:
    """Serie diaria del S&P 500 (con el ETF que lo replica si el índice falla), caché de `market_cache_ttl_s`."""
    P, H = cfg("market.price_series"), cfg("market.history")

    def make():
        res = _download(P["market_symbol"], FETCHER)
        if res["frame"] is None:
            alt = _download(P["market_fallback_symbol"], FETCHER)
            alt["fallback_of"] = {"symbol": P["market_symbol"], "reason": res["reason"]}
            return alt
        return res
    return _cached("^MARKET", H["market_cache_ttl_s"], make)


def _company_and_market(symbol: str) -> Dict[str, Any]:
    """El título y, después, el S&P 500 (en caché casi siempre) para la beta propia (T6)."""
    res = dict(company(symbol))
    try:
        res["market"] = market()
    except Exception as e:  # el índice falla de muchas maneras: el análisis sigue sin beta propia y lo dice
        res["market"] = {"symbol": None, "frame": None, "reason": f"{type(e).__name__}: {e}"}
    return res


def start(symbol: str):
    """Lanza la descarga del título y del índice en un hilo (se recoge con `collect`)."""
    return _pool.submit(_company_and_market, symbol)


def collect(future) -> Dict[str, Any]:
    """Resultado de `start`, o "sin serie" si falla o tarda más que `wait_timeout_s`."""
    if future is None:
        return {"symbol": None, "frame": None, "attempts": 0, "latency_s": None, "reason": "no se lanzó la descarga"}
    try:
        return future.result(timeout=cfg("market.history.wait_timeout_s"))
    except Exception as e:  # tiempo agotado u otro fallo del hilo: el análisis sigue sin serie
        return {"symbol": None, "frame": None, "attempts": None, "latency_s": None,
                "reason": f"{type(e).__name__}: {e}"}


def dividend_events(frame: Optional[pd.DataFrame]) -> List[tuple]:
    """[(fecha ex, importe)] de los dividendos declarados en la serie, en la moneda y la clase del precio."""
    if frame is None or "dividend" not in frame:
        return []
    d = frame["dividend"]
    return [(ts.date(), float(v)) for ts, v in d[d > 0].items()]


def summary(res: Dict[str, Any]) -> Dict[str, Any]:
    """Registro para data_provenance.price_history (sin la serie)."""
    f = res.get("frame")
    out = {"symbol": res.get("symbol"), "status": "ok" if f is not None else "sin_dato",
           "reason": res.get("reason"), "attempts": res.get("attempts"),
           "source": "Yahoo Finance (yfinance history: precios sin ajustar por dividendos y eventos)",
           "period": cfg("market.history.period"), "interval": cfg("market.history.interval")}
    if f is not None:
        out.update({"first_date": f.index[0].strftime("%Y-%m-%d"), "last_date": f.index[-1].strftime("%Y-%m-%d"),
                    "rows": len(f)})
    mk = res.get("market")
    if mk is not None:
        mf = mk.get("frame")
        out["market"] = {"symbol": mk.get("symbol"), "status": "ok" if mf is not None else "sin_dato",
                         "reason": mk.get("reason"), "fallback_of": mk.get("fallback_of"),
                         **({"last_date": mf.index[-1].strftime("%Y-%m-%d"), "rows": len(mf)} if mf is not None else {})}
    return out


def reset() -> None:
    """Vacía la caché (tests)."""
    with _lock:
        _cache.clear()
