"""Fase 6: los estados financieros de Yahoo se guardan más que la cotización (cambian cada trimestre). Sin red."""
import pandas as pd
import pytest

import yf_adapter as Y


class _FakeTicker:
    calls = []

    def __init__(self, symbol):
        self.symbol = symbol

    def __getattr__(self, name):
        _FakeTicker.calls.append(name)
        if name == "fast_info":
            return {"lastPrice": 10.0}
        if name == "quarterly_cashflow":
            return pd.DataFrame()                       # vacío: no se guarda
        return pd.DataFrame({"2025-12-31": [1.0]}, index=["Total Revenue"])


@pytest.fixture
def fake(monkeypatch):
    import yfinance
    monkeypatch.setattr(yfinance, "Ticker", _FakeTicker)
    Y._stmt_cache.clear()
    _FakeTicker.calls = []
    yield
    Y._stmt_cache.clear()


def test_statements_are_reused_within_their_ttl(fake, monkeypatch):
    a = Y._stmt_ticker("ABC").income_stmt
    b = Y._stmt_ticker("ABC").income_stmt
    assert _FakeTicker.calls.count("income_stmt") == 1 and a.equals(b) and a is not b
    t0 = Y.time.time()
    monkeypatch.setattr(Y.time, "time", lambda: t0 + Y._STMT_TTL + 1)
    Y._stmt_ticker("ABC").income_stmt
    assert _FakeTicker.calls.count("income_stmt") == 2


def test_quote_and_empty_statements_are_never_cached(fake):
    for _ in range(2):
        t = Y._stmt_ticker("ABC")
        t.fast_info
        t.quarterly_cashflow
    assert _FakeTicker.calls.count("fast_info") == 2 and _FakeTicker.calls.count("quarterly_cashflow") == 2


def test_cache_is_per_symbol_and_bounded(fake, monkeypatch):
    monkeypatch.setattr(Y, "_STMT_MAX", 2)
    for s in ("A", "B", "C"):
        Y._stmt_ticker(s).balance_sheet
    assert len(Y._stmt_cache) == 2 and ("A", "balance_sheet") not in Y._stmt_cache


def test_statement_currency_probe_is_cached(fake, monkeypatch):
    n = []

    class _R:
        status_code = 200

        def json(self):
            return {"timeseries": {"result": [{"annualTotalRevenue": [{"currencyCode": "EUR"}]}]}}

    class _S:
        def get(self, *a, **k):
            n.append(1)
            return _R()

    monkeypatch.setattr(Y, "_ensure_session", lambda: None)
    monkeypatch.setattr(Y, "_session", _S())
    assert Y._statement_currency("ABC") == "EUR" and Y._statement_currency("ABC") == "EUR"
    assert len(n) == 1
