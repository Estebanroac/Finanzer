"""
Fase 3 (T1b): el FFO anual de los REIT es beneficio + D&A, como el TTM (parada 1b: EBITDA = EBIT del emisor + D&A).
"""
import archetype_metrics
from classify import REIT


def test_reit_ffo_is_net_income_plus_da():
    """FFO anual = beneficio + D&A, la definición del FFO TTM (con el EBITDA del emisor, EBITDA − EBIT de Yahoo ya no
    es la D&A)."""
    st = {"net_income": [100.0, 90.0, 80.0, 70.0], "depreciation_amortization": [-50.0, -50.0, -50.0, -50.0],
          "ebitda": [999.0] * 4, "ebit": [1.0] * 4, "ordinary_shares": [10.0] * 4}
    v = archetype_metrics.compute(REIT, st, {})
    assert v["ffo_series"] == [150.0, 140.0, 130.0, 120.0]
