"""
Rediseño E5 (Task 2): componentes de dibujo del PDF nuevo.

Cada parte es un `Flowable` de reportlab que solo maqueta lo que ya trae el análisis (`display`, `display.extended`,
la serie de `/api/v2/prices` y los segmentos de `/api/v2/segments`): ninguna lectura se recalcula. Una parte sin
dato no reserva su caja (revisión del PM de E5): se reduce a una línea con el título del bloque y el motivo en texto
secundario (`missing_line`), y lo que sigue sube a ocupar el sitio.

  ScoreScale     escala de puntuación (tramos con las bandas del motor, marca, valor, base y desglose)
  FigureCard     tarjeta de cifra (etiqueta, valor, referencia y lectura en pastilla)
  tech_table     tabla técnica (Métrica en negrita + significado · Empresa · Referencia · Brecha · Lectura)
  CategoryBars   barras de las categorías de la calidad (x / 20)
  Range52        rango de 52 semanas (tramos de posición en grises y marca del precio)
  Piotroski      Piotroski 3 × 3 (criterio, cumple o no, y su detalle o los valores de los dos años)
  PriceChart     precio en base 100: empresa frente al S&P 500 y al ETF del sector (1 año o 5 años)
  SegmentBars    ingresos por segmento del último ejercicio
  History10      historia financiera de 10 ejercicios
  equal_row      fila de tarjetas de igual ancho e igual alto
"""
import math
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from reportlab.lib import colors as RLC
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Flowable, Paragraph, Table, TableStyle

import price_returns
from settings import cfg

from . import theme as T
from .doc import esc

F = T.FONT
PAD = 10                      # relleno interior de las tarjetas
MESES_CORTOS = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")


# ══════════════════════════════ utilidades de dibujo ══════════════════════════════
def _ps(name, font="regular", size=T.BODY, leading=None, color=None, align=None):
    st = ParagraphStyle(name, fontName=F[font], fontSize=size, leading=leading or round(size * 1.35, 2),
                        textColor=color or T.TEXT_2)
    if align == "right":
        st.alignment = TA_RIGHT
    elif align == "center":
        st.alignment = TA_CENTER
    return st


def _para(text, style, width):
    p = Paragraph(text, style)
    _, h = p.wrap(width, 10_000)
    return p, h


def _w(s, font, size, spacing=0.0):
    return stringWidth(s, F[font], size) + spacing * max(len(s) - 1, 0)


def _card(c, w, h, fill=None, stroke=None):
    c.setFillColor(fill or T.CARD)
    c.setStrokeColor(stroke or T.LINE)
    c.setLineWidth(0.6)
    c.roundRect(0, 0, w, h, T.RADIUS, stroke=1, fill=1)


def _label(c, x, y, text, color=None, size=T.LABEL):
    c.setFont(F["semibold"], size)
    c.setFillColor(color or T.TEXT_3)
    c.drawString(x, y, text.upper(), charSpace=T.LABEL_SPACING)


def _fit_label(text, width, size=T.LABEL):
    """Etiqueta en versalitas partida en líneas que caben en `width`."""
    words, lines, cur = (text or "").upper().split(), [], ""
    for wd in words:
        nxt = f"{cur} {wd}".strip()
        if cur and _w(nxt, "semibold", size, T.LABEL_SPACING) > width:
            lines.append(cur)
            cur = wd
        else:
            cur = nxt
    if cur:
        lines.append(cur)
    return lines


LABEL_LH = T.LABEL + 2.5      # interlineado de las etiquetas


class _Fixed(Flowable):
    """Flowable con alto fijo opcional (`fixed_height`) para igualar filas de tarjetas; `label_lines` reserva las
    líneas de etiqueta de la tarjeta vecina más larga."""
    fixed_height: Optional[float] = None
    label_lines: int = 0

    def natural_height(self, w) -> float:  # pragma: no cover - lo implementa cada parte
        raise NotImplementedError

    def label_count(self, w) -> int:
        """Líneas de la etiqueta con el ancho `w` (para alinear las cifras de una fila)."""
        return len(_fit_label(getattr(self, "title", ""), w - 2 * PAD))

    def wrap(self, aw, ah):
        self.width = aw
        nat = self.natural_height(aw)
        self.height = max(nat, self.fixed_height or 0)
        return aw, self.height


class Sized(Flowable):
    """Tabla que se construye con el ancho disponible (`build(ancho) -> Table`). Dentro de un bloque que encoge
    (KeepInFrame) el ancho disponible crece en la misma proporción que la escala: una tabla de anchos fijos quedaría
    más estrecha que el resto y centrada."""

    def __init__(self, build: Callable[[float], Flowable]):
        super().__init__()
        self.build = build
        self._t = None

    def wrap(self, aw, ah):
        self._t = self.build(aw)
        self.width, self.height = self._t.wrap(aw, ah)
        return self.width, self.height

    def draw(self):
        self._t.drawOn(self.canv, 0, 0)


def equal_row(cells: Sequence[_Fixed], width: Optional[float] = None, gutter: float = T.GUTTER) -> Sized:
    """Fila de tarjetas de igual ancho y alto (spec §5): el alto es el de la más alta; se ajusta al ancho disponible."""
    return Sized(lambda aw: _equal_row_table(cells, aw, gutter))


def _equal_row_table(cells: Sequence[_Fixed], width: float, gutter: float) -> Table:
    n = len(cells)
    cw = (width - gutter * (n - 1)) / n
    # Etiquetas de distinto largo: todas reservan las líneas de la más larga, así las cifras quedan alineadas.
    lines = max(cell.label_count(cw) for cell in cells)
    for cell in cells:
        cell.label_lines = lines
    h = max(cell.natural_height(cw) for cell in cells)
    for cell in cells:
        cell.fixed_height = h
    row, widths = [], []
    for i, cell in enumerate(cells):
        row.append(cell)
        widths.append(cw)
        if i < n - 1:
            row.append("")
            widths.append(gutter)
    t = Table([row], colWidths=widths)
    t.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                           ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                           ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    return t


class Pill(Flowable):
    """Pastilla de lectura: texto del tono sobre su fondo apagado."""

    def __init__(self, text, tone="neutral", size=8.5, max_width=None):
        super().__init__()
        self.text, self.tone, self.size, self.max_width = text or "", T.tone(tone), size, max_width

    def wrap(self, aw, ah):
        limit = min(aw, self.max_width or aw)
        self._lines = _wrap_words(self.text, "semibold", self.size, limit - 12)
        self.width = min(limit, max(_w(ln, "semibold", self.size) for ln in self._lines) + 12)
        self.height = len(self._lines) * (self.size + 2) + 5
        return self.width, self.height

    def draw(self):
        c = self.canv
        c.setFillColor(T.PILL_BG[self.tone])
        c.roundRect(0, 0, self.width, self.height, min(self.height / 2, 7), stroke=0, fill=1)
        c.setFillColor(T.TONE_TEXT[self.tone])
        c.setFont(F["semibold"], self.size)
        for i, ln in enumerate(self._lines):
            c.drawCentredString(self.width / 2, self.height - 2.5 - (i + 1) * (self.size + 2) + 2.3, ln)


def _wrap_words(text, font, size, width) -> List[str]:
    words, lines, cur = (text or "").split(), [], ""
    for wd in words:
        nxt = f"{cur} {wd}".strip()
        if cur and _w(nxt, font, size) > width:
            lines.append(cur)
            cur = wd
        else:
            cur = nxt
    lines.append(cur)
    return lines


def missing_line(title: str, reason: Optional[str], space_before: float = 0) -> Paragraph:
    """Un bloque sin dato no reserva su caja (revisión del PM de E5): una línea con el título del bloque y el motivo
    en texto secundario; lo que sigue sube a ocupar el sitio."""
    st = _ps("miss", "regular", T.SMALL, leading=T.SMALL_LEADING, color=T.TEXT_3)
    st.spaceBefore = space_before
    head = f"<font name='{F['semibold']}' size='{T.TABLE}' color='{T.INK.hexval()}'>{esc(title)}</font>"
    reason = (reason or "").strip().rstrip(".")
    return Paragraph(head + (f" · {esc(reason)}" if reason else ""), st)


class _Absent:
    """Partes de dibujo: sin dato, se reducen a `missing_line` (una línea), nunca a un hueco de su tamaño."""

    _miss = None

    def _absent_wrap(self, aw, ah, title, reason):
        self._miss = missing_line(title, reason)
        _, h = self._miss.wrap(aw, ah)
        self.width, self.height = aw, h
        return aw, h

    def _absent_draw(self) -> bool:
        if self._miss is None:
            return False
        self._miss.drawOn(self.canv, 0, 0)
        return True


# ══════════════════════════════ escalas de puntuación ══════════════════════════════
@dataclass
class Segment:
    label: str
    range: str
    frm: float
    to: float
    tone: str


@dataclass
class ScaleModel:
    kind: str
    score: Optional[float]
    level: Optional[str]
    segments: List[Segment]
    pin: Optional[float]


def _seg_tone(i, n, confidence=False):
    if confidence:
        return "warn" if i == 0 else "good" if i == n - 1 else "neutral"
    return "bad" if i == 0 else "good" if i == n - 1 else "warn" if i == 1 else "neutral"


def build_scale(kind: str, score: Optional[float], level: Optional[str]) -> ScaleModel:
    """Puntuación 0–100 con las bandas del motor (`thresholds.score.<kind>`), del peor tramo al mejor
    (misma regla que la cabecera de la web, frontend/src/v2/lib/scale.ts)."""
    bands, labels = cfg(f"thresholds.score.{kind}.bands"), cfg(f"thresholds.score.{kind}.labels")
    if kind == "price_l1":              # versión 1.0: «frente a su sector» (las claves de la config no cambian)
        from display import L1_LEVEL_SHORT
        labels = [L1_LEVEL_SHORT.get(x, x) for x in labels]
    cuts, names = list(reversed(bands)), list(reversed(labels))
    edges = [0, *cuts, 100]
    last = len(names) - 1
    segs = [Segment(n, f"<{edges[i + 1]}" if i == 0 else f"{edges[i]}+" if i == last else f"{edges[i]}–{edges[i + 1]}",
                    edges[i], edges[i + 1], _seg_tone(i, len(names))) for i, n in enumerate(names)]
    pin = None if score is None else min(max(float(score), 0.0), 100.0)
    return ScaleModel(kind, score, level, segs, pin)


def build_level_scale(level: Optional[str]) -> ScaleModel:
    """Consistencia (Fase 1 · pendientes, 7-nov-2026; lib/consistency.py): dos niveles, tramos iguales y la marca en
    el centro del nivel."""
    import consistency
    names = list(reversed(consistency.LEVELS))   # «mixta», «consistente»
    width = 100 / len(names)
    segs = [Segment(n, "", i * width, (i + 1) * width, _seg_tone(i, len(names), confidence=True))
            for i, n in enumerate(names)]
    hit = next((s for s in segs if level and s.label == level.lower()), None)
    return ScaleModel("confidence", None, level, segs, None if hit is None else (hit.frm + hit.to) / 2)


def bands_line(model: ScaleModel) -> str:
    """Leyenda de los tramos ("débil <45 · media 45–65 · sólida 65–85 · excelente 85+"). En la confianza, cuánto acerca
    cada nivel el precio a su neutro (`[score.price] confidence_factor` y `neutral`)."""
    if model.kind == "confidence":
        return " · ".join(s.label for s in model.segments)
    return " · ".join(f"{s.label} {s.range}".strip() for s in model.segments)


class ScoreScale(_Fixed):
    """Puntuación con su escala y su base (spec §3.1): título y pregunta, cifra grande con su nivel, barra con los
    tramos del motor y la marca del valor, leyenda de tramos, base y desglose (siempre visible)."""

    BAR_H = 6
    VALUE = 20
    MINI = 12
    MINI_LINE = 11

    def __init__(self, model: ScaleModel, title: str, question: str, display: str, suffix: Optional[str],
                 tone: str, base: str, mini: Sequence[Tuple[str, str, Optional[str]]] = (),
                 level_tone: Optional[str] = None):
        super().__init__()
        self.model, self.title, self.question = model, title, question
        self.display, self.suffix, self.tone = display, suffix, T.tone(tone)
        self.level_tone = T.tone(level_tone) if level_tone else self.tone
        self.base, self.mini = base, list(mini)

    def _layout(self, w):
        iw = w - 2 * PAD
        self._title_lines = _fit_label(self.title, iw)
        self._title_lines += [""] * max(self.label_lines - len(self._title_lines), 0)
        self._q, self._qh = _para(esc(self.question), _ps("q", "regular", T.SMALL, color=T.TEXT_3), iw)
        # la confianza enseña sus niveles bajo la barra; su efecto (acercar el precio a 50) lo cuenta la lectura
        legend = bands_line(self.model) if self.model.kind != "confidence" else ""
        self._legend, self._lh = (_para(esc(legend), _ps("lg", "regular", T.LABEL, leading=10.5, color=T.TEXT_3), iw)
                                  if legend else (None, 0))
        self._base, self._bh = _para(esc(self.base), _ps("b", "regular", T.SMALL, leading=T.SMALL_LEADING,
                                                         color=T.TEXT_2), iw)
        # desglose: el nombre completo, partido en líneas si no cabe junto a su cifra (nunca con «…»)
        self._mini_rows = []
        for name, value, tone in self.mini:
            lines = _wrap_words(name, "regular", T.SMALL, iw - _w(value, "semibold", T.SMALL) - 8)
            self._mini_rows.append((lines, value, tone, self.MINI + (len(lines) - 1) * self.MINI_LINE))
        self._mini_h = sum(r[3] for r in self._mini_rows)
        # bajo la barra: los nombres de nivel en la confianza; en las puntuaciones, la leyenda ya da tramos y cortes
        ticks = 10.5 + 3 if self.model.kind == "confidence" else 0
        top = PAD + len(self._title_lines) * LABEL_LH + self._qh + 6 + self.VALUE + 8
        bar = 7 + self.BAR_H + ticks
        legend_h = (self._lh + 4) if self._legend else 0
        foot = 6 + self._bh + (8 + self._mini_h if self.mini else 0) + PAD
        return top + bar + legend_h + foot

    def natural_height(self, w):
        return self._layout(w)

    def draw(self):
        c, w, h = self.canv, self.width, self.height
        self._layout(w)
        iw = w - 2 * PAD
        _card(c, w, h)
        y = h - PAD
        for ln in self._title_lines:
            y -= LABEL_LH
            _label(c, PAD, y + 2.5, ln)
        y -= self._qh
        self._q.drawOn(c, PAD, y)
        y -= 6 + self.VALUE
        c.setFont(F["semibold"], self.VALUE)
        c.setFillColor(T.TONE_TEXT[self.tone] if self.tone != "neutral" else T.INK)
        c.drawString(PAD, y + 4, self.display)
        if self.suffix:
            vx = PAD + _w(self.display, "semibold", self.VALUE) + 5
            c.setFont(F["regular"], T.TABLE)
            c.setFillColor(T.TEXT_3)
            c.drawString(vx, y + 4, self.suffix)
        y -= 8
        # barra de tramos
        y -= 7 + self.BAR_H
        self._draw_bar(c, PAD, y, iw)
        if self.model.kind == "confidence":
            y -= 3
            self._draw_ticks(c, PAD, y, iw)
            y -= 10.5
        if self._legend:
            y -= 4 + self._lh
            self._legend.drawOn(c, PAD, y)
        # base bajo la leyenda; el desglose, pegado abajo: en una fila igualada las líneas de desglose quedan alineadas
        y -= 6 + self._bh
        self._base.drawOn(c, PAD, y)
        if self.mini:
            yy = PAD + self._mini_h
            c.setStrokeColor(T.LINE)
            c.setLineWidth(0.5)
            c.line(PAD, yy + 3, w - PAD, yy + 3)
            for lines, value, tone, rh in self._mini_rows:
                top = yy
                yy -= rh
                c.setFont(F["regular"], T.SMALL)
                c.setFillColor(T.TEXT_2)
                for k, ln in enumerate(lines):
                    c.drawString(PAD, top - self.MINI + 3.5 - k * self.MINI_LINE, ln)
                c.setFont(F["semibold"], T.SMALL)
                c.setFillColor(T.TONE_TEXT[T.tone(tone)] if tone else T.INK)
                c.drawRightString(w - PAD, top - self.MINI + 3.5, value)

    def _draw_bar(self, c, x, y, width):
        gap = 1.5
        segs = self.model.segments
        level = (self.model.level or "").lower()
        for s in segs:
            x0 = x + width * s.frm / 100 + (gap / 2 if s.frm > 0 else 0)
            x1 = x + width * s.to / 100 - (gap / 2 if s.to < 100 else 0)
            on = s.label == level
            # el tramo del valor, en el color de su tono (neutro: gris medio, no negro)
            c.setFillColor(T.TONE_TEXT[self.level_tone] if on and self.level_tone != "neutral"
                           else T.TEXT_3 if on else T.TINT[s.tone])
            c.rect(x0, y, x1 - x0, self.BAR_H, stroke=0, fill=1)
        if self.model.pin is not None:
            px = x + width * self.model.pin / 100
            c.setFillColor(T.INK)
            c.setStrokeColor(T.SURFACE)
            c.setLineWidth(0.8)
            p = c.beginPath()
            p.moveTo(px - 4, y + self.BAR_H + 6)
            p.lineTo(px + 4, y + self.BAR_H + 6)
            p.lineTo(px, y + self.BAR_H + 0.5)
            p.close()
            c.drawPath(p, stroke=1, fill=1)

    def _draw_ticks(self, c, x, y, width):
        c.setFont(F["regular"], T.LABEL)
        c.setFillColor(T.TEXT_3)
        base = y - T.LABEL
        if self.model.kind == "confidence":
            level = (self.model.level or "").lower()
            for s in self.model.segments:
                cx = x + width * (s.frm + s.to) / 200
                on = s.label == level
                c.setFont(F["semibold" if on else "regular"], T.LABEL)
                c.setFillColor(T.INK if on else T.TEXT_3)
                c.drawCentredString(cx, base, s.label)
            return
        # cortes de las bandas bajo la barra (0 y 100 en los extremos)
        cuts = [0] + [s.to for s in self.model.segments[:-1]] + [100]
        for v in cuts:
            tx = x + width * v / 100
            label = str(int(v)) if float(v).is_integer() else f"{v:g}"
            if v == 0:
                c.drawString(tx, base, label)
            elif v == 100:
                c.drawRightString(tx, base, label)
            else:
                c.drawCentredString(tx, base, label)


# ══════════════════════════════ tarjeta de cifra ══════════════════════════════
class FigureCard(_Fixed):
    """Cifra clave: etiqueta, valor (con unidad) con su lectura en pastilla al lado (debajo si no cabe) y la
    referencia."""

    VALUE = 16
    LABEL_LH = 12

    def __init__(self, label: str, value: str, unit: str = "", bench: str = "", pill: str = "",
                 tone: Optional[str] = None, note: str = ""):
        super().__init__()
        self.label, self.value, self.unit, self.bench = label, value or "—", unit or "", bench or ""
        self.pill_text, self.tone, self.note = pill or "", T.tone(tone), note or ""

    def label_count(self, w) -> int:
        return len(_wrap_words(self.label, "regular", T.SMALL, w - 2 * PAD))

    def _value_w(self):
        return _w(self.value, "semibold", self.VALUE) + (2 + _w(self.unit, "regular", T.TABLE) if self.unit else 0)

    def _layout(self, w):
        iw = w - 2 * PAD
        # el nombre de la métrica tal cual (P/E, FCF yield, EV/EBITDA): sin versalitas, que cambiarían el nombre técnico
        self._lines = _wrap_words(self.label, "regular", T.SMALL, iw)
        self._lines += [""] * max(self.label_lines - len(self._lines), 0)
        sub = self.bench or self.note
        self._sub, self._sh = (_para(esc(sub), _ps("fs", "regular", T.SMALL, leading=T.SMALL_LEADING,
                                                    color=T.TEXT_3), iw) if sub else (None, 0))
        self._pill = Pill(self.pill_text, self.tone, max_width=iw) if self.pill_text else None
        pw, ph = self._pill.wrap(iw, 100) if self._pill else (0, 0)
        self._pill_inline = bool(self._pill) and self._value_w() + 8 + pw <= iw and ph <= self.VALUE + 2
        below = (ph + 4) if self._pill and not self._pill_inline else 0
        return PAD + len(self._lines) * self.LABEL_LH + 4 + self.VALUE + below + (4 + self._sh) + PAD

    def natural_height(self, w):
        return self._layout(w)

    def draw(self):
        c, w, h = self.canv, self.width, self.height
        self._layout(w)
        _card(c, w, h)
        y = h - PAD
        c.setFont(F["regular"], T.SMALL)
        c.setFillColor(T.TEXT_3)
        for ln in self._lines:
            y -= self.LABEL_LH
            if ln:
                c.drawString(PAD, y + 2.5, ln)
        y -= 4 + self.VALUE
        c.setFont(F["semibold"], self.VALUE)
        c.setFillColor(T.INK)
        c.drawString(PAD, y + 3, self.value)
        if self.unit:
            c.setFont(F["regular"], T.TABLE)
            c.setFillColor(T.TEXT_3)
            c.drawString(PAD + _w(self.value, "semibold", self.VALUE) + 2, y + 3, self.unit)
        if self._pill:
            pw, ph = self._pill.wrap(w - 2 * PAD, 100)
            if self._pill_inline:
                self._pill.drawOn(c, w - PAD - pw, y + 1)
            else:
                y -= 4 + ph
                self._pill.drawOn(c, PAD, y)
        if self._sub:
            # la referencia va pegada abajo: en una fila igualada, las referencias quedan alineadas
            self._sub.drawOn(c, PAD, PAD)


# ══════════════════════════════ tabla técnica ══════════════════════════════
TECH_HEADER = ("Métrica", "Empresa", "Referencia", "Brecha", "Lectura")
TECH_WIDTHS = (0.36, 0.14, 0.14, 0.11, 0.25)   # fracciones del ancho


def tech_table(rows: Sequence[Dict[str, Any]], width: float, header: Optional[Sequence[str]] = None,
               meaning: Optional[Callable[[str, str], Optional[str]]] = None) -> Table:
    """Tabla técnica de un capítulo (spec §3.3, maqueta 4). `rows` son filas de `display.sections.*.rows`
    ({key, label, value, bench, gap, reading, tone, state, text}); `meaning(key, label)` da el significado llano bajo
    el nombre técnico (si no hay, solo el nombre). Una fila sin dato dice "Sin dato" y su motivo, nunca queda vacía."""
    head = [str(h).capitalize() if h else "" for h in (header or TECH_HEADER)]
    st_h = _ps("th", "semibold", T.LABEL, leading=10, color=T.TEXT_3)
    st_hr = _ps("thr", "semibold", T.LABEL, leading=10, color=T.TEXT_3, align="right")
    st_m = _ps("tm", "semibold", T.TABLE, leading=T.TABLE_LEADING, color=T.INK)
    st_mean = _ps("tmn", "regular", 8.5, leading=11, color=T.TEXT_3)
    st_r = _ps("tr", "regular", T.TABLE, leading=T.TABLE_LEADING, color=T.TEXT_2, align="right")
    widths = [width * f for f in TECH_WIDTHS]
    data = [[Paragraph(esc(h.upper()), st_h if i == 0 or i == 4 else st_hr) for i, h in enumerate(head)]]
    for r in rows:
        tone = T.tone(r.get("tone"))
        has = r.get("state", "con_dato") == "con_dato"
        sub = (meaning(r.get("key", ""), r.get("label", "")) if meaning else None) or None
        if not has:
            sub = r.get("text") or r.get("reading") or sub
        name = f"{esc(r.get('label'))}" + (f"<br/><font name='{F['regular']}' size='8.5' color='{T.TEXT_3.hexval()}'>"
                                             f"{esc(sub)}</font>" if sub else "")
        value_color = T.TONE_TEXT[tone] if tone != "neutral" else T.INK
        st_v = _ps("tv", "semibold", T.TABLE, leading=T.TABLE_LEADING, color=value_color, align="right")
        reading = r.get("reading") if has else None
        cells = [Paragraph(name, st_m),
                 Paragraph(esc(r.get("value") if has else _state_label(r)), st_v),
                 Paragraph(esc(_dash(r.get("bench"))), st_r),
                 Paragraph(esc(_dash(r.get("gap"))), st_r),
                 # sin lectura del motor (p. ej. sin referencia): la celda queda vacía; la raya ya está en Brecha
                 Pill(reading, tone, max_width=widths[4] - 8) if reading and reading.strip() not in ("—", "") else
                 Paragraph("", _ps("tdash", "regular", T.TABLE, color=T.TEXT_3))]
        data.append(cells)
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, T.INK),
        ("LINEBELOW", (0, 1), (-1, -2), 0.5, T.LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (0, -1), 0),
    ]))
    return t


def _state_label(r) -> str:
    """Rótulo del estado de una fila sin dato (lib/display.py STATE_LABELS): «No aplica», «Sin dato»…"""
    from display import STATE_LABELS
    return STATE_LABELS.get(r.get("state"), "Sin dato")


def _dash(v):
    return "—" if v in (None, "") else v


TECH3_WIDTHS = (0.46, 0.18, 0.36)


def tech_table3(rows: Sequence[Dict[str, Any]], width: float, header: Optional[Sequence[str]] = None,
                meaning: Optional[Callable[[str, str], Optional[str]]] = None) -> Table:
    """Tabla técnica de tres columnas (Métrica + significado · Valor · Lectura) para las filas sin referencia
    (solidez, crecimiento, valor intrínseco). Misma regla: sin dato, «Sin dato» y su motivo."""
    head = [str(h).capitalize() for h in (header or ("Métrica", "Valor", "Lectura"))]
    st_h = _ps("t3h", "semibold", T.LABEL, leading=10, color=T.TEXT_3)
    st_hr = _ps("t3hr", "semibold", T.LABEL, leading=10, color=T.TEXT_3, align="right")
    st_m = _ps("t3m", "semibold", T.TABLE, leading=T.TABLE_LEADING, color=T.INK)
    widths = [width * f for f in TECH3_WIDTHS]
    data = [[Paragraph(esc(head[0].upper()), st_h), Paragraph(esc(head[1].upper()), st_hr),
             Paragraph(esc(head[2].upper()), st_h)]]
    for r in rows:
        tone = T.tone(r.get("tone"))
        has = r.get("state", "con_dato") == "con_dato"
        sub = (meaning(r.get("key", ""), r.get("label", "")) if meaning else None) or None
        if not has:
            sub = r.get("text") or r.get("reading") or sub
        name = esc(r.get("label")) + (f"<br/><font name='{F['regular']}' size='8.5' color='{T.TEXT_3.hexval()}'>"
                                      f"{esc(sub)}</font>" if sub else "")
        st_v = _ps("t3v", "semibold", T.TABLE, leading=T.TABLE_LEADING,
                   color=T.TONE_TEXT[tone] if tone != "neutral" else T.INK, align="right")
        reading = r.get("reading") if has else None
        data.append([Paragraph(name, st_m), Paragraph(esc(r.get("value") if has else _state_label(r)), st_v),
                     Pill(reading, tone, max_width=widths[2] - 8) if reading and reading.strip() not in ("—", "")
                     else Paragraph("", _ps("t3d", "regular", T.TABLE, color=T.TEXT_3))])
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, T.INK), ("LINEBELOW", (0, 1), (-1, -2), 0.5, T.LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (0, -1), 0), ("LEFTPADDING", (2, 0), (2, -1), 12),
    ]))
    return t


SIGUE = " (sigue)"


def _empty(cell) -> bool:
    """Celda vacía (la de la etiqueta en la parte que pasa de página: reportlab la deja en `()`)."""
    return cell in ("", None) or (isinstance(cell, (list, tuple)) and not any(not _empty(c) for c in cell))


def _blank_label(cell) -> bool:
    """Etiqueta sin texto: vacía, o un párrafo vacío (las filas agrupadas bajo la etiqueta de la primera)."""
    items = cell if isinstance(cell, (list, tuple)) else [cell]
    return _empty(cell) or all(isinstance(c, Paragraph) and not (c.text or "").strip() for c in items)


class LabeledTable(Table):
    """Tabla con etiqueta en la columna 0 (`label_cols`) cuyas filas pueden partirse entre páginas (`splitInRow`). V7
    (PM): la parte de una fila que pasa a la página siguiente repite su etiqueta con «(sigue)» («NOTA · CALIDAD
    (sigue)»), en lugar de empezar la página con texto suelto en la columna del valor; la anterior conserva la suya.
    Igual si la página empieza a mitad de un grupo de filas que solo lleva la etiqueta en la primera (las bandas de una
    métrica en el anexo): la siguiente página repite la última etiqueta con «(sigue)»."""

    label_cols = (0,)

    def split(self, aw, ah):
        parts = super().split(aw, ah)
        if len(parts) < 2:
            return parts
        head = getattr(parts[0], "repeatRows", 0) or 0
        head = head if isinstance(head, int) else len(head)
        rows = parts[0]._cellvalues[head:]
        for rest in parts[1:]:
            if len(rest._cellvalues) <= head:
                continue
            row = rest._cellvalues[head]               # su continuación, la primera fila tras la cabecera repetida
            if all(_empty(c) for i, c in enumerate(row) if i not in self.label_cols):
                continue
            for i in self.label_cols:
                # la fila partida, o la última de esta página con etiqueta (filas agrupadas bajo una sola)
                label = next((r[i] for r in reversed(rows) if i < len(r) and not _blank_label(r[i])), None)
                if not _blank_label(row[i]) or label is None:
                    continue
                p = label[0] if isinstance(label, (list, tuple)) else label
                if isinstance(p, Paragraph):
                    text = p.text[:-len(SIGUE)] if p.text.endswith(SIGUE) else p.text
                    row[i] = (Paragraph(text + SIGUE, p.style),)      # como reportlab deja las celdas partidas
        return parts


def data_table(header: Sequence[str], rows: Sequence[Sequence[Any]], width: float, fracs: Sequence[float],
               align: Optional[Sequence[str]] = None, bold_first: bool = True,
               tones: Optional[Sequence[Optional[str]]] = None, tone_col: Optional[int] = None) -> Table:
    """Tabla de datos genérica a 9.5 pt: cabecera en versalitas, raya de tinta y filetes finos. Las celdas de texto
    se parten en líneas dentro de su columna; `tones[i]` colorea la columna `tone_col` de la fila i."""
    align = list(align or (["left"] + ["right"] * (len(header) - 1)))
    widths = [width * f for f in fracs]
    hs = [_ps(f"dh{i}", "semibold", T.LABEL, leading=10, color=T.TEXT_3, align=align[i]) for i in range(len(header))]
    data = [[Paragraph(esc(str(h).upper()), hs[i]) for i, h in enumerate(header)]]
    for ri, row in enumerate(rows):
        cells = []
        for ci, cell in enumerate(row):
            if isinstance(cell, Flowable):
                cells.append(cell)
                continue
            tone = T.tone((tones or [None] * len(rows))[ri]) if tone_col == ci and tones else None
            color = T.TONE_TEXT[tone] if tone and tone != "neutral" else (T.INK if ci == 0 and bold_first else T.TEXT_2)
            font = "semibold" if (ci == 0 and bold_first) or (tone and tone != "neutral") else "regular"
            cells.append(Paragraph(esc("" if cell is None else cell),
                                   _ps(f"dc{ci}", font, T.TABLE, leading=T.TABLE_LEADING, color=color, align=align[ci])))
        data.append(cells)
    t = LabeledTable(data, colWidths=widths, repeatRows=1, splitInRow=1)
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, T.INK), ("LINEBELOW", (0, 1), (-1, -2), 0.5, T.LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 4.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (0, -1), 0), ("RIGHTPADDING", (-1, 0), (-1, -1), 0),
    ]))
    return t


# Fondos de las 5 bandas del grid de sensibilidad (de muy por encima del precio a muy por debajo): tintes apagados.
GRID_BG = ["#D3E8DA", "#E8F2EC", "#F3F1EC", "#F7E6DD", "#EFD3C4"]


def sensitivity_grid(sn: Dict[str, Any], width: float) -> list:
    """Grid de sensibilidad del DCF del informe (display.sections.valuation.sensitivity): valor justo por crecimiento
    (filas) y WACC (columnas), con la banda de cada celda frente al precio y el escenario base recuadrado; debajo, la
    leyenda de las bandas."""
    head = [sn["corner"]] + list(sn["columns"])
    n = len(head)
    first = 0.2
    widths = [width * first] + [width * (1 - first) / (n - 1)] * (n - 1)
    st_h = _ps("sgh", "semibold", T.LABEL, leading=10, color=T.TEXT_3, align="center")
    st_l = _ps("sgl", "semibold", T.TABLE, leading=T.TABLE_LEADING, color=T.TEXT_3, align="center")
    data = [[Paragraph(esc(h), st_h) for h in head]]
    cmds = [("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LINEBELOW", (0, 0), (-1, 0), 0.8, T.INK),
            ("TOPPADDING", (0, 0), (-1, -1), 4.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
            ("LINEBELOW", (0, 1), (-1, -2), 0.5, T.SURFACE), ("LINEAFTER", (0, 1), (-2, -1), 0.5, T.SURFACE)]
    for gi, r in enumerate(sn["rows"]):
        row = [Paragraph(esc(r["label"]), st_l)]
        for di, cell in enumerate(r["cells"]):
            base = bool(cell.get("base"))
            row.append(Paragraph(esc(cell["value"]), _ps("sgc", "semibold" if base else "regular", T.TABLE,
                                                         leading=T.TABLE_LEADING, color=T.INK, align="center")))
            if cell.get("band") is not None:
                cmds.append(("BACKGROUND", (di + 1, gi + 1), (di + 1, gi + 1),
                             RLC.HexColor(GRID_BG[cell["band"]])))
            if base:
                cmds.append(("BOX", (di + 1, gi + 1), (di + 1, gi + 1), 1.4, T.GOOD))
        data.append(row)
    t = Table(data, colWidths=widths)
    t.setStyle(TableStyle(cmds))
    out = [t]
    labels = sn.get("band_labels") or []
    if labels:
        cells = []
        for i, lab in enumerate(labels):
            sw = Table([[""]], colWidths=[9], rowHeights=[9])
            sw.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), RLC.HexColor(GRID_BG[i]))]))
            cells += [sw, Paragraph(esc(lab), _ps("sgk", "regular", T.LABEL, leading=10, color=T.TEXT_3))]
        cw = width / len(labels)
        leg = Table([cells], colWidths=[12, cw - 12] * len(labels))
        leg.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                 ("RIGHTPADDING", (0, 0), (-1, -1), 2), ("TOPPADDING", (0, 0), (-1, -1), 6),
                                 ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
        out.append(leg)
    return out


class BarList(Flowable):
    """Lista de barras horizontales: etiqueta (partida en líneas si no cabe) · barra de la fracción · cifra. Para la
    escalera de márgenes (sobre ingresos) y la composición de las puntuaciones."""

    ROW = 20
    LINE = 12

    def __init__(self, rows: Sequence[Tuple[str, Optional[float], str, Optional[str]]], value_w: float = 120,
                 neutral=None):
        super().__init__()
        # v4 (PM): el relleno sin tono. En la composición de las puntuaciones, el gris del tramo medio (TEXT_3); en la
        # escalera de márgenes, la base y un margen sin referencia, el azul pizarra sin juicio (T.POS)
        self.rows, self.value_w, self.neutral = list(rows), value_w, neutral or T.TEXT_3

    def split(self, aw, ah):
        """Por filas: al menos dos en cada parte."""
        _, rows = self._lines(aw)
        used, k = 0.0, 0
        for _, lines in rows:
            rh = self.ROW + (len(lines) - 1) * self.LINE
            if used + rh > ah:
                break
            used += rh
            k += 1
        if k < 2 or len(rows) - k < 2:
            return []
        return [BarList(self.rows[:k], self.value_w, self.neutral), BarList(self.rows[k:], self.value_w, self.neutral)]

    def _lines(self, w):
        name_w = min(170, w * 0.36)
        return name_w, [(r, _wrap_words(r[0], "regular", T.TABLE, name_w)) for r in self.rows]

    def wrap(self, aw, ah):
        self.width = aw
        self.height = sum(self.ROW + (len(l) - 1) * self.LINE for _, l in self._lines(aw)[1]) or self.ROW
        return aw, self.height

    def draw(self):
        c, w = self.canv, self.width
        name_w, rows = self._lines(w)
        bar_x, bar_w = name_w + 8, w - name_w - 8 - self.value_w - 8
        y = self.height
        for (label, frac, value, tone), lines in rows:
            rh = self.ROW + (len(lines) - 1) * self.LINE
            y -= rh
            mid = y + rh / 2
            c.setFont(F["regular"], T.TABLE)
            c.setFillColor(T.INK)
            for k, ln in enumerate(lines):
                c.drawString(0, mid - 3.3 + (len(lines) - 1) * self.LINE / 2 - k * self.LINE, ln)
            if tone == "sin_barra":       # cierre de la 1.0: una cifra (la regla L1), sin barra que medir
                frac = None
            else:
                c.setFillColor(T.NEUTRAL)
                c.roundRect(bar_x, mid - 3, bar_w, 6, 3, stroke=0, fill=1)
            if frac is not None and frac > 0:
                tn = T.tone(tone)
                c.setFillColor(T.TONE_TEXT[tn] if tn != "neutral" else self.neutral)
                c.roundRect(bar_x, mid - 3, max(bar_w * min(frac, 1.0), 6), 6, 3, stroke=0, fill=1)
            c.setFont(F["semibold"], T.TABLE)
            c.setFillColor(T.INK)
            c.drawRightString(w, mid - 3.3, value)


# ══════════════════════════════ barras de categorías ══════════════════════════════
class CategoryBars(_Absent, Flowable):
    """Categorías de la calidad (x / máx.) con barra del tono del motor; las no concluyentes lo dicen. El nombre
    completo, partido en líneas si no cabe."""

    ROW = 20
    LINE = 12

    def __init__(self, items: Sequence[Dict[str, Any]]):
        super().__init__()
        self.items = [i for i in items if i.get("applicable", True)]

    def _rows(self, w):
        name_w = min(150, w * 0.38)
        return name_w, [(it, _wrap_words(it.get("name", ""), "regular", T.TABLE, name_w)) for it in self.items]

    def wrap(self, aw, ah):
        _, rows = self._rows(aw)
        if not rows:
            return self._absent_wrap(aw, ah, "Sin categorías", "el análisis no trae categorías de calidad")
        self._miss = None
        self.width = aw
        self.height = sum(self.ROW + (len(lines) - 1) * self.LINE for _, lines in rows)
        return aw, self.height

    def draw(self):
        c, w = self.canv, self.width
        name_w, rows = self._rows(w)
        val_w = 80
        bar_x, bar_w = name_w + 8, w - name_w - 8 - val_w - 8
        y = self.height
        if self._absent_draw():
            return
        for it, lines in rows:
            rh = self.ROW + (len(lines) - 1) * self.LINE
            y -= rh
            mid = y + rh / 2
            c.setFont(F["regular"], T.TABLE)
            c.setFillColor(T.INK)
            for k, ln in enumerate(lines):
                c.drawString(0, mid - 3.3 + (len(lines) - 1) * self.LINE / 2 - k * self.LINE, ln)
            c.setFillColor(T.NEUTRAL)
            c.roundRect(bar_x, mid - 3, bar_w, 6, 3, stroke=0, fill=1)
            if it.get("conclusive", True) and it.get("max"):
                frac = max(0.0, min(1.0, (it.get("score") or 0) / it["max"]))
                if frac > 0:
                    c.setFillColor(T.TONE_TEXT[T.tone(it.get("tone"))] if T.tone(it.get("tone")) != "neutral"
                                   else T.TEXT_3)
                    c.roundRect(bar_x, mid - 3, max(bar_w * frac, 6), 6, 3, stroke=0, fill=1)
                txt = f"{it.get('score')} / {it.get('max')}"
            else:
                txt = "no concluyente"
            c.setFont(F["semibold"], T.TABLE)
            c.setFillColor(T.INK)
            c.drawRightString(w, mid - 3.3, txt)


# ══════════════════════════════ rango de 52 semanas ══════════════════════════════
class Range52(_Absent, Flowable):
    """Rango de 52 semanas (display.sections.growth.range52): tramos de posición en grises (contexto, no juicio de
    precio), marca del precio y mínimo/máximo. Sin rango, una línea con el motivo."""

    HEIGHT = 50

    def __init__(self, range52: Optional[Dict[str, Any]], reason: str = "sin serie de precios de 52 semanas"):
        super().__init__()
        self.r, self.reason = range52, reason

    def wrap(self, aw, ah):
        if not self.r or self.r.get("pos") is None:
            return self._absent_wrap(aw, ah, "Rango de 52 semanas: sin dato", self.reason)
        self._miss = None
        self.width, self.height = aw, self.HEIGHT
        return aw, self.height

    def draw(self):
        c, w, h, r = self.canv, self.width, self.height, self.r
        if self._absent_draw():
            return
        bar_y, bar_h = 20, 7
        zones = r.get("zones") or [{"from": 0, "to": 100}]
        # v4 (PM): posición sin juicio: degradado neutro (azul pizarra) de un extremo al otro; los tramos, separados por
        # una línea del color de la página; la marca, en tinta con un aro blanco
        c.saveState()
        p = c.beginPath()
        p.rect(0, bar_y, w, bar_h)
        c.clipPath(p, stroke=0, fill=0)
        c.linearGradient(0, bar_y, w, bar_y, (T.POS_A, T.POS_B), extend=False)
        c.restoreState()
        c.setFillColor(T.SURFACE)
        for z in zones[1:]:
            c.rect(w * z["from"] / 100 - 0.75, bar_y, 1.5, bar_h, stroke=0, fill=1)
        px = w * max(0.0, min(100.0, float(r["pos"]))) / 100
        c.setFillColor(T.SURFACE)
        c.rect(px - 2.5, bar_y - 4.5, 5, bar_h + 9, stroke=0, fill=1)
        c.setFillColor(T.INK)
        c.rect(px - 1, bar_y - 3, 2, bar_h + 6, stroke=0, fill=1)
        c.setFont(F["semibold"], T.SMALL)
        label = f"{r.get('price', '')} · {round(float(r['pos']))}% del rango"
        lw = _w(label, "semibold", T.SMALL)
        lx = min(max(px - lw / 2, 0), w - lw)
        c.drawString(lx, bar_y + bar_h + 7, label)
        c.setFont(F["regular"], T.SMALL)
        c.setFillColor(T.TEXT_3)
        c.drawString(0, 6, f"Mínimo {r.get('low', '—')}")
        c.drawRightString(w, 6, f"Máximo {r.get('high', '—')}")
        reading = (r.get("reading") or {}).get("label")
        if reading:
            c.setFillColor(T.TEXT_2)
            c.drawCentredString(w / 2, 6, reading)


# ══════════════════════════════ Piotroski 3 × 3 ══════════════════════════════
class Piotroski(_Absent, Flowable):
    """Los 9 criterios de Piotroski en rejilla 3 × 3: nombre, cumple o no (tono del motor) y, si E2 los trae, los
    valores de los dos ejercicios (`display.extended.piotroski_values`); si no, el detalle del motor. Todas las celdas
    con el mismo alto: el de la celda con más líneas (nada se corta), como mínimo `CELL_H`. Sin criterios, el hueco de
    alto mínimo con el motivo."""

    GAP = 6
    IN = 8
    NAME_LH = 11
    DET_LH = 10.5
    CELL_H = 2 * IN + 2 * NAME_LH + 6 + T.SMALL + 4 + 2 * DET_LH   # nombre y detalle de hasta dos líneas

    def __init__(self, criteria: Optional[Sequence[Dict[str, Any]]], values: Optional[Sequence[Dict]] = None,
                 reason: str = "el análisis no trae los criterios de Piotroski"):
        super().__init__()
        self.criteria = list(criteria or [])
        self.values = {v.get("key"): v for v in (values or [])}
        self.reason = reason

    @staticmethod
    def _detail(cr, value):
        if value:
            return f"{value.get('cur_txt') or '—'} frente a {value.get('prev_txt') or '—'}"
        d = cr.get("detail") or ""
        head, _, rest = d.partition(": ")
        # "FY2025: ROA positivo" repite el nombre del criterio: basta el ejercicio.
        return head if rest and rest.strip().lower() == (cr.get("label") or "").strip().lower() else d

    def _cells(self, w):
        cw = (w - 2 * self.GAP) / 3
        iw = cw - 2 * self.IN
        cells = [(cr, _wrap_words(cr.get("label") or "", "semibold", T.SMALL, iw),
                  _wrap_words(self._detail(cr, self.values.get(cr.get("key"))), "regular", 8.5, iw))
                 for cr in self.criteria]
        names = max([len(n) for _, n, _ in cells] + [2])
        dets = max([len(d) for _, _, d in cells] + [2])
        cell_h = max(self.CELL_H, 2 * self.IN + names * self.NAME_LH + 6 + T.SMALL + 4 + dets * self.DET_LH)
        return cw, cells, names, dets, cell_h

    def wrap(self, aw, ah):
        if len(self.criteria) != 9:
            return self._absent_wrap(aw, ah, "Piotroski: sin criterios", self.reason)
        self._miss = None
        self.width = aw
        cell_h = self._cells(aw)[4]
        self.height = 3 * cell_h + 2 * self.GAP
        return aw, self.height

    def draw(self):
        c, w, h = self.canv, self.width, self.height
        if self._absent_draw():
            return
        cw, cells, _names, dets, cell_h = self._cells(w)
        for i, (cr, name_lines, detail) in enumerate(cells):
            col, row = i % 3, i // 3
            x, y = col * (cw + self.GAP), h - (row + 1) * cell_h - row * self.GAP
            c.saveState()
            c.translate(x, y)
            _card(c, cw, cell_h)
            tone = T.tone(cr.get("tone"))
            yy = cell_h - self.IN - T.SMALL
            c.setFont(F["semibold"], T.SMALL)
            c.setFillColor(T.INK)
            for ln in name_lines:
                c.drawString(self.IN, yy, ln)
                yy -= self.NAME_LH
            # estado y detalle, abajo: alineados entre celdas aunque el nombre ocupe más o menos líneas
            c.setFont(F["regular"], 8.5)
            c.setFillColor(T.TEXT_3)
            for k, ln in enumerate(detail):
                c.drawString(self.IN, self.IN + 1 + (len(detail) - 1 - k) * self.DET_LH, ln)
            c.setFont(F["semibold"], T.SMALL)
            c.setFillColor(T.TONE_TEXT[tone] if tone != "neutral" else T.TEXT_2)
            c.drawString(self.IN, self.IN + dets * self.DET_LH + 3, cr.get("status") or "—")
            c.restoreState()


# ══════════════════════════════ gráfica de precio ══════════════════════════════
PERIOD_DAYS = {"1y": 365, "5y": 5 * 365}   # = 1A y 5A de [price_returns]
PERIOD_LABEL = {"1y": "1 año", "5y": "5 años"}
SERIES_LABEL = {"market": "S&P 500"}
MAX_POINTS = 260


def _iso(s) -> date:
    return date.fromisoformat(str(s)[:10])


def _points(serie: Optional[Dict[str, Any]]) -> List[Tuple[date, float]]:
    """Puntos de una serie de /api/v2/prices: cierre ajustado (`a`, E2) o, si no viene, `c`."""
    return price_returns.points(serie, "a")


def chart_window(prices: Optional[Dict[str, Any]], period: str) -> Dict[str, Any]:
    """Recorta las tres series al periodo y las pasa a base 100 en la primera sesión común (la de la empresa marca el
    final). Devuelve {status, reason, series: {rol: [(fecha, base100)]}, returns: {rol: fracción}, start, end, missing}.
    Revisión V6 (F1): lib/price_returns, la misma ventana que la gráfica de la web."""
    comp = (prices or {}).get("company")
    if not _points(comp):
        reason = (comp or {}).get("reason") or ("sin serie de precios" if prices else "la serie de precios no llegó")
        return {"status": "sin_dato", "reason": reason, "series": {}, "returns": {}, "missing": {}}
    return price_returns.window(prices, PERIOD_DAYS[period])


# Periodos de la tabla de rentabilidades: los de la web (config/market.toml [price_returns]) salvo la semana.
PDF_RANGES = ("1M", "3M", "6M", "YTD", "1A", "3A", "5A")


def period_returns(prices: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Rentabilidad total (con dividendos) de cada serie (empresa, S&P 500, ETF del sector) en los periodos de la web.
    Revisión V6 (F1): los mismos números que /api/v2/prices (lib/price_returns). Un periodo que la serie no cubre
    queda sin dato ("—"), nunca con una cifra de un periodo más corto."""
    comp = _points((prices or {}).get("company"))
    if not comp:
        return {"status": "sin_dato", "reason": ((prices or {}).get("company") or {}).get("reason")
                or "sin serie de precios", "roles": [], "rows": []}
    rets = price_returns.returns(prices)
    roles = [r for r in price_returns.ROLES if r in rets]
    rows = [(r["label"], {role: rets[role][r["key"]]["total"] for role in roles})
            for r in price_returns.ranges() if r["key"] in PDF_RANGES]
    return {"status": "ok", "reason": None, "roles": roles, "rows": rows, "end": comp[-1][0]}


def _fmt_ret(x: float) -> str:
    return price_returns.fmt(x)


def _fmt_day(d: date) -> str:
    return f"{d.day} {MESES_CORTOS[d.month - 1]} {d.year}"


def _nice_step(span: float, target: int = 5) -> float:
    raw = span / max(target, 1)
    mag = 10 ** math.floor(math.log10(raw)) if raw > 0 else 1
    for m in (1, 2, 2.5, 5, 10):
        if raw <= m * mag:
            return m * mag
    return 10 * mag


class PriceChart(_Absent, Flowable):
    """Precio en base 100: la empresa (verde de marca) frente al S&P 500 (gris, discontinua) y al ETF de su sector
    (gris cálido, punteada), 1 o 5 años. Leyenda con la rentabilidad de cada serie en el periodo; ejes con fechas y
    base 100. Sin serie de la empresa: una línea con el motivo."""

    def __init__(self, prices: Optional[Dict[str, Any]], symbol: str, height: float = 150, period: str = "1y",
                 sector_label: Optional[str] = None, source: str = "Yahoo Finance, cierre ajustado",
                 title: Optional[str] = None):
        super().__init__()
        self.title = title or f"{PERIOD_LABEL[period]} · base 100"
        self.prices, self.symbol, self.fixed_h, self.period = prices, symbol, height, period
        self.sector_label = sector_label or ((prices or {}).get("sector") or {}).get("symbol") or "ETF del sector"
        self.source = source
        self.win = chart_window(prices, period)

    def wrap(self, aw, ah):
        if self.win["status"] != "ok":
            return self._absent_wrap(aw, ah, f"Gráfica de precio ({PERIOD_LABEL[self.period]}) no disponible",
                                     self.win["reason"])
        self._miss = None
        self.width, self.height = aw, self.fixed_h
        return aw, self.height

    def _label(self, role):
        return {"company": self.symbol, "market": SERIES_LABEL["market"], "sector": self.sector_label}[role]

    def draw(self):
        c, w, h, win = self.canv, self.width, self.height, self.win
        if self._absent_draw():
            return
        # leyenda arriba
        legend_y = h - T.SMALL
        x = 0
        for role in ("company", "market", "sector"):
            if role in win["series"]:
                txt = f"{self._label(role)} {_fmt_ret(win['returns'][role])}"
            elif role in win["missing"]:
                txt = f"{self._label(role)}: {win['missing'][role]}"
            else:
                continue
            self._swatch(c, x, legend_y + 3, role)
            c.setFont(F["semibold" if role == "company" else "regular"], T.SMALL)
            c.setFillColor(T.INK if role == "company" else T.TEXT_2)
            c.drawString(x + 18, legend_y, txt)
            x += 18 + _w(txt, "semibold" if role == "company" else "regular", T.SMALL) + 16
        c.setFont(F["semibold"], T.SMALL)
        c.setFillColor(T.TEXT_3)
        c.drawRightString(w, legend_y, self.title)
        # área de dibujo: abajo, la fila de fechas y la de la fuente; las líneas de la escala, cada ≥ 20 pt
        axis_w, top_pad = 26, 7
        px0, py0 = axis_w, 2 * T.LABEL + 10
        pw, ph = w - axis_w, h - T.SMALL - top_pad - py0
        vals = [v for s in win["series"].values() for _, v in s]
        lo, hi = min(vals + [100.0]), max(vals + [100.0])
        step = _nice_step(hi - lo or 10, max(2, int(ph // 20)))
        lo, hi = math.floor(lo / step) * step, math.ceil(hi / step) * step
        d0, d1 = win["start"], win["end"]
        span = max((d1 - d0).days, 1)

        def X(d):
            return px0 + pw * (d - d0).days / span

        def Y(v):
            return py0 + ph * (v - lo) / (hi - lo)

        c.setFont(F["regular"], T.LABEL)
        v = lo
        while v <= hi + 1e-9:
            y = Y(v)
            c.setStrokeColor(T.INK if abs(v - 100) < 1e-9 else T.LINE)
            c.setLineWidth(0.6 if abs(v - 100) < 1e-9 else 0.4)
            c.line(px0, y, w, y)
            c.setFillColor(T.TEXT_3)
            c.drawRightString(px0 - 4, y - 2.8, f"{v:g}")
            v += step
        for d, lab in self._ticks(d0, d1):
            xx = X(d)
            c.setStrokeColor(T.LINE)
            c.setLineWidth(0.4)
            c.line(xx, py0, xx, py0 - 3)
            c.setFillColor(T.TEXT_3)
            c.drawCentredString(min(max(xx, px0 + 12), w - 12), py0 - 4 - T.LABEL, lab)
        for role in ("sector", "market", "company"):
            pts = win["series"].get(role)
            if not pts:
                continue
            k = max(1, math.ceil(len(pts) / MAX_POINTS))
            pts = pts[::k] + ([pts[-1]] if (len(pts) - 1) % k else [])
            self._style(c, role)
            path = c.beginPath()
            path.moveTo(X(pts[0][0]), Y(pts[0][1]))
            for d, val in pts[1:]:
                path.lineTo(X(d), Y(val))
            c.drawPath(path, stroke=1, fill=0)
            c.setDash()
        # fuente y periodo
        c.setFont(F["regular"], T.LABEL)
        c.setFillColor(T.TEXT_3)
        c.drawString(0, 0, f"Base 100 = {_fmt_day(d0)} · hasta {_fmt_day(d1)} · {self.source}"
                     + (f" · {win['reason']}" if win.get("reason") else ""))

    def _style(self, c, role):
        c.setStrokeColor(T.SERIES_COLOR[role])
        c.setLineJoin(1)
        c.setLineCap(1)
        if role == "company":
            c.setLineWidth(1.6)
            c.setDash()
        elif role == "market":
            c.setLineWidth(1.0)
            c.setDash(3, 2)
        else:
            c.setLineWidth(1.0)
            c.setDash(1, 1.6)

    def _swatch(self, c, x, y, role):
        self._style(c, role)
        c.line(x, y, x + 14, y)
        c.setDash()

    def _ticks(self, d0: date, d1: date):
        months = 3 if self.period == "1y" else 12
        out, y, m = [], d0.year, d0.month + 1
        while True:
            if m > 12:
                y, m = y + 1, m - 12
            d = date(y, m, 1)
            if d > d1:
                break
            if (m - 1) % months == 0:
                lab = f"{MESES_CORTOS[m - 1]} {str(y)[2:]}" if months == 3 else str(y)
                out.append((d, lab))
            m += 1
        return out


# ══════════════════════════════ segmentos ══════════════════════════════
def _cap_first(t: str) -> str:
    """Mayúscula inicial para un título que el motor da en minúscula ("zonas geográficas")."""
    return t[:1].upper() + t[1:]


class SegmentBars(_Absent, Flowable):
    """Ingresos por segmento del último ejercicio (E2b, `/api/v2/segments`): barra por segmento con su peso e
    importe. Sin desglose oficial: una línea con el motivo."""

    ROW = 19
    LINE = 12

    def __init__(self, segments: Optional[Dict[str, Any]], money: Callable[[float], str] = None,
                 note: Optional[str] = None):
        super().__init__()
        self.s = segments
        self.note = note       # V7 · P4: lo que cubren los segmentos, en la línea de la fuente
        if money is None:
            from numfmt import money as _m
            money = _m
        self.money = money

    def _ok(self):
        s = self.s
        return bool(s and s.get("status") == "ok" and s.get("segments"))

    def available(self) -> bool:
        return self._ok()

    def reason(self) -> str:
        return (self.s or {}).get("reason") or "el desglose por segmento aún no llegó para esta empresa"

    def _rows(self, w):
        name_w = w * 0.34
        segs = sorted(self.s["segments"], key=lambda x: -(x.get("share_last") or 0))
        return name_w, [(seg, _wrap_words(seg.get("label") or seg.get("member", ""), "regular", T.TABLE, name_w))
                        for seg in segs]

    def wrap(self, aw, ah):
        if not self._ok():
            return self._absent_wrap(aw, ah, "Sin desglose oficial por segmento", self.reason())
        self._miss = None
        self.width = aw
        body = sum(self.ROW + (len(lines) - 1) * self.LINE for _, lines in self._rows(aw)[1])
        self._src = _wrap_words(self._source_text(), "regular", T.LABEL, aw)
        self.height = 22 + body + 14 + (len(self._src) - 1) * self.LINE
        return aw, self.height

    def draw(self):
        c, w, h, s = self.canv, self.width, self.height, self.s
        if self._absent_draw():
            return
        fy = (s.get("fiscal_years") or [None])[-1]
        name_w, rows = self._rows(w)
        c.setFont(F["semibold"], T.SMALL)
        c.setFillColor(T.TEXT_3)
        c.drawString(0, h - T.SMALL - 2, f"{_cap_first(s.get('axis_label') or 'Segmentos')} · ejercicio {fy}")
        y = h - 22
        val_w = 108
        bar_x, bar_w = name_w + 8, w - name_w - 8 - val_w - 8
        for seg, lines in rows:
            rh = self.ROW + (len(lines) - 1) * self.LINE
            y -= rh
            mid = y + rh / 2
            share = seg.get("share_last") or 0
            c.setFont(F["regular"], T.TABLE)
            c.setFillColor(T.INK)
            for k, ln in enumerate(lines):
                c.drawString(0, mid - 3.3 + (len(lines) - 1) * self.LINE / 2 - k * self.LINE, ln)
            c.setFillColor(T.NEUTRAL)
            c.rect(bar_x, mid - 3, bar_w, 6, stroke=0, fill=1)
            c.setFillColor(T.POS)          # v4: el peso de un segmento no es «bueno»: azul pizarra, sin juicio
            c.rect(bar_x, mid - 3, bar_w * max(0.0, min(1.0, share)), 6, stroke=0, fill=1)
            v = (seg.get("values") or {}).get(str(fy), (seg.get("values") or {}).get(fy))
            c.setFont(F["semibold"], T.TABLE)
            c.setFillColor(T.INK)
            c.drawRightString(w, mid - 3.3, f"{share * 100:.0f}% · {self.money(v) if v is not None else '—'}")
        c.setFont(F["regular"], T.LABEL)
        c.setFillColor(T.TEXT_3)
        for k, ln in enumerate(self._src):
            c.drawString(0, (len(self._src) - 1 - k) * self.LINE, ln)

    def _source_text(self) -> str:
        s = self.s
        src = s.get("source") or {}
        note = f"Fuente: SEC EDGAR, {src.get('form', 'informe anual')}" + (f" ({src['filed']})" if src.get("filed") else "")
        if s.get("currency"):
            note += f" · {s['currency']}"
        # lo que cubren los segmentos, si se sabe, ya lo dice (y con su cifra): no se repite con «difieren un 0%»
        if s.get("reconciles") is False and s.get("gap_pct") is not None and not self.note:
            note += f" · los segmentos difieren un {abs(s['gap_pct']):.0f}% de los ingresos consolidados"
        if self.note:
            note += f" · {self.note[:1].lower()}{self.note[1:]}"
        return note


# ══════════════════════════════ historia de 10 ejercicios ══════════════════════════════
HISTORY_COLS = (("year", "Ejercicio"), ("revenue_txt", "Ingresos"), ("revenue_growth_txt", "Crec."),
                ("net_income_txt", "Beneficio neto"), ("net_margin_txt", "Margen neto"), ("fcf_txt", "FCF"))


class History10(_Absent, Flowable):
    """Historia financiera de 10 ejercicios (E2a, `display.extended.history_10y`): un ejercicio por fila, del más
    antiguo al más reciente. Con menos años, los que hay (el alto es el de sus filas) y el motivo; sin historia, una
    línea con el motivo."""

    WIDTHS = (0.13, 0.19, 0.12, 0.2, 0.16, 0.2)

    def _xs(self, w):
        xs, acc = [], 0.0
        for f in self.WIDTHS:
            acc += f
            xs.append(w * acc)
        return xs

    def _header(self, c, w, y):
        xs = self._xs(w)
        c.setFont(F["semibold"], T.LABEL)
        c.setFillColor(T.TEXT_3)
        for i, (_, lab) in enumerate(HISTORY_COLS):
            if i == 0:
                c.drawString(0, y, lab.upper(), charSpace=T.LABEL_SPACING)
            else:
                c.drawRightString(xs[i], y, lab.upper(), charSpace=T.LABEL_SPACING)
        c.setStrokeColor(T.INK)
        c.setLineWidth(0.8)
        c.line(0, y - 5, w, y - 5)

    YEARS = 10
    ROW = 15

    def __init__(self, history: Optional[Dict[str, Any]]):
        super().__init__()
        self.hist = history

    def available(self) -> bool:
        return bool(self.hist and self.hist.get("rows"))

    def reason(self) -> str:
        return (self.hist or {}).get("reason") or "la historia de 10 ejercicios aún no llegó para esta empresa"

    def wrap(self, aw, ah):
        if not self.available():
            return self._absent_wrap(aw, ah, "Historia financiera: sin dato", self.reason())
        self._miss = None
        n = min(self.YEARS, len(self.hist["rows"]))
        self.width, self.height = aw, 18 + n * self.ROW + 16
        return aw, self.height

    def draw(self):
        c, w, h, hs = self.canv, self.width, self.height, self.hist
        if self._absent_draw():
            return
        rows = hs["rows"]
        rows = rows[-self.YEARS:]
        xs = self._xs(w)
        y = h - 12
        self._header(c, w, y)
        y -= 5
        for r in rows:
            y -= self.ROW
            for i, (key, _) in enumerate(HISTORY_COLS):
                val = str(r.get(key) if r.get(key) not in (None, "") else "—")
                c.setFont(F["semibold" if i == 0 else "regular"], T.TABLE)
                c.setFillColor(T.INK if i == 0 else T.TEXT_2)
                if i == 0:
                    c.drawString(0, y + 4, val)
                else:
                    c.drawRightString(xs[i], y + 4, val)
            c.setStrokeColor(T.LINE)
            c.setLineWidth(0.4)
            c.line(0, y, w, y)
        c.setFont(F["regular"], T.LABEL)
        c.setFillColor(T.TEXT_3)
        note = f"Fuente: {hs.get('source') or 'SEC EDGAR'}"
        if hs.get("currency"):
            note += f" · cifras en {hs['currency']}"
        if hs.get("reason"):
            note += f" · {hs['reason']}"
        c.drawString(0, 0, note)
