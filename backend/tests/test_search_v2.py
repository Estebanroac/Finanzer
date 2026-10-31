"""Rediseño E4 (Task 2): buscador de /v2 (lib/search_v2.py): base local y Yahoo, con la bolsa y solo acciones. Sin red:
las respuestas de Yahoo capturadas (tests/capture_search.py)."""
import asyncio

import pytest

import capture_search
import search_v2
from settings import cfg


@pytest.fixture
def replay(monkeypatch):
    monkeypatch.setattr(search_v2, "YAHOO_QUOTES", capture_search.replay_quotes())
    return monkeypatch


def test_apple_first_with_its_exchange(replay):
    r = search_v2.search("apple")["results"]
    assert r[0] == {"ticker": "AAPL", "name": "Apple Inc.", "exchange": "Nasdaq"}
    assert all(x["ticker"] != "SAAPL=F" for x in r)                    # futuros fuera
    assert len(r) <= cfg("market.search.limit")


def test_only_equities(replay):
    tickers = [x["ticker"] for x in search_v2.search("aapl")["results"]]
    assert "AAPU" not in tickers and "AAPD" not in tickers             # ETF apalancados: no se analizan


def test_exact_ticker_first_and_names_of_exchanges(replay):
    r = search_v2.search("jpm")["results"]
    assert r[0]["ticker"] == "JPM" and r[0]["exchange"] == "NYSE"
    mc = {x["ticker"]: x for x in search_v2.search("lvmh")["results"]}
    assert mc["MC.PA"]["exchange"] == "Euronext París"


def test_without_yahoo_local_results_have_no_exchange(monkeypatch):
    def boom(q, n):
        raise TimeoutError("Yahoo caído")
    monkeypatch.setattr(search_v2, "YAHOO_QUOTES", boom)
    r = search_v2.search("apple")["results"]
    assert r[0]["ticker"] == "AAPL" and r[0]["exchange"] is None


def test_empty_and_unknown(replay):
    assert search_v2.search("   ") == {"results": []}
    assert search_v2.search("zzzzqqq") == {"results": []}


def test_endpoint(replay):
    import main
    out = asyncio.run(main.search_v2_endpoint("apple"))
    assert out["results"][0]["ticker"] == "AAPL"
