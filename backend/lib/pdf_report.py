"""
Finanzer — Informe PDF de análisis fundamental
==============================================
Generador del PDF descargable. Identidad Finanzer: un solo verde de marca
(#0cc06c) sobre tinta neutra, logo, layout editorial denso (sin espacios
muertos) y narrativa ADAPTATIVA: cada indicador se interpreta en texto según
la banda en la que cae (vs sector, vs umbrales canónicos), tanto en los
párrafos de cada sección como en la columna "Lectura" de las tablas.

Uso: build_report(buf, analysis, sector_bench, logo_path). Etapa 9b: maqueta el bloque
`display` (lib/display.py), el mismo que consume la web; aquí no se calcula ninguna lectura.
"""
import os
from datetime import datetime
from xml.sax.saxutils import escape as _esc

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table,
    TableStyle, PageBreak, HRFlowable, Image, KeepTogether, KeepInFrame,
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.lib.utils import ImageReader

from settings import cfg

_PDF_BANDS = cfg("thresholds.pdf")  # bandas de la barra de 52 semanas

# ══════════════════════════════ IDENTIDAD ══════════════════════════════
INK    = colors.HexColor('#141417')   # titulares
BODY   = colors.HexColor('#3a3a40')   # texto
MUTED  = colors.HexColor('#77777f')   # secundario
FAINT  = colors.HexColor('#a5a5ac')   # terciario
HAIR   = colors.HexColor('#e8e9eb')   # líneas finas
HAIR2  = colors.HexColor('#f1f2f3')   # fondos de barra
PANEL  = colors.HexColor('#f7f8f8')   # paneles suaves

BRAND      = colors.HexColor('#0cc06c')   # verde Finanzer (único acento)
BRAND_TXT  = colors.HexColor('#0a8f55')   # verde legible sobre blanco
BRAND_PALE = colors.HexColor('#eaf8f1')

RED,  RED_PALE  = colors.HexColor('#c0453e'), colors.HexColor('#faeeec')
AMBER, AMBER_PALE = colors.HexColor('#9c7c14'), colors.HexColor('#faf4e0')

# Zonas del rango de 52 semanas. Etapa 9a: solo POSICIÓN (contexto), sin juicio de
# precio: tramos en grises, sin rojo/ámbar/verde.
Z_EDGE, Z_MID = colors.HexColor('#d4d4d9'), colors.HexColor('#e6e6ea')

TONE_COLOR = {'pos': BRAND_TXT, 'neg': RED, 'warn': AMBER, 'neu': MUTED}
TONE_PALE  = {'pos': BRAND_PALE, 'neg': RED_PALE, 'warn': AMBER_PALE, 'neu': PANEL}

PAGE_W, PAGE_H = letter
M_LR, M_TOP, M_BOT = 0.6 * inch, 0.72 * inch, 0.62 * inch
CW = PAGE_W - 2 * M_LR   # ancho útil

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def _fecha_es(d=None):
    d = d or datetime.now()
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


# ══════════════════════════════ ESTILOS ══════════════════════════════
def _styles():
    s = {}
    s['title']    = ParagraphStyle('title', fontName='Helvetica-Bold', fontSize=23, leading=26, textColor=INK)
    s['meta']     = ParagraphStyle('meta', fontName='Helvetica', fontSize=9, leading=12, textColor=MUTED)
    s['kicker']   = ParagraphStyle('kicker', fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=BRAND_TXT)
    s['h1']       = ParagraphStyle('h1', fontName='Helvetica-Bold', fontSize=12.5, leading=15, textColor=INK)
    s['h2']       = ParagraphStyle('h2', fontName='Helvetica-Bold', fontSize=10.5, leading=13, textColor=INK,
                                   spaceBefore=10, spaceAfter=3)
    s['body']     = ParagraphStyle('body', fontName='Helvetica', fontSize=9, leading=13.5, textColor=BODY,
                                   alignment=TA_LEFT, spaceAfter=4)
    s['small']    = ParagraphStyle('small', fontName='Helvetica', fontSize=7.6, leading=10, textColor=MUTED)
    s['cell']     = ParagraphStyle('cell', fontName='Helvetica', fontSize=8.6, leading=11, textColor=BODY)
    s['cellb']    = ParagraphStyle('cellb', fontName='Helvetica-Bold', fontSize=8.6, leading=11, textColor=INK)
    return s


# ══════════════════════ NARRATIVA ADAPTATIVA (bandas) ══════════════════════
# Etapa 9b: los lectores y todo lo que se lee de cada métrica viven en lib/display.py
# (capa de presentación compartida con la web). Se reexportan aquí por compatibilidad.
from display import (  # noqa: E402,F401
    DE_NOT_APPLICABLE, build_display, fv, join_sentences, price_tone, quality_tone, read_beta, read_buyback,
    read_coverage, read_current, read_de, read_fcf_yield, read_graham, read_growth, read_nde, read_payout,
    read_pe, read_pos52, read_roe, read_runway, read_spread, read_upside, read_vs_sector,
)

# Colores de las 5 bandas del grid de sensibilidad (display: thresholds.pdf.grid_color_bounds).
GRID_BG = [colors.HexColor('#d9f3e6'), colors.HexColor('#ecf9f2'), colors.HexColor('#f6f6f4'),
           colors.HexColor('#f9edea'), colors.HexColor('#f4dfdb')]


# ══════════════════════════════ HELPERS UI ══════════════════════════════
def hbar(pct, width, height=6, fg=BRAND, bg=HAIR2):
    """Barra horizontal simple construida con celdas (robusta, sin gráficos)."""
    p = max(0.0, min(100.0, pct or 0.0)) / 100.0
    if p <= 0.01:
        cols, bgs = [width], [bg]
    elif p >= 0.99:
        cols, bgs = [width], [fg]
    else:
        cols, bgs = [width * p, width * (1 - p)], [fg, bg]
    t = Table([[''] * len(cols)], colWidths=cols, rowHeights=[height])
    cmds = [('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('ROUNDEDCORNERS', [3, 3, 3, 3])]
    for i, b in enumerate(bgs):
        cmds.append(('BACKGROUND', (i, 0), (i, 0), b))
    t.setStyle(TableStyle(cmds))
    return t


def zone_bar_52(pos_pct, width, height=7):
    """Barra del rango de 52 semanas con sus 5 tramos (mínimos, parte baja, zona
    media, parte alta, máximos) en grises y un marcador triangular en la posición
    del precio. Etapa 9a: es contexto, no una señal de cara o barata."""
    p = max(0.0, min(100.0, pos_pct or 0.0)) / 100.0
    # anchos de zona (curva U) derivados de las bandas de read_pos52
    _edges = [0, *_PDF_BANDS["pos52_bounds"], 100]
    seg  = [(_edges[i + 1] - _edges[i]) / 100 for i in range(5)]
    zcol = [Z_EDGE, Z_MID, Z_EDGE, Z_MID, Z_EDGE]
    cols = [width * s for s in seg]
    bar = Table([[''] * 5], colWidths=cols, rowHeights=[height])
    bcmds = [('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
             ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
             ('ROUNDEDCORNERS', [3, 3, 3, 3])]
    for i, c in enumerate(zcol):
        bcmds.append(('BACKGROUND', (i, 0), (i, 0), c))
    bar.setStyle(TableStyle(bcmds))
    # marcador ▼ centrado sobre la posición del precio
    mx = width * p
    lw = max(0.0, mx - 4)
    rw = max(0.0, width - lw - 8)
    tri = Table([['', Paragraph("▼", ParagraphStyle('tri52', fontName='Helvetica-Bold',
                fontSize=7, leading=8, textColor=INK, alignment=TA_CENTER)), '']],
                colWidths=[lw, 8, rw], rowHeights=[9])
    tri.setStyle(TableStyle([('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                             ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                             ('VALIGN', (0, 0), (-1, -1), 'BOTTOM')]))
    wrap = Table([[tri], [bar]], colWidths=[width])
    wrap.setStyle(TableStyle([('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                              ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0)]))
    return wrap


def chip(text, tone='neu', size=8.5):
    st = ParagraphStyle('chip', fontName='Helvetica-Bold', fontSize=size, leading=size + 2,
                        textColor=TONE_COLOR[tone], alignment=TA_CENTER)
    t = Table([[Paragraph(_esc(text), st)]])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), TONE_PALE[tone]),
        ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 8), ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('ROUNDEDCORNERS', [7, 7, 7, 7]),
    ]))
    return t


def section_header(num, title, S):
    """Encabezado de sección: barrita verde + título en versalitas."""
    t = Table([['', Paragraph(f"{num}&nbsp;&nbsp;{_esc(title.upper())}", ParagraphStyle(
        'sh', fontName='Helvetica-Bold', fontSize=11.5, leading=14, textColor=INK)) ]],
        colWidths=[4, CW - 4])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), BRAND),
        ('LEFTPADDING', (0, 0), (0, 0), 0), ('RIGHTPADDING', (0, 0), (0, 0), 0),
        ('LEFTPADDING', (1, 0), (1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 1), ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    return [t, Spacer(1, 5)]


def data_table(header, rows, widths, aligns=None, reads=None, bold_col=1):
    """Tabla editorial: cabecera gris con subrayado verde, hairlines, sin cebra.
    reads: lista opcional de (row_idx, tone) para colorear la última columna.
    bold_col: columna de valores en negrita (None para desactivar)."""
    all_rows = [header] + rows
    t = Table(all_rows, colWidths=widths, repeatRows=1)
    cmds = [
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 7.4),
        ('TEXTCOLOR', (0, 0), (-1, 0), MUTED),
        ('LINEBELOW', (0, 0), (-1, 0), 1, BRAND),
        ('FONTSIZE', (0, 1), (-1, -1), 8.6),
        ('TEXTCOLOR', (0, 1), (-1, -1), BODY),
        ('LINEBELOW', (0, 1), (-1, -2), 0.4, HAIR),
        ('TOPPADDING', (0, 0), (-1, -1), 4.5), ('BOTTOMPADDING', (0, 0), (-1, -1), 4.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 4), ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]
    if bold_col is not None:
        cmds.append(('FONTNAME', (bold_col, 1), (bold_col, -1), 'Helvetica-Bold'))
        cmds.append(('TEXTCOLOR', (bold_col, 1), (bold_col, -1), INK))
    aligns = aligns or (['LEFT'] + ['RIGHT'] * (len(header) - 1))
    for i, a in enumerate(aligns):
        cmds.append(('ALIGN', (i, 0), (i, -1), a))
    if reads:
        last = len(header) - 1
        for row_idx, tone in reads:
            cmds.append(('TEXTCOLOR', (last, row_idx + 1), (last, row_idx + 1), TONE_COLOR[tone]))
            cmds.append(('FONTNAME', (last, row_idx + 1), (last, row_idx + 1), 'Helvetica-Bold'))
    t.setStyle(TableStyle(cmds))
    return t


# ══════════════════════════════ PLANTILLA DE PÁGINA ══════════════════════════════
def _page_decor(symbol, name, logo_path):
    def draw(canvas, doc):
        canvas.saveState()
        # banda superior de marca
        canvas.setFillColor(BRAND)
        canvas.rect(0, PAGE_H - 4, PAGE_W, 4, stroke=0, fill=1)
        # cabecera corrida (páginas > 1)
        if doc.page > 1:
            canvas.setFont('Helvetica-Bold', 7.2)
            canvas.setFillColor(MUTED)
            canvas.drawString(M_LR, PAGE_H - 0.42 * inch, "FINANZER")
            canvas.setFont('Helvetica', 7.2)
            canvas.drawString(M_LR + 0.62 * inch, PAGE_H - 0.42 * inch,
                              f"·  {name} ({symbol})  ·  Informe de análisis fundamental")
            canvas.setFillColor(HAIR)
            canvas.setLineWidth(0.5)
            canvas.setStrokeColor(HAIR)
            canvas.line(M_LR, PAGE_H - 0.5 * inch, PAGE_W - M_LR, PAGE_H - 0.5 * inch)
        # pie
        canvas.setStrokeColor(HAIR)
        canvas.setLineWidth(0.5)
        canvas.line(M_LR, 0.48 * inch, PAGE_W - M_LR, 0.48 * inch)
        canvas.setFont('Helvetica', 6.8)
        canvas.setFillColor(FAINT)
        canvas.drawString(M_LR, 0.34 * inch,
                          "Finanzer · Documento informativo y educativo — no constituye asesoría de inversión")
        canvas.drawRightString(PAGE_W - M_LR, 0.34 * inch, f"Página {doc.page}")
        canvas.restoreState()
    return draw


# ══════════════════════════════ TARJETAS / RADAR ══════════════════════════════
def status_pill(text, tone, size=6.6):
    """Pill de estado (SALUDABLE/ATENCIÓN/RIESGO) con fondo pálido del tono."""
    st = ParagraphStyle('spill', fontName='Helvetica-Bold', fontSize=size, leading=size + 2,
                        textColor=TONE_COLOR[tone], alignment=TA_CENTER)
    t = Table([[Paragraph(_esc(text.upper()), st)]])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), TONE_PALE[tone]),
        ('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6), ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('ROUNDEDCORNERS', [5, 5, 5, 5]),
    ]))
    return t


def metric_card(label, value, unit, pill, tone, delta, subnote, width):
    """Tarjeta de métrica estilo plantilla: barra de acento superior (color del
    tono) + etiqueta + pill de estado + valor grande + delta vs sector."""
    accent = TONE_COLOR[tone]
    # ancho de CONTENIDO de la card (padding 10+10): las tablas internas deben
    # ceñirse a esto o la pill se sale del cuadro.
    _iw = width - 20
    lab = Paragraph(f"<font name='Helvetica-Bold' size='6.6' color='#77777f'>{_esc(label.upper())}</font>",
                    ParagraphStyle('mcl', leading=9))
    pill_cell = status_pill(pill, tone, 6.0) if pill else ''
    head = Table([[lab, pill_cell]], colWidths=[_iw * 0.48, _iw * 0.52])
    head.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    val_p = Paragraph(
        f"<font name='Helvetica-Bold' size='19' color='{INK.hexval()}'>{_esc(value)}</font>"
        f"<font size='9' color='#a5a5ac'> {_esc(unit)}</font>",
        ParagraphStyle('mcv', leading=23))
    parts = []
    if delta:
        parts.append(f"<font size='7.4' color='{accent.hexval()}'><b>{_esc(delta)}</b></font>")
    if subnote:
        parts.append(f"<font size='7' color='#9a9aa0'>{_esc(subnote)}</font>")
    delta_p = Paragraph("&nbsp;&nbsp;".join(parts) or "&nbsp;", ParagraphStyle('mcd', leading=9.5))
    card = Table([[head], [val_p], [delta_p]], colWidths=[width])
    card.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.white),
        ('BOX', (0, 0), (-1, -1), 0.5, HAIR),
        ('LINEABOVE', (0, 0), (-1, 0), 2.2, accent),
        ('LEFTPADDING', (0, 0), (-1, -1), 10), ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (0, 0), 11), ('BOTTOMPADDING', (0, 0), (0, 0), 4),
        ('TOPPADDING', (0, 1), (0, 1), 0), ('BOTTOMPADDING', (0, 1), (0, 1), 5),
        ('TOPPADDING', (0, 2), (0, 2), 0), ('BOTTOMPADDING', (0, 2), (0, 2), 12),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    return card


def card_grid(cards, cols, width, gutter=8):
    """Coloca tarjetas en una grilla de `cols` columnas con canaletas."""
    cell_w = (width - gutter * (cols - 1)) / cols
    rows = []
    for i in range(0, len(cards), cols):
        row = cards[i:i + cols]
        while len(row) < cols:
            row.append('')
        rows.append(row)
    # ancho de columna incluye media canaleta a cada lado vía padding
    t = Table(rows, colWidths=[width / cols] * cols)
    cmds = [('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), gutter)]
    t.setStyle(TableStyle(cmds))
    return t, cell_w


def _tbl_rows5(rows):
    """Filas de display (5 columnas) -> filas y lecturas coloreadas de data_table."""
    out, reads = [], []
    for i, r in enumerate(rows):
        out.append([r["label"], r["value"], r["bench"], r["gap"], r["reading"]])
        if r["tone"]:
            reads.append((i, r["tone"]))
    return out, reads


def _tbl_rows3(rows):
    out, reads = [], []
    for i, r in enumerate(rows):
        out.append([r["label"], r["value"], r["reading"]])
        if r["tone"]:
            reads.append((i, r["tone"]))
    return out, reads


def _tone_col(tone):
    return BRAND if tone == 'pos' else AMBER if tone == 'warn' else RED


def build_report(buf, analysis, sector_bench, logo_path=None):
    """Maqueta el bloque `display` (lib/display.py): el PDF no calcula lecturas propias."""
    S = _styles()
    D = analysis.get("display") or build_display(analysis, sector_bench)
    C, SM, SEC = D["cover"], D["summary"], D["sections"]
    profile = analysis.get("profile", {}) or {}
    symbol = analysis.get("symbol", "")
    name = profile.get("name") or symbol
    sector = profile.get("sector") or "N/A"
    archetype = D["archetype"]

    doc = BaseDocTemplate(buf, pagesize=letter,
                          topMargin=M_TOP, bottomMargin=M_BOT,
                          leftMargin=M_LR, rightMargin=M_LR,
                          title=f"Finanzer — {name} ({symbol})", author="Finanzer")
    frame = Frame(M_LR, M_BOT, CW, PAGE_H - M_TOP - M_BOT, id='main',
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    deco = _page_decor(symbol, name, logo_path)
    doc.addPageTemplates([PageTemplate(id='page', frames=[frame], onPage=deco)])

    story = []

    # ════════════════ PÁGINA 1 — PORTADA ════════════════
    # Logo respetando su proporción real (el fuente es vertical 220x360; forzarlo
    # a cuadrado lo aplastaba). Alto fijo, ancho proporcional.
    logo_cell = ''
    _logo_col = 0.30 * inch
    if logo_path and os.path.isfile(logo_path):
        try:
            _iw, _ih = ImageReader(logo_path).getSize()
            _lh = 0.40 * inch
            _lw = _lh * (_iw / _ih)
            logo_cell = Image(logo_path, width=_lw, height=_lh)
            _logo_col = _lw + 0.11 * inch  # ancho de imagen + separación al wordmark
        except Exception:
            logo_cell = ''
    mast = Table([[
        logo_cell,
        Paragraph("<b>FINANZER</b>", ParagraphStyle('wm', fontName='Helvetica-Bold', fontSize=15,
                                                    leading=17, textColor=INK)),
        Paragraph(f"INFORME DE ANÁLISIS FUNDAMENTAL<br/><font color='#77777f' size='7.6'>{_fecha_es()}</font>",
                  ParagraphStyle('doct', fontName='Helvetica-Bold', fontSize=8, leading=11,
                                 textColor=BRAND_TXT, alignment=TA_RIGHT)),
    ]], colWidths=[_logo_col, 2.6 * inch, CW - _logo_col - 2.6 * inch])
    mast.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(mast)
    story.append(HRFlowable(width="100%", thickness=0.8, color=INK, spaceAfter=6))

    # Portada de ALTURA COMPLETA: 4 bandas repartidas (título · hero · KPIs ·
    # "lo esencial") para llenar la página y evitar el espacio muerto inferior.
    def _kpi_card(value, label, w):
        c = Table([
            [Paragraph(f"<font name='Helvetica-Bold' size='16' color='{INK.hexval()}'>{_esc(value)}</font>",
                       ParagraphStyle('kcv', leading=19, alignment=TA_CENTER))],
            [Paragraph(f"<font name='Helvetica-Bold' size='6.4' color='#77777f'>{_esc(label.upper())}</font>",
                       ParagraphStyle('kcl', leading=8.5, alignment=TA_CENTER))],
        ], colWidths=[w])
        c.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.white), ('BOX', (0, 0), (-1, -1), 0.5, HAIR),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8), ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (0, 0), 13), ('BOTTOMPADDING', (0, 0), (0, 0), 2),
            ('TOPPADDING', (0, 1), (0, 1), 0), ('BOTTOMPADDING', (0, 1), (0, 1), 13),
        ]))
        return c

    def _hl_card(kicker, text, tone, w):
        c = Table([
            [Paragraph(f"<font size='6.2' color='{TONE_COLOR[tone].hexval()}'><b>{_esc(kicker)}</b></font>",
                       ParagraphStyle('hlk', leading=9))],
            [Paragraph(f"<font size='9.5' color='{INK.hexval()}'>{_esc(text)}</font>",
                       ParagraphStyle('hlt', leading=12))],
        ], colWidths=[w])
        c.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.white), ('BOX', (0, 0), (-1, -1), 0.5, HAIR),
            ('LINEABOVE', (0, 0), (-1, 0), 2, TONE_COLOR[tone]),
            ('LEFTPADDING', (0, 0), (-1, -1), 11), ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (0, 0), 10), ('BOTTOMPADDING', (0, 0), (0, 0), 4),
            ('TOPPADDING', (0, 1), (0, 1), 0), ('BOTTOMPADDING', (0, 1), (0, 1), 12),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        return c

    # Banda 1 — título
    _title_flow = [
        Paragraph("ANÁLISIS FUNDAMENTAL",
                  ParagraphStyle('cve', fontName='Helvetica-Bold', fontSize=8.5, leading=12, textColor=BRAND_TXT)),
        Spacer(1, 9),
        Paragraph(_esc(name),
                  ParagraphStyle('ctitle', fontName='Helvetica-Bold', fontSize=33, leading=36, textColor=INK)),
        Spacer(1, 8),
        Paragraph(
            f"<b>{_esc(symbol)}</b>&nbsp;&nbsp;·&nbsp;&nbsp;{_esc(sector)}&nbsp;&nbsp;·&nbsp;&nbsp;"
            f"{_esc(profile.get('industry') or 'N/A')}&nbsp;&nbsp;·&nbsp;&nbsp;{_esc(profile.get('exchange') or '')}"
            f"&nbsp;&nbsp;·&nbsp;&nbsp;Corte al {_fecha_es()}",
            ParagraphStyle('csub', fontName='Helvetica', fontSize=9.5, leading=13, textColor=MUTED)),
    ]
    if C["classification_notes"]:
        _title_flow += [Spacer(1, 5), Paragraph(
            f"<font color='{BRAND_TXT.hexval()}'><b>{_esc(D['archetype_label'])}</b></font>&nbsp;&nbsp;·&nbsp;&nbsp;"
            + _esc(" · ".join(C["classification_notes"])),
            ParagraphStyle('ccls', fontName='Helvetica', fontSize=8.4, leading=11.5, textColor=BODY))]
    if C.get("currency_note"):   # etapa 11b: estados convertidos a la moneda/clase de la cotización
        _title_flow += [Spacer(1, 3), Paragraph(
            _esc(C["currency_note"]), ParagraphStyle('ccur', fontName='Helvetica', fontSize=8.0, leading=10.8,
                                                      textColor=MUTED))]

    # Banda 2 — las DOS puntuaciones (izquierda) y sus componentes (derecha):
    # calidad = 4 categorías; precio = Valoración (múltiplos + DCF).
    _sl_w = 2.15 * inch
    _ctr = ParagraphStyle('slc', leading=8.6, alignment=TA_CENTER)

    def _score_block(sb):
        rows = [[Paragraph(f"<font size='6.6' color='#77777f'><b>{sb['title']}</b></font><br/>"
                           f"<font size='6.6' color='#9a9aa0'>{sb['question']}</font>", _ctr)],
                [Paragraph(f"<font size='34' color='{TONE_COLOR[sb['tone']].hexval()}'><b>"
                           f"{sb['score'] if sb['score'] is not None else '—'}</b></font>"
                           f"<font size='11' color='#a5a5ac'> /100</font>",
                           ParagraphStyle('heronum', fontName='Helvetica-Bold', leading=36, alignment=TA_CENTER))],
                [chip(sb['level'] or "sin dato", sb['tone'], size=8.4)]]
        if sb['note']:
            rows.append([Paragraph(f"<font size='6.4' color='{AMBER.hexval()}'><b>{_esc(sb['note'])}</b></font>",
                                   ParagraphStyle('sln', leading=8.2, alignment=TA_CENTER, spaceBefore=3))])
        t = Table(rows, colWidths=[_sl_w])
        t.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                               ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                               ('TOPPADDING', (0, 0), (-1, -1), 1), ('BOTTOMPADDING', (0, 0), (-1, -1), 1)]))
        return t

    score_left = Table([[_score_block(C["quality"])], [Spacer(1, 10)], [_score_block(C["price"])]],
                       colWidths=[_sl_w])
    score_left.setStyle(TableStyle([('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                                    ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0)]))
    _catw = CW - _sl_w - 42
    _barw = _catw - 1.55 * inch - 0.5 * inch
    _grp_st = ParagraphStyle('cgh', fontName='Helvetica-Bold', fontSize=6.6, leading=9, textColor=MUTED)
    cat_rows, _grp_idx = [], []
    for grp in C["categories"]:
        _grp_idx.append(len(cat_rows))
        cat_rows.append([Paragraph(grp["title"], _grp_st), "", ""])
        for cat in grp["items"]:
            if not cat["conclusive"]:
                # Etapa 5: categoría no concluyente (cobertura < 50%), fuera de su puntuación.
                cat_rows.append([
                    Paragraph(_esc(cat["name"]), ParagraphStyle('cn', fontName='Helvetica', fontSize=8.6, leading=11,
                                                                textColor=BODY)),
                    Paragraph(cat["text"], ParagraphStyle('cnc', fontName='Helvetica', fontSize=7.6, leading=10,
                                                          textColor=MUTED)),
                    Paragraph("<b>n/c</b>", ParagraphStyle('csc', fontName='Helvetica', fontSize=8.6, leading=11,
                                                           alignment=TA_RIGHT, textColor=MUTED)),
                ])
                continue
            cat_rows.append([
                Paragraph(_esc(cat["name"]), ParagraphStyle('cn', fontName='Helvetica', fontSize=8.6, leading=11,
                                                            textColor=BODY)),
                hbar(cat["pct"], width=_barw, height=6, fg=_tone_col(cat["tone"])),
                Paragraph(f"<b>{cat['score']}</b><font color='#a5a5ac'>/{cat['max']}</font>",
                          ParagraphStyle('csc', fontName='Helvetica', fontSize=8.6, leading=11, alignment=TA_RIGHT)),
            ])
    cat_tbl = Table(cat_rows, colWidths=[1.55 * inch, _barw, 0.5 * inch])
    _ccmds = [
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4.2), ('BOTTOMPADDING', (0, 0), (-1, -1), 4.2),
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (1, 0), (1, -1), 8),
    ]
    for _gi in _grp_idx:
        _ccmds += [('SPAN', (0, _gi), (-1, _gi)), ('TOPPADDING', (0, _gi), (-1, _gi), 8 if _gi else 0),
                   ('LINEBELOW', (0, _gi), (-1, _gi), 0.4, HAIR)]
    cat_tbl.setStyle(TableStyle(_ccmds))
    hero = Table([[score_left, cat_tbl]], colWidths=[_sl_w, CW - _sl_w])
    hero.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (-1, -1), PANEL), ('ROUNDEDCORNERS', [8, 8, 8, 8]),
        ('LINEABOVE', (0, 0), (-1, 0), 2.5, BRAND),
        ('LINEAFTER', (0, 0), (0, 0), 0.5, colors.HexColor('#e2e3e5')),
        ('TOPPADDING', (0, 0), (-1, -1), 18), ('BOTTOMPADDING', (0, 0), (-1, -1), 18),
        ('LEFTPADDING', (0, 0), (0, 0), 6), ('RIGHTPADDING', (0, 0), (0, 0), 14),
        ('LEFTPADDING', (1, 0), (1, 0), 22), ('RIGHTPADDING', (1, 0), (1, 0), 20),
    ]))

    # Banda 2b — veredicto verbal + confianza (motivos en lenguaje llano) + cobertura parcial
    _V = C["verdict"]
    _vrows = [[Paragraph(f"<font size='6.6' color='#77777f'><b>VEREDICTO</b></font>",
                         ParagraphStyle('vk', leading=9))],
              [Paragraph(_esc(_V["text"]),
                         ParagraphStyle('vt', fontName='Helvetica-Bold', fontSize=15, leading=19, textColor=INK))]]
    if _V["confidence_text"]:
        _vrows.append([Paragraph(_esc(_V["confidence_text"]),
                                 ParagraphStyle('vc', fontName='Helvetica', fontSize=9.4, leading=12.5,
                                                textColor=TONE_COLOR[_V["confidence_tone"]]))])
    if C["confidence_reasons"]:
        _vrows.append([Paragraph(_esc("Motivos de la confianza: " + " ".join(C["confidence_reasons"])),
                                 ParagraphStyle('vr', fontName='Helvetica', fontSize=7.6, leading=10, textColor=BODY))])
    if C["coverage_notes"]:
        _vrows.append([Paragraph(_esc("Cobertura parcial: " + "; ".join(C["coverage_notes"])),
                                 ParagraphStyle('vn', fontName='Helvetica', fontSize=7.6, leading=10, textColor=AMBER))])
    verdict_band = Table(_vrows, colWidths=[CW])
    verdict_band.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.white), ('BOX', (0, 0), (-1, -1), 0.5, HAIR),
        ('LINEBEFORE', (0, 0), (0, -1), 3, TONE_COLOR[C["quality"]["tone"]]),
        ('LEFTPADDING', (0, 0), (-1, -1), 14), ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (0, 0), 9), ('TOPPADDING', (0, 1), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, -1), (-1, -1), 10),
    ]))

    # Banda 3 — KPIs (2 filas de 4 = 8 indicadores clave, los primarios del arquetipo)
    _kw = (CW - 3 * 9) / 4.0
    _kpis = [(k["value"], k["label"]) for k in C["kpis"]]

    def _krow(items):
        t = Table([[_kpi_card(v, l, _kw) for v, l in items]], colWidths=[CW / 4.0] * 4)
        t.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (0, -1), 0), ('RIGHTPADDING', (-1, 0), (-1, -1), 0),
            ('LEFTPADDING', (1, 0), (-1, -1), 9), ('RIGHTPADDING', (0, 0), (-2, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        return t
    krow = Table([[_krow(_kpis[0:4])], [_krow(_kpis[4:8])]], colWidths=[CW])
    krow.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (0, 0), 0), ('BOTTOMPADDING', (0, 0), (0, 0), 9),
        ('TOPPADDING', (0, 1), (0, 1), 0), ('BOTTOMPADDING', (0, 1), (0, 1), 0),
    ]))

    # Banda 4 — "lo esencial" (fortaleza clave · a vigilar · contexto)
    _hlw = (CW - 2 * 9) / 3.0
    hl_row = Table([[_hl_card(h["kicker"], h["text"], h["tone"], _hlw) for h in C["highlights"]]],
                   colWidths=[CW / 3.0] * 3)
    hl_row.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (0, -1), 0), ('RIGHTPADDING', (-1, 0), (-1, -1), 0),
        ('LEFTPADDING', (1, 0), (-1, -1), 9), ('RIGHTPADDING', (0, 0), (-2, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))

    # Ensamblado de portada: las bandas separadas por GAPS VERTICALES IGUALES; el
    # sobrante de altura se reparte entre las separaciones (alturas medidas con .wrap()).
    _title_band = Table([[_title_flow]], colWidths=[CW])
    _title_band.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    _bands = [_title_band, hero, verdict_band, krow, hl_row]
    _frame_h = PAGE_H - M_TOP - M_BOT
    _mast_h = mast.wrap(CW, _frame_h)[1] + 0.8 + 6  # regla (grosor) + spaceAfter
    _top_pad = 26  # baja un poco el bloque de título para que no quede pegado al encabezado
    _avail = _frame_h - _mast_h - 4 - _top_pad  # colchón anti-desborde a página 2
    _content = sum(b.wrap(CW, _avail)[1] for b in _bands)
    _gap = max(10.0, (_avail - _content) / (len(_bands) - 1))
    story.append(Spacer(1, _top_pad))
    _cover = []
    for _i, _b in enumerate(_bands):
        _cover.append(_b)
        if _i < len(_bands) - 1:
            _cover.append(Spacer(1, _gap))
    if _content + _gap * (len(_bands) - 1) > _avail:
        # Etapa 9a: la portada cabe SIEMPRE en una página; si el contenido no entra
        # (veredicto o motivos largos), se reduce en bloque en lugar de desbordar.
        story.append(KeepInFrame(CW, _avail, _cover, mode='shrink'))
    else:
        story.extend(_cover)
    story.append(PageBreak())

    # ════════════════ PÁGINA 2 — RESUMEN EJECUTIVO ════════════════
    story.extend(section_header("", "Resumen ejecutivo", S))
    story.append(Spacer(1, 3))

    # ── Grilla de metric-cards (valor + pill de estado + delta vs benchmark) ──
    _cellw = (CW - 8 * 2) / 3.0
    _cards = [metric_card(c["label"], c["value"], c["unit"], c["pill"], c["tone"], c["delta"], c["bench"], _cellw)
              for c in SM["cards"]]
    cg = Table([_cards[0:3], _cards[3:6]], colWidths=[CW / 3.0] * 3)
    cg.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (0, -1), 0), ('RIGHTPADDING', (-1, 0), (-1, -1), 0),
        ('LEFTPADDING', (1, 0), (-1, -1), 8), ('RIGHTPADDING', (0, 0), (-2, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 1), (-1, 1), 0),
    ]))

    # ── Composición de las dos puntuaciones (etapa 9a: sustituye al radar de 5 ejes) ──
    _ac = SM["alert_counts"]
    n_red, n_warn, n_str = _ac["red_flags"], _ac["warnings"], _ac["strengths"]
    _bal_line = (f"<font color='{BRAND_TXT.hexval()}'><b>{n_str}</b> fortaleza{'s' if n_str != 1 else ''}</font>"
                 f"&nbsp;&nbsp;·&nbsp;&nbsp;<font color='{AMBER.hexval()}'><b>{n_warn}</b> advertencia{'s' if n_warn != 1 else ''}</font>"
                 f"&nbsp;&nbsp;·&nbsp;&nbsp;<font color='{RED.hexval()}'><b>{n_red}</b> riesgo{'s' if n_red != 1 else ''}</font>")
    _halfw = (CW - 24 - 18) / 2.0
    _lab_st = ParagraphStyle('cpl', fontName='Helvetica', fontSize=8.2, leading=10.5, textColor=BODY)
    _num_st = ParagraphStyle('cpn', fontName='Helvetica-Bold', fontSize=8.2, leading=10.5, alignment=TA_RIGHT)
    _CP = SM["composition"]

    def _head(blk):
        tone = blk["tone"]
        return [Paragraph(f"<font size='6.8' color='#77777f'><b>{blk['title']}</b></font><br/>"
                          f"<font size='17' color='{TONE_COLOR[tone].hexval()}'><b>"
                          f"{blk['score'] if blk['score'] is not None else '—'}</b></font><font size='9' color='#a5a5ac'>/100</font>"
                          f"&nbsp;&nbsp;<font size='8.4' color='{TONE_COLOR[tone].hexval()}'><b>{_esc(blk['level'] or 'sin dato')}</b></font>"
                          + (f"<br/><font size='6.8' color='{AMBER.hexval()}'>{_esc(blk['note'])}</font>"
                             if blk['note'] else ""),
                          ParagraphStyle('cph', leading=13)), "", ""]

    def _bar_row(r):
        if r["kind"] == "nc":
            return [Paragraph(_esc(r["label"]), _lab_st), Paragraph("no concluyente", _lab_st), Paragraph("n/c", _num_st)]
        if r["kind"] == "signed":   # componente de Valoración: ajuste ± sobre la base 10/20
            col = BRAND if r["tone"] == 'pos' else RED if r["tone"] == 'neg' else MUTED
            return [Paragraph(_esc(r["label"]), _lab_st),
                    hbar(min(100, abs(r["value"]) / _CP["price"]["signed_max"] * 100), width=_halfw - 1.9 * inch,
                         height=5, fg=col),
                    Paragraph(f"<font color='{col.hexval()}'>{r['value']:+d}</font>", _num_st)]
        return [Paragraph(_esc(r["label"]), _lab_st),
                hbar(r["pct"], width=_halfw - 1.9 * inch, height=5, fg=_tone_col(r["tone"])),
                Paragraph(f"{r['value']}<font color='#a5a5ac'>/{r['max']}</font>", _num_st)]

    _qrows = [_head(_CP["quality"])] + [_bar_row(r) for r in _CP["quality"]["rows"]]
    _prows = [_head(_CP["price"])] + [_bar_row(r) for r in _CP["price"]["rows"]]

    def _comp_tbl(rows):
        t = Table(rows, colWidths=[1.4 * inch, _halfw - 1.9 * inch, 0.5 * inch])
        t.setStyle(TableStyle([('SPAN', (0, 0), (-1, 0)), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                               ('BOTTOMPADDING', (0, 0), (-1, 0), 6), ('LINEBELOW', (0, 0), (-1, 0), 0.4, HAIR),
                               ('TOPPADDING', (0, 1), (-1, -1), 2.6), ('BOTTOMPADDING', (0, 1), (-1, -1), 2.6),
                               ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0)]))
        return t
    comp_box = Table([
        [Paragraph("<font size='7' color='#77777f'><b>COMPOSICIÓN DE LAS DOS PUNTUACIONES</b></font>",
                   ParagraphStyle('rbt', leading=10)), ""],
        [_comp_tbl(_qrows), _comp_tbl(_prows)],
        [Paragraph(f"<font size='7.4' color='#9a9aa0'>{_esc(_CP['caption'])}</font><br/>"
                   f"<font size='8.5'>{_bal_line}</font>",
                   ParagraphStyle('rbc', leading=11)), ""],
    ], colWidths=[_halfw + 9, _halfw + 9])
    comp_box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.white), ('BOX', (0, 0), (-1, -1), 0.5, HAIR),
        ('SPAN', (0, 0), (-1, 0)), ('SPAN', (0, 2), (-1, 2)),
        ('LINEAFTER', (0, 1), (0, 1), 0.4, HAIR),
        ('LEFTPADDING', (0, 0), (-1, -1), 12), ('RIGHTPADDING', (0, 0), (-1, -1), 9),
        ('TOPPADDING', (0, 0), (-1, 0), 11), ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
        ('TOPPADDING', (0, 1), (-1, 1), 4), ('BOTTOMPADDING', (0, 1), (-1, 1), 8),
        ('TOPPADDING', (0, 2), (-1, 2), 2), ('BOTTOMPADDING', (0, 2), (-1, 2), 11),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))

    # ── Lectura del análisis — DEBAJO, ancho completo, 2 columnas ──
    _exc_st = ParagraphStyle('exc', fontName='Helvetica', fontSize=8.6, leading=12.3,
                             textColor=BODY, spaceAfter=8)

    def _exec_cell(label, text):
        return Paragraph(
            f"<font size='6.6' color='{BRAND_TXT.hexval()}'><b>{_esc(label)}</b></font><br/>{_esc(text)}", _exc_st)
    exec_items = [(e["label"], e["text"]) for e in SM["exec_items"]]
    _pairs = [exec_items[i:i + 2] for i in range(0, len(exec_items), 2)]
    _grid = []
    for pr in _pairs:
        cells = [_exec_cell(l, t) for l, t in pr]
        if len(cells) == 1:
            cells.append('')
        _grid.append(cells)
    _innerw = (CW - 28) / 2.0
    inner_narr = Table(_grid, colWidths=[_innerw, _innerw])
    _incmds = [
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (0, -1), 0), ('RIGHTPADDING', (0, 0), (0, -1), 16),
        ('LEFTPADDING', (1, 0), (1, -1), 16), ('RIGHTPADDING', (1, 0), (1, -1), 0),
    ]
    for _i in range(len(_grid) - 1):
        _incmds.append(('LINEBELOW', (0, _i), (-1, _i), 0.4, HAIR))
    inner_narr.setStyle(TableStyle(_incmds))
    narr_box = Table([
        [Paragraph("<font size='7' color='#77777f'><b>LECTURA DEL ANÁLISIS</b></font>",
                   ParagraphStyle('nbt', leading=12, spaceAfter=6))],
        [inner_narr],
    ], colWidths=[CW])
    narr_box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.white), ('BOX', (0, 0), (-1, -1), 0.5, HAIR),
        ('LEFTPADDING', (0, 0), (-1, -1), 14), ('RIGHTPADDING', (0, 0), (-1, -1), 14),
        ('TOPPADDING', (0, 0), (0, 0), 11), ('BOTTOMPADDING', (0, 0), (0, 0), 2),
        ('TOPPADDING', (0, 1), (0, 1), 0), ('BOTTOMPADDING', (0, 1), (0, 1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))

    # Reparto de altura: cards · composición de las dos puntuaciones · lectura
    _rem2 = (PAGE_H - M_TOP - M_BOT) - 34
    body2 = Table([[cg], [comp_box], [narr_box]], colWidths=[CW],
                  rowHeights=[_rem2 * 0.27, _rem2 * 0.46, _rem2 * 0.27])
    body2.setStyle(TableStyle([
        ('VALIGN', (0, 0), (0, 0), 'TOP'),
        ('VALIGN', (0, 1), (0, 1), 'MIDDLE'),
        ('VALIGN', (0, 2), (0, 2), 'BOTTOM'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(body2)

    # ════════════════ 01 VALORACIÓN ════════════════
    V = SEC["valuation"]
    story.append(PageBreak())
    story.extend(section_header("01", "Valoración", S))
    if V["intro"]:
        story.append(Paragraph(_esc(V["intro"]), S['body']))
    story.append(Spacer(1, 4))
    rows, reads = _tbl_rows5(V["rows"])
    story.append(data_table(
        V["columns"], rows,
        [1.9 * inch, 1.15 * inch, 1.15 * inch, 1.0 * inch, CW - 5.2 * inch],
        aligns=['LEFT', 'RIGHT', 'RIGHT', 'RIGHT', 'RIGHT'], reads=reads))
    if V["market_note"]:
        story.append(Paragraph(_esc(V["market_note"]), S['small']))
    if V["normalization_note"]:
        story.append(Spacer(1, 4))
        story.append(Paragraph(_esc(V["normalization_note"]), S['small']))
    story.append(Spacer(1, 12))

    # Valor intrínseco
    IV = V["intrinsic"]
    story.append(Paragraph("Valor intrínseco", S['h2']))
    if IV["intro"]:
        story.append(Paragraph(_esc(IV["intro"]), S['body']))
    rows, reads = _tbl_rows3(IV["rows"])
    story.append(data_table(["CONCEPTO", "VALOR", "LECTURA"], rows,
                            [3.4 * inch, 1.6 * inch, CW - 5.0 * inch],
                            aligns=['LEFT', 'RIGHT', 'RIGHT'], reads=reads))
    if IV["graham_note"]:
        story.append(Paragraph(_esc(IV["graham_note"]), S['small']))
    if V["dcf_params"]:
        story.append(Spacer(1, 6))
        story.append(Paragraph(_esc(V["dcf_params"]), S['small']))
        if V["dcf_reliability"]:
            story.append(Spacer(1, 3))
            story.append(Paragraph(_esc(V["dcf_reliability"]), S['small']))
    elif V["dcf_missing"]:
        story.append(Spacer(1, 6))
        story.append(Paragraph(_esc(V["dcf_missing"]), S['small']))
    if V["ke_note"]:
        story.append(Spacer(1, 3))
        story.append(Paragraph(_esc(V["ke_note"]), S['small']))
    if V["wacc_note"]:
        story.append(Spacer(1, 3))
        story.append(Paragraph(_esc(V["wacc_note"]), S['small']))

    # Sensibilidad DCF
    SN = V["sensitivity"]
    if SN:
        story.append(Spacer(1, 10))
        story.append(Paragraph("Sensibilidad del valor justo", S['h2']))
        story.append(Paragraph(SN["intro"], S['small']))
        story.append(Spacer(1, 4))
        head = [SN["corner"]] + SN["columns"]
        srows = [head] + [[r["label"]] + [c["value"] for c in r["cells"]] for r in SN["rows"]]
        n = len(head)
        st = Table(srows, colWidths=[1.15 * inch] + [(CW - 1.15 * inch) / (n - 1)] * (n - 1))
        cmds = [
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'), ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7.6),
            ('TEXTCOLOR', (0, 0), (-1, 0), MUTED), ('TEXTCOLOR', (0, 1), (0, -1), MUTED),
            ('LINEBELOW', (0, 0), (-1, 0), 1, BRAND),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LINEBELOW', (0, 1), (-1, -2), 0.4, HAIR),
        ]
        for gi, r in enumerate(SN["rows"]):
            for di, c in enumerate(r["cells"]):
                if c["band"] is not None:
                    cmds.append(('BACKGROUND', (di + 1, gi + 1), (di + 1, gi + 1), GRID_BG[c["band"]]))
        if SN["base_growth_idx"] is not None and SN["base_discount_idx"] is not None:
            cmds.append(('BOX', (SN["base_discount_idx"] + 1, SN["base_growth_idx"] + 1),
                         (SN["base_discount_idx"] + 1, SN["base_growth_idx"] + 1), 1.4, BRAND))
        st.setStyle(TableStyle(cmds))
        story.append(st)
        if SN["note"]:
            story.append(Paragraph(_esc(SN["note"]), S['small']))

    # Confianza del veredicto (etapa 8): aquí, y solo aquí, el detalle técnico.
    CF = D["confidence"]
    if CF:
        story.append(Spacer(1, 8))
        story.append(Paragraph("Confianza del veredicto", S['h2']))
        _crows = [[d["label"], d["level"], Paragraph(_esc(d["text"]), S['small'])] for d in CF["dimensions"]]
        story.append(data_table(["DIMENSIÓN", "NIVEL", "MOTIVO"], _crows,
                                [1.9 * inch, 0.8 * inch, CW - 2.7 * inch], aligns=['LEFT', 'CENTER', 'LEFT']))
        story.append(Paragraph(_esc(CF["summary"]), S['small']))
        # Etapa 9b: el código del arquetipo y el motivo técnico de la clasificación, solo aquí.
        if C["classification_detail"]:
            story.append(Paragraph(_esc("Clasificación (detalle técnico): " + " · ".join(C["classification_detail"])),
                                   S['small']))

    # ════════════════ 02 RENTABILIDAD + 03 SOLIDEZ ════════════════
    P = SEC["profitability"]
    story.append(PageBreak())
    story.extend(section_header("02", "Rentabilidad y eficiencia", S))
    if P["intro"]:
        story.append(Paragraph(_esc(P["intro"]), S['body']))
    story.append(Spacer(1, 4))
    rows, reads = _tbl_rows5(P["rows"])
    story.append(data_table(
        P["columns"], rows,
        [1.9 * inch, 1.15 * inch, 1.15 * inch, 1.0 * inch, CW - 5.2 * inch],
        aligns=['LEFT', 'RIGHT', 'RIGHT', 'RIGHT', 'RIGHT'], reads=reads))
    if P["divergence_note"]:
        story.append(Spacer(1, 4))
        story.append(Paragraph(_esc(P["divergence_note"]), S['small']))

    story.append(Spacer(1, 8))
    story.append(Paragraph("Cifras del ejercicio", S['h2']))
    story.append(data_table(
        ["CONCEPTO", "VALOR", "CONCEPTO", "VALOR"], P["figures"],
        [2.05 * inch, 1.55 * inch, 2.05 * inch, CW - 5.65 * inch],
        aligns=['LEFT', 'RIGHT', 'LEFT', 'RIGHT']))

    SO = SEC["solvency"]
    story.append(Spacer(1, 12))
    story.extend(section_header("03", "Solidez financiera", S))
    if SO["intro"]:
        story.append(Paragraph(_esc(SO["intro"]), S['body']))
    story.append(Spacer(1, 4))
    if SO["rows"]:
        rows, reads = _tbl_rows3(SO["rows"])
        story.append(data_table(SO["columns"], rows,
                                [3.2 * inch, 1.6 * inch, CW - 4.8 * inch],
                                aligns=['LEFT', 'RIGHT', 'RIGHT'], reads=reads))
    story.append(Spacer(1, 4))
    story.append(Paragraph(_esc(SO["balance"]), S['small']))

    # ════════════════ 04 CRECIMIENTO + RETORNO AL ACCIONISTA ════════════════
    G = SEC["growth"]
    story.append(PageBreak())
    story.extend(section_header("04", "Crecimiento y retorno al accionista", S))
    if G["intro"]:
        story.append(Paragraph(_esc(G["intro"]), S['body']))
    story.append(Spacer(1, 4))
    if G["rows"]:
        rows, reads = _tbl_rows3(G["rows"])
        story.append(data_table(G["columns"], rows,
                                [3.2 * inch, 1.6 * inch, CW - 4.8 * inch],
                                aligns=['LEFT', 'RIGHT', 'RIGHT'], reads=reads))
    if G["eps_vs_revenue_note"]:
        story.append(Paragraph(_esc(G["eps_vs_revenue_note"]), S['small']))

    # Rango 52 semanas: posición del precio (contexto de mercado, etapa 9a)
    R52 = G["range52"]
    if R52:
        r_52 = R52["reading"]
        story.append(Spacer(1, 10))
        story.append(Paragraph("Rango de precio · 52 semanas", S['h2']))
        # Etiqueta de EJE: es CONTEXTO (posición), ni precio (cara/barata) ni calidad.
        story.append(Paragraph(
            f"<font color='{MUTED.hexval()}'><b>CONTEXTO</b></font>&nbsp;&nbsp;·&nbsp;&nbsp;{_esc(R52['axis'])}",
            ParagraphStyle('praxis', parent=S['small'], spaceAfter=4)))
        if r_52:
            story.append(Paragraph(_esc(join_sentences([r_52["text"]])), S['body']))
        bar = zone_bar_52(R52["pos"], width=CW - 2.4 * inch, height=7)
        rng = Table([[
            Paragraph(f"<font size='8' color='#77777f'>{R52['low']}</font>", S['cell']),
            bar,
            Paragraph(f"<font size='8' color='#77777f'>{R52['high']}</font>",
                      ParagraphStyle('r', parent=S['cell'], alignment=TA_RIGHT)),
        ]], colWidths=[1.2 * inch, CW - 2.4 * inch, 1.2 * inch])
        rng.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(rng)
        _z52 = (f"<font color='#77777f'>{_esc(R52['caption'])}</font>"
                + (f"&nbsp;&nbsp;<font color='{TONE_COLOR[r_52['tone']].hexval()}'><b>{_esc(r_52['label'])}</b></font>"
                   if r_52 else ""))
        story.append(Paragraph(_z52, ParagraphStyle('rngc', parent=S['small'], alignment=TA_CENTER, spaceBefore=4)))
        story.append(Paragraph(
            _esc(R52["zones_note"]),
            ParagraphStyle('rngz', parent=S['small'], alignment=TA_CENTER, textColor=FAINT, fontSize=6.8, spaceBefore=1)))

    # Etapa 9b: el histórico anual (yearly_financials) es dato bruto de la web; no va en el PDF.

    # ════════════════ 05 EVALUACIÓN INSTITUCIONAL ════════════════
    # Sin salto forzado: la sección fluye tras crecimiento para no dejar media
    # página en blanco. El encabezado viaja pegado a la primera tarjeta.
    INS = SEC["institutional"]
    story.append(Spacer(1, 14))
    _sec5_head = section_header("05", "Evaluación institucional", S)

    def _emit_card(block):
        nonlocal _sec5_head
        if _sec5_head is not None:
            story.append(KeepTogether(_sec5_head + [block]))
            _sec5_head = None
        else:
            story.append(block)

    def model_card(score_txt, score_tone_, title, subtitle, body_txt):
        left = Table([
            [Paragraph(f"<font size='24' color='{TONE_COLOR[score_tone_].hexval()}'><b>{_esc(score_txt)}</b></font>",
                       ParagraphStyle('mc', fontName='Helvetica-Bold', leading=27, alignment=TA_CENTER))],
            [chip(subtitle, score_tone_, size=7.6)],
        ], colWidths=[1.5 * inch])
        left.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 1), ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        right = [Paragraph(f"<b>{_esc(title)}</b>", S['h2']),
                 Paragraph(body_txt, ParagraphStyle('mcb', parent=S['body'], fontSize=8.4, leading=11.5))]
        t = Table([[left, right]], colWidths=[1.8 * inch, CW - 1.8 * inch])
        t.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BACKGROUND', (0, 0), (-1, -1), PANEL),
            ('ROUNDEDCORNERS', [6, 6, 6, 6]),
            ('TOPPADDING', (0, 0), (-1, -1), 9), ('BOTTOMPADDING', (0, 0), (-1, -1), 9),
            ('LEFTPADDING', (0, 0), (-1, -1), 8), ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ]))
        return t

    for _ci, card in enumerate(INS["cards"]):
        _emit_card(model_card(card["value"], card["tone"], card["title"], card["subtitle"], _esc(card["body"])))
        if card["key"] != "piotroski":
            story.append(Spacer(1, 8))
    if INS["piotroski_criteria"]:
        story.append(Spacer(1, 6))
        rows = [[c["label"], c["detail"], c["status"]] for c in INS["piotroski_criteria"]]
        reads = [(i, c["tone"]) for i, c in enumerate(INS["piotroski_criteria"])]
        story.append(data_table(["CRITERIO", "DETALLE", "ESTADO"], rows,
                                [2.1 * inch, CW - 3.3 * inch, 1.2 * inch],
                                aligns=['LEFT', 'LEFT', 'RIGHT'], reads=reads, bold_col=None))

    # Si ningún modelo emitió tarjeta, el encabezado 05 aún está pendiente.
    if _sec5_head is not None:
        story.extend(_sec5_head)
        _sec5_head = None

    # Desglose del score como TABLA: fila de categoría (nombre + puntos + barra)
    # seguida de sus indicadores con ajuste coloreado y lectura del motor.
    BD = INS["breakdown"]
    if BD:
        story.append(Spacer(1, 10))
        story.append(Paragraph("Desglose por categoría", S['h2']))
        story.append(Paragraph(
            _esc(BD["intro"]) + (f" {_esc(' · '.join(BD['coverage_notes']))}." if BD["coverage_notes"] else ""),
            S['small']))
        story.append(Spacer(1, 4))

        _hdr_st = ParagraphStyle('bdh', fontName='Helvetica-Bold', fontSize=7.4, leading=9, textColor=MUTED)
        _hdr_ct = ParagraphStyle('bdhc', parent=_hdr_st, alignment=TA_CENTER)
        _ind_st = ParagraphStyle('bdi', fontName='Helvetica', fontSize=8.2, leading=10.5, textColor=INK)
        _rea_st = ParagraphStyle('bdr', fontName='Helvetica', fontSize=8.2, leading=10.5, textColor=BODY)
        _cat_st = ParagraphStyle('bdc', fontName='Helvetica-Bold', fontSize=8.8, leading=11, textColor=INK)

        _w = [2.15 * inch, 0.6 * inch, CW - 2.75 * inch]
        bd_rows = [[Paragraph('INDICADOR', _hdr_st), Paragraph('AJUSTE', _hdr_ct),
                    Paragraph('LECTURA DEL MOTOR', _hdr_st)]]
        bd_cmds = [
            ('LINEBELOW', (0, 0), (-1, 0), 1, BRAND),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 3.6), ('BOTTOMPADDING', (0, 0), (-1, -1), 3.6),
            ('LEFTPADDING', (0, 0), (-1, -1), 5), ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ]
        r = 1
        for cat in BD["categories"]:
            if not cat["conclusive"]:
                bd_rows.append([
                    Paragraph(_esc(cat["name"]), _cat_st),
                    Paragraph("<b>n/c</b>", ParagraphStyle('bdcs', fontName='Helvetica-Bold', fontSize=8.8,
                                                           leading=11, textColor=MUTED, alignment=TA_CENTER)),
                    Paragraph(_esc(cat["text"]), _rea_st),
                ])
            else:
                bd_rows.append([
                    Paragraph(_esc(cat["name"]), _cat_st),
                    Paragraph(f"<b>{cat['score']}/{cat['max']}</b>",
                              ParagraphStyle('bdcs', fontName='Helvetica-Bold', fontSize=8.8, leading=11,
                                             textColor=TONE_COLOR[cat["tone"]], alignment=TA_CENTER)),
                    hbar(cat["pct"], width=CW - 2.75 * inch - 0.35 * inch, height=5, fg=_tone_col(cat["tone"])),
                ])
            bd_cmds.append(('BACKGROUND', (0, r), (-1, r), PANEL))
            bd_cmds.append(('TOPPADDING', (0, r), (-1, r), 5.5))
            bd_cmds.append(('BOTTOMPADDING', (0, r), (-1, r), 5.5))
            r += 1
            items = cat["items"]
            for k, it in enumerate(items):
                val = it["value"]
                bd_rows.append([
                    Paragraph(f"{_esc(it['metric'])}"
                              + (f" <font color='#a5a5ac'>({_esc(val)})</font>" if val else ""), _ind_st),
                    Paragraph(f"<b>{it['sign']}</b>",
                              ParagraphStyle('bda', fontName='Helvetica-Bold', fontSize=8.4, leading=10.5,
                                             textColor=TONE_COLOR[it["tone"]], alignment=TA_CENTER)),
                    Paragraph(_esc(it["reason"]), _rea_st),
                ])
                if k < len(items) - 1:
                    bd_cmds.append(('LINEBELOW', (0, r), (-1, r), 0.3, HAIR))
                r += 1
        bd_tbl = Table(bd_rows, colWidths=_w, repeatRows=1)
        bd_tbl.setStyle(TableStyle(bd_cmds))
        story.append(bd_tbl)

    # ════════════════ 06 ALERTAS ════════════════
    story.append(Spacer(1, 12))
    story.extend(section_header("06", "Alertas y señales", S))
    story.append(Paragraph(
        f"<font color='{RED.hexval()}'><b>{n_red}</b> riesgo{'s' if n_red != 1 else ''}</font>&nbsp;&nbsp;·&nbsp;&nbsp;"
        f"<font color='{AMBER.hexval()}'><b>{n_warn}</b> advertencia{'s' if n_warn != 1 else ''}</font>&nbsp;&nbsp;·&nbsp;&nbsp;"
        f"<font color='{BRAND_TXT.hexval()}'><b>{n_str}</b> fortaleza{'s' if n_str != 1 else ''}</font>",
        ParagraphStyle('alsum', fontName='Helvetica', fontSize=9.5, leading=13, spaceAfter=6)))

    for grp in SEC["alerts"]["groups"]:
        if not grp["items"]:
            continue
        tone = grp["tone"]
        story.append(Paragraph(f"<font color='{TONE_COLOR[tone].hexval()}'><b>{_esc(grp['title'])}</b></font>",
                               ParagraphStyle('abt', fontName='Helvetica-Bold', fontSize=9,
                                              leading=12, spaceBefore=5, spaceAfter=2)))
        for it in grp["items"]:
            head = f"{it['category']}: {it['reason']}"
            txt = f"<font color='{TONE_COLOR[tone].hexval()}'>●</font>&nbsp;&nbsp;<b>{_esc(head)}</b>"
            if it["detail"]:
                txt += f"<br/><font size='7.6' color='#77777f'>{_esc(it['detail'])}</font>"
            story.append(Paragraph(txt, ParagraphStyle(
                'ab', fontName='Helvetica', fontSize=8.4, leading=11, textColor=INK,
                leftIndent=8, spaceAfter=2.5)))
    if not (n_red or n_warn or n_str):
        story.append(Paragraph("No se detectaron alertas significativas.", S['body']))

    # Metodología + cierre (solo los modelos que aplican al arquetipo)
    story.append(Spacer(1, 14))
    story.append(HRFlowable(width="100%", thickness=0.5, color=HAIR))
    story.append(Spacer(1, 5))
    story.append(Paragraph(
        "<b>Metodología.</b> Este informe combina ratios TTM y del último ejercicio (fuente: Yahoo Finance) con "
        + D["methodology"]["models_text"] + " y "
        "dos puntuaciones Finanzer de 0 a 100: calidad del negocio (solidez, rentabilidad, calidad de ganancias y "
        "crecimiento) y atractivo del precio (valoración por múltiplos y DCF, contraída hacia 50 según la confianza "
        "del veredicto). Las lecturas se generan automáticamente según "
        "la banda en la que cae cada indicador frente a umbrales canónicos y a la mediana de su sector (o del "
        "mercado amplio cuando el arquetipo de la empresa contradice a su sector).",
        ParagraphStyle('meth', parent=S['small'], leading=10.5)))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "Documento generado automáticamente por Finanzer. La información puede contener errores u omisiones y no "
        "constituye asesoría financiera, recomendación de inversión ni oferta de valores. Verifique los datos y "
        "consulte a un profesional antes de invertir.",
        ParagraphStyle('disc', parent=S['small'], textColor=FAINT, fontSize=7)))

    doc.build(story)
