import pandas as pd
import pytest
import prices_v2


def _frame():
    idx = pd.to_datetime(["2026-10-14", "2026-10-15", "2026-10-16"])
    return pd.DataFrame({"close": [10.0, 11.0, None], "adj_close": [9.5, 10.5, 12.0],
                         "volume": [100.0, 200.0, 300.0], "dividend": [0.0, 0.25, 0.0], "split": [0.0, 0.0, 4.0]},
                        index=idx)


def test_serialize_cierre_sin_ajustar_ajustado_y_fecha_iso():
    """Rediseño E2a (T9): `c` es el cierre sin ajustar por dividendos (rentabilidad de precio) y `a` el ajustado
    (rentabilidad total); sin cierre en la última sesión, `c` toma el ajustado."""
    out = prices_v2.serialize({"symbol": "AAPL", "frame": _frame(), "reason": None}, "AAPL")
    assert out["status"] == "ok"
    assert out["points"][0] == {"t": "2026-10-14", "c": 10.0, "a": 9.5, "v": 100.0}
    assert out["points"][1]["c"] != out["points"][1]["a"]
    assert out["points"][-1]["a"] == 12.0


def test_eventos_de_dividendos_y_splits():
    out = prices_v2.serialize({"symbol": "AAPL", "frame": _frame(), "reason": None}, "AAPL")
    assert out["events"] == [
        {"t": "2026-10-15", "kind": "dividend", "value": 0.25, "label": "Dividendo: 0.25 por acción"},
        {"t": "2026-10-16", "kind": "split", "value": 4.0, "label": "Split 4:1"}]
    rev = pd.DataFrame({"close": [1.0], "adj_close": [1.0], "volume": [1.0], "dividend": [0.0], "split": [0.1]},
                       index=pd.to_datetime(["2026-01-02"]))
    assert prices_v2.serialize({"frame": rev}, "X")["events"][0]["label"] == "Contrasplit 1:10"
    # un factor que no es una proporción simple (escisión de Orion en O, 2021: 1.032) no se llama split
    assert prices_v2._split_label(1.032) == "Ajuste de capital (factor 1.032)"
    assert prices_v2._split_label(1.5) == "Split 3:2"


def test_serialize_sin_serie():
    out = prices_v2.serialize({"symbol": "XYZ", "frame": None, "reason": "sin datos"}, "XYZ")
    assert out == {"symbol": "XYZ", "status": "sin_dato", "reason": "sin datos", "points": [], "events": []}


def test_resultados_desde_los_8k_de_edgar():
    filings = [{"form": "8-K", "items": "2.02,9.01", "filingDate": "2026-07-30"},
               {"form": "8-K", "items": "5.07", "filingDate": "2026-06-01"},
               {"form": "10-Q", "items": "", "filingDate": "2026-08-01"},
               {"form": "8-K", "items": "2.02", "filingDate": "2026-04-30"}]
    ev = prices_v2.earnings_events_from(filings, first="2026-05-01")
    assert ev == [{"t": "2026-07-30", "kind": "earnings", "value": None, "label": "Resultados (8-K)"}]


def test_chart_usa_su_periodo_y_no_toca_la_cache_del_motor(monkeypatch):
    import price_history
    from settings import cfg
    asked = []

    def fetcher(sym, period, interval):
        asked.append((sym, period))
        idx = pd.DatetimeIndex(pd.to_datetime(["2026-10-15", "2026-10-16"])).tz_localize("America/New_York")
        return pd.DataFrame({"Open": [1.0, 1.0], "High": [1.0, 1.0], "Low": [1.0, 1.0], "Close": [1.0, 1.1],
                             "Adj Close": [1.0, 1.1], "Volume": [1.0, 1.0], "Dividends": [0.0, 0.0],
                             "Stock Splits": [0.0, 0.0]}, index=idx)
    price_history.reset()
    monkeypatch.setattr(price_history, "FETCHER", fetcher)
    res = price_history.chart("aapl")
    assert res["frame"] is not None and asked == [("AAPL", cfg("market.history.chart_period"))]
    assert price_history.peek("AAPL") is None            # la serie de 2 años del motor no se rellena con la de 5
    price_history.chart("AAPL")
    assert len(asked) == 1                               # caché propia
    price_history.company("AAPL")
    assert asked[-1] == ("AAPL", cfg("market.history.period"))
    price_history.reset()


def test_cache_de_la_grafica_acotada(monkeypatch):
    import price_history
    from settings import cfg
    price_history.reset()
    monkeypatch.setattr(price_history, "_download",
                        lambda sym, fetcher, period=None: {"symbol": sym, "frame": _frame(), "reason": None})
    for i in range(cfg("market.history.chart_cache_max") + 5):
        price_history.chart(f"S{i}")
    assert len(price_history._chart_cache) == cfg("market.history.chart_cache_max")
    price_history.reset()


def _patch_history(monkeypatch, calls):
    import price_history

    def fake(sym):
        calls.append(sym)
        return {"symbol": sym, "frame": _frame(), "reason": None}
    monkeypatch.setattr(price_history, "chart", fake)
    monkeypatch.setattr(price_history, "chart_market", lambda: fake("^GSPC"))
    monkeypatch.setattr(prices_v2, "earnings_events", lambda sym, first=None: ([], "sin EDGAR en el test"))


def test_endpoint_empresa_mercado_y_etf_de_sector(monkeypatch):
    import main
    calls = []
    _patch_history(monkeypatch, calls)
    out = main.prices_v2_endpoint("aapl", sector="Technology")
    assert out["symbol"] == "AAPL" and out["as_of"] == "2026-10-16"
    assert [out[k]["status"] for k in ("company", "market", "sector")] == ["ok", "ok", "ok"]
    assert out["sector"]["symbol"] == "XLK"
    assert calls == ["AAPL", "^GSPC", "XLK", "SPY"]   # V7 (M7): SPY, para la rentabilidad total del mercado
    assert out["market"]["total_status"] == "ok" and out["market"]["total_symbol"] == "SPY"
    assert out["source"].startswith("Serie diaria de Yahoo Finance de 5 años (del ")
    assert [e["kind"] for e in out["company"]["events"]] == ["dividend", "split"]
    assert out["company"]["events_reason"] == "sin EDGAR en el test"


def test_endpoint_el_etf_sale_del_registro_de_sectores(monkeypatch):
    import main
    calls = []
    _patch_history(monkeypatch, calls)
    # Un sector desconocido cae en el perfil neutro (SPY, que ya es el mercado): sin serie de sector, sin descarga.
    out = main.prices_v2_endpoint("AAPL", sector="TSLA")
    assert out["sector"]["status"] == "sin_dato" and out["sector"]["points"] == []
    assert calls == ["AAPL", "^GSPC", "SPY"]
    assert main.prices_v2_endpoint("AAPL")["sector"]["status"] == "sin_dato"


# ─────────────────────────── V6 (revisión de seguridad): B8 ───────────────────────────
def test_endpoint_valida_el_simbolo():
    from fastapi import HTTPException
    import main
    for bad in ("../etc", "A" * 11, "AAPL;rm", "", "a b"):
        with pytest.raises(HTTPException) as e:
            main.prices_v2_endpoint(bad)
        assert e.value.status_code == 422


def test_grafica_una_descarga_por_simbolo_turno_y_fallo_recordado(monkeypatch):
    """B8: consultas simultáneas del mismo símbolo, una descarga; como mucho `chart_concurrency` a la vez; un símbolo
    sin serie se recuerda `chart_fail_ttl_s` (antes se volvía a descargar en cada consulta)."""
    import threading
    import time
    import price_history
    from settings import cfg
    price_history.reset()
    calls, now, peak, lock = [], [0], [0], threading.Lock()

    def slow(sym, fetcher, period=None):
        with lock:
            calls.append(sym)
            now[0] += 1
            peak[0] = max(peak[0], now[0])
        time.sleep(0.1)
        with lock:
            now[0] -= 1
        return {"symbol": sym, "frame": None, "reason": "Yahoo no devolvió la serie"}
    monkeypatch.setattr(price_history, "_download", slow)
    ts = [threading.Thread(target=price_history.chart, args=(s,)) for s in ["DUP"] * 5 + [f"S{i}" for i in range(6)]]
    [t.start() for t in ts]
    [t.join(5) for t in ts]
    assert calls.count("DUP") == 1 and peak[0] == cfg("market.history.chart_concurrency")
    assert price_history.chart("DUP")["reason"] == "Yahoo no devolvió la serie" and calls.count("DUP") == 1
    price_history.reset()


# ─────────────────────────── V7 (M7): rentabilidad total del mercado ───────────────────────────
def _series(sym, rows):
    return {"symbol": sym, "status": "ok", "events": [],
            "points": [{"t": t, "c": c, "a": a, "v": None} for t, c, a in rows]}


def test_mercado_con_dividendos_sale_de_spy_ajustado():
    """El índice no reparte dividendos (su `a` es su `c`): la rentabilidad total sale del cierre ajustado de SPY, en la
    escala del índice; el de precio sigue siendo el índice."""
    gspc = _series("^GSPC", [("2026-01-02", 100.0, 100.0), ("2026-01-05", 110.0, 110.0), ("2026-01-06", 121.0, 121.0)])
    spy = _series("SPY", [("2026-01-02", 50.0, 40.0), ("2026-01-06", 60.0, 50.0)])   # sin la sesión del 5
    out = prices_v2.with_total_return(gspc, spy, "SPY")
    assert out["total_status"] == "ok" and out["total_symbol"] == "SPY" and "dividendos" in out["total_note"]
    assert [p["c"] for p in out["points"]] == [100.0, 110.0, 121.0]
    assert [p["a"] for p in out["points"]] == pytest.approx([100.0, 100.0, 125.0])   # +25 % con dividendos


def test_mercado_sin_serie_con_dividendos_lo_dice():
    gspc = _series("^GSPC", [("2026-01-02", 100.0, 100.0)])
    out = prices_v2.with_total_return(gspc, {"status": "sin_dato", "reason": "Yahoo caído", "points": []}, "SPY")
    assert out["total_status"] == "sin_dato" and "Yahoo caído" in out["total_note"]
    # con el ETF como respaldo del índice, su cierre ajustado ya incluye dividendos
    spy = _series("SPY", [("2026-01-02", 50.0, 40.0)])
    assert prices_v2.with_total_return(spy, {}, "SPY")["total_status"] == "ok"
    assert prices_v2.with_total_return({"status": "sin_dato", "points": []}, spy, "SPY") == {"status": "sin_dato",
                                                                                           "points": []}
