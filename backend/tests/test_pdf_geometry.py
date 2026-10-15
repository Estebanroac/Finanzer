"""
Fase 1 del plan de fiabilidad (T4): la página 2 del PDF en los 30 del panel (SPY se rechaza: no hay informe) y los
6 de `local`.
"""
import re

import pypdfium2 as pdfium
import pytest

import fixture_backend as fb

CASES = ([("panel", t) for t in fb.PANEL_TICKERS if t != "SPY"] if fb.panel_available() else []) + \
        [("local", t) for t in fb.TICKERS]
IDS = [f"{e}-{t}" for e, t in CASES]


@pytest.mark.parametrize("env,sym", CASES, ids=IDS)
def test_page_2_holds_the_whole_summary(env, sym, outputs_by_env):
    """Cards, composición y lectura en la página 2; la sección 01 empieza en la 3 (nada se desborda)."""
    a, pdf = outputs_by_env(env)[sym]
    doc = pdfium.PdfDocument(pdf)
    p2 = " ".join(doc[1].get_textpage().get_text_bounded().split())
    p3 = doc[2].get_textpage().get_text_bounded()
    assert "COMPOSICIÓN DE LAS DOS PUNTUACIONES" in p2 and "LECTURA DEL ANÁLISIS" in p2
    last = a["display"]["summary"]["exec_items"][-1]["text"].split()[-1]
    assert last in p2, "la lectura no termina en la página 2"
    assert re.search(r"01\s+VALORACI", p3[:300])
