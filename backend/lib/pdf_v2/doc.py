"""
Rediseño E5 (Task 1): base del documento PDF.

`ReportDoc` es un `BaseDocTemplate` carta con tres plantillas:
  · portada: banda de marca arriba y aviso legal abajo;
  · índice: cabecera con la empresa y pie con la fecha de los datos y "Página x de y";
  · cuerpo: lo mismo y, en el pie, "↑ índice" enlazado al índice.

Cada capítulo empieza con un `ChapterHeading`: al dibujarse deja un destino con nombre (el enlace del índice y del
marcador del lector apunta a su línea, no a la página entera) y, en `afterFlowable`, el documento lo registra en el
índice (`Index`). El total de páginas del pie sale de la pasada anterior: `_allSatisfied` exige que el índice y el
total no cambien entre dos pasadas, así que en la última el "de y" es exacto.

Ninguna cifra se calcula aquí: el documento solo maqueta.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple
from xml.sax.saxutils import escape

from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Flowable, Frame, KeepInFrame, NextPageTemplate,
                                PageTemplate, Paragraph, Table, TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

from . import theme as T

INDEX_KEY = "indice"
COVER_KEY = "portada"
INDEX_LABEL = "↑ índice"


# ══════════════════════════════ estilos ══════════════════════════════
def styles():
    F = T.FONT
    s = {
        "body": ParagraphStyle("body", fontName=F["regular"], fontSize=T.BODY, leading=T.BODY_LEADING,
                               textColor=T.TEXT_2, alignment=TA_LEFT, allowWidows=0, allowOrphans=0),
        "body_ink": ParagraphStyle("body_ink", fontName=F["regular"], fontSize=T.BODY, leading=T.BODY_LEADING,
                                   textColor=T.INK),
        "title": ParagraphStyle("title", fontName=F["semibold"], fontSize=T.TITLE, leading=T.TITLE_LEADING,
                                textColor=T.INK),
        "subtitle": ParagraphStyle("subtitle", fontName=F["semibold"], fontSize=12, leading=15, textColor=T.INK),
        "table": ParagraphStyle("table", fontName=F["regular"], fontSize=T.TABLE, leading=T.TABLE_LEADING,
                                textColor=T.TEXT_2),
        "table_b": ParagraphStyle("table_b", fontName=F["semibold"], fontSize=T.TABLE, leading=T.TABLE_LEADING,
                                  textColor=T.INK),
        "table_r": ParagraphStyle("table_r", fontName=F["regular"], fontSize=T.TABLE, leading=T.TABLE_LEADING,
                                  textColor=T.INK, alignment=TA_RIGHT),
        "small": ParagraphStyle("small", fontName=F["regular"], fontSize=T.SMALL, leading=T.SMALL_LEADING,
                                textColor=T.TEXT_3, allowWidows=0, allowOrphans=0),
        "label": ParagraphStyle("label", fontName=F["semibold"], fontSize=T.LABEL, leading=T.LABEL + 2.5,
                                textColor=T.TEXT_3),
        "toc": ParagraphStyle("toc", fontName=F["medium"], fontSize=T.BODY, leading=T.BODY_LEADING,
                              textColor=T.GOOD),
        "toc_r": ParagraphStyle("toc_r", fontName=F["medium"], fontSize=T.BODY, leading=T.BODY_LEADING,
                                textColor=T.TEXT_3, alignment=TA_RIGHT),
    }
    return s


# Letras griegas que usa el motor (β de la beta, σ de la volatilidad) y que Geist no trae: van en Symbol, una de
# las 14 fuentes estándar de PDF (sin incrustar). Cualquier otro carácter que falte lo detecta la prueba de cobertura.
FALLBACK_GLYPHS = "αβγδεθλμπρσΔΣΩ"


def esc(text) -> str:
    """Texto del motor listo para un Paragraph: escapado y con las letras griegas en Symbol."""
    out = escape("" if text is None else str(text))
    for ch in FALLBACK_GLYPHS:
        if ch in out:
            out = out.replace(ch, f'<font name="Symbol">{ch}</font>')
    return out


def covered(ch: str) -> bool:
    """¿Se puede pintar `ch` en el informe? (Geist o la reserva de Symbol)."""
    if ch in FALLBACK_GLYPHS or ord(ch) < 128:
        return True
    from reportlab.pdfbase import pdfmetrics
    font = pdfmetrics.getFont(T.FONT["regular"])
    face = getattr(font, "face", None)
    return face is None or ord(ch) in face.charToGlyph


# ══════════════════════════════ piezas de texto ══════════════════════════════
class Eyebrow(Flowable):
    """Etiqueta en versalitas (8 pt, espaciada): una línea; si no cabe, se parte en palabras."""

    def __init__(self, text, color=None, size=T.LABEL, space_after=3):
        super().__init__()
        self.text = (text or "").upper()
        self.color = color or T.TEXT_3
        self.size = size
        self.spaceAfter = space_after
        self._lines: List[str] = []

    def _width(self, s):
        return stringWidth(s, T.FONT["semibold"], self.size) + T.LABEL_SPACING * max(len(s) - 1, 0)

    def wrap(self, aw, ah):
        words, lines, cur = self.text.split(), [], ""
        for w in words:
            nxt = f"{cur} {w}".strip()
            if cur and self._width(nxt) > aw:
                lines.append(cur)
                cur = w
            else:
                cur = nxt
        lines.append(cur)
        self._lines = lines
        self.width = aw
        self.height = len(lines) * (self.size + 2.5)
        return aw, self.height

    def draw(self):
        c = self.canv
        c.setFont(T.FONT["semibold"], self.size)
        c.setFillColor(self.color)
        lh = self.size + 2.5
        for i, ln in enumerate(self._lines):
            c.drawString(0, self.height - (i + 1) * lh + 2.2, ln, charSpace=T.LABEL_SPACING)


class ChapterHeading(Flowable):
    """Apertura de un capítulo: etiqueta ("4 · Calidad") y título de 18 pt. Deja el destino con nombre `key` en su
    línea y el marcador del lector; el documento lo añade al índice (`toc_text`). `new_page`: el capítulo empieza
    página por diseño (V7: el glosario); lo declara en las palabras clave del PDF ("pagina_nueva_glosario=21") para que
    la geometría no cuente como hueco el pie de la página anterior."""

    def __init__(self, key: str, eyebrow: str, title: str, toc_text: str, level: int = 0, space_before=6,
                 space_after=8, new_page: bool = False):
        super().__init__()
        self.key, self.eyebrow, self.title, self.toc_text, self.level = key, eyebrow, title, toc_text, level
        self.new_page = new_page
        self.spaceBefore, self.spaceAfter = space_before, space_after
        self._eb = Eyebrow(eyebrow, color=T.GOOD, space_after=0)
        self._title = Paragraph(esc(title), styles()["title"])

    def wrap(self, aw, ah):
        _, h1 = self._eb.wrap(aw, ah)
        _, h2 = self._title.wrap(aw, ah)
        self.width, self._h1, self._h2 = aw, h1, h2
        self.height = h1 + 3 + h2
        return aw, self.height

    def draw(self):
        c = self.canv
        c.bookmarkHorizontal(self.key, 0, self.height + 6)
        c.addOutlineEntry(self.toc_text, self.key, level=self.level, closed=False)
        if self.new_page:
            prev = getattr(c._doc.info, "keywords", "") or ""
            c.setKeywords(f"{prev} pagina_nueva_{self.key}={c.getPageNumber()}".strip())
        self._eb.drawOn(c, 0, self.height - self._h1)
        self._title.drawOn(c, 0, 0)


class Anchor(Flowable):
    """Destino con nombre y marcador del lector sin tamaño (portada, índice)."""
    _ZEROSIZE = 1   # sin esto, un bloque (KeepInFrame) descarta los flowables de alto 0 y el destino no existe

    def __init__(self, key: str, outline: Optional[str] = None):
        super().__init__()
        self.key, self.outline = key, outline

    def wrap(self, aw, ah):
        return 0, 0

    def draw(self):
        self.canv.bookmarkHorizontal(self.key, 0, 8)
        if self.outline:
            self.canv.addOutlineEntry(self.outline, self.key, level=0, closed=False)


class Index(TableOfContents):
    """Índice enlazado: título y página de cada entrada, los dos con enlace, con separador punteado.

    `expected` son las entradas que tendrá ((texto, clave)): en la primera pasada el índice ya mide lo mismo que en la
    última (mismas filas con página provisional), así que ni la portada ni el resumen se mueven entre pasadas.
    `fixed` son entradas de página conocida que no pasan por un `ChapterHeading` ((texto, clave, página)); van en la
    posición `fixed_at` (por defecto, al final). Con `columns` > 1 las entradas se reparten en rejilla, fila a fila."""

    def __init__(self, expected: Sequence[Tuple[str, str]], fixed: Sequence[Tuple[str, str, int]] = (),
                 fixed_at: Optional[int] = None, columns: int = 1, gutter: float = 16):
        super().__init__(dotsMinLevel=-1)
        self.expected, self.fixed, self.columns, self.gutter = list(expected), list(fixed), columns, gutter
        self.fixed_at = fixed_at

    def entries(self):
        got = self._lastEntries or [(0, text, 0, key) for text, key in self.expected]
        out = [(text, page, key) for _lvl, text, page, key in got]
        at = len(out) if self.fixed_at is None else self.fixed_at
        return out[:at] + [(t, p, k) for t, k, p in self.fixed] + out[at:]

    def _cell(self, text, page, key, width):
        S = styles()
        num_w = 28
        t = Table([[Paragraph(f'<a href="#{key}">{esc(text)}</a>', S["toc"]),
                    Paragraph(f'<a href="#{key}">{page or "–"}</a>', S["toc_r"])]], colWidths=[width - num_w, num_w])
        t.setStyle(TableStyle([
            ("LINEBELOW", (0, 0), (-1, -1), 0.6, T.LINE_DOT, None, (1, 2)),
            ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
            ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ]))
        return t

    def wrap(self, aw, ah):
        n = max(self.columns, 1)
        cw = (aw - self.gutter * (n - 1)) / n
        cells = [self._cell(t, p, k, cw) for t, p, k in self.entries()]
        rows = []
        for i in range(0, len(cells), n):
            row = []
            for j, cell in enumerate(cells[i:i + n] + [""] * (n - len(cells[i:i + n]))):
                if j:
                    row.append("")
                row.append(cell)
            rows.append(row)
        widths = []
        for j in range(n):
            if j:
                widths.append(self.gutter)
            widths.append(cw)
        self._table = Table(rows, colWidths=widths)
        self._table.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                                         ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
        return self._table.wrap(aw, ah)


class FitPage(KeepInFrame):
    """Bloque que debe caber en el resto de la página: encoge (modo shrink) y declara su escala en las palabras clave
    del PDF ("escala_portada=1.000"), como el informe actual; la geometría falla por debajo de `MIN_SCALE`."""

    def __init__(self, tag, max_w, max_h, content):
        super().__init__(max_w, max_h, content, mode="shrink")
        self._tag = tag

    def drawOn(self, canv, x, y, _sW=0):
        prev = getattr(canv._doc.info, "keywords", "") or ""
        canv.setKeywords(f"{prev} escala_{self._tag}={1.0 / getattr(self, '_scale', 1.0):.3f}".strip())
        return super().drawOn(canv, x, y, _sW)


# ══════════════════════════════ documento ══════════════════════════════
@dataclass
class DocMeta:
    name: str
    symbol: str
    report_date: str              # fecha del informe ("17 de octubre de 2026")
    data_note: str                # fecha de los datos para el pie ("Precio al 14 oct 2026 · estados a 30 jun 2026")
    title: str = ""
    subject: str = "Informe de análisis Finanzer"
    keywords: List[str] = field(default_factory=list)


class ReportDoc(BaseDocTemplate):
    def __init__(self, buf, meta: DocMeta, **kw):
        self.meta = meta
        self._total_prev: Optional[int] = None
        self._total_now: Optional[int] = None
        super().__init__(buf, pagesize=(T.PAGE_W, T.PAGE_H), leftMargin=T.M_LR, rightMargin=T.M_LR,
                         topMargin=T.M_TOP, bottomMargin=T.M_BOT, title=meta.title or f"Informe Finanzer {meta.symbol}",
                         author="Finanzer", subject=meta.subject, creator="Finanzer · pdf_v2", **kw)
        frame = Frame(T.M_LR, T.M_BOT, T.CW, T.CH, id="main", leftPadding=0, rightPadding=0, topPadding=0,
                      bottomPadding=0)
        self.addPageTemplates([
            PageTemplate(id="cover", frames=[frame], onPage=self._decor_cover),
            PageTemplate(id="index", frames=[frame], onPage=self._decor_index),
            PageTemplate(id="body", frames=[frame], onPage=self._decor_body),
        ])

    # ── pasadas: índice y total de páginas estables ──
    def build(self, flowables, **kw):
        super().build(flowables, **kw)
        self._total_now = self.page

    def _allSatisfied(self):
        ok = super()._allSatisfied() and self._total_prev == self._total_now
        self._total_prev = self._total_now
        return ok

    def afterFlowable(self, flowable):
        if isinstance(flowable, ChapterHeading):
            self.notify("TOCEntry", (flowable.level, flowable.toc_text, self.page, flowable.key))

    def render(self, story):
        """Construye el PDF (varias pasadas hasta que el índice y el total de páginas no cambian)."""
        self.multiBuild(story)

    @property
    def total_pages(self) -> Optional[int]:
        return self._total_prev

    # ── decoración ──
    def _page_label(self, page):
        return f"Página {page} de {self._total_prev}" if self._total_prev else f"Página {page}"

    def _rules(self, c, top=True, bottom=True):
        c.setStrokeColor(T.LINE)
        c.setLineWidth(0.6)
        if top:
            y = T.HEADER_Y - T.RULE_GAP
            c.line(T.M_LR, y, T.PAGE_W - T.M_LR, y)
        if bottom:
            y = T.FOOTER_Y + T.LABEL + T.RULE_GAP - 2
            c.line(T.M_LR, y, T.PAGE_W - T.M_LR, y)

    def _brand(self, c, x, y, size=11):
        """La marca, como en la cabecera de la web: el logo en su placa nocturna a 1,8 veces el cuerpo del nombre y
        «Finanzer» en Manrope 700 en tinta, a 0,28 del alto de la placa; la placa se centra en la media altura de las
        mayúsculas del nombre. `y` es la línea base del nombre; devuelve el ancho del conjunto."""
        name_w = stringWidth("Finanzer", T.FONT["brand"], size)
        lw = 0
        if T.BRAND_LOGO:
            h = 1.8 * size
            lw = h * T.BRAND_LOGO_RATIO
            mid = y + 0.36 * size                         # media altura de mayúscula del nombre
            c.drawImage(T.BRAND_LOGO, x, mid - h / 2, lw, h, mask="auto")
            lw += 0.28 * h
        c.setFont(T.FONT["brand"], size)
        c.setFillColor(T.INK)
        c.drawString(x + lw, y, "Finanzer")
        return lw + name_w

    def _decor_cover(self, c, doc):
        c.saveState()
        self._brand(c, T.M_LR, T.HEADER_Y, size=12)
        c.setFont(T.FONT["semibold"], T.LABEL)
        c.setFillColor(T.TEXT_3)
        right = f"INFORME DE ANÁLISIS · {self.meta.report_date.upper()}"
        w = stringWidth(right, T.FONT["semibold"], T.LABEL) + T.LABEL_SPACING * (len(right) - 1)
        c.drawString(T.PAGE_W - T.M_LR - w, T.HEADER_Y + 1, right, charSpace=T.LABEL_SPACING)
        self._rules(c)
        self._footer(c, doc, "Documento informativo · no constituye asesoría de inversión", link_index=False)
        c.restoreState()

    def _running_header(self, c):
        x = T.M_LR + self._brand(c, T.M_LR, T.HEADER_Y, size=10) + 6
        c.setFont(T.FONT["regular"], T.SMALL)
        c.setFillColor(T.TEXT_3)
        c.drawString(x, T.HEADER_Y, f"·  Informe de análisis")
        c.setFont(T.FONT["semibold"], T.SMALL)
        c.setFillColor(T.INK)
        c.drawRightString(T.PAGE_W - T.M_LR, T.HEADER_Y, f"{self.meta.name} · {self.meta.symbol}")

    def _decor_index(self, c, doc):
        c.saveState()
        self._running_header(c)
        self._rules(c)
        self._footer(c, doc, self.meta.data_note, link_index=False)
        c.restoreState()

    def _decor_body(self, c, doc):
        c.saveState()
        self._running_header(c)
        self._rules(c)
        self._footer(c, doc, self.meta.data_note, link_index=True)
        c.restoreState()

    def _footer(self, c, doc, left_text, link_index):
        y = T.FOOTER_Y
        c.setFont(T.FONT["regular"], T.SMALL)
        c.setFillColor(T.TEXT_3)
        c.drawString(T.M_LR, y, left_text)
        c.drawRightString(T.PAGE_W - T.M_LR, y, self._page_label(doc.page))
        if link_index:
            c.setFont(T.FONT["medium"], T.SMALL)
            c.setFillColor(T.GOOD)
            w = stringWidth(INDEX_LABEL, T.FONT["medium"], T.SMALL)
            x = (T.PAGE_W - w) / 2
            c.drawString(x, y, INDEX_LABEL)
            c.linkRect("", INDEX_KEY, (x - 4, y - 4, x + w + 4, y + T.SMALL + 2), relative=0, thickness=0)


def start_on(template: str):
    """Cambia la plantilla de la página siguiente (portada → índice → cuerpo)."""
    return NextPageTemplate(template)


# ══════════════════════════════ composición sin huecos ══════════════════════════════
MIN_TABLE_PART = 3      # cada parte de una tabla partida: la cabecera y al menos dos filas


def _is_title(f) -> bool:
    return getattr(f, "is_title", False)


class Stack(Flowable):
    """Bloque indivisible de varios flowables uno debajo de otro (p. ej. un subtítulo y su gráfica)."""

    def __init__(self, items):
        super().__init__()
        self.items = list(items)

    def getSpaceBefore(self):
        return self.items[0].getSpaceBefore() if self.items else 0

    def wrap(self, aw, ah):
        self._sizes = []
        h = 0
        for i, f in enumerate(self.items):
            c = getattr(self, "canv", None)
            _, fh = f.wrapOn(c, aw, ah) if c is not None else f.wrap(aw, ah)
            gap = max(f.getSpaceAfter(), self.items[i + 1].getSpaceBefore()) if i < len(self.items) - 1 else 0
            self._sizes.append((fh, gap))
            h += fh + gap
        self.width, self.height = aw, h
        return aw, h

    def draw(self):
        y = self.height
        for f, (fh, gap) in zip(self.items, self._sizes):
            y -= fh
            f.drawOn(self.canv, 0, y)
            y -= gap

    def split(self, aw, ah):
        """Se parte entre sus piezas (o dentro de una pieza que se parta, p. ej. una lista de barras), nunca dejando
        un subtítulo solo al pie."""
        c, used = self.canv, 0.0
        for i, f in enumerate(self.items):
            _, fh = f.wrapOn(c, aw, ah)
            gap = max(f.getSpaceAfter(), self.items[i + 1].getSpaceBefore()) if i < len(self.items) - 1 else 0
            if used + fh <= ah:
                used += fh + gap
                continue
            parts = f.splitOn(c, aw, ah - used) if ah - used > 0 else []
            if isinstance(f, Table):
                # una tabla no se parte dejando una fila sola a un lado: si pasaría, se lleva una fila más abajo
                room = ah - used
                while parts and any(len(p._cellvalues) < MIN_TABLE_PART for p in parts) and room > 40:
                    room -= 10
                    parts = f.splitOn(c, aw, room)
                if parts and any(len(p._cellvalues) < MIN_TABLE_PART for p in parts):
                    parts = []
            head = self.items[:i] + ([parts[0]] if parts else [])
            tail = (list(parts[1:]) if parts else [f]) + self.items[i + 1:]
            if not head or all(_is_title(x) for x in head) or not tail:
                return []
            return [Stack(head), Stack(tail)]
        return [self]


class Unit(Stack):
    """V4b: un Stack que no se parte: si no cabe en lo que queda de página, pasa entero a la siguiente (un subtítulo,
    su texto de contexto y la figura que explican)."""

    def split(self, aw, ah):
        return []


class FloatGroup(Flowable):
    """Un bloque visual indivisible (`unit`) seguido del resto de su capítulo (`rest`). Si el bloque no cabe en lo
    que queda de página, el texto que le sigue (párrafos y filas de tabla, que sí se parten) llena ese espacio y el
    bloque pasa a la página siguiente, como una figura flotante: la página no termina con su hueco detrás. Si cabe,
    todo sigue en su orden."""

    def __init__(self, unit, rest):
        super().__init__()
        self.unit, self.rest = unit, list(rest)

    def getSpaceBefore(self):
        return self.unit.getSpaceBefore()

    def wrap(self, aw, ah):
        # Siempre «no cabe entero»: el marco llama a split, que devuelve las piezas en el orden que toca.
        self.width, self.height = aw, ah + 1
        return aw, ah + 1

    def draw(self):  # pragma: no cover - nunca se dibuja entero: siempre se parte
        pass

    def split(self, aw, ah):
        c = self.canv
        _, uh = self.unit.wrapOn(c, aw, ah)
        # `ah` ya descuenta el espacio previo del grupo (el del bloque): el marco lo resta antes de llamar a split
        if uh <= ah:
            return [self.unit] + self.rest
        taken, remaining, rest = [], ah, list(self.rest)
        while rest:
            f = rest[0]
            if isinstance(f, CondPageBreak):
                if remaining < f.height:
                    break
                rest.pop(0)
                continue
            # a la primera pieza el marco le aplica su propio espacio previo en lugar del del grupo (ya descontado)
            sb = f.getSpaceBefore() if taken else max(0.0, f.getSpaceBefore() - self.getSpaceBefore())
            sa = f.getSpaceAfter()
            if not isinstance(f, FloatGroup):
                _, fh = f.wrapOn(c, aw, remaining)
                if fh + sb + sa <= remaining:
                    taken.append(rest.pop(0))
                    remaining -= fh + sb + sa
                    continue
            parts = f.splitOn(c, aw, remaining - sb) if remaining - sb > 0 else []
            # solo vale una primera pieza que de verdad cabe (un FloatGroup anidado puede devolver su bloque entero)
            if parts and parts[0].wrapOn(c, aw, remaining - sb)[1] + sb <= remaining:
                taken.append(parts[0])
                rest = list(parts[1:]) + rest[1:]
            break
        if not rest:
            # nada más que adelantar (fin del capítulo): el bloque sigue en su sitio y, si se puede partir, se parte
            if taken:
                return taken + [self.unit]
            parts = self.unit.splitOn(c, aw, ah) if hasattr(self.unit, "split") else []
            return list(parts) if parts and parts[0].wrapOn(c, aw, ah)[1] <= ah else []
        if not taken:
            # nada de lo que sigue cabe: antes que dejar el hueco, el bloque se parte si puede (entre sus piezas o
            # dentro de una tabla o un párrafo, nunca un título solo) y su resto abre la página siguiente
            parts = self.unit.splitOn(c, aw, ah) if hasattr(self.unit, "split") else []
            if parts and parts[0].wrapOn(c, aw, ah)[1] <= ah:
                return list(parts) + rest
            return []
        return taken + [FloatGroup(self.unit, rest)]
