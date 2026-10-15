"""
Fase 1 del plan de fiabilidad (T3.1): el estado de la cobertura de intereses se decide con el signo del EBIT de los
estados y el del resultado financiero neto, no con el signo del cociente.

PLTR (panel): EBIT +2.63 B, ingreso financiero neto (+77.5 M por trimestre) y una cobertura de Finnhub de −1.53
(negativa porque cobra más intereses de los que paga). Antes salía "EBIT negativo y caja neta".
"""
import pytest

import fixture_backend as fb
from financial_ratios import interest_coverage_state


@pytest.mark.parametrize("ic,net_debt,ebit,nii,expected", [
    (-1.53, -9e9, 2.6e9, 2.9e8, "sin_carga"),        # EBIT > 0 e ingreso financiero neto: la deuda no es carga
    (None, -9e9, 2.6e9, 2.9e8, "sin_carga"),         # sin cobertura, mismo caso
    (-1.53, -9e9, 2.6e9, None, "sin_carga"),         # sin fila de resultado financiero: inferido del signo
    (-4.48, -4e9, -1.2e8, 1.5e8, "no_significativo"),  # EBIT < 0 con caja neta (CRWD)
    (-13.3, 4.3e7, -3.5e9, -1e8, "negativa"),         # EBIT < 0 con deuda neta (RIVN)
    (50.9, -1e9, 1.3e11, 2.5e8, "ok"),               # cobertura positiva: se lee como cobertura (MSFT)
    (-2.0, 5e8, None, None, "negativa"),             # sin EBIT: regla anterior por el signo del cociente
])
def test_interest_coverage_state_cases(ic, net_debt, ebit, nii, expected):
    assert interest_coverage_state(ic, net_debt, ebit=ebit, net_interest_income=nii) == expected


@pytest.fixture(scope="module")
def pltr(outputs_by_env):
    if not fb.panel_available():
        pytest.skip("sin panel")
    return outputs_by_env("panel")["PLTR"]


def test_pltr_has_no_interest_burden_and_never_says_negative_ebit(pltr):
    a, pdf = pltr
    km = a["key_metrics"]
    assert km["operating_income"] > 0 and km["net_interest_income"] > 0
    assert km["interest_coverage_state"] == "sin_carga"
    txt = fb.pdf_text(pdf).replace("\n", " ")
    assert "EBIT negativo" not in txt and "EBIT < 0" not in txt
    assert "sin carga financiera neta" in txt.lower()
    assert not any("EBIT < 0" in (f.get("reason") or "") for f in a["data_validation"])


def test_pltr_wacc_rating_not_by_rule_m(pltr):
    a, _ = pltr
    rating = a["wacc"]["rating"]
    assert "regla M" not in (rating.get("flag") or "") and rating["rating"] == "AAA"


def test_pltr_solidez_coverage_is_top_band(pltr):
    from settings import cfg
    a, _ = pltr
    row = next(x for x in a["score"]["breakdown"]["Solidez Financiera"]["adjustments"]
               if x["metric"] == "Cobertura Intereses")
    assert row["adjustment"] == cfg("thresholds.score.solidez.coverage_points")[0]
    assert row["value"] == "Sin carga financiera neta"


def test_crwd_keeps_negative_ebit_with_net_cash(outputs_by_env):
    if not fb.panel_available():
        pytest.skip("sin panel")
    km = outputs_by_env("panel")["CRWD"][0]["key_metrics"]
    assert km["operating_income"] < 0 and km["interest_coverage_state"] == "no_significativo"


def test_one_outlier_quarter_does_not_make_a_payer_a_net_lender(outputs_by_env):
    """NFLX (local): el TTM del resultado financiero sale +2.14 B por un trimestre atípico (2026-03, +2.85 B de
    ingresos financieros); los otros tres son negativos y el anual −604 M. "Sin carga" exige el signo en cada
    trimestre, no solo en la suma."""
    from financial_ratios import interest_coverage_state as st
    km = outputs_by_env("local")["NFLX"][0]["key_metrics"]
    assert km["net_interest_income"] > 0                     # el TTM, tal cual
    assert km["interest_coverage_state"] == "ok"
    # con la misma cifra y una cobertura ausente, el peor trimestre (negativo) impide "sin carga"
    assert st(None, 1e9, ebit=1.3e10, net_interest_income=min(km["net_interest_income"], -1.2e8)) is None
