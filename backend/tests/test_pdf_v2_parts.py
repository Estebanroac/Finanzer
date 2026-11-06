"""
Rediseño E5 (Task 2): componentes de dibujo del PDF nuevo (lib/pdf_v2/parts.py).

Cada parte se dibuja sin error con los datos de AAPL y sin datos; la ausente dice su motivo en una línea (no reserva
su caja: lo que sigue sube a ocupar el sitio; revisión del PM de E5). Las escalas usan las bandas del motor; la geometría (área, solapes, letra ≥ 8 pt) se comprueba en una página
con todas las partes.
"""
import io

import pytest
from reportlab.pdfgen import canvas

import pdf_geometry as pg
import pdf_inspect as pi
import pdf_v2_samples as S
from pdf_v2 import parts as P
from pdf_v2 import theme as T
from settings import cfg

AREA = pg.Area(T.M_LR, T.M_TOP, T.M_BOT, T.PAGE_W, T.PAGE_H)


@pytest.fixture(scope="module")
def aapl():
    return S.analysis("AAPL")


@pytest.fixture(scope="module")
def aapl_prices():
    p = S.prices("AAPL")
    if p is None:
        pytest.skip("sin series de precios grabadas")
    return p


def _render(*flowables, width=T.CW):
    """Dibuja las partes una debajo de otra en páginas carta; devuelve (pdf, [(ancho, alto)])."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(T.PAGE_W, T.PAGE_H))
    y = T.PAGE_H - T.M_TOP
    sizes = []
    for f in flowables:
        w, h = f.wrapOn(c, width, T.CH)
        if y - h < T.M_BOT:
            c.showPage()
            y = T.PAGE_H - T.M_TOP
        y -= h
        f.drawOn(c, T.M_LR, y)
        y -= 12
        sizes.append((w, h))
    c.showPage()
    c.save()
    return buf.getvalue(), sizes


def _text(pdf):
    return " ".join(" ".join(pi.page_texts(pdf)).split())


# ── escalas ──
def test_quality_scale_uses_engine_bands():
    m = P.build_scale("quality", 75, "sólida")
    assert [s.label for s in m.segments] == list(reversed(cfg("thresholds.score.quality.labels")))
    assert [s.range for s in m.segments] == ["<45", "45–65", "65–85", "85+"]
    assert m.pin == 75 and P.bands_line(m) == "débil <45 · media 45–65 · sólida 65–85 · excelente 85+"


def test_price_scale_and_confidence_levels():
    m = P.build_scale("price", 15, "muy exigente")
    assert [s.range for s in m.segments] == ["<30", "30–45", "45–65", "65+"]
    lv = P.build_level_scale("alta")
    assert [s.label for s in lv.segments] == ["baja", "media", "alta"] and lv.pin == pytest.approx(500 / 6)
    assert P.build_level_scale(None).pin is None


def test_score_scales_draw_in_an_equal_row(aapl):
    q = aapl["display"]["cover"]["quality"]
    cards = [P.ScoreScale(P.build_scale("quality", q["score"], q["level"]), q["title"], q["question"],
                          str(q["score"]), f"/ 100 · {q['level']}", q["tone"], "4 categorías × 20 puntos",
                          [("Rentabilidad", "20 / 20", "pos")]),
             P.ScoreScale(P.build_level_scale("alta"), "Confianza del veredicto", "¿cuánto fiarse?", "Alta", None,
                          "neu", "DCF inverso y los múltiplos coinciden",
                          [("Convergencia", "Alta", None), ("Cobertura", "Alta", None), ("Fuente", "Alta", None)])]
    row = P.equal_row(cards, T.CW)
    pdf, _ = _render(row)
    assert cards[0].height == cards[1].height
    t = _text(pdf)
    # F8 · E10: la calidad de AAPL sale del golden (con el Altman por SIC y su peso; los números cambian con el motor)
    assert str(q["score"]) in t and f"/ 100 · {q['level']}" in t and "débil <45" in t and "baja" in t and "Alta" in t


def test_score_scale_without_score_shows_dash():
    card = P.ScoreScale(P.build_scale("price", None, None), "Atractivo del precio", "¿está cara hoy?", "—", None,
                        None, "sin valoración: no hay múltiplos ni DCF")
    pdf, _ = _render(card)
    assert "sin valoración" in _text(pdf)


# ── tarjetas, tabla y barras ──
def test_figure_cards_from_summary_cards(aapl):
    cards = [P.FigureCard(c["label"], c["value"], c["unit"], c["bench"], c["pill"], c["tone"])
             for c in aapl["display"]["summary"]["cards"][:3]]
    pdf, _ = _render(P.equal_row(cards, T.CW))
    assert len({c.height for c in cards}) == 1
    t = _text(pdf)
    # F9 · R3: la precisión de las tablas. F10 · N2: AAPL es el 91 % de su industria de Damodaran en EE. UU.; F14 · paso
    # 6: la referencia es la misma industria a escala global sin Apple, no la mediana de 7 pares
    assert "vs industria 4.71%" in t and "Muy superior" in t


def test_tech_table_with_reading_pills_and_missing_rows(aapl):
    rows = list(aapl["display"]["sections"]["valuation"]["rows"][:4])
    rows.append({"key": "x", "label": "Métrica sin dato", "state": "sin_dato", "value": None,
                 "text": "la fuente no la publica"})
    pdf, _ = _render(P.tech_table(rows, T.CW, meaning=lambda k, l: "Cuántas veces el beneficio" if k == "pe" else None))
    t = _text(pdf)
    assert "P/E (TTM)" in t and "Prima elevada" in t and "Cuántas veces el beneficio" in t   # F10 · N2: frente a sus pares
    assert "Sin dato" in t and "la fuente no la publica" in t


def test_category_bars(aapl):
    items = aapl["display"]["cover"]["categories"][0]["items"]
    pdf, _ = _render(P.CategoryBars(items))
    t = _text(pdf)
    assert "Rentabilidad" in t and "20 / 20" in t


# ── la parte ausente dice su motivo en una línea ──
ONE_LINE = T.SMALL_LEADING + 1


def _absent_one_line(present, absent, reason):
    pdf, sizes = _render(present, absent)
    assert sizes[1][1] <= ONE_LINE, f"la parte sin dato ocupa {sizes[1][1]:.1f} pt: debe ser una línea"
    assert sizes[0][1] > 3 * ONE_LINE, sizes
    assert reason in _text(pdf)
    return pdf


def test_missing_line_is_title_and_reason_in_one_line():
    line = P.missing_line("Ingresos por segmento", "sin desglose oficial: sin XBRL de segmentos.")
    w, h = line.wrap(T.CW, T.CH)
    assert h <= ONE_LINE
    pdf, _ = _render(line)
    t = _text(pdf)
    assert "Ingresos por segmento · sin desglose oficial: sin XBRL de segmentos" in t
    assert "segmentos." not in t        # sin punto final suelto


def test_range52(aapl):
    r = aapl["display"]["sections"]["growth"]["range52"]
    pdf = _absent_one_line(P.Range52(r), P.Range52(None, reason="sin serie de 52 semanas"), "sin serie de 52 semanas")
    assert "Máximo $348.15" in _text(pdf) and "95% del rango" in _text(pdf)


def test_piotroski_grid(aapl):
    crit = aapl["display"]["sections"]["institutional"]["piotroski_criteria"]
    values = [{"key": crit[0]["key"], "cur_txt": "33.6%", "prev_txt": "30.1%", "compare": "prior_year"}]
    pdf = _absent_one_line(P.Piotroski(crit, values), P.Piotroski([], reason="no aplica a bancos"), "no aplica a bancos")
    t = _text(pdf)
    assert "ROA positivo" in t and "Cumple" in t and "33.6% frente a 30.1%" in t


def test_price_chart_one_and_five_years(aapl_prices):
    one = P.PriceChart(aapl_prices, "AAPL", period="1y")
    five = P.PriceChart(aapl_prices, "AAPL", period="5y")
    assert one.win["status"] == "ok" and five.win["status"] == "ok"
    assert set(one.win["series"]) == {"company", "market", "sector"}
    assert one.win["series"]["company"][0][1] == pytest.approx(100)
    pdf = _absent_one_line(one, P.PriceChart({"company": {"points": [], "reason": "Yahoo no respondió"}}, "AAPL"),
                     "Yahoo no respondió")
    t = _text(pdf)
    assert "AAPL" in t and "S&P 500" in t and "XLK" in t and "base 100" in t
    _render(five)


def test_price_chart_says_which_reference_is_missing(aapl_prices):
    p = dict(aapl_prices, sector={"symbol": None, "status": "sin_dato", "reason": "sin ETF de sector", "points": []})
    pdf, _ = _render(P.PriceChart(p, "AAPL"))
    assert "sin ETF de sector" in _text(pdf)


def test_segments_bars():
    seg = {"status": "ok", "fiscal_years": ["2024", "2025"], "axis_label": "Productos",
           "segments": [{"member": "a", "label": "Producto A", "values": {"2025": 2.0e11}, "share_last": 0.5},
                        {"member": "b", "label": "Servicio B", "values": {"2025": 1.0e11}, "share_last": 0.25}],
           "currency": "USD", "source": {"form": "10-K", "filed": "2025-10-31"}, "reason": None}
    pdf = _absent_one_line(P.SegmentBars(seg), P.SegmentBars({"status": "sin_dato", "reason": "sin XBRL de segmentos"}),
                     "sin XBRL de segmentos")
    t = _text(pdf)
    assert "Producto A" in t and "50% · $200.00B" in t and "Sin desglose oficial" in t
    assert P.SegmentBars(seg).available() and not P.SegmentBars(None).available()


def test_history_ten_years():
    rows = [{"year": 2016 + i, "revenue_txt": f"${200 + i}.00B", "net_income_txt": "$50.00B", "fcf_txt": "$40.00B",
             "operating_margin_txt": "30.0%", "net_margin_txt": "25.0%", "revenue_growth_txt": "+5.0%"}
            for i in range(10)]
    hist = {"status": "ok", "currency": "USD", "source": "SEC EDGAR", "reason": None, "rows": rows}
    short = {"status": "ok", "currency": "USD", "source": "SEC EDGAR", "reason": "EDGAR trae 4 ejercicios",
             "rows": rows[-4:]}
    full, part = P.History10(hist), P.History10(short)
    pdf, sizes = _render(full, part)
    assert sizes[1][1] == sizes[0][1] - 6 * P.History10.ROW      # con 4 años, el alto de sus 4 filas
    assert "EDGAR trae 4 ejercicios" in _text(pdf)
    assert "2016" in _text(pdf) and "$209.00B" in _text(pdf)
    _absent_one_line(P.History10(hist), P.History10(None), "aún no llegó")


# ── geometría de una página con las partes ──
def test_parts_page_geometry(aapl, aapl_prices):
    d = aapl["display"]
    q = d["cover"]["quality"]
    page = [P.equal_row([P.ScoreScale(P.build_scale("quality", q["score"], q["level"]), q["title"], q["question"],
                                      str(q["score"]), f"/ 100 · {q['level']}", q["tone"], "4 categorías × 20 puntos"),
                         P.FigureCard("ROE", "119.9", "%", "", "En rango", "neu")], T.CW),
            P.PriceChart(aapl_prices, "AAPL"), P.Range52(d["sections"]["growth"]["range52"]),
            P.tech_table(d["sections"]["valuation"]["rows"][:3], T.CW)]
    pdf, _ = _render(*page)
    bad = pg.check(pdf, area=AREA, min_font=T.MIN_FONT)
    assert not bad, "\n".join(bad[:10])


def test_tech_table_without_reference_leaves_reading_empty():
    """Revisión del PM: sin referencia, una sola raya en Brecha (y la de Referencia) y la Lectura vacía, no «— —»."""
    rows = [{"key": "forward_pe", "label": "Forward P/E", "value": "7.60x", "bench": "—", "gap": "—", "reading": "—",
             "state": "con_dato"}]
    t = _text(_render(P.tech_table(rows, T.CW))[0])
    assert t.count("—") == 2, t
    rows3 = [{"key": "x", "label": "Valor justo", "value": "$10", "reading": None, "state": "con_dato"}]
    assert "—" not in _text(_render(P.tech_table3(rows3, T.CW))[0])
