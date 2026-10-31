"""
F8 · E8 (auditoría externa del 26-oct-2026, §3 E8): la fiabilidad del DCF se juzga por sus insumos, nunca por si el
valor coincide con el precio. Parte de «alta» y cada criterio que falla resta un escalón: (1) valor terminal > 75 %
(> 85 %: baja); (2) bloque central de la tabla (g ± 2,5 pp, WACC ± 1 pp) con máximo ÷ mínimo > 2,5; (3) margen FCF de
5 ejercicios con coeficiente de variación > 0,33; (4) banderas de datos. La distancia al precio va a la convergencia.
"""
import pytest

import valuation_confidence as vc
from settings import cfg


def _sens(block, full_extra=0.0):
    """Tabla 5×5 con el caso base en el centro; el bloque central ±1 es `block` (3×3)."""
    m = [[None] * 5 for _ in range(5)]
    for i in range(5):
        for j in range(5):
            m[i][j] = 100.0 + full_extra
    for i in range(3):
        for j in range(3):
            m[i + 1][j + 1] = block[i][j]
    return {"matrix": m, "base_growth_idx": 2, "base_discount_idx": 2}


STEADY = [[90, 100, 110]] * 3


def _hist(margins):
    ends = [f"{2021 + i}-12-31" for i in range(len(margins))]
    return {"revenue": {"values": [{"fy_end": e, "value": 100.0} for e in ends]},
            "operating_cash_flow": {"values": [{"fy_end": e, "value": 100.0 * m + 10} for e, m in zip(ends, margins)]},
            "capex": {"values": [{"fy_end": e, "value": -10.0} for e in ends]}}


def _rel(price=100.0, block=STEADY, tv=60.0, margins=(0.2, 0.21, 0.19, 0.2, 0.22), flags=None, arch="MATURE"):
    return vc.dcf_reliability(dcf={"fair_value": 100.0, "value_composition": {"terminal_pct": tv}},
                              sensitivity=_sens(block), price=price, archetype=arch, possible_cyclical=False,
                              fcf_flags=[], fcf_source="yfinance_statements", history_fy=_hist(list(margins)),
                              data_flags=flags)


def test_price_never_changes_the_level():
    """La auditoría: MSFT, GOOGL, LIN, WMT, CAT, FCX y ASML se descartaban por quedar fuera de la tabla."""
    levels = {_rel(price=p)["level"] for p in (1.0, 50.0, 100.0, 1e4)}
    assert levels == {"alta"}
    assert _rel(price=1e4)["grid_contains_price"] is False and _rel(price=1e4)["reasons"] == []


def test_each_failing_criterion_subtracts_one_step():
    assert _rel(tv=80.0)["level"] == "media" and "valor terminal" in _rel(tv=80.0)["reasons"][0]
    wide = [[40, 100, 160]] * 3                                             # 4 veces
    assert _rel(block=wide)["level"] == "media" and "4.0 veces" in _rel(block=wide)["reasons"][0]
    assert _rel(margins=(0.29, 0.22, 0.21, 0.10, 0.11))["level"] == "media"   # KO: coeficiente de variación 0,39
    assert _rel(flags=["beneficio con pico"])["level"] == "media"
    assert _rel(tv=80.0, block=wide)["level"] == "baja"
    assert _rel(tv=90.0)["level"] == "baja"


def test_non_positive_values_in_central_block_and_margin():
    assert _rel(block=[[-5, 100, 160]] * 3)["level"] == "media"
    assert "≤ 0" in _rel(margins=(-0.1, -0.05, 0.02, -0.03, 0.01))["reasons"][0]


def test_margin_stability_needs_five_edgar_years():
    r = _rel(margins=(0.2, 0.5, 0.1))
    assert r["level"] == "alta" and r["criteria"]["fcf_margin"] is None
    assert "sin evaluar" in r["criteria"]["notes"][0]
    st = vc.fcf_margin_stability(_hist([0.291, 0.222, 0.213, 0.101, 0.11]), 5)
    assert st["cv"] == pytest.approx(0.39, abs=0.01)


def test_cyclical_never_above_media():
    assert _rel(arch="CYCLICAL")["level"] == "media"


def test_config_matches_the_audit():
    R = cfg("thresholds.dcf_reliability")
    assert (R["terminal_minus_pct"], R["central_dispersion_max"], R["fcf_margin_years"]) == (75, 2.5, 5)


# ── criterio (5): crecimiento proyectado con el margen en caída (PM, 27-oct) ──

def _hist_om(margins):
    ends = [f"{2021 + i}-12-31" for i in range(len(margins))]
    return {"revenue": {"values": [{"fy_end": e, "value": 100.0} for e in ends]},
            "operating_income": {"values": [{"fy_end": e, "value": 100.0 * m} for e, m in zip(ends, margins)]},
            "operating_cash_flow": {"values": [{"fy_end": e, "value": 30.0} for e in ends]},
            "capex": {"values": [{"fy_end": e, "value": -10.0} for e in ends]}}


def _rel5(margins, current, g=0.114):
    return vc.dcf_reliability(dcf={"fair_value": 100.0, "value_composition": {"terminal_pct": 60.0}, "growth_rate": g},
                              sensitivity=_sens(STEADY), price=100.0, archetype="MATURE", possible_cyclical=False,
                              fcf_flags=[], fcf_source="yfinance_statements", history_fy=_hist_om(margins),
                              current_margins={"operating_margin": current, "net_margin": None})


UNH = ([0.083, 0.088, 0.087, 0.081, 0.042], 0.048)     # FY2021–FY2025 de EDGAR y TTM del 26-oct


def test_unh_margin_collapse_with_projected_growth_is_low():
    """UNH: margen operativo TTM 4,8 % frente a una mediana de 8,3 % (−42 %, ≥ el doble del 20 %), 3 bajadas en 4 años,
    con el DCF creciendo al 11,4 %: fiabilidad baja (la auditoría la pone entre los veredictos no utilizables)."""
    r = _rel5(*UNH)
    assert r["level"] == "baja" and "supuesto no verificado hasta el DCF de tres impulsores" in r["reasons"][0]
    assert r["criteria"]["margin_trend"]["drop"] == pytest.approx(0.42, abs=0.01)


def test_moderate_margin_decline_subtracts_one_step():
    r = _rel5([0.20, 0.19, 0.18, 0.17, 0.16], 0.14)      # −22 % frente a la mediana (0,18), 4 bajadas
    assert r["level"] == "media" and "margen en caída" in r["reasons"][0]


def test_no_trigger_with_stable_margin_without_trend_or_without_growth():
    assert _rel5([0.20, 0.21, 0.19, 0.20, 0.22], 0.20)["level"] == "alta"          # estable
    assert _rel5([0.20, 0.10, 0.25, 0.12, 0.20], 0.12)["level"] == "alta"          # caída, pero sin 3 bajadas
    assert _rel5(*UNH, g=-0.01)["level"] == "alta"                                 # el DCF no proyecta crecimiento
