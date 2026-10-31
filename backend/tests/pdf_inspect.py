"""
Rediseño E5: inspección de un PDF con pypdfium2 para las pruebas de `lib/pdf_v2` (sin dependencias nuevas).

  outline(pdf)      marcadores del lector: [(nivel, título, página 1-based)]
  links(pdf)        enlaces de cada página: [Link(page, rect, kind, target)] con kind "internal" (target = página
                    1-based de destino) o "uri" (target = URL)
  page_texts(pdf)   texto de cada página
  font_sizes(pdf)   [(página, tamaño efectivo en pt, carácter)] de cada carácter visible: el tamaño de la fuente por la
                    escala de su matriz (un bloque encogido con KeepInFrame cuenta con su escala real)
"""
import ctypes
from collections import namedtuple
from typing import List, Tuple

import pypdfium2 as pdfium
import pypdfium2.raw as R

Link = namedtuple("Link", "page rect kind target")


def _doc(pdf):
    return pdf if isinstance(pdf, pdfium.PdfDocument) else pdfium.PdfDocument(pdf)


def outline(pdf) -> List[Tuple[int, str, int]]:
    doc = _doc(pdf)
    return [(it.level, it.title, (it.page_index + 1) if it.page_index is not None else None) for it in doc.get_toc()]


def page_texts(pdf) -> List[str]:
    doc = _doc(pdf)
    return [doc[i].get_textpage().get_text_bounded() for i in range(len(doc))]


def links(pdf) -> List[Link]:
    doc = _doc(pdf)
    out: List[Link] = []
    for p in range(len(doc)):
        page = doc[p]
        pos = ctypes.c_int(0)
        lk = R.FPDF_LINK()
        while R.FPDFLink_Enumerate(page.raw, ctypes.byref(pos), ctypes.byref(lk)):
            rect = R.FS_RECTF()
            R.FPDFLink_GetAnnotRect(lk, ctypes.byref(rect))
            box = (rect.left, rect.bottom, rect.right, rect.top)
            dest = R.FPDFLink_GetDest(doc.raw, lk)
            action = R.FPDFLink_GetAction(lk)
            if not dest and action and R.FPDFAction_GetType(action) == R.PDFACTION_GOTO:
                dest = R.FPDFAction_GetDest(doc.raw, action)
            if dest:
                out.append(Link(p + 1, box, "internal", R.FPDFDest_GetDestPageIndex(doc.raw, dest) + 1))
                continue
            if action and R.FPDFAction_GetType(action) == R.PDFACTION_URI:
                n = R.FPDFAction_GetURIPath(doc.raw, action, None, 0)
                buf = ctypes.create_string_buffer(n)
                R.FPDFAction_GetURIPath(doc.raw, action, buf, n)
                out.append(Link(p + 1, box, "uri", buf.value.decode("utf-8", "replace")))
                continue
            out.append(Link(p + 1, box, "other", None))
    return out


def font_sizes(pdf) -> List[Tuple[int, float, str]]:
    doc = _doc(pdf)
    out = []
    for p in range(len(doc)):
        tp = doc[p].get_textpage()
        for i in range(tp.count_chars()):
            ch = chr(R.FPDFText_GetUnicode(tp.raw, i))
            if not ch.strip():
                continue
            size = R.FPDFText_GetFontSize(tp.raw, i)
            m = R.FS_MATRIX()
            if R.FPDFText_GetMatrix(tp.raw, i, ctypes.byref(m)):
                # escala vertical efectiva de la matriz del carácter (texto sin girar: |d|; en general, la norma de (c, d))
                size *= (m.c ** 2 + m.d ** 2) ** 0.5 or 1.0
            out.append((p + 1, size, ch))
    return out
