"""
Etapa 11b: invariantes sobre la muestra amplia (tests/fixtures/muestra, capturada en local
con red) y sobre los 12 juegos con golden. Sin red.

  · textos visibles sin códigos de arquetipo ni "$-" (signo antes del símbolo);
  · moneda: los ADR (TSM, NVO, ASML) con los estados convertidos y múltiplos coherentes;
    sin tipo de cambio, el análisis se rechaza (422) en vez de mezclar monedas;
  · clase de acciones: BRK-B con BPA y acciones en la clase B;
  · plausibilidad: P/E, P/B y BPA × acciones fuera de rango se marcan inválidos;
  · UTILITY: NEE y DUK con su rama (deuda neta/EBITDA y dividendo; FCF, DCF, Altman y D/E no aplican);
  · DCF: nunca un valor razonable negativo ("no significativo");
  · ETF: SPY rechazado con un mensaje claro.
"""
import os
import re

import pytest
from fastapi import HTTPException

import fixture_backend as fb
import invariants as inv

SAMPLE_DIR = fb.fixtures_dir(fb.SAMPLE_ENV)
pytestmark = pytest.mark.skipif(not os.path.isdir(SAMPLE_DIR), reason="sin fixtures de la muestra")

BAD_SIGN = re.compile(r"\$\s*[-−]")


@pytest.fixture(scope="module")
def sample():
    """{ticker: análisis | HTTPException} de la muestra, desde los fixtures."""
    out = {}
    with fb.replay(SAMPLE_DIR) as store:
        for sym in fb.SAMPLE_TICKERS:
            try:
                out[sym] = fb.run_analysis(sym, store)
            except HTTPException as e:
                out[sym] = e
        assert not store.misses, store.misses
    return out


def _ok(sample):
    return {s: a for s, a in sample.items() if not isinstance(a, HTTPException)}


# ── 7. textos ──
def test_visible_text_has_no_archetype_codes_nor_sign_after_symbol(sample, outputs_by_env):
    """Recorre el texto visible (display, que pintan la web y el PDF) y el texto del PDF de
    toda la muestra y de los 12 juegos con golden."""
    analyses = [(f"muestra/{s}", a) for s, a in _ok(sample).items()]
    pdfs = []
    for env in fb.available_envs():
        for sym, (a, pdf) in outputs_by_env(env).items():
            analyses.append((f"{env}/{sym}", a))
            pdfs.append((f"{env}/{sym}", fb.pdf_text(pdf)))
    for name, a in _ok(sample).items():
        pdfs.append((f"muestra/{name}", fb.pdf_text(fb.build_pdf_bytes(a, fb.capture_date(
            {"captured_at_local": "2026-10-13T12:00:00"})))))
    bad = []
    for name, a in analyses:
        try:
            inv.no_archetype_codes_nor_sign_after_symbol(a, "")
        except AssertionError as e:
            bad.append(f"{name} {e}")
    for name, txt in pdfs:
        # En el PDF el código solo puede ir en la línea del detalle técnico de la clasificación.
        try:
            inv.no_archetype_codes_nor_sign_after_symbol({"display": {}}, txt)
        except AssertionError as e:
            bad.append(f"{name} {e}")
    assert not bad, "\n".join(bad[:30])


# ── 1. moneda ──
@pytest.mark.parametrize("sym,cur", [("TSM", "TWD"), ("NVO", "DKK"), ("ASML", "EUR")])
def test_adr_statements_converted_to_price_currency(sample, sym, cur):
    a = sample[sym]
    c = a["data_provenance"]["currency"]
    assert c["statements"] == cur and c["price"] == "USD" and c["converted"] is True
    assert c["fx_symbols"] == [f"{cur}=X"] and c["rates"] and c.get("ttm_rate") and c.get("balance_rate")
    assert a["display"]["cover"]["currency_note"] and f"{cur} convertidos a USD" in a["display"]["cover"]["currency_note"]
    km = a["key_metrics"]
    # Múltiplos en una sola moneda: un P/E de ADR entre 5x y 80x y un DCF del orden del precio.
    assert 5 < km["pe"] < 80, km["pe"]
    fv = (a.get("dcf") or {}).get("fair_value")
    assert fv is None or 0 < fv < 5 * a["price"], fv
    # BPA × acciones (clase de la cotización) ≈ beneficio neto convertido (misma moneda y clase).
    eps, shares, ni = a["price"] / km["pe"], km["market_cap"] / a["price"], km["net_income"]
    assert abs(eps * shares - ni) / abs(ni) < 0.3, (eps, shares, ni)


def test_tsm_per_share_figures_per_adr(sample):
    """TSM: 1 ADR = 5 acciones ordinarias. El balance cuenta ordinarias; el BPA, por ADR."""
    a = sample["TSM"]
    sc = a["data_provenance"]["currency"]["share_class"]
    assert sc["applied"] and abs(sc["factor"] - 5) < 0.05
    assert "5.00 acciones de los estados" in a["display"]["cover"]["currency_note"]
    assert 20 < a["key_metrics"]["pe"] < 50 and 3 < a["key_metrics"]["pb"] < 30


def test_missing_fx_rejects_instead_of_mixing(monkeypatch):
    import currency
    import main

    def _no_fx(fin, px, _cls):
        raise currency.CurrencyConversionError(f"Yahoo no devolvió el tipo de cambio {fin}=X")
    monkeypatch.setattr(currency, "fetch_fx", _no_fx)
    with fb.replay(SAMPLE_DIR) as store:
        with pytest.raises(HTTPException) as ei:
            fb.run_analysis("TSM", store)
    assert ei.value.status_code == 422
    assert "TWD=X" in ei.value.detail and "no mezcla monedas" in ei.value.detail
    del main


# ── 2. clases de acciones y plausibilidad ──
def test_brk_b_per_share_in_class_b(sample):
    a = sample["BRK-B"]
    sc = a["data_provenance"]["currency"]["share_class"]
    assert sc["applied"] and sc["factor"] < 0.01          # los estados cuentan acciones A
    km = a["key_metrics"]
    assert 5 < km["pe"] < 50 and 0.5 < km["pb"] < 5, (km["pe"], km["pb"])
    assert "títulos cotizados" in a["display"]["cover"]["currency_note"]


def test_plausibility_rule_marks_impossible_per_share_values():
    import validate
    base = {"currentPrice": 500.0, "sharesOutstanding": 2.0e9, "_eps_net_income": 8.0e10, "_provenance": {},
            "_data_path": "yahoo_quotesummary"}
    # BPA de otra clase: P/E < 1.
    info = validate.validate_info({**base, "trailingEps": 59_000.0, "trailingPE": 0.0085}, "X")
    assert info["trailingEps"] is None and info["trailingPE"] is None
    assert {f["rule"] for f in info["_validation"]} >= {"pe_implausible"}
    # BPA × acciones lejos del beneficio (factor 5: ADR sin reexpresar).
    info = validate.validate_info({**base, "trailingEps": 8.0}, "X")
    assert info["trailingEps"] is None and info["_validation"][0]["rule"] == "bpa_incoherente"
    # Coherente: no se toca.
    info = validate.validate_info({**base, "trailingEps": 40.0}, "X")
    assert info["trailingEps"] == 40.0 and not info["_validation"]
    # P/B imposible (valor en libros por acción de otra clase).
    info = validate.validate_info({**base, "trailingEps": 40.0, "bookValue": 522_000.0,
                                   "_yahoo_ratios": {"priceToBook": 0.001}}, "X")
    assert info["bookValue"] is None and info["_yahoo_ratios"]["priceToBook"] is None
    assert all(f["action"] == "invalido" for f in info["_validation"])


# ── 4. UTILITY ──
@pytest.mark.parametrize("sym", ["NEE", "DUK"])
def test_utility_branch(sample, sym):
    a = sample[sym]
    assert a["classification"]["archetype"] == "UTILITY" and a["classification"]["label"] == "Utility regulada"
    na = set(a["display"]["na_keys"])
    assert {"altman", "de", "dcf", "fcf", "fcf_to_ni", "p_fcf"} <= na
    assert a["dcf_status"]["state"] == "no_aplica" and not (a.get("dcf") or {}).get("fair_value")
    sol = {x["metric"]: x for x in a["score"]["breakdown"]["Solidez Financiera"]["adjustments"]}
    assert "utility" in sol["Deuda neta/EBITDA"]["reason"] and "Altman Z-Score" not in sol and "Deuda/Equity" not in sol
    val = {x["metric"] for x in a["score"]["breakdown"]["Valoración"]["adjustments"]}
    assert "Rentabilidad por dividendo (utility)" in val and "P/FCF" not in val and "DCF (upside)" not in val


# ── 3. DCF ──
def test_dcf_never_negative_fair_value(sample, outputs_by_env):
    allv = list(_ok(sample).items()) + [(f"{e}/{s}", o[0]) for e in fb.available_envs()
                                        for s, o in outputs_by_env(e).items()]
    for name, a in allv:
        inv.dcf_never_negative_fair_value(a, None)
    amzn = sample["AMZN"]   # FCF TTM <= 0 en la captura: no significativo, no "sin dato"
    assert amzn["dcf_status"]["state"] == "no_significativo" and "no es significativo" in amzn["dcf_status"]["reason"]


def test_dcf_negative_equity_is_not_significant(monkeypatch):
    """La deuda neta se come el valor de la empresa: sin valor razonable ni grid."""
    import validate
    orig = validate.validate_info

    def _heavy_debt(info, symbol=""):
        info = orig(info, symbol)
        info["totalDebt"] = (info.get("marketCap") or 0) * 50
        return info
    monkeypatch.setattr(validate, "validate_info", _heavy_debt)
    with fb.replay(SAMPLE_DIR) as store:
        a = fb.run_analysis("KO", store)
    assert a["dcf_status"]["state"] == "no_significativo", a["dcf_status"]
    assert a["dcf"]["fair_value"] is None and not a.get("sensitivity")
    row = next(r for r in a["display"]["sections"]["valuation"]["intrinsic"]["rows"] if r["key"] == "dcf_fair_value")
    assert row["state"] == "no_significativo"


# ── 6. ETF ──
def test_etf_rejected_with_clear_message(sample):
    e = sample["SPY"]
    assert isinstance(e, HTTPException) and e.status_code == 422
    assert "Finanzer analiza acciones individuales" in e.detail and "ETF" in e.detail


def test_sensitivity_grid_sign_before_symbol(sample):
    """La muestra no trae celdas negativas: se inyectan para cubrir el formato ("−$8", no "$-8")."""
    import copy
    import main
    import numfmt
    from display import build_display
    assert (numfmt.whole(-8.4), numfmt.whole(-0.3), numfmt.whole(142.6), numfmt.whole(None)) == ("−$8", "$0", "$143", "—")
    a = copy.deepcopy(sample["PFE"])
    assert a.get("sensitivity", {}).get("matrix"), "PFE debería tener grid"
    a["sensitivity"]["matrix"][0][0] = -8.0
    cells = [c["value"] for r in build_display(a, main._pdf_benchmark(a))["sections"]["valuation"]["sensitivity"]["rows"]
             for c in r["cells"]]
    assert "−$8" in cells and not any(BAD_SIGN.search(c) for c in cells)


def test_source_failure_in_instrument_check_is_not_a_500(monkeypatch):
    """Un símbolo inexistente hace fallar a la fuente (yfinance: KeyError en fast_info). La
    comprobación de ETF no debe convertirlo en un 500: sigue el camino normal (404)."""
    import main
    import yf_adapter

    def _boom(_sym):
        raise KeyError("currency")
    monkeypatch.setattr(yf_adapter, "get_ticker_info", _boom)
    monkeypatch.setattr(main.data_service, "get_complete_analysis_data", lambda _s: {})
    with pytest.raises(HTTPException) as ei:
        main._compute_analysis("ZZZQX")
    assert ei.value.status_code == 404


# ── 11b (2): UTILITY con bandas propias de cobertura de intereses ──
@pytest.mark.parametrize("sym", ["NEE", "DUK"])
def test_utility_interest_coverage_bands(sample, sym):
    sol = {x["metric"]: x for x in sample[sym]["score"]["breakdown"]["Solidez Financiera"]["adjustments"]}
    ic = sol["Cobertura Intereses"]
    assert "para una utility" in ic["reason"] and ic["adjustment"] == 0   # 2.3x: en línea (≥ 2.0x)


# ── 11b (3): filas IFRS ──
def test_ifrs_operating_cash_flow_alias_asml(sample):
    a = sample["ASML"]
    aliases = a["data_provenance"]["currency"]["row_aliases"]["cashflow"]
    assert "Operating Cash Flow ← Cash Flow From Continuing Operating Activities" in aliases
    assert a["archetype_metrics"]["fcf_maintenance"] and a["dcf_status"]["state"] == "ok"
    assert a["price_attractiveness"]["score"] is not None          # antes: precio "sin dato"
    assert not [f for f in a["data_validation"] if f["rule"] == "fila_clave_ausente"]


def test_missing_key_row_warns_by_archetype():
    import validate
    st = {"revenue": [1.0], "net_income": [1.0], "total_assets": [1.0], "stockholders_equity": [1.0],
          "operating_cash_flow": [1.0], "capital_expenditure": [-1.0], "depreciation_amortization": []}
    assert validate.missing_key_rows(st, "MATURE") == []
    flags = validate.missing_key_rows(st, "CYCLICAL")
    assert [f["field"] for f in flags] == ["_statements_fy.depreciation_amortization"]
    assert flags[0]["action"] == "aviso" and "Depreciation And Amortization" in flags[0]["reason"]


# ── 11b (4): la compresión del Forward P/E no suma en la peor banda ──
def test_forward_compression_does_not_add_in_worst_band(sample):
    adj = {x["metric"]: x for x in sample["PLTR"]["score"]["breakdown"]["Valoración"]["adjustments"]}
    f = adj["Forward P/E"]
    assert f["adjustment"] == 0 and "sigue en la peor banda" in f["reason"]
    assert "Forward P/E +0.00" in adj["Bloque de múltiplos"]["reason"]


# ── 11b (2): velocidad del plan B ──
def test_plan_b_is_not_retried_and_quote_summary_block_is_remembered(monkeypatch):
    import yf_adapter
    calls = {"qs": 0, "b": 0}

    class _R401:
        status_code = 401
        text = ""

        def json(self):
            return {}

    class _Sess:
        def get(self, url, **_k):
            calls["qs"] += "quoteSummary" in url
            return _R401()

    def _planb(sym):
        calls["b"] += 1
        return {"symbol": sym, "_data_path": "plan_b_yfinance"}   # "degradado": sin beta, forward…
    monkeypatch.setattr(yf_adapter, "_ensure_session", lambda: None)
    monkeypatch.setattr(yf_adapter, "_session", _Sess())
    monkeypatch.setattr(yf_adapter, "_refresh_crumb", lambda: None)
    monkeypatch.setattr(yf_adapter, "_fallback_yfinance", _planb)
    monkeypatch.setattr(yf_adapter, "_qs_blocked_until", 0.0)
    yf_adapter._cache.clear()
    yf_adapter.get_ticker_info("AAA")
    assert calls == {"qs": 2, "b": 1}          # dos 401 (con refresco de crumb) y un solo plan B
    yf_adapter.get_ticker_info("BBB")
    assert calls == {"qs": 2, "b": 2}          # bloqueo recordado: directo al plan B
    yf_adapter._cache.clear()
