"""
Rediseño E5 (Task 1): base del documento del PDF nuevo (lib/pdf_v2/doc.py).

Un documento con portada, índice y 3 capítulos ficticios: índice con 3 entradas enlazadas a su página, marcadores
del lector, "↑ índice" enlazado en cada página del cuerpo, "Página x de y" exacto y geometría limpia (dentro del
área, sin solapes, letra ≥ 8 pt).
"""
import io

import pytest
from reportlab.platypus import PageBreak, Paragraph, Spacer

import pdf_geometry as pg
import pdf_inspect as pi
from pdf_v2 import doc as D
from pdf_v2 import theme as T

AREA = pg.Area(T.M_LR, T.M_TOP, T.M_BOT, T.PAGE_W, T.PAGE_H)
CHAPTERS = [("cap-uno", "1 · Uno", "El primer capítulo", 3),
            ("cap-dos", "2 · Dos", "El segundo capítulo, largo", 40),
            ("cap-tres", "3 · Tres", "El tercer capítulo", 5)]
LOREM = ("Texto de prueba del cuerpo del informe con la letra de lectura a 10.5 puntos e interlineado de 1.45, "
         "lo bastante largo para ocupar varias líneas del marco y comprobar el paso de página.")


def _pdf():
    buf = io.BytesIO()
    meta = D.DocMeta(name="Empresa Ficticia S.A.", symbol="FICT", report_date="17 de octubre de 2026",
                     data_note="Datos de prueba al 14 oct 2026")
    doc = D.ReportDoc(buf, meta)
    S = D.styles()
    story = [D.Anchor(D.COVER_KEY, "Portada"), Paragraph("Portada de prueba", S["title"]),
             D.start_on("index"), PageBreak(),
             D.Anchor(D.INDEX_KEY, "Índice"), Paragraph("Contenido", S["title"]), Spacer(1, 8),
             D.Index([(f"{eb} · {title}", key) for key, eb, title, _ in CHAPTERS]),
             D.start_on("body"), PageBreak()]
    for key, eb, title, n in CHAPTERS:
        story.append(D.ChapterHeading(key, eb, title, toc_text=f"{eb} · {title}"))
        story += [Paragraph(LOREM, S["body"]) for _ in range(n)]
    doc.render(story)
    return buf.getvalue(), doc


@pytest.fixture(scope="module")
def built():
    return _pdf()


def test_bookmarks_cover_index_and_each_chapter(built):
    pdf, _ = built
    ol = pi.outline(pdf)
    assert [t for _, t, _ in ol] == ["Portada", "Índice"] + [f"{eb} · {title}" for _, eb, title, _ in CHAPTERS]
    pages = [p for _, _, p in ol]
    assert pages[:3] == [1, 2, 3] and pages == sorted(pages)
    assert pages[-1] - pages[-2] >= 2, "el capítulo 2 ocupa más de una página"


def test_index_has_one_linked_entry_per_chapter(built):
    pdf, _ = built
    ol = {t: p for _, t, p in pi.outline(pdf)}
    on_index = [lk for lk in pi.links(pdf) if lk.page == 2 and lk.kind == "internal"]
    # título y número de página de cada entrada, los dos enlazados al capítulo
    assert {lk.target for lk in on_index} == {ol[f"{eb} · {t}"] for _, eb, t, _ in CHAPTERS}
    assert len(on_index) == 2 * len(CHAPTERS)
    lines = [ln.strip() for ln in pi.page_texts(pdf)[1].splitlines()]
    for _, eb, title, _ in CHAPTERS:
        line = next(ln for ln in lines if title in ln)
        assert line.endswith(f" {ol[f'{eb} · {title}']}"), line


def test_up_to_index_link_on_every_body_page(built):
    pdf, _ = built
    texts = pi.page_texts(pdf)
    lks = pi.links(pdf)
    assert len(texts) >= 5
    for p in range(3, len(texts) + 1):
        assert D.INDEX_LABEL in texts[p - 1], f"p{p} sin «↑ índice»"
        assert any(lk.page == p and lk.kind == "internal" and lk.target == 2 for lk in lks), f"p{p}: enlace"
    assert D.INDEX_LABEL not in texts[0] and D.INDEX_LABEL not in texts[1]


def test_page_x_of_y_is_exact(built):
    pdf, doc = built
    texts = pi.page_texts(pdf)
    n = len(texts)
    assert doc.total_pages == n
    for p, t in enumerate(texts, 1):
        assert f"Página {p} de {n}" in t


def test_geometry_inside_area_without_overlaps_or_small_text(built):
    pdf, _ = built
    bad = pg.check(pdf, area=AREA, min_font=T.MIN_FONT)
    assert not bad, "\n".join(bad[:10])


def test_geometry_detects_small_text():
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(T.PAGE_W, T.PAGE_H))
    c.setFont("Helvetica", 7)
    c.drawString(T.M_LR + 10, 400, "letra de siete puntos")
    c.showPage()
    c.save()
    assert any("letra de 7.00 pt" in x for x in pg.check(buf.getvalue(), area=AREA, min_font=T.MIN_FONT))


def test_geist_is_embedded(built):
    pdf, _ = built
    assert T.FONT["regular"] == "Geist", T.FONT_SOURCE
    assert b"Geist" in pdf


# ── huecos (config/pdf.toml) y bloques flotantes ──
def test_gaps_detect_a_short_page_and_a_hole():
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(T.PAGE_W, T.PAGE_H))
    top = T.PAGE_H - T.M_TOP - 12
    c.drawString(T.M_LR, top, "arriba")
    c.drawString(T.M_LR, top - 200, "doscientos puntos más abajo")
    c.showPage()
    c.drawString(T.M_LR, 300, "última página")
    c.showPage()
    c.save()
    bad = pg.gaps(buf.getvalue(), AREA, max_tail=100, max_block=48)
    assert any("hueco al pie" in b and b.startswith("p1") for b in bad)
    assert any("hueco entre bloques" in b for b in bad)
    assert not any(b.startswith("p2") and "al pie" in b for b in bad), "la última página no cuenta"


def test_a_block_that_does_not_fit_lets_the_text_after_it_fill_the_page():
    from reportlab.platypus import Spacer as Sp
    from pdf_v2.doc import FloatGroup, Stack
    buf = io.BytesIO()
    doc = D.ReportDoc(buf, D.DocMeta(name="X", symbol="X", report_date="hoy", data_note="d"))
    S = D.styles()
    block = Stack([Paragraph("BLOQUE VISUAL", S["title"]), Sp(1, 300)])
    story = [D.Anchor(D.INDEX_KEY, "Índice"), D.start_on("body"), Paragraph("x", S["body"]), Sp(1, T.CH - 200),
             FloatGroup(block, [Paragraph(f"línea de texto que sigue {i}", S["body"]) for i in range(12)])]
    doc.render(story)
    texts = pi.page_texts(buf.getvalue())
    # el bloque (≈ 330 pt) no cabe en los ≈ 180 pt que quedan: el texto que le sigue llena la página 1
    assert "BLOQUE VISUAL" not in texts[0] and "BLOQUE VISUAL" in texts[1]
    assert "sigue 0" in texts[0] and "sigue 5" in texts[0]
