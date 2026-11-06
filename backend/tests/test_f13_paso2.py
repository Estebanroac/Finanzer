"""
F13 · paso 2 (revisión de 110 empresas, patrón 3): la cobertura con la que se busca el rating sintético
(cost_of_capital.rating_coverage). Cifras de los casos verificados (banco congelado del 5-nov-2026).
"""
import cost_of_capital as cc
from financial_ratios import interest_coverage_state


def _state(net_debt=1e9):
    return lambda c, e: interest_coverage_state(c, net_debt, ebit=e, net_interest_income=None)


def _rc(**kw):
    base = dict(coverage=None, state=None, ebit=None, ebit_normalized=None, interest=None, reit=False, ebitda=None,
                operating_cash_flow=None, depreciation=None, market_cap=50e9, state_fn=_state())
    base.update(kw)
    return cc.rating_coverage(**base)


def _rating(r, mcap=50e9):
    return cc.synthetic_rating(r["coverage"], mcap, r["state"])["rating"]


def test_reported_ebit_stays_when_nothing_distorts_it():
    r = _rc(coverage=6.3, state="ok", ebit=17.0e9, ebit_normalized=17.0e9, interest=2.7e9)
    assert r["basis"] == "EBIT" and r["coverage"] == 6.3 and r["reason"] is None


def test_normalized_ebit_lifts_an_impairment_out_of_the_rating():
    """APD: EBIT −0,59 B$ por cancelar proyectos (rating D, WACC 20 %); normalizado 1,77 B$."""
    r = _rc(coverage=-2.68, state="negativa", ebit=-0.59e9, ebit_normalized=1.77e9, interest=0.22e9)
    assert r["basis"] == "EBIT normalizado" and _rating(r) not in ("D", "C", "CC", "CCC")
    assert r["reported"]["coverage"] == -2.68


def test_reit_uses_ebitda():
    """WELL: el EBIT de un REIT lo hunde la depreciación inmobiliaria (CC, Ke 18,5 %)."""
    r = _rc(coverage=0.76, state="ok", ebit=1.0e9, interest=1.3e9, reit=True, ebitda=4.9e9)
    assert r["basis"] == "EBITDA" and _rating(r) not in ("D", "C", "CC", "CCC")


def test_default_rating_with_positive_cash_is_incoherent_and_uses_cash_coverage():
    """KHC: aun normalizado, el EBIT apenas cubre los intereses (0,65 frente a 0,68 B$) con 4,6 B$ de caja operativa."""
    r = _rc(coverage=-4.65, state="negativa", ebit=-3.18e9, ebit_normalized=0.65e9, interest=0.68e9,
            operating_cash_flow=4.62e9, depreciation=0.95e9)
    assert r["basis"] == "caja operativa" and "incoherente" in r["reason"]
    assert _rating(r) not in ("D", "C", "CC", "CCC")


def test_no_cash_no_rescue():
    """Un impago con caja operativa negativa sigue siendo impago."""
    r = _rc(coverage=-1.0, state="negativa", ebit=-1e9, interest=1e9, operating_cash_flow=-0.5e9, depreciation=0.3e9)
    assert _rating(r) == "D"


def test_net_cash_rule_survives():
    """MRNA: EBIT < 0 con caja neta sigue en el tramo de caja neta (no D): el estado se recalcula con la regla M."""
    r = _rc(coverage=-79.0, state="no_significativo", ebit=-3.2e9, ebit_normalized=-3.0e9, interest=0.04e9,
            state_fn=_state(net_debt=-5e9))
    assert _rating(r) == cc.synthetic_rating(None, 50e9, "no_significativo")["rating"]
