"""lib/market_signals.py: señales técnicas y beta propia (aisladas).

1. Contraste independiente en 5 tickers: cada señal se recalcula aquí con un método escrito aparte (numpy y
   bucles de Python, sin resample ni rolling de pandas y sin importar nada de market_signals).
2. Beta frente a la referencia de la fase 2a: (a) el método de la 2a, copiado tal cual de su rama, sobre la
   misma serie da la misma beta; (b) los números que la 2a dejó calculados (11:44, intradía) coinciden con la
   beta propia (cierre) dentro de la tolerancia que explica la diferencia de la última semana.
3. Casos límite: historia corta (IPO), serie con hueco, split sin ajustar, volumen cero.
"""
import datetime as _dt
import json
import math
import os

import numpy as np
import pandas as pd
import pytest

import cost_of_capital
import market_signals as ms
import price_fixtures as pf
from settings import cfg

needs_fixtures = pytest.mark.skipif(not pf.available(), reason="sin tests/fixtures/prices")
CONTRAST = ["AAPL", "JPM", "XOM", "NVO", "PLTR"]   # madura, banco, cíclica, ADR, crecimiento
TOL = 1e-9


def _arrays(symbol):
    o = pf.load_obj(symbol)
    dates = [_dt.date.fromisoformat(d) for d in o["dates"]]
    return dates, np.array(o["close"], dtype=float), np.array([np.nan if v is None else v for v in o["volume"]])


def _series(ticker):
    return pf.replay_series(ticker)


# ── 1. Contraste independiente ──

def ind_momentum(c):
    return c[-22] / c[-253] - 1


def ind_trend(c):
    sma_now = sum(c[-200:]) / 200
    sma_prev = sum(c[-221:-21]) / 200
    return c[-1] / sma_now - 1, sma_now / sma_prev - 1


def ind_vol(c):
    lr = np.log(c[-253:][1:]) - np.log(c[-253:][:-1])
    return float(np.std(lr, ddof=1) * math.sqrt(252))


def ind_drawdown(dates, c, years):
    n = 252 * years + 1
    w, d = c[-n:], dates[-n:]
    peak_i, worst, out = 0, 0.0, (None, None)
    for i in range(len(w)):
        if w[i] > w[peak_i]:
            peak_i = i
        dd = w[i] / w[peak_i] - 1
        if dd < worst:
            worst, out = dd, (d[peak_i], d[i])
    return worst, out


def ind_rel(dates, c, edates, e, window):
    common = sorted(set(dates) & set(edates))
    pc = dict(zip(dates, c))
    pe = dict(zip(edates, e))
    a, b = common[-1 - window], common[-1]
    return (pc[b] / pc[a] - 1) - (pe[b] / pe[a] - 1)


def ind_volume(v):
    v = v[~np.isnan(v)]
    recent, base = v[-5:], v[-95:-5]
    return (recent.mean() - base.mean()) / np.std(base, ddof=1)


def ind_range(c):
    w = c[-252:]
    return (c[-1] - w.min()) / (w.max() - w.min())


def _week_end(d):
    return d + _dt.timedelta(days=(4 - d.weekday()) % 7)   # viernes de su semana (sábado/domingo → siguiente)


def _weekly(dates, c):
    last = {}
    for d, p in zip(dates, c):
        last[_week_end(d)] = p   # en orden: queda el último cierre de cada semana
    weeks = sorted(last)
    return {weeks[i]: last[weeks[i]] / last[weeks[i - 1]] - 1 for i in range(1, len(weeks))}


def ind_beta(dates, c, mdates, m):
    r, rm = _weekly(dates, c), _weekly(mdates, m)
    weeks = sorted(set(r) & set(rm))[-104:]
    x = np.array([rm[w] for w in weeks])
    y = np.array([r[w] for w in weeks])
    slope = np.polyfit(x, y, 1)[0]
    return float(slope), float(np.corrcoef(x, y)[0, 1] ** 2), len(weeks)


@needs_fixtures
@pytest.mark.parametrize("ticker", CONTRAST)
def test_independent_contrast(ticker):
    meta = pf.metadata()["tickers"][ticker]
    dates, c, v = _arrays(ticker)
    edates, e, _ = _arrays(meta["sector_etf"])
    mdates, m, _ = _arrays(meta["market_symbol"])
    sig = ms.all_signals(_series(ticker))

    assert sig["momentum_12_1"]["value"] == pytest.approx(ind_momentum(c), rel=TOL, abs=TOL)
    above, slope = ind_trend(c)
    assert sig["trend"]["value"] == pytest.approx(above, rel=TOL, abs=TOL)
    assert sig["trend"]["slope"] == pytest.approx(slope, rel=TOL, abs=TOL)
    assert sig["realized_volatility"]["value"] == pytest.approx(ind_vol(c), rel=TOL)
    for y in (1, 3):
        worst, (peak, trough) = ind_drawdown(dates, c, y)
        got = sig["max_drawdown"][str(y)]
        assert got["value"] == pytest.approx(worst, rel=TOL, abs=TOL)
        assert (got["peak_date"], got["trough_date"]) == (peak.isoformat(), trough.isoformat())
    for w in (126, 252):
        assert sig["relative_strength"]["windows"][str(w)]["difference"] == pytest.approx(
            ind_rel(dates, c, edates, e, w), rel=TOL, abs=TOL)
    assert sig["abnormal_volume"]["value"] == pytest.approx(ind_volume(v), rel=TOL, abs=TOL)
    assert sig["range_52w_position"]["value"] == pytest.approx(ind_range(c), rel=TOL, abs=TOL)
    b, r2, n = ind_beta(dates, c, mdates, m)
    assert sig["beta"]["raw"] == pytest.approx(b, rel=TOL, abs=TOL)
    assert sig["beta"]["r2"] == pytest.approx(r2, rel=TOL, abs=TOL)
    assert sig["beta"]["observations"] == n == cfg("market.signals.beta.window_weeks")
    for name, s in sig.items():
        for one in (s.values() if name == "max_drawdown" else [s]):
            assert one["status"] == "ok", (name, one)


def test_independent_contrast_uses_the_configured_windows():
    """Las ventanas fijas del contraste independiente son las de config (si cambia la config, cambia el test)."""
    S = cfg("market.signals")
    assert (S["momentum"]["lookback_sessions"], S["momentum"]["skip_sessions"]) == (252, 21)
    assert (S["trend"]["sma_sessions"], S["trend"]["slope_sessions"]) == (200, 21)
    assert S["volatility"]["window_sessions"] == 252 and S["sessions_per_year"] == 252
    assert tuple(S["relative_strength"]["windows_sessions"]) == (126, 252)
    assert (S["volume"]["recent_sessions"], S["volume"]["baseline_sessions"]) == (5, 90)
    assert S["range52"]["window_sessions"] == 252 and tuple(S["drawdown"]["windows_years"]) == (1, 3)
    assert (S["beta"]["frequency"], S["beta"]["window_weeks"]) == ("W-FRI", 104)


# ── 2. Beta frente a la referencia de la fase 2a ──

def beta_2a_weekly_returns(series):
    """Copia literal de tests/beta_ref.py, rama fiabilidad/f2a-medir, commit f8f13df."""
    s = series.dropna().resample("W-FRI").last().dropna()
    return s.pct_change().dropna()


def beta_2a(r, rm):
    """Copia literal de tests/beta_ref.py, rama fiabilidad/f2a-medir, commit f8f13df."""
    df = pd.concat([r, rm], axis=1, join="inner").dropna().tail(104)
    if len(df) < 52:
        return None, len(df)
    cov = df.iloc[:, 0].cov(df.iloc[:, 1])
    return cov / df.iloc[:, 1].var(), len(df)


def _ref_2a():
    with open(os.path.join(pf.PRICES_DIR, "ref_2a_beta.json"), encoding="utf-8") as fh:
        return json.load(fh)


@needs_fixtures
@pytest.mark.parametrize("ticker", sorted(_ref_2a()["betas"]) if pf.available() else [])
def test_beta_equals_the_2a_method_on_the_same_series(ticker):
    s = _series(ticker)
    co, mk = s["series"]["company"]["frame"]["close"], s["series"]["market"]["frame"]["close"]
    ref, n = beta_2a(beta_2a_weekly_returns(co), beta_2a_weekly_returns(mk))
    got = ms.beta(co, mk, s["market_symbol"])
    assert got["raw"] == pytest.approx(ref, rel=1e-12, abs=1e-12) and got["observations"] == n


# La 2a calculó a las 11:44 con el mercado abierto: su última semana usa el precio intradía y la propia el
# cierre de las 16:30. Es 1 de 104 observaciones. Diferencia medida en los 31: mediana 0.0037, máx. 0.0113
# (SNOW) (F5PREP_MUESTRA.md §2); la tolerancia deja menos del doble de margen.
TOL_VS_2A_NUMBERS = 0.02


@needs_fixtures
@pytest.mark.parametrize("ticker", sorted(_ref_2a()["betas"]) if pf.available() else [])
def test_beta_matches_the_numbers_left_by_the_2a(ticker):
    ref = _ref_2a()["betas"][ticker]
    got = ms.all_signals(_series(ticker))["beta"]
    assert got["observations"] == ref["semanas"]
    assert abs(got["raw"] - ref["beta_ref"]) <= TOL_VS_2A_NUMBERS, (got["raw"], ref["beta_ref"])


def test_blume_adjustment_is_the_one_of_cost_of_capital():
    rng = np.random.default_rng(7)
    idx = pd.bdate_range("2023-01-02", periods=700)
    m = pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.01, 700))), index=idx)
    c = pd.Series(50 * np.exp(np.cumsum(1.3 * np.log(m / m.shift(1)).fillna(0) + rng.normal(0, 0.005, 700))),
                  index=idx)
    b = ms.beta(c, m, "^GSPC")
    assert b["status"] == "ok" and b["adjusted"] == pytest.approx(cost_of_capital.adjusted_beta(b["raw"]))
    assert b["raw"] == pytest.approx(1.3, abs=0.1) and b["params"]["market_symbol"] == "^GSPC"


# ── 3. Casos límite ──

def _synthetic(n, seed=3):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2021-01-04", periods=n)
    close = pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.01, n))), index=idx)
    volume = pd.Series(rng.uniform(0.5, 1.5, n) * 1e6, index=idx)
    return close, volume


@pytest.mark.parametrize("n,expected", [
    (150, {"momentum_12_1", "trend", "realized_volatility", "range_52w_position", "beta", "dd1", "dd3"}),
    (240, {"momentum_12_1", "realized_volatility", "range_52w_position", "beta", "dd1", "dd3"}),
    (400, {"dd3"}),
])
def test_short_history_ipo_is_historia_insuficiente(n, expected):
    close, volume = _synthetic(n)
    market, _ = _synthetic(n, seed=4)
    got = {
        "momentum_12_1": ms.momentum_12_1(close), "trend": ms.trend(close),
        "realized_volatility": ms.realized_volatility(close), "range_52w_position": ms.range_52w_position(close),
        "beta": ms.beta(close, market), "dd1": ms.max_drawdown(close, 1), "dd3": ms.max_drawdown(close, 3),
        "abnormal_volume": ms.abnormal_volume(volume),
    }
    short = {k for k, v in got.items() if v["status"] == "historia_insuficiente"}
    assert short == expected
    for k in short:
        assert got[k]["value"] is None and "hacen falta" in got[k]["reason"]
    for k in set(got) - short:
        assert got[k]["status"] == "ok" and got[k]["value"] is not None


def test_relative_strength_short_common_history():
    close, _ = _synthetic(600)
    etf, _ = _synthetic(200, seed=5)
    r = ms.relative_strength(close, etf)
    assert r["status"] == "historia_insuficiente"
    assert r["windows"]["126"]["status"] == "ok" and r["windows"]["252"]["status"] == "historia_insuficiente"


def test_missing_inputs_are_sin_dato():
    close, volume = _synthetic(600)
    assert ms.relative_strength(close, None)["status"] == "sin_dato"
    assert ms.beta(close, None)["status"] == "sin_dato"
    assert ms.momentum_12_1(None)["status"] == "sin_dato"
    assert ms.abnormal_volume(pd.Series([np.nan] * 200, index=close.index[:200]))["status"] == "sin_dato"


def test_zero_volume():
    close, volume = _synthetic(300)
    zero = volume * 0
    r = ms.abnormal_volume(zero)
    assert r["status"] == "sin_dato" and "constante o cero" in r["reason"]
    v = volume.copy()
    v.iloc[-5:] = 0.0
    r = ms.abnormal_volume(v)
    assert r["status"] == "ok" and r["value"] < 0 and r["zero_volume_sessions"] == 5


def test_flat_range_is_sin_dato():
    close = pd.Series(10.0, index=pd.bdate_range("2024-01-01", periods=300))
    assert ms.range_52w_position(close)["status"] == "sin_dato"


def test_range_includes_todays_price():
    close, _ = _synthetic(300)
    close.iloc[-1] = close.max() * 1.1
    r = ms.range_52w_position(close)
    assert r["value"] == 1.0 and r["high_date"] == close.index[-1].strftime("%Y-%m-%d")


def _ps(frames, statuses=None, reasons=None):
    statuses = statuses or {}
    return {"series": {role: {"symbol": role.upper(), "frame": f, "status": statuses.get(role, "ok"),
                              "reasons": (reasons or {}).get(role, [])}
                       for role, f in frames.items()}}


def test_series_with_a_gap_or_an_unadjusted_split_feeds_no_signal():
    close, volume = _synthetic(900)
    f = pd.DataFrame({"close": close, "volume": volume})
    for status, why in (("sospechosa", "1 sesiones sin cotización frente al índice: 2023-05-04"),
                        ("sospechosa", "salto de un día por encima del umbral (¿split sin ajustar?): 2023-05-04"),
                        ("sin_dato", "sin dato tras 3 intentos")):
        sig = ms.all_signals(_ps({"company": f, "market": f, "sector": f}, {"company": status}, {"company": [why]}))
        flat = [sig[k] for k in sig if k != "max_drawdown"] + list(sig["max_drawdown"].values())
        assert all(s["status"] == "sin_dato" and why in s["reason"] for s in flat)


def test_unadjusted_split_would_distort_signals_if_not_blocked():
    """Por qué se bloquea: un 2:1 sin ajustar convierte el drawdown de 1 año en ~−50%."""
    close, _ = _synthetic(600)
    broken = close.copy()
    broken.iloc[-100:] = broken.iloc[-100:] / 2
    assert ms.max_drawdown(broken, 1)["value"] < -0.45 < ms.max_drawdown(close, 1)["value"]


def test_market_or_sector_sospechosa_only_blocks_their_signals():
    close, volume = _synthetic(900)
    f = pd.DataFrame({"close": close, "volume": volume})
    sig = ms.all_signals(_ps({"company": f, "market": f, "sector": f}, {"sector": "sospechosa"},
                             {"sector": ["hueco"]}))
    assert sig["relative_strength"]["status"] == "sin_dato" and sig["beta"]["status"] == "ok"
    assert sig["momentum_12_1"]["status"] == "ok"


def test_every_signal_reports_status_value_params_and_as_of():
    close, volume = _synthetic(900)
    f = pd.DataFrame({"close": close, "volume": volume})
    sig = ms.all_signals(_ps({"company": f, "market": f, "sector": f}))
    flat = [sig[k] for k in sig if k != "max_drawdown"] + list(sig["max_drawdown"].values())
    assert len(flat) == 9
    for s in flat:
        assert {"status", "value", "params", "as_of"} <= set(s) and s["params"]


def test_no_rsi_macd_or_chart_patterns():
    """PLAN §2.2: fuera RSI, MACD, figuras chartistas y Fibonacci."""
    names = {n.lower() for n in dir(ms)}
    assert not any(bad in n for n in names for bad in ("rsi", "macd", "fibonacci", "pattern", "head_and"))


def test_modules_are_isolated_from_the_engine():
    """Nada del motor, la web ni el PDF importa price_series ni market_signals (fase 5: contexto aparte)."""
    backend = os.path.dirname(pf.TESTS_DIR)
    offenders = []
    for folder in (backend, os.path.join(backend, "lib")):
        for name in os.listdir(folder):
            if not name.endswith(".py") or name in ("price_series.py", "market_signals.py"):
                continue
            with open(os.path.join(folder, name), encoding="utf-8") as fh:
                text = fh.read()
            if "price_series" in text or "market_signals" in text:
                offenders.append(name)
    assert offenders == []
