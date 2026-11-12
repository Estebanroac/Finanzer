"""Rediseño E2b (Task 4): tendencias del día sobre el universo (lib/trending.py). Sin red: DataFrames con la forma real
de yf.download(group_by="ticker") y la descarga capturada (tests/fixtures/trending/batch.json)."""
import datetime as dt
import threading
import time

import numpy as np
import pandas as pd
import pytest

import analysis_queue as AQ
import trending
import universe
from settings import cfg

# Espera máxima de los cálculos en su hilo: holgada para la suite completa en paralelo con otros hilos (una pasada
# de 4.750 tests superó una vez los 5 s de antes).
SETTLE_S = 15
DAYS = pd.to_datetime(["2026-10-12", "2026-10-13", "2026-10-14", "2026-10-15", "2026-10-16"])


def frame(series):
    """{símbolo: [(cierre, volumen) por día o None]} -> DataFrame con columnas (ticker, campo)."""
    cols, data = [], {}
    for sym, rows in series.items():
        for field in ("Open", "High", "Low", "Close", "Adj Close", "Volume"):
            cols.append((sym, field))
            vals = []
            for r in rows:
                if r is None:
                    vals.append(np.nan)
                else:
                    vals.append(r[1] if field == "Volume" else r[0])
            data[(sym, field)] = vals
    df = pd.DataFrame(data, index=DAYS[:len(next(iter(series.values())))])
    df.columns = pd.MultiIndex.from_tuples(cols, names=["Ticker", "Price"])
    df.index.name = "Date"
    return df


SERIES = {
    "AAA": [(10, 1e6), (10, 1e6), (10, 1e6), (100, 1e6), (110, 2e6)],       # +10 %, 220 M$
    "BBB": [(50, 1e6), (50, 1e6), (50, 1e6), (50, 1e6), (40, 9e6)],         # −20 %, 360 M$
    "CCC": [(20, 1e6), (20, 1e6), (20, 1e6), (20, 1e6), (21, 1e6)],         # +5 %, 21 M$
    "DDD": [(0.5, 1e6)] * 4 + [(0.9, 1e9)],                                  # precio < min_price: fuera
    "EEE": [(30, 1e6), (30, 1e6), (30, 1e6), (30, 1e6), None],              # sin la última sesión: fuera
    "FFF": [None, None, None, None, (5, 1e6)],                               # una sola sesión: fuera
}


def _no_engine(sym):
    raise RuntimeError("sin motor en el test")


@pytest.fixture
def fresh(monkeypatch):
    # Rediseño E4: las tarjetas se precalientan en la cola compartida; main conecta el motor real (red) al importarse:
    # se importa antes y se sustituye.
    import main  # noqa: F401
    monkeypatch.setattr(AQ, "ANALYZE", _no_engine)
    AQ.reset()
    trending.reset()
    yield monkeypatch
    trending.reset()
    AQ.reset()


def fetcher(df, calls=None, delay=0.0):
    def fetch(symbols):
        if calls is not None:
            calls.append(list(symbols))
        time.sleep(delay)
        cols = [c for c in df.columns if c[0] in set(symbols)]
        return df[cols]
    return fetch


def test_compute_lists_order_and_exclusions(fresh):
    syms = list(SERIES)
    fresh.setattr(trending, "_universe_symbols", lambda: syms)
    out = trending.compute(fetcher(frame(SERIES)))
    assert out["session"] == "2026-10-16" and out["count"] == 3
    L = out["lists"]["1D"]
    assert [x["symbol"] for x in L["most_traded"]] == ["BBB", "AAA", "CCC"]
    # P8b: «Suben más» solo con los que suben y «Bajan más» solo con los que bajan; si no llegan, se dice
    assert [x["symbol"] for x in L["gainers"]] == ["AAA", "CCC"]
    assert [x["symbol"] for x in L["losers"]] == ["BBB"]
    assert out["list_notes"]["1D"] == {"gainers": "solo 2 valores del universo suben en 1 día",
                                       "losers": "solo 1 valor del universo baja en 1 día"}
    aaa = L["gainers"][0]
    assert aaa["price"] == 110 and aaa["change_pct"] == pytest.approx(0.10) and aaa["dollar_volume"] == 110 * 2e6
    assert set(aaa) == {"symbol", "name", "price", "change_pct", "dollar_volume", "sector"}


def test_compute_batches_and_top_n(fresh):
    series = {f"S{i:02d}": [(10, 1e6)] * 4 + [(10 + i, 1e6 * (i + 1))] for i in range(35)}
    fresh.setattr(trending, "_universe_symbols", lambda: list(series))
    fresh.setitem(trending._limits, "batch_size", 10)
    calls = []
    out = trending.compute(fetcher(frame(series), calls))
    assert [len(c) for c in calls] == [10, 10, 10, 5]
    assert len(out["lists"]["1D"]["gainers"]) == cfg("market.trending.top_n")
    assert out["lists"]["1D"]["gainers"][0]["symbol"] == "S34" and out["lists"]["1D"]["most_traded"][0]["symbol"] == "S34"


def test_compute_cuts_partial_session_of_today(fresh):
    """En horario de mercado Yahoo trae la fila parcial de hoy: se recorta a la última sesión cerrada."""
    fresh.setattr(trending, "_universe_symbols", lambda: ["AAA", "BBB"])
    out = trending.compute(fetcher(frame({k: SERIES[k] for k in ("AAA", "BBB")})), session="2026-10-15")
    assert out["session"] == "2026-10-15"
    assert out["lists"]["1D"]["gainers"][0]["symbol"] == "AAA" and out["lists"]["1D"]["gainers"][0]["change_pct"] == \
        pytest.approx(9.0)


def test_last_closed_session():
    ny = trending.NY
    f = trending.last_closed_session
    assert f(dt.datetime(2026, 10, 16, 16, 31, tzinfo=ny)) == "2026-10-16"      # viernes tras el cierre + 30 min
    assert f(dt.datetime(2026, 10, 16, 16, 10, tzinfo=ny)) == "2026-10-15"      # aún no: el jueves
    assert f(dt.datetime(2026, 10, 18, 12, 0, tzinfo=ny)) == "2026-10-16"       # domingo: el viernes
    assert f(dt.datetime(2026, 10, 19, 9, 0, tzinfo=ny)) == "2026-10-16"        # lunes antes de abrir: el viernes


def test_get_is_lazy_single_flight_and_refreshes(fresh):
    fresh.setattr(trending, "_universe_symbols", lambda: list(SERIES))
    calls = []
    fresh.setattr(trending, "FETCH_BATCH", fetcher(frame(SERIES), calls, delay=0.2))
    expected = {"s": "2026-10-16"}
    fresh.setattr(trending, "last_closed_session", lambda now=None: expected["s"])
    r = [trending.get() for _ in range(3)]
    assert [x["status"] for x in r] == ["calculando"] * 3 and r[0]["data"] is None
    t0 = time.monotonic()
    while trending.get()["status"] != "listo":
        assert time.monotonic() - t0 < SETTLE_S
        time.sleep(0.02)
    assert len(calls) == 1                                     # tres pedidos a la vez: un solo cálculo
    assert trending.get()["data"]["session"] == "2026-10-16" and len(calls) == 1
    expected["s"] = "2026-10-19"                               # nueva sesión cerrada: recalcula, sirve la anterior
    r = trending.get()
    assert r["status"] == "listo" and r["refreshing"] is True and r["data"]["session"] == "2026-10-16"
    t0 = time.monotonic()
    while len(calls) < 2 or trending.get()["refreshing"]:
        assert time.monotonic() - t0 < SETTLE_S
        time.sleep(0.02)
    # Yahoo no trae sesión nueva (festivo): la lista sigue con su fecha y no se repite la descarga en cada pedido
    assert trending.get()["data"]["session"] == "2026-10-16"
    trending.get()
    assert len(calls) == 2


def test_get_failure_is_sin_dato_with_reason(fresh):
    fresh.setattr(trending, "_universe_symbols", lambda: list(SERIES))

    def boom(symbols):
        raise RuntimeError("Yahoo caído")
    fresh.setattr(trending, "FETCH_BATCH", boom)
    trending.get()
    t0 = time.monotonic()
    while (r := trending.get())["status"] == "calculando":
        assert time.monotonic() - t0 < 5
        time.sleep(0.02)
    assert r["status"] == "sin_dato"
    assert r["reason"] == "no se pudieron calcular las tendencias: Yahoo no devolvió cotizaciones del universo (1 de 1 " \
        "lotes fallidos)"


def test_universe_note_when_stale(fresh):
    fresh.setattr(trending, "_universe_symbols", lambda: list(SERIES))
    fresh.setattr(universe, "meta", lambda: {"date": "2020-01-01", "source": "x", "count": 6})
    out = trending.compute(fetcher(frame(SERIES)))
    assert out["universe_date"] == "2020-01-01" and out["note"] == "universo del 2020-01-01"


def test_warm_at_boot_unless_disabled(fresh):
    """Portada rápida: el cálculo empieza al arrancar el servidor (también en local, no solo en Render). Los tests y
    las herramientas lo apagan con FINANZER_TRENDING_WARM=0 (conftest)."""
    started = []
    fresh.setattr(trending, "get", lambda: started.append(1))
    fresh.setattr(trending, "SNAPSHOT", None)
    fresh.setattr(trending, "WARM_SPARKLINES", False)
    assert trending.warm({"FINANZER_TRENDING_WARM": "0"}) is False and started == []
    assert trending.warm({}) is True and started == [1]
    assert trending.warm({"RENDER_EXTERNAL_URL": "https://x.onrender.com"}) is True and started == [1, 1]


# ─────────────────────────── fixture capturado y endpoint ───────────────────────────
def test_captured_batch_gives_three_lists(fresh):
    import capture_trending
    fetch, session = capture_trending.replay_fetcher()
    out = trending.compute(fetch, session=session)
    assert out["session"] == session and out["count"] >= 500
    for k in ("most_traded", "gainers", "losers"):
        assert len(out["lists"]["1D"][k]) == cfg("market.trending.top_n")
    assert out["lists"]["1D"]["gainers"][0]["change_pct"] > 0 > out["lists"]["1D"]["losers"][0]["change_pct"]


def test_endpoint(fresh):
    import asyncio
    import main
    fresh.setattr(trending, "_universe_symbols", lambda: list(SERIES))
    fresh.setattr(trending, "FETCH_BATCH", fetcher(frame(SERIES)))
    r = asyncio.run(main.trending_v2_endpoint())
    assert r["status"] in ("calculando", "listo")
    t0 = time.monotonic()
    while (r := asyncio.run(main.trending_v2_endpoint()))["status"] != "listo":
        assert time.monotonic() - t0 < 5
        time.sleep(0.02)
    assert r["data"]["lists"]["1D"]["most_traded"][0]["symbol"] == "BBB"


# ─────────────────────────── Rediseño E4: el motor en cada tarjeta ───────────────────────────
def _wait(pred, timeout=5.0):
    t0 = time.monotonic()
    while not (r := pred()):
        assert time.monotonic() - t0 < timeout
        time.sleep(0.02)
    return r


def _cards(r):
    return {x["symbol"]: x for k in ("most_traded", "gainers", "losers") for x in r["data"]["lists"]["1D"][k]}


def test_cards_carry_engine_and_prewarm_respects_the_daily_cap(fresh):
    fresh.setattr(trending, "_universe_symbols", lambda: list(SERIES))
    fresh.setattr(trending, "FETCH_BATCH", fetcher(frame(SERIES)))
    fresh.setitem(trending._limits, "prewarm_max", 2)
    gold = {"BBB": "AAPL", "AAA": "JPM"}
    calls = []

    def engine(sym):
        calls.append(sym)
        if sym not in gold:
            raise RuntimeError(f"{sym} sin datos")
        import json
        import os
        with open(os.path.join(os.path.dirname(__file__), "golden", "panel", gold[sym] + ".json"),
                  encoding="utf-8") as fh:
            return {**json.load(fh), "symbol": sym}
    fresh.setattr(AQ, "ANALYZE", engine)
    r = _wait(lambda: (x := trending.get())["status"] == "listo" and x)
    assert r["poll_s"] == cfg("market.trending.poll_s")
    # Orden de la portada: más negociadas (BBB, AAA, CCC); con un cupo de 2, solo BBB y AAA se analizan.
    r = _wait(lambda: all((_cards(x := trending.get())[s]["engine"] or {}).get("status") == "listo"
                          for s in ("BBB", "AAA")) and x)
    c = _cards(r)
    assert c["CCC"]["engine"] is None and sorted(calls) == ["AAA", "BBB"]
    assert set(c["BBB"]["engine"]) == {"status", "quality", "price_score", "as_of", "reason"} and c["BBB"]["engine"]["reason"] is None
    import json
    import os
    with open(os.path.join(os.path.dirname(__file__), "golden", "panel", "AAPL.json"), encoding="utf-8") as fh:
        g = json.load(fh)
    assert c["BBB"]["engine"]["quality"] == {"score": g["quality"]["score"], "level": g["quality"]["level"]}
    assert c["BBB"]["engine"]["price_score"] == {"score": g["price_attractiveness"]["score"],
                                                 "level": g["price_attractiveness"]["level"],
                                                 "reason": g["price_attractiveness"].get("reason")}
    # Al día siguiente hay cupo nuevo: CCC entra (y falla); la lista guardada no lleva `engine`.
    assert trending.prewarm(trending._state["data"], today="2099-01-01") == 1
    ccc = _wait(lambda: (e := _cards(trending.get())["CCC"]["engine"] or {}).get("status") == "fallo" and e)
    assert ccc["reason"] == "CCC sin datos" and ccc["quality"] is None
    assert "engine" not in trending._state["data"]["lists"]["1D"]["gainers"][0]


def test_prewarm_once_per_symbol_per_day_and_never_ahead_of_users(fresh):
    data = {"lists": {"1D": {"most_traded": [{"symbol": "A"}], "gainers": [{"symbol": "B"}], "losers": [{"symbol": "A"}]}}}
    fresh.setattr(AQ, "ANALYZE", _no_engine)
    assert trending.prewarm(data, today="2026-10-16") == 2
    _wait(lambda: all((AQ.peek(s) or {}).get("status") == "fallo" for s in ("A", "B")))
    fresh.setitem(AQ._limits, "fail_ttl_s", 0)                  # el fallo ya no se recuerda en la cola...
    assert trending.prewarm(data, today="2026-10-16") == 0     # ...pero el mismo día no se repite
    assert trending.prewarm(data, today="2026-10-17") == 2


def test_endpoint_reports_each_card_state_with_the_replay(fresh):
    """GET /api/v2/trending con la descarga capturada y el motor en replay: las tarjetas de las empresas del juego de
    fixtures pasan a `listo` con la calidad y el precio del golden; las demás, a `fallo`."""
    import asyncio
    import json
    import logging
    import os
    import capture_trending
    import fixture_backend as fb
    import main
    logging.disable(logging.CRITICAL)
    fetch, session = capture_trending.replay_fetcher()
    fresh.setattr(trending, "FETCH_BATCH", fetch)
    fresh.setattr(trending, "last_closed_session", lambda now=None: session)
    have = set(os.listdir(fb.fixtures_dir("panel")))
    seen = set()
    try:
        with fb.replay(fb.fixtures_dir("panel")) as store:
            def engine(sym):
                if sym not in have:
                    raise RuntimeError(f"{sym} no está en el juego de fixtures")
                return fb.run_analysis(sym, store)
            fresh.setattr(AQ, "ANALYZE", engine)

            def settled():
                r = asyncio.run(main.trending_v2_endpoint())
                if r["status"] != "listo":
                    return False
                # P8: con 30 por lista hay más tarjetas que cupo de precalentado; las de fuera, sin `engine`.
                states = {s: c["engine"]["status"] for s, c in _cards(r).items() if c["engine"]}
                seen.update(states.values())
                return len(states) >= cfg("market.trending.prewarm_max") and \
                    all(v in ("listo", "fallo") for v in states.values()) and r
            r = _wait(settled, timeout=240)
    finally:
        logging.disable(logging.NOTSET)
    cards = {s: c for s, c in _cards(r).items() if c["engine"]}
    assert len(cards) == cfg("market.trending.prewarm_max")
    # los precalentados son las más negociadas, en su orden (la lista que abre la portada)
    assert set(cards) == {x["symbol"] for x in r["data"]["lists"]["1D"]["most_traded"][:cfg("market.trending.prewarm_max")]}
    assert {"en_cola", "listo", "fallo"} <= seen
    ready = {s for s, c in cards.items() if c["engine"]["status"] == "listo"}
    assert ready == have & set(cards) and {"AAPL", "NVDA", "MSFT"} <= ready
    for s in ready:
        with open(os.path.join(fb.golden_dir("panel"), s + ".json"), encoding="utf-8") as fh:
            g = json.load(fh)
        assert cards[s]["engine"]["quality"]["score"] == g["quality"]["score"]
        assert cards[s]["engine"]["price_score"]["level"] == g["price_attractiveness"]["level"]
    assert all(c["engine"]["quality"] is None for s, c in cards.items() if s not in ready)


def test_each_batch_downloads_inside_a_background_slot(fresh):
    """V4 · memoria: cada lote de la descarga del universo, dentro de un turno (main: _background_slot), no además de
    los análisis en curso."""
    import contextlib
    syms = list(SERIES)
    fresh.setattr(trending, "_universe_symbols", lambda: syms)
    fresh.setitem(trending._limits, "batch_size", 2)
    held, log = [False], []

    @contextlib.contextmanager
    def slot():
        held[0] = True
        try:
            yield
        finally:
            held[0] = False

    def fetch(symbols):
        log.append(held[0])
        return fetcher(frame(SERIES))(symbols)
    fresh.setattr(trending, "SLOT", slot)
    trending.compute(fetch)
    assert log == [True, True, True]


def test_main_wires_the_background_slot(fresh):
    """main conecta las tendencias a _background_slot: espera mientras haya usuarios esperando turno y después toma un
    turno de fondo de _ANALYSIS_SLOTS."""
    import main
    real_cfg = main.cfg
    fresh.setattr(main, "cfg", lambda k: 0.01 if k == "market.analysis_queue.busy_wait_s" else real_cfg(k))
    got = threading.Event()

    def take():
        with trending.SLOT():
            got.set()
    with main._waiting_lock:
        main._waiting[0] += 1
    try:
        t = threading.Thread(target=take, daemon=True)
        t.start()
        assert not got.wait(0.2)                        # un usuario espera turno: la descarga, no
    finally:
        with main._waiting_lock:
            main._waiting[0] -= 1
    assert got.wait(SETTLE_S)
    t.join(SETTLE_S)


# ─────────────────────────── P8: listas por sector ───────────────────────────
SECTOR_OF = {"AAA": "Energy", "BBB": "Energy", "CCC": "Financials", "DDD": "Energy", "EEE": "Energy",
             "FFF": "Energy"}


def test_sector_lists_by_dollar_volume_with_the_row_shape(fresh):
    """Cada sector: los de más volumen en dólares de la misma descarga, con la misma forma de fila y su `sector`."""
    syms = list(SERIES)
    fresh.setattr(trending, "_universe_symbols", lambda: syms)
    fresh.setattr(universe, "get", lambda s: {"name": s.lower(), "gics_sector": SECTOR_OF.get(s)})
    fresh.setitem(trending._limits, "min_sector_items", 2)
    calls = []
    out = trending.compute(fetcher(frame(SERIES), calls))
    assert len(calls) == 1                                           # sin llamadas nuevas a Yahoo
    assert [x["symbol"] for x in out["sectors"]["1D"]["Energy"]] == ["BBB", "AAA"]
    assert set(out["sectors"]["1D"]["Energy"][0]) == set(out["lists"]["1D"]["most_traded"][0])
    assert out["sectors"]["1D"]["Energy"][0]["sector"] == "Energy"
    st = out["sector_status"]["1D"]
    assert list(st) == list(cfg("market.trending.sectors"))          # orden de config, claves GICS en inglés
    assert st["Energy"] == {"label": "Energía", "count": 2, "available": True, "reason": None}
    # un sector escaso (1 valor < 2) sale, pero no disponible y con su motivo; uno vacío, igual
    assert st["Financials"]["available"] is False and "solo 1 valor del sector" in st["Financials"]["reason"]
    assert out["sectors"]["1D"]["Utilities"] == [] and st["Utilities"]["count"] == 0 and not st["Utilities"]["available"]


def test_sector_ties_break_by_symbol(fresh):
    series = {s: [(10, 1e6)] * 4 + [(10, 1e6)] for s in ("ZZZ", "MMM", "AAA")}       # mismo volumen en dólares
    fresh.setattr(trending, "_universe_symbols", lambda: list(series))
    fresh.setattr(universe, "get", lambda s: {"name": s, "gics_sector": "Industrials"})
    out = trending.compute(fetcher(frame(series)))
    assert [x["symbol"] for x in out["sectors"]["1D"]["Industrials"]] == ["AAA", "MMM", "ZZZ"]


def test_sector_cards_carry_engine(fresh):
    syms = list(SERIES)
    fresh.setattr(trending, "_universe_symbols", lambda: syms)
    fresh.setattr(universe, "get", lambda s: {"name": s, "gics_sector": SECTOR_OF.get(s)})
    data = trending.compute(fetcher(frame(SERIES)))
    out = trending.with_engine(data)
    assert all("engine" in x for g in out["sectors"].values() for v in g.values() for x in v)
    assert "engine" not in data["sectors"]["1D"]["Energy"][0]        # la lista guardada no cambia
    assert "changes" not in out and "changes" in data                # las variaciones, solo para las mini-gráficas


def test_captured_batch_gives_sector_lists(fresh):
    """Con la descarga capturada y el universo real: todos los sectores GICS con valores (los ADR, con su sector)."""
    import capture_trending
    fetch, session = capture_trending.replay_fetcher()
    out = trending.compute(fetch, session=session)
    st = out["sector_status"]["1D"]
    assert all(st[k]["available"] for k in cfg("market.trending.sectors")), st
    assert sum(st[k]["count"] for k in st) == out["count"]          # ninguna fila sin sector
    tech = [x["symbol"] for x in out["sectors"]["1D"]["Information Technology"]]
    assert "TSM" in tech or "ASML" in tech                           # ADR con sector


# ─────────────────────────── P8b: las listas en el periodo elegido ───────────────────────────
def long_frame(series, n=130):
    """{símbolo: función(i) -> (cierre, cierre ajustado, volumen) o None} en `n` sesiones laborables seguidas."""
    days = pd.bdate_range(end="2026-10-16", periods=n)
    cols, data = [], {}
    for sym, f in series.items():
        rows = [f(i) for i in range(n)]
        for k, field in enumerate(("Close", "Adj Close", "Volume")):
            cols.append((sym, field))
            data[(sym, field)] = [np.nan if r is None else r[k] for r in rows]
    df = pd.DataFrame(data, index=days)
    df.columns = pd.MultiIndex.from_tuples(cols, names=["Ticker", "Price"])
    return df


def test_lists_are_computed_in_each_period_with_the_adjusted_close(fresh):
    """Un valor que sube en el día pero cae en 6 meses está en «Suben más · 1 día» y en «Bajan más · 6 meses»: la lista
    y su % salen del mismo periodo. Un split (el cierre se parte por 2) no es una caída: la variación usa el cierre
    ajustado; el precio mostrado es el cierre sin ajustar."""
    n = 130
    series = {
        "UPDAY": lambda i: (200 - i + (5 if i == n - 1 else 0),) * 2 + (1e6,),     # cae en 6M, sube el último día
        "SPLIT": lambda i: (100.0 if i < n - 10 else 51.0, 50.0 if i < n - 10 else 51.0, 1e6),   # split 2:1: +2 %
        "STEADY": lambda i: (10 + i * 0.1,) * 2 + (2e6,),
    }
    fresh.setattr(trending, "_universe_symbols", lambda: list(series))
    out = trending.compute(fetcher(long_frame(series, n)))
    L = out["lists"]
    up6 = {x["symbol"] for x in L["6M"]["gainers"]}
    down6 = {x["symbol"] for x in L["6M"]["losers"]}
    assert "UPDAY" in {x["symbol"] for x in L["1D"]["gainers"]} and "UPDAY" in down6 and "UPDAY" not in up6
    split = next(x for x in L["6M"]["gainers"] if x["symbol"] == "SPLIT")
    assert split["change_pct"] == pytest.approx(51 / 50 - 1) and split["price"] == 51.0   # no −49 %
    # la definición única: cierre ajustado de la última sesión / el de hace N sesiones − 1
    upday = next(x for x in L["6M"]["losers"] if x["symbol"] == "UPDAY")
    assert upday["change_pct"] == pytest.approx((200 - (n - 1) + 5) / (200 - (n - 1 - 126)) - 1)
    p = out["periods"]
    assert p["6M"]["sessions"] == 126 and p["6M"]["to"] == "2026-10-16"
    assert p["6M"]["from"] == pd.bdate_range(end="2026-10-16", periods=n)[n - 1 - 126].strftime("%Y-%m-%d")
    assert p["1D"]["from"] == "2026-10-15" and p["1S"]["sessions"] == 5 and p["1M"]["sessions"] == 21


def test_most_traded_uses_the_mean_daily_dollar_volume_of_the_period(fresh):
    """«Más negociadas» del periodo: volumen medio diario en dólares de sus N sesiones, no el del último día."""
    n = 130
    series = {"BIGDAY": lambda i: (10.0, 10.0, 1e9 if i == n - 1 else 1e3),   # un solo día enorme
              "STEADY": lambda i: (10.0, 10.0, 5e7)}
    fresh.setattr(trending, "_universe_symbols", lambda: list(series))
    out = trending.compute(fetcher(long_frame(series, n)))
    assert out["lists"]["1D"]["most_traded"][0]["symbol"] == "BIGDAY"
    assert out["lists"]["6M"]["most_traded"][0]["symbol"] == "STEADY"
    steady = out["lists"]["6M"]["most_traded"][0]
    assert steady["dollar_volume"] == pytest.approx(10.0 * 5e7)


def test_captured_batch_lists_have_the_sign_they_promise_in_every_period(fresh):
    """Con la descarga real: en cada periodo, «Suben más» solo trae valores que suben y «Bajan más» solo los que bajan
    (el fallo de «Bajan más · 6 meses» con PLTR ▲27 %); todas las listas llenas (sin nota) y cada tarjeta con la
    variación del periodo de su lista."""
    import capture_trending
    fetch, session = capture_trending.replay_fetcher()
    out = trending.compute(fetch, session=session)
    n = cfg("market.trending.top_n")
    for p in cfg("market.trending.periods"):
        L = out["lists"][p]
        assert all(x["change_pct"] > 0 for x in L["gainers"]), p
        assert all(x["change_pct"] < 0 for x in L["losers"]), p
        assert len(L["gainers"]) == len(L["losers"]) == len(L["most_traded"]) == n, p
        assert out["list_notes"][p] == {"gainers": None, "losers": None}
        for k in L:
            for x in L[k]:
                assert x["change_pct"] == out["changes"][x["symbol"]][p], (p, k, x["symbol"])
        for sec in out["sectors"][p].values():
            for x in sec:
                assert x["change_pct"] == out["changes"][x["symbol"]][p]


def test_endpoint_returns_only_the_requested_period(fresh):
    """V6b: /api/v2/trending?period=6M trae solo las listas, notas y sectores de 6M (la respuesta que se repite cada
    poll_s pesa una cuarta parte); sin `period`, todo; un periodo desconocido, 422."""
    import asyncio
    import capture_trending
    import gzip
    import json
    import main
    from fastapi import HTTPException
    fetch, session = capture_trending.replay_fetcher()
    fresh.setattr(trending, "FETCH_BATCH", fetch)
    fresh.setattr(trending, "last_closed_session", lambda now=None: session)
    _wait(lambda: asyncio.run(main.trending_v2_endpoint())["status"] == "listo", timeout=SETTLE_S)
    whole = asyncio.run(main.trending_v2_endpoint())
    one = asyncio.run(main.trending_v2_endpoint(period="6M"))
    for k in ("lists", "list_notes", "sectors", "sector_status"):
        assert list(one["data"][k]) == ["6M"] and one["data"][k]["6M"] == whole["data"][k]["6M"], k
    assert one["data"]["periods"] == whole["data"]["periods"] and "changes" not in one["data"]
    size = lambda r: len(gzip.compress(json.dumps(r).encode()))        # noqa: E731
    assert size(one) < size(whole) / 3
    with pytest.raises(HTTPException) as e:
        asyncio.run(main.trending_v2_endpoint(period="2Y"))
    assert e.value.status_code == 422


# ─────────────────────────── portada rápida: la última lista buena en disco ───────────────────────────
def _computed(fresh, tmp_path, session="2026-10-16", calls=None):
    """Un cálculo terminado con el archivo de la última lista buena en tmp_path."""
    fresh.setattr(trending, "_universe_symbols", lambda: list(SERIES))
    fresh.setattr(trending, "FETCH_BATCH", fetcher(frame(SERIES), calls))
    fresh.setattr(trending, "last_closed_session", lambda now=None: session)
    fresh.setattr(trending, "SNAPSHOT", str(tmp_path / "portada.json"))
    _wait(lambda: trending.get()["status"] == "listo" and (tmp_path / "portada.json").exists(), timeout=SETTLE_S)
    return trending.get("1D")


def test_snapshot_serves_the_last_good_list_at_once_after_a_restart(fresh, tmp_path):
    """Tras un reinicio con la lista de la misma sesión en disco: «listo» en la primera petición y sin descargar el
    universo otra vez (la misma lista que daría el cálculo, que no cambia dentro de una sesión)."""
    calls = []
    before = _computed(fresh, tmp_path, calls=calls)
    assert len(calls) == 1
    trending.reset()                                           # el proceso nuevo: nada en memoria
    assert trending.restore() is True
    after = trending.get("1D")
    assert after["status"] == "listo" and after["refreshing"] is False
    assert after["data"]["lists"] == before["data"]["lists"] and after["data"]["session"] == "2026-10-16"
    time.sleep(0.1)
    assert len(calls) == 1                                     # misma sesión: no se vuelve a descargar


def test_snapshot_of_an_older_session_is_served_while_recomputing(fresh, tmp_path):
    calls = []
    _computed(fresh, tmp_path, calls=calls)
    trending.reset()
    fresh.setattr(trending, "last_closed_session", lambda now=None: "2026-10-19")
    assert trending.restore() is True
    r = trending.get("1D")
    assert r["status"] == "listo" and r["refreshing"] is True and r["data"]["session"] == "2026-10-16"
    _wait(lambda: len(calls) == 2 and not trending.get()["refreshing"], timeout=SETTLE_S)


def test_snapshot_of_another_universe_is_served_while_recomputing(fresh, tmp_path):
    calls = []
    _computed(fresh, tmp_path, calls=calls)
    trending.reset()
    fresh.setattr(universe, "meta", lambda: {"date": "2099-01-01", "source": "x", "count": 6})
    assert trending.restore() is True
    assert trending.get("1D")["refreshing"] is True
    _wait(lambda: len(calls) == 2, timeout=SETTLE_S)


def test_snapshot_of_another_config_or_unreadable_is_ignored(fresh, tmp_path):
    _computed(fresh, tmp_path)
    path = tmp_path / "portada.json"
    trending.reset()
    real_cfg = trending.cfg
    fresh.setattr(trending, "cfg", lambda k: {**real_cfg(k), "top_n": 2} if k == "market.trending" else real_cfg(k))
    assert trending.restore() is False and trending._state["data"] is None    # otra config: otra forma
    fresh.setattr(trending, "cfg", real_cfg)
    trending.reset()
    path.write_text("{no es json", encoding="utf-8")
    assert trending.restore() is False and trending._state["data"] is None
    path.unlink()
    assert trending.restore() is False


def test_no_snapshot_without_a_path(fresh, tmp_path):
    fresh.setattr(trending, "SNAPSHOT", None)
    fresh.setattr(trending, "_universe_symbols", lambda: list(SERIES))
    fresh.setattr(trending, "FETCH_BATCH", fetcher(frame(SERIES)))
    _wait(lambda: trending.get()["status"] == "listo", timeout=SETTLE_S)
    assert trending.restore() is False and list(tmp_path.iterdir()) == []


def test_lists_ready_warm_the_sparklines_of_the_first_view(fresh, tmp_path):
    """Al publicar las listas, el servidor descarga las mini-gráficas de la vista inicial (1D, «Más negociadas») con
    la misma petición que hará la web (mismos símbolos y orden: la descarga en marcha se comparte). Van en el
    archivo y vuelven tras un reinicio."""
    import price_history
    import sparklines
    price_history.reset()
    sparklines.reset()
    asked = []

    def fetch(symbols, rng, interval):
        asked.append((tuple(symbols), rng, interval))
        day = [("2026-10-15", 1.0), ("2026-10-16", 2.0)]
        bars = [("2026-10-16T09:30:00-04:00", 1.0), ("2026-10-16T09:35:00-04:00", 2.0)]
        return {s: (bars if interval == "5m" else day) for s in symbols}
    fresh.setattr(sparklines, "FETCH", fetch)
    fresh.setattr(sparklines, "_in_universe", lambda s: True)
    fresh.setattr(trending, "WARM_SPARKLINES", True)
    r = _computed(fresh, tmp_path)
    first = tuple(x["symbol"] for x in r["data"]["lists"]["1D"]["most_traded"])
    _wait(lambda: all(sparklines.peek(s, "1D") for s in first), timeout=SETTLE_S)
    assert sorted(asked[:2]) == [(first, "1d", "5m"), (first, "5d", "1d")]
    import json
    _wait(lambda: set(json.loads((tmp_path / "portada.json").read_text())["sparklines"].get("1D", {})) == set(first),
          timeout=SETTLE_S)
    sparklines.reset()
    trending.reset()
    fresh.setattr(trending, "WARM_SPARKLINES", False)
    assert trending.restore() is True
    assert all(sparklines.peek(s, "1D") for s in first)       # vuelven con su hora (y caducan con su TTL)
    sparklines.reset()
    price_history.reset()


def test_main_starts_the_strip_at_boot_with_its_snapshot_file(fresh):
    """main: el evento startup llama a warm con el archivo de config (relativo a backend/), otra ruta por
    FINANZER_PORTADA_SNAPSHOT o ninguno con «0»."""
    import os
    import main
    got = []
    fresh.setattr(trending, "warm", lambda env, snapshot=None: got.append(snapshot))
    assert main._trending_at_boot in main.app.router.on_startup
    fresh.delenv("FINANZER_PORTADA_SNAPSHOT", raising=False)
    main._trending_at_boot()
    fresh.setenv("FINANZER_PORTADA_SNAPSHOT", "/disco/portada.json")
    main._trending_at_boot()
    fresh.setenv("FINANZER_PORTADA_SNAPSHOT", "0")
    main._trending_at_boot()
    backend = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assert got == [os.path.join(backend, cfg("market.trending.snapshot_file")), "/disco/portada.json", None]


# ── cintillo en vivo (12-nov-2026): con la bolsa abierta, las listas van hasta el último precio de la sesión ──
LIVE_AT = dt.datetime(2026, 10, 19, 11, 0, tzinfo=trending.NY).timestamp()      # lunes, sesión posterior al viernes 16


def _quote(sym, px, prev, vol, at=LIVE_AT):
    return {"symbol": sym, "regularMarketPrice": px, "regularMarketPreviousClose": prev, "regularMarketVolume": vol,
            "regularMarketTime": at, "marketState": "REGULAR"}


def _closed(fresh):
    fresh.setattr(trending, "_universe_symbols", lambda: list(SERIES))
    return trending.compute(fetcher(frame(SERIES)))


def test_market_open_window():
    ny, f = trending.NY, trending.market_open
    assert not f(dt.datetime(2026, 10, 19, 9, 29, tzinfo=ny))           # lunes antes de la apertura
    assert f(dt.datetime(2026, 10, 19, 9, 30, tzinfo=ny))
    assert f(dt.datetime(2026, 10, 19, 16, 29, tzinfo=ny))              # hasta que llega el cálculo del cierre
    assert not f(dt.datetime(2026, 10, 19, 16, 30, tzinfo=ny))
    assert not f(dt.datetime(2026, 10, 18, 12, 0, tzinfo=ny))           # domingo


def test_live_overlay_ranks_the_session_against_the_previous_close(fresh):
    d = _closed(fresh)
    # hoy: AAA cae un 10 % (110 → 99), BBB sube un 25 % (40 → 50), CCC igual; BBB es la más negociada de hoy
    q = [_quote("AAA", 99.0, 110.0, 1e6), _quote("BBB", 50.0, 40.0, 4e6), _quote("CCC", 21.0, 21.0, 1e5)]
    L = trending.live_overlay(d, q)
    assert L["session"] == "2026-10-19" and L["live"] == {"session": "2026-10-19", "at": "2026-10-19T15:00:00Z",
                                                          "refresh_s": cfg("market.trending.live_refresh_s")}
    day = L["lists"]["1D"]
    assert [(x["symbol"], round(x["change_pct"], 4)) for x in day["gainers"]] == [("BBB", 0.25)]
    assert [(x["symbol"], round(x["change_pct"], 4)) for x in day["losers"]] == [("AAA", -0.1)]
    assert [x["symbol"] for x in day["most_traded"]] == ["BBB", "AAA", "CCC"]       # volumen en dólares de hoy
    assert day["most_traded"][0]["price"] == 50.0
    assert L["periods"]["1D"]["from"] == "2026-10-16" and L["periods"]["1D"]["to"] == "2026-10-19"
    # periodos largos: la variación ajustada hasta el cierre encadenada con la de hoy (con una sesión más, 1S parte del
    # día 12, el primero de la descarga: AAA 10 → 99)
    assert round(L["changes"]["AAA"]["1S"], 4) == round(99 / 10 - 1, 4)
    assert L["periods"]["1S"]["from"] == "2026-10-12"
    assert "live_base" not in trending.with_engine(L)


def test_live_overlay_ignores_quotes_of_the_closed_session(fresh):
    d = _closed(fresh)
    friday = dt.datetime(2026, 10, 16, 16, 0, tzinfo=trending.NY).timestamp()
    assert trending.live_overlay(d, [_quote("AAA", 110.0, 100.0, 1e6, at=friday)]) is None     # preapertura, festivo
    assert trending.live_overlay(d, []) is None


def test_get_serves_the_live_lists_while_the_market_is_open(fresh):
    fresh.setattr(trending, "_universe_symbols", lambda: list(SERIES))
    fresh.setattr(trending, "FETCH_BATCH", fetcher(frame(SERIES)))
    fresh.setattr(trending, "last_closed_session", lambda now=None: "2026-10-16")
    is_open = {"v": False}
    fresh.setattr(trending, "market_open", lambda now=None: is_open["v"])
    asked = []
    fresh.setattr(trending, "FETCH_QUOTES", lambda syms: asked.append(sorted(syms)) or [
        _quote("AAA", 99.0, 110.0, 1e6), _quote("BBB", 50.0, 40.0, 4e6)])
    _wait(lambda: trending.get()["status"] == "listo", timeout=SETTLE_S)
    r = trending.get()
    assert r["data"]["live"] is None and r["next_s"] is None and not asked     # cerrada: las del cierre, sin sondeo
    is_open["v"] = True
    fresh.setattr(trending, "FETCH_QUOTES", lambda syms: (time.sleep(0.3), asked.append(sorted(syms)))[1] or [
        _quote("AAA", 99.0, 110.0, 1e6), _quote("BBB", 50.0, 40.0, 4e6)])
    assert trending.get()["next_s"] == cfg("market.trending.poll_s")              # pidiéndolas: vuelve enseguida
    _wait(lambda: trending.get()["data"]["live"] is not None, timeout=SETTLE_S)
    r = trending.get(period="1D")
    assert r["data"]["session"] == "2026-10-19"
    # la siguiente pregunta, cuando toque la ronda siguiente (no 2 min después de esta)
    assert cfg("market.trending.poll_s") <= r["next_s"] <= cfg("market.trending.live_refresh_s")
    assert [x["symbol"] for x in r["data"]["lists"]["1D"]["gainers"]] == ["BBB"]
    assert trending.change_of("AAA", "1D") == pytest.approx(-0.1)                    # la de la tarjeta y su gráfica
    assert asked == [["AAA", "BBB", "CCC", "FFF"]]                                  # una sola petición por ronda
    for _ in range(3):
        trending.get()
    assert len(asked) == 1                                                          # hasta pasados live_refresh_s
    # llega el cálculo del cierre de esa sesión: se sirve el del cierre, no la capa en vivo
    fresh.setattr(trending, "last_closed_session", lambda now=None: "2026-10-19")
    with trending._lock:
        trending._state["data"] = {**trending._state["data"], "session": "2026-10-19", "as_of": "otro"}
    assert trending.get()["data"]["live"] is None
