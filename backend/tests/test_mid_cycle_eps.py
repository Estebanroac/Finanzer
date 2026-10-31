"""
F8 (auditoría externa; PM, 27-oct-2026): BPA de ciclo medio entre las medias de las dos mitades del ciclo.

Antes se leía en los dos picos de ingresos, y un pico de ventas puede ser un valle del BPA (SHEL 2015: 0,30 $ → +52 %
anual). Casos con la historia real grabada (companyfacts del juego f2b) y uno sintético con el valle en el pico.
"""
import json
import os

import pytest

import cyclicality as cy
import sec_edgar as edgar
from test_cyclicality import H

F2B = os.path.join(os.path.dirname(__file__), "fixtures", "f2b", "edgar", "companyfacts")


def _hist(cik):
    return edgar.history(json.load(open(os.path.join(F2B, f"CIK{cik:010d}.json"), encoding="utf-8")))


def test_valle_del_bpa_en_el_pico_de_ingresos():
    """Ingresos con picos en 2014, 2018 y 2022; BPA estable en ~2 salvo un valle de 0,2 justo en el pico de 2014. Pico
    a pico daba (2 / 0,2)^(1/8) − 1 = +33 % anual; con las medias de las mitades (1,55 en 2014–2017 frente a 2,0 en
    2019–2022; 2018, el central, queda fuera), +5,2 %: el valle pesa un año de cuatro, no decide."""
    rev = [100, 105, 110, 115, 120, 90, 95, 100, 130, 100, 110, 125, 150, 120, 125]
    eps = [2.0] * 15
    eps[4] = 0.2                                    # 2014: pico de ingresos, valle del BPA
    r = cy.mid_cycle_growth(H(rev, eps=eps, first=2010))
    assert [p[:4] for p in r["peaks"]] == ["2014", "2018", "2022"]
    assert abs(r["eps_cagr"] - ((2.0 / 1.55) ** (1 / 5) - 1)) < 0.002 and r["eps_method"] == "medias_de_mitades"
    old = (2.0 / 0.2) ** (1 / 8) - 1
    assert old > 0.33 and r["eps_cagr"] < 0.06
    assert r["eps_halves"]["first"][0][:4] == "2014" and r["eps_halves"]["second"][1][:4] == "2022"


def test_media_negativa_es_sin_dato():
    rev = [100, 105, 110, 115, 120, 90, 95, 100, 130, 100, 110, 125, 150, 120, 125]
    eps = [2.0] * 4 + [1.0, 1.0, 1.0, 1.0, 1.0, -9.0, 1.0, 1.0, 1.0, 2.0, 2.0]    # 2019: −9 en la 2.ª mitad
    r = cy.mid_cycle_growth(H(rev, eps=eps, first=2010))
    assert r["eps_cagr"] is None and "no es positivo" in r["eps_reason"]


@pytest.mark.parametrize("cik,lo,hi,old", [
    (1306965, 0.05, 0.15, 0.523),    # SHEL 2015–2022: media 1,31 → 1,86 (+9,2 %; antes +52,3 % desde el valle de 2015)
    (34088, -0.05, 0.02, 0.072),     # XOM 2014–2022: 4,49 → 4,19 (−1,4 %; antes +7,2 %)
])
def test_casos_reales(cik, lo, hi, old):
    r = cy.mid_cycle_growth(_hist(cik))
    assert lo < r["eps_cagr"] < hi and abs(r["eps_cagr"] - old) > 0.05


def test_fcx_sin_tasa_por_las_perdidas_del_ciclo():
    """FCX 2011–2018: la segunda mitad (2015–2018) tiene BPA medio negativo (−11,31 en 2015): sin tasa (antes −13,2 %
    entre dos años sueltos)."""
    r = cy.mid_cycle_growth(_hist(831259))
    assert r["eps_cagr"] is None and r["eps_halves"]["mean_second"] < 0
