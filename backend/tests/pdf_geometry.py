"""
Fase 1 del plan de fiabilidad (T4): comprobación geométrica del PDF con las cajas de texto de pypdfium2.

(a) Todo texto queda dentro del área útil de la página: en horizontal, el ancho útil del informe
    ([M_LR, PAGE_W − M_LR], donde también se alinean cabecera y pie); en vertical, a más de 1/4" del borde, y ningún
    texto del cuerpo invade la banda de la cabecera o del pie (una caja que cruza el borde del marco).
(c) La portada y la página 2 encogen su contenido para caber (KeepInFrame en modo shrink) como mucho hasta
    MIN_SCALE: por debajo la letra queda demasiado pequeña. pdf_report deja cada escala en las palabras clave del
    PDF ("escala_portada=0.973 escala_pagina2=1.000").
(b) No hay líneas de bloques distintos que se solapen: dos cajas de texto que se cruzan en horizontal y en vertical
    (más que el redondeo de pdfium) son texto pintado encima de otro texto (p. ej. la "Lectura del análisis" sobre la
    "Composición" de la página 2).

Las cifras de la geometría salen de lib/pdf_report.py (márgenes y tamaño de página): ninguna se copia aquí.

Rediseño E5: el informe nuevo (lib/pdf_v2) tiene sus propios márgenes; `check(pdf, area=Area(...))` aplica las mismas
reglas con ellos (por defecto, las del informe actual), y `small_text` comprueba el tamaño mínimo de letra.
"""
import re
from collections import namedtuple
from typing import Dict, List, Optional, Tuple

import pypdfium2 as pdfium

from pdf_report import M_BOT, M_LR, M_TOP, PAGE_H, PAGE_W

TOL = 1.0              # pt: redondeo de las cajas de pdfium
SAFE = 18.0            # pt: 1/4" de margen físico de impresión
MIN_V_OVERLAP = 0.35   # fracción de la altura de la caja menor: por debajo es interlineado apretado, no solape
MIN_SCALE = 0.85       # escala mínima admitida del contenido encogido (portada y página 2)

Box = Tuple[int, float, float, float, float, str]   # (página, izq, abajo, der, arriba, texto)
Area = namedtuple("Area", "m_lr m_top m_bot page_w page_h")
AREA = Area(M_LR, M_TOP, M_BOT, PAGE_W, PAGE_H)      # el informe actual (lib/pdf_report.py)


def text_boxes(pdf_bytes) -> List[Box]:
    doc = pdfium.PdfDocument(pdf_bytes)
    out: List[Box] = []
    for p in range(len(doc)):
        tp = doc[p].get_textpage()
        for i in range(tp.count_rects()):
            l, b, r, t = tp.get_rect(i)
            txt = tp.get_text_bounded(l, b, r, t).strip()
            if txt:
                out.append((p + 1, l, b, r, t, txt))
    return out


def outside_area(boxes: List[Box], area: Area = AREA) -> List[str]:
    bad = []
    for p, l, b, r, t, txt in boxes:
        if l < area.m_lr - TOL or r > area.page_w - area.m_lr + TOL or b < SAFE or t > area.page_h - SAFE:
            bad.append(f"p{p} fuera del área útil ({l:.0f},{b:.0f})–({r:.0f},{t:.0f}): {txt[:50]!r}")
        elif (b < area.m_bot - TOL < t) or (b < area.page_h - area.m_top + TOL < t):
            bad.append(f"p{p} cruza el borde del marco ({b:.0f}–{t:.0f}): {txt[:50]!r}")
    return bad


def overlaps(boxes: List[Box]) -> List[str]:
    bad = []
    by_page: Dict[int, List[Box]] = {}
    for bx in boxes:
        by_page.setdefault(bx[0], []).append(bx)
    for p, bxs in by_page.items():
        bxs.sort(key=lambda x: x[2])                    # por el borde inferior
        for i, (_, l1, b1, r1, t1, s1) in enumerate(bxs):
            for _, l2, b2, r2, t2, s2 in bxs[i + 1:]:
                if b2 >= t1:                            # ya no pueden cruzarse en vertical
                    break
                ix = min(r1, r2) - max(l1, l2)
                iy = min(t1, t2) - max(b1, b2)
                if ix > TOL and iy > MIN_V_OVERLAP * min(t1 - b1, t2 - b2):
                    bad.append(f"p{p} solape: {s1[:40]!r} / {s2[:40]!r}")
    return bad


def scales(pdf_bytes) -> Dict[str, float]:
    """Escalas de los bloques encogidos ({"portada": 0.97, "pagina2": 1.0}); {} si el PDF no las declara."""
    kw = pdfium.PdfDocument(pdf_bytes).get_metadata_dict().get("Keywords") or ""
    return {k: float(v) for k, v in re.findall(r"escala_(\w+)=([\d.]+)", kw)}


def too_small(pdf_bytes) -> List[str]:
    return [f"{k} encogida a {v:.3f} (< {MIN_SCALE})" for k, v in scales(pdf_bytes).items() if v < MIN_SCALE]


def small_text(pdf_bytes, min_pt: float) -> List[str]:
    """Caracteres por debajo de `min_pt` (tamaño efectivo: fuente × escala de su matriz, p. ej. un bloque encogido)."""
    import pdf_inspect
    bad: Dict[Tuple[int, float], str] = {}
    for p, size, ch in pdf_inspect.font_sizes(pdf_bytes):
        if size < min_pt - 0.01:
            key = (p, round(size, 2))
            bad[key] = bad.get(key, "") + ch
    return [f"p{p} letra de {sz:.2f} pt (< {min_pt}): {txt[:40]!r}" for (p, sz), txt in sorted(bad.items())]


def _frame_boxes(boxes: List[Box], area: Area) -> Dict[int, List[Box]]:
    """Cajas de texto dentro del marco de cada página (sin cabecera ni pie)."""
    out: Dict[int, List[Box]] = {}
    for bx in boxes:
        p, l, b, r, t, txt = bx
        if b >= area.m_bot - TOL and t <= area.page_h - area.m_top + TOL:
            out.setdefault(p, []).append(bx)
    return out


def content_boxes(pdf_bytes) -> List[Box]:
    """Cajas de todo lo pintado (texto, trazos e imágenes) de cada página, con pdfium."""
    doc = pdfium.PdfDocument(pdf_bytes)
    out: List[Box] = []
    for p in range(len(doc)):
        for obj in doc[p].get_objects(max_depth=4):
            l, b, r, t = obj.get_pos()
            out.append((p + 1, l, b, r, t, ""))
    return out


def headless_page_starts(pdf_bytes, area: Area = AREA, indent: float = 100.0, line: float = 8.0,
                         gap: float = 6.0) -> List[str]:
    """V7 (PM): páginas (desde la 2) cuya primera línea del marco empieza en la columna del valor de una tabla: el resto
    de una fila partida sin su etiqueta a la izquierda (debe repetirla con «(sigue)», parts.LabeledTable).
    «Línea»: lo que hay a menos de `line` pt de su parte más alta (la etiqueta va algo más baja que el valor: letra menor
    y más relleno arriba). La cabecera repetida de una tabla (en versalitas) no cuenta: se mira la línea siguiente. Una
    sangría de hasta `indent` pt tampoco (viñetas; la tabla de sensibilidad, que va sangrada con su etiqueta): la columna
    del valor de las tablas del informe empieza a 132 pt del margen o más."""
    by_page = _frame_boxes(text_boxes(pdf_bytes), area)
    bad = []
    for p, bxs in sorted(by_page.items()):
        if p == 1 or not bxs:
            continue
        rest = sorted(bxs, key=lambda bx: -bx[4])
        while rest:
            top = rest[0][4]
            first = sorted((bx for bx in rest if bx[4] >= top - line), key=lambda bx: bx[1])
            rest = [bx for bx in rest if bx[4] < top - line]
            text = " ".join(bx[5] for bx in first)
            if not (text == text.upper() and any(ch.isalpha() for ch in text)):
                break
        x0 = first[0][1]
        if x0 <= area.m_lr + indent:
            continue
        # el primer bloque de la columna del valor (líneas seguidas que se solapan en horizontal con la primera: vale para
        # columnas alineadas a la derecha); una etiqueta centrada en la fila cae dentro de su alto, más abajo que la
        # primera línea del valor
        l0, r0 = first[0][1], first[0][3]
        col = sorted((bx for bx in bxs if bx in first or (bx[1] < r0 and bx[3] > l0 and bx[4] <= first[0][4] + line)),
                     key=lambda bx: -bx[4])
        bottom = col[0][2]
        for bx in col[1:]:
            if bx[4] < bottom - gap:
                break
            bottom = min(bottom, bx[2])
        # (de la primera línea del valor hacia abajo: la cabecera repetida, encima, no es la etiqueta)
        if not any(bx[1] <= area.m_lr + indent and bottom <= bx[4] <= first[0][4] + line for bx in bxs):
            bad.append(f"p{p} empieza sin etiqueta a la izquierda: «{text[:60]}» (x = {x0:.0f})")
    return bad


def new_page_starts(pdf_bytes) -> Dict[str, int]:
    """Capítulos que empiezan página por diseño, con su página ({"glosario": 21}; ChapterHeading(new_page=True))."""
    kw = pdfium.PdfDocument(pdf_bytes).get_metadata_dict().get("Keywords") or ""
    return {k: int(v) for k, v in re.findall(r"pagina_nueva_(\w+)=(\d+)", kw)}


def gaps(pdf_bytes, area: Area, max_tail: float, max_block: float, exempt_pages=()) -> List[str]:
    """Rediseño E5: huecos de composición (config/pdf.toml [layout]).

    · al pie: de lo más bajo pintado en el marco (texto, trazo o imagen) a su borde inferior, en cada página salvo la
      última, la anterior a cada capítulo que empieza página por diseño (V7: el glosario; `new_page_starts`) y las de
      `exempt_pages`;
    · entre bloques: el mayor tramo vertical del marco sin nada pintado, entre lo primero y lo último de la página.
    Una tarjeta o un recuadro cuentan como contenido aunque su texto vaya centrado."""
    boxes = content_boxes(pdf_bytes)
    by_page = _frame_boxes(boxes, area)
    n = max([bx[0] for bx in boxes] + [0])
    exempt_pages = set(exempt_pages) | {p - 1 for p in new_page_starts(pdf_bytes).values()}
    bad = []
    for p in range(1, n + 1):
        bxs = by_page.get(p, [])
        if not bxs:
            continue
        if p != n and p not in exempt_pages:
            tail = min(b for _, _, b, _, _, _ in bxs) - area.m_bot
            if tail > max_tail:
                bad.append(f"p{p} hueco al pie de {tail:.0f} pt (> {max_tail:.0f})")
        spans = sorted((b, t) for _, _, b, _, t, _ in bxs)
        top_b, cur_t = spans[0]
        for b, t in spans[1:]:
            if b - cur_t > max_block:
                bad.append(f"p{p} hueco entre bloques de {b - cur_t:.0f} pt (> {max_block:.0f}) a la altura {cur_t:.0f}")
            cur_t = max(cur_t, t)
    return bad


def check(pdf_bytes, area: Area = AREA, min_font: Optional[float] = None) -> List[str]:
    boxes = text_boxes(pdf_bytes)
    out = outside_area(boxes, area) + overlaps(boxes) + too_small(pdf_bytes)
    return out + (small_text(pdf_bytes, min_font) if min_font else [])
