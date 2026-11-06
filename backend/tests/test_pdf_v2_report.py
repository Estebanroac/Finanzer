"""
Rediseño E5 (Task 3): portada, índice y resumen del PDF nuevo (lib/pdf_v2), con el análisis del replay (golden del
panel) y las series grabadas.

La portada cabe en una página sin encoger y lleva identidad, precio y variación (o su ausencia con el motivo),
conclusión, las tres escalas con su base, la gráfica de 1 año y las 6 cifras clave. La página 2 tiene el índice
enlazado (9 capítulos, resumen, metodología y anexo) y la lectura del análisis completa. Geometría limpia y letra
≥ 8 pt en todo el panel.
"""
import copy
import glob
import json
import os
from datetime import date

import pytest

import pdf_geometry as pg
import pdf_inspect as pi
import pdf_v2_samples as S
from pdf_v2 import build_pdf
from pdf_v2 import chapters as C
from pdf_v2 import doc as D
from pdf_v2 import theme as T

AREA = pg.Area(T.M_LR, T.M_TOP, T.M_BOT, T.PAGE_W, T.PAGE_H)
TODAY = date(2026, 10, 17)
PANEL = sorted(os.path.basename(f)[:-5] for f in glob.glob(os.path.join(S.GOLDEN_PANEL, "*.json"))
               if json.load(open(f, encoding="utf-8")).get("display"))


def _flat(t):
    return " ".join(t.split())


@pytest.fixture(scope="module")
def built():
    cache = {}

    def get(sym, prices=True, mutate=None):
        key = (sym, prices, mutate.__name__ if mutate else None)
        if key not in cache:
            a = S.analysis(sym)
            if mutate:
                a = copy.deepcopy(a)
                mutate(a)
            pdf = build_pdf(a, S.prices(sym) if prices else None, today=TODAY)
            cache[key] = (a, pdf, pi.page_texts(pdf))
        return cache[key]
    return get


# ── portada ──
@pytest.mark.parametrize("sym", ["AAPL", "JPM"])
def test_cover_holds_identity_scales_chart_and_key_figures(built, sym):
    a, pdf, texts = built(sym)
    p1 = _flat(texts[0])
    d = a["display"]
    assert a["profile"]["name"] in p1 and sym in p1
    assert d["charts"]["price_card"]["price_txt"] in p1
    pc = (d.get("extended") or {}).get("price_change") or {}
    if pc.get("status") == "ok":                        # E2a: la variación del día, con su signo
        assert "hoy" in p1 and "Variación del día: sin dato" not in p1
    else:
        assert "Variación del día: sin dato" in p1
    assert d["cover"]["verdict"]["text"] in p1
    for title in (d["cover"]["quality"]["title"], d["cover"]["price"]["title"], "CONFIANZA DEL VEREDICTO"):
        assert title in p1
    assert f"{d['cover']['quality']['score']}" in p1 and "4 categorías × 20 puntos" in p1
    assert "S&P 500" in p1 and "Precio en el último año" in p1
    for card in d["summary"]["cards"]:
        assert card["label"] in p1 and card["pill"] in p1
    assert "Documento informativo" in p1
    assert pg.scales(pdf)["portada"] == 1.0


def test_cover_without_price_series_says_why_and_keeps_one_page(built):
    _, pdf, texts = built("AAPL", prices=False)
    assert "Gráfica de precio (1 año) no disponible" in _flat(texts[0])
    assert "Contenido" in texts[1] and pg.scales(pdf)["portada"] >= T.MIN_SCALE


def _with_day_change(a):
    a["display"]["extended"] = {"price_change": {"status": "ok", "value_txt": "+$2.71", "pct_txt": "+0.8%",
                                                 "tone": "pos", "session": "2026-10-14"}}


def test_cover_shows_day_change_when_e2_publishes_it(built):
    _, _, texts = built("AAPL", mutate=_with_day_change)
    p1 = _flat(texts[0])
    assert "+$2.71 (+0.8%) hoy" in p1 and "Variación del día: sin dato" not in p1


# ── índice, marcadores y resumen ──
@pytest.mark.parametrize("sym", ["AAPL", "JPM"])
def test_index_links_every_chapter_methodology_and_annex(built, sym):
    _, pdf, texts = built(sym)
    ol = {t: p for _, t, p in pi.outline(pdf)}
    expected = [t for t, _ in C.toc_entries()]
    assert list(ol)[:3] == ["Portada", "Índice", "Resumen"]
    assert [t for t in ol if t in expected] == expected
    targets = {lk.target for lk in pi.links(pdf) if lk.page == 2 and lk.kind == "internal"}
    # V7: sin «Resumen 2» en el índice (el resumen empieza debajo, en la misma página); sigue en los marcadores
    assert targets == {ol[t] for t in expected}
    assert "Resumen 2" not in " ".join(texts[1].split()) and C.GLOSSARY[1] in expected
    for t in expected:
        assert t in texts[1]


@pytest.mark.parametrize("sym", ["AAPL", "JPM"])
def test_summary_reads_the_whole_engine_summary(built, sym):
    a, _, texts = built(sym)
    body = _flat(" ".join(texts[1:3]))
    for e in a["display"]["summary"]["exec_items"]:
        assert e["label"] in body
        # V7 · P1 (opción C): la fila de la confianza lleva el resumen de la confianza (test_confidence_row_…)
        text = a["display"]["confidence"]["summary"] if e["label"] == "CONFIANZA DEL VEREDICTO" else e["text"]
        assert _flat(text)[-40:] in body, e["label"]


def test_quality_note_goes_to_the_summary(built):
    # F8 · E4: con el resumen de KO más largo, la nota empieza en la página 3 (antes, en la 2): sigue en el resumen.
    # F8 · E10: con Altman a +3, KO (79) ya no pasa el codo de la persistencia y no lleva nota; el caso es MU, la nota
    # más larga del panel.
    a, _, texts = built("MU")
    note = a["display"]["cover"]["quality"]["note"]
    summary = " ".join(texts[1:3])
    assert "NOTA · CALIDAD" in summary and _flat(note)[-30:] in _flat(summary)


@pytest.mark.parametrize("sym", ["AAPL", "JPM"])
def test_every_body_page_links_back_to_the_index_and_numbers_are_exact(built, sym):
    _, pdf, texts = built(sym)
    n = len(texts)
    lks = pi.links(pdf)
    for p in range(1, n + 1):
        assert f"Página {p} de {n}" in texts[p - 1]
    for p in range(3, n + 1):
        assert D.INDEX_LABEL in texts[p - 1]
        assert any(lk.page == p and lk.target == 2 for lk in lks)


# ── geometría, letra y glifos en todo el panel ──
@pytest.mark.parametrize("sym", PANEL)
def test_panel_geometry_min_font_and_cover_fit(sym):
    pdf = build_pdf(S.analysis(sym), S.prices(sym), today=TODAY)
    bad = pg.check(pdf, area=AREA, min_font=T.MIN_FONT)
    assert not bad, "\n".join(bad[:10])
    assert pg.scales(pdf)["portada"] == 1.0
    assert len(pdf) <= 1.5 * 1024 * 1024


def test_every_engine_character_has_a_glyph():
    missing = {}
    for sym in PANEL:
        for ch in set(json.dumps(S.analysis(sym)["display"], ensure_ascii=False)):
            if not D.covered(ch):
                missing.setdefault(ch, sym)
    assert not missing, missing


@pytest.mark.parametrize("sym", ["KO", "ASML", "MU", "NFLX", "NVDA", "PGR"])
def test_a_split_summary_row_repeats_its_label_with_sigue(built, sym):
    """V7 (PM): una fila del resumen partida entre dos páginas conserva su etiqueta en la primera y la repite con
    «(sigue)» en la siguiente. F8 · E4: KO ya no parte la nota de calidad (empieza entera en la página 3) y ninguna
    empresa del panel la parte hoy; el mecanismo lo prueba test_labeled_table_repeats_the_label_once y aquí queda la
    invariante sobre las que llevan nota: «(sigue)» solo detrás de la página que abre la fila."""
    _, _, texts = built(sym)
    for i, t in enumerate(texts):
        if "NOTA · CALIDAD (sigue)" in t:
            assert i > 0 and "NOTA · CALIDAD" in texts[i - 1].replace("NOTA · CALIDAD (sigue)", ""), (sym, i)


def test_labeled_table_repeats_the_label_once(tmp_path):
    """Una fila más larga que dos páginas: cada parte siguiente dice «(sigue)» una vez, no «(sigue) (sigue)»."""
    from reportlab.platypus import Paragraph
    from pdf_v2 import parts as P
    from pdf_v2.doc import styles
    st = styles()["body"]
    t = P.LabeledTable([[Paragraph("ETIQUETA", st), Paragraph(" ".join(["palabra"] * 600), st)]], colWidths=[120, 380],
                       splitInRow=1)
    t.wrap(500, 2000)
    first, rest = t.split(500, 200)
    rest.wrap(500, 2000)
    second, third = rest.split(500, 200)
    labels = [p._cellvalues[0][0] for p in (first, second, third)]
    texts = [(c[0] if isinstance(c, (list, tuple)) else c).text for c in labels]
    assert texts == ["ETIQUETA", "ETIQUETA (sigue)", "ETIQUETA (sigue)"]


@pytest.mark.parametrize("sym", ["PLD", "JNJ", "XOM", "O"])
def test_confidence_row_is_the_engine_summary(built, sym):
    """V7 · P1 (decisión del PM, opción C): la fila «CONFIANZA DEL VEREDICTO» del resumen (página 2) es exactamente
    `display.confidence.summary`, el mismo texto que enseña la web; la portada no cambia y su tarjeta lleva el
    `verdict_text` de M5 bis (PLD: «DCF inverso y los múltiplos coinciden»; KO, con el directo fiable: «el DCF…»)."""
    from pdf_v2 import cover as CV
    from pdf_v2.doc import esc
    a, _, texts = built(sym)
    conf = a["display"]["confidence"]
    rows = {e["label"]: e["text"] for e in [{"label": t._cellvalues[0][0].text, "text": t._cellvalues[0][1].text}
                                            for t in CV._exec_summary_rows(a)]}
    assert rows[CV.CONFIDENCE_LABEL] == esc(conf["summary"])
    assert _flat(conf["summary"]) in _flat(" ".join(texts[1:3]))
    cover = _flat(texts[0])
    assert _flat(CV._unwrap(conf["verdict_text"])) in cover
    # F8 · E8: con la fiabilidad por los insumos, AAPL usa el DCF directo; PLD (REIT) es el caso del inverso, y KO
    # vuelve a ser el del directo fiable.
    if sym == "PLD":
        # F13 · paso 3: sin el DCF inverso contado también dentro de los múltiplos, sus múltiplos (P/FFO) la ven cara y
        # el inverso en precio: confianza media (antes, «coinciden»: la misma lectura contada dos veces)
        # F13 (SRE y Oncor): el EV/EBITDA sin sus participadas inmobiliarias la ve en línea con su industria, como el
        # inverso: ahora sí coinciden (sin el inverso dentro de los múltiplos, paso 3)
        assert "DCF inverso y los múltiplos coinciden" in cover and "El DCF y los múltiplos coinciden" not in cover
    # F10 · N4: KO era el caso del directo fiable; con P/E, forward y PEG como una sola lectura su precio queda a un
    # punto de la frontera y ±1 pp de Ke cambia su nivel (confianza media por eso). JNJ es ahora el caso.
    if sym == "JNJ":    # PM: siempre de qué DCF se habla, como la fila «DCF directo» de la tarjeta
        assert "El DCF directo y los múltiplos coinciden" in cover
