"""Rediseño E2b (Task 5): los tipos de frontend/src/lib/api.ts (SegmentsResponse, PeersResponse, TrendingResponse)
encajan con salidas reales de los endpoints (fixtures sin red), con el mismo verificador que StockAnalysis
(frontend/scripts/check-contract.mjs --root=Tipo)."""
import json
import threading
import os
import time

import pytest

import analysis_queue as AQ
import peers
import sec_edgar as edgar
import segments
import trending
from settings import cfg
from test_frontend_contract import _run, needs_node

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
SEG_TICKERS = ["AAPL", "JPM", "O", "NEE", "XOM", "PLTR", "RIVN", "BCS", "MC.PA"]


def _dump(d, name, obj):
    d.mkdir(exist_ok=True)
    (d / f"{name}.json").write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


def _segments_samples(d, monkeypatch):
    import capture_segments
    monkeypatch.setenv("SEC_EDGAR_USER_AGENT", "test test@example.invalid")
    monkeypatch.setattr(edgar.time, "sleep", lambda *_a: None)
    monkeypatch.setattr(segments, "FETCHER", capture_segments.replay_fetcher())
    edgar.reset()
    segments.reset()
    for t in SEG_TICKERS:
        res = segments.build(t)
        _dump(d, t, {**res, "summary": segments.summary(res)})      # como lo sirve /api/v2/segments (V7)
    edgar.reset()
    segments.reset()


def _wait(fn, done, timeout=10.0):
    t0 = time.monotonic()
    while True:
        r = fn()
        if done(r):
            return r
        assert time.monotonic() - t0 < timeout, r
        time.sleep(0.02)


def _pe(comp, value):
    groups = [{**g, "items": [{**i, "value": value, "value_txt": f"{value:.2f}x"} if i["key"] == "pe" else i
                              for i in g.get("items") or []]} for g in comp.get("groups") or []]
    return {**comp, "groups": groups}


def _peers_samples(d, monkeypatch):
    import capture_peer_caps

    base = {"AAPL": "AAPL", "DELL": "AAPL", "SNDK": "MC.PA", "NOPE": "JPM"}

    def engine(sym):
        if sym not in base:
            raise RuntimeError(f"{sym} no está en el juego de fixtures")
        with open(os.path.join(TESTS_DIR, "golden", "panel", base[sym] + ".json"), encoding="utf-8") as fh:
            a = {**json.load(fh), "symbol": sym}
        if sym in ("SNDK", "NOPE"):         # sin industria de referencia (reference: null)
            a["benchmark"] = {**a["benchmark"], "industry": None}
        if sym == "DELL":                   # V7 · P5: un P/E fuera de rango («n. s.», con `note`)
            a["display"] = {**a["display"], "charts": {**a["display"]["charts"], "comparison": _pe(
                a["display"]["charts"]["comparison"], 4366.0)}}
        return a
    import main  # noqa: F401  (conecta el motor real al importarse: se sustituye después)
    peers.reset()
    monkeypatch.setattr(peers, "CAPS_FETCHER", capture_peer_caps.load_caps().get)
    monkeypatch.setattr(AQ, "ANALYZE", engine)
    _dump(d, "auto_calculando", peers.peers_for("AAPL"))
    _dump(d, "auto_listo", _wait(lambda: peers.peers_for("AAPL"),
                                 lambda r: r["rivals"] and r["status"] == "listo"))
    _dump(d, "elegidos", _wait(lambda: peers.peers_for("AAPL", ["DELL", "SNDK", "ZZZZ"]),
                               lambda r: r["status"] == "listo"))
    _dump(d, "empresa_ns", _wait(lambda: peers.peers_for("DELL", ["AAPL"]), lambda r: r["status"] == "listo"))
    peers.peers_for("NOPE")
    _dump(d, "sin_dato", _wait(lambda: peers.peers_for("NOPE"), lambda r: r["status"] == "sin_dato"))
    # V6 (B7): cola llena: "en_cola" con retry (el hilo bloqueado en el primero; el tope de 1 deja fuera al segundo)
    peers.reset()
    gate = threading.Event()
    monkeypatch.setattr(AQ, "ANALYZE", lambda sym: gate.wait(5) and engine("AAPL"))
    monkeypatch.setitem(AQ._limits, "max_queue", 1)
    _dump(d, "cola_llena", peers.peers_for("AAPL", ["DELL", "SNDK", "NOPE"]))
    gate.set()
    peers.reset()


def _trending_samples(d, monkeypatch):
    """Rediseño E4: la muestra "listo" cubre los cinco estados del motor de una tarjeta (listo, fallo, analizando,
    en_cola y null por el cupo de precalentado)."""
    import threading
    import capture_trending
    import main  # noqa: F401  (conecta el motor real al importarse: se sustituye después)
    AQ.reset()
    trending.reset()
    fetch, _session = capture_trending.replay_fetcher()
    monkeypatch.setattr(trending, "FETCH_BATCH", fetch)
    gate = threading.Event()
    order = []

    def engine(sym):
        order.append(sym)
        if len(order) == 2:
            raise RuntimeError(f"{sym} sin datos")
        if len(order) == 3:
            gate.wait(10)
        with open(os.path.join(TESTS_DIR, "golden", "panel", "AAPL.json"), encoding="utf-8") as fh:
            return {**json.load(fh), "symbol": sym}
    monkeypatch.setattr(AQ, "ANALYZE", engine)
    monkeypatch.setitem(trending._limits, "prewarm_max", cfg("market.trending.prewarm_max") - 1)
    _dump(d, "calculando", trending.get())

    def states(r):
        cards = [x for k in ("most_traded", "gainers", "losers") for x in r["data"]["lists"]["1D"][k]]   # P8b: por periodo
        return {(x["engine"] or {}).get("status") for x in cards}
    _dump(d, "listo", _wait(trending.get, lambda r: r["status"] == "listo" and states(r) == {
        "listo", "fallo", "analizando", "en_cola", None}))
    gate.set()
    trending.reset()
    AQ.reset()

    def boom(_s):
        raise RuntimeError("Yahoo caído")
    monkeypatch.setattr(trending, "FETCH_BATCH", boom)
    trending.get()
    _dump(d, "sin_dato", _wait(trending.get, lambda r: r["status"] == "sin_dato"))
    trending.reset()


def _search_samples(d, monkeypatch):
    """Rediseño E4: el buscador de /v2 (con bolsa y sin ella)."""
    import capture_search
    import search_v2
    monkeypatch.setattr(search_v2, "YAHOO_QUOTES", capture_search.replay_quotes())
    for q in ("apple", "coca", "jpm", "zzzzqqq"):
        _dump(d, q, search_v2.search(q))

    def boom(q, n):
        raise TimeoutError("Yahoo caído")
    monkeypatch.setattr(search_v2, "YAHOO_QUOTES", boom)
    _dump(d, "sin_yahoo", search_v2.search("apple"))


@needs_node
@pytest.mark.parametrize("root,make", [("SegmentsResponse", _segments_samples), ("PeersResponse", _peers_samples),
                                       ("TrendingResponse", _trending_samples), ("SearchResponse", _search_samples)])
def test_v2_types_match_backend(tmp_path, monkeypatch, root, make):
    d = tmp_path / root
    make(d, monkeypatch)
    r = _run("check-contract.mjs", "--strict-unions", f"--root={root}", str(d))
    assert r.returncode == 0, r.stderr or r.stdout
    assert f"{root} encaja" in r.stdout
