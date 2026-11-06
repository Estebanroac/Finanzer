"""
F13 · decisiones del usuario (5-nov) y pasos 11 y 12:
- 3c, opción (a) con matiz: una cíclica sigue en «baja» y dice lo que el ciclo hizo en sus cifras;
- referencia acotada: entre el 2 % y el 3 %, se decide por su causa (margen fino, muchas pérdidas, bajo la mediana);
- SRE y Oncor: las participadas son operativas hasta su nivel recurrente; entran en la cobertura del rating;
- paso 11 (opción c): el crecimiento del DCF converge a la tasa base; ventas y BPA separados restan fiabilidad;
- paso 12: una base inflada recibe el mismo trato que una deprimida (regresión y cota inferior).
"""
import pytest

import base_rates
import industry_bench
from cost_of_capital import rating_coverage
from historical_metrics import _cap_by_bound, growth_rate
from normalize import after_tax
from settings import cfg
from valuation_confidence import cycle_evidence, dcf_reliability, stability_dimension

B = 1e9


# ── 3c: cíclicas, opción (a) con matiz ──
def _rows(nis, margins=None):
    return [{"year": 2016 + i, "net_income": v, "operating_income": 1.0,
             "operating_margin": (margins or [0.1] * len(nis))[i]} for i, v in enumerate(nis)]


def test_cyclical_stays_low_and_says_what_the_cycle_did():
    ev = cycle_evidence(_rows([100, 70, -5, 90], [0.12, 0.08, 0.01, 0.11]), "Farm & Heavy Construction Machinery")
    d = stability_dimension("CYCLICAL", {}, ev)
    assert d["level"] == "baja"
    assert "pérdidas en 2018" in d["reasons"][0]
    assert "cayó un 30% en 2017" in d["reasons"][0]
    assert "entre el 1.0% y el 12.0%" in d["reasons"][0]


def test_commodity_producer_says_so_and_a_cycle_not_seen_says_so():
    assert "materias primas" in stability_dimension("CYCLICAL", {}, cycle_evidence(_rows([1, 2, 3]), "Gold"))[
        "reasons"][0]
    d = stability_dimension("CYCLICAL", {}, cycle_evidence(_rows([1, 2, 3]), "Auto Manufacturers"))
    assert d["level"] == "baja" and "no se ha visto" in d["reasons"][0]


# ── referencia acotada: prueba por causa ──
def _col(v):
    return {"before": 0.04, "after": v, "how": "sin_empresa"}


def test_cause_test_only_acts_between_two_and_three_percent():
    assert industry_bench._cause("net_margin", _col(0.035), "Entertainment", "us", "X") is None
    assert industry_bench._cause("pe", _col(0.025), "Entertainment", "us", "X") is None


def test_thin_margin_industry_keeps_its_reference():
    c = industry_bench._cause("net_margin", _col(0.027), "Retail (General)", "us", "AMZN")
    assert c == {"bounded": False, "test": "margen_fino"}


def test_many_money_losing_firms_bound_the_reference():
    # Entretenimiento de EE. UU.: el 83 % de sus empresas pierde dinero frente al 64 % del mercado
    c = industry_bench._cause("net_margin", _col(0.024), "Entertainment", "us", "DIS")
    assert c["bounded"] and c["test"] == "muchas_perdidas"


def test_aggregate_far_below_the_peer_median_bounds_the_reference():
    # Equipos y servicios petroleros sin Halliburton: 2,2 % frente a una mediana de pares del 8,4 %
    c = industry_bench._cause("net_margin", _col(0.022), "Oilfield Svcs/Equip.", "us", "HAL")
    assert c["bounded"] and c["test"] == "bajo_la_mediana"


# ── SRE y Oncor: participadas operativas ──
def _parts(eq_net, hist):
    return {"operating_income": 3.459 * B, "revenue": 13.552 * B, "pretax": 1.575 * B, "tax": 0.649 * B,
            "net_interest": -1.325 * B, "equity_income": 0.0, "equity_income_net_of_tax": eq_net * B,
            "minority_interests": -0.445 * B, "equity_net_history": [h * B for h in hist],
            "tax_history": [(1.5 * B, 0.3 * B), (1.4 * B, 0.3 * B)]}


def test_recurrent_equity_income_is_operating():
    # SRE: Oncor 1,80 B$ en el periodo con 1,60 / 1,61 / 1,48 B$ en los ejercicios: su nivel recurrente es operativo
    at = after_tax(_parts(1.80, [1.604, 1.609, 1.481]), 2.609 * B)
    assert at["equity_net_operating"] == pytest.approx(1.604 * B)
    assert at["named_equity_net_of_tax"] == pytest.approx(0.196 * B)
    assert not at["applied"]


def test_equity_spike_without_history_is_still_trimmed():
    # FIS: 2,39 B$ por la venta de su parte de Worldpay, sin participadas en los ejercicios: sigue sin explicar
    at = after_tax(_parts(1.80, []), 2.609 * B)
    assert at["equity_net_operating"] == 0.0 and at["applied"]


def test_equity_income_enters_the_rating_coverage_when_it_weighs():
    st = lambda c, e: "ok"
    r = rating_coverage(coverage=2.2, state="ok", ebit=3.0 * B, ebit_normalized=None, interest=1.36 * B, reit=False,
                        ebitda=None, operating_cash_flow=None, depreciation=None, market_cap=50 * B, state_fn=st,
                        equity_income=1.6 * B)
    assert r["coverage"] == pytest.approx(4.6 / 1.36) and r["basis"] == "EBIT + participadas"
    small = cfg("valuation.synthetic_rating.coverage_equity_min_share") * 3.0 * B * 0.5
    r = rating_coverage(coverage=2.2, state="ok", ebit=3.0 * B, ebit_normalized=None, interest=1.36 * B, reit=False,
                        ebitda=None, operating_cash_flow=None, depreciation=None, market_cap=50 * B, state_fn=st,
                        equity_income=small)
    assert r["basis"] == "EBIT"


# ── paso 11 (opción c) ──
def test_base_rate_median_by_size_and_industry():
    m = base_rates.median_growth(400 * B, "Technology", 5)
    assert m["cell"] == "100+ · All" and m["median"] == pytest.approx(0.029)
    assert base_rates.median_growth(None, "Technology")["median"] is None


def test_revenue_and_eps_far_apart_cost_one_reliability_step():
    dcf = {"fair_value": 100.0, "value_composition": {"terminal_pct": 50.0}, "growth_rate": 0.05}
    kw = dict(dcf=dcf, sensitivity=None, price=90.0, archetype="MATURE", possible_cyclical=False, fcf_flags=[],
              fcf_source=None)
    assert dcf_reliability(**kw, growth_divergence={"revenue": 0.006, "eps": 0.211})["level"] == "media"
    assert dcf_reliability(**kw, growth_divergence={"revenue": 0.05, "eps": 0.08})["level"] == "alta"


# ── paso 12: base inflada ──
def test_inflated_base_uses_the_regression_and_is_a_lower_bound():
    # PFE: FCF de 29,9 B$ en 2022 (vacunas) frente a 4,8 / 9,8 / 9,9 B$ después
    r = growth_rate([9.9, 9.8, 4.8, 29.9, 14.0, 12.0], 3)
    assert r["inflated_base"] and r["method"] == "log_lineal"
    assert r["bound"]["direction"] == "inferior"


def test_lower_bound_caps_a_regression_below_it():
    r = _cap_by_bound({"value": -0.40, "bound": {"value": -0.30, "direction": "inferior"}}, short=-0.10)
    assert r["value"] == -0.10 and r["capped"]
