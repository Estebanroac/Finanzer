"""
F13 · paso 9 (revisión de 110 empresas, patrón 2): la intensidad inversora (capex frente a la D&A y al flujo
operativo de varios ejercicios) decide si una empresa está en expansión; en expansión el DCF enseña también la lectura
con el flujo de mantenimiento. Cifras aproximadas del banco congelado del 5-nov-2026 (miles de millones).
"""
import archetype_metrics as am


def _st(capex, da, ocf):
    return {"capital_expenditure": [-c for c in capex], "depreciation_amortization": da, "operating_cash_flow": ocf}


def test_intensity_sums_the_last_years():
    r = am.investment_intensity(_st([70, 39, 28, 30], [18, 15, 11, 9], [115, 91, 71, 50]))
    assert r["years"] == 3 and abs(r["ratio"] - 137 / 44) < 1e-9 and abs(r["to_ocf"] - 137 / 277) < 1e-9


def test_accelerating_investment_counts_with_the_ttm():
    """META: capex 3 veces la D&A, ~50 % del flujo en tres años pero 78 % en el TTM."""
    r = am.investment_intensity(_st([70, 39, 28], [18, 15, 11], [115, 91, 71]))
    assert not am.expansion(r, 0.45) and am.expansion(r, 0.78)


def test_low_capex_to_cash_flow_is_not_expansion():
    """KO: capex 1,85 veces su D&A (pequeña tras refranquiciar), pero el 12 % del flujo operativo."""
    assert not am.expansion(am.investment_intensity(_st([2.0, 1.9, 1.5], [1.1, 1.0, 0.8], [13, 12, 11])), 0.12)


def test_replacing_what_it_depreciates_is_not_expansion():
    """VZ: invierte lo que amortiza (1,1 veces) aunque sea más de la mitad de su flujo."""
    assert not am.expansion(am.investment_intensity(_st([17, 17, 18], [17.5, 17, 16.5], [37, 36, 37])), 0.5)


def test_without_enough_years_there_is_no_reading():
    r = am.investment_intensity(_st([70, 39], [18, 15], [115, 91]))
    assert r["ratio"] is None and not am.expansion(r, 0.9)
