"""
F9 · R1b (revisión externa de NU; supuestos del PM del 27-oct): P/B justificado en dos etapas cuando el valor en libros
crece por encima de `valuation.pb_two_stage.bv_growth_threshold`. Etapa alta de N años con g₁ = mín(crecimiento
observado, ROE × retención); después g con el ROE de la industria regional de Damodaran. Sin ROE de la industria, una
etapa, declarado. Los bancos maduros no cambian.
"""
import pytest

import archetype_metrics as am
from settings import cfg

C = cfg("valuation.pb_two_stage")


def _xm(**kw):
    base = {"book_value_cagr_3y": 0.336, "roe_reference": 0.2541, "cost_of_equity": 0.108378, "terminal_growth": 0.025,
            "pb": 5.33, "pb_justified": am.justified_multiple(0.2541, 0.108378, 0.025), "rote": None}
    return {**base, **kw}


def test_two_stage_reduces_to_gordon_with_one_stage_assumptions():
    assert am.two_stage_multiple(0.2, 0.025, 5, 0.2, 0.025, 0.1) == pytest.approx(am.justified_multiple(0.2, 0.1, 0.025))
    assert am.two_stage_multiple(0.15, 0.1, 5, 0.15, 0.025, 0.1) is not None      # Ke = g₁: la otra rama


def test_nu_converges_to_the_regional_industry_roe():
    """NU (vivo, 27-oct): ROE 25,4 %, valor en libros +33,6 %, sin dividendo, Ke 10,84 %; ROE de los bancos grandes de
    emergentes 11 %. g₁ = mín(33,6 %, 25,4 % × 100 %) = 25,4 %."""
    xm = _xm()
    upd = am.apply_two_stage(xm, 0.11, None, 0.0)
    ts = upd["two_stage"]
    assert ts["applied"] and ts["g_high"] == pytest.approx(0.2541) and ts["retention"] == 1.0
    assert upd["pb_justified"] == pytest.approx(am.two_stage_multiple(0.2541, 0.2541, 5, 0.11, 0.025, 0.108378))
    assert upd["pb_justified"] < xm["pb_justified"]                 # el ROE estable de la industria pesa más
    assert upd["pb_ratio"] == pytest.approx(5.33 / upd["pb_justified"])
    assert ts["text"].startswith("dos etapas: 5 años con crecimiento del 25.4% (sin dividendo: retención 100 %), "
                                 "después ROE de la industria (11.0%)")


def test_growth_is_capped_by_roe_times_retention():
    ts = am.apply_two_stage(_xm(), 0.11, 0.4, 0.02)["two_stage"]
    assert ts["g_high"] == pytest.approx(0.2541 * 0.6) and ts["retention_basis"] == "retención 60%"


def test_mature_banks_do_not_change():
    """JPM (+10,8 % anual del valor en libros) y los bancos con crecimiento por debajo del umbral: una etapa."""
    assert C["bv_growth_threshold"] == 0.20
    assert am.apply_two_stage(_xm(book_value_cagr_3y=0.108), 0.1286, 0.27, 0.02) == {}


def test_without_industry_roe_one_stage_declared():
    upd = am.apply_two_stage(_xm(), None, None, 0.0)
    assert set(upd) == {"two_stage"} and not upd["two_stage"]["applied"]
    assert "una sola etapa" in upd["two_stage"]["reason"]
