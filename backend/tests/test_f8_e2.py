"""
F8 · E2 (auditoría externa del 26-oct-2026, §3 E2): bandera de pico de beneficio.

(a) beneficio TTM > mediana de 3 ejercicios × 1,4 y (b) forward P/E > TTM × 1,2. El forward de Yahoo solo si es
coherente (el beneficio que implica no queda por debajo de mín(TTM, mediana) / 3); si no, solo (a), declarado. Con la
bandera, el P/E del score es la media del P/E sobre la mediana y el forward (o solo el primero) y el texto lo dice.
"""
import pytest

import earnings_peak as ep
import financial_ratios as fr
from settings import cfg

# NEE con datos reales del 26-oct: TTM 11,64 mil millones (normalizado 11,58), FY2025–FY2023 6,835 / 6,946 / 7,31;
# P/E normalizado 14,85x, reportado 14,78x, forward 18,74x.
NEE = dict(ni_ttm=11.58e9, ni_reported=11.636e9, fy_net_income=[6.835e9, 6.946e9, 7.31e9, 4.147e9],
           pe_score=14.85, pe_reported=14.78, forward_pe=18.74)


def test_nee_peak_flag_with_both_conditions():
    r = ep.detect(**NEE)
    assert r["flag"] and r["conditions"] == {"a": True, "b": True} and r["forward"]["coherent"]
    assert r["median"] == 6.946e9 and r["ttm_over_median"] == pytest.approx(11.58 / 6.946 - 1)
    assert r["pe_median"] == pytest.approx(14.85 * 11.58 / 6.946)
    assert r["pe_score"] == pytest.approx((r["pe_median"] + 18.74) / 2)
    assert "beneficio TTM atípico" in r["reason"] and f"{r['pe_score']:.1f}x" in r["reason"]


def test_genuine_growth_is_not_flagged_when_the_market_believes_it():
    """NVDA (compensación de la auditoría): (a) se cumple, pero el forward P/E es menor que el TTM."""
    r = ep.detect(ni_ttm=192.9e9, ni_reported=192.9e9, fy_net_income=[120e9, 72.9e9, 29.8e9],
                  pe_score=27.3, pe_reported=27.3, forward_pe=13.6)
    assert r["conditions"] == {"a": True, "b": False} and not r["flag"] and r["pe_score"] is None


def test_without_reliable_forward_only_condition_a_and_says_so():
    r = ep.detect(**{**NEE, "forward_pe": None})
    assert r["flag"] and r["conditions"]["b"] is None and r["pe_score"] == pytest.approx(r["pe_median"])
    assert "sin forward fiable" in r["reason"] and "solo con esa condición" in r["reason"]


def test_incoherent_forward_is_not_used():
    """Un forward que implica un beneficio por debajo de mín(TTM, mediana)/3 no entra: solo (a). Uno que implica más
    que el TTM entra siempre (MU: 3,2 veces el BPA TTM) y no pone la bandera."""
    r = ep.detect(**{**NEE, "forward_pe": 14.78 * 11.636 / 1.5})      # implica 1,5 mil millones
    assert not r["forward"]["coherent"] and "por debajo de" in r["forward"]["reason"]
    assert r["flag"] and r["pe_score"] == pytest.approx(r["pe_median"])
    mu = ep.detect(ni_ttm=50.47e9, ni_reported=50.47e9, fy_net_income=[8.5e9, 0.778e9, -5.83e9],
                   pe_score=20.7, pe_reported=20.7, forward_pe=6.52)
    assert mu["forward"]["coherent"] and mu["conditions"]["b"] is False and not mu["flag"]


def test_no_flag_below_threshold_and_no_data_cases():
    assert not ep.detect(**{**NEE, "ni_ttm": 6.946e9 * 1.39})["flag"]
    assert ep.detect(**{**NEE, "fy_net_income": [6.8e9, 6.9e9]}) is None          # menos de 3 ejercicios
    assert ep.detect(**{**NEE, "fy_net_income": [-1e9, -2e9, 3e9]}) is None       # mediana ≤ 0
    assert ep.detect(**{**NEE, "ni_ttm": -1.0}) is None


def test_score_uses_the_peak_pe_and_measures_forward_compression_against_ttm():
    r = ep.detect(**NEE)
    base = dict(p_fcf=None, ev_ebitda=None, peg=None, sector_pe=21.0, archetype="MATURE", forward_pe=18.74)
    v = fr.score_valoracion(pe=r["pe_score"], earnings_peak=r, **base)
    adj = {x["metric"]: x for x in v["adjustments"]}
    assert adj["P/E frente al sector"]["value"] == f"{r['pe_score']:.2f}x" and adj["P/E frente al sector"]["earnings_peak"]
    assert "beneficio TTM atípico" in adj["P/E frente al sector"]["reason"]
    assert "(15x → 19x" in adj["Forward P/E"]["reason"]       # frente al TTM, no frente al P/E de la bandera
    v0 = fr.score_valoracion(pe=14.85, **base)
    p0 = {x["metric"]: x for x in v0["adjustments"]}["P/E frente al sector"]["adjustment"]
    assert adj["P/E frente al sector"]["adjustment"] < p0         # deja de ser «atractivo» por un TTM atípico


def test_config_is_the_audit_rule():
    C = cfg("valuation.earnings_peak")
    assert (C["ttm_over_median"], C["median_years"], C["forward_premium"]) == (0.40, 3, 0.20)


def test_annual_basis_texts_do_not_say_ttm():
    """Sin 4 trimestres consecutivos (UL), el beneficio es el del último ejercicio y el texto no dice «TTM»."""
    r = ep.detect(**NEE, period="último ejercicio")
    assert "beneficio del último ejercicio atípico" in r["reason"] and "TTM" not in r["reason"]
