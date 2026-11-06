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


# ── Opción (b), decisión del usuario: el flujo que financia el crecimiento, año a año ──
import reverse_dcf as rd
from financial_ratios import dcf_multi_stage


def test_reinvestment_lowers_the_value_and_fades_with_growth():
    base = dict(fcf=100.0, shares_outstanding=10.0, high_growth_rate=0.20, discount_rate=0.10, terminal_growth=0.025)
    plain = dcf_multi_stage(**base)["fair_value_per_share"]
    paid = dcf_multi_stage(**base, reinvestment_roic=0.25)
    assert paid["fair_value_per_share"] < plain and paid["inputs"]["reinvestment_roic"] == 0.25
    # el valor terminal reinvierte g terminal ÷ min(ROIC, WACC) (25 %), no el 80 % del crecimiento inicial: en la fase
    # estable la inversión nueva rinde su coste de capital
    tv = paid["stages"]["terminal"]["terminal_value"]
    plain_tv = dcf_multi_stage(**base)["stages"]["terminal"]["terminal_value"]
    assert abs(tv / plain_tv - (1 - 0.025 / 0.10)) < 1e-5     # redondeo a 2 decimales del modelo


def test_direct_and_reverse_share_the_reinvestment():
    """El inverso resuelve con la misma estructura: con el g del directo recupera su valor."""
    d = dcf_multi_stage(fcf=100.0, shares_outstanding=1.0, high_growth_rate=0.12, discount_rate=0.09,
                        terminal_growth=0.025, reinvestment_roic=0.30)
    v = rd.equity_value_per_share(0.12, 100.0, 0.09, 0.025, 10, 6, 0.0, roic=0.30)
    assert abs(v - d["fair_value_per_share"]) < 0.02


def test_growth_that_destroys_value_cannot_reach_the_price():
    """TSLA: ROIC 5 % frente a un WACC del 11 %; crecer cuesta más de lo que rinde."""
    r = rd.implied_growth(500.0, 1.0, 0.11, net_debt_per_share=0.0, roic=0.05)
    assert r["state"] == rd.OUT_OF_RANGE and r["side"] == "superior" and "ROIC" in r["reason"]
