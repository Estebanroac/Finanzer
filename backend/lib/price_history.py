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
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional

import pandas as pd

from settings import cfg
import bounded

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
# Fase 6 (revisión de código, hallazgo 2): la serie de la empresa y la del índice de cada análisis, para los análisis
# que corren a la vez (server.max_concurrent_analyses); con 2 hilos, el 3.º y el 4.º esperaban y se quedaban sin serie.
_pool = ThreadPoolExecutor(max_workers=2 * cfg("data.server.max_concurrent_analyses"), thread_name_prefix="price_history")


def normalize(raw) -> Optional[pd.DataFrame]:
    """DataFrame de yfinance → columnas open/high/low/close (sin ajustar), adj_close, volume, dividend, split;
    índice de fechas de sesión (sin zona ni hora). Se descartan las filas sin cierre, salvo la de una sesión que trae
    máximo y mínimo: Yahoo da la barra del día con el cierre vacío hasta que la consolida (XOM en producción el
    2026-10-16 a las 20:53 de Nueva York: máximo 179.16, mínimo 175.15, cierre NaN). Es la sesión de la cotización y
    el rango de 52 semanas la necesita (la beta usa cierres y los descarta vacíos)."""
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
    df = df[df["close"].notna() | (df["high"].notna() & df["low"].notna())]
    return None if df.empty or df["close"].notna().sum() == 0 else df


def _download(symbol: str, fetcher: Fetcher, sleep=time.sleep, clock=time.perf_counter,
              period: Optional[str] = None) -> Dict[str, Any]:
    """`period`: el de la serie del motor (`market.history.period`) salvo que se pida otro (la gráfica de /v2)."""
    H = cfg("market.history")
    period = period or H["period"]
    t0, reason, attempts = clock(), None, 0
    for attempt in range(H["max_attempts"]):
        if attempt:
            sleep(H["retry_pause_s"] * attempt)
        attempts += 1
        try:
            frame = normalize(fetcher(symbol, period, H["interval"]))
        except Exception as e:  # la fuente falla de muchas maneras: se registra el tipo y el mensaje
            logger.warning(f"[PRICE_HISTORY] {symbol}: intento {attempts}: {type(e).__name__}: {e}")
            reason = "Yahoo no respondió"
            continue
        if frame is not None:
            lat = clock() - t0
            logger.info(f"[PRICE_HISTORY] {symbol}: {len(frame)} sesiones en {lat:.2f}s ({attempts} intento/s)")
            return {"symbol": symbol, "frame": frame, "attempts": attempts, "latency_s": lat, "reason": None}
        reason = "Yahoo no devolvió la serie de precios"
    # Verificación de la v4 (V3): el motivo se muestra en la página ("Sin gráfica de precio: …"): en lenguaje claro, sin
    # el nombre de la excepción (va al log).
    return {"symbol": symbol, "frame": None, "attempts": attempts, "latency_s": clock() - t0,
            "reason": f"{reason} ({attempts} intentos)"}


def _cached(key: str, ttl: float, make: Callable[[], Dict[str, Any]], fail_ttl: float = 0.0) -> Dict[str, Any]:
    """`fail_ttl` > 0: un fallo también se recuerda ese tiempo (no se repite la descarga en cada análisis)."""
    now = time.time()
    with _lock:
        ent = _cache.get(key)
        if ent and now - ent[0] < ttl and (ent[1]["frame"] is not None or now - ent[0] < fail_ttl):
            return ent[1]
    res = make()
    with _lock:
        bounded.put(_cache, key, (now, res), cfg("market.history.cache_max"))
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


def _peek(key: str, ttl: float) -> Optional[Dict[str, Any]]:
    with _lock:
        ent = _cache.get(key)
    # Revisión F5 (hallazgo 7): solo una entrada vigente; una vieja (la descarga de hoy agotó el tiempo) no se usa.
    return ent[1] if ent and time.time() - ent[0] < ttl else None


def peek(symbol: str) -> Optional[Dict[str, Any]]:
    """Fase 5: la serie del título que ya descargó el análisis (caché vigente), sin volver a descargar si falló."""
    return _peek(symbol.upper(), cfg("market.history.cache_ttl_s"))


def peek_market() -> Optional[Dict[str, Any]]:
    return _peek("^MARKET", cfg("market.history.market_cache_ttl_s"))


def sector(etf: Optional[str]) -> Dict[str, Any]:
    """Fase 5: serie diaria del ETF del sector (fuerza relativa), en caché como la del índice (`market_cache_ttl_s`):
    los análisis del mismo sector la comparten. Nunca bloquea: sin serie, la señal lo dice."""
    if not etf:
        return {"symbol": None, "frame": None, "attempts": 0, "latency_s": None, "reason": "sin ETF de sector"}
    H = cfg("market.history")
    try:
        # Revisión F5 (hallazgo 1): un fallo se recuerda `sector_fail_ttl_s` (no se repiten ~30 s por análisis).
        return _cached(f"^SECTOR:{etf.upper()}", H["market_cache_ttl_s"], lambda: _download(etf.upper(), FETCHER),
                       fail_ttl=cfg("market.context.sector_fail_ttl_s"))
    except Exception as e:  # la fuente falla de muchas maneras: el contexto sigue sin fuerza relativa
        return {"symbol": etf, "frame": None, "attempts": None, "latency_s": None, "reason": f"{type(e).__name__}: {e}"}


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


def day_change(frame: Optional[pd.DataFrame], price: Optional[float]) -> Dict[str, Any]:
    """Rediseño E2a: variación del precio frente al cierre (sin ajustar) de la sesión anterior. La última fila es la
    sesión del precio, aunque venga sin cierre (normalize la conserva a propósito: XOM)."""
    def none(reason):
        return {"status": "sin_dato", "prev_close": None, "change": None, "change_pct": None, "session": None,
                "reason": reason}
    if frame is None or price is None:
        return none("sin serie de precios o sin precio")
    if len(frame) < 2:
        return none("una sola sesión en la serie")
    prev = frame["close"].iloc[:-1].dropna()
    if prev.empty or not prev.iloc[-1] > 0:
        return none("sin cierre de la sesión anterior")
    pc = float(prev.iloc[-1])
    return {"status": "ok", "prev_close": pc, "change": price - pc, "change_pct": price / pc - 1,
            "session": frame.index[-1].strftime("%Y-%m-%d"), "reason": None}


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


# ── Rediseño E2a (T9): serie larga para la gráfica de /v2 ──
# Aparte de la del motor (2 años: beta, rango de 52 semanas, señales), que no cambia. Caché propia, acotada en número
# de símbolos (`chart_cache_max`, Render tiene 512 MB) y en tiempo (`chart_cache_ttl_s`): la menos usada sale primero.
_chart_cache: "OrderedDict[str, tuple]" = OrderedDict()


def chart(symbol: str) -> Dict[str, Any]:
    """Serie diaria de `chart_period` (5 años) del símbolo para la gráfica de /v2. Nunca lanza: sin serie, lo dice."""
    H = cfg("market.history")
    key = symbol.upper().strip()
    now = time.time()
    with _lock:
        ent = _chart_cache.get(key)
        if ent and now - ent[0] < H["chart_cache_ttl_s"] and ent[1]["frame"] is not None:
            _chart_cache.move_to_end(key)
            return ent[1]
    return _chart_gate().run(key, lambda: _chart_download(key, H), lambda r: r["frame"] is None)


def _chart_download(key: str, H: Dict[str, Any]) -> Dict[str, Any]:
    now = time.time()
    try:
        res = _download(key, FETCHER, period=H["chart_period"])
    except Exception as e:  # la fuente falla de muchas maneras: sin serie y se dice
        res = {"symbol": key, "frame": None, "attempts": None, "latency_s": None, "reason": f"{type(e).__name__}: {e}"}
    if res["frame"] is not None:
        with _lock:
            _chart_cache[key] = (now, res)
            _chart_cache.move_to_end(key)
            while len(_chart_cache) > H["chart_cache_max"]:
                _chart_cache.popitem(last=False)
    return res


_gate: List[Any] = []


def _chart_gate():
    """V6 (B8): como mucho `chart_concurrency` descargas de la gráfica a la vez, una por símbolo, y un símbolo sin
    serie se recuerda `chart_fail_ttl_s` (antes se volvía a descargar en cada consulta)."""
    import lazy_gate
    with _lock:
        if not _gate:
            H = cfg("market.history")
            _gate.append(lazy_gate.Gate(H["chart_concurrency"], H["chart_fail_ttl_s"], H["chart_cache_max"]))
        return _gate[0]


def chart_market() -> Dict[str, Any]:
    """La serie larga del S&P 500 (con el ETF que lo replica si el índice falla), como market()."""
    P = cfg("market.price_series")
    res = chart(P["market_symbol"])
    if res["frame"] is None:
        alt = dict(chart(P["market_fallback_symbol"]))
        alt["fallback_of"] = {"symbol": P["market_symbol"], "reason": res["reason"]}
        return alt
    return res


def reset() -> None:
    """Vacía la caché (tests)."""
    with _lock:
        _cache.clear()
        _chart_cache.clear()
        _gate.clear()
