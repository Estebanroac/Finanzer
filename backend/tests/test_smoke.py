"""Tests de humo de las piezas aisladas del motor, con valores calculados a
mano. Verifican propiedades que deberían sobrevivir al rediseño, no los bugs
actuales (esos viven en test_known_bugs.py)."""
import pytest

import fixture_backend  # noqa: F401  (añade backend/ y lib/ al path)
from financial_ratios import (
    altman_z_score, calculate_score_v2, dcf_multi_stage,
    dcf_sensitivity_analysis, piotroski_f_score,
)



# ─────────────────────────── Piotroski ───────────────────────────
_PIO_GOOD = dict(
    net_income=100, roa_current=0.10, roa_prior=0.08, operating_cash_flow=150,
    long_term_debt_current=80, long_term_debt_prior=100,
    current_ratio_current=2.0, current_ratio_prior=1.5,
    shares_current=95, shares_prior=100,
    gross_margin_current=0.50, gross_margin_prior=0.40,
    asset_turnover_current=1.1, asset_turnover_prior=1.0,
)


def test_piotroski_all_criteria_pass():
    score, details, interp = piotroski_f_score(**_PIO_GOOD)
    assert score == 9 and len(details) == 9
    assert all(d.startswith("✓") for d in details)
    assert interp.startswith("Excelente")


def test_piotroski_all_criteria_fail():
    bad = dict(_PIO_GOOD, roa_current=-0.05, roa_prior=0.02, operating_cash_flow=-10,
               net_income=-5, long_term_debt_current=120, current_ratio_current=1.0,
               shares_current=110, gross_margin_current=0.30, asset_turnover_current=0.9)
    score, details, _ = piotroski_f_score(**bad)
    assert score == 0 and all(d.startswith("✗") for d in details)


def test_piotroski_no_history_is_inconclusive():
    no_hist = {k: (None if k.endswith("_prior") else v) for k, v in _PIO_GOOD.items()}
    score, _, interp = piotroski_f_score(**no_hist)
    assert score == 3  # solo ROA>0, CFO>0, CFO>NI son evaluables
    assert "no concluyente" in interp


# ─────────────────────────── Altman Z ───────────────────────────
_ALT = dict(working_capital=20, total_assets=100, retained_earnings=30, ebit=15,
            market_value_equity=120, total_liabilities=50, sales=150, book_value_equity=40)


def test_altman_original_manufacturing():
    z, zone, _, det = altman_z_score(**_ALT, sector="Industrials")
    # 1.2·0.2 + 1.4·0.3 + 3.3·0.15 + 0.6·2.4 + 1.0·1.5 = 4.095
    assert z == pytest.approx(4.095, abs=0.006)
    assert zone == "SAFE" and "Original" in det["model"]


def test_altman_z_double_prime_non_manufacturing():
    z, zone, _, det = altman_z_score(**_ALT, sector="Technology")
    # X4 = patrimonio CONTABLE / pasivo (40/50), no la capitalización (120/50):
    # 6.56·0.2 + 3.26·0.3 + 6.72·0.15 + 1.05·0.8 = 4.138
    assert z == pytest.approx(4.138, abs=0.006)
    assert zone == "SAFE" and "Z''" in det["model"] and det["X4_book_tl"] == 0.8


def test_altman_not_applicable_by_archetype():
    """Etapa 6: lo decide el arquetipo (FINANCIAL, REIT), no el nombre del sector."""
    z, zone, interp, det = altman_z_score(**_ALT, sector="Financial Services",
                                          not_applicable_reason="No aplica a FINANCIAL: prueba")
    assert z is None and zone == "N/A" and det["reason"] == "no_aplica"
    assert interp.startswith("No aplica a FINANCIAL")
    # una red de pagos (MATURE) dentro de Financial Services sí se evalúa
    z, zone, _, det = altman_z_score(**_ALT, sector="Financial Services")
    assert z is not None and "Z''" in det["model"]


def test_altman_missing_total_assets():
    z, zone, _, _ = altman_z_score(**dict(_ALT, total_assets=None), sector="Industrials")
    assert z is None and zone == "N/A"


# WACC: tests/test_cost_of_capital.py (etapa 8, WACC ponderado real).


# ─────────────────────────── DCF multietapa ───────────────────────────
def _dcf(**kw):
    base = dict(fcf=100.0, shares_outstanding=10.0, high_growth_rate=0.10,
                discount_rate=0.10, terminal_growth=0.025, decay_type="linear")
    base.update(kw)
    return dcf_multi_stage(**base)


def test_dcf_valid_and_composition_sums_to_100():
    r = _dcf()
    assert r["is_valid"] and r["fair_value_per_share"] > 0
    vc = r["value_composition"]
    assert vc["stage1_pct"] + vc["stage2_pct"] + vc["terminal_pct"] == pytest.approx(100, abs=0.2)
    assert r["fair_value_per_share"] == pytest.approx(r["equity_value"] / 10.0, abs=0.01)


def test_dcf_net_debt_bridge_reduces_equity():
    plain, levered = _dcf(), _dcf(net_debt=200.0)
    assert plain["fair_value_per_share"] - levered["fair_value_per_share"] == pytest.approx(20.0, abs=0.01)


def test_dcf_higher_discount_rate_lowers_value():
    assert _dcf(discount_rate=0.12)["fair_value_per_share"] < _dcf()["fair_value_per_share"]


@pytest.mark.parametrize("kw", [dict(fcf=-5.0), dict(fcf=None), dict(shares_outstanding=0),
                                dict(discount_rate=0.02)])
def test_dcf_invalid_inputs(kw):
    assert _dcf(**kw)["is_valid"] is False


# ─────────────────────────── Grid de sensibilidad ───────────────────────────
def test_sensitivity_grid_shape_and_monotonicity():
    s = dcf_sensitivity_analysis(fcf=100.0, shares_outstanding=10.0, current_price=50.0,
                                 base_growth_rate=0.10, base_discount_rate=0.10)
    assert s["is_valid"]
    assert s["growth_rates"] == pytest.approx([0.05, 0.075, 0.10, 0.125, 0.15])
    assert s["discount_rates"] == pytest.approx([0.08, 0.09, 0.10, 0.11, 0.12])
    m = s["matrix"]
    assert len(m) == 5 and all(len(row) == 5 for row in m)
    for row in m:  # más WACC -> menos valor
        assert all(a > b for a, b in zip(row, row[1:]))
    for col in range(5):  # más crecimiento -> más valor
        assert all(m[i][col] < m[i + 1][col] for i in range(4))
    st = s["statistics"]
    assert st["min_value"] == min(min(r) for r in m) and st["max_value"] == max(max(r) for r in m)


def test_sensitivity_base_case_is_center_cell():
    s = dcf_sensitivity_analysis(fcf=100.0, shares_outstanding=10.0, current_price=50.0,
                                 base_growth_rate=0.10, base_discount_rate=0.10)
    assert s["base_case"]["fair_value"] == s["matrix"][2][2]
    assert s["base_case"]["fair_value"] == _dcf()["fair_value_per_share"]


def test_sensitivity_invalid_fcf():
    assert dcf_sensitivity_analysis(fcf=-1.0, shares_outstanding=10.0)["is_valid"] is False


# ─────────────────────────── Score v2 ───────────────────────────
_RATIOS = dict(roe=0.22, roa=0.10, operating_margin=0.25, net_margin=0.18, roic=0.20,
               current_ratio=1.8, debt_to_equity=0.4, interest_coverage=15.0,
               pe=25.0, forward_pe=21.0, p_fcf=22.0, ev_ebitda=16.0, peg=1.5,
               fcf_yield=0.045, dividend_yield=0.01, fcf=1e9, operating_cash_flow=1.3e9,
               net_income=9e8, fcf_to_net_income=1.1, pb=6.0, payout_ratio=0.2)
_CTX = dict(sector_pe=25.0, sector_ev_ebitda=16.0, revenue_cagr_3y=0.12, eps_cagr_3y=0.14,
            total_equity=5e9, total_assets=1e10)


def test_score_v2_total_is_sum_of_categories():
    r = calculate_score_v2(_RATIOS, _CTX, z_score_value=4.0, z_score_level="SAFE",
                           f_score_value=7, sector_key="technology", real_sector="Technology", wacc=0.10)
    cats = r["categories"]
    assert len(cats) == 5
    assert all(0 <= c["score"] <= 20 and c["max_score"] == 20 for c in cats)
    assert r["score"] == sum(c["score"] for c in cats) and 0 <= r["score"] <= 100
    assert r["level"] in {"Excelente", "Favorable", "Neutral", "Precaución", "Alto Riesgo"}
    assert r["is_financial_sector"] is False and r["financial_health"] is None


def test_score_v2_financial_path():
    r = calculate_score_v2(dict(_RATIOS, debt_to_equity=8.0, roa=0.012, roe=0.15, pb=1.4), _CTX,
                           sector_key="financials", real_sector="Financial Services", archetype="FINANCIAL")
    assert r["is_financial_sector"] is True and r["financial_health"] is not None
    assert r["category_scores"]["solidez"] <= 18  # tope sin datos regulatorios


def test_score_v2_all_missing_is_neutral():
    r = calculate_score_v2({}, {}, sector_key="default")
    assert r["score"] == 50  # 5 categorías en su base neutra de 10
