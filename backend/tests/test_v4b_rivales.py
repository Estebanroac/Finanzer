"""
V4b (decisión del PM): rivales del replay. Cada ticker del panel con rivales propuestos tiene al menos 3 analizados en
el replay (los del panel o los capturados aparte, comprimidos, en tests/fixtures/peers); los demás no parecen un fallo.
"""
import gzip
import json
import os

import pytest

import analysis_queue as AQ
import capture_peer_caps
import fixture_backend as fb
import peers
from settings import cfg

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
PEERS_DIR = os.path.join(TESTS_DIR, "fixtures", "peers")
PANEL_DIR = fb.fixtures_dir(fb.PANEL_ENV)
GOLDEN = fb.golden_dir(fb.PANEL_ENV)
MIN_ANALYZED = 3


def _rivals(sym):
    """Los rivales automáticos del replay, sin red: la industria del análisis (golden) y las capitalizaciones grabadas."""
    with open(os.path.join(GOLDEN, f"{sym}.json"), encoding="utf-8") as fh:
        ref = AQ.reference(json.load(fh))
    if ref is None:
        return None
    caps_tbl = capture_peer_caps.load_caps()
    cands = peers.lookup_order(peers.candidates(sym, ref["industry"], ref["region"]),
                               ref["region"])[:cfg("market.peers.max_cap_lookups")]
    caps = {s: caps_tbl.get(s) for s in [sym] + cands}
    return peers.rank(sym, cands, caps, ref["region"])["rivals"]


def _has_fixtures(sym):
    return any(os.path.isdir(os.path.join(d, sym)) for d in (PANEL_DIR, PEERS_DIR))


@pytest.mark.parametrize("sym", fb.env_tickers(fb.PANEL_ENV))
def test_every_panel_ticker_has_three_analyzed_rivals(sym):
    rivals = _rivals(sym)
    if rivals is None:
        pytest.skip(f"{sym}: sin industria de referencia (sin rivales propuestos)")
    have = [r for r in rivals if _has_fixtures(r)]
    assert len(have) >= min(MIN_ANALYZED, len(rivals)), (sym, rivals, have)


def test_peer_fixtures_are_compressed_and_readable():
    syms = sorted(d for d in os.listdir(PEERS_DIR) if os.path.isdir(os.path.join(PEERS_DIR, d)) and d != "f2b")
    assert len(syms) > 30
    for s in syms:
        names = sorted(os.listdir(os.path.join(PEERS_DIR, s)))
        assert names == ["finnhub.json.gz", "metadata.json.gz", "yahoo_http.json.gz", "yfinance.json.gz"], (s, names)
    meta = fb.read_json(os.path.join(PEERS_DIR, syms[0], "metadata.json"))
    assert meta["ticker"] == syms[0]


def test_store_reads_gz_and_falls_back_to_extra_dirs(tmp_path):
    d = tmp_path / "peers" / "ZZZ"
    d.mkdir(parents=True)
    for name, obj in (("metadata.json", {"ticker": "ZZZ"}), ("yahoo_http.json", []), ("yfinance.json", {}),
                      ("finnhub.json", [])):
        (d / name).write_text(json.dumps(obj), encoding="utf-8")
    fb.gzip_fixture_dir(str(d))
    first = (d / "metadata.json.gz").read_bytes()
    assert gzip.decompress(first) == json.dumps({"ticker": "ZZZ"}).encode()
    store = fb.FixtureStore(str(tmp_path / "panel"), extra_dirs=(str(tmp_path / "peers"),))
    assert store.has("zzz") and not store.has("AAA")
    store.load("ZZZ")
    assert store.meta["ZZZ"] == {"ticker": "ZZZ"}


def test_replay_analyzes_a_recorded_rival_and_names_the_rest_for_the_reader():
    """En la cola de fondo del replay (rivales, tarjetas de la portada): un rival grabado en tests/fixtures/peers se
    analiza con el motor; una empresa sin datos grabados no es un fallo: el motivo es de lector. El 404 del análisis de
    una página sigue diciendo el suyo (la pantalla de carga lo prueba)."""
    import logging
    import main
    import replay_server as rs
    from fastapi import HTTPException
    assert rs.NOT_IN_DEMO == "No incluido en la demo con datos grabados; con datos reales se analiza al momento"
    logging.disable(logging.CRITICAL)
    orig_compute, orig_analyze = main._compute_analysis, AQ.ANALYZE
    try:
        with fb.replay(PANEL_DIR, extra_dirs=(PEERS_DIR,)) as store:
            rs.install(main, PANEL_DIR, store)
            a = AQ.ANALYZE("WFC")                       # rival grabado (comprimido)
            assert a["symbol"] == "WFC" and a["quality"]["score"] is not None
            assert not [m for m in store.misses if m.startswith(("edgar", "history"))], store.misses
            with pytest.raises(HTTPException) as e:
                AQ.ANALYZE("HD")
            assert e.value.detail == rs.NOT_IN_DEMO
            with pytest.raises(HTTPException) as e:
                main._compute_analysis("HD")
            assert "sin fixtures en el replay" in e.value.detail
    finally:
        main._compute_analysis, AQ.ANALYZE = orig_compute, orig_analyze
        logging.disable(logging.NOTSET)
