"""Rediseño E2a (T8): próximos resultados — anunciados (calendario de Finnhub) o estimados (último 8-K de resultados
de EDGAR + un trimestre), nunca inventados."""
import datetime as dt

import finnhub_fallback as fh
import market_context as mc

TODAY = dt.date(2026, 10, 17)


def test_fecha_anunciada(monkeypatch):
    monkeypatch.setattr(fh, "is_enabled", lambda: True)
    monkeypatch.setattr(fh, "earnings_calendar", lambda s, a, b: [
        {"date": "2026-10-30", "hour": "amc", "symbol": "AAPL"}, {"date": "2026-10-10", "symbol": "AAPL"}])
    r = mc.next_earnings("AAPL", [], TODAY)
    assert r["status"] == "ok" and r["kind"] == "anunciada" and r["date"] == "2026-10-30" and r["hour"] == "amc"
    assert "Finnhub" in r["source"]


def test_fecha_estimada_por_el_ritmo_de_filings(monkeypatch):
    monkeypatch.setattr(fh, "is_enabled", lambda: True)
    monkeypatch.setattr(fh, "earnings_calendar", lambda s, a, b: [])
    filings = [{"form": "8-K", "items": "2.02,9.01", "filingDate": (TODAY - dt.timedelta(days=40)).isoformat()},
               {"form": "8-K", "items": "5.07", "filingDate": (TODAY - dt.timedelta(days=5)).isoformat()},
               {"form": "8-K", "items": "2.02", "filingDate": (TODAY - dt.timedelta(days=131)).isoformat()}]
    r = mc.next_earnings("AAPL", filings, TODAY)
    assert r["status"] == "ok" and r["kind"] == "estimada"
    assert r["date"] == (TODAY - dt.timedelta(days=40) + dt.timedelta(days=91)).isoformat()
    assert "EDGAR" in r["source"] and r["basis"]


def test_sin_nada(monkeypatch):
    monkeypatch.setattr(fh, "is_enabled", lambda: False)
    r = mc.next_earnings("AAPL", None, TODAY)
    assert r["status"] == "sin_dato" and r["date"] is None and r["reason"] == "Sin fecha anunciada"
    old = [{"form": "8-K", "items": "2.02", "filingDate": (TODAY - dt.timedelta(days=200)).isoformat()}]
    assert mc.next_earnings("AAPL", old, TODAY)["status"] == "sin_dato"     # la estimada ya pasó: no se inventa
