"""ROTE/ROE implícitos (preparación de la fase 3, F3_DISENO_METODO §3): lib/bank_implied.py, aislado del motor.

Es la inversa exacta del P/TBV y el P/B justificados del motor (archetype_metrics.justified_multiple): ida y vuelta
con los datos de JPM, BAC y BCS del panel. Sin red: lee los golden del panel.
"""
import json
import os

import pytest

import fixture_backend as fb
from archetype_metrics import justified_multiple
from bank_implied import implied_roe, implied_rote, rote_sensitivity
from settings import cfg

BANKS = ["JPM", "BAC", "BCS"]


def _am(t):
    path = os.path.join(fb.golden_dir(fb.PANEL_ENV), f"{t}.json")
    if not os.path.exists(path):
        pytest.skip("sin golden del panel")
    return json.load(open(path, encoding="utf-8"))["archetype_metrics"]


def test_bcs_example_from_design():
    """F3_DISENO §3: P/TBV 0.81, Ke 11.0%, g 2.5% → ROTE implícito ≈ 9.4%."""
    r = implied_rote(0.81, 0.110, 0.025)
    assert r["state"] == "ok"
    assert r["value"] == pytest.approx(0.09385, abs=1e-12)
    assert round(r["value"], 3) == 0.094


@pytest.mark.parametrize("t", BANKS)
def test_round_trip_with_engine_justified_multiples(t):
    """implied_rote(P/TBV justificado del motor) = ROTE que usó el motor; igual con P/B y ROE."""
    am = _am(t)
    ke, g = am["cost_of_equity"], am["terminal_growth"]
    assert implied_rote(am["ptbv_justified"], ke, g)["value"] == pytest.approx(am["rote"], abs=1e-12)
    assert implied_roe(am["pb_justified"], ke, g)["value"] == pytest.approx(am["roe_fy"], abs=1e-12)


@pytest.mark.parametrize("t", BANKS)
def test_implied_from_market_multiple_inverts_back(t):
    """Con el P/TBV de mercado, el ROTE implícito justifica exactamente ese P/TBV."""
    am = _am(t)
    ke, g = am["cost_of_equity"], am["terminal_growth"]
    rote = implied_rote(am["ptbv"], ke, g)["value"]
    assert justified_multiple(rote, ke, g) == pytest.approx(am["ptbv"], rel=1e-12)
    # cotiza por debajo de su justificado ⇔ el precio descuenta menos ROTE del que obtiene
    assert (am["ptbv"] < am["ptbv_justified"]) == (rote < am["rote"])


@pytest.mark.parametrize("fn", [implied_rote, implied_roe])
@pytest.mark.parametrize("multiple,ke,g", [
    (0.8, 0.025, 0.025),    # Ke = g
    (0.8, 0.02, 0.025),     # Ke < g
    (0.0, 0.11, 0.025),     # múltiplo 0
    (-0.5, 0.11, 0.025),    # múltiplo negativo (patrimonio tangible negativo)
    (None, 0.11, 0.025),
    (0.8, None, 0.025),
])
def test_not_applicable(fn, multiple, ke, g):
    r = fn(multiple, ke, g)
    assert r["state"] == "no_aplica" and r["value"] is None and r["reason"]


def test_sensitivity_default_steps_around_implied():
    r = rote_sensitivity(0.81, 0.110, 0.025)
    deltas = cfg("valuation.bank_implied.rote_sensitivity_deltas")
    assert [row["delta"] for row in r["rows"]] == list(deltas)
    center = next(row for row in r["rows"] if row["delta"] == 0)
    assert center["ptbv_justified"] == pytest.approx(0.81)
    js = [row["ptbv_justified"] for row in r["rows"]]
    assert js == sorted(js)
    # +2 pp de ROTE (11.385%) justificaría (0.11385 − 0.025) / 0.085 ≈ 1.045x
    assert r["rows"][-1]["ptbv_justified"] == pytest.approx((0.09385 + 0.02 - 0.025) / 0.085)


def test_sensitivity_around_bank_rote_and_below_g():
    r = rote_sensitivity(0.81, 0.110, 0.025, deltas_pp=[-0.05, 0.0, 0.02], rote_center=0.06)
    assert r["center"] == 0.06
    assert r["rows"][0]["ptbv_justified"] is None           # ROTE 1% ≤ g: Gordon no da múltiplo
    assert r["rows"][2]["ptbv_justified"] == pytest.approx((0.08 - 0.025) / 0.085)


def test_sensitivity_not_applicable_propagates():
    r = rote_sensitivity(0.81, 0.02, 0.025)
    assert r["state"] == "no_aplica" and r["rows"] == [] and r["implied_rote"] is None
