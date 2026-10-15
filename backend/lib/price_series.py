"""
Serie diaria de precios (preparación de las fases 2b y 5; PLAN_FIABILIDAD §2.2, RECON §6.6 y C8).

MÓDULO AISLADO: no lo importa el motor (main.py), ni el score, ni la web, ni el PDF. Lo usan
lib/market_signals.py (señales técnicas y beta propia) y los tests.

Para un ticker descarga tres series diarias AJUSTADAS por splits y dividendos (cierre ajustado y volumen,
yfinance `history(auto_adjust=True)`), con el periodo de config (market.price_series.period):

  company  la empresa;
  market   el S&P 500 (^GSPC). Si el índice falla tras los reintentos, el ETF que lo replica (SPY),
           declarado en `market_fallback`;
  sector   el ETF de su sector (sector_profiles: `sector_info.sector_etf`; sector desconocido → SPY).

Cada serie lleva su estado:

  ok          serie completa, sin huecos ni saltos;
  sospechosa  huecos (sesiones en que cotizó el mercado y la serie no, desde su primera fecha; incluye una
              serie desactualizada que acaba antes que el índice) o saltos de un día mayores que el umbral
              (max(p1/p0, p0/p1) − 1 > jump_threshold, 0.8: caída ≥ 44% o subida ≥ 80%; posible split sin
              ajustar), con las fechas;
  sin_dato    la descarga falló tras `max_attempts` intentos o vino vacía, con el motivo.

Nunca se devuelve una serie parcial sin avisar: el estado global (`status`) es el peor de los tres y
`reasons` dice qué serie y por qué. Los días con volumen cero y los eventos de split que declara Yahoo
(`splits`, ya aplicados al cierre ajustado) se listan como información: no cambian el estado. Cada split
lleva `kind`: "split" o "posible_escision" (ratio que no es una fracción simple: UL, Magnum, 2025-12-09,
0.888); market_signals marca con una nota la beta y el drawdown cuya ventana contiene una posible escisión.

Sin secretos: Yahoo no usa clave. Concurrencia: este módulo descarga en serie; la pausa entre reintentos
crece con el intento (retry_pause_s × k). La latencia de cada serie se mide y se devuelve (`latency_s`).

El descargador se inyecta (`fetcher`): en producción, yfinance; en los tests, el replay de
tests/fixtures/prices/ (sin red).
"""
import time
from fractions import Fraction
from typing import Any, Callable, Dict, List, Optional

import pandas as pd

from sector_profiles import get_sector_profile
from settings import cfg

STATUS_ORDER = ("ok", "sospechosa", "sin_dato")

Fetcher = Callable[[str, str, str], Any]


def yfinance_fetcher(symbol: str, period: str, interval: str):
    """Descarga real: cierre y volumen ajustados por splits y dividendos."""
    import yfinance as yf
    return yf.Ticker(symbol).history(period=period, interval=interval, auto_adjust=True)


def normalize_frame(raw) -> Optional[pd.DataFrame]:
    """DataFrame de yfinance → columnas `close` y `volume` con índice de fechas (sin zona ni hora).

    La fecha es la de la sesión en la zona del mercado (yfinance la da en la hora local de la bolsa).
    Filas sin cierre se descartan (aparecen como huecos frente al calendario del índice)."""
    if raw is None or getattr(raw, "empty", True) or "Close" not in raw:
        return None
    idx = pd.DatetimeIndex(raw.index)
    if idx.tz is not None:
        idx = idx.tz_localize(None)
    vol = raw["Volume"] if "Volume" in raw else pd.Series(float("nan"), index=raw.index)
    split = raw["Stock Splits"] if "Stock Splits" in raw else pd.Series(0.0, index=raw.index)
    df = pd.DataFrame({"close": pd.to_numeric(raw["Close"], errors="coerce").to_numpy(dtype=float),
                       "volume": pd.to_numeric(vol, errors="coerce").to_numpy(dtype=float),
                       "split": pd.to_numeric(split, errors="coerce").fillna(0).to_numpy(dtype=float)},
                      index=idx.normalize())
    df.index.name = "date"
    df = df[~df.index.duplicated(keep="last")].sort_index()
    df = df[df["close"].notna()]
    return None if df.empty else df


def download(symbol: str, fetcher: Fetcher, sleep: Callable[[float], None] = time.sleep,
             clock: Callable[[], float] = time.perf_counter) -> Dict[str, Any]:
    """Una serie con reintentos limitados: {symbol, frame, attempts, latency_s, reason}."""
    P = cfg("market.price_series")
    t0 = clock()
    reason = None
    attempts = 0
    for attempt in range(P["max_attempts"]):
        if attempt:
            sleep(P["retry_pause_s"] * attempt)
        attempts += 1
        try:
            frame = normalize_frame(fetcher(symbol, P["period"], P["interval"]))
        except Exception as e:  # la fuente puede fallar de muchas maneras; se registra el tipo y el mensaje
            reason = f"{type(e).__name__}: {e}"
            continue
        if frame is not None:
            return {"symbol": symbol, "frame": frame, "attempts": attempts,
                    "latency_s": clock() - t0, "reason": None}
        reason = "respuesta vacía"
    return {"symbol": symbol, "frame": None, "attempts": attempts, "latency_s": clock() - t0,
            "reason": f"sin dato tras {attempts} intentos ({reason})"}


def split_kind(ratio: float) -> str:
    """"split" si el ratio es una fracción simple (10:1, 3:2, 1:8…); si no, "posible_escision"."""
    P = cfg("market.price_series")
    simple = Fraction(ratio).limit_denominator(P["spin_off_max_denominator"])
    return "split" if abs(float(simple) - ratio) <= P["spin_off_ratio_tol"] else "posible_escision"


def check_series(frame: Optional[pd.DataFrame], calendar: Optional[pd.DatetimeIndex] = None) -> Dict[str, Any]:
    """Huecos frente al calendario del índice, saltos de un día y volumen cero → {status, reasons, ...}."""
    P = cfg("market.price_series")
    if frame is None:
        return {"status": "sin_dato", "reasons": ["sin serie"], "missing_days": [], "jumps": [],
                "zero_volume_days": [], "splits": []}
    missing: List[str] = []
    if calendar is not None and len(calendar):
        expected = calendar[calendar >= frame.index[0]]
        missing = [d.strftime("%Y-%m-%d") for d in expected.difference(frame.index)]
    close = frame["close"]
    ratio = close / close.shift(1)
    jump = pd.concat([ratio, 1 / ratio], axis=1).max(axis=1) - 1
    jumps = [{"date": d.strftime("%Y-%m-%d"), "change": float(ratio.loc[d] - 1)}
             for d in jump.index[jump > P["jump_threshold"]]]
    zero_vol = [d.strftime("%Y-%m-%d") for d in frame.index[frame["volume"] == 0]]
    splits = [{"date": d.strftime("%Y-%m-%d"), "ratio": float(frame.loc[d, "split"]),
               "kind": split_kind(float(frame.loc[d, "split"]))}
              for d in frame.index[frame["split"] != 0]] if "split" in frame else []
    reasons = []
    if len(missing) > P["max_missing_days"]:
        reasons.append(f"{len(missing)} sesiones sin cotización frente al índice: {', '.join(missing)}")
    if jumps:
        reasons.append("salto de un día por encima del umbral (¿split sin ajustar?): "
                       + ", ".join(f"{j['date']} ({j['change']:+.1%})" for j in jumps))
    return {"status": "sospechosa" if reasons else "ok", "reasons": reasons, "missing_days": missing,
            "jumps": jumps, "zero_volume_days": zero_vol, "splits": splits}


def _series_entry(role: str, dl: Dict[str, Any], calendar) -> Dict[str, Any]:
    chk = check_series(dl["frame"], calendar)
    reasons = [dl["reason"]] if dl["frame"] is None else chk["reasons"]
    out = {"role": role, "symbol": dl["symbol"], "status": chk["status"], "reasons": reasons,
           "frame": dl["frame"], "attempts": dl["attempts"], "latency_s": dl["latency_s"],
           "missing_days": chk["missing_days"], "jumps": chk["jumps"],
           "zero_volume_days": chk["zero_volume_days"], "splits": chk["splits"]}
    if dl["frame"] is not None:
        out["first_date"] = dl["frame"].index[0].strftime("%Y-%m-%d")
        out["last_date"] = dl["frame"].index[-1].strftime("%Y-%m-%d")
        out["rows"] = len(dl["frame"])
    return out


def fetch_price_series(ticker: str, sector: Optional[str] = None, fetcher: Optional[Fetcher] = None,
                       sleep: Callable[[float], None] = time.sleep,
                       clock: Callable[[], float] = time.perf_counter) -> Dict[str, Any]:
    """Las tres series de un ticker con su estado y su latencia.

    `sector`: clave canónica o nombre de Yahoo (lo resuelve sector_profiles). Devuelve
    {ticker, status, reasons, market_symbol, market_fallback, sector_etf, series: {company, market, sector},
    latency_s, params}."""
    P = cfg("market.price_series")
    fetcher = fetcher or yfinance_fetcher
    t0 = clock()
    cache: Dict[str, Dict[str, Any]] = {}

    def get(symbol):
        if symbol not in cache:
            cache[symbol] = download(symbol, fetcher, sleep, clock)
        return cache[symbol]

    market = get(P["market_symbol"])
    fallback = False
    if market["frame"] is None:
        first_reason = market["reason"]
        market = dict(get(P["market_fallback_symbol"]))
        fallback = True
        if market["frame"] is None:
            market["reason"] = f"{P['market_symbol']}: {first_reason}; {P['market_fallback_symbol']}: {market['reason']}"
    calendar = market["frame"].index if market["frame"] is not None else None
    etf = get_sector_profile(sector or "").sector_etf
    series = {
        "company": _series_entry("company", get(ticker), calendar),
        "market": _series_entry("market", market, None),
        "sector": _series_entry("sector", get(etf), calendar),
    }
    if fallback and market["frame"] is not None:
        series["market"]["reasons"] = [f"{P['market_symbol']} sin dato ({first_reason}); se usa "
                                       f"{P['market_fallback_symbol']}"] + series["market"]["reasons"]
    worst = max((s["status"] for s in series.values()), key=STATUS_ORDER.index)
    reasons = [f"{role} ({s['symbol']}): {r}" for role, s in series.items() for r in s["reasons"]
               if s["status"] != "ok" or role == "market" and fallback]
    return {"ticker": ticker, "status": worst, "reasons": reasons,
            "market_symbol": series["market"]["symbol"], "market_fallback": fallback, "sector_etf": etf,
            "series": series, "latency_s": clock() - t0,
            "params": {k: P[k] for k in ("period", "interval", "market_symbol", "market_fallback_symbol",
                                         "max_attempts", "max_missing_days", "jump_threshold")}}
