"""P8: mini-gráficas del cintillo de la portada (lib/sparklines.py, GET /api/v2/sparklines). Sin red: series
inyectadas y la descarga capturada (tests/fixtures/sparklines)."""
import pytest
from fastapi import HTTPException

import sparklines
from settings import cfg


@pytest.fixture
def fresh(monkeypatch):
    import price_history
    # los tests usan símbolos de juguete (AAA): fuera de test_only_universe_symbols, cualquiera vale
    monkeypatch.setattr(sparklines, "_in_universe", lambda s: True)
    sparklines.reset()
    price_history.reset()            # la puerta de las descargas de /v2 recuerda los fallos
    yield monkeypatch
    sparklines.reset()
    price_history.reset()


def _endpoint(symbols, period="1D"):
    import main
    return main.sparklines_v2_endpoint(symbols=symbols, period=period)


def _status(symbols, period="1D"):
    try:
        _endpoint(symbols, period)
    except HTTPException as e:
        return e.status_code
    return 200


def intraday(day, closes):
    return [(f"{day}T{9 + (30 + 5 * i) // 60:02d}:{(30 + 5 * i) % 60:02d}:00-04:00", c) for i, c in enumerate(closes)]


def fake(series, calls=None):
    """FETCH de prueba: {(rango, intervalo): {símbolo: serie}}."""
    def fetch(symbols, rng, interval):
        if calls is not None:
            calls.append((tuple(symbols), rng, interval))
        return {s: series[(rng, interval)][s] for s in symbols if s in series.get((rng, interval), {})}
    return fetch


# ─────────────────────────── validación ───────────────────────────
def test_validation_422(fresh):
    fresh.setattr(sparklines, "FETCH", fake({}))
    assert _status(None) == 422 and _status(" , ") == 422                      # sin símbolos
    assert _status("AAPL", "2A") == 422                                         # periodo fuera de config
    assert _status("AAPL;DROP") == 422 and _status("<script>") == 422          # la regla de símbolos de /v2
    n = cfg("market.sparklines.max_symbols")
    assert _status(",".join(f"S{i}" for i in range(n))) == 200                 # el tope, sí
    assert _status(",".join(f"S{i}" for i in range(n + 1))) == 422             # uno más, no
    assert sparklines.parse("brk.b,AAPL,aapl", "1m") == (["BRK-B", "AAPL"], "1M")   # normaliza y quita repetidos


# ─────────────────────────── reducción ───────────────────────────
def test_lttb_keeps_ends_extremes_and_cap():
    import math
    vals = [100 + 10 * math.sin(i / 15) + (25 if i == 137 else 0) - (30 if i == 222 else 0) for i in range(390)]
    keep = sparklines.lttb(vals, 60)
    assert len(keep) == 60 and keep[0] == 0 and keep[-1] == 389 and keep == sorted(keep)
    assert 137 in keep and 222 in keep                                          # el pico y el valle no se pierden
    assert sparklines.lttb([1.0, 2.0, 3.0], 60) == [0, 1, 2]                    # con menos puntos, todos


def test_points_reduced_in_the_backend(fresh):
    closes = [100 + (i % 7) for i in range(126)]
    days = [f"2026-{4 + i // 22:02d}-{1 + i % 22:02d}" for i in range(126)]
    fresh.setattr(sparklines, "FETCH", fake({("6mo", "1d"): {"AAA": list(zip(days, closes))}}))
    it = _endpoint("AAA", "6M")["items"]["AAA"]
    assert it["status"] == "ok" and it["n"] == 126 and len(it["points"]) == cfg("market.sparklines.max_points")
    assert it["points"][0] == [0, 100] and it["points"][-1][0] == 125
    assert it["first_t"] == days[0] and it["last_t"] == days[-1]


# ─────────────────────────── referencia y variación ───────────────────────────
def test_1d_reference_is_previous_close_and_1m_the_first_close(fresh):
    calls = []
    fresh.setattr(sparklines, "FETCH", fake({
        ("1d", "5m"): {"AAA": intraday("2026-10-16", [101, 99, 103, 104])},
        ("5d", "1d"): {"AAA": [("2026-10-14", 98.0), ("2026-10-15", 100.0), ("2026-10-16", 104.0)]},
        ("1mo", "1d"): {"AAA": [("2026-09-17", 80.0), ("2026-10-16", 104.0)]},
    }, calls))
    d = _endpoint("AAA", "1D")
    a = d["items"]["AAA"]
    assert a["ref"] == 100.0 and a["ref_basis"] == "cierre anterior"
    assert a["first_t"].startswith("2026-10-16T09:30") and d["period"] == "1D" and d["label"] == "1 día"
    assert sorted(c[1:] for c in calls) == [("1d", "5m"), ("5d", "1d")]         # 1D: barras y cierre diario, a la vez
    m = _endpoint("AAA", "1M")["items"]["AAA"]
    assert m["ref"] == 80.0 and m["ref_basis"] == "primer cierre"


def test_change_is_the_one_of_the_lists(fresh):
    """P8b: la variación de la mini-gráfica es la de las listas del cintillo (lib/period_change.py por
    trending.change_of), no la de su serie; sin listas, null y el motivo."""
    import trending
    fresh.setattr(sparklines, "FETCH", fake({
        ("1d", "5m"): {"AAA": intraday("2026-10-16", [101, 99, 103, 104])},
        ("5d", "1d"): {"AAA": [("2026-10-15", 100.0), ("2026-10-16", 104.0)]},
        ("1mo", "1d"): {"AAA": [("2026-09-17", 80.0), ("2026-10-16", 104.0)]}}))
    trending.reset()
    try:
        a = _endpoint("AAA", "1D")["items"]["AAA"]
        assert a["change_pct"] is None and a["change_reason"] == "sin variación del periodo en las listas"
        with trending._lock:
            trending._state["data"] = {"changes": {"AAA": {"1D": 0.0412, "1M": 0.2875}}}
        assert _endpoint("AAA", "1D")["items"]["AAA"]["change_pct"] == 0.0412      # la caché no la congela
        m = _endpoint("AAA", "1M")["items"]["AAA"]
        assert m["change_pct"] == 0.2875 and m["change_reason"] is None
    finally:
        trending.reset()


def test_1d_keeps_only_the_last_session(fresh):
    fresh.setattr(sparklines, "FETCH", fake({
        ("1d", "5m"): {"AAA": intraday("2026-10-15", [90, 91]) + intraday("2026-10-16", [101, 102])},
        ("5d", "1d"): {"AAA": [("2026-10-15", 100.0), ("2026-10-16", 102.0)]}}))
    a = _endpoint("AAA")["items"]["AAA"]
    assert a["n"] == 2 and a["ref"] == 100.0 and a["first_t"].startswith("2026-10-16")


# ─────────────────────────── Yahoo caído y huecos ───────────────────────────
def test_yahoo_down_gives_items_without_chart_never_5xx(fresh):
    def down(*a, **kw):
        raise ConnectionError("sin red")
    fresh.setattr(sparklines, "FETCH", down)
    d = _endpoint("AAPL,MSFT", "1S")
    assert list(d["items"]) == ["AAPL", "MSFT"] and d["as_of"] is None
    for it in d["items"].values():
        assert it["status"] == "sin_dato" and it["reason"] == "Yahoo no respondió (ConnectionError)"


def test_missing_symbol_and_single_point(fresh):
    fresh.setattr(sparklines, "FETCH", fake({("1mo", "1d"): {"ONE": [("2026-10-16", 5.0)],
                                                             "OK": [("2026-10-15", 5.0), ("2026-10-16", 5.5)]}}))
    d = _endpoint("ONE,NONE,OK", "1M")["items"]
    assert d["NONE"] == {"status": "sin_dato", "reason": "Yahoo no devolvió la serie del periodo"}
    assert d["ONE"]["status"] == "sin_dato" and "una sola" in d["ONE"]["reason"]
    assert d["OK"]["status"] == "ok"


# ─────────────────────────── caché ───────────────────────────
def test_cache_by_symbol_and_period_with_ttl(fresh):
    calls = []
    fresh.setattr(sparklines, "FETCH", fake({("1mo", "1d"): {"A": [("2026-10-15", 1.0), ("2026-10-16", 2.0)],
                                                             "B": [("2026-10-15", 1.0), ("2026-10-16", 3.0)]}}, calls))
    now = [1000.0]
    fresh.setattr(sparklines.time, "time", lambda: now[0])
    _endpoint("A", "1M")
    _endpoint("A,B", "1M")                                       # A de la caché; solo B se descarga
    assert [c[0] for c in calls] == [("A",), ("B",)]
    now[0] += cfg("market.sparklines.periods")["1M"]["ttl_s"] + 1
    r = _endpoint("A,B", "1M")
    assert all(it["stale"] for it in r["items"].values())        # caducados: se sirven los de antes...
    sparklines.wait_refreshes()
    assert calls[-1][0] == ("A", "B")                            # ...y una descarga para los dos, en segundo plano
    r = _endpoint("A,B", "1M")
    assert not any(it.get("stale") for it in r["items"].values()) and len(calls) == 3


def test_expired_sparklines_do_not_make_the_visitor_wait(fresh):
    """Portada rápida: pasado el TTL, la respuesta no espera a Yahoo (sirve lo anterior, marcado `stale`, mientras
    se refresca una sola vez aunque lleguen varias visitas)."""
    import threading
    day = [("2026-10-15", 1.0), ("2026-10-16", 2.0)]
    gate = threading.Event()
    calls = []

    def fetch(symbols, rng, interval):
        calls.append(tuple(symbols))
        if len(calls) > 1:
            assert gate.wait(10)
        return {s: day for s in symbols}
    fresh.setattr(sparklines, "FETCH", fetch)
    now = [1000.0]
    fresh.setattr(sparklines.time, "time", lambda: now[0])
    _endpoint("A,B", "1M")
    now[0] += cfg("market.sparklines.periods")["1M"]["ttl_s"] + 1
    t0 = __import__("time").monotonic()
    for _ in range(3):
        r = _endpoint("A,B", "1M")
        assert r["items"]["A"]["status"] == "ok" and r["items"]["A"]["stale"] is True
    assert __import__("time").monotonic() - t0 < 1.0             # Yahoo sigue sin responder: nadie esperó
    gate.set()
    sparklines.wait_refreshes()
    assert len(calls) == 2                                        # un solo refresco para las tres visitas


def test_dump_and_load_keep_the_time_of_each_sparkline(fresh):
    fresh.setattr(sparklines, "FETCH", fake({("1mo", "1d"): {"A": [("2026-10-15", 1.0), ("2026-10-16", 2.0)]}}))
    now = [1000.0]
    fresh.setattr(sparklines.time, "time", lambda: now[0])
    _endpoint("A", "1M")
    snap = sparklines.dump("1M", ["A", "ZZZ"])                   # solo lo que hay en caché
    assert list(snap["1M"]) == ["A"]
    sparklines.reset()
    sparklines.load(snap)
    assert sparklines.peek("A", "1M") == snap["1M"]["A"][1]
    now[0] += cfg("market.sparklines.periods")["1M"]["ttl_s"] + 1
    assert _endpoint("A", "1M")["items"]["A"]["stale"] is True    # con su hora de entonces: caduca igual


def test_cache_is_bounded(fresh):
    cap = cfg("market.sparklines.cache_max")
    for k in range(0, (cap // 40 + 2) * 40, 40):
        fresh.setattr(sparklines, "FETCH", fake({("1mo", "1d"): {f"S{i}": [("2026-10-15", 1.0),
                                                                            ("2026-10-16", 2.0)]
                                                                 for i in range(k, k + 40)}}))
        _endpoint(",".join(f"S{i}" for i in range(k, k + 40)), "1M")
    assert len(sparklines._cache) == cap


# ─────────────────────────── replay ───────────────────────────
def test_replay_fixtures_cover_the_strip_in_every_period(fresh):
    """Con la descarga capturada: las 30 más negociadas del replay tienen gráfica en los cuatro periodos y, en cada
    periodo, la variación de cada tarjeta es exactamente la de su lista (P8b: la misma función)."""
    import capture_sparklines
    import capture_trending
    import trending
    fresh.setattr(sparklines, "FETCH", capture_sparklines.replay_fetcher())
    fetch, session = capture_trending.replay_fetcher()
    trending.reset()
    out = trending.compute(fetch, session=session)
    try:
        with trending._lock:
            trending._state["data"] = out
        syms = [x["symbol"] for x in out["lists"]["1D"]["most_traded"]]
        for p in cfg("market.sparklines.periods"):
            d = sparklines.get(syms, p)
            assert all(it["status"] == "ok" for it in d["items"].values()), p
            assert all(len(it["points"]) <= cfg("market.sparklines.max_points") for it in d["items"].values())
        # P8b: en cada periodo, el % de cada tarjeta (el de su mini-gráfica) es exactamente el de su lista
        for p in cfg("market.trending.periods"):
            for k, cards in out["lists"][p].items():
                got = sparklines.get([x["symbol"] for x in cards], p)["items"]
                for x in cards:
                    assert got[x["symbol"]]["change_pct"] == x["change_pct"], (p, k, x["symbol"])
    finally:
        trending.reset()


def test_only_universe_symbols(monkeypatch):
    """V6b: un símbolo que no está en el universo del cintillo es un 422 y no llega a Yahoo (una lista inventada no
    convierte cada petición en descargas nuevas)."""
    calls = []
    monkeypatch.setattr(sparklines, "FETCH", lambda *a, **kw: calls.append(a) or {})
    sparklines.reset()
    with pytest.raises(HTTPException) as e:
        _endpoint("AAPL,ZZZZ9", "1D")
    assert e.value.status_code == 422 and e.value.detail == "símbolo fuera del universo de la portada"
    assert calls == []
    assert sparklines.parse("aapl,MSFT,BRK.B", "6M") == (["AAPL", "MSFT", "BRK-B"], "6M")


def test_1d_bars_and_reference_download_at_the_same_time(fresh):
    """Portada rápida: en frío, las dos descargas de 1D (barras y cierre anterior) se solapan; antes iban seguidas."""
    import threading
    both = threading.Barrier(2, timeout=5)                       # solo pasa si las dos están en marcha a la vez
    series = {("1d", "5m"): {"AAA": intraday("2026-10-16", [101, 103])},
              ("5d", "1d"): {"AAA": [("2026-10-15", 100.0), ("2026-10-16", 103.0)]}}

    def fetch(symbols, rng, interval):
        both.wait()
        return {s: series[(rng, interval)][s] for s in symbols}
    fresh.setattr(sparklines, "FETCH", fetch)
    a = _endpoint("AAA", "1D")["items"]["AAA"]
    assert a["status"] == "ok" and a["ref"] == 100.0
