"""Capa de validación de entrada (lib/validate.py) y trazabilidad de fuente.

Cada regla tiene un caso positivo (se dispara y deja flag) y uno negativo (no
toca un dato válido), con datos sintéticos. Al final, comprobaciones sobre los
juegos de fixtures (data_provenance / data_validation en la salida).
"""
import copy

import pytest

import validate as V


def _info(**kw):
    base = {
        "symbol": "TEST", "sector": "Technology",
        "currentPrice": 100.0, "marketCap": 1e11, "sharesOutstanding": 1e9,
        "totalRevenue": 5e10, "netIncome": 5e9, "totalAssets": 8e10,
        "operatingCashflow": 1e10, "freeCashflow": 8e9,
        "revenueGrowth": 0.10,
        "_statements_fy": {
            "inc_years": ["2025", "2024", "2023", "2022"],
            "bs_years": ["2025", "2024", "2023", "2022"],
            "cf_years": ["2025", "2024", "2023", "2022"],
            "revenue": [5e10, 4.55e10, 4.1e10, 3.7e10],
            "net_income": [5e9, 4.5e9, 4e9, 3.5e9],
            "ordinary_shares": [1e9, 1.01e9],
            "total_assets": [8e10, 7.5e10],
            "operating_cash_flow": [1e10, 9e9],
            "capital_expenditure": [-2e9, -1.8e9],
            "free_cash_flow": [8e9, 7.2e9],
        },
        "_piotroski_current": {"shares": 1e9},
        "_prior_year": {"shares": 1.01e9, "revenue": 4.55e10, "net_income": 4.5e9,
                        "asset_turnover": 0.6, "roa": 0.06, "gross_margin": 0.5},
        "_yahoo_ratios": {"grossMargins": 0.5, "profitMargins": 0.1},
    }
    for k, v in kw.items():
        base[k] = v
    return base


def _run(info):
    return V.validate_info(info, "TEST")


def _flags(info, rule=None):
    return [f for f in info["_validation"] if rule is None or f["rule"] == rule]


# ─────────────────────────── política general ───────────────────────────
def test_clean_input_produces_no_flags_and_no_changes():
    info = _info()
    before = copy.deepcopy(info)
    _run(info)
    assert info["_validation"] == []
    for k in before:
        assert info[k] == before[k], k


def test_thresholds_live_in_a_single_dict():
    assert isinstance(V.THRESHOLDS, dict) and len(V.THRESHOLDS) >= 5
    assert V.THRESHOLDS["margin_min"] == -10.0 and V.THRESHOLDS["margin_max"] == 1.0


def test_validation_is_rerun_safe():
    info = _info(freeCashflow=2e10)
    _run(info)
    _run(info)  # segunda pasada: ya corregido, sin flags nuevos acumulados
    assert info["_validation"] == []


# ─────────────────────────── bug d: FCF <= OCF ───────────────────────────
def test_fcf_above_ocf_is_recalculated_from_cash_flow_statement():
    info = _run(_info(freeCashflow=2.5e10))
    assert info["freeCashflow"] == pytest.approx(1e10 - 2e9)
    (f,) = _flags(info, "fcf_le_ocf")
    assert f["action"] == "recalculado" and f["old"] == 2.5e10
    assert info["_provenance"]["freeCashflow"]["source"] == "recalculado_por_validacion"


def test_fcf_above_ocf_without_statements_becomes_sin_dato():
    info = _info(freeCashflow=2.5e10)
    info["_statements_fy"] = {}
    _run(info)
    assert info["freeCashflow"] is None
    assert _flags(info, "fcf_le_ocf")[0]["action"] == "sin_dato"
    assert info["_provenance"]["freeCashflow"]["source"] == "sin_dato"


def test_fcf_below_ocf_untouched():
    info = _run(_info(freeCashflow=9.9e9))
    assert info["freeCashflow"] == 9.9e9 and not _flags(info, "fcf_le_ocf")


# ─────────────────────────── valores imposibles ───────────────────────────
def test_non_positive_assets_recalculated_from_balance_sheet():
    info = _run(_info(totalAssets=-5.0))
    assert info["totalAssets"] == 8e10
    assert _flags(info, "valor_imposible")[0]["action"] == "recalculado"


def test_non_positive_assets_without_balance_sheet_sin_dato():
    info = _info(totalAssets=0.0)
    info["_statements_fy"]["total_assets"] = []
    _run(info)
    assert info["totalAssets"] is None and _flags(info, "valor_imposible")[0]["action"] == "sin_dato"


def test_non_positive_shares_recalculated_as_mcap_over_price():
    info = _run(_info(sharesOutstanding=0))
    assert info["sharesOutstanding"] == pytest.approx(1e9)
    assert _flags(info, "valor_imposible")[0]["action"] == "recalculado"


def test_non_positive_price_sin_dato():
    info = _run(_info(currentPrice=-1.0))
    assert info["currentPrice"] is None
    assert any(f["field"] == "currentPrice" and f["action"] == "sin_dato" for f in _flags(info))


def test_positive_values_not_flagged_as_impossible():
    assert not _flags(_run(_info()), "valor_imposible")


# ─────────────────────────── márgenes ───────────────────────────
def test_precomputed_margin_out_of_range_sin_dato():
    info = _info()
    info["_yahoo_ratios"]["profitMargins"] = 1.7     # 170%
    _run(info)
    assert info["_yahoo_ratios"]["profitMargins"] is None
    assert _flags(info, "margen_fuera_de_rango")[0]["field"] == "_yahoo_ratios.profitMargins"


def test_component_implying_impossible_margin_sin_dato():
    info = _run(_info(netIncome=-6e11))               # margen neto −1200%
    assert info["netIncome"] is None
    assert _flags(info, "margen_fuera_de_rango")[0]["field"] == "netIncome"


def test_margins_at_range_edges_are_valid():
    info = _info(netIncome=-5e11)                      # −1000% exacto
    info["_yahoo_ratios"]["grossMargins"] = 1.0        # 100% exacto
    _run(info)
    assert info["netIncome"] == -5e11 and info["_yahoo_ratios"]["grossMargins"] == 1.0
    assert not _flags(info, "margen_fuera_de_rango")


# ─────────────────────────── unidades ───────────────────────────
def test_dividend_yield_in_percent_recalculated_from_rate():
    info = _run(_info(dividendYield=2.5, dividendRate=2.5))
    assert info["dividendYield"] == pytest.approx(0.025)
    assert _flags(info, "unidades")[0]["action"] == "recalculado"


def test_dividend_yield_in_percent_without_rate_sin_dato():
    info = _run(_info(dividendYield=3.0))
    assert info["dividendYield"] is None and _flags(info, "unidades")[0]["action"] == "sin_dato"


def test_growth_in_percent_scale_sin_dato():
    info = _run(_info(earningsGrowth=45.0))
    assert info["earningsGrowth"] is None and _flags(info, "unidades")


def test_decimal_units_untouched():
    info = _run(_info(dividendYield=0.03, payoutRatio=0.6, earningsGrowth=0.2))
    assert not _flags(info, "unidades")


# ─────────────────────────── bug e: crecimiento ───────────────────────────
def _old_finnhub_growth(ttm, cagr3, cagr5):
    """Copia literal de finnhub_fallback._growth antes de la etapa 3."""
    def n(v):
        try:
            return None if v is None else float(v)
        except (TypeError, ValueError):
            return None
    ttm, c3, c5 = n(ttm), n(cagr3), n(cagr5)
    lt = c5 if c5 is not None else c3
    if ttm is not None:
        if abs(ttm) <= 60 or (lt is not None and abs(ttm) <= 3 * abs(lt)):
            return ttm / 100.0
    if c3 is not None:
        return c3 / 100.0
    return None


@pytest.mark.parametrize("args", [
    (108.98, 3.4, 7.7), (24.0, 20.0, 25.0), (-70.0, -5.0, None), (150.0, 60.0, 55.0),
    (61.0, None, None), (None, 4.0, 5.0), (None, None, None), (60.0, 1.0, 1.0), ("x", "2", None),
])
def test_growth_guard_equivalent_to_previous_finnhub_rule(args):
    import finnhub_fallback
    assert V.growth_guard(*args) == _old_finnhub_growth(*args)
    assert finnhub_fallback._growth(*args) == _old_finnhub_growth(*args)


def test_growth_artifact_replaced_by_statement_cagr():
    info = _run(_info(revenueGrowth=1.09))             # 109% con CAGR ~10%
    cagr3 = (5e10 / 3.7e10) ** (1 / 3) - 1
    assert info["revenueGrowth"] == pytest.approx(cagr3)
    assert _flags(info, "crecimiento_artefacto")[0]["action"] == "recalculado"


def test_real_hypergrowth_with_matching_cagr_kept():
    info = _info(revenueGrowth=0.9)
    info["_statements_fy"]["revenue"] = [1.9e10, 1e10, 5.2e9, 2.8e9]
    _run(info)
    assert info["revenueGrowth"] == 0.9 and not _flags(info, "crecimiento_artefacto")


def test_financial_growth_incoherent_with_statements_uses_statement_yoy():
    info = _run(_info(sector="Financial Services", industry="Banks - Diversified", revenueGrowth=0.304))
    assert info["revenueGrowth"] == pytest.approx(5e10 / 4.55e10 - 1)
    assert _flags(info, "crecimiento_financiera_estados")[0]["action"] == "recalculado"


def test_financial_growth_always_from_statements_even_if_close():
    """Etapa 6 (RECON §7.8): en FINANCIAL siempre el YoY de los estados, no solo con > 15 pp."""
    info = _run(_info(sector="Financial Services", industry="Banks - Diversified", revenueGrowth=0.12))
    assert info["revenueGrowth"] == pytest.approx(5e10 / 4.55e10 - 1)
    assert _flags(info, "crecimiento_financiera_estados")


def test_payment_network_is_not_financial_for_growth():
    """Una red de pagos (MATURE) dentro de Financial Services conserva el crecimiento de la fuente."""
    info = _info(sector="Financial Services", industry="Credit Services", revenueGrowth=0.12)
    info["_statements_fy"]["total_assets"] = [1e11]       # activos/ingresos 2x: red de pagos
    _run(info)
    assert info["revenueGrowth"] == 0.12 and not _flags(info)


def test_non_financial_growth_incoherent_only_warns():
    info = _run(_info(revenueGrowth=0.499))
    assert info["revenueGrowth"] == 0.499
    assert _flags(info, "crecimiento_incoherente")[0]["action"] == "aviso"


def test_growth_coherent_with_statements_untouched():
    info = _run(_info(sector="Technology", revenueGrowth=0.12))
    assert info["revenueGrowth"] == 0.12 and not _flags(info)


# ─────────────────────────── bug c: base de splits ───────────────────────────
def test_unadjusted_prior_shares_rescaled_by_split_factor():
    info = _info(lastSplitFactor="10:1")
    info["_prior_year"]["shares"] = 4.3e8              # pre-split
    info["_piotroski_current"]["shares"] = 4.22e9
    _run(info)
    assert info["_prior_year"]["shares"] == pytest.approx(4.3e9)
    assert _flags(info, "base_de_split")[0]["action"] == "recalculado"


def test_reverse_split_factor_parsed():
    info = _info(lastSplitFactor="1:10")
    info["_prior_year"]["shares"] = 1e10
    _run(info)
    assert info["_prior_year"]["shares"] == pytest.approx(1e9)


def test_share_jump_without_matching_split_sin_dato():
    info = _info(lastSplitFactor="2:1")
    info["_prior_year"]["shares"] = 1e8                 # ×10, no lo explica un 2:1
    _run(info)
    assert info["_prior_year"]["shares"] is None
    assert _flags(info, "base_de_split")[0]["action"] == "sin_dato"


def test_same_basis_shares_untouched_even_with_recent_split():
    info = _run(_info(lastSplitFactor="10:1"))         # 1.01e9 -> 1e9, ya ajustado
    assert info["_prior_year"]["shares"] == 1.01e9 and not _flags(info, "base_de_split")


# ─────────────────────────── saltos interanuales ───────────────────────────
def test_revenue_jump_voids_prior_revenue_and_derived():
    info = _info()
    info["_statements_fy"]["revenue"] = [5e10, 5e9]    # ×10
    _run(info)
    assert info["_prior_year"]["revenue"] is None
    assert info["_prior_year"]["asset_turnover"] is None
    assert {f["field"] for f in _flags(info, "salto_interanual")} >= {
        "_prior_year.revenue", "_prior_year.asset_turnover"}


def test_net_income_jump_voids_prior_roa():
    info = _info()
    info["_statements_fy"]["net_income"] = [5e9, 1e8]  # ×50
    _run(info)
    assert info["_prior_year"]["net_income"] is None and info["_prior_year"]["roa"] is None


def test_net_income_sign_change_is_not_a_jump():
    info = _info()
    info["_statements_fy"]["net_income"] = [5e9, -1e8]
    _run(info)
    assert info["_prior_year"]["net_income"] == 4.5e9 and not _flags(info, "salto_interanual")


def test_normal_growth_is_not_a_jump():
    assert not _flags(_run(_info()), "salto_interanual")


# ─────────────────────────── múltiplos de salida ───────────────────────────
def test_negative_multiples_become_non_significant():
    res = {"key_metrics": {"pe": -12.0, "ev_ebitda": -3.0, "p_ffo": 0.0, "roe": -0.2},
           "ratios": {"pe": -12.0, "ev_ebitda": 8.0}}
    flags = V.validate_outputs(res)
    assert res["key_metrics"]["pe"] is None and res["key_metrics"]["ev_ebitda"] is None
    assert res["key_metrics"]["p_ffo"] is None
    assert res["key_metrics"]["roe"] == -0.2           # no es un múltiplo
    assert res["ratios"]["ev_ebitda"] == 8.0
    assert {f["field"] for f in flags} == {"key_metrics.pe", "key_metrics.ev_ebitda",
                                           "key_metrics.p_ffo", "ratios.pe"}
    assert all(f["rule"] == "multiplo_no_significativo" for f in flags)


def test_positive_multiples_untouched():
    res = {"key_metrics": {"pe": 20.0, "ev_ebitda": 12.0, "p_ffo": None}}
    assert V.validate_outputs(res) == [] and res["key_metrics"]["pe"] == 20.0


# ─────────────────────────── integración con los fixtures ───────────────────────────
VOCAB = {"yahoo_quotesummary", "yfinance_statements", "finnhub", "derivado",
         "recalculado_por_validacion", "sin_dato"}


@pytest.mark.parametrize("env", ["local", "prod"])
def test_provenance_block_present_and_in_vocabulary(env, outputs_by_env):
    import conftest
    if env not in conftest.ENVS:
        pytest.skip(f"falta el juego {env}")
    for sym, (a, _) in outputs_by_env(env).items():
        dp = a["data_provenance"]
        assert dp["path"] == ("yahoo_quotesummary" if env == "local" else "plan_b_yfinance"), sym
        assert dp["fields"], sym
        assert {v["source"] for v in dp["fields"].values()} <= VOCAB, sym
        assert isinstance(a["data_validation"], list)
        for f in a["data_validation"]:
            assert f["action"] in {"recalculado", "sin_dato", "aviso"} and f["reason"], (sym, f)


def test_prod_provenance_marks_finnhub_and_statements(outputs_by_env):
    import conftest
    if "prod" not in conftest.ENVS:
        pytest.skip("falta el juego prod")
    f = outputs_by_env("prod")["NFLX"][0]["data_provenance"]["fields"]
    assert f["beta"]["source"] == "finnhub"
    assert f["_prior_year.shares"]["source"] == "yfinance_statements"
    assert f["sector"]["detail"].startswith("búsqueda de Yahoo")
    assert f["forwardEps"]["source"] == "sin_dato"


def test_validation_flags_reach_the_analysis(analysis):
    """Desde la etapa 7 el FCF local de NFLX es el TTM de los estados trimestrales:
    el FCF apalancado de quoteSummary (25.4B > OCF) ya no llega a la regla d, que
    sigue cubierta con datos sintéticos (test_fcf_* de este archivo)."""
    nflx = analysis("NFLX")
    assert nflx["data_provenance"]["fields"]["freeCashflow"]["detail"].startswith("TTM: suma de los 4 trimestres")
    assert nflx["key_metrics"]["free_cash_flow"] <= nflx["key_metrics"]["operating_cash_flow"]
    snow = analysis("SNOW")
    assert snow["key_metrics"]["pe"] is None
    assert snow["data_provenance"]["fields"]["key_metrics.pe"]["rule"] == "multiplo_no_significativo"


def test_last_known_good_fill_is_marked_derivado():
    import yf_adapter
    yf_adapter._best_cache["ZZZ"] = (yf_adapter.time.time(), {"beta": 1.2, "_prior_year": {"roa": 0.1}})
    try:
        merged = yf_adapter._merge_last_known_good("ZZZ", {"beta": None, "_prior_year": {}}, True)
    finally:
        yf_adapter._best_cache.pop("ZZZ", None)
    assert merged["beta"] == 1.2
    assert merged["_provenance"]["beta"]["source"] == "derivado"
    assert merged["_provenance"]["_prior_year.roa"]["source"] == "derivado"


def test_broad_except_logs_and_marks_block_sin_dato(monkeypatch):
    import fixture_backend as fb
    import main

    def boom(*a, **kw):
        raise RuntimeError("fallo sintético")

    logged = []
    monkeypatch.setattr(main, "build_signals", boom)
    monkeypatch.setattr(main.logger, "error", lambda msg, *a, **kw: logged.append(str(msg)))
    with fb.replay(fb.fixtures_dir("local")) as store:
        a = fb.run_analysis("V", store)
    assert a["alerts"] == {"red_flags": [], "warnings": [], "strengths": []}  # flujo intacto
    errs = a["data_provenance"]["errors"]
    assert errs == [{"block": "alerts", "source": "sin_dato", "reason": "RuntimeError: fallo sintético"}]
    assert any("bloque 'alerts' sin calcular" in m for m in logged)


def test_pdf_keeps_no_earnings_reading_for_non_significant_pe(analysis, fixture_store):
    import fixture_backend as fb
    a = analysis("SNOW")
    assert a["key_metrics"]["pe"] is None
    text = fb.pdf_text(fb.build_pdf_bytes(a, fb.capture_date(fixture_store.meta["SNOW"])))
    assert "no es significativo al no haber beneficios positivos" in text
