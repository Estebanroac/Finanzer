"""
Rediseño E5 (Task 3): portada y página de índice + resumen.

Portada (una página, maqueta 5): identidad, precio y variación del día (o su ausencia con el motivo), conclusión con lo
que destaca, las tres escalas con su base y su desglose (igual que la cabecera de la web), gráfica de precio de 1 año en
base 100 (toma el alto que dejan los demás bloques) y las 6 cifras clave. Sin encoger: la prueba lo exige en todo el
panel.

Página 2: índice enlazado en rejilla (9 capítulos; resumen, metodología y anexo) y la lectura del análisis (resumen
ejecutivo del motor y las notas de las puntuaciones). La lectura no se encoge: si no cabe, sigue en la página 3 y los
capítulos van a continuación, sin páginas a medio llenar.

Todo sale de `display` (y de `display.extended` cuando E2 lo publique): nada se recalcula aquí.
"""
import io
import re
from typing import Any, Dict, List, Optional

from reportlab.pdfgen import canvas

from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

from display import STATE_LABELS
from numfmt import MESES, price as _price
from settings import cfg
from . import parts as P
from . import theme as T
from .chapters import toc_entries
from .doc import INDEX_KEY, COVER_KEY, Anchor, Eyebrow, FitPage, Index, esc, start_on, styles

F = T.FONT


# ══════════════════════════════ fechas y datos de cabecera ══════════════════════════════
def short_date(iso: Optional[str]) -> Optional[str]:
    """'2026-10-14' → '14 oct 2026'."""
    if not iso:
        return None
    y, m, d = (int(x) for x in str(iso)[:10].split("-"))
    return f"{d} {MESES[m - 1][:3]} {y}"


def price_session(a: Dict[str, Any]) -> Optional[str]:
    """Sesión del precio: la de la variación del día (E2) o, hasta entonces, la del rango de 52 semanas del motor
    (fase 2b: misma sesión que el precio)."""
    ext = (a.get("display") or {}).get("extended") or {}
    prov = a.get("data_provenance") or {}
    return ((ext.get("price_change") or {}).get("session") or (prov.get("range52") or {}).get("last_session")
            or (prov.get("price_history") or {}).get("last_date"))


def statements_date(a: Dict[str, Any]) -> Optional[str]:
    return ((a.get("data_provenance") or {}).get("as_of") or {}).get("date")


def data_note(a: Dict[str, Any]) -> str:
    parts = []
    if price_session(a):
        parts.append(f"precio {short_date(price_session(a))}")
    if statements_date(a):
        parts.append(f"estados {short_date(statements_date(a))}")
    return "Datos: " + " · ".join(parts) if parts else "Datos: fecha no disponible"


def day_change(a: Dict[str, Any]) -> Dict[str, Any]:
    """Variación del día (E2a, `display.extended.price_change`) o su ausencia con el motivo."""
    pc = ((a.get("display") or {}).get("extended") or {}).get("price_change")
    if pc and pc.get("status") == "ok" and pc.get("pct_txt"):
        txt = f"{pc.get('value_txt')} ({pc['pct_txt']}) hoy" if pc.get("value_txt") else f"{pc['pct_txt']} hoy"
        return {"ok": True, "text": txt, "tone": pc.get("tone")}
    reason = (pc or {}).get("reason") or "el análisis aún no trae el cierre anterior"
    return {"ok": False, "text": f"Variación del día: sin dato — {reason}", "tone": None}


# ══════════════════════════════ escalas (como la cabecera de la web) ══════════════════════════════
def _signed(v) -> str:
    return f"+{v}" if v > 0 else "0" if v == 0 else f"−{abs(v)}"


def _unwrap(s: Optional[str]) -> str:
    t = re.sub(r"^\((.*)\)$", r"\1", s or "")
    t = re.sub(r"^(confianza|consistencia)\s+\S+:\s*", "", t, flags=re.I)
    return t[:1].upper() + t[1:]


def _sentence(t: Optional[str]) -> str:
    """Nota del motor como frase (mayúscula inicial): "en la frontera con…" → "En la frontera con…"."""
    t = (t or "").strip()
    return t[:1].upper() + t[1:]


def score_notes(a: Dict[str, Any]) -> List[Dict[str, str]]:
    """Notas del motor sobre las puntuaciones (persistencia de la calidad, frontera entre niveles, ajuste por
    confianza) que la lectura del análisis aún no cuenta: van como filas del resumen de la página 2. En la portada no
    caben en una tarjeta de un tercio sin hacerla el doble de alta que sus vecinas."""
    cover, d = a["display"]["cover"], a["display"]
    told = " ".join(e["text"] for e in d["summary"]["exec_items"])
    out = []
    for k, label in (("quality", "NOTA · CALIDAD"), ("price", "NOTA · PRECIO")):
        note = cover[k].get("note")
        if note and not all(part.strip()[:40] in told for part in note.split(";") if part.strip()):
            out.append({"label": label, "text": _sentence(note)})
    return out


def score_cards(a: Dict[str, Any], mini: bool = True) -> List[P.ScoreScale]:
    """Las tres escalas de la cabecera (spec §3.1): calidad, precio y confianza, cada una con su base y su desglose
    compacto (mismo contenido que `CompanyHeader.tsx` de la web)."""
    d = a["display"]
    cover = d["cover"]
    q, p = cover["quality"], cover["price"]
    comp = d["summary"]["composition"]
    cats = [i for c in cover["categories"] for i in c["items"]]
    qcats = [i for i in cats if i.get("applicable") and i["name"] != "Valoración"]
    valuation = next((i for i in cats if i["name"] == "Valoración"), None)
    conf = d.get("consistency") or d.get("confidence") or {}
    per_cat = qcats[0]["max"] if qcats else None

    q_mini = [(c["name"], c["score_txt"], c.get("tone")) for c in qcats]
    # cierre de la 1.0: con la regla L1 las filas son sus cifras («fact»), sin la Valoración /20 del sistema anterior
    _facts = any(r.get("kind") == "fact" for r in comp["price"]["rows"])
    p_mini = [(r.get("short") or r["label"], r["text"], None) if r.get("kind") == "fact" else
              (r["label"].split(" · ")[0], _signed(r["value"]), r.get("tone")) for r in comp["price"]["rows"]]
    if valuation and not _facts:
        p_mini.append(("Valoración", valuation["score_txt"], valuation.get("tone")))
    if p.get("contracted"):
        p_mini.append(("Ajuste por confianza", f"{p.get('raw', '—')} → {p.get('score', '—')}", None))
    c_mini = [(x["label"], x["level"], None) for x in conf.get("dimensions") or []]

    def disp(x):
        return "—" if x.get("score") is None else str(x["score"])

    def suffix(x):
        return None if x.get("score") is None else f"/ 100 · {x.get('level')}"

    level = conf.get("level")
    if not mini:
        q_mini, p_mini, c_mini = [], [], []
    return [
        P.ScoreScale(P.build_scale("quality", q.get("score"), q.get("level")), q["title"], q["question"], disp(q),
                     suffix(q), q.get("tone"), f"{len(qcats)} categorías × {per_cat} puntos", q_mini),
        P.ScoreScale(P.build_scale("price_l1", p.get("score"), p.get("level")), p["title"], p["question"], disp(p),
                     suffix(p), p.get("tone"), "P/E normalizado frente a la mediana de su grupo", p_mini),
        P.ScoreScale(P.build_level_scale(level), "Consistencia", "¿coinciden métodos y datos?",
                     level.capitalize() if level else "—", None, "neu",
                     _unwrap(conf.get("verdict_text") or cover["verdict"].get("confidence_text")) or "Sin dato",
                     c_mini, level_tone=conf.get("tone")),
    ]


# ══════════════════════════════ portada ══════════════════════════════
class _Identity(P._Fixed):
    """Etiqueta (sector · industria · bolsa), nombre y ticker, precio grande con la variación del día y su sesión."""

    NAME, PRICE = 24, 22

    def __init__(self, a: Dict[str, Any]):
        super().__init__()
        prof = a.get("profile") or {}
        es = a["display"].get("profile") or {}     # V7: sector e industria en español
        self.eyebrow = " · ".join(x for x in (es.get("sector") or prof.get("sector"),
                                              es.get("industry") or prof.get("industry"), prof.get("exchange")) if x)
        self.name, self.symbol = prof.get("name") or a.get("symbol"), a.get("symbol")
        card = (a["display"]["charts"] or {}).get("price_card") or {}
        self.price = card.get("price_txt") or ("—" if a.get("price") is None else _price(a["price"], (a.get("profile") or {}).get("currency")))
        self.change = day_change(a)
        sess = price_session(a)
        self.session = f"Precio de la sesión del {short_date(sess)}" if sess else "Sesión del precio: sin dato"

    NAME_LH, CHANGE_LH = 27, 12

    def _layout(self, w):
        """Líneas de cada texto: nada se corta; si no cabe en una línea, se parte."""
        sess_w = P._w(self.session.upper(), "semibold", T.LABEL, T.LABEL_SPACING)
        self._sess_w = sess_w
        # sector, industria y bolsa tal como los da la fuente (sin versalitas: son nombres propios, a veces en inglés)
        self._eyebrow = P._wrap_words(self.eyebrow, "regular", T.SMALL, w - sess_w - 16)
        tick_w = P._w(self.symbol, "regular", 15) + 10
        self._name = P._wrap_words(self.name, "bold", self.NAME, w - tick_w)
        x = P._w(self.price, "semibold", self.PRICE) + 10
        font, size = ("semibold", 11) if self.change["ok"] else ("regular", T.SMALL)
        self._change = P._wrap_words(self.change["text"], font, size, w - x)
        return (len(self._eyebrow) * P.LABEL_LH + 4 + self.NAME + (len(self._name) - 1) * self.NAME_LH + 6
                + max(self.PRICE, len(self._change) * self.CHANGE_LH) + 4)

    def natural_height(self, w):
        return self._layout(w)

    def draw(self):
        c, w, h = self.canv, self.width, self.height
        self._layout(w)
        y = h - T.LABEL
        P._label(c, w - self._sess_w, y, self.session)
        c.setFont(F["regular"], T.SMALL)
        c.setFillColor(T.TEXT_3)
        for k, ln in enumerate(self._eyebrow):
            c.drawString(0, y - k * P.LABEL_LH, ln)
        y -= (len(self._eyebrow) - 1) * P.LABEL_LH + 4 + self.NAME
        c.setFont(F["bold"], self.NAME)
        c.setFillColor(T.INK)
        for k, ln in enumerate(self._name):
            c.drawString(0, y + 5 - k * self.NAME_LH, ln)
        y -= (len(self._name) - 1) * self.NAME_LH
        c.setFont(F["regular"], 15)
        c.setFillColor(T.TEXT_3)
        c.drawString(P._w(self._name[-1], "bold", self.NAME) + 10, y + 5, self.symbol)
        y -= 6 + self.PRICE
        c.setFont(F["semibold"], self.PRICE)
        c.setFillColor(T.INK)
        c.drawString(0, y + 4, self.price)
        x = P._w(self.price, "semibold", self.PRICE) + 10
        tone = T.tone(self.change["tone"]) if self.change["ok"] else "neutral"
        c.setFont(F["semibold" if self.change["ok"] else "regular"], 11 if self.change["ok"] else T.SMALL)
        c.setFillColor(T.TONE_TEXT[tone] if self.change["ok"] else T.TEXT_3)
        for k, ln in enumerate(self._change):
            c.drawString(x, y + 5 - k * self.CHANGE_LH, ln)


def _conclusion_table(a: Dict[str, Any], width: float) -> Table:
    """Conclusión: el veredicto del motor y, al lado, lo que destaca (fortaleza clave, a vigilar, contexto)."""
    cover = a["display"]["cover"]
    left_w = width * 0.40
    left = [Eyebrow("Conclusión", color=T.GOOD, space_after=0), Spacer(1, 4),
            Paragraph(esc(cover["verdict"]["text"]), P._ps("verdict", "semibold", 14, leading=18, color=T.INK))]
    kick_w = 86
    right_w = width - left_w - 2 * P.PAD
    rows = []
    for h in cover.get("highlights") or []:
        tone = T.tone(h.get("tone"))
        dot = T.TONE_TEXT[tone] if tone != "neutral" else T.TEXT_3
        rows.append([Paragraph(esc(h["kicker"]), P._ps("hk", "semibold", T.LABEL, leading=12.5, color=T.TEXT_3)),
                     Paragraph(f"<font color='{dot.hexval()}'>●</font>&nbsp; {esc(h['text'])}",
                               P._ps("ht", "regular", T.TABLE, leading=12.5, color=T.INK))])
    grid = Table(rows, colWidths=[kick_w, right_w - kick_w])
    grid.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                              ("TOPPADDING", (0, 0), (-1, -1), 1.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
                              ("TOPPADDING", (0, 0), (0, -1), 2.5), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    t = Table([[left, grid]], colWidths=[left_w, width - left_w])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), T.CARD), ("ROUNDEDCORNERS", [T.RADIUS] * 4),
        ("BOX", (0, 0), (-1, -1), 0.6, T.LINE), ("LINEBEFORE", (1, 0), (1, 0), 0.6, T.LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), P.PAD), ("RIGHTPADDING", (0, 0), (-1, -1), P.PAD),
        ("TOPPADDING", (0, 0), (-1, -1), P.PAD - 1), ("BOTTOMPADDING", (0, 0), (-1, -1), P.PAD - 1),
    ]))
    return t


def key_figures(a: Dict[str, Any]) -> list:
    """Las 6 cifras clave del resumen del motor (`display.summary.cards`) en dos filas de tres, de igual alto."""
    def card(c):
        state = c.get("state", "con_dato")
        ok = state == "con_dato"
        bench = " ".join(x for x in (c.get("bench"), f"({c['delta']})" if c.get("delta") else "") if x)
        value = c["value"] if ok else STATE_LABELS.get(state, "Sin dato")
        pill = c.get("pill") if ok or c.get("pill") != value else ""   # "No aplica" una vez, no dos
        # F10 · B1: sin cifra, su motivo (lib/empty_reasons.py) en la línea de referencia
        sub = (c.get("text") if not ok else None) or bench or "Sin referencia"
        return P.FigureCard(c["label"], value, c.get("unit") if ok else "", sub, pill, c.get("tone"))
    cards = [card(c) for c in a["display"]["summary"]["cards"][:6]]
    out = []
    for i in range(0, len(cards), 3):
        if i:
            out.append(Spacer(1, T.SPACE[1]))
        out.append(P.equal_row(cards[i:i + 3]))
    return out


# Alto de la gráfica de la portada: ocupa lo que dejan los demás bloques, entre estos límites (config/pdf.toml).
CHART_MIN, CHART_MAX = cfg("pdf.layout.cover_chart_min_pt"), cfg("pdf.layout.cover_chart_max_pt")


def cover_story(a: Dict[str, Any], prices: Optional[Dict[str, Any]]) -> list:
    """La portada, en una página. La gráfica de precio toma el alto que dejan libre los demás bloques (entre
    CHART_MIN y CHART_MAX): la página queda llena sin hueco al pie. Si ni con la gráfica mínima cabe, las escalas
    pierden su desglose (que repiten los capítulos 4 y 5) y, como último recurso, el bloque encoge hasta MIN_SCALE y lo
    declara (escala_portada)."""
    sector_etf = ((prices or {}).get("sector") or {}).get("symbol")
    gap = 10
    probe = canvas.Canvas(io.BytesIO())
    for mini in (True, False):
        head = [Anchor(COVER_KEY, "Portada"),
                _Identity(a), Spacer(1, gap),
                P.Sized(lambda w: _conclusion_table(a, w)), Spacer(1, gap),
                P.equal_row(score_cards(a, mini=mini)), Spacer(1, gap)]
        tail = [Spacer(1, gap), Eyebrow("Cifras clave", space_after=0), Spacer(1, T.SPACE[0]), *key_figures(a)]
        used = sum(f.wrapOn(probe, T.CW, T.CH)[1] for f in head + tail)
        if used + CHART_MIN <= T.CH - 1:
            break
    chart_h = max(CHART_MIN, min(CHART_MAX, T.CH - used - 1))
    chart = P.PriceChart(prices, a.get("symbol"), height=chart_h, period="1y", sector_label=sector_etf,
                         title="Precio en el último año · base 100")
    if chart.win["status"] != "ok":
        # sin serie, la gráfica es una línea (no reserva su caja) y el contexto del precio lo da el rango de 52
        # semanas del motor, que no depende de la serie
        extra = _range52_block(a)
        free = T.CH - 1 - used - chart.wrapOn(probe, T.CW, T.CH)[1]
        chart = [chart] + (extra if sum(f.wrapOn(probe, T.CW, T.CH)[1] for f in extra) <= free else [])
    else:
        chart = [chart]
    return [FitPage("portada", T.CW, T.CH, head + chart + tail)]


def _range52_block(a: Dict[str, Any]) -> list:
    r = ((a["display"].get("sections") or {}).get("growth") or {}).get("range52")
    if not r or r.get("pos") is None:
        return []
    cap = P._ps("r52c", "regular", T.SMALL, leading=T.SMALL_LEADING, color=T.TEXT_3)
    return [Spacer(1, 10), Eyebrow("Rango de 52 semanas", space_after=0), Spacer(1, T.SPACE[1]), P.Range52(r),
            Spacer(1, 2), Paragraph(esc(f"{r['caption']} {r.get('zones_note') or ''}".strip()), cap)]


# ══════════════════════════════ índice y resumen ══════════════════════════════
def _exec_summary_rows(a: Dict[str, Any]) -> list:
    """La lectura del análisis (resumen ejecutivo del motor y las notas de las puntuaciones): una tabla por fila, para
    que la lectura pueda seguir en la página siguiente sin partir una fila."""
    items = list(a["display"]["summary"]["exec_items"]) + score_notes(a)
    # V7 · P1 (decisión del PM, opción C): la fila de la confianza dice el resumen del motor (M5 bis) entero, el mismo
    # que la web (la tarjeta y Conclusión): qué no puntúa (el DCF directo descartado), cuánto contrae y qué no
    summary = (a["display"].get("consistency") or a["display"].get("confidence") or {}).get("summary")
    if summary:
        items = [dict(e, text=summary) if e["label"] == CONFIDENCE_LABEL else e for e in items]
    return [_exec_row(e) for e in items]


CONFIDENCE_LABEL = "CONSISTENCIA"


def _exec_row(e: Dict[str, str]) -> "P.LabeledTable":
    S = styles()
    label_w = 132
    # si la fila se parte entre páginas, la parte de la siguiente repite la etiqueta con «(sigue)» (P.LabeledTable)
    t = P.LabeledTable([[Paragraph(esc(e["label"]), P._ps("exl", "semibold", T.LABEL, leading=10.5, color=T.TEXT_3)),
                         Paragraph(esc(e["text"]), S["body"])]], colWidths=[label_w, T.CW - label_w], splitInRow=1)
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEABOVE", (0, 0), (-1, -1), 0.5, T.LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (0, -1), 10),
        ("RIGHTPADDING", (1, 0), (1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (0, -1), 7.5),
    ]))
    return t


SUMMARY_KEY = "resumen"


def _note_table(width: float) -> Table:
    note = Table([[Paragraph(
        "<b>Interactivo:</b> el índice lleva a cada capítulo, el lector de PDF muestra sus marcadores, cada página "
        "tiene «↑&nbsp;índice» al pie y las noticias y fuentes enlazan al original.",
        P._ps("note", "regular", T.TABLE, color=T.TEXT_2))]], colWidths=[width])
    note.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), T.CARD), ("BOX", (0, 0), (-1, -1), 0.6, T.LINE),
                              ("ROUNDEDCORNERS", [T.RADIUS] * 4),
                              ("LEFTPADDING", (0, 0), (-1, -1), P.PAD), ("RIGHTPADDING", (0, 0), (-1, -1), P.PAD),
                              ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
    return note


def index_story(a: Dict[str, Any]) -> list:
    """Página 2: índice enlazado en rejilla (los 9 capítulos; resumen, metodología y anexo) y la lectura del análisis.
    La lectura no se encoge: si no cabe, sigue en la página siguiente y los capítulos van a continuación (sin páginas a
    medio llenar). Lo que venga después del índice usa ya la plantilla del cuerpo («↑ índice» al pie)."""
    S = styles()
    # V7: el resumen empieza justo debajo del índice, en esta misma página, y su entrada («Resumen 2») no llevaba a
    # ningún sitio que no se viera ya: su hueco es para el glosario. Así el índice sigue en 4 filas (12 entradas) y el
    # resumen no pierde sitio en la página 2. «Resumen» sigue en los marcadores del PDF.
    index = Index(toc_entries(), columns=3)
    return [
        Anchor(INDEX_KEY, "Índice"),
        Eyebrow("Índice · haz clic para ir", color=T.GOOD, space_after=0), Spacer(1, 3),
        Paragraph("Contenido", S["title"]), Spacer(1, T.SPACE[1]),
        index, Spacer(1, T.SPACE[2]),
        P.Sized(_note_table), start_on("body"), Spacer(1, T.SPACE[3]),
        Anchor(SUMMARY_KEY, "Resumen"),
        Eyebrow("Resumen", color=T.GOOD, space_after=0), Spacer(1, 3),
        Paragraph("Lectura del análisis", S["title"]), Spacer(1, T.SPACE[1]),
        *_exec_summary_rows(a),
    ]
