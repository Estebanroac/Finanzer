"""Fase 3 (T6): lecturas de calidad que informan y no puntúan."""
import math

import pytest

import quality_readings as qr


ST = {"inc_years": ["2025", "2024", "2023", "2022"], "cf_years": ["2025", "2024", "2023", "2022"],
      "net_income": [30.0, 25.0, 22.0, 20.0], "revenue": [100.0, 95.0, 90.0, 80.0],
      "total_assets": [200.0, 190.0, 180.0, 170.0], "stockholders_equity": [100.0, 100.0, 100.0, 100.0],
      "free_cash_flow": [25.0, 20.0, 18.0, 12.0], "stock_based_compensation": [5.0, 5.0, 5.0, 4.0],
      "ebit": [40.0, 35.0, 30.0, 25.0], "interest_expense": [2.0, 2.0, 2.5, 5.0], "interest_paid": []}


def test_dupont_identity_and_driver():
    d = qr.dupont(ST)
    c = d["current"]
    assert c["roe"] == pytest.approx(c["margin"] * c["turnover"] * c["leverage"])
    assert d["driver"] == "margin" and "ROE 30.0% = margen neto 30.0%" in d["text"]


def test_fcf_margin_trend_uses_fcf_minus_sbc():
    f = qr.fcf_margin_trend(ST)
    assert f["basis"] == "margen FCF − SBC" and f["latest"] == pytest.approx(0.20)
    assert f["oldest"] == pytest.approx(0.10) and f["direction"] == "mejora"


def test_rule_of_40_and_sbc_cost():
    r = qr.rule_of_40(0.25, 0.20)
    assert r["meets"] and math.isclose(r["value"], 0.45)
    assert qr.sbc_cost({"sbc_to_revenue": 0.02, "fcf_margin_raw": 0.3, "fcf_margin_adjusted": 0.28}) is None
    s = qr.sbc_cost({"sbc_to_revenue": 0.08, "fcf_margin_raw": 0.30, "fcf_margin_adjusted": 0.22})
    assert "del 30.0% al 22.0%" in s["text"]


def test_interest_coverage_with_ebitda_trend_and_paid_fallback():
    c = qr.interest_coverage(ST, 40.0, 50.0, 2.0)
    assert c["ebit"] == pytest.approx(20.0) and c["ebitda"] == pytest.approx(25.0)
    assert c["trend"]["direction"] == "mejora"                      # 5x -> 20x
    # Sin gasto por intereses: los intereses pagados del estado de flujos, declarados.
    st = dict(ST, interest_expense=[], interest_paid=[-4.0, -4.0])
    c = qr.interest_coverage(st, 40.0, 50.0, None)
    assert c["ebit"] == pytest.approx(10.0) and c["basis"].startswith("intereses pagados")
    # REIT: (FFO + intereses) / intereses, como segunda medida.
    c = qr.interest_coverage(ST, 40.0, 50.0, 2.0, ffo_ttm=8.0)
    assert c["ffo"] == pytest.approx(5.0) and "el FFO más los intereses, 5.0 veces" in c["text"]
    assert qr.interest_coverage(ST, 40.0, 50.0, 2.0)["ffo"] is None


def test_statements_are_crossed_by_fiscal_year_not_position():
    """Revisión de código F3 (hallazgo 8): el estado de flujos sin una columna intermedia no desalinea el margen."""
    st = {"revenue": [100.0, 90.0, 80.0], "inc_years": [2025, 2024, 2023],
          "free_cash_flow": [20.0, 8.0], "cf_years": [2025, 2023]}
    m = qr.fcf_margin_trend(st)
    assert m["series"] == [pytest.approx(0.20), pytest.approx(0.10)] and m["years"] == [2025, 2023]
