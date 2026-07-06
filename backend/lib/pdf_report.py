"""
Finanzer — Informe PDF de análisis fundamental
==============================================
Generador del PDF descargable. Identidad Finanzer: un solo verde de marca
(#0cc06c) sobre tinta neutra, logo, layout editorial denso (sin espacios
muertos) y narrativa ADAPTATIVA: cada indicador se interpreta en texto según
la banda en la que cae (vs sector, vs umbrales canónicos), tanto en los
párrafos de cada sección como en la columna "Lectura" de las tablas.

Uso: build_report(buf, analysis, sector_bench, logo_path)
"""
import os
from datetime import datetime
from xml.sax.saxutils import escape as _esc

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table,
    TableStyle, PageBreak, HRFlowable, Image, KeepTogether,
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

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
# Cada lector devuelve (etiqueta_corta, tono, frase) o None si no hay dato.
# tono ∈ {pos, neg, warn, neu} → color en tablas y acentos del texto.

def _pct(v, dec=1):
    return f"{v * 100:.{dec}f}%"


def read_vs_sector(name, val, bench, higher_better, fmt="mult"):
    """Lectura genérica de una métrica vs la mediana sectorial."""
    if val is None or bench in (None, 0):
        return None
    diff = (val - bench) / abs(bench) * 100
    d = f"{'+' if diff > 0 else ''}{diff:.0f}%"
    if higher_better:
        if diff >= 35:   lab, tone = "Muy superior", 'pos'
        elif diff >= 10: lab, tone = "Superior", 'pos'
        elif diff > -10: lab, tone = "En línea", 'neu'
        elif diff > -35: lab, tone = "Inferior", 'warn'
        else:            lab, tone = "Muy inferior", 'neg'
    else:
        if diff <= -35:  lab, tone = "Descuento profundo", 'pos'
        elif diff <= -10: lab, tone = "Descuento", 'pos'
        elif diff < 10:  lab, tone = "En línea", 'neu'
        elif diff < 35:  lab, tone = "Prima moderada", 'warn'
        else:            lab, tone = "Prima elevada", 'neg'
    vv = _pct(val) if fmt == "pct" else f"{val:.1f}x"
    bb = _pct(bench) if fmt == "pct" else f"{bench:.1f}x"
    frase = f"{name} de {vv} frente a {bb} del sector ({d}): {lab.lower()}"
    return lab, tone, frase, d


def read_pe(pe, sector_pe, spread):
    if pe is None:
        return None
    if pe <= 0:
        return ("Sin beneficios", 'neg',
                "el P/E no es significativo al no haber beneficios positivos en los últimos doce meses")
    r = read_vs_sector("P/E", pe, sector_pe, False)
    if r is None:
        return ("—", 'neu', f"el P/E se sitúa en {pe:.1f}x")
    lab, tone, _, d = r
    base = (f"el mercado paga {pe:.1f}x beneficios, un {d} frente a la mediana del sector "
            f"({sector_pe:.1f}x)")
    if tone in ('warn', 'neg') and spread is not None and spread > 0.05:
        base += (f"; una prima que encuentra respaldo parcial en la creación de valor de la compañía "
                 f"(ROIC−WACC de +{_pct(spread)})")
    elif tone == 'pos':
        base += "; un descuento que amerita revisar si responde a riesgos específicos o a una oportunidad"
    return lab, tone, base


def read_roe(roe, roa):
    if roe is None:
        return None
    if roe < 0 and roa is not None and roa > 0.03:
        return ("Distorsionado", 'neu',
                f"el ROE negativo responde a un patrimonio contable negativo por recompras agresivas, "
                f"no a pérdidas: el ROA de {_pct(roa)} confirma la rentabilidad real de los activos")
    if roe < 0:      return ("Negativo", 'neg', f"el ROE de {_pct(roe)} refleja destrucción de valor para el accionista")
    if roe < 0.05:   return ("Débil", 'neg', f"el ROE de {_pct(roe)} es bajo para prácticamente cualquier estándar sectorial")
    if roe < 0.12:   return ("Moderado", 'warn', f"el ROE de {_pct(roe)} se sitúa por debajo del umbral de excelencia (12–15%)")
    if roe < 0.20:   return ("Sólido", 'pos', f"el ROE de {_pct(roe)} evidencia un uso eficiente del capital de los accionistas")
    if roe < 0.40:   return ("Excelente", 'pos', f"el ROE de {_pct(roe)} sitúa a la compañía en el rango alto de generación de retornos")
    return ("Excepcional", 'pos',
            f"el ROE de {_pct(roe)} es excepcional, en parte amplificado por una base de patrimonio reducida por recompras")


def read_spread(spread, roic, wacc):
    if spread is None:
        return None
    if spread >= 0.10:
        return ("Crea mucho valor", 'pos',
                f"con un ROIC de {_pct(roic)} frente a un costo de capital (WACC) de {_pct(wacc)}, la compañía genera "
                f"un spread de +{_pct(spread)}: cada dólar reinvertido crea valor económico sustancial")
    if spread >= 0.03:
        return ("Crea valor", 'pos',
                f"el ROIC ({_pct(roic)}) supera al WACC ({_pct(wacc)}) en {_pct(spread)}, señal de creación de valor")
    if spread >= 0:
        return ("Marginal", 'neu',
                f"el ROIC ({_pct(roic)}) apenas cubre el costo de capital ({_pct(wacc)}): la creación de valor es marginal")
    if spread >= -0.03:
        return ("Al límite", 'warn',
                f"el ROIC ({_pct(roic)}) queda ligeramente por debajo del costo de capital ({_pct(wacc)})")
    return ("Destruye valor", 'neg',
            f"el ROIC ({_pct(roic)}) no cubre el costo de capital ({_pct(wacc)}): el crecimiento a estos retornos destruye valor")


def read_current(cr):
    if cr is None: return None
    if cr < 1:    return ("Tensión", 'neg', f"el current ratio de {cr:.2f}x indica que los pasivos corrientes superan a los activos corrientes")
    if cr < 1.5:  return ("Ajustada", 'warn', f"la liquidez es ajustada (current ratio {cr:.2f}x), habitual en negocios con caja predecible")
    if cr < 3:    return ("Cómoda", 'pos', f"la posición de liquidez es cómoda (current ratio {cr:.2f}x)")
    return ("Holgada", 'neu', f"el current ratio de {cr:.2f}x es muy holgado, con posible caja ociosa")


def read_de(de):
    if de is None: return None
    if de < 0:    return ("Equity negativo", 'warn', "el patrimonio contable es negativo por recompras acumuladas, lo que invalida la lectura tradicional del D/E")
    if de < 0.5:  return ("Conservador", 'pos', f"el apalancamiento es conservador (D/E {de:.2f}x)")
    if de < 1:    return ("Moderado", 'neu', f"el apalancamiento es moderado (D/E {de:.2f}x)")
    if de < 2:    return ("Elevado", 'warn', f"el apalancamiento es elevado (D/E {de:.2f}x) y merece seguimiento")
    return ("Alto", 'neg', f"el apalancamiento es alto (D/E {de:.2f}x) para un negocio no financiero")


def read_coverage(ic):
    if ic is None: return None
    if ic < 2:   return ("Crítica", 'neg', f"la cobertura de intereses ({ic:.1f}x) es críticamente baja")
    if ic < 5:   return ("Justa", 'warn', f"la cobertura de intereses ({ic:.1f}x) deja poco margen ante caídas del beneficio operativo")
    if ic < 10:  return ("Buena", 'pos', f"el beneficio operativo cubre {ic:.1f} veces el gasto por intereses")
    return ("Muy holgada", 'pos', f"la deuda es fácilmente servible: cobertura de intereses de {ic:.1f}x")


def read_nde(nde):
    if nde is None: return None
    if nde < 0:    return ("Caja neta", 'pos', "la posición de caja supera a la deuda total (caja neta)")
    if nde < 1:    return ("Baja", 'pos', f"la deuda neta equivale a {nde:.1f}x EBITDA, un nivel bajo")
    if nde < 2.5:  return ("Moderada", 'neu', f"la deuda neta ({nde:.1f}x EBITDA) es manejable")
    if nde < 4:    return ("Elevada", 'warn', f"la deuda neta ({nde:.1f}x EBITDA) es elevada")
    return ("Alta", 'neg', f"la deuda neta ({nde:.1f}x EBITDA) es alta y condiciona la flexibilidad financiera")


def read_payout(p):
    if p is None: return None
    if p < 0:     return ("Con pérdidas", 'neg', "el dividendo se paga en un ejercicio con pérdidas, algo insostenible en el tiempo")
    if p < 0.40:  return ("Conservador", 'pos', f"el payout de {_pct(p, 0)} deja amplio margen para sostener y aumentar el dividendo")
    if p < 0.60:  return ("Sostenible", 'pos', f"el payout de {_pct(p, 0)} es sostenible")
    if p < 0.80:  return ("Exigente", 'warn', f"el payout de {_pct(p, 0)} es exigente y depende de la estabilidad del beneficio")
    if p <= 1:    return ("Muy exigente", 'warn', f"el payout de {_pct(p, 0)} consume casi todo el beneficio")
    return ("Insostenible", 'neg', f"el payout de {_pct(p, 0)} supera el beneficio: el dividendo actual no es sostenible")


def read_growth(g, what="los ingresos"):
    if g is None: return None
    if g < 0:     return ("Contracción", 'neg', f"{what} se contraen un {_pct(abs(g))} interanual")
    if g < 0.03:  return ("Plano", 'warn', f"{what} crecen apenas {_pct(g)}, prácticamente planos")
    if g < 0.10:  return ("Moderado", 'neu', f"{what} crecen {_pct(g)}, un ritmo moderado")
    if g < 0.20:  return ("Sólido", 'pos', f"{what} crecen {_pct(g)}, un ritmo sólido")
    return ("Acelerado", 'pos', f"{what} crecen {_pct(g)}, un ritmo acelerado propio de compañías growth")


def read_upside(up):
    if up is None: return None
    if up >= 30:   return ("Muy infravalorada", 'pos', f"el modelo DCF sugiere un descuento sustancial: potencial teórico de +{up:.0f}% hasta el valor justo estimado")
    if up >= 15:   return ("Infravalorada", 'pos', f"el precio cotiza por debajo del valor intrínseco estimado (potencial teórico de +{up:.0f}%)")
    if up > -15:   return ("Precio justo", 'neu', f"el precio cotiza en torno al valor justo estimado por el DCF ({'+' if up > 0 else ''}{up:.0f}%)")
    if up > -30:   return ("Prima", 'warn', f"el precio incorpora una prima de {abs(up):.0f}% sobre el valor intrínseco estimado")
    return ("Sobrevalorada", 'neg', f"el precio excede en {abs(up):.0f}% el valor intrínseco estimado: el DCF exige asumir escenarios muy optimistas")


def read_graham(m):
    if m is None: return None
    if m >= 0.20:  return ("Descuento Graham", 'pos', f"cotiza {_pct(m, 0)} por debajo del número de Graham, criterio clásico de valor")
    if m >= 0:     return ("Cerca de Graham", 'neu', f"cotiza cerca del número de Graham (margen de {_pct(m, 0)})")
    return ("Sobre Graham", 'warn',
            f"cotiza {_pct(abs(m), 0)} por encima del número de Graham — habitual en compañías de calidad/crecimiento, "
            "donde este criterio de 1949 resulta demasiado restrictivo")


def read_beta(b):
    if b is None: return None
    if b < 0.8:   return ("Defensiva", 'pos', f"con beta {b:.2f}, la acción amortigua los movimientos del mercado")
    if b < 1.2:   return ("De mercado", 'neu', f"con beta {b:.2f}, la acción se mueve en línea con el mercado")
    if b < 1.6:   return ("Volátil", 'warn', f"con beta {b:.2f}, la acción amplifica los movimientos del mercado")
    return ("Muy volátil", 'neg', f"con beta {b:.2f}, la acción es notablemente más volátil que el mercado")


def read_pos52(p):
    if p is None: return None
    if p >= 85:   return ("Cerca de máximos", 'neu', f"cotiza en el {p:.0f}% del rango de 52 semanas, cerca de máximos")
    if p >= 55:   return ("Rango alto", 'neu', f"cotiza en la parte alta del rango anual ({p:.0f}%)")
    if p >= 25:   return ("Rango medio", 'neu', f"cotiza en la zona media del rango anual ({p:.0f}%)")
    return ("Cerca de mínimos", 'warn', f"cotiza en el {p:.0f}% del rango anual, cerca de mínimos")


def read_buyback(by):
    if by is None: return None
    if by >= 0.03:   return ("Recompra intensiva", 'pos', f"el programa de recompras retiró un {_pct(by)} de las acciones en el último año")
    if by >= 0.005:  return ("Recompra neta", 'pos', f"la compañía recompró un {_pct(by)} neto de sus acciones")
    if by > -0.005:  return ("Neutra", 'neu', "el número de acciones se mantuvo estable")
    return ("Dilución", 'neg', f"la emisión de acciones diluyó a los accionistas un {_pct(abs(by))} en el año")


def read_fcf_yield(fy):
    if fy is None: return None
    if fy < 0:     return ("Negativo", 'neg', "la compañía quema caja libre a nivel operativo")
    if fy < 0.03:  return ("Bajo", 'warn', f"el FCF yield de {_pct(fy)} es bajo: se paga caro cada dólar de caja libre")
    if fy < 0.05:  return ("Razonable", 'neu', f"el FCF yield de {_pct(fy)} es razonable")
    if fy < 0.08:  return ("Atractivo", 'pos', f"el FCF yield de {_pct(fy)} es atractivo")
    return ("Alto", 'pos', f"el FCF yield de {_pct(fy)} es alto para los estándares actuales del mercado")


def _join_sentences(parts):
    """Une frases en un párrafo fluido: Mayúscula inicial + '. ' y cierre."""
    parts = [p for p in parts if p]
    if not parts:
        return None
    out = []
    for p in parts:
        p = p.strip().rstrip('.')
        out.append(p[0].upper() + p[1:])
    return _esc('. '.join(out) + '.')


# ══════════════════════════════ HELPERS UI ══════════════════════════════
def fv(val, fmt="num"):
    if val is None:
        return "N/A"
    try:
        v = float(val)
        if fmt == "pct":   return f"{v * 100:.2f}%"
        if fmt == "mult":  return f"{v:.2f}x"
        if fmt == "price": return f"${v:,.2f}"
        if fmt == "money":
            if abs(v) >= 1e12: return f"${v / 1e12:.2f}T"
            if abs(v) >= 1e9:  return f"${v / 1e9:.2f}B"
            if abs(v) >= 1e6:  return f"${v / 1e6:.2f}M"
            return f"${v:,.0f}"
        return f"{v:,.2f}"
    except (TypeError, ValueError):
        return "N/A"


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


# ══════════════════════════════ INFORME ══════════════════════════════
def build_report(buf, analysis, sector_bench, logo_path=None):
    S = _styles()

    profile = analysis.get("profile", {}) or {}
    km = analysis.get("key_metrics", {}) or {}
    price = analysis.get("price")
    score = analysis.get("score") or {}
    dcf = analysis.get("dcf") or {}
    graham = analysis.get("graham_number")
    graham_margin = analysis.get("graham_margin")
    altman = analysis.get("altman_z") or {}
    piotroski = analysis.get("piotroski_f") or {}
    fin_health = analysis.get("financial_health")
    alerts = analysis.get("alerts") or {}
    sensitivity = analysis.get("sensitivity") or {}
    company_type = (analysis.get("company_type") or "balanced").replace("_", " ")
    symbol = analysis.get("symbol", "")
    name = profile.get("name") or symbol
    sector = profile.get("sector") or "N/A"
    is_financial = "financ" in (analysis.get("sector_info", {}).get("mapped_sector", "") or "").lower()

    # posición en rango 52 semanas
    h52, l52 = km.get("price_52w_high"), km.get("price_52w_low")
    pos52 = None
    if h52 and l52 and price and (h52 - l52) > 0:
        pos52 = (price - l52) / (h52 - l52) * 100

    total = score.get("total_score") or 0
    level = score.get("level") or "N/A"
    breakdown = score.get("breakdown") or {}
    score_tone = 'pos' if total >= 65 else 'warn' if total >= 45 else 'neg'

    n_red = len(alerts.get("red_flags") or [])
    n_warn = len(alerts.get("warnings") or [])
    n_str = len(alerts.get("strengths") or [])

    # ── lecturas adaptativas (se usan en resumen, secciones y tablas) ──
    r_pe = read_pe(km.get("pe"), sector_bench.get("pe"), km.get("roic_wacc_spread"))
    r_roe = read_roe(km.get("roe"), km.get("roa"))
    r_spread = read_spread(km.get("roic_wacc_spread"), km.get("roic"), km.get("wacc"))
    r_up = read_upside(dcf.get("upside"))
    r_graham = read_graham(graham_margin)
    r_cr = read_current(km.get("current_ratio"))
    r_de = read_de(km.get("de"))
    r_ic = read_coverage(km.get("interest_coverage"))
    r_nde = read_nde(km.get("net_debt_to_ebitda"))
    r_pay = read_payout(km.get("payout_ratio"))
    r_grev = read_growth(km.get("revenue_growth"), "los ingresos")
    r_gearn = read_growth(km.get("earnings_growth"), "los beneficios")
    r_beta = read_beta(km.get("beta"))
    r_52 = read_pos52(pos52)
    r_bb = read_buyback(km.get("buyback_yield"))
    r_fcfy = read_fcf_yield(km.get("fcf_yield"))

    doc = BaseDocTemplate(buf, pagesize=letter,
                          topMargin=M_TOP, bottomMargin=M_BOT,
                          leftMargin=M_LR, rightMargin=M_LR,
                          title=f"Finanzer — {name} ({symbol})", author="Finanzer")
    frame = Frame(M_LR, M_BOT, CW, PAGE_H - M_TOP - M_BOT, id='main',
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    deco = _page_decor(symbol, name, logo_path)
    doc.addPageTemplates([PageTemplate(id='page', frames=[frame], onPage=deco)])

    story = []

    # ════════════════ PÁGINA 1 — PORTADA + RESUMEN EJECUTIVO ════════════════
    # Masthead: logo + wordmark | título del documento + fecha
    logo_cell = ''
    if logo_path and os.path.isfile(logo_path):
        try:
            logo_cell = Image(logo_path, width=0.34 * inch, height=0.34 * inch)
        except Exception:
            logo_cell = ''
    mast = Table([[
        logo_cell,
        Paragraph("<b>FINANZER</b>", ParagraphStyle('wm', fontName='Helvetica-Bold', fontSize=15,
                                                    leading=17, textColor=INK)),
        Paragraph(f"INFORME DE ANÁLISIS FUNDAMENTAL<br/><font color='#77777f' size='7.6'>{_fecha_es()}</font>",
                  ParagraphStyle('doct', fontName='Helvetica-Bold', fontSize=8, leading=11,
                                 textColor=BRAND_TXT, alignment=TA_RIGHT)),
    ]], colWidths=[0.44 * inch, 2.6 * inch, CW - 0.44 * inch - 2.6 * inch])
    mast.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(mast)
    story.append(HRFlowable(width="100%", thickness=0.8, color=INK, spaceAfter=10))

    # Empresa
    story.append(Paragraph(_esc(name), S['title']))
    story.append(Spacer(1, 2))
    story.append(Paragraph(
        f"<b>{_esc(symbol)}</b>&nbsp;&nbsp;·&nbsp;&nbsp;{_esc(sector)}&nbsp;&nbsp;·&nbsp;&nbsp;"
        f"{_esc(profile.get('industry') or 'N/A')}&nbsp;&nbsp;·&nbsp;&nbsp;{_esc(profile.get('country') or '')}"
        f"&nbsp;&nbsp;·&nbsp;&nbsp;{_esc(profile.get('exchange') or '')}",
        S['meta']))
    story.append(Spacer(1, 10))

    # Franja de indicadores clave: etiquetas y valores en filas separadas para
    # que TODA la franja comparta la misma línea base, con separadores sutiles.
    _lab_st = ParagraphStyle('kl', fontName='Helvetica-Bold', fontSize=6.8, leading=9, textColor=MUTED)
    _val_st = ParagraphStyle('kv', fontName='Helvetica-Bold', fontSize=13, leading=16, textColor=INK)
    _kpi_labels = ["PRECIO", "MARKET CAP", "P/E (TTM)", "ROE", "MARGEN NETO", "PERFIL"]
    _kpi_values = [fv(price, "price"), fv(km.get("market_cap"), "money"), fv(km.get("pe"), "mult"),
                   fv(km.get("roe"), "pct"), fv(km.get("net_margin"), "pct"), company_type.title()]
    kt = Table([
        [Paragraph(_esc(l), _lab_st) for l in _kpi_labels],
        [Paragraph(_esc(v), _val_st) for v in _kpi_values],
    ], colWidths=[CW / 6.0] * 6)
    kt.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), PANEL),
        ('LINEABOVE', (0, 0), (-1, 0), 1.4, BRAND),
        ('LINEBEFORE', (1, 0), (-1, -1), 0.5, colors.HexColor('#e2e3e5')),
        ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
        ('TOPPADDING', (0, 0), (-1, 0), 9), ('BOTTOMPADDING', (0, 0), (-1, 0), 1),
        ('TOPPADDING', (0, 1), (-1, 1), 0), ('BOTTOMPADDING', (0, 1), (-1, 1), 9),
        ('LEFTPADDING', (0, 0), (-1, -1), 10), ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(kt)
    story.append(Spacer(1, 14))

    # Puntuación Finanzer: número + nivel + barras por categoría
    story.extend(section_header("", "Puntuación Finanzer", S))
    cat_rows = []
    for cat_name, cat in breakdown.items():
        cs, cm = cat.get("score", 0), cat.get("max", 20) or 20
        pct = cs / cm * 100
        tone = 'pos' if pct >= 65 else 'warn' if pct >= 45 else 'neg'
        cat_rows.append([
            Paragraph(_esc(cat_name), S['cell']),
            hbar(pct, width=2.55 * inch, height=5.5,
                 fg=(BRAND if tone == 'pos' else AMBER if tone == 'warn' else RED)),
            Paragraph(f"<b>{cs}</b><font color='#a5a5ac'>/{cm}</font>",
                      ParagraphStyle('sc', fontName='Helvetica', fontSize=8.6, alignment=TA_RIGHT)),
        ])
    cat_tbl = Table(cat_rows, colWidths=[1.35 * inch, 2.65 * inch, 0.55 * inch])
    cat_tbl.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3.2), ('BOTTOMPADDING', (0, 0), (-1, -1), 3.2),
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    score_left = Table([
        [Paragraph(f"<font size='40' color='{TONE_COLOR[score_tone].hexval()}'><b>{total}</b></font>"
                   f"<font size='13' color='#a5a5ac'> / 100</font>",
                   ParagraphStyle('big', fontName='Helvetica-Bold', leading=42, alignment=TA_CENTER))],
        [Spacer(1, 3)],
        [chip(level, score_tone, size=9)],
    ], colWidths=[2.0 * inch])
    score_left.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    sc_tbl = Table([[score_left, cat_tbl]], colWidths=[2.3 * inch, CW - 2.3 * inch])
    sc_tbl.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (0, 0), PANEL),
        ('ROUNDEDCORNERS', [6, 6, 6, 6]),
        ('TOPPADDING', (0, 0), (-1, -1), 10), ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 8), ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(sc_tbl)
    story.append(Spacer(1, 14))

    # Resumen ejecutivo adaptativo — bloques etiquetados en grilla de 2 columnas
    # (no un párrafo corrido): cada tema con su micro-encabezado verde.
    story.extend(section_header("", "Resumen ejecutivo", S))

    def _cap(t):
        t = (t or "").strip().rstrip('.')
        return (t[0].upper() + t[1:] + ".") if t else ""

    # solidez condensada para el resumen
    if fin_health and isinstance(fin_health, dict) and fin_health.get("score") is not None:
        sol_short = (f"salud financiera bancaria de {fin_health['score']}/10 "
                     f"({fin_health.get('level', '')})")
    elif altman.get("z_score") is not None:
        _zmap = {'safe': 'zona segura', 'grey': 'zona gris', 'distress': 'zona de riesgo'}
        sol_short = f"Altman Z de {altman['z_score']:.2f} ({_zmap.get(altman.get('zone'), '')})"
        if r_ic:
            sol_short += f"; {r_ic[2]}"
    else:
        sol_short = r_de[2] if r_de else None

    exec_items = [("PERFIL Y PUNTUACIÓN",
                   f"{_esc(name)} ({_esc(symbol)}) opera en el sector {_esc(sector.lower())} con un perfil "
                   f"{_esc(company_type)}. Puntuación Finanzer: <b>{total}/100</b> ({_esc(level.lower())}).")]
    _val = (_cap(r_pe[2]) + (" " + _cap(r_up[2]) if r_up else "")) if r_pe else (_cap(r_up[2]) if r_up else "")
    if _val.strip():
        exec_items.append(("VALORACIÓN", _esc(_val)))
    if not is_financial and r_spread:
        exec_items.append(("CREACIÓN DE VALOR", _esc(_cap(r_spread[2]))))
    elif r_roe:
        exec_items.append(("RENTABILIDAD", _esc(_cap(r_roe[2]))))
    _gro = " ".join(filter(None, [_cap(r_grev[2]) if r_grev else None, _cap(r_bb[2]) if r_bb else None]))
    if _gro.strip():
        exec_items.append(("CRECIMIENTO Y RETORNO", _esc(_gro)))
    if sol_short:
        exec_items.append(("SOLIDEZ", _esc(_cap(sol_short))))
    _ctx = " ".join(filter(None, [_cap(r_52[2]) if r_52 else None, _cap(r_beta[2]) if r_beta else None]))
    if _ctx.strip():
        exec_items.append(("CONTEXTO DE MERCADO", _esc(_ctx)))

    _exc_st = ParagraphStyle('exc', fontName='Helvetica', fontSize=8.6, leading=12.2, textColor=BODY)
    def _exec_cell(label, text):
        return Paragraph(
            f"<font size='6.8' color='{BRAND_TXT.hexval()}'><b>{_esc(label)}</b></font><br/>{text}", _exc_st)

    _pairs = [exec_items[i:i + 2] for i in range(0, len(exec_items), 2)]
    _grid = []
    for pr in _pairs:
        cells = [_exec_cell(l, t) for l, t in pr]
        if len(cells) == 1:
            cells.append('')
        _grid.append(cells)
    gt = Table(_grid, colWidths=[CW / 2.0] * 2)
    _gcmds = [
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('LEFTPADDING', (0, 0), (0, -1), 0), ('RIGHTPADDING', (0, 0), (0, -1), 14),
        ('LEFTPADDING', (1, 0), (1, -1), 10), ('RIGHTPADDING', (1, 0), (1, -1), 0),
    ]
    for i in range(len(_grid) - 1):
        _gcmds.append(('LINEBELOW', (0, i), (-1, i), 0.4, HAIR))
    gt.setStyle(TableStyle(_gcmds))
    story.append(gt)

    # balance de señales al pie del resumen
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f"<font size='6.8' color='#77777f'><b>BALANCE DE SEÑALES</b></font>&nbsp;&nbsp;&nbsp;"
        f"<font color='{BRAND_TXT.hexval()}'><b>{n_str}</b> fortaleza{'s' if n_str != 1 else ''}</font>"
        f"&nbsp;&nbsp;·&nbsp;&nbsp;"
        f"<font color='{AMBER.hexval()}'><b>{n_warn}</b> advertencia{'s' if n_warn != 1 else ''}</font>"
        f"&nbsp;&nbsp;·&nbsp;&nbsp;"
        f"<font color='{RED.hexval()}'><b>{n_red}</b> riesgo{'s' if n_red != 1 else ''}</font>",
        ParagraphStyle('bal', fontName='Helvetica', fontSize=9, leading=12)))

    # ════════════════ PÁGINA 2 — VALORACIÓN ════════════════
    story.append(PageBreak())
    story.extend(section_header("01", "Valoración", S))
    val_txt = _join_sentences([
        r_pe[2] if r_pe else None,
        r_fcfy[2] if r_fcfy else None,
        r_graham[2] if r_graham else None,
    ])
    if val_txt:
        story.append(Paragraph(val_txt, S['body']))
    story.append(Spacer(1, 4))

    # Tabla de múltiplos con brecha vs sector y Lectura adaptativa
    mult_defs = [
        ("P/E (TTM)", km.get("pe"), sector_bench.get("pe"), False, "mult"),
        ("Forward P/E", km.get("forward_pe"), sector_bench.get("forward_pe"), False, "mult"),
        ("P/B", km.get("pb"), sector_bench.get("pb"), False, "mult"),
        ("P/S", km.get("ps"), None, False, "mult"),
        ("PEG", km.get("peg"), sector_bench.get("peg"), False, "mult"),
        ("EV/EBITDA", km.get("ev_ebitda"), sector_bench.get("ev_ebitda"), False, "mult"),
        ("P/FCF", km.get("pfcf"), sector_bench.get("pfcf"), False, "mult"),
        ("FCF Yield", km.get("fcf_yield"), sector_bench.get("fcf_yield"), True, "pct"),
        ("Dividend Yield", km.get("dividend_yield"), None, True, "pct"),
    ]
    rows, reads = [], []
    for i, (lab, val, bench, hb, fm) in enumerate(mult_defs):
        r = read_vs_sector(lab, val, bench, hb, fm) if bench else None
        rows.append([lab, fv(val, fm), fv(bench, fm) if bench else "—",
                     r[3] if r else "—", r[0] if r else "—"])
        if r:
            reads.append((i, r[1]))
    story.append(data_table(
        ["MÚLTIPLO", "EMPRESA", "SECTOR", "BRECHA", "LECTURA"], rows,
        [1.9 * inch, 1.15 * inch, 1.15 * inch, 1.0 * inch, CW - 5.2 * inch],
        aligns=['LEFT', 'RIGHT', 'RIGHT', 'RIGHT', 'RIGHT'], reads=reads))
    story.append(Spacer(1, 12))

    # Valor intrínseco
    story.append(Paragraph("Valor intrínseco", S['h2']))
    iv_txt = _join_sentences([r_up[2] if r_up else None,
                              None if r_up else "el modelo DCF no es aplicable con los datos disponibles" +
                              (" (sector financiero: se valora sobre libros y retornos)" if is_financial else "")])
    if iv_txt:
        story.append(Paragraph(iv_txt, S['body']))
    iv_rows = [["Precio de mercado", fv(price, "price"), ""]]
    if graham is not None:
        iv_rows.append(["Número de Graham", fv(graham, "price"),
                        (r_graham[0] if r_graham else "")])
    if dcf.get("fair_value") is not None:
        iv_rows.append(["Valor justo DCF", fv(dcf.get("fair_value"), "price"), ""])
        iv_rows.append(["Potencial vs precio (upside)",
                        (f"{dcf['upside']:+.1f}%" if dcf.get("upside") is not None else "N/A"),
                        (r_up[0] if r_up else "")])
        if dcf.get("margin_of_safety") is not None:
            iv_rows.append(["Margen de seguridad", fv(dcf.get("margin_of_safety"), "pct"), ""])
    iv_reads = []
    for i, row in enumerate(iv_rows):
        if row[2] == (r_up[0] if r_up else None) and r_up:
            iv_reads.append((i, r_up[1]))
        elif row[2] == (r_graham[0] if r_graham else None) and r_graham:
            iv_reads.append((i, r_graham[1]))
    story.append(data_table(["CONCEPTO", "VALOR", "LECTURA"], iv_rows,
                            [3.4 * inch, 1.6 * inch, CW - 5.0 * inch],
                            aligns=['LEFT', 'RIGHT', 'RIGHT'], reads=iv_reads))

    if dcf.get("fair_value") is not None:
        story.append(Spacer(1, 6))
        params = (f"Parámetros del modelo — WACC {fv(dcf.get('wacc'), 'pct')} · "
                  f"crecimiento {fv(dcf.get('growth_rate'), 'pct')} · "
                  f"terminal {fv(dcf.get('terminal_growth'), 'pct')}")
        vc = dcf.get("value_composition") or {}
        if vc.get("terminal_pct") is not None:
            params += f" · el valor terminal aporta el {vc['terminal_pct']:.0f}% del valor total"
        story.append(Paragraph(_esc(params), S['small']))

    # Sensibilidad DCF
    matrix = sensitivity.get("matrix") or []
    if matrix:
        story.append(Spacer(1, 10))
        story.append(Paragraph("Sensibilidad del valor justo", S['h2']))
        story.append(Paragraph(
            "Valor justo estimado según crecimiento (filas) y tasa de descuento (columnas). "
            "Verde: escenario por encima del precio actual; rojo: por debajo.", S['small']))
        story.append(Spacer(1, 4))
        g_rates = sensitivity.get("growth_rates") or []
        d_rates = sensitivity.get("discount_rates") or []
        base_gi, base_di = sensitivity.get("base_growth_idx"), sensitivity.get("base_discount_idx")
        head = ["CREC. \\ WACC"] + [f"{dr * 100:.1f}%" for dr in d_rates]
        srows = [head]
        for gi, row in enumerate(matrix):
            srows.append([f"{g_rates[gi] * 100:.1f}%"] +
                         [(f"${v:,.0f}" if v is not None else "—") for v in row])
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
        if price:
            for gi in range(len(matrix)):
                for di in range(len(matrix[gi])):
                    v = matrix[gi][di]
                    if v is None:
                        continue
                    diff = (v - price) / price * 100
                    if diff > 30:    bg = colors.HexColor('#d9f3e6')
                    elif diff > 10:  bg = colors.HexColor('#ecf9f2')
                    elif diff > -10: bg = colors.HexColor('#f6f6f4')
                    elif diff > -30: bg = colors.HexColor('#f9edea')
                    else:            bg = colors.HexColor('#f4dfdb')
                    cmds.append(('BACKGROUND', (di + 1, gi + 1), (di + 1, gi + 1), bg))
        if base_gi is not None and base_di is not None:
            cmds.append(('BOX', (base_di + 1, base_gi + 1), (base_di + 1, base_gi + 1), 1.4, BRAND))
        st.setStyle(TableStyle(cmds))
        story.append(st)
        if price:
            story.append(Paragraph(
                _esc(f"Precio actual: ${price:,.2f}. El recuadro verde marca el escenario base del modelo."),
                S['small']))

    # ════════════════ PÁGINA 3 — RENTABILIDAD + SOLIDEZ ════════════════
    story.append(PageBreak())
    story.extend(section_header("02", "Rentabilidad y eficiencia", S))
    rent_txt = _join_sentences([
        r_roe[2] if r_roe else None,
        (r_spread[2] if (r_spread and not is_financial) else None),
    ])
    if rent_txt:
        story.append(Paragraph(rent_txt, S['body']))
    story.append(Spacer(1, 4))

    ret_defs = [
        ("ROE", km.get("roe"), sector_bench.get("roe"), True, "pct"),
        ("ROA", km.get("roa"), sector_bench.get("roa"), True, "pct"),
        ("ROIC", km.get("roic"), sector_bench.get("roic"), True, "pct"),
        ("Margen bruto", km.get("gross_margin"), sector_bench.get("gross_margin"), True, "pct"),
        ("Margen operativo", km.get("operating_margin"), sector_bench.get("operating_margin"), True, "pct"),
        ("Margen neto", km.get("net_margin"), sector_bench.get("net_margin"), True, "pct"),
    ]
    rows, reads = [], []
    for i, (lab, val, bench, hb, fm) in enumerate(ret_defs):
        r = read_vs_sector(lab, val, bench, hb, fm) if bench else None
        rows.append([lab, fv(val, fm), fv(bench, fm) if bench else "—",
                     r[3] if r else "—", r[0] if r else "—"])
        if r:
            reads.append((i, r[1]))
    if not is_financial and km.get("roic_wacc_spread") is not None and r_spread:
        rows.append(["Spread ROIC − WACC", f"{km['roic_wacc_spread'] * 100:+.1f} pp", "> 0", "—", r_spread[0]])
        reads.append((len(rows) - 1, r_spread[1]))
    story.append(data_table(
        ["MÉTRICA", "EMPRESA", "SECTOR", "BRECHA", "LECTURA"], rows,
        [1.9 * inch, 1.15 * inch, 1.15 * inch, 1.0 * inch, CW - 5.2 * inch],
        aligns=['LEFT', 'RIGHT', 'RIGHT', 'RIGHT', 'RIGHT'], reads=reads))

    story.append(Spacer(1, 8))
    story.append(Paragraph("Cifras del ejercicio", S['h2']))
    story.append(data_table(
        ["CONCEPTO", "VALOR", "CONCEPTO", "VALOR"],
        [["Ingresos", fv(km.get("revenue"), "money"), "EBITDA", fv(km.get("ebitda"), "money")],
         ["Beneficio operativo", fv(km.get("operating_income"), "money"), "Beneficio neto", fv(km.get("net_income"), "money")],
         ["Flujo de caja operativo", fv(km.get("operating_cash_flow"), "money"), "Flujo de caja libre", fv(km.get("free_cash_flow"), "money")],
         ["EPS", fv(km.get("eps"), "price"), "Valor en libros / acción", fv(km.get("book_value_per_share"), "price")]],
        [2.05 * inch, 1.55 * inch, 2.05 * inch, CW - 5.65 * inch],
        aligns=['LEFT', 'RIGHT', 'LEFT', 'RIGHT']))

    story.append(Spacer(1, 12))
    story.extend(section_header("03", "Solidez financiera", S))
    sol_txt = _join_sentences([
        r_cr[2] if r_cr else None,
        r_de[2] if r_de else None,
        r_nde[2] if r_nde else None,
        r_ic[2] if r_ic else None,
        r_pay[2] if r_pay else None,
    ])
    if sol_txt:
        story.append(Paragraph(sol_txt, S['body']))
    story.append(Spacer(1, 4))

    sol_defs = [
        ("Current ratio", km.get("current_ratio"), "mult", r_cr),
        ("Quick ratio", km.get("quick_ratio"), "mult", None),
        ("Cash ratio", km.get("cash_ratio"), "mult", None),
        ("Deuda / Equity", km.get("de"), "mult", r_de),
        ("Deuda / Activos", km.get("debt_to_assets"), "pct", None),
        ("Deuda neta / EBITDA", km.get("net_debt_to_ebitda"), "mult", r_nde),
        ("Cobertura de intereses", km.get("interest_coverage"), "mult", r_ic),
        ("Payout del dividendo", km.get("payout_ratio"), "pct", r_pay),
    ]
    rows, reads = [], []
    for lab, val, fm, rd in sol_defs:
        if val is None:
            continue
        i = len(rows)
        rows.append([lab, fv(val, fm), rd[0] if rd else "—"])
        if rd:
            reads.append((i, rd[1]))
    if rows:
        story.append(data_table(["MÉTRICA", "VALOR", "LECTURA"], rows,
                                [3.2 * inch, 1.6 * inch, CW - 4.8 * inch],
                                aligns=['LEFT', 'RIGHT', 'RIGHT'], reads=reads))
    bal = (f"Balance — deuda total {fv(km.get('total_debt'), 'money')} · caja {fv(km.get('cash'), 'money')} · "
           f"patrimonio {fv(km.get('total_equity'), 'money')} · activos {fv(km.get('total_assets'), 'money')}")
    story.append(Spacer(1, 4))
    story.append(Paragraph(_esc(bal), S['small']))

    # ════════════════ PÁGINA 4 — CRECIMIENTO + RETORNO AL ACCIONISTA ════════════════
    story.append(PageBreak())
    story.extend(section_header("04", "Crecimiento y retorno al accionista", S))
    gro_txt = _join_sentences([
        r_grev[2] if r_grev else None,
        r_gearn[2] if r_gearn else None,
        r_bb[2] if r_bb else None,
    ])
    if gro_txt:
        story.append(Paragraph(gro_txt, S['body']))
    story.append(Spacer(1, 4))

    gro_defs = [
        ("Crecimiento de ingresos (YoY)", km.get("revenue_growth"), "pct", r_grev),
        ("Crecimiento de beneficios (YoY)", km.get("earnings_growth"), "pct", r_gearn),
        ("Buyback yield (recompras netas)", km.get("buyback_yield"), "pct", r_bb),
        ("Shareholder yield (div. + recompras)", km.get("shareholder_yield"), "pct", None),
        ("Dividend yield", km.get("dividend_yield"), "pct", None),
    ]
    rows, reads = [], []
    for lab, val, fm, rd in gro_defs:
        if val is None:
            continue
        i = len(rows)
        rows.append([lab, fv(val, fm), rd[0] if rd else "—"])
        if rd:
            reads.append((i, rd[1]))
    if rows:
        story.append(data_table(["MÉTRICA", "VALOR", "LECTURA"], rows,
                                [3.2 * inch, 1.6 * inch, CW - 4.8 * inch],
                                aligns=['LEFT', 'RIGHT', 'RIGHT'], reads=reads))

    # Rango 52 semanas con barra de posición
    if pos52 is not None:
        story.append(Spacer(1, 10))
        story.append(Paragraph("Rango de precio · 52 semanas", S['h2']))
        if r_52:
            story.append(Paragraph(_join_sentences([r_52[2]]), S['body']))
        bar = hbar(pos52, width=CW - 2.4 * inch, height=7)
        rng = Table([[
            Paragraph(f"<font size='8' color='#77777f'>{fv(l52, 'price')}</font>", S['cell']),
            bar,
            Paragraph(f"<font size='8' color='#77777f'>{fv(h52, 'price')}</font>",
                      ParagraphStyle('r', parent=S['cell'], alignment=TA_RIGHT)),
        ]], colWidths=[1.2 * inch, CW - 2.4 * inch, 1.2 * inch])
        rng.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(rng)
        story.append(Paragraph(
            _esc(f"Precio actual {fv(price, 'price')} — posición {pos52:.0f}% del rango"),
            ParagraphStyle('rngc', parent=S['small'], alignment=TA_CENTER, spaceBefore=3)))

    # Evolución histórica anual (si está disponible)
    yearly = analysis.get("yearly_financials") or []
    if yearly:
        story.append(Spacer(1, 10))
        story.append(Paragraph("Evolución histórica anual", S['h2']))
        sorted_y = sorted(yearly, key=lambda x: x.get("year", 0))
        yrows = []
        for i, y in enumerate(sorted_y):
            rev, earn = y.get("revenue"), y.get("earnings")
            g = ""
            if i > 0 and rev and sorted_y[i - 1].get("revenue"):
                pr = sorted_y[i - 1]["revenue"]
                if pr:
                    g = f"{(rev - pr) / abs(pr) * 100:+.1f}%"
            yrows.append([str(y.get("year", "")), fv(rev, "money"), fv(earn, "money"), g or "—"])
        story.append(data_table(["AÑO", "INGRESOS", "BENEFICIO", "CREC. INGRESOS"],
                                yrows, [1.2 * inch, 2.2 * inch, 2.2 * inch, CW - 5.6 * inch],
                                aligns=['LEFT', 'RIGHT', 'RIGHT', 'RIGHT']))

    # ════════════════ EVALUACIÓN INSTITUCIONAL + ALERTAS ════════════════
    # Sin salto forzado: la sección fluye tras crecimiento para no dejar media
    # página en blanco. El encabezado viaja pegado a la primera tarjeta.
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

    # Altman Z (no financieras) o Salud financiera (financieras)
    if fin_health and isinstance(fin_health, dict) and fin_health.get("score") is not None:
        fh_tone = 'pos' if fin_health.get("level") in ("STRONG", "GOOD") else \
                  'warn' if fin_health.get("level") == "NEUTRAL" else 'neg'
        details = fin_health.get("details") or []
        det_txt = " · ".join(d.get("detail", "") for d in details[:4])
        _emit_card(model_card(f"{fin_health['score']}/10", fh_tone, "Salud financiera (sector financiero)",
                              str(fin_health.get("level", "")),
                              _esc((fin_health.get("interpretation", "") + ". " + det_txt).strip())))
        story.append(Spacer(1, 8))
    if altman and altman.get("z_score") is not None and not is_financial:
        z, zone = altman.get("z_score", 0), altman.get("zone", "grey")
        z_tone = 'pos' if zone == 'safe' else 'warn' if zone == 'grey' else 'neg'
        z_lab = "Zona segura" if zone == 'safe' else "Zona gris" if zone == 'grey' else "Zona de riesgo"
        z_body = (f"{altman.get('interpretation', '')}. El modelo Altman Z pondera capital de trabajo, beneficios retenidos, "
                  f"EBIT, valor de mercado y ventas para estimar el riesgo de insolvencia a 2 años: por encima de 2.99 el "
                  f"riesgo es bajo; por debajo de 1.81, elevado.")
        _emit_card(model_card(f"{z:.2f}", z_tone, "Altman Z-Score", z_lab, _esc(z_body)))
        story.append(Spacer(1, 8))

    if piotroski and piotroski.get("score") is not None:
        f_sc, f_max = piotroski.get("score", 0), piotroski.get("max_score", 9)
        f_tone = 'pos' if f_sc >= 7 else 'warn' if f_sc >= 4 else 'neg'
        f_body = (f"{piotroski.get('interpretation', '')}. El F-Score de Piotroski verifica 9 señales contables de mejora "
                  f"en rentabilidad, estructura de capital y eficiencia operativa"
                  + (f" ({piotroski.get('fiscal_year')})" if piotroski.get("fiscal_year") else "") + ".")
        _emit_card(model_card(f"{f_sc}/{f_max}", f_tone, "Piotroski F-Score",
                              str(piotroski.get("level", "")), _esc(f_body)))

        detail_labels = {
            "roa_positive": "ROA positivo", "cfo_positive": "Flujo de caja operativo positivo",
            "roa_improved": "ROA en mejora", "earnings_quality": "Calidad del beneficio (CFO > BN)",
            "debt_reduced": "Reducción de deuda", "current_ratio_improved": "Liquidez en mejora",
            "no_dilution": "Sin dilución de acciones", "gross_margin_improved": "Margen bruto en mejora",
            "asset_turnover_improved": "Rotación de activos en mejora",
        }
        f_details = piotroski.get("details") or {}
        if f_details:
            story.append(Spacer(1, 6))
            rows, reads = [], []
            for k, crit in f_details.items():
                ok = bool(crit.get("passed"))
                i = len(rows)
                rows.append([detail_labels.get(k, k.replace("_", " ").title()),
                             (crit.get("detail") or "")[:72], "Cumple" if ok else "No cumple"])
                reads.append((i, 'pos' if ok else 'neg'))
            story.append(data_table(["CRITERIO", "DETALLE", "ESTADO"], rows,
                                    [2.1 * inch, CW - 3.3 * inch, 1.2 * inch],
                                    aligns=['LEFT', 'LEFT', 'RIGHT'], reads=reads, bold_col=None))

    # Si ningún modelo emitió tarjeta, el encabezado 05 aún está pendiente.
    if _sec5_head is not None:
        story.extend(_sec5_head)
        _sec5_head = None

    # Desglose del score como TABLA: fila de categoría (nombre + puntos + barra)
    # seguida de sus indicadores con ajuste coloreado y lectura del motor.
    if breakdown:
        story.append(Spacer(1, 10))
        story.append(Paragraph("Desglose de la puntuación", S['h2']))
        story.append(Paragraph(
            "Cada categoría parte de una base neutral de 10/20. La columna Ajuste muestra cuánto suma o "
            "resta cada indicador según la banda en la que cae.", S['small']))
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
        for cat_name, cat in breakdown.items():
            cs, cm = cat.get("score", 0), cat.get("max", 20) or 20
            pctc = cs / cm * 100
            tone = 'pos' if pctc >= 65 else 'warn' if pctc >= 45 else 'neg'
            bar_color = BRAND if tone == 'pos' else AMBER if tone == 'warn' else RED
            bd_rows.append([
                Paragraph(_esc(cat_name), _cat_st),
                Paragraph(f"<b>{cs}/{cm}</b>",
                          ParagraphStyle('bdcs', fontName='Helvetica-Bold', fontSize=8.8, leading=11,
                                         textColor=TONE_COLOR[tone], alignment=TA_CENTER)),
                hbar(pctc, width=CW - 2.75 * inch - 0.35 * inch, height=5, fg=bar_color),
            ])
            bd_cmds.append(('BACKGROUND', (0, r), (-1, r), PANEL))
            bd_cmds.append(('TOPPADDING', (0, r), (-1, r), 5.5))
            bd_cmds.append(('BOTTOMPADDING', (0, r), (-1, r), 5.5))
            r += 1
            adjs = cat.get("adjustments") or []
            for k, adj in enumerate(adjs):
                a = adj.get("adjustment", 0)
                sev = adj.get("severity", "")
                if a > 0:
                    tone_a = 'pos'
                elif a < 0:
                    tone_a = 'neg' if sev in ("severe", "critical") else 'warn'
                else:
                    tone_a = 'neu'
                sign = f"+{a}" if a > 0 else str(a)
                val = adj.get("value", "")
                bd_rows.append([
                    Paragraph(f"{_esc(adj.get('metric', ''))}"
                              + (f" <font color='#a5a5ac'>({_esc(val)})</font>" if val else ""), _ind_st),
                    Paragraph(f"<b>{sign}</b>",
                              ParagraphStyle('bda', fontName='Helvetica-Bold', fontSize=8.4, leading=10.5,
                                             textColor=TONE_COLOR[tone_a], alignment=TA_CENTER)),
                    Paragraph(_esc(adj.get('reason', '')), _rea_st),
                ])
                if k < len(adjs) - 1:
                    bd_cmds.append(('LINEBELOW', (0, r), (-1, r), 0.3, HAIR))
                r += 1
        bd_tbl = Table(bd_rows, colWidths=_w, repeatRows=1)
        bd_tbl.setStyle(TableStyle(bd_cmds))
        story.append(bd_tbl)

    # Alertas
    story.append(Spacer(1, 12))
    story.extend(section_header("06", "Alertas y señales", S))
    story.append(Paragraph(
        f"<font color='{RED.hexval()}'><b>{n_red}</b> riesgo{'s' if n_red != 1 else ''}</font>&nbsp;&nbsp;·&nbsp;&nbsp;"
        f"<font color='{AMBER.hexval()}'><b>{n_warn}</b> advertencia{'s' if n_warn != 1 else ''}</font>&nbsp;&nbsp;·&nbsp;&nbsp;"
        f"<font color='{BRAND_TXT.hexval()}'><b>{n_str}</b> fortaleza{'s' if n_str != 1 else ''}</font>",
        ParagraphStyle('alsum', fontName='Helvetica', fontSize=9.5, leading=13, spaceAfter=6)))

    def alert_block(title, items, tone):
        if not items:
            return
        story.append(Paragraph(f"<font color='{TONE_COLOR[tone].hexval()}'><b>{_esc(title)}</b></font>",
                               ParagraphStyle('abt', fontName='Helvetica-Bold', fontSize=9,
                                              leading=12, spaceBefore=5, spaceAfter=2)))
        for a in items:
            head = f"{a.get('category', '')}: {a.get('reason', '')}"
            det = a.get("detail", "")
            txt = f"<font color='{TONE_COLOR[tone].hexval()}'>●</font>&nbsp;&nbsp;<b>{_esc(head)}</b>"
            if det and det != a.get("reason"):
                txt += f"<br/><font size='7.6' color='#77777f'>{_esc(det)}</font>"
            story.append(Paragraph(txt, ParagraphStyle(
                'ab', fontName='Helvetica', fontSize=8.4, leading=11, textColor=INK,
                leftIndent=8, spaceAfter=2.5)))

    alert_block("Riesgos", alerts.get("red_flags") or [], 'neg')
    alert_block("Advertencias", alerts.get("warnings") or [], 'warn')
    alert_block("Fortalezas", alerts.get("strengths") or [], 'pos')
    if not (n_red or n_warn or n_str):
        story.append(Paragraph("No se detectaron alertas significativas.", S['body']))

    # Metodología + cierre
    story.append(Spacer(1, 14))
    story.append(HRFlowable(width="100%", thickness=0.5, color=HAIR))
    story.append(Spacer(1, 5))
    story.append(Paragraph(
        "<b>Metodología.</b> Este informe combina ratios TTM y del último ejercicio (fuente: Yahoo Finance) con los "
        "modelos de Altman (1968), Piotroski (2000), número de Graham, un DCF multietapa con WACC estimado por CAPM y "
        "la puntuación propietaria Finanzer (5 categorías, 100 puntos). Las lecturas se generan automáticamente según "
        "la banda en la que cae cada indicador frente a umbrales canónicos y a la mediana de su sector.",
        ParagraphStyle('meth', parent=S['small'], leading=10.5)))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "Documento generado automáticamente por Finanzer. La información puede contener errores u omisiones y no "
        "constituye asesoría financiera, recomendación de inversión ni oferta de valores. Verifique los datos y "
        "consulte a un profesional antes de invertir.",
        ParagraphStyle('disc', parent=S['small'], textColor=FAINT, fontSize=7)))

    doc.build(story)
