"""
F9 · R7 (revisión externa de NU, errores menores):

- «Posible cíclica» por la oscilación del crecimiento de ingresos exige algún año con caída: la desaceleración de un
  hipercrecimiento (NU: de +182 % a +37 %) no es un ciclo.
- La estabilidad del ROE no mide el paso de pérdidas a ganancias: se mide desde entonces y se dice; con menos de 3
  ejercicios con beneficio no se evalúa y no resta. Una pérdida entre años con beneficio sí cuenta.
- El Rf se rotula con su fuente y fecha (el par Rf–ERP de Damodaran) y el ^TNX del día, para que no se lea como el
  bono del día (5,29 % frente al 5,00 % que citó el revisor).
"""
import pytest

from archetype_metrics import _roe_stability
from classify import classify


def _st(revenue, op_income):
    return {"revenue": revenue, "operating_income": op_income, "total_assets": []}


def _alerts(st):
    c = classify(sector="Financial Services", industry="Banks - Regional", eps_ttm=1.0, net_margin_ttm=0.27,
                 statements_fy=st)
    return [a["code"] for a in c["alerts"]]


def test_hypergrowth_slowdown_is_not_possible_cyclical():
    """Más reciente primero: +37 %, +67 %, +70 %, +182 %; margen constante."""
    rev = [11.0, 8.0, 4.8, 2.82, 1.0]
    assert _alerts(_st(rev, [r * 0.2 for r in rev])) == []


def test_a_fall_still_makes_it_possible_cyclical():
    rev = [11.0, 8.0, 9.5, 4.0, 1.0]                     # una caída (9,5 → 8,0)
    assert _alerts(_st(rev, [r * 0.2 for r in rev])) == ["posible_ciclica"]


NU_NI = {"2019-12-31": -92.5, "2020-12-31": -171.5, "2021-12-31": -165.0, "2022-12-31": -364.6, "2023-12-31": 1030.5,
         "2024-12-31": 1972.1, "2025-12-31": 2868.9}        # EDGAR, millones de USD


def test_roe_stability_after_turning_profitable():
    """NU: pérdidas en 2019–2022 y beneficio desde 2023 (ROE más reciente primero)."""
    nu = _roe_stability([0.28, 0.27, 0.19, -0.05], NU_NI)
    assert nu["roe_years"] == 3 and nu["roe_std_basis"] == "desde el paso a beneficios"
    assert nu["roe_std"] == pytest.approx(_roe_stability([0.28, 0.27, 0.19])["roe_std"])
    short = _roe_stability([0.15, -0.05, -0.20], {"2023-12-31": -2.0, "2024-12-31": -1.0, "2025-12-31": 1.5})
    assert short["roe_std"] is None and short["roe_std_reason"].startswith("pasó de pérdidas a beneficios hace 1 "
                                                                           "ejercicio:")


def test_a_loss_after_profits_is_volatility():
    """BRK-B: la ventana de 4 años empieza en la pérdida contable de 2022, pero en 2021 ganó: no es un paso."""
    brk = _roe_stability([0.12, 0.13, 0.10, -0.04],
                         {"2020-12-31": 42.5, "2021-12-31": 89.8, "2022-12-31": -22.8, "2023-12-31": 96.2})
    assert brk["roe_std_basis"] is None and brk["roe_years"] == 4 and brk["roe_std"] > 0.05
    assert _roe_stability([0.12, 0.13, 0.10, -0.04])["roe_std_basis"] is None      # sin historia larga, cuenta
    assert _roe_stability([0.12, -0.04, 0.11, 0.10], NU_NI)["roe_std_basis"] is None


def test_rf_is_labelled_with_its_source_and_date():
    import display as dp
    a = {"risk_free": {"value": 0.0529, "source": "par Rf–ERP de Damodaran", "as_of": "2026-10-01",
                       "market": {"value": 0.04993, "source": "^TNX", "as_of": "2026-10-27"}}}
    assert dp._rf_txt(a) == ("Rf 5.29% [Tesoro de EE. UU. a 10 años del par Rf–ERP de Damodaran, 1 de octubre de 2026; "
                             "bono a 10 años (^TNX) el 27 de octubre de 2026: 4.99%]")
    assert dp._rf_txt({"risk_free": {"value": 0.0529}}) == "Rf 5.29%"
