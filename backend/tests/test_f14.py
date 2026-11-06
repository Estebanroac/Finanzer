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
