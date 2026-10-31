"""
F9 · R5 (revisión externa de NU, 27-oct): en bancos y aseguradoras la cobertura de intereses no aplica: ni puntúa, ni
genera riesgo, ni tiene lectura de plantilla. En vivo, NU, JPM, ITUB, HSBC y BCS decían «la cobertura de intereses
(0.8x) es críticamente baja» y CB «la deuda es fácilmente servible». La fila queda «No aplica» con el motivo.
"""
import copy
import json
import os

import pytest

import display as dp
from classify import FINANCIAL, not_applicable

GOLDEN = os.path.join(os.path.dirname(__file__), "golden", "panel")


def test_financial_coverage_is_not_applicable_with_its_reason():
    why = not_applicable(FINANCIAL, "interest_coverage")
    assert why.startswith("No aplica a bancos y aseguradoras: el gasto por intereses es parte del negocio")
    assert not_applicable(FINANCIAL, "net_debt_ebitda").startswith("No aplica a bancos y aseguradoras: su caja")


@pytest.mark.parametrize("ic,nd", [(0.83, None), (16.5, -26.7e9)])      # JPM y CB (caja neta) en vivo (27-oct)
def test_bank_display_has_no_coverage_reading(ic, nd):
    with open(os.path.join(GOLDEN, "JPM.json")) as fh:
        a = copy.deepcopy(json.load(fh))
    assert a["classification"]["archetype"] == FINANCIAL
    a["key_metrics"].update(interest_coverage=ic, interest_coverage_state="ok", net_debt=nd,
                            net_debt_to_ebitda=None if nd is None else -2.1,
                            net_debt_to_ebitda_state=None if nd is None else "no_significativo")
    d = dp.build_display(a)
    s = json.dumps(d, ensure_ascii=False)
    assert "cobertura de intereses (" not in s and "fácilmente servible" not in s and "caja neta" not in s
    rows = [r for r in d["sections"]["solvency"]["rows"] if r["label"] == "Cobertura de intereses"]
    assert rows and all(r["state"] == "no_aplica" and r["reading"] == "No aplica" for r in rows)
    assert rows[0]["text"].startswith("el gasto por intereses es parte del negocio")
    nde = [r for r in d["sections"]["solvency"]["rows"] if r["label"] == "Deuda neta / EBITDA"]
    assert all(r["state"] == "no_aplica" for r in nde)
