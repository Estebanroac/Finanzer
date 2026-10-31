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
    df = pd.DataFrame({"close": close.to_numpy(), "quote": pd.to_numeric(raw["Close"], errors="coerce").to_numpy(),
                       "volume": pd.to_numeric(raw["Volume"], errors="coerce").to_numpy()},
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
    # la distancia al máximo es la de la cotización (cierre sin ajustar, revisión F5 hallazgo 5)
    q = df["quote"].dropna().to_numpy(dtype=float)
    assert mc["series_drawdown"]["from_high"] == pytest.approx(q[-1] / q.max() - 1, abs=TOL)
    # volumen: z de la media de 5 sesiones frente a las 90 anteriores
    rec, base = v[-5:], v[-95:-5]
    assert S["abnormal_volume"]["value"] == pytest.approx((rec.mean() - base.mean()) / base.std(ddof=1), abs=1e-6)
    # fuerza relativa frente al ETF de su sector, 1 año como la tabla de rentabilidades (F8 · P3): días naturales
    # desde la última sesión de la empresa; cada serie, de su primer cierre en o después del inicio al último
    etf = mc["sector_etf"]
    e = _series(store, etf, until, own_fixture=False)["close"].dropna()
    co = df["close"].dropna()
    end = co.index[-1]
    start = end - pd.Timedelta(days=365)

    def _ret(s):
        s = s[s.index <= end]
        return float(s.iloc[-1] / s[s.index >= start].iloc[0] - 1)
    assert S["relative_strength"]["value"] == pytest.approx(_ret(co) - _ret(e), abs=TOL)


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
    raw = [{"datetime": 1760000000 + i * 3600, "headline": f"AAPL titular {i}", "related": "AAPL" if i % 2 else "MSFT",
            "source": "X", "url": f"https://x/{i}"} for i in range(12)]
    monkeypatch.setattr(fh, "company_news", lambda s, a, b: raw)
    n = mc.news("AAPL")
    # rediseño E2a: news() devuelve hasta max(news_max, news_max_v2) (6); la web actual sigue con news_max (display)
    assert [x["headline"] for x in n["items"]] == ["AAPL titular 11", "AAPL titular 9", "AAPL titular 7",
                                                   "AAPL titular 5", "AAPL titular 3", "AAPL titular 1"]
    assert n["total"] == 6
    monkeypatch.setattr(fh, "company_news", lambda s, a, b: None)
    assert mc.news("AAPL")["items"] == [] and mc.news("AAPL")["reason"]


def test_low_volume_is_not_called_habitual():
    import market_context as mc
    ctx = {"signals": {"abnormal_volume": {"value": -3.1, "status": "ok"}}}
    txt = " ".join(r.get("text", "") for r in mc.readings(ctx))
    assert "muy por debajo de lo habitual" in txt and "rango habitual" not in txt


def test_behavioral_readings_are_not_forecasts():
    """Revisión F5, hallazgo 6: describen un sesgo estudiado, sin anticipar el precio."""
    import inspect
    import market_context as mc
    src = inspect.getsource(mc.behavioral)
    for phrase in ("tiende a revertir", "tiende a infravalorar", "incorporarlas tarde"):
        assert phrase not in src


def test_today_is_the_new_york_date():
    """V6 (B12): "hoy" de los próximos resultados es la fecha de Nueva York: a las 02:00 UTC aún es ayer allí."""
    import datetime as dt
    import market_context as mc
    utc = dt.timezone.utc
    assert mc.ny_today(now=dt.datetime(2026, 10, 19, 2, 0, tzinfo=utc)) == dt.date(2026, 10, 18)
    assert mc.ny_today(now=dt.datetime(2026, 10, 19, 15, 0, tzinfo=utc)) == dt.date(2026, 10, 19)
    assert mc.TODAY is mc.ny_today                       # en producción; el replay pone el día de su captura


def test_build_takes_today_from_the_injected_clock(monkeypatch):
    """B12: build pide "hoy" a TODAY (con la serie de la empresa, para el replay), no al reloj del servidor."""
    import market_context as mc
    seen = []

    class Stop(Exception):
        pass

    def clock(frame):
        seen.append(frame)
        raise Stop()
    monkeypatch.setattr(mc, "TODAY", clock)
    frame = object()
    with pytest.raises(Stop):
        mc.build("AAPL", {"symbol": "AAPL", "frame": frame}, None, None, {"profile": {}})
    assert seen == [frame]


def test_news_of_a_class_share_ask_finnhub_with_its_dot_symbol(monkeypatch):
    """V4b (auditoría de datos): Finnhub escribe las acciones de clase con punto (BRK.B) y Yahoo con guion (BRK-B); con
    el guion no devuelve ningún titular. El análisis pide y filtra los titulares con el símbolo de Finnhub."""
    import finnhub_fallback as fh
    import market_context as mc
    assert fh.provider_symbol("BRK-B") == "BRK.B" and fh.provider_symbol("brk-b") == "BRK.B"
    assert fh.provider_symbol("AAPL") == "AAPL" and fh.provider_symbol("MC.PA") == "MC.PA"
    assert fh.provider_symbol("BF-B") == "BF.B" and fh.provider_symbol("7203-T") == "7203-T"
    asked = []
    monkeypatch.setattr(fh, "is_enabled", lambda: True)
    monkeypatch.setattr(fh, "_get", lambda path, params: asked.append(params["symbol"]) or [
        {"datetime": 1760000000, "headline": "Berkshire Hathaway buys more shares", "related": "BRK.B",
         "source": "X", "url": "https://x/1"}])
    fh._cache.clear()
    n = mc.news("BRK-B", "Berkshire Hathaway Inc.")
    assert asked == ["BRK.B"]
    assert [x["headline"] for x in n["items"]] == ["Berkshire Hathaway buys more shares"]


def test_news_text_with_mojibake_is_repaired():
    """V4b: un resumen de Finnhub traía «2027â\\x80\\x9328» (un «–» en UTF-8 leído como latin-1): el PDF no tiene glifo
    para los controles C1. Se recompone; si no se puede, se quitan los controles."""
    import market_context as mc
    assert mc.clean_external("cost cuts by 2027â\x80\x9328, dividend") == "cost cuts by 2027–28, dividend"
    assert mc.clean_external("caf\x93e ok") == "cafe ok"
    assert mc.clean_external("Déjà vu – fine") == "Déjà vu – fine"
    assert mc.clean_external(None) is None
