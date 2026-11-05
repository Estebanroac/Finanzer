"""Verificación de la v4 (V3 · fuentes caídas): con cada fallo de tests/faults.py sobre el replay, la API responde sin
5xx y cada bloque dice su motivo. Los mismos fallos los usa el e2e de e2e/v2-faults (POST /__replay/fault en el
servidor de replay).

Endpoints: /api/analysis, /api/v2/{prices, segments, peers, trending, scenario, search, logo}, /api/pdf y, si existe
en la rama (E5), /api/v2/pdf. Empresa: AAPL (y MSFT y NVDA como rivales)."""
import asyncio
import json
import logging
import os
import time

import pytest
from fastapi import HTTPException

import faults
import fixture_backend as fb

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
SYMBOL = "AAPL"
RIVALS = "MSFT,NVDA"
SETTLE_S = 120          # rivales y tendencias se calculan en segundo plano: espera máxima
POLL_S = 0.05
CLIENT_ERROR = 400
SERVER_ERROR = 500


def _call(fn):
    """(estado HTTP, cuerpo) como lo vería el cliente: HTTPException con su código; cualquier otra excepción, 500."""
    try:
        r = fn()
        if asyncio.iscoroutine(r):
            r = asyncio.run(r)
        return getattr(r, "status_code", 200), r
    except HTTPException as e:
        return e.status_code, e.detail
    except Exception as e:  # noqa: BLE001 — así respondería FastAPI: 500
        return SERVER_ERROR, f"{type(e).__name__}: {e}"


class _Req:
    headers: dict = {}


def _settle(fn, done):
    t0 = time.monotonic()
    while True:
        st, r = _call(fn)
        if st >= CLIENT_ERROR or done(r) or time.monotonic() - t0 > SETTLE_S:
            return st, r
        time.sleep(POLL_S)


@pytest.fixture(scope="module")
def app():
    import main
    import replay_server
    logging.disable(logging.CRITICAL)
    base = fb.fixtures_dir("panel")
    import analysis_queue
    with fb.replay(base) as store:
        orig, orig_analyze = main._compute_analysis, analysis_queue.ANALYZE
        replay_server.install(main, base, store)
        switch = faults.Switch()
        try:
            yield main, switch
        finally:
            switch.set(None)
            main._compute_analysis = orig
            analysis_queue.ANALYZE = orig_analyze     # V4b: install envuelve la cola de fondo del replay
            logging.disable(logging.NOTSET)


def _golden_inputs():
    with open(os.path.join(TESTS_DIR, "golden", "panel", f"{SYMBOL}.json"), encoding="utf-8") as fh:
        return json.load(fh)["scenario_inputs"]


def _run_all(main):
    """Todos los endpoints de la v4 para SYMBOL: {nombre: (estado, cuerpo)}."""
    out = {"analysis": _call(lambda: main.analyze_stock(SYMBOL))}
    a = out["analysis"][1] if out["analysis"][0] == 200 else None
    sector = (a or {}).get("profile", {}).get("sector") or "Technology"
    out["prices"] = _call(lambda: main.prices_v2_endpoint(SYMBOL, sector=sector))
    out["segments"] = _call(lambda: main.segments_v2_endpoint(SYMBOL))
    out["search"] = _call(lambda: main.search_v2_endpoint("apple"))
    inputs = (a or {}).get("scenario_inputs") or _golden_inputs()
    out["scenario"] = _call(lambda: main.scenario_v2({"inputs": inputs, "assumptions": {"discount_rate": 0.12}}))
    out["peers"] = _settle(lambda: main.peers_v2_endpoint(SYMBOL, symbols=RIVALS), lambda r: r["status"] != "calculando")
    out["trending"] = _settle(main.trending_v2_endpoint, lambda r: r["status"] != "calculando")
    out["pdf"] = _call(lambda: main.download_pdf(SYMBOL))
    out["logo"] = _call(lambda: main.logo_v2_endpoint(SYMBOL, _Req()))      # corrutina: _call la ejecuta
    if hasattr(main, "download_pdf_v2"):          # rediseño E5 (cuando esté fusionado)
        out["pdf_v2"] = _call(lambda: main.download_pdf_v2(SYMBOL))
    return out


@pytest.mark.parametrize("fault", [None, *faults.FAULTS])
def test_no_5xx_and_reasons_in_place(app, fault, monkeypatch):
    import capture_logos
    import logos
    main, switch = app
    monkeypatch.setattr(logos, "FETCH", capture_logos.replay_fetcher())   # los grabados (conftest los quita)
    switch.set(fault)
    res = _run_all(main)
    errors = {k: (st, str(body)[:200]) for k, (st, body) in res.items() if st >= SERVER_ERROR}
    assert errors == {}, f"5xx con {fault}: {errors}"

    st, a = res["analysis"]
    prices = res["prices"][1]
    if fault == "yahoo_down":
        # La fuente no respondió: se dice así (antes "No data found", como si el símbolo no existiera).
        assert st == 404 and a == main.source_unavailable_message(SYMBOL)
        assert prices["company"]["status"] == "sin_dato" and prices["company"]["reason"]
        assert res["trending"][1]["status"] == "sin_dato" and "no se pudieron calcular" in res["trending"][1]["reason"]
        assert res["search"][1]["results"][0]["ticker"] == SYMBOL      # la base local sigue respondiendo
        assert res["pdf"][0] == 404
        return
    assert st == 200 and a["symbol"] == SYMBOL
    if fault == "logos_down":       # sin logotipo: null en el análisis y 204 en su endpoint (la web pone la placa)
        assert a["logo"] is None and res["logo"][0] == 204
    else:
        assert a["logo"]["source"] and res["logo"][0] == 200 and res["logo"][1].media_type == "image/png"
    ext = a["display"]["extended"]
    assert res["scenario"][1]["status"] == "ok"
    assert res["peers"][1]["status"] == "listo" and {r["status"] for r in res["peers"][1]["rivals"]} == {"listo"}
    assert res["trending"][1]["status"] == "listo"
    assert res["pdf"][0] == 200 and res["pdf"][1].body[:4] == b"%PDF"

    if fault in ("edgar_no_ua", "edgar_slow"):
        why = "User-Agent" if fault == "edgar_no_ua" else "no respondió a tiempo"
        for block in (ext["company_profile"], ext["history_10y"], res["segments"][1]):
            assert block["status"] == "sin_dato" and why in block["reason"], block
        assert why in prices["company"]["events_reason"]
        assert "TimeoutError: " not in json.dumps(ext, ensure_ascii=False)        # nada de motivos vacíos
    else:
        assert ext["company_profile"]["status"] == "ok" and res["segments"][1]["status"] == "ok"
    if fault in ("finnhub_no_key", "finnhub_429"):
        assert ext["news"] == []                                                  # la página dice que no hay
    if fault == "prices_empty":
        assert prices["company"]["status"] == "sin_dato"
        assert prices["company"]["reason"].startswith("Yahoo no devolvió la serie de precios")
        assert prices["market"]["status"] == "ok"
    elif fault == "sector_etf_down":
        assert prices["sector"]["status"] == "sin_dato" and prices["sector"]["reason"].startswith("Yahoo no respondió")
        assert prices["company"]["status"] == "ok"
    elif fault == "spy_down":       # el índice sigue; su rentabilidad total, «sin dato» con el motivo
        assert {prices[k]["status"] for k in ("company", "market", "sector")} == {"ok"}
        assert prices["market"]["total_status"] == "sin_dato"
        assert prices["market"]["total_note"].startswith("sin la serie con dividendos")
    else:
        assert {prices[k]["status"] for k in ("company", "market", "sector")} == {"ok"}


def test_slow_edgar_does_not_hold_the_analysis(app):
    """EDGAR que no responde: el análisis sigue dentro de su presupuesto (más el margen de espera), no se cuelga. F10
    (PM, 29-oct): con un reintento de `data.edgar.retry_s` antes de seguir sin EDGAR (un tiempo agotado no cambia el
    análisis en silencio)."""
    from settings import cfg
    main, switch = app
    switch.set("edgar_slow")
    t0 = time.monotonic()
    st, _a = _call(lambda: main.analyze_stock(SYMBOL))
    assert st == 200 and time.monotonic() - t0 < (cfg("data.edgar.budget_s") + cfg("data.edgar.timeout_s")
                                                  + cfg("data.edgar.retry_s") + 2)
    switch.set(None)


def test_switch_undoes_every_fault(app):
    """Tras cada fallo, el replay vuelve exactamente al estado base (el e2e cambia de fallo en caliente)."""
    import finnhub_fallback
    import price_history
    import sec_edgar
    import yf_adapter
    import yfinance
    main, switch = app
    switch.set(None)
    before = (yf_adapter._ensure_session, yfinance.Ticker, price_history.FETCHER, sec_edgar.FETCHER,
              finnhub_fallback._get, os.environ.get("SEC_EDGAR_USER_AGENT"))
    for f in faults.FAULTS:
        switch.set(f)
    switch.set(None)
    after = (yf_adapter._ensure_session, yfinance.Ticker, price_history.FETCHER, sec_edgar.FETCHER,
             finnhub_fallback._get, os.environ.get("SEC_EDGAR_USER_AGENT"))
    assert after == before
    with pytest.raises(KeyError):
        faults.apply("no_existe")
