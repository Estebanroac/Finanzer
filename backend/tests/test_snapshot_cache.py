"""Fase 7 (verificación en prod con EDGAR, BRK-B con P/E 49x): el perfil y los estados que se derivan de un snapshot de
get_ticker_info valen solo para ese snapshot. Con su propio TTL (30 y 60 min) sobrevivían al snapshot (5 min) y el
análisis mezclaba el beneficio del ejercicio de un snapshot sin EDGAR con las ganancias de la cartera del corte de
EDGAR del siguiente. Sin red."""
import data_fetcher as DF


def _snap(ni, mcap=1000.0):
    return {"regularMarketPrice": 10.0, "netIncome": ni, "totalRevenue": 500.0, "marketCap": mcap,
            "longName": "X Corp", "sector": "Financial Services", "industry": "Insurance - Diversified"}


def test_financials_follow_the_current_snapshot(monkeypatch):
    DF._data_cache.clear()
    cur = {"s": _snap(100.0)}
    monkeypatch.setattr(DF, "get_ticker_info", lambda symbol: cur["s"])
    svc = DF.YahooFinanceFetcher()
    a = svc.get_financial_data("XX")
    assert a.net_income == 100.0 and a.snapshot is cur["s"]
    assert svc.get_financial_data("XX") is a                  # mismo snapshot: lo guardado
    cur["s"] = _snap(120.0)                                    # snapshot nuevo (caducó el de 5 min)
    b = svc.get_financial_data("XX")
    assert b.net_income == 120.0 and b.snapshot is cur["s"]   # antes: 100 (estados del snapshot anterior, 60 min)


def test_profile_follows_the_current_snapshot(monkeypatch):
    DF._data_cache.clear()
    cur = {"s": _snap(100.0, mcap=1000.0)}
    monkeypatch.setattr(DF, "get_ticker_info", lambda symbol: cur["s"])
    svc = DF.YahooFinanceFetcher()
    assert svc.get_company_profile("XX").market_cap == 1000.0
    cur["s"] = _snap(100.0, mcap=1500.0)
    assert svc.get_company_profile("XX").market_cap == 1500.0


def test_snapshot_never_reaches_the_ratio_engine():
    import main
    fin = DF.FinancialStatements(net_income=5.0, snapshot={"netIncome": 5.0})
    assert main.financials_to_dict(fin) == {"net_income": 5.0}
