"""
Fase 3 (T1b): crecimiento en la moneda de los estados, con el efecto divisa aparte (F3_T1_PARADA1 §3; registro #25).
"""
import pytest

import archetype_metrics
import growth_currency as gc
from classify import CYCLICAL, FINANCIAL, MATURE

CUR = {"statements": "EUR", "price": "USD", "converted": True,
       "rates": {"income_stmt": {"2025-12-31": 1.13, "2024-12-31": 1.08}, "cashflow": {"2025-12-31": 1.13}}}


def test_local_undoes_the_conversion_with_the_same_rates():
    st = {"inc_ends": ["2025-12-31", "2024-12-31"], "revenue": [113.0, 108.0], "cf_ends": ["2025-12-31"],
          "free_cash_flow": [11.3], "total_assets": [500.0]}
    loc = gc.local(st, CUR)
    assert loc["revenue"] == pytest.approx([100.0, 100.0]) and loc["free_cash_flow"] == pytest.approx([10.0])
    assert loc["total_assets"] == [500.0], "solo flujos: un saldo no entra en el crecimiento"
    assert st["revenue"] == [113.0, 108.0], "no toca las filas del análisis"


def test_ul_grows_minus_3_8_in_eur_and_plus_0_5_in_usd():
    """F2b_PARADA2 §6: el tipo de cambio entra en el crecimiento medido en dólares."""
    usd = [60.0 * 1.13 * 0.962, 60.0 * 1.08]
    st = {"inc_ends": ["2025-12-31", "2024-12-31"], "revenue": usd}
    assert gc.yoy(usd) == pytest.approx(0.0065, abs=1e-3)
    assert gc.yoy(gc.local(st, CUR)["revenue"]) == pytest.approx(-0.038, abs=1e-3)
    assert gc.fx_effect(gc.yoy(usd), -0.038) == pytest.approx(0.0445, abs=1e-3)


def test_a_year_without_rate_is_missing_not_mixed():
    st = {"inc_ends": ["2025-12-31", "2023-12-31"], "revenue": [113.0, 100.0]}
    assert gc.local(st, CUR)["revenue"] == [pytest.approx(100.0), None]


def test_without_conversion_the_rows_are_the_same_object():
    st = {"revenue": [1.0]}
    assert gc.local(st, {"converted": False}) is st and gc.local(st, None) is st


def test_yoy_needs_a_positive_base():
    assert gc.yoy([1.0, 0.0]) is None and gc.yoy([1.0]) is None and gc.yoy([None, 1.0]) is None


def test_cyclical_growth_values_are_measured_on_local_rows():
    st = {"revenue": [110.0, 100.0, 100.0], "diluted_eps": [2.2, 2.0, 2.0]}
    v = archetype_metrics.growth_values(CYCLICAL, st)
    assert v["revenue_growth_normalized_raw"] == pytest.approx(0.05)
    assert v["eps_growth_normalized_raw"] == pytest.approx(0.05)


def test_financial_growth_value_and_other_archetypes():
    assert archetype_metrics.growth_values(FINANCIAL, {"revenue": [110.0, 100.0]}) == \
        {"revenue_growth_statements": pytest.approx(0.10)}
    assert archetype_metrics.growth_values(MATURE, {"revenue": [110.0, 100.0]}) == {}
