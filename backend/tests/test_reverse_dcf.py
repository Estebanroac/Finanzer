"""DCF inverso (preparación de la fase 3, F3_DISENO_METODO §2): lib/reverse_dcf.py, aislado del motor.

  · ida y vuelta con el DCF directo del motor (dcf_multi_stage, modo "step") en 5 tickers del panel;
  · contraste con un cálculo independiente (descuento año a año escrito aparte, otro método de raíz) en 3 casos;
  · casos límite con estado explícito, y las bandas de lectura.
Sin red: lee los golden del panel (las entradas del DCF que usó el motor).
"""
import json
import os

import pytest

import fixture_backend as fb
from financial_ratios import dcf_multi_stage, dcf_multi_stage_dynamic
from reverse_dcf import classify_implied_growth, equity_value_per_share, growth_path, implied_growth
from settings import cfg

TG = cfg("valuation.dcf.terminal_growth")
LO, HI = cfg("valuation.reverse_dcf.growth_bounds")
YEARS = cfg("valuation.dcf.high_growth_years") + cfg("valuation.dcf.transition_years")
FADE = cfg("valuation.dcf.high_growth_years") + 1

# 5 tickers del panel con DCF "ok" y crecimiento <= 15% (el motor usa decay "step": la estructura del inverso).
ROUND_TRIP = ["KO", "JNJ", "XOM", "AAPL", "PG"]
GROWTHS = [-0.15, -0.05, 0.0, 0.025, 0.06, 0.12, 0.25, 0.40, 0.50]   # 0.50 = growth_cap del DCF directo


def _inputs(t):
    path = os.path.join(fb.golden_dir(fb.PANEL_ENV), f"{t}.json")
    if not os.path.exists(path):
        pytest.skip("sin golden del panel")
    a = json.load(open(path, encoding="utf-8"))
    d, km = a["dcf"], a["key_metrics"]
    return dict(fcf=d["fcf_input"], shares=km["shares_outstanding"], wacc=d["wacc"], net_debt=km["net_debt"],
                growth=d["growth_rate"], fair_value=d["fair_value"], state=a["dcf_status"]["state"])


@pytest.mark.parametrize("t", ROUND_TRIP)
def test_inputs_reproduce_the_engine_dcf(t):
    """Las entradas leídas del golden son las que usó el motor: su DCF se reproduce al céntimo."""
    x = _inputs(t)
    assert x["state"] == "ok"
    r = dcf_multi_stage_dynamic(fcf=x["fcf"], shares_outstanding=x["shares"], wacc=x["wacc"],
                                total_debt=x["net_debt"], cash=0.0, revenue_growth_3y=x["growth"])
    assert r["decay_type"] == "step"
    assert r["fair_value_per_share"] == x["fair_value"]


@pytest.mark.parametrize("t", ROUND_TRIP)
@pytest.mark.parametrize("g", GROWTHS)
def test_round_trip_with_direct_dcf(t, g):
    """Valor del DCF directo con g → usado como precio → implied_growth recupera g (mismo modelo)."""
    x = _inputs(t)
    m = dcf_multi_stage(fcf=x["fcf"], shares_outstanding=x["shares"], high_growth_rate=g, terminal_growth=TG,
                        discount_rate=x["wacc"], decay_type="step", net_debt=x["net_debt"])
    price = m["equity_value"] / x["shares"]   # equity_value está redondeado a 0.01 en total: sin pérdida por acción
    if price <= 0:
        pytest.skip("equity ≤ 0 con este g")
    r = implied_growth(price, x["fcf"] / x["shares"], x["wacc"], net_debt_per_share=x["net_debt"] / x["shares"])
    assert r["state"] == "ok", r
    assert r["g_star"] == pytest.approx(g, abs=1e-8)
    assert r["relative_error"] <= cfg("valuation.reverse_dcf.value_tolerance")
    # las tasas año a año coinciden con las del DCF directo
    rates = m["stages"]["high_growth"]["rates"] + m["stages"]["transition"]["rates"]
    assert [round(v, 4) for v in r["growth_path"]] == pytest.approx(rates, abs=1e-12)


@pytest.mark.parametrize("t", ROUND_TRIP)
def test_engine_fair_value_gives_back_engine_growth(t):
    """El valor razonable que publicó el motor, tomado como precio, devuelve el crecimiento que usó (al céntimo)."""
    x = _inputs(t)
    r = implied_growth(x["fair_value"], x["fcf"] / x["shares"], x["wacc"], net_debt_per_share=x["net_debt"] / x["shares"])
    assert r["state"] == "ok"
    assert r["g_star"] == pytest.approx(x["growth"], abs=1e-4)   # el valor publicado está redondeado al céntimo


# ── Contraste independiente: otra escritura del modelo y otro método de raíz (secante) ──

def _independent_value(fcf0, wacc, tg, g, net_debt=0.0):
    rates = [g] * 5 + [g + (tg - g) * k / 5 for k in range(1, 6)]
    flows, f = [], fcf0
    for r in rates:
        f = f * (1 + r)
        flows.append(f)
    factors = [1.0]
    for _ in range(10):
        factors.append(factors[-1] / (1 + wacc))
    explicit = sum(cf * df for cf, df in zip(flows, factors[1:]))
    terminal = flows[-1] * (1 + tg) / (wacc - tg) * factors[10]
    return explicit + terminal - net_debt


def _independent_solve(price, fcf0, wacc, tg, net_debt=0.0):
    a, b = 0.0, 0.1
    fa, fb_ = (_independent_value(fcf0, wacc, tg, a, net_debt) - price,
               _independent_value(fcf0, wacc, tg, b, net_debt) - price)
    for _ in range(100):
        c = b - fb_ * (b - a) / (fb_ - fa)
        a, fa, b = b, fb_, c
        fb_ = _independent_value(fcf0, wacc, tg, b, net_debt) - price
        if abs(fb_) < 1e-12:
            break
    return b


HAND_CASES = [
    # (fcf por acción, wacc, g terminal, deuda neta por acción, precio)
    (5.0, 0.09, 0.025, 0.0, 120.0),
    (2.0, 0.10, 0.03, 10.0, 60.0),
    (1.0, 0.08, 0.02, 0.0, 1.0 * 1.02 / 0.06),   # precio = Gordon puro → g* = g terminal (solución analítica)
]


@pytest.mark.parametrize("fcf0,wacc,tg,nd,price", HAND_CASES)
def test_independent_contrast(fcf0, wacc, tg, nd, price):
    r = implied_growth(price, fcf0, wacc, terminal_growth=tg, years=10, fade_start=6, net_debt_per_share=nd)
    assert r["state"] == "ok"
    g_ind = _independent_solve(price, fcf0, wacc, tg, nd)
    assert r["g_star"] == pytest.approx(g_ind, abs=1e-8)
    assert _independent_value(fcf0, wacc, tg, r["g_star"], nd) == pytest.approx(price, rel=1e-8)


def test_gordon_case_is_analytic():
    r = implied_growth(1.02 / 0.06, 1.0, 0.08, terminal_growth=0.02, years=10, fade_start=6)
    assert r["g_star"] == pytest.approx(0.02, abs=1e-9)


# ── Casos límite: estado explícito, nunca un número inventado ──

@pytest.mark.parametrize("fcf", [0.0, -1.5, None])
def test_non_positive_fcf_is_not_applicable(fcf):
    r = implied_growth(50.0, fcf, 0.08)
    assert r["state"] == "no_aplica" and r["g_star"] is None and "sin flujo positivo" in r["reason"]


@pytest.mark.parametrize("wacc", [TG, TG - 0.01, None])
def test_wacc_not_above_terminal_is_not_applicable(wacc):
    r = implied_growth(50.0, 2.0, wacc)
    assert r["state"] == "no_aplica" and r["g_star"] is None


@pytest.mark.parametrize("price", [0.0, -3.0, None])
def test_no_price_is_not_applicable(price):
    assert implied_growth(price, 2.0, 0.08)["state"] == "no_aplica"


def test_out_of_range_above():
    top = equity_value_per_share(HI, 1.0, 0.08, TG, YEARS, FADE)
    r = implied_growth(top * 1.01, 1.0, 0.08)
    assert r["state"] == "fuera_de_rango" and r["side"] == "superior" and r["g_star"] is None
    assert "+60%" in r["reason"]


def test_out_of_range_below():
    bottom = equity_value_per_share(LO, 1.0, 0.08, TG, YEARS, FADE)
    r = implied_growth(bottom * 0.99, 1.0, 0.08)
    assert r["state"] == "fuera_de_rango" and r["side"] == "inferior" and r["g_star"] is None
    assert "-20%" in r["reason"]


@pytest.mark.parametrize("bound", [LO, HI])
def test_price_exactly_at_a_bound(bound):
    price = equity_value_per_share(bound, 1.0, 0.08, TG, YEARS, FADE)
    r = implied_growth(price, 1.0, 0.08)
    assert r["state"] == "ok" and r["g_star"] == bound and r["iterations"] == 0


def test_net_debt_shifts_the_answer():
    """Con deuda neta el mismo precio exige más crecimiento (puente al equity como el DCF-FCFF)."""
    a = implied_growth(40.0, 2.0, 0.09)
    b = implied_growth(40.0, 2.0, 0.09, net_debt_per_share=5.0)
    assert b["g_star"] > a["g_star"]


def test_non_monotonic_range_is_refused():
    """Si el rango admite g < −100% el valor oscila: la bisección no vale y se dice."""
    r = implied_growth(20.0, 1.0, 0.08, bounds=(-3.0, 0.5))
    assert r["state"] == "sin_convergencia" and r["g_star"] is None


def test_invalid_structure_raises():
    with pytest.raises(ValueError):
        implied_growth(20.0, 1.0, 0.08, years=10, fade_start=12)


def test_growth_path_structure():
    p = growth_path(0.20, TG, YEARS, FADE)
    assert p[:FADE - 1] == [0.20] * (FADE - 1)
    assert p[-1] == pytest.approx(TG)
    steps = [p[i] - p[i + 1] for i in range(FADE - 2, YEARS - 1)]
    assert steps == pytest.approx([steps[0]] * len(steps))   # convergencia lineal


def test_reconstructed_value_and_assumptions():
    r = implied_growth(75.0, 3.0, 0.085, net_debt_per_share=4.0)
    assert r["reconstructed_value"] == pytest.approx(75.0, rel=1e-8)
    assert r["assumptions"] == {"price": 75.0, "fcf_per_share_base": 3.0, "net_debt_per_share": 4.0, "wacc": 0.085,
                                "terminal_growth": TG, "years": YEARS, "fade_start": FADE, "bounds": [LO, HI]}
    assert 0 < r["iterations"] <= cfg("valuation.reverse_dcf.max_iterations")


# ── Lectura: bandas de F3_DISENO §2.2 ──

@pytest.mark.parametrize("g_star,achieved,band", [
    (0.02, 0.10, "barata"),
    (0.10, 0.10, "en_precio"),
    (0.15, 0.10, "en_precio"),       # justo en +5 pp: en precio
    (0.05, 0.10, "en_precio"),       # justo en −5 pp: en precio
    (0.16, 0.10, "exigente"),
    (0.04, 0.10, "barata"),
    (0.20, None, "sin_contraste"),
    (None, 0.10, "sin_dato"),
])
def test_bands(g_star, achieved, band):
    assert classify_implied_growth(g_star, achieved)["band"] == band


def test_very_demanding_with_low_base_rate():
    thr = cfg("valuation.reverse_dcf.very_demanding_base_rate")
    assert classify_implied_growth(0.30, 0.10, base_rate=thr / 2)["band"] == "muy_exigente"
    assert classify_implied_growth(0.30, None, base_rate=thr / 2)["band"] == "muy_exigente"
    assert classify_implied_growth(0.30, 0.10, base_rate=thr)["band"] == "exigente"   # tasa base razonable


def test_band_width_is_a_parameter():
    assert classify_implied_growth(0.13, 0.10, band_pp=0.02)["band"] == "exigente"
    assert classify_implied_growth(0.13, 0.10)["gap"] == pytest.approx(0.03)
