"""
Fase 5: el contexto de mercado del análisis frente a un cálculo de referencia INDEPENDIENTE (pandas a mano, sin
lib/market_signals ni lib/market_context) sobre la misma serie de los fixtures (PLAN §4, fase 5: "terminado cuando el
panel muestra las señales correctas contra un cálculo de referencia independiente"). Y D5: nunca puntúa.
"""
import math

import numpy as np
import pandas as pd
import pytest

import fixture_backend as fb
import history_fixtures as hf

TICKERS = ("AAPL", "JPM", "XOM", "NVO", "PLTR", "O", "NFLX")
TOL = 1e-9


def _series(store, sym, until, own_fixture=True):
    own = None
    if own_fixture:
        store.load(sym)
        own = (store.yf.get(sym) or {}).get("price_history")
    raw = hf.obj_to_history(own) if own else hf.load_frame(sym, until)
    adj = pd.to_numeric(raw["Adj Close"], errors="coerce")
    close = adj.where(adj.notna(), pd.to_numeric(raw["Close"], errors="coerce"))
    df = pd.DataFrame({"close": close.to_numpy(), "volume": pd.to_numeric(raw["Volume"], errors="coerce").to_numpy()},
                      index=pd.DatetimeIndex(raw.index).tz_localize(None).normalize())
    return df[df["close"].notna()]


@pytest.fixture(scope="module")
def panel(outputs_by_env):
    return outputs_by_env("panel")


@pytest.mark.parametrize("sym", TICKERS)
def test_signals_match_an_independent_reference(panel, sym):
    a = panel[sym][0]
    mc = a["market_context"]
    S = mc["signals"]
    store = fb.FixtureStore(fb.fixtures_dir("panel"))
    store.load(sym)
    until = str((store.meta.get(sym) or {}).get("captured_at_local") or "")[:10] or None
    df = _series(store, sym, until)
    c, v = df["close"].to_numpy(dtype=float), df["volume"].to_numpy(dtype=float)
    # momentum 12-1: P(t−21) / P(t−252) − 1
    assert S["momentum_12_1"]["value"] == pytest.approx(c[-22] / c[-253] - 1, abs=TOL)
    # tendencia: P / media de 200 sesiones − 1
    assert S["trend"]["value"] == pytest.approx(c[-1] / c[-200:].mean() - 1, abs=TOL)
    # volatilidad: desviación típica muestral de 252 rentabilidades logarítmicas, anualizada
    r = np.log(c[-252:] / c[-253:-1])
    assert S["realized_volatility"]["value"] == pytest.approx(r.std(ddof=1) * math.sqrt(252), abs=TOL)
    # caída máxima de 1 año (253 cierres)
    w = c[-253:]
    assert S["max_drawdown"]["1"]["value"] == pytest.approx((w / np.maximum.accumulate(w) - 1).min(), abs=TOL)
    # caída de toda la serie y distancia de hoy al máximo
    assert mc["series_drawdown"]["value"] == pytest.approx((c / np.maximum.accumulate(c) - 1).min(), abs=TOL)
    assert mc["series_drawdown"]["from_high"] == pytest.approx(c[-1] / c.max() - 1, abs=TOL)
    # volumen: z de la media de 5 sesiones frente a las 90 anteriores
    rec, base = v[-5:], v[-95:-5]
    assert S["abnormal_volume"]["value"] == pytest.approx((rec.mean() - base.mean()) / base.std(ddof=1), abs=1e-6)
    # fuerza relativa frente al ETF de su sector, 12 meses de sesiones comunes
    etf = mc["sector_etf"]
    e = _series(store, etf, until, own_fixture=False)["close"]
    both = pd.concat([df["close"], e], axis=1, join="inner").dropna().to_numpy(dtype=float)
    ref = (both[-1, 0] / both[-253, 0] - 1) - (both[-1, 1] / both[-253, 1] - 1)
    assert S["relative_strength"]["value"] == pytest.approx(ref, abs=TOL)


def test_context_never_changes_the_scores(panel):
    """D5: sin el contexto (lo que se mostraría si faltara la serie), calidad, precio y confianza son los mismos:
    el contexto se calcula después y nada del motor lo lee (tests/test_market_signals.py lo comprueba en el código)."""
    for sym, (a, _pdf) in panel.items():
        if not a.get("market_context"):
            continue
        for k in ("quality", "price_attractiveness", "confidence"):
            assert "market_context" not in str(a.get(k)), (sym, k)


def test_news_are_the_company_own_most_recent_headlines(monkeypatch):
    import finnhub_fallback as fh
    import market_context as mc
    monkeypatch.setattr(fh, "is_enabled", lambda: True)
    raw = [{"datetime": 1760000000 + i * 3600, "headline": f"titular {i}", "related": "AAPL" if i % 2 else "MSFT",
            "source": "X", "url": f"https://x/{i}"} for i in range(12)]
    monkeypatch.setattr(fh, "company_news", lambda s, a, b: raw)
    n = mc.news("AAPL")
    assert [x["headline"] for x in n["items"]] == ["titular 11", "titular 9", "titular 7", "titular 5", "titular 3"]
    assert n["total"] == 6
    monkeypatch.setattr(fh, "company_news", lambda s, a, b: None)
    assert mc.news("AAPL")["items"] == [] and mc.news("AAPL")["reason"]
