"""Verificación de la v4 (V4 · carga y memoria): las cachés por símbolo tienen tope (lib/bounded.py)."""
import bounded


def test_put_keeps_the_most_recent_writes():
    c = {}
    for i in range(10):
        bounded.put(c, f"S{i}", i, 3)
    assert list(c) == ["S7", "S8", "S9"]
    bounded.put(c, "S7", 70, 3)                 # reescribir la sube al final
    bounded.put(c, "S10", 10, 3)
    assert list(c) == ["S9", "S7", "S10"] and c["S7"] == 70


def test_price_history_engine_cache_is_bounded(monkeypatch):
    import pandas as pd
    import price_history
    from settings import cfg
    price_history.reset()
    frame = pd.DataFrame({"close": [1.0]}, index=pd.to_datetime(["2026-10-16"]))
    monkeypatch.setattr(price_history, "_download",
                        lambda sym, fetcher, period=None: {"symbol": sym, "frame": frame, "reason": None})
    for i in range(cfg("market.history.cache_max") + 7):
        price_history.company(f"S{i}")
    assert len(price_history._cache) == cfg("market.history.cache_max")
    price_history.reset()


def test_finnhub_cache_is_bounded(monkeypatch):
    import finnhub_fallback
    from settings import cfg
    finnhub_fallback._cache.clear()
    monkeypatch.setattr(finnhub_fallback, "_get", lambda path, params: {"metric": {}})
    for i in range(cfg("data.finnhub.cache_max_entries") + 7):
        finnhub_fallback._basic_financials(f"S{i}")
    assert len(finnhub_fallback._cache) == cfg("data.finnhub.cache_max_entries")
    finnhub_fallback._cache.clear()


def test_yahoo_last_known_good_is_bounded():
    import yf_adapter
    from settings import cfg
    yf_adapter._best_cache.clear()
    info = {f: 1.0 for f in cfg("data.yahoo.completeness_fields")}
    for i in range(cfg("data.yahoo.info_cache_max_symbols") + 7):
        yf_adapter._merge_last_known_good(f"S{i}", dict(info), False)
    assert len(yf_adapter._best_cache) == cfg("data.yahoo.info_cache_max_symbols")
    yf_adapter._best_cache.clear()


_REAL_COMPACT = None


def _recorded_metric(sym):
    import json
    import os
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "panel", sym, "finnhub.json")
    with open(path, encoding="utf-8") as fh:
        return next(e["response"] for e in json.load(fh) if e["path"] == "/stock/metric")


def _enrich(monkeypatch, sym, response, compact):
    import copy
    import finnhub_fallback
    global _REAL_COMPACT
    _REAL_COMPACT = _REAL_COMPACT or finnhub_fallback._compact_metrics
    finnhub_fallback._cache.clear()
    monkeypatch.setenv("FINNHUB_API_KEY", "test")
    monkeypatch.setattr(finnhub_fallback, "_get", lambda path, params: copy.deepcopy(response))
    monkeypatch.setattr(finnhub_fallback, "_compact_metrics", _REAL_COMPACT if compact else (lambda d: d))
    info = finnhub_fallback.enrich_info({"_currency": {}}, sym)
    cached = finnhub_fallback._cache[sym][1]
    finnhub_fallback._cache.clear()
    return info, cached


def test_finnhub_cache_keeps_only_what_enrich_reads(monkeypatch):
    """V4 · memoria: la caché guarda `metric` y las series de Piotroski de los dos últimos años, no la respuesta entera
    de /stock/metric (~1,7 MB en memoria por empresa); lo que enrich_info rellena es idéntico."""
    import json
    for sym in ("AAPL", "JPM", "KO"):
        resp = _recorded_metric(sym)
        full, raw = _enrich(monkeypatch, sym, resp, compact=False)
        small, kept = _enrich(monkeypatch, sym, resp, compact=True)
        assert small == full and small["_piotroski_current"] and small["_prior_year"], sym
        assert set(kept) == {"metric", "series"} and all(len(v) <= 2 for v in kept["series"]["annual"].values())
        assert len(json.dumps(kept)) < len(json.dumps(raw)) / 5, sym


def test_yahoo_unreachable_is_bounded():
    """V6 (B10): la marca de "Yahoo no respondió" por símbolo también tiene tope."""
    import yf_adapter
    from settings import cfg
    yf_adapter._unreachable.clear()
    for i in range(cfg("data.yahoo.info_cache_max_symbols") + 9):
        yf_adapter._note_unreachable(f"S{i}", TimeoutError())
    assert len(yf_adapter._unreachable) == cfg("data.yahoo.info_cache_max_symbols")
    assert yf_adapter.unreachable(f"S{cfg('data.yahoo.info_cache_max_symbols') + 8}")
    yf_adapter._unreachable.clear()
