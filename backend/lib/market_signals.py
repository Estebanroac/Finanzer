"""
Señales técnicas con evidencia y beta propia (preparación de las fases 2b y 5; PLAN_FIABILIDAD §2.2).

MÓDULO AISLADO: funciones puras sobre la serie diaria ajustada de lib/price_series.py. No entran en el
motor, ni en el score, ni en la web, ni en el PDF. Son CONTEXTO que, en la fase 5, modulará la confianza;
nunca suman ni restan puntos (PLAN §2.3).

Solo las señales de PLAN §2.2. **Fuera:** RSI, MACD, figuras chartistas y Fibonacci (sin evidencia fuera de
muestra que justifique ponerlas en un informe que se presenta como fiable).

Cada función devuelve un dict con:
  status  "ok" | "sin_dato" | "historia_insuficiente";
  value   la cifra principal (None si no hay);
  params  los parámetros usados (de config/market.toml; Blume de valuation.capm);
  as_of   la fecha de la última sesión usada;
y los campos propios de la señal. Las entradas son pd.Series indexadas por fecha (orden ascendente), como
las columnas `close` y `volume` de price_series. Los parámetros salen de la config: ningún literal.
"""
import math
from typing import Any, Dict, Optional

import pandas as pd

from settings import cfg


def _date(ts) -> Optional[str]:
    return None if ts is None else pd.Timestamp(ts).strftime("%Y-%m-%d")


def _empty(series) -> bool:
    return series is None or len(series) == 0


def _result(status: str, params: Dict[str, Any], series=None, value=None, reason=None, **extra) -> Dict[str, Any]:
    out = {"status": status, "value": value, "params": dict(params),
           "as_of": None if _empty(series) else _date(series.index[-1])}
    if reason:
        out["reason"] = reason
    out.update(extra)
    return out


def _short(params, series, needed: int) -> Dict[str, Any]:
    return _result("historia_insuficiente", params, series,
                   reason=f"{len(series)} sesiones; hacen falta {needed}", needed=needed, available=len(series))


def momentum_12_1(close: pd.Series) -> Dict[str, Any]:
    """Momentum 12-1: rentabilidad de 12 meses excluyendo el último mes, P(t−21) / P(t−252) − 1.

    Referencia: Jegadeesh y Titman (1993), "Returns to Buying Winners and Selling Losers"; Asness, Moskowitz y
    Pedersen (2013), "Value and Momentum Everywhere". Se excluye el último mes por la reversión a corto plazo."""
    P = cfg("market.signals.momentum")
    if _empty(close):
        return _result("sin_dato", P, close, reason="sin serie")
    needed = P["lookback_sessions"] + 1
    if len(close) < needed:
        return _short(P, close, needed)
    start = close.iloc[-needed]
    end = close.iloc[-1 - P["skip_sessions"]]
    return _result("ok", P, close, value=float(end / start - 1),
                   start_date=_date(close.index[-needed]), end_date=_date(close.index[-1 - P["skip_sessions"]]))


def trend(close: pd.Series) -> Dict[str, Any]:
    """Tendencia: precio frente a su media de 200 sesiones y pendiente de esa media.

    value = P(t) / SMA200(t) − 1; slope = SMA200(t) / SMA200(t − slope_sessions) − 1.
    Régimen: "alcista" (precio sobre la media y media subiendo), "bajista" (debajo y bajando), "lateral" (resto).
    Referencias: Faber (2007), "A Quantitative Approach to Tactical Asset Allocation"; Moskowitz, Ooi y
    Pedersen (2012), "Time Series Momentum"."""
    P = cfg("market.signals.trend")
    if _empty(close):
        return _result("sin_dato", P, close, reason="sin serie")
    needed = P["sma_sessions"] + P["slope_sessions"]
    if len(close) < needed:
        return _short(P, close, needed)
    sma = close.rolling(P["sma_sessions"]).mean()
    above = float(close.iloc[-1] / sma.iloc[-1] - 1)
    slope = float(sma.iloc[-1] / sma.iloc[-1 - P["slope_sessions"]] - 1)
    if above > 0 and slope > 0:
        regime = "alcista"
    elif above < 0 and slope < 0:
        regime = "bajista"
    else:
        regime = "lateral"
    return _result("ok", P, close, value=above, sma=float(sma.iloc[-1]), price=float(close.iloc[-1]),
                   slope=slope, regime=regime)


def realized_volatility(close: pd.Series) -> Dict[str, Any]:
    """Volatilidad realizada: desviación típica (muestral) de las rentabilidades diarias logarítmicas del
    último año, anualizada con √sessions_per_year. Referencia: práctica estándar de gestión de riesgo."""
    P = {**cfg("market.signals.volatility"), "sessions_per_year": cfg("market.signals.sessions_per_year")}
    if _empty(close):
        return _result("sin_dato", P, close, reason="sin serie")
    needed = P["window_sessions"] + 1
    if len(close) < needed:
        return _short(P, close, needed)
    window = close.iloc[-needed:]
    rets = (window / window.shift(1)).dropna().map(math.log)
    return _result("ok", P, close, value=float(rets.std() * P["sessions_per_year"] ** 0.5),
                   observations=len(rets))


def max_drawdown(close: pd.Series, years: int) -> Dict[str, Any]:
    """Drawdown máximo en `years` años (years × sessions_per_year sesiones de rentabilidad): mayor caída desde un
    máximo previo dentro de la ventana, min(P / máx. acumulado − 1), con las fechas del pico y del valle.
    Referencia: práctica estándar de gestión de riesgo."""
    P = {"years": years, "sessions_per_year": cfg("market.signals.sessions_per_year")}
    if _empty(close):
        return _result("sin_dato", P, close, reason="sin serie")
    needed = years * P["sessions_per_year"] + 1
    if len(close) < needed:
        return _short(P, close, needed)
    window = close.iloc[-needed:]
    dd = window / window.cummax() - 1
    trough = dd.idxmin()
    peak = window.loc[:trough].idxmax()
    return _result("ok", P, close, value=float(dd.loc[trough]), peak_date=_date(peak), trough_date=_date(trough),
                   peak_price=float(window.loc[peak]), trough_price=float(window.loc[trough]),
                   window_start=_date(window.index[0]))


def relative_strength(close: pd.Series, sector_close: Optional[pd.Series]) -> Dict[str, Any]:
    """Fuerza relativa frente al ETF del sector: rentabilidad de la empresa menos la del ETF en 6 y 12 meses
    (126 y 252 sesiones comunes). value = diferencia de la ventana más larga; `windows` trae cada una.
    Referencia: extensión del momentum (Jegadeesh y Titman, 1993) a la comparación con el sector."""
    P = cfg("market.signals.relative_strength")
    if _empty(close):
        return _result("sin_dato", P, close, reason="sin serie de la empresa")
    if _empty(sector_close):
        return _result("sin_dato", P, close, reason="sin serie del ETF del sector")
    both = pd.concat([close, sector_close], axis=1, join="inner").dropna()
    windows = {}
    for w in P["windows_sessions"]:
        if len(both) < w + 1:
            windows[str(w)] = {"status": "historia_insuficiente", "needed": w + 1, "available": len(both)}
            continue
        r_co = float(both.iloc[-1, 0] / both.iloc[-1 - w, 0] - 1)
        r_etf = float(both.iloc[-1, 1] / both.iloc[-1 - w, 1] - 1)
        windows[str(w)] = {"status": "ok", "company": r_co, "sector": r_etf, "difference": r_co - r_etf,
                           "start_date": _date(both.index[-1 - w])}
    longest = windows[str(max(P["windows_sessions"]))]
    if longest["status"] != "ok":
        return _result("historia_insuficiente", P, both, reason="sesiones comunes insuficientes", windows=windows)
    return _result("ok", P, both, value=longest["difference"], windows=windows)


def abnormal_volume(volume: pd.Series) -> Dict[str, Any]:
    """Volumen anómalo: z = (media de las últimas 5 sesiones − media de las 90 anteriores) / desviación típica
    (muestral) del volumen diario de esas 90. La referencia no se solapa con la ventana reciente.
    Referencia: Gervais, Kaniel y Mingelgrin (2001), "The High-Volume Return Premium"."""
    P = cfg("market.signals.volume")
    if _empty(volume) or volume.isna().all():
        return _result("sin_dato", P, volume, reason="sin volumen")
    vol = volume.dropna()
    needed = P["recent_sessions"] + P["baseline_sessions"]
    if len(vol) < needed:
        return _short(P, vol, needed)
    recent = vol.iloc[-P["recent_sessions"]:]
    base = vol.iloc[-needed:-P["recent_sessions"]]
    sd = float(base.std())
    if not sd > 0:
        return _result("sin_dato", P, vol, reason="volumen de referencia constante o cero (z sin definir)",
                       recent_mean=float(recent.mean()), baseline_mean=float(base.mean()))
    return _result("ok", P, vol, value=float((recent.mean() - base.mean()) / sd), recent_mean=float(recent.mean()),
                   baseline_mean=float(base.mean()), baseline_std=sd, zero_volume_sessions=int((recent == 0).sum()))


def range_52w_position(close: pd.Series) -> Dict[str, Any]:
    """Posición en el rango de 52 semanas desde la serie: (P − mín.) / (máx. − mín.) sobre las últimas 252
    sesiones, INCLUIDA la de hoy (criterio de la fase 1: el rango contiene la cotización actual). Usa cierres
    ajustados (no máximos y mínimos intradía), así que puede diferir algo del rango que publica Yahoo."""
    P = cfg("market.signals.range52")
    if _empty(close):
        return _result("sin_dato", P, close, reason="sin serie")
    if len(close) < P["window_sessions"]:
        return _short(P, close, P["window_sessions"])
    window = close.iloc[-P["window_sessions"]:]
    hi, lo = float(window.max()), float(window.min())
    if not hi > lo:
        return _result("sin_dato", P, close, reason="rango nulo (máximo = mínimo)")
    return _result("ok", P, close, value=(float(close.iloc[-1]) - lo) / (hi - lo), high=hi, low=lo,
                   high_date=_date(window.idxmax()), low_date=_date(window.idxmin()))


def weekly_returns(close: pd.Series, frequency: str) -> pd.Series:
    """Rentabilidades semanales simples: último cierre de cada semana (`frequency`, W-FRI) y variación."""
    s = close.dropna().resample(frequency).last().dropna()
    return s.pct_change().dropna()


def beta(close: pd.Series, market_close: Optional[pd.Series], market_symbol: Optional[str] = None) -> Dict[str, Any]:
    """Beta propia: MCO de las rentabilidades SEMANALES de 2 años (104 semanas) de la empresa sobre las del
    S&P 500; beta = cov(r, r_m) / var(r_m), R² = corr², nº de semanas. Cruda y ajustada por Blume con los
    coeficientes ya existentes en config (valuation.capm: blume_weight × β + blume_prior).

    Mismo método que la beta de referencia de la fase 2a (tests/beta_ref.py de la rama fiabilidad/f2a-medir):
    cierre ajustado de la última sesión de cada semana (W-FRI), rentabilidades simples, semanas comunes, las
    104 últimas, mínimo 52.

    ADR: la beta se calcula frente al S&P 500 con el precio del ADR en dólares (perspectiva del inversor en
    dólares, que es la del CAPM y el WACC del motor), no frente al índice de su mercado local.
    Referencia: práctica estándar (Bloomberg BETA: 2 años semanales; ajuste de Blume, 1971)."""
    B = cfg("market.signals.beta")
    C = cfg("valuation.capm")
    P = {**B, "blume_weight": C["blume_weight"], "blume_prior": C["blume_prior"], "market_symbol": market_symbol}
    if _empty(close):
        return _result("sin_dato", P, close, reason="sin serie de la empresa")
    if _empty(market_close):
        return _result("sin_dato", P, close, reason="sin serie del mercado")
    df = pd.concat([weekly_returns(close, B["frequency"]), weekly_returns(market_close, B["frequency"])],
                   axis=1, join="inner").dropna().tail(B["window_weeks"])
    if len(df) < B["min_weeks"]:
        return _result("historia_insuficiente", P, close, reason=f"{len(df)} semanas; hacen falta {B['min_weeks']}",
                       needed=B["min_weeks"], available=len(df), observations=len(df))
    r, rm = df.iloc[:, 0], df.iloc[:, 1]
    var_m = float(rm.var())
    if not var_m > 0:
        return _result("sin_dato", P, close, reason="varianza del mercado nula")
    raw = float(r.cov(rm)) / var_m
    corr = float(r.corr(rm))
    return _result("ok", P, close, value=raw, raw=raw, adjusted=C["blume_weight"] * raw + C["blume_prior"],
                   r2=corr * corr, observations=len(df), first_week=_date(df.index[0]), last_week=_date(df.index[-1]),
                   window_start=_date(df.index[0] - pd.tseries.frequencies.to_offset(B["frequency"])))


def _blocked(reason: str) -> Dict[str, Any]:
    return {"status": "sin_dato", "value": None, "params": {}, "as_of": None, "reason": reason}


def all_signals(price_series: Dict[str, Any]) -> Dict[str, Any]:
    """Todas las señales de un resultado de price_series.fetch_price_series.

    Una serie `sin_dato` o `sospechosa` no alimenta señales: devuelven `sin_dato` con el motivo (un split sin
    ajustar o un hueco falsearían el momentum, el drawdown y la beta).

    Una posible escisión registrada como split (price_series `splits[].kind`) NO bloquea: la beta y cada drawdown
    cuya ventana la contiene llevan `notes` con la fecha y el ratio (decisión del usuario, 2026-10-15; se revisa
    en la fase 5)."""
    S = price_series["series"]

    def usable(role):
        s = S[role]
        if s["status"] != "ok":
            return None, f"serie {role} ({s['symbol']}) {s['status']}: " + "; ".join(s["reasons"])
        return s["frame"], None

    co, why = usable("company")
    mk, why_m = usable("market")
    se, why_s = usable("sector")
    out: Dict[str, Any] = {}
    if co is None:
        for name in ("momentum_12_1", "trend", "realized_volatility", "abnormal_volume", "range_52w_position",
                     "relative_strength", "beta"):
            out[name] = _blocked(why)
        out["max_drawdown"] = {str(y): _blocked(why) for y in cfg("market.signals.drawdown.windows_years")}
        return out
    close = co["close"]
    out["momentum_12_1"] = momentum_12_1(close)
    out["trend"] = trend(close)
    out["realized_volatility"] = realized_volatility(close)
    out["max_drawdown"] = {str(y): max_drawdown(close, y) for y in cfg("market.signals.drawdown.windows_years")}
    out["relative_strength"] = relative_strength(close, se["close"]) if se is not None else _blocked(why_s)
    out["abnormal_volume"] = abnormal_volume(co["volume"])
    out["range_52w_position"] = range_52w_position(close)
    out["beta"] = beta(close, mk["close"], S["market"]["symbol"]) if mk is not None else _blocked(why_m)
    spin_offs = [s for s in S["company"].get("splits", []) if s.get("kind") == "posible_escision"]
    for sig in [out["beta"], *out["max_drawdown"].values()]:
        notes = [f"posible escisión registrada como split el {s['date']} (ratio {s['ratio']}): el cierre ajustado "
                 f"puede no reflejarla; se revisa en la fase 5"
                 for s in spin_offs if sig["status"] == "ok" and s["date"] > sig["window_start"]]
        if notes:
            sig["notes"] = notes
    return out
