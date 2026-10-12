"""Clasificador de arquetipos (etapa 6): casos límite sintéticos y fixtures."""
import pytest

import fixture_backend as fb
from classify import (CYCLICAL, FINANCIAL, GROWTH_PRE_PROFIT, MATURE, REIT, classify, display_industry,
                      norm_industry, not_applicable)
from settings import cfg


def _st(revenue, op_income=None, total_assets=None):
    """_statements_fy sintético (más reciente primero)."""
    return {"revenue": revenue, "operating_income": op_income or [], "total_assets": total_assets or []}


GROWING = _st([150.0, 120.0, 95.0, 75.0], [-10.0, -12.0, -15.0, -14.0], [200.0])     # CAGR ~26%
STEADY = _st([110.0, 105.0, 100.0, 96.0], [22.0, 21.0, 20.0, 19.2], [150.0])        # CAGR ~4.6%


def C(sector, industry, eps=1.0, nm=0.1, st=STEADY):
    return classify(sector=sector, industry=industry, eps_ttm=eps, net_margin_ttm=nm, statements_fy=st)


# ─────────────────────────── casos límite ───────────────────────────
def test_bank():
    c = C("Financial Services", "Banks - Regional")
    assert c["archetype"] == FINANCIAL and c["rule"] == "industria_banco"
    assert c["reason"] == "Clasificada como FINANCIAL por industria Banks - Regional (banco)"


def test_bank_with_prod_em_dash():
    c = C("Financial Services", "Banks—Diversified")
    assert c["archetype"] == FINANCIAL and c["industry"] == "Banks - Diversified"


def test_insurer():
    assert C("Financial Services", "Insurance - Property & Casualty")["archetype"] == FINANCIAL
    assert C("Financial Services", "Insurance—Life")["rule"] == "industria_aseguradora"


def test_insurance_broker_is_not_an_insurer():
    c = C("Financial Services", "Insurance Brokers")
    assert c["archetype"] == MATURE and c["rule"] == "excepcion_financiera"


def test_visa_payment_network_is_mature():
    c = C("Financial Services", "Credit Services", st=_st([40.0, 36.0, 33.0, 29.0], total_assets=[99.6]))
    assert c["archetype"] == MATURE and c["rule"] == "red_de_pagos"
    assert "red de pagos (activos/ingresos 2.5x" in c["reason"]


def test_card_lender_is_financial():
    c = C("Financial Services", "Credit Services", st=_st([40.0, 36.0, 33.0, 29.0], total_assets=[480.0]))
    assert c["archetype"] == FINANCIAL and c["rule"] == "credito_con_balance" and not c["ambiguous"]


def test_credit_services_without_balance_data_is_financial_and_ambiguous():
    c = C("Financial Services", "Credit Services", st={})
    assert c["archetype"] == FINANCIAL and c["ambiguous"] and c["confidence"] == "baja"


def test_exchange_and_asset_manager_are_mature():
    assert C("Financial Services", "Financial Data & Stock Exchanges")["archetype"] == MATURE
    assert C("Financial Services", "Asset Management")["archetype"] == MATURE


@pytest.mark.parametrize("industry", ["Capital Markets", "Mortgage Finance", "Financial Conglomerates", None])
def test_ambiguous_financial_industry_is_financial_and_flagged(industry):
    c = C("Financial Services", industry)
    assert c["archetype"] == FINANCIAL and c["ambiguous"] and c["rule"] == "financiera_ambigua"
    assert c["confidence"] == "baja"


def test_reit():
    c = C("Real Estate", "REIT - Retail")
    assert c["archetype"] == REIT and c["reason"] == "Clasificada como REIT por industria REIT - Retail"
    assert C("Real Estate", "REIT—Healthcare Facilities")["archetype"] == REIT


def test_homebuilder_promoter_is_not_reit():
    c = C("Real Estate", "Real Estate - Development")
    assert c["archetype"] == CYCLICAL and "inmobiliaria no REIT" in c["reason"]


def test_real_estate_services_is_mature_not_reit():
    c = C("Real Estate", "Real Estate Services")
    assert c["archetype"] == MATURE and "inmobiliaria no REIT" in c["reason"]


def test_saas_without_profit_is_growth_pre_profit():
    c = C("Technology", "Software - Application", eps=-1.2, nm=-0.15, st=GROWING)
    assert c["archetype"] == GROWTH_PRE_PROFIT
    assert c["inputs"]["revenue_cagr_3y"] == pytest.approx((150 / 75) ** (1 / 3) - 1)
    assert "BPA TTM -1.20 <= 0" in c["reason"]


def test_saas_with_profit_is_mature():
    assert C("Technology", "Software - Application", eps=2.0, nm=0.18, st=GROWING)["archetype"] == MATURE


def test_pre_profit_without_growth_is_not_growth_pre_profit():
    c = C("Technology", "Software - Application", eps=-1.0, nm=-0.1, st=STEADY)
    assert c["archetype"] == MATURE


def test_growth_pre_profit_needs_the_real_3y_cagr():
    """Con 3 ejercicios el CAGR a 3 años no está definido: no hay proxy interanual."""
    c = C("Technology", "Software - Application", eps=-1.0, nm=-0.1, st=_st([150.0, 120.0, 95.0]))
    assert c["archetype"] == MATURE and c["inputs"]["revenue_cagr_3y"] is None
    assert "menos de 4 ejercicios" in c["inputs"]["revenue_cagr_3y_reason"]


def test_negative_margin_alone_is_enough_for_no_profit():
    c = C("Technology", "Software - Infrastructure", eps=0.5, nm=-0.02, st=GROWING)
    assert c["archetype"] == GROWTH_PRE_PROFIT and "margen neto" in c["reason"]


def test_cyclical_with_peak_profit_stays_cyclical():
    """Una cíclica en pico de beneficio sigue siendo cíclica: decide la industria."""
    peak = _st([200.0, 120.0, 90.0, 80.0], [80.0, 30.0, 9.0, 4.0])
    c = C("Technology", "Semiconductor Equipment & Materials", eps=12.0, nm=0.35, st=peak)
    assert c["archetype"] == CYCLICAL and c["alerts"] == []


BOOM_BUST = _st([37.4, 25.1, 15.5, 30.8], [9.8, 1.3, -5.4, 9.7])          # memoria: MU
STABLE = _st([34.0, 33.0, 32.9, 33.4], [9.25, 8.6, 8.1, 6.5])             # gases industriales: LIN


@pytest.mark.parametrize("industry", ["Semiconductors", "Specialty Chemicals"])
def test_conditional_cyclical_needs_volatility(industry):
    c = C("Technology", industry, eps=5.0, nm=0.2, st=BOOM_BUST)
    assert c["archetype"] == CYCLICAL and c["rule"] == "industria_ciclica_condicional"
    assert "volatilidad alta" in c["reason"]
    c = C("Basic Materials", industry, eps=5.0, nm=0.2, st=STABLE)
    assert c["archetype"] == MATURE and c["rule"] == "ciclica_condicional_estable"


def test_conditional_cyclical_without_history_stays_mature():
    c = C("Technology", "Semiconductors", eps=5.0, nm=0.2, st=_st([30.0, 25.0]))
    assert c["archetype"] == MATURE


def test_financial_mature_exceptions_confirmed():
    exc = cfg("sectors.archetypes.financial_mature_industries")
    assert "financial data & stock exchanges" in exc and "asset management" in exc


def test_mature_default():
    c = C("Consumer Defensive", "Household & Personal Products")
    assert c["archetype"] == MATURE and c["rule"] == "por_defecto" and c["confidence"] == "normal"


def test_possible_cyclical_is_only_an_alert():
    boom_bust = _st([100.0, 150.0, 90.0, 140.0], [5.0, 40.0, -10.0, 35.0])
    c = C("Industrials", "Specialty Industrial Machinery", st=boom_bust)
    assert c["archetype"] == MATURE                     # no cambia el arquetipo
    assert c["confidence"] == "baja"
    assert [a["code"] for a in c["alerts"]] == ["posible_ciclica"]


def test_possible_cyclical_needs_enough_years():
    c = C("Industrials", "Specialty Industrial Machinery", st=_st([100.0, 150.0, 90.0], [5.0, 40.0, -10.0]))
    assert c["alerts"] == []


def test_steady_trend_is_not_possible_cyclical():
    """Una mejora sostenida de margen (tendencia) no es oscilación."""
    trend = _st([180.0, 150.0, 125.0, 100.0], [54.0, 36.0, 22.5, 12.0])
    assert C("Communication Services", "Entertainment", st=trend)["alerts"] == []


def test_cyclical_list_includes_the_requested_families():
    cyc = cfg("sectors.archetypes.cyclical_industries")
    for ind in ("copper", "steel", "aluminum", "other industrial metals & mining", "oil & gas e&p",
                "oil & gas refining & marketing", "chemicals", "airlines",
                "auto manufacturers", "auto parts", "building materials"):
        assert ind in cyc
    cond = cfg("sectors.archetypes.cyclical_conditional_industries")
    assert set(cond) == {"semiconductors", "specialty chemicals"} and not set(cond) & set(cyc)


def test_industry_normalization():
    assert norm_industry("Banks—Diversified") == norm_industry("Banks - Diversified") == "banks - diversified"
    assert display_industry("REIT—Retail") == "REIT - Retail"
    assert norm_industry("Oil & Gas E&P") == "oil & gas e&p"


def test_not_applicable_reason():
    assert not_applicable(FINANCIAL, "piotroski").startswith("No aplica a FINANCIAL")
    assert not_applicable(MATURE, "piotroski") is None
    assert not_applicable(REIT, "de") is None                      # D/E sí aplica a un REIT
    assert not_applicable(REIT, "altman") == ("No aplica a REIT: el beneficio contable está distorsionado "
                                              "por la depreciación inmobiliaria")


# ─────────────────────────── fixtures ───────────────────────────
EXPECTED = {"NFLX": MATURE, "JPM": FINANCIAL, "O": REIT, "FCX": CYCLICAL, "SNOW": GROWTH_PRE_PROFIT, "V": MATURE}


def test_six_tickers_both_envs(outputs_by_env):
    import conftest
    for env in conftest.ENVS:
        for sym, (a, _) in outputs_by_env(env).items():
            c = a["classification"]
            assert c["archetype"] == EXPECTED[sym], (env, sym, c["reason"])
    assert outputs_by_env(conftest.ENVS[0])["O"][0]["classification"]["reason"] == \
        "Clasificada como REIT por industria REIT - Retail"


@pytest.mark.parametrize("sym,arch", [("TRV", FINANCIAL), ("FOR", CYCLICAL),
                                      ("NVDA", CYCLICAL), ("MU", CYCLICAL), ("LIN", MATURE), ("AMAT", CYCLICAL)])
def test_extra_local_fixtures(sym, arch):
    """Fixtures locales solo para el clasificador: TRV (aseguradora), FOR (promotora),
    NVDA y MU (Semiconductors, condicional, con volatilidad), LIN (Specialty Chemicals,
    condicional, estable) y AMAT (Semiconductor Equipment & Materials, cíclica siempre)."""
    with fb.replay(fb.fixtures_dir("local")) as store:
        a = fb.run_analysis(sym, store)
    assert a["classification"]["archetype"] == arch, a["classification"]["reason"]
