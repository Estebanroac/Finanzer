"""
Rediseño E5 (Task 6): el PDF nuevo en todo el panel (36 informes; SPY se rechaza).

Por informe: geometría (dentro del área, sin solapes, letra ≥ 8 pt), sin huecos (config/pdf.toml [layout]: al pie y
entre bloques), portada sin encoger, enlaces (los internos a una página que existe, los externos https), peso,
tiempo y golden de texto (tests/golden/panel_pdf_v2, regenerable solo a mano con tests/pdf_v2_golden.py).
"""
import time
import tracemalloc

import pytest

import fixture_backend as fb
import pdf_geometry as pg
import pdf_inspect as pi
import pdf_v2_golden as G
import pdf_v2_samples as S
from pdf_v2 import theme as T
from settings import cfg

AREA = pg.Area(T.M_LR, T.M_TOP, T.M_BOT, T.PAGE_W, T.PAGE_H)
PANEL = S.panel_symbols()
MAX_BYTES = 1.5 * 1024 * 1024
MAX_SECONDS = 3.0
MAX_PEAK_MB = 150


@pytest.fixture(scope="module")
def built():
    cache = {}

    def get(sym):
        if sym not in cache:
            # el tiempo es el de componer el informe: las entradas (análisis, series, segmentos) llegan de las cachés en
            # producción; aquí se leen y procesan de los fixtures, y eso no cuenta (la primera, AAPL, tardaba unos 3 s en
            # leer y analizar el 10-K de los segmentos)
            inp = S.inputs(sym)
            t0 = time.perf_counter()
            pdf = S.build_from(inp)
            cache[sym] = (pdf, time.perf_counter() - t0)
        return cache[sym]
    return get


def test_panel_is_complete():
    assert len(PANEL) >= 36 and "SPY" not in PANEL and "MC.PA" in PANEL


@pytest.mark.parametrize("sym", PANEL)
def test_geometry_gaps_and_cover(sym, built):
    pdf, _ = built(sym)
    L = cfg("pdf.layout")
    bad = pg.check(pdf, area=AREA, min_font=T.MIN_FONT) + \
        pg.gaps(pdf, AREA, L["max_tail_gap_pt"], L["max_block_gap_pt"])
    # la única excepción al hueco al pie: la página anterior a un capítulo que empieza página por diseño (el glosario)
    n = len(pi.page_texts(pdf))
    assert pg.new_page_starts(pdf) == {"glosario": n}
    assert not bad, "\n".join(bad[:10])
    assert pg.scales(pdf)["portada"] == 1.0


@pytest.mark.parametrize("sym", PANEL)
def test_links(sym, built):
    pdf, _ = built(sym)
    n = len(pi.page_texts(pdf))
    links = pi.links(pdf)
    internal = [lk for lk in links if lk.kind == "internal"]
    external = [lk for lk in links if lk.kind == "uri"]
    assert internal and all(1 <= lk.target <= n for lk in internal)
    assert len(external) >= 4 and all(lk.target.startswith("https://") for lk in external), \
        [lk.target for lk in external]
    assert not [lk for lk in links if lk.kind == "other"]
    ol = pi.outline(pdf)
    assert all(p and 1 <= p <= n for _, _, p in ol) and len(ol) == 3 + 12      # portada, índice, resumen; 9 capítulos, metodología, anexo y glosario (V7)


@pytest.mark.parametrize("sym", PANEL)
def test_weight_and_time(sym, built):
    pdf, secs = built(sym)
    assert len(pdf) <= MAX_BYTES
    assert secs <= MAX_SECONDS


def test_peak_memory():
    tracemalloc.start()
    try:
        S.build("AAPL")
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert peak / 1e6 <= MAX_PEAK_MB


@pytest.mark.parametrize("sym", PANEL)
def test_golden_text(sym, built):
    pdf, _ = built(sym)
    with open(G.path(sym), encoding="utf-8") as fh:
        assert fb.pdf_text(pdf) == fh.read(), f"el texto de {sym} cambió: tests/pdf_v2_golden.py {sym}"


@pytest.mark.parametrize("sym", PANEL)
def test_nothing_is_cut_with_an_ellipsis(sym, built):
    """Retoque del PM: ningún dato se corta con «…». Los «…» del texto vienen del propio motor."""
    import json
    import re
    pdf, _ = built(sym)
    text = " ".join(fb.pdf_text(pdf).split())
    engine = [s for s in re.findall(r'"([^"]*…[^"]*)"', json.dumps(S.analysis(sym)["display"], ensure_ascii=False))]
    for m in re.finditer("…", text):
        before = text[max(0, m.start() - 10):m.start() + 1]
        assert any(before in " ".join(e.split()) for e in engine), f"«…» que no es del motor: {before!r}"


@pytest.mark.parametrize("sym", PANEL)
def test_absent_e2_blocks_take_one_line(sym, built):
    """Revisión del PM: un bloque con datos de E2 que no llegan se reduce a una línea (título · motivo); no reserva su
    caja. Con los datos de E2 (v4): la historia de 10 años (E2a) y los segmentos capturados (E2b) salen con su tabla;
    los rivales, que el informe no espera, siguen en una línea."""
    pdf, _ = built(sym)
    text = " ".join(fb.pdf_text(pdf).split())
    a = S.analysis(sym)
    h10 = (a.get("history_10y") or {}).get("status") == "ok"
    seg = (S.segments_of(sym) or {}).get("status") == "ok"
    for has, line in ((seg, "Ingresos por segmento · sin desglose oficial"), (h10, "Historia de 10 ejercicios · sin dato")):
        assert (line not in text) if has else (line in text), line
    if h10:
        assert "Historia de 10 ejercicios EJERCICIO INGRESOS" in text
    if seg:
        assert "Ingresos por segmento" in text and "Fuente: SEC EDGAR" in text
    assert "Rivales de la misma industria · consulta la web" in text
    for gone in ("Historia financiera: sin dato", "Sin desglose oficial por segmento"):
        assert gone not in text, gone


@pytest.mark.parametrize("sym", PANEL)
def test_no_page_starts_with_a_value_without_its_label(sym, built):
    """V7 (PM): una fila de dos columnas (resumen, anexo, metodología) partida entre páginas repite su etiqueta con
    «(sigue)» en la siguiente; ninguna página empieza con texto de la columna del valor sin etiqueta a su izquierda."""
    pdf, _ = built(sym)
    assert pg.headless_page_starts(pdf, AREA) == []
