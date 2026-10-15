"""
Fase 1 del plan de fiabilidad (T4): comprobación geométrica de los PDF (tests/pdf_geometry.py) en los 30 del panel
(SPY se rechaza: no hay informe) y los 6 de `local`, con su prueba de que detecta en páginas sintéticas.
"""
import io
import re

import pypdfium2 as pdfium
import pytest
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

import fixture_backend as fb
import pdf_geometry as pg
from pdf_report import M_LR, PAGE_H, PAGE_W

CASES = ([("panel", t) for t in fb.PANEL_TICKERS if t != "SPY"] if fb.panel_available() else []) + \
        [("local", t) for t in fb.TICKERS]
IDS = [f"{e}-{t}" for e, t in CASES]


@pytest.mark.parametrize("env,sym", CASES, ids=IDS)
def test_pdf_text_inside_area_and_without_overlaps(env, sym, outputs_by_env):
    bad = pg.check(outputs_by_env(env)[sym][1])
    assert not bad, "\n".join(bad[:10])


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


# ─────────────────────────── prueba de que detecta ───────────────────────────

def _page(draw):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.setFont("Helvetica", 9)
    draw(c)
    c.showPage()
    c.save()
    return buf.getvalue()


def test_clean_page_passes():
    pdf = _page(lambda c: (c.drawString(M_LR + 10, 600, "Calidad del negocio"),
                           c.drawString(M_LR + 10, 585, "Atractivo del precio")))
    assert pg.check(pdf) == []


def test_overlapping_text_fails():
    pdf = _page(lambda c: (c.drawString(M_LR + 10, 600, "Composición de las dos puntuaciones"),
                           c.drawString(M_LR + 60, 602, "Lectura del análisis encima")))
    assert any("solape" in x for x in pg.check(pdf))


def test_text_past_the_right_margin_fails():
    pdf = _page(lambda c: c.drawRightString(PAGE_W - M_LR + 30, 600, "13/20 recortado"))
    assert any("fuera del área útil" in x for x in pg.check(pdf))


def test_body_text_crossing_into_the_footer_band_fails():
    from pdf_report import M_BOT
    pdf = _page(lambda c: c.drawString(M_LR + 10, M_BOT - 3, "texto que invade el pie"))
    assert any("cruza el borde del marco" in x for x in pg.check(pdf))


def test_header_and_footer_bands_are_allowed():
    pdf = _page(lambda c: (c.drawString(M_LR, PAGE_H - 30, "FINANZER · cabecera"),
                           c.drawString(M_LR, 24, "Finanzer · pie")))
    assert pg.check(pdf) == []
