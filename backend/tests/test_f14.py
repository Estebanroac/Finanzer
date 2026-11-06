"""
F14 (segunda revisión externa, 6-nov-2026): pasos 2 a 11. El paso 1 está en tests/test_damodaran_erp.py.
"""
import pytest

import base_rates


def _rows(growths):
    return [{"revenue_growth": g, "gap_before": False} for g in growths]


# ── paso 2: tasa base con peso por evidencia y sin cambiar el signo ──
def test_a_decade_of_growth_weighs_the_base_rate_less():
    short = base_rates.blend(0.16, 0.03, _rows([-0.02, 0.1, 0.1, 0.1]))
    long = base_rates.blend(0.16, 0.03, _rows([0.1] * 10))
    assert short["weight"] == pytest.approx(0.5) and long["weight"] == pytest.approx(0.25)
    assert long["used"] > short["used"] and long["evidence_years"] == 10


def test_a_shrinking_company_is_never_projected_growing():
    # KHC: −2,0 % con una mediana de comparables del +4,4 % salía creciendo al +1,2 %
    b = base_rates.blend(-0.02, 0.044, _rows([0.01, -0.01, -0.02]))
    assert b["used"] == 0.0 and b["sign_kept"]
    assert base_rates.blend(-0.06, 0.02, _rows([-0.05] * 3))["used"] < 0


def test_a_gap_in_the_history_ends_the_evidence():
    rows = _rows([0.1] * 6)
    rows[3]["gap_before"] = True
    assert base_rates.blend(0.1, 0.03, rows)["evidence_years"] == 2


# ── paso 3: señales graves de la base del veredicto (techo «baja») ──
import valuation_confidence as vc  # noqa: E402

_Z = {"applicable": True, "zone": "distress", "z_score": 0.51}


def test_impairments_alone_do_not_make_the_base_grave():
    # KHC: EBIT −3,2 B$ por deterioros, normalizado +0,6 B$, rating A+: techo «media» por el Altman, no «baja»
    fr = vc.fragility_dimension("MATURE", {}, _Z, ebit_normalized=0.645e9, rating="A+")
    assert fr["level"] == "media"


def test_a_normalized_operating_loss_is_grave():
    fr = vc.fragility_dimension("MATURE", {}, None, ebit_normalized=-7.1e9)
    assert fr["level"] == "baja" and "normalizado ≤ 0" in fr["reasons"][0]
    assert vc.fragility_dimension("FINANCIAL", {}, None, ebit_normalized=-1e9)["level"] == "alta"


def test_altman_with_a_speculative_rating_is_grave():
    fr = vc.fragility_dimension("MATURE", {}, _Z, rating="B")
    assert fr["level"] == "baja" and len(fr["reasons"]) == 1
    assert vc.fragility_dimension("MATURE", {}, _Z, altman_referential=True, rating="B")["level"] == "alta"


def test_an_extreme_scoring_dcf_is_grave_and_caps_the_confidence():
    fr = vc.fragility_dimension("MATURE", {}, None, dcf_upside=2.39)
    assert fr["level"] == "baja"
    assert vc.fragility_dimension("MATURE", {}, None, dcf_upside=-1.2)["level"] == "alta"
    dims = {k: {"level": "alta", "reasons": []} for k in ("convergence", "coverage", "source", "stability")}
    assert vc.verdict_confidence({**dims, "base": fr})["level"] == "baja"


def test_only_a_dcf_that_scores_counts_as_extreme():
    import main
    assert main._dcf_upside_scoring({"fair_value": 84.6, "upside": 239.2, "reliability": {"level": "media"}}) \
        == pytest.approx(2.392)
    assert main._dcf_upside_scoring({"fair_value": 84.6, "upside": 239.2, "reliability": {"level": "baja"}}) is None
