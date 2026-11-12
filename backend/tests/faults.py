"""
Verificación de la v4 (V3 · fuentes caídas): inyección de fallos sobre el replay (tests/fixture_backend.replay).

Cada fallo se aplica encima del replay con un `_Patcher` y se deshace con `undo()`. Lo usan la batería de pytest
(tests/test_faults.py) y el servidor de replay (tests/replay_server.py: `POST /__replay/fault?name=…`, que cambia de
fallo en caliente para el e2e de e2e/v2-faults).

  yahoo_down       Yahoo no responde: sesión HTTP, yfinance, series de precios, lotes de tendencias, búsqueda y
                   mini-gráficas del cintillo.
  yahoo_401        quoteSummary responde 401 "Invalid Crumb" y yfinance.info viene vacío (plan B, como en Render).
                   Los fixtures del panel ya se capturaron así (metadata.render_simulation): el fallo lo fuerza
                   para cualquier petición, grabada o no.
  edgar_no_ua      sin la variable del User-Agent de la SEC: EDGAR desactivado.
  edgar_slow       cada petición a EDGAR tarda más que el presupuesto (análisis y segmentos).
  finnhub_no_key   sin FINNHUB_API_KEY: noticias, calendario y métricas de Finnhub ausentes.
  finnhub_429      con clave, pero Finnhub responde 429 (límite de peticiones) a todo.
  prices_empty     la serie de precios de la empresa viene vacía (Yahoo sin datos para el símbolo).
  sector_etf_down  la serie del ETF del sector falla (la de la empresa y la del mercado, no).
  logos_down       Parqet y Finnhub no responden a los logotipos: la web pone la placa con las iniciales.
"""
import logging
import threading
from typing import Callable, Dict, Optional, Tuple

import fixture_backend as fb

logger = logging.getLogger(__name__)


class SourceDown(ConnectionError):
    """Una fuente que no responde (como un error de conexión real)."""


def _raise(what: str):
    raise SourceDown(f"{what} no responde (fallo inyectado)")


class _DownSession:
    def get(self, url, params=None, **_kw):
        _raise("Yahoo")

    def __getattr__(self, name):
        return lambda *a, **kw: _raise("Yahoo")


class _DownTicker:
    def __init__(self, symbol, *_a, **_kw):
        self.ticker = symbol

    def __getattr__(self, name):
        _raise("Yahoo")


def _market_symbols():
    from settings import cfg
    return {cfg("market.price_series.market_symbol"), cfg("market.price_series.market_fallback_symbol")}


def _sector_etfs():
    import sector_profiles
    return {p.sector_etf.upper() for p in sector_profiles.SECTOR_PROFILES.values() if p.sector_etf}


def _yahoo_down(p: fb._Patcher) -> None:
    import price_history
    import search_v2
    import sparklines
    import trending
    import yf_adapter
    import yfinance

    def ensure():
        yf_adapter._session = _DownSession()
        yf_adapter._crumb = "fallo-inyectado"
    p.set(yf_adapter, "_ensure_session", ensure)
    p.set(yfinance, "Ticker", _DownTicker)
    p.set(price_history, "FETCHER", lambda *a, **kw: _raise("Yahoo"))
    p.set(trending, "FETCH_BATCH", lambda *a, **kw: _raise("Yahoo"))
    p.set(trending, "FETCH_QUOTES", lambda *a, **kw: _raise("Yahoo"))     # cintillo en vivo
    p.set(search_v2, "YAHOO_QUOTES", lambda *a, **kw: _raise("Yahoo"))
    p.set(sparklines, "FETCH", lambda *a, **kw: _raise("Yahoo"))          # P8: mini-gráficas del cintillo


def _yahoo_401(p: fb._Patcher) -> None:
    import yf_adapter
    import yfinance
    replay_ensure, replay_ticker = yf_adapter._ensure_session, yfinance.Ticker

    def ensure():
        replay_ensure()
        if not isinstance(yf_adapter._session, fb._Render401Session):
            yf_adapter._session = fb._Render401Session(yf_adapter._session)
    p.set(yf_adapter, "_ensure_session", ensure)
    p.set(yfinance, "Ticker", lambda symbol, *a, **kw: fb._RenderTicker(replay_ticker, symbol, *a, **kw))


def _edgar_no_ua(p: fb._Patcher) -> None:
    from settings import cfg
    p.env(cfg("data.edgar.user_agent_env"), None)


def _edgar_slow(p: fb._Patcher) -> None:
    """Cada petición espera más que el mayor de los presupuestos (análisis, segmentos y eventos de la gráfica). La
    espera es real (`Event.wait`; el replay anula `time.sleep`)."""
    import segments
    import sec_edgar
    from settings import cfg
    slow_s = max(cfg("data.edgar.budget_s"), cfg("market.segments.segments_budget_s")) + 1.0

    def slow(fetcher: Callable) -> Callable:
        def fetch(url, timeout):
            if slow_s > timeout:           # como urllib: la petición agota su tiempo de espera
                threading.Event().wait(timeout)
                raise TimeoutError("timed out")
            threading.Event().wait(slow_s)
            return fetcher(url, timeout)
        return fetch
    p.set(sec_edgar, "FETCHER", slow(sec_edgar.FETCHER))
    if segments.FETCHER is not None:
        p.set(segments, "FETCHER", slow(segments.FETCHER))


def _finnhub(p: fb._Patcher, with_key: bool) -> None:
    import finnhub_fallback

    def get(path, params):
        if with_key:
            logger.warning("[FINNHUB] %s failed: HTTP Error 429: Too Many Requests (fallo inyectado)", path)
        return None
    if not with_key:
        p.set(finnhub_fallback, "_api_key", lambda: "")
    p.set(finnhub_fallback, "_get", get)
    p.set(finnhub_fallback, "earnings_calendar", lambda *a, **kw: None)


def _prices_empty(p: fb._Patcher) -> None:
    import pandas as pd
    import price_history
    real = price_history.FETCHER
    skip = _market_symbols() | _sector_etfs()

    def fetch(symbol, period, interval):
        if str(symbol).upper() not in skip:
            return pd.DataFrame()
        return real(symbol, period, interval)
    p.set(price_history, "FETCHER", fetch)


def _sector_etf_down(p: fb._Patcher) -> None:
    import price_history
    real = price_history.FETCHER
    etfs = _sector_etfs() - _market_symbols()

    def fetch(symbol, period, interval):
        if str(symbol).upper() in etfs:
            _raise(f"Yahoo ({symbol})")
        return real(symbol, period, interval)
    p.set(price_history, "FETCHER", fetch)


def _spy_down(p: fb._Patcher) -> None:
    """Pasada final (PM): SPY, la serie con dividendos del S&P 500 (M7, [history] market_total_return_symbol), no
    responde; el índice (sin dividendos) sí."""
    import price_history
    from settings import cfg
    real = price_history.FETCHER
    trs = cfg("market.history.market_total_return_symbol").upper()

    def fetch(symbol, period, interval):
        if str(symbol).upper() == trs:
            _raise(f"Yahoo ({symbol})")
        return real(symbol, period, interval)
    p.set(price_history, "FETCHER", fetch)


def _logos_down(p: fb._Patcher) -> None:
    import logos

    def fetch(symbol):
        raise logos.SourceError("Parqet y Finnhub no responden (fallo inyectado)")
    p.set(logos, "FETCH", fetch)


FAULTS: Dict[str, Tuple[str, Callable[[fb._Patcher], None]]] = {
    "yahoo_down": ("Yahoo caído", _yahoo_down),
    "yahoo_401": ("Yahoo responde 401 (plan B)", _yahoo_401),
    "edgar_no_ua": ("EDGAR sin User-Agent", _edgar_no_ua),
    "edgar_slow": ("EDGAR agota el presupuesto", _edgar_slow),
    "finnhub_no_key": ("Finnhub sin clave", lambda p: _finnhub(p, with_key=False)),
    "finnhub_429": ("Finnhub 429", lambda p: _finnhub(p, with_key=True)),
    "prices_empty": ("Serie de precios vacía", _prices_empty),
    "sector_etf_down": ("ETF del sector caído", _sector_etf_down),
    "spy_down": ("SPY caído (rentabilidad total del mercado)", _spy_down),
    "logos_down": ("Logotipos caídos (Parqet y Finnhub)", _logos_down),
}


def reset_caches() -> None:
    """Cachés de todo lo que un fallo cambia: el pipeline, la gráfica, segmentos, rivales, cola, tendencias y
    logotipos."""
    import logos
    import peers
    import segments
    import sparklines
    import trending
    fb.reset_state()
    sparklines.reset()
    segments.reset()
    peers.reset()          # también la cola compartida (analysis_queue)
    trending.reset()
    logos.reset()


def apply(name: str) -> fb._Patcher:
    """Aplica el fallo `name` (debe estar en FAULTS) y devuelve el patcher para deshacerlo."""
    if name not in FAULTS:
        raise KeyError(f"fallo desconocido: {name} (válidos: {', '.join(FAULTS)})")
    p = fb._Patcher()
    FAULTS[name][1](p)
    reset_caches()
    return p


class Switch:
    """Un fallo activo a la vez (servidor de replay): `set(name)` deshace el anterior; `set(None)` lo quita."""

    def __init__(self):
        self.name: Optional[str] = None
        self._p: Optional[fb._Patcher] = None
        self._lock = threading.Lock()

    def set(self, name: Optional[str]) -> Optional[str]:
        import analysis_queue
        from settings import cfg
        with self._lock:
            # El análisis de fondo en marcha (rivales, tarjetas de la portada) acaba con el fallo con el que empezó:
            # si no, seguía con el nuevo y retenía el turno único del replay (test_faults: con EDGAR lento, el análisis
            # de la prueba siguiente esperaba 7,5 s detrás de una tarjeta de la anterior).
            analysis_queue.reset(wait_s=cfg("data.web.analysis_timeout_s"))
            if self._p is not None:
                self._p.undo()
                self._p, self.name = None, None
                reset_caches()
            if name:
                self._p, self.name = apply(name), name
            return self.name
