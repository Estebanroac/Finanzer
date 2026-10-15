"""lib/price_series.py: ingesta de la serie diaria (aislada), estados explícitos y replay sin red."""
import datetime as _dt

import numpy as np
import pandas as pd
import pytest

import price_fixtures as pf
import price_series as ps
from settings import cfg

needs_fixtures = pytest.mark.skipif(not pf.available(), reason="sin tests/fixtures/prices")


def _yf_frame(n=300, seed=1, start="2025-01-02", vol_level=1e6):
    """Serie sintética con la forma de yfinance `history` (Close, Volume, índice con zona de NY)."""
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range(start, periods=n, tz=pf.TZ, name="Date")
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
    vol = rng.uniform(0.5, 1.5, n) * vol_level
    return pd.DataFrame({"Close": close, "Volume": vol}, index=idx)


def _fetcher(frames):
    calls = []

    def fetch(symbol, period, interval):
        calls.append(symbol)
        f = frames.get(symbol)
        if isinstance(f, Exception):
            raise f
        if callable(f):
            return f()
        return f
    fetch.calls = calls
    return fetch


def _three(company=None, market=None, sector=None):
    base = _yf_frame()
    return {"AAA": base if company is None else company, "^GSPC": _yf_frame(seed=2) if market is None else market,
            "XLK": _yf_frame(seed=3) if sector is None else sector, "SPY": _yf_frame(seed=4)}


def test_normalize_frame_drops_timezone_and_nan_close():
    raw = _yf_frame(n=5)
    raw.iloc[2, 0] = float("nan")
    f = ps.normalize_frame(raw)
    assert list(f.columns) == ["close", "volume", "split"] and (f["split"] == 0).all()
    assert f.index.tz is None and len(f) == 4
    assert f.index[0] == pd.Timestamp("2025-01-02")
    assert ps.normalize_frame(pd.DataFrame()) is None and ps.normalize_frame(None) is None


def test_all_ok_and_sector_etf_from_sector_profiles():
    r = ps.fetch_price_series("AAA", "Technology", fetcher=_fetcher(_three()), sleep=lambda s: None)
    assert r["status"] == "ok" and r["reasons"] == []
    assert r["sector_etf"] == "XLK" and r["market_symbol"] == "^GSPC" and r["market_fallback"] is False
    assert {k: s["status"] for k, s in r["series"].items()} == {"company": "ok", "market": "ok", "sector": "ok"}
    assert all(s["latency_s"] >= 0 for s in r["series"].values()) and r["latency_s"] >= 0
    assert r["params"]["period"] == cfg("market.price_series.period")


def test_unknown_sector_uses_spy_as_etf():
    r = ps.fetch_price_series("AAA", None, fetcher=_fetcher(_three()), sleep=lambda s: None)
    assert r["sector_etf"] == "SPY" and r["status"] == "ok"


def test_retries_are_limited_with_growing_pause_then_sin_dato():
    pauses = []
    frames = _three(company=RuntimeError("HTTP 429"))
    r = ps.fetch_price_series("AAA", "Technology", fetcher=_fetcher(frames), sleep=pauses.append)
    P = cfg("market.price_series")
    co = r["series"]["company"]
    assert co["status"] == "sin_dato" and co["frame"] is None and co["attempts"] == P["max_attempts"]
    assert "HTTP 429" in co["reasons"][0] and f"{P['max_attempts']} intentos" in co["reasons"][0]
    assert pauses == [P["retry_pause_s"] * k for k in range(1, P["max_attempts"])]
    assert r["status"] == "sin_dato" and any("company (AAA)" in x for x in r["reasons"])


def test_retry_recovers_after_a_transient_failure():
    state = {"n": 0}

    def flaky():
        state["n"] += 1
        if state["n"] == 1:
            raise ConnectionError("reset")
        return _yf_frame()
    r = ps.fetch_price_series("AAA", "Technology", fetcher=_fetcher(_three(company=flaky)), sleep=lambda s: None)
    assert r["series"]["company"]["status"] == "ok" and r["series"]["company"]["attempts"] == 2


def test_empty_response_is_sin_dato_not_a_partial_series():
    r = ps.fetch_price_series("AAA", "Technology", fetcher=_fetcher(_three(company=pd.DataFrame())),
                              sleep=lambda s: None)
    assert r["series"]["company"]["status"] == "sin_dato"
    assert "respuesta vacía" in r["series"]["company"]["reasons"][0]


def test_index_failure_falls_back_to_spy_and_declares_it():
    frames = _three(market=RuntimeError("404"))
    r = ps.fetch_price_series("AAA", "Technology", fetcher=_fetcher(frames), sleep=lambda s: None)
    assert r["market_symbol"] == "SPY" and r["market_fallback"] is True
    assert r["series"]["market"]["status"] == "ok"
    assert "^GSPC sin dato" in r["series"]["market"]["reasons"][0]
    assert any("se usa SPY" in x for x in r["reasons"])


def test_index_and_fallback_failing_is_sin_dato_with_both_reasons():
    frames = _three(market=RuntimeError("404"))
    frames["SPY"] = RuntimeError("503")
    r = ps.fetch_price_series("AAA", "Technology", fetcher=_fetcher(frames), sleep=lambda s: None)
    m = r["series"]["market"]
    assert m["status"] == "sin_dato" and "^GSPC" in m["reasons"][0] and "SPY" in m["reasons"][0]
    assert r["status"] == "sin_dato"


def test_gap_against_the_index_calendar_is_sospechosa_with_the_date():
    co = _yf_frame().drop(index=_yf_frame().index[100])
    r = ps.fetch_price_series("AAA", "Technology", fetcher=_fetcher(_three(company=co)), sleep=lambda s: None)
    c = r["series"]["company"]
    missing = _yf_frame().index[100].strftime("%Y-%m-%d")
    assert c["status"] == "sospechosa" and c["missing_days"] == [missing] and missing in c["reasons"][0]


def test_stale_series_ending_before_the_index_is_sospechosa():
    co = _yf_frame().iloc[:-1]
    r = ps.fetch_price_series("AAA", "Technology", fetcher=_fetcher(_three(company=co)), sleep=lambda s: None)
    assert r["series"]["company"]["status"] == "sospechosa"
    assert r["series"]["company"]["missing_days"] == [_yf_frame().index[-1].strftime("%Y-%m-%d")]


def test_short_history_ipo_is_not_a_gap():
    co = _yf_frame().iloc[200:]
    r = ps.fetch_price_series("AAA", "Technology", fetcher=_fetcher(_three(company=co)), sleep=lambda s: None)
    assert r["series"]["company"]["status"] == "ok" and r["series"]["company"]["rows"] == 100


@pytest.mark.parametrize("factor", [2.0, 0.5, 10.0])
def test_unadjusted_split_injected_is_detected_with_its_date(factor):
    co = _yf_frame()
    split_day = co.index[150]
    co.loc[co.index < split_day, "Close"] *= factor
    r = ps.fetch_price_series("AAA", "Technology", fetcher=_fetcher(_three(company=co)), sleep=lambda s: None)
    c = r["series"]["company"]
    assert c["status"] == "sospechosa" and [j["date"] for j in c["jumps"]] == [split_day.strftime("%Y-%m-%d")]
    assert "split" in c["reasons"][0]


def test_jump_threshold_is_symmetric_and_from_config():
    thr = cfg("market.price_series.jump_threshold")
    idx = pd.date_range("2025-01-02", periods=3, freq="B")
    below = pd.DataFrame({"close": [100.0, 100 * (1 + thr) * 0.999, 100.0], "volume": [1.0, 1.0, 1.0]}, index=idx)
    assert ps.check_series(below)["jumps"] == []
    above = pd.DataFrame({"close": [100.0, 100 / (1 + thr) / 1.001, 100.0], "volume": [1.0, 1.0, 1.0]}, index=idx)
    assert len(ps.check_series(above)["jumps"]) == 2


def test_zero_volume_days_are_a_warning_not_a_state_change():
    co = _yf_frame()
    co.iloc[[10, 11], 1] = 0.0
    r = ps.fetch_price_series("AAA", "Technology", fetcher=_fetcher(_three(company=co)), sleep=lambda s: None)
    c = r["series"]["company"]
    assert c["status"] == "ok" and len(c["zero_volume_days"]) == 2


def test_shared_symbol_is_downloaded_once_per_call():
    f = _fetcher(_three())
    ps.fetch_price_series("SPY", None, fetcher=f, sleep=lambda s: None)
    assert f.calls.count("SPY") == 1


# ── Fixtures de precios (36 tickers): replay sin red ──

@needs_fixtures
def test_fixture_metadata_declares_capture_source_and_versions():
    m = pf.metadata()
    assert set(m["tickers"]) == set(pf.panel_tickers()) and len(m["tickers"]) == 36
    assert m["versions"]["yfinance"] and "auto_adjust=True" in m["source"]
    assert (m["period"], m["interval"]) == (cfg("market.price_series.period"), cfg("market.price_series.interval"))
    ny = _dt.datetime.fromisoformat(m["captured_at_new_york"])
    assert ny.hour >= 16, "la captura debe ser posterior al cierre de Nueva York"
    assert m["shared_series_mismatches"] == []
    assert set(m["latency_s"]) == set(m["tickers"])


@needs_fixtures
@pytest.mark.parametrize("ticker", pf.panel_tickers())
def test_replay_without_network_reproduces_every_ticker(ticker):
    m = pf.metadata()
    r = pf.replay_series(ticker)
    assert r["status"] == m["tickers"][ticker]["status"] and r["reasons"] == m["tickers"][ticker]["reasons"]
    assert r["sector_etf"] == m["tickers"][ticker]["sector_etf"]
    last = {s["last_date"] for s in r["series"].values()}
    assert len(last) == 1, f"las tres series deben acabar en la misma sesión: {last}"


@needs_fixtures
def test_replay_blocks_the_network():
    import socket
    with pf.no_network():
        with pytest.raises(RuntimeError, match="Red bloqueada"):
            socket.create_connection(("query1.finance.yahoo.com", 443))


@needs_fixtures
def test_replay_fails_loudly_on_a_symbol_that_was_not_recorded():
    with pf.no_network():
        r = ps.fetch_price_series("NOPE", "Technology", fetcher=pf.replay_fetcher(), sleep=lambda s: None)
    assert r["series"]["company"]["status"] == "sin_dato" and "no grabado" in r["series"]["company"]["reasons"][0]


def test_split_events_declared_by_yahoo_are_listed_as_information():
    co = _yf_frame()
    co["Stock Splits"] = 0.0
    co.iloc[120, 2] = 0.888          # escisión registrada como split (UL, Magnum, 2025-12-09)
    r = ps.fetch_price_series("AAA", "Technology", fetcher=_fetcher(_three(company=co)), sleep=lambda s: None)
    c = r["series"]["company"]
    assert c["status"] == "ok" and c["splits"] == [{"date": co.index[120].strftime("%Y-%m-%d"), "ratio": 0.888}]


@needs_fixtures
def test_real_crash_is_not_flagged_as_a_split():
    """NFLX cayó un 35.1% el 2022-04-20 (resultados): es real; con el umbral simétrico de 0.5 se marcaba."""
    c = pf.replay_series("NFLX")["series"]["company"]
    assert c["status"] == "ok" and c["jumps"] == []
    assert {"date": "2025-11-17", "ratio": 10.0} in c["splits"]   # el 10:1 viene ajustado


@needs_fixtures
def test_ul_spin_off_is_listed_as_a_split_event():
    c = pf.replay_series("UL")["series"]["company"]
    assert c["status"] == "ok" and any(s["date"] == "2025-12-09" for s in c["splits"])
