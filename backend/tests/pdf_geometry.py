"""
Fase 1 del plan de fiabilidad (T4): comprobación geométrica del PDF con las cajas de texto de pypdfium2.

(a) Todo texto queda dentro del área útil de la página: en horizontal, el ancho útil del informe
    ([M_LR, PAGE_W − M_LR], donde también se alinean cabecera y pie); en vertical, a más de 1/4" del borde, y ningún
    texto del cuerpo invade la banda de la cabecera o del pie (una caja que cruza el borde del marco).
(b) No hay líneas de bloques distintos que se solapen: dos cajas de texto que se cruzan en horizontal y en vertical
    (más que el redondeo de pdfium) son texto pintado encima de otro texto (p. ej. la "Lectura del análisis" sobre la
    "Composición" de la página 2).

Las cifras de la geometría salen de lib/pdf_report.py (márgenes y tamaño de página): ninguna se copia aquí.
"""
from typing import Dict, List, Tuple

import pypdfium2 as pdfium

from pdf_report import M_BOT, M_LR, M_TOP, PAGE_H, PAGE_W

TOL = 1.0              # pt: redondeo de las cajas de pdfium
SAFE = 18.0            # pt: 1/4" de margen físico de impresión
MIN_V_OVERLAP = 0.35   # fracción de la altura de la caja menor: por debajo es interlineado apretado, no solape

Box = Tuple[int, float, float, float, float, str]   # (página, izq, abajo, der, arriba, texto)


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


def outside_area(boxes: List[Box]) -> List[str]:
    bad = []
    for p, l, b, r, t, txt in boxes:
        if l < M_LR - TOL or r > PAGE_W - M_LR + TOL or b < SAFE or t > PAGE_H - SAFE:
            bad.append(f"p{p} fuera del área útil ({l:.0f},{b:.0f})–({r:.0f},{t:.0f}): {txt[:50]!r}")
        elif (b < M_BOT - TOL < t) or (b < PAGE_H - M_TOP + TOL < t):
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


def check(pdf_bytes) -> List[str]:
    boxes = text_boxes(pdf_bytes)
    return outside_area(boxes) + overlaps(boxes)
