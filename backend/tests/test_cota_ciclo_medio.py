"""
Fase 1 del plan de fiabilidad (T3.4): el crecimiento de ciclo medio de una CYCLICAL está acotado por el modelo
(valuation.archetypes.cyclical_growth_bounds). En la cota no es un dato medido: el texto lo dice en lenguaje llano.
La cifra de ciclo medio no se rotula "(3 años)".
"""
import pytest

import fixture_backend as fb
from display import read_growth
from settings import cfg

LO, HI = cfg("valuation.archetypes.cyclical_growth_bounds")


def test_bound_is_said_in_plain_language():
    assert "acotado al mínimo que admite el modelo" in read_growth(LO, cycle=True)[2]
    assert "acotado al máximo que admite el modelo" in read_growth(HI, cycle=True)[2]
    assert "acotado" not in read_growth(LO + 0.01, cycle=True)[2]
    assert "acotado" not in read_growth(LO, cagr=True)[2]          # una CAGR no tiene cota


@pytest.mark.parametrize("sym", ["XOM", "DOW", "FCX", "MU", "ASML"])
def test_cyclical_texts_say_bound_and_cycle_basis(sym, outputs_by_env):
    if not fb.panel_available():
        pytest.skip("sin panel")
    a, pdf = outputs_by_env("panel")[sym]
    assert a["classification"]["archetype"] == "CYCLICAL"
    labels = [it["label"] for g in a["display"]["charts"]["comparison"]["groups"] for it in g["items"]]
    labels += [r["label"] for r in a["display"]["sections"]["growth"]["rows"]]
    assert not any("(3 años)" in x for x in labels) and any("(ciclo medio)" in x for x in labels)
    for g in (a["key_metrics"].get("revenue_cagr_3y"), a["key_metrics"].get("eps_cagr_3y")):
        if g is not None and (abs(g - LO) < 1e-12 or abs(g - HI) < 1e-12):
            assert "acotado al m" in fb.pdf_text(pdf).replace("\n", " ")
