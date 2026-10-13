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
from reportlab.lib.utils import ImageReader

from settings import cfg
from financial_ratios import IC_NEGATIVE, NET_CASH_TEXT, SECTOR_THRESHOLDS, ThresholdConfig, growth_for_bands

_PDF_BANDS = cfg("thresholds.pdf")  # bandas de las lecturas del informe
DE_NOT_APPLICABLE = "No aplica a entidades financieras"

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
# Cada lector devuelve (etiqueta_corta, tono, frase) o None si no hay dato.
# tono ∈ {pos, neg, warn, neu} → color en tablas y acentos del texto.

def _pct(v, dec=1):
    return f"{v * 100:.{dec}f}%"


def read_vs_sector(name, val, bench, higher_better, fmt="mult", ref="del sector"):
    """Lectura genérica de una métrica vs la mediana sectorial (o la del mercado: `ref`)."""
    if val is None or bench in (None, 0):
        return None
    diff = (val - bench) / abs(bench) * 100
    d = f"{'+' if diff > 0 else ''}{diff:.0f}%"
    b = _PDF_BANDS["vs_sector_bounds"]
    if higher_better:
        if diff >= b[0]:   lab, tone = "Muy superior", 'pos'
        elif diff >= b[1]: lab, tone = "Superior", 'pos'
        elif diff > -b[1]: lab, tone = "En línea", 'neu'
        elif diff > -b[0]: lab, tone = "Inferior", 'warn'
        else:            lab, tone = "Muy inferior", 'neg'
    else:
        if diff <= -b[0]:  lab, tone = "Descuento profundo", 'pos'
        elif diff <= -b[1]: lab, tone = "Descuento", 'pos'
        elif diff < b[1]:  lab, tone = "En línea", 'neu'
        elif diff < b[0]:  lab, tone = "Prima moderada", 'warn'
        else:            lab, tone = "Prima elevada", 'neg'
    vv = _pct(val) if fmt == "pct" else f"{val:.1f}x"
    bb = _pct(bench) if fmt == "pct" else f"{bench:.1f}x"
    frase = f"{name} de {vv} frente a {bb} {ref} ({d}): {lab.lower()}"
    return lab, tone, frase, d


def read_pe(pe, sector_pe, spread, ref="del sector"):
    if pe is None:
        return None
    if pe <= 0:
        return ("Sin beneficios", 'neg',
                "el P/E no es significativo al no haber beneficios positivos en los últimos doce meses")
    r = read_vs_sector("P/E", pe, sector_pe, False, ref=ref)
    if r is None:
        return ("—", 'neu', f"el P/E se sitúa en {pe:.1f}x")
    lab, tone, _, d = r
    base = (f"el mercado paga {pe:.1f}x beneficios, un {d} frente a la mediana {ref} "
            f"({sector_pe:.1f}x)")
    if tone in ('warn', 'neg') and spread is not None and spread > _PDF_BANDS["pe_spread_support"]:
        base += (f"; una prima que encuentra respaldo parcial en la creación de valor de la compañía "
                 f"(ROIC−WACC de +{_pct(spread)})")
    elif tone == 'pos':
        base += "; un descuento que amerita revisar si responde a riesgos específicos o a una oportunidad"
    return lab, tone, base


# Etapa 9a: UNA sola fuente de bandas por métrica. Las lecturas de las métricas que
# puntúan leen las bandas del score (thresholds.score.*) y, donde el arquetipo lo
# permite, las sectoriales (sectors.score_thresholds: ROE y D/E). thresholds.pdf
# solo conserva las bandas de métricas que el score no puntúa.
def read_roe(roe, roa, th=None, market=False):
    if roe is None:
        return None
    T = cfg("thresholds.score.rentabilidad")
    th = th or ThresholdConfig()
    hi, lo = th.roe_high, th.roe_low
    if roe < 0 and roa is not None and roa > T["negative_equity_min_roa"]:
        return ("Distorsionado", 'neu',
                f"el ROE negativo responde a un patrimonio contable negativo por recompras agresivas, "
                f"no a pérdidas: el ROA de {_pct(roa)} confirma la rentabilidad real de los activos")
    su = "el mercado" if market else "su sector"
    ref = f" ({'mercado' if market else 'sector'}: {_pct(lo)} competitivo, {_pct(hi)} rango alto)"
    if roe >= hi * T["roe_high_mult"]:
        return ("Excepcional", 'pos', f"el ROE de {_pct(roe)} es excepcional "
                                      f"{'frente al mercado' if market else 'para su sector'}" + ref)
    if roe >= hi:   return ("Alto", 'pos', f"el ROE de {_pct(roe)} está en el rango alto de {su}" + ref)
    if roe >= lo:   return ("Competitivo", 'neu', f"el ROE de {_pct(roe)} es competitivo en {su}" + ref)
    if roe >= T["roe_floor"]:
        return ("Bajo", 'warn', f"el ROE de {_pct(roe)} queda por debajo del nivel competitivo de {su}" + ref)
    if roe >= 0:    return ("Débil", 'neg', f"el ROE de {_pct(roe)} es débil para prácticamente cualquier sector")
    return ("Negativo", 'neg', f"el ROE de {_pct(roe)} refleja destrucción de valor para el accionista")


def read_spread(spread, roic, wacc):
    if spread is None:
        return None
    b = cfg("thresholds.score.rentabilidad.spread_bounds")   # las del score
    if spread >= b[0]:
        return ("Crea mucho valor", 'pos',
                f"con un ROIC de {_pct(roic)} frente a un costo de capital (WACC) de {_pct(wacc)}, la compañía genera "
                f"un spread de +{_pct(spread)}: cada dólar reinvertido crea valor económico sustancial")
    if spread >= b[1]:
        return ("Crea valor", 'pos',
                f"el ROIC ({_pct(roic)}) supera al WACC ({_pct(wacc)}) en {_pct(spread)}, señal de creación de valor")
    if spread >= b[2]:
        return ("Marginal", 'neu',
                f"el ROIC ({_pct(roic)}) apenas cubre el costo de capital ({_pct(wacc)}): la creación de valor es marginal")
    if spread >= b[3]:
        return ("Al límite", 'warn',
                f"el ROIC ({_pct(roic)}) queda ligeramente por debajo del costo de capital ({_pct(wacc)})")
    return ("Destruye valor", 'neg',
            f"el ROIC ({_pct(roic)}) no cubre el costo de capital ({_pct(wacc)}): el crecimiento a estos retornos destruye valor")


def read_current(cr):
    if cr is None: return None
    b = cfg("thresholds.score.solidez.current_bounds")   # las del score
    if cr >= b[0]:  return ("Holgada", 'pos', f"el current ratio de {cr:.2f}x cubre con holgura los pasivos corrientes")
    if cr >= b[1]:  return ("Sólida", 'pos', f"la posición de liquidez es sólida (current ratio {cr:.2f}x)")
    if cr >= b[2]:  return ("Justa", 'neu', f"la liquidez es justa (current ratio {cr:.2f}x): cubre sus obligaciones de corto plazo")
    if cr >= b[3]:  return ("Ajustada", 'warn', f"la liquidez es ajustada (current ratio {cr:.2f}x), con poco margen de maniobra")
    return ("Tensión", 'neg', f"el current ratio de {cr:.2f}x indica que los pasivos corrientes superan a los activos corrientes")


def read_de(de, threshold=None, coverage=None, market=False):
    if de is None: return None
    if de < 0:    return ("Equity negativo", 'warn', "el patrimonio contable es negativo por recompras acumuladas, lo que invalida la lectura tradicional del D/E")
    T = cfg("thresholds.score.solidez")                   # las del score, sobre el umbral sectorial
    t = threshold if threshold else ThresholdConfig().debt_equity_high
    m = T["de_mults"]
    ref = f" (umbral {'del mercado' if market else 'del sector'} {t:.1f}x)"
    if de <= t * m[0]: return ("Conservador", 'pos', f"el apalancamiento es conservador (D/E {de:.2f}x)" + ref)
    if de <= t:        return ("Controlado", 'pos', f"el apalancamiento está controlado (D/E {de:.2f}x)" + ref)
    if de <= t * m[1]: return ("Aceptable", 'neu', f"el apalancamiento es aceptable, cerca del límite {'del mercado' if market else 'sectorial'} (D/E {de:.2f}x)" + ref)
    if de <= t * m[2]: return ("Elevado", 'warn', f"el apalancamiento es elevado (D/E {de:.2f}x) y merece seguimiento" + ref)
    if coverage is not None and coverage >= T["de_mitigation_coverage"]:
        return ("Alto, servible", 'warn', f"el D/E es alto ({de:.2f}x) pero la deuda es fácilmente servible "
                                          f"(cobertura {coverage:.0f}x)" + ref)
    return ("Alto", 'neg', f"el apalancamiento es alto (D/E {de:.2f}x)" + ref)


def read_coverage(ic, state=None):
    # Etapa 5: EBIT < 0 con caja neta -> no significativa; con deuda neta ->
    # riesgo, sin presentar la cifra negativa como si fuera una cobertura.
    if state == "no_significativo":
        return ("No significativa", 'neu', "con EBIT negativo y caja neta, la cobertura de intereses no es "
                "significativa: los intereses se pagan con caja")
    if ic is None: return None
    if state == "negativa":
        return ("Riesgo", 'neg', "el resultado operativo es negativo (EBIT < 0) y la empresa tiene deuda neta: "
                "los intereses no se cubren con el negocio")
    b = cfg("thresholds.score.solidez.coverage_bounds")   # las del score
    if ic >= b[0]:  return ("Muy holgada", 'pos', f"la deuda es fácilmente servible: cobertura de intereses de {ic:.1f}x")
    if ic >= b[1]:  return ("Sólida", 'pos', f"el beneficio operativo cubre {ic:.1f} veces el gasto por intereses")
    if ic >= b[2]:  return ("Aceptable", 'neu', f"la cobertura de intereses ({ic:.1f}x) es aceptable")
    if ic >= b[3]:  return ("Justa", 'warn', f"la cobertura de intereses ({ic:.1f}x) deja poco margen ante caídas del beneficio operativo")
    return ("Crítica", 'neg', f"la cobertura de intereses ({ic:.1f}x) es críticamente baja")


def read_nde(nde, state=None, net_debt=None, reit=False):
    # Etapa 5 (regla M): con EBITDA <= 0 la ratio no se lee; "caja neta" solo
    # cuando la caja supera a la deuda total. Etapa 9a: en REIT, las bandas de REIT
    # del score (thresholds.score.solidez.reit_nde_*), una sola fuente.
    if state == "no_significativo":
        txt = "con EBITDA negativo, la deuda neta/EBITDA no es significativa"
        if net_debt is not None and net_debt < 0:
            txt += f"; {NET_CASH_TEXT}"
        return ("No significativa", 'neu', txt)
    if nde is None: return None
    if nde < 0:    return ("Caja neta", 'pos', NET_CASH_TEXT)
    if reit:
        b = cfg("thresholds.score.solidez.reit_nde_bounds")
        if nde <= b[0]: return ("Conservadora", 'pos', f"la deuda neta ({nde:.1f}x EBITDA) es conservadora para un REIT")
        if nde <= b[1]: return ("Adecuada", 'pos', f"la deuda neta ({nde:.1f}x EBITDA) está en el rango habitual de un "
                                                   f"REIT con grado de inversión (hasta {b[1]:.1f}x)")
        if nde <= b[2]: return ("En línea", 'neu', f"la deuda neta ({nde:.1f}x EBITDA) está en línea con los REIT")
        if nde <= b[3]: return ("Elevada", 'warn', f"la deuda neta ({nde:.1f}x EBITDA) es elevada para un REIT")
        return ("Alta", 'neg', f"la deuda neta ({nde:.1f}x EBITDA) es alta para un REIT")
    b = _PDF_BANDS["nde_bounds"]
    if nde < b[0]:    return ("Baja", 'pos', f"la deuda neta equivale a {nde:.1f}x EBITDA, un nivel bajo")
    if nde < b[1]:  return ("Moderada", 'neu', f"la deuda neta ({nde:.1f}x EBITDA) es manejable")
    if nde < b[2]:    return ("Elevada", 'warn', f"la deuda neta ({nde:.1f}x EBITDA) es elevada")
    return ("Alta", 'neg', f"la deuda neta ({nde:.1f}x EBITDA) es alta y condiciona la flexibilidad financiera")


def read_runway(rw):
    """Runway de GROWTH_PRE_PROFIT (etapa 7): (etiqueta, tono, frase) o None sin dato."""
    if not rw or rw.get("state") not in ("autofinanciada", "runway"):
        return None
    if rw["state"] == "autofinanciada":
        return ("Autofinanciada", 'pos', "el FCF de los últimos doce meses es positivo: la empresa no consume caja")
    b, y = cfg("thresholds.score.solidez.runway_bounds"), rw["years"]
    if y >= b[0]: return ("Holgado", 'pos', f"la caja cubre {y:.1f} años de quema de FCF")
    if y >= b[1]: return ("Cómodo", 'pos', f"la caja cubre {y:.1f} años de quema de FCF")
    if y >= b[2]: return ("Ajustado", 'warn', f"la caja cubre {y:.1f} años de quema de FCF: tendrá que financiarse")
    return ("Crítico", 'neg', f"la caja cubre {y:.1f} años de quema de FCF: necesita financiación urgente")


def read_payout(p, basis=None):
    if p is None: return None
    if basis == "ffo":    # REIT (etapa 7): mismos tramos que el score (thresholds.score.calidad)
        b = cfg("thresholds.score.calidad.reit_ffo_payout_bounds")
        if p < 0:     return ("FFO negativo", 'neg', "el dividendo se paga con un FFO negativo, algo insostenible en el tiempo")
        if p <= b[0]: return ("Holgado", 'pos', f"el payout sobre FFO de {_pct(p, 0)} deja margen para sostener el dividendo")
        if p <= b[1]: return ("Cubierto", 'pos', f"el payout sobre FFO de {_pct(p, 0)} está cubierto por el FFO")
        if p <= b[2]: return ("Justo", 'warn', f"el payout sobre FFO de {_pct(p, 0)} deja poco margen sobre el FFO")
        return ("Insostenible", 'neg', f"el payout sobre FFO de {_pct(p, 0)} supera lo que genera el FFO: "
                                       "el dividendo actual no es sostenible")
    if p < 0:     return ("Con pérdidas", 'neg', "el dividendo se paga en un ejercicio con pérdidas, algo insostenible en el tiempo")
    b = _PDF_BANDS["payout_bounds"]
    if p < b[0]:  return ("Conservador", 'pos', f"el payout de {_pct(p, 0)} deja amplio margen para sostener y aumentar el dividendo")
    if p < b[1]:  return ("Sostenible", 'pos', f"el payout de {_pct(p, 0)} es sostenible")
    if p < b[2]:  return ("Exigente", 'warn', f"el payout de {_pct(p, 0)} es exigente y depende de la estabilidad del beneficio")
    if p <= b[3]:    return ("Muy exigente", 'warn', f"el payout de {_pct(p, 0)} consume casi todo el beneficio")
    return ("Insostenible", 'neg', f"el payout de {_pct(p, 0)} supera el beneficio: el dividendo actual no es sostenible")


def read_growth(g, what="los ingresos", kind="revenue"):
    if g is None: return None
    if growth_for_bands(g) < 0:   # entre −2% y 0: plano (estancamiento), no contracción
        return ("Contracción", 'neg', f"{what} se contraen un {_pct(abs(g))} interanual")
    b = cfg(f"thresholds.score.crecimiento.{kind}_bounds")   # las del score (ingresos o BPA)
    if g >= b[0]: return ("Acelerado", 'pos', f"{what} crecen {_pct(g)}, un ritmo acelerado propio de compañías growth")
    if g >= b[1]: return ("Sólido", 'pos', f"{what} crecen {_pct(g)}, un ritmo sólido")
    if g >= b[2]: return ("Moderado", 'neu', f"{what} crecen {_pct(g)}, un ritmo moderado")
    return ("Plano", 'warn', f"{what} están prácticamente planos ({_pct(g)})")


def read_upside(up):
    """Upside del DCF en %: las bandas del DCF en Valoración (thresholds.score.valoracion)."""
    if up is None: return None
    b = [x * 100 for x in cfg("thresholds.score.valoracion.dcf_upside_bounds")]
    if up >= b[0]:   return ("Muy infravalorada", 'pos', f"el modelo DCF sugiere un descuento sustancial: potencial teórico de +{up:.0f}% hasta el valor justo estimado")
    if up >= b[1]:   return ("Infravalorada", 'pos', f"el precio cotiza por debajo del valor intrínseco estimado (potencial teórico de +{up:.0f}%)")
    if up >= b[2]:   return ("Precio justo", 'neu', f"el precio cotiza en torno al valor justo estimado por el DCF ({'+' if up > 0 else ''}{up:.0f}%)")
    if up >= b[3]:   return ("Prima", 'warn', f"el precio incorpora una prima de {abs(up):.0f}% sobre el valor intrínseco estimado")
    return ("Sobrevalorada", 'neg', f"el precio excede en {abs(up):.0f}% el valor intrínseco estimado: el DCF exige asumir escenarios muy optimistas")


def read_graham(m):
    if m is None: return None
    if m >= _PDF_BANDS["graham_discount"]:  return ("Descuento Graham", 'pos', f"cotiza {_pct(m, 0)} por debajo del número de Graham, criterio clásico de valor")
    if m >= 0:     return ("Cerca de Graham", 'neu', f"cotiza cerca del número de Graham (margen de {_pct(m, 0)})")
    return ("Sobre Graham", 'warn',
            f"cotiza {_pct(abs(m), 0)} por encima del número de Graham — habitual en compañías de calidad/crecimiento, "
            "donde este criterio de 1949 resulta demasiado restrictivo")


def read_beta(b):
    if b is None: return None
    bb = _PDF_BANDS["beta_bounds"]
    if b < bb[0]:   return ("Defensiva", 'pos', f"con beta {b:.2f}, la acción amortigua los movimientos del mercado")
    if b < bb[1]:   return ("De mercado", 'neu', f"con beta {b:.2f}, la acción se mueve en línea con el mercado")
    if b < bb[2]:   return ("Volátil", 'warn', f"con beta {b:.2f}, la acción amplifica los movimientos del mercado")
    return ("Muy volátil", 'neg', f"con beta {b:.2f}, la acción es notablemente más volátil que el mercado")


def read_pos52(p):
    # Etapa 9a: solo POSICIÓN dentro del rango de 52 semanas, como contexto de
    # mercado. No dice si la acción está cara o barata (eso es el atractivo del
    # precio: múltiplos y DCF).
    if p is None: return None
    b = _PDF_BANDS["pos52_bounds"]
    if p < b[0]:   return ("En mínimos de 52 semanas", 'neu', f"cotiza en el {p:.0f}% del rango de 52 semanas, en la zona de mínimos")
    if p < b[1]:   return ("Parte baja del rango", 'neu', f"cotiza en el {p:.0f}% del rango de 52 semanas, en la parte baja")
    if p <= b[2]:  return ("Zona media del rango", 'neu', f"cotiza en el {p:.0f}% del rango de 52 semanas, en la zona media")
    if p < b[3]:   return ("Parte alta del rango", 'neu', f"cotiza en el {p:.0f}% del rango de 52 semanas, en la parte alta")
    return ("En máximos de 52 semanas", 'neu', f"cotiza en el {p:.0f}% del rango de 52 semanas, en la zona de máximos")


_QUALITY_TONE = {"excelente": 'pos', "sólida": 'pos', "media": 'warn', "débil": 'neg'}
_PRICE_TONE = {"atractivo": 'pos', "razonable": 'neu', "exigente": 'warn', "muy exigente": 'neg'}


def quality_tone(level):
    """Tono de un nivel de calidad (bandas de thresholds.score.quality, las del motor)."""
    return _QUALITY_TONE.get(level, 'neu')


def price_tone(level):
    """Tono de un nivel de precio (bandas de thresholds.score.price, sobre el contraído)."""
    return _PRICE_TONE.get(level, 'neu')


def read_buyback(by):
    if by is None: return None
    b = _PDF_BANDS["buyback_bounds"]
    if by >= b[0]:   return ("Recompra intensiva", 'pos', f"el programa de recompras retiró un {_pct(by)} de las acciones en el último año")
    if by >= b[1]:  return ("Recompra neta", 'pos', f"la compañía recompró un {_pct(by)} neto de sus acciones")
    if by > -b[1]:  return ("Neutra", 'neu', "el número de acciones se mantuvo estable")
    return ("Dilución", 'neg', f"la emisión de acciones diluyó a los accionistas un {_pct(abs(by))} en el año")


def read_fcf_yield(fy):
    if fy is None: return None
    if fy < 0:     return ("Negativo", 'neg', "la compañía quema caja libre a nivel operativo")
    b = _PDF_BANDS["fcf_yield_bounds"]
    if fy < b[0]:  return ("Bajo", 'warn', f"el FCF yield de {_pct(fy)} es bajo: se paga caro cada dólar de caja libre")
    if fy < b[1]:  return ("Razonable", 'neu', f"el FCF yield de {_pct(fy)} es razonable")
    if fy < b[2]:  return ("Atractivo", 'pos', f"el FCF yield de {_pct(fy)} es atractivo")
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


def build_report(buf, analysis, sector_bench, logo_path=None):
    S = _styles()

    # Benchmark de los múltiplos (main._select_benchmark): sector o mercado amplio.
    _vb = analysis.get("benchmark") or {}
    _mkt = _vb.get("profile") == "market"
    _ref = "del mercado (S&P 500)" if _mkt else "del sector"
    _bcol = "MERCADO" if _mkt else "SECTOR"

    def _rvs(*a, **k):
        return read_vs_sector(*a, ref=_ref, **k)

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
    # Etapa 6: el arquetipo del clasificador único decide qué se lee y qué no aplica.
    classification = analysis.get("classification") or {}
    archetype = classification.get("archetype") or "MATURE"
    not_app = analysis.get("not_applicable") or {}
    is_financial = archetype == "FINANCIAL"
    xm = analysis.get("archetype_metrics") or {}
    _na_keys = set((cfg(f"sectors.archetypes.not_applicable.{archetype}")
                    if archetype in ("FINANCIAL", "REIT", "GROWTH_PRE_PROFIT", "CYCLICAL", "MATURE") else ()))
    if archetype == "GROWTH_PRE_PROFIT" and xm.get("ebitda") is not None and xm["ebitda"] <= 0:
        _na_keys.add("ev_ebitda")   # EBITDA <= 0: EV/EBITDA no aplica (etapa 6)
    # Múltiplos propios de cada rama (filas del score de Valoración).
    _branch_metrics = ("P/B frente a ROE", "P/TBV frente a ROTE", "P/FFO (REIT)", "Rentabilidad por dividendo (REIT)",
                       "EV/Ventas", "Regla de 40", "EV/EBITDA normalizado vs Sector",
                       "EV/EBITDA normalizado vs mercado", "P/FCF normalizado")

    # posición en rango 52 semanas
    h52, l52 = km.get("price_52w_high"), km.get("price_52w_low")
    pos52 = None
    if h52 and l52 and price and (h52 - l52) > 0:
        pos52 = (price - l52) / (h52 - l52) * 100

    breakdown = score.get("breakdown") or {}
    # Etapa 9a: dos puntuaciones, nunca un total único. Calidad del negocio y
    # atractivo del precio (crudo y contraído por la confianza), con el veredicto.
    _q = analysis.get("quality") or {}
    _pa = analysis.get("price_attractiveness") or {}
    _vd = analysis.get("verdict") or {}
    q_score, q_level = _q.get("score"), _q.get("level")
    p_score, p_raw, p_level = _pa.get("score"), _pa.get("score_raw"), _pa.get("level")
    q_tone, p_tone = quality_tone(q_level), price_tone(p_level)
    _cover_notes = []                    # cobertura parcial de cualquiera de las dos
    if _q.get("basis"):
        _cover_notes.append(f"Calidad {_q['basis']}" + (f" ({', '.join(_q.get('excluded_categories') or [])} "
                                                      "no concluyente)" if _q.get("excluded_categories") else ""))
    if _q.get("low_coverage_categories"):
        _cover_notes.append("cobertura baja en " + ", ".join(_q["low_coverage_categories"]))
    if _pa.get("basis") or (p_score is None and breakdown):
        _cover_notes.append("Precio sin dato: Valoración no concluyente")
    _price_note = (f"crudo {p_raw} · contraído por confianza {_pa.get('confidence')} (×{_pa.get('factor')})"
                   if _pa.get("contracted") else None)

    n_red = len(alerts.get("red_flags") or [])
    n_warn = len(alerts.get("warnings") or [])
    n_str = len(alerts.get("strengths") or [])

    # ── lecturas adaptativas (se usan en resumen, secciones y tablas) ──
    # P/E <= 0 llega como None marcado "no significativo" (validate_outputs):
    # la lectura "Sin beneficios" se conserva a partir del flag de validación.
    _pe_flag = next((f for f in (analysis.get("data_validation") or [])
                     if f.get("field") == "key_metrics.pe"
                     and f.get("rule") == "multiplo_no_significativo"), None)
    _pe_in = km.get("pe") if km.get("pe") is not None or not _pe_flag else _pe_flag.get("old")
    r_pe = read_pe(_pe_in, sector_bench.get("pe"), km.get("roic_wacc_spread"), ref=_ref)
    # Bandas del score (ROE, D/E): las del sector o, con el perfil market, las del mercado.
    _th = SECTOR_THRESHOLDS.get(_vb.get("thresholds_key")
                                or (analysis.get("sector_info") or {}).get("mapped_sector") or "default",
                                ThresholdConfig())
    r_roe = read_roe(km.get("roe"), km.get("roa"), _th, market=_mkt)
    r_spread = read_spread(km.get("roic_wacc_spread"), km.get("roic"), km.get("wacc"))
    r_up = read_upside(dcf.get("upside"))
    # Etapa 8: fiabilidad del DCF. Con fiabilidad baja la lectura lo dice y el DCF
    # no puntúa; el texto del aviso es el mismo que el de Valoración.
    _rel = dcf.get("reliability") or {}
    DCF_NO_RECONCILE = ("El DCF no concilia con el precio bajo ningún supuesto razonable; "
                        "no se usa en el score")
    if r_up and _rel.get("level") == "baja":
        r_up = (r_up[0] + " (fiabilidad baja)", 'neu',
                r_up[2] + ". " + (DCF_NO_RECONCILE if _rel.get("grid_contains_price") is False
                                  else "DCF de fiabilidad baja: no se usa en el score"))
    _conf = analysis.get("confidence") or {}
    _wacc = analysis.get("wacc") or {}
    r_graham = read_graham(graham_margin)
    r_cr = None if "current_ratio" in _na_keys else read_current(km.get("current_ratio"))
    _rw = xm.get("runway") if archetype == "GROWTH_PRE_PROFIT" else None
    r_rw = read_runway(_rw)
    # D/E contable sin lectura en financieras (los depósitos son pasivo): decisión
    # de la etapa 4. La celda muestra "—" y DE_NOT_APPLICABLE.
    r_de = None if is_financial else read_de(km.get("de"), _th.debt_equity_high, km.get("interest_coverage"), market=_mkt)
    ic_state = km.get("interest_coverage_state")
    r_ic = read_coverage(km.get("interest_coverage"), ic_state)
    nde_state = km.get("net_debt_to_ebitda_state")
    r_nde = read_nde(km.get("net_debt_to_ebitda"), nde_state, km.get("net_debt"), reit=archetype == "REIT")
    r_pay = read_payout(km.get("payout_ratio"), km.get("payout_basis"))
    r_grev = read_growth(km.get("revenue_growth"), "los ingresos")
    r_gearn = read_growth(km.get("earnings_growth"), "los beneficios", "eps")
    r_beta = read_beta(km.get("beta"))
    r_52 = read_pos52(pos52)
    r_bb = read_buyback(km.get("buyback_yield"))
    r_fcfy = read_fcf_yield(km.get("fcf_yield"))
    # Etapa 9a: ningún texto (intro de sección, resumen, Graham) cita una métrica que no
    # aplica al arquetipo; el Número de Graham no se muestra donde el P/E no aplica.
    _graham_shown = graham is not None and not ({"graham", "pe"} & _na_keys)
    if "pe" in _na_keys:
        r_pe = None
    if "p_fcf" in _na_keys or archetype == "CYCLICAL":   # CYCLICAL: se lee el P/FCF normalizado, no el TTM
        r_fcfy = None
    if not _graham_shown:
        r_graham = None
    if "roe" in _na_keys:
        r_roe = None
    if "roic_wacc" in _na_keys:
        r_spread = None
    if "eps_growth" in _na_keys:
        r_gearn = None

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
    if classification.get("reason"):
        _cls_note = [classification["reason"]]
        if classification.get("ambiguous"):
            _cls_note.append("clasificación ambigua: confianza baja")
        _cls_note += [a.get("detail") for a in classification.get("alerts") or [] if a.get("detail")]
        _title_flow += [Spacer(1, 5), Paragraph(
            f"<font color='{BRAND_TXT.hexval()}'><b>{_esc(archetype)}</b></font>&nbsp;&nbsp;·&nbsp;&nbsp;"
            + _esc(" · ".join(_cls_note)),
            ParagraphStyle('ccls', fontName='Helvetica', fontSize=8.4, leading=11.5, textColor=BODY))]

    # Banda 2 — las DOS puntuaciones (izquierda) y sus componentes (derecha):
    # calidad = 4 categorías; precio = Valoración (múltiplos + DCF).
    _sl_w = 2.15 * inch
    _ctr = ParagraphStyle('slc', leading=8.6, alignment=TA_CENTER)

    def _score_block(kicker, sub, value, lvl, tone, note):
        rows = [[Paragraph(f"<font size='6.6' color='#77777f'><b>{kicker}</b></font><br/>"
                           f"<font size='6.6' color='#9a9aa0'>{sub}</font>", _ctr)],
                [Paragraph(f"<font size='34' color='{TONE_COLOR[tone].hexval()}'><b>"
                           f"{value if value is not None else '—'}</b></font>"
                           f"<font size='11' color='#a5a5ac'> /100</font>",
                           ParagraphStyle('heronum', fontName='Helvetica-Bold', leading=36, alignment=TA_CENTER))],
                [chip(lvl or "sin dato", tone, size=8.4)]]
        if note:
            rows.append([Paragraph(f"<font size='6.4' color='{AMBER.hexval()}'><b>{_esc(note)}</b></font>",
                                   ParagraphStyle('sln', leading=8.2, alignment=TA_CENTER, spaceBefore=3))])
        t = Table(rows, colWidths=[_sl_w])
        t.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                               ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                               ('TOPPADDING', (0, 0), (-1, -1), 1), ('BOTTOMPADDING', (0, 0), (-1, -1), 1)]))
        return t

    score_left = Table([
        [_score_block("CALIDAD DEL NEGOCIO", "¿es buena la empresa?", q_score, q_level, q_tone,
                      "baja confianza: " + "; ".join(_q.get("low_confidence_reasons") or [])
                      if _q.get("low_confidence") else None)],
        [Spacer(1, 10)],
        [_score_block("ATRACTIVO DEL PRECIO", "¿está cara hoy?", p_score, p_level, p_tone, _price_note)],
    ], colWidths=[_sl_w])
    score_left.setStyle(TableStyle([('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                                    ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0)]))
    _catw = CW - _sl_w - 42
    _barw = _catw - 1.55 * inch - 0.5 * inch
    _grp_st = ParagraphStyle('cgh', fontName='Helvetica-Bold', fontSize=6.6, leading=9, textColor=MUTED)
    _groups = [("CALIDAD DEL NEGOCIO", cfg("thresholds.score.quality.categories")),
               ("ATRACTIVO DEL PRECIO", cfg("thresholds.score.price.categories"))]
    cat_rows, _grp_idx = [], []
    for _gname, _gcats in _groups:
        _grp_idx.append(len(cat_rows))
        cat_rows.append([Paragraph(_gname, _grp_st), "", ""])
        for cat_name in _gcats:
            cat = breakdown.get(cat_name)
            if cat is None:
                continue
            cs, cm = cat.get("score", 0), cat.get("max", 20) or 20
            pctc = cs / cm * 100
            _t = 'pos' if pctc >= 60 else 'warn' if pctc >= 40 else 'neg'
            if cat.get("conclusive") is False:
                # Etapa 5: categoría no concluyente (cobertura < 50%), fuera de su puntuación.
                cat_rows.append([
                    Paragraph(_esc(cat_name), ParagraphStyle('cn', fontName='Helvetica', fontSize=8.6, leading=11, textColor=BODY)),
                    Paragraph(f"No concluyente · cobertura {(cat.get('coverage') or 0):.0%}",
                              ParagraphStyle('cnc', fontName='Helvetica', fontSize=7.6, leading=10, textColor=MUTED)),
                    Paragraph("<b>n/c</b>", ParagraphStyle('csc', fontName='Helvetica', fontSize=8.6, leading=11,
                                                           alignment=TA_RIGHT, textColor=MUTED)),
                ])
                continue
            cat_rows.append([
                Paragraph(_esc(cat_name), ParagraphStyle('cn', fontName='Helvetica', fontSize=8.6, leading=11, textColor=BODY)),
                hbar(pctc, width=_barw, height=6, fg=(BRAND if _t == 'pos' else AMBER if _t == 'warn' else RED)),
                Paragraph(f"<b>{cs}</b><font color='#a5a5ac'>/{cm}</font>",
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

    # Banda 2b — veredicto verbal + confianza (motivos) + cobertura parcial
    _conf0 = analysis.get("confidence") or {}
    _vrows = [[Paragraph(f"<font size='6.6' color='#77777f'><b>VEREDICTO</b></font>",
                         ParagraphStyle('vk', leading=9))],
              [Paragraph(_esc(_vd.get("text") or "Sin veredicto"),
                         ParagraphStyle('vt', fontName='Helvetica-Bold', fontSize=15, leading=19, textColor=INK))]]
    if _vd.get("confidence_text"):
        _vrows.append([Paragraph(_esc(_vd["confidence_text"]),
                                 ParagraphStyle('vc', fontName='Helvetica', fontSize=9.4, leading=12.5,
                                                textColor=TONE_COLOR[{'alta': 'pos', 'media': 'warn', 'baja': 'neg'}
                                                                     .get(_conf0.get('level'), 'neu')]))])
    _why = [r for r in (_conf0.get("reasons") or [])][:3]
    if _why:
        _vrows.append([Paragraph(_esc("Motivos de la confianza: " + " · ".join(_why)),
                                 ParagraphStyle('vr', fontName='Helvetica', fontSize=7.6, leading=10, textColor=BODY))])
    if _cover_notes:
        _vrows.append([Paragraph(_esc("Cobertura parcial: " + "; ".join(_cover_notes)),
                                 ParagraphStyle('vn', fontName='Helvetica', fontSize=7.6, leading=10, textColor=AMBER))])
    verdict_band = Table(_vrows, colWidths=[CW])
    verdict_band.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.white), ('BOX', (0, 0), (-1, -1), 0.5, HAIR),
        ('LINEBEFORE', (0, 0), (0, -1), 3, TONE_COLOR[q_tone]),
        ('LEFTPADDING', (0, 0), (-1, -1), 14), ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (0, 0), 9), ('TOPPADDING', (0, 1), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, -1), (-1, -1), 10),
    ]))

    # Banda 3 — KPIs (2 filas de 4 = 8 indicadores clave)
    _kw = (CW - 3 * 9) / 4.0
    # Etapa 6: los indicadores destacados son los primarios del arquetipo (un
    # banco nunca recibe P/E ni FCF como métrica primaria; un REIT, P/FFO…).
    _k_common = [(fv(price, "price"), "Precio"), (fv(km.get("market_cap"), "money"), "Market cap")]
    if archetype == "FINANCIAL":
        _k_arch = [(fv(xm.get("pb"), "mult"), "P/B"), (fv(km.get("roe"), "pct"), "ROE"),
                   (fv(km.get("net_margin"), "pct"), "Margen neto"), (fv(xm.get("ptbv"), "mult"), "P/TBV"),
                   (fv(km.get("dividend_yield"), "pct"), "Dividend yield"), (fv(km.get("beta"), "num"), "Beta")]
    elif archetype == "REIT":
        _k_arch = [(fv(km.get("p_ffo"), "mult"), "P/FFO"), (fv(km.get("dividend_yield"), "pct"), "Dividend yield"),
                   (fv(km.get("ffo_payout"), "pct"), "Payout sobre FFO"), (fv(km.get("de"), "mult"), "Deuda/Equity"),
                   (fv(km.get("net_debt_to_ebitda"), "mult"), "Deuda neta/EBITDA"), (fv(km.get("beta"), "num"), "Beta")]
    elif archetype == "GROWTH_PRE_PROFIT":
        _r40 = xm.get("rule_of_40")
        _k_arch = [(fv(xm.get("ev_sales"), "mult"), "EV/Ventas"),
                   (f"{_r40 * 100:.0f}" if _r40 is not None else "N/A", "Regla de 40"),
                   # Etapa 9a: el margen neto no aplica a pre-beneficio; el bruto sí.
                   (fv(km.get("gross_margin"), "pct"), "Margen bruto"), (fv(km.get("fcf_yield"), "pct"), "FCF yield"),
                   (fv(km.get("net_debt_to_ebitda"), "mult"), "Deuda neta/EBITDA"), (fv(km.get("beta"), "num"), "Beta")]
    elif archetype == "CYCLICAL":
        _k_arch = [(fv(xm.get("ev_ebitda_normalized"), "mult"), "EV/EBITDA normalizado"),
                   (fv(km.get("roe"), "pct"), "ROE"),
                   (fv(km.get("net_margin"), "pct"), "Margen neto"), (fv(km.get("fcf_yield"), "pct"), "FCF yield"),
                   (fv(km.get("net_debt_to_ebitda"), "mult"), "Deuda neta/EBITDA"), (fv(km.get("beta"), "num"), "Beta")]
    else:
        _k_arch = [(fv(km.get("pe"), "mult"), "P/E (TTM)"), (fv(km.get("roe"), "pct"), "ROE"),
                   (fv(km.get("net_margin"), "pct"), "Margen neto"), (fv(km.get("fcf_yield"), "pct"), "FCF yield"),
                   (fv(km.get("net_debt_to_ebitda"), "mult"), "Deuda neta/EBITDA"), (fv(km.get("beta"), "num"), "Beta")]
    _kpis = _k_common + _k_arch
    # Etapa 9a: la portada muestra las cifras REPORTADAS; si el score usa el beneficio
    # normalizado, lo dice la etiqueta (el normalizado va en el desglose, etiquetado).
    if (analysis.get("earnings_normalization") or {}).get("differs"):
        _rep = {"P/E (TTM)": "P/E reportado (TTM)", "ROE": "ROE reportado", "Margen neto": "Margen neto reportado"}
        _kpis = [(v, _rep.get(l, l)) for v, l in _kpis]

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

    # Banda 4 — "lo esencial" (fortaleza clave · a vigilar · valoración), desde señales
    _S = analysis.get("alerts", {}).get("strengths") or []
    _R = analysis.get("alerts", {}).get("red_flags") or []
    _W = analysis.get("alerts", {}).get("warnings") or []
    _hl_pos = _S[0]["reason"] if _S else "Fundamentos sólidos en la mayoría de categorías"
    _watch = _R[0] if _R else (_W[0] if _W else None)
    _hl_watch = _watch["reason"] if _watch else "Sin alertas relevantes"
    _hl_wtone = 'neg' if _R else ('warn' if _W else 'pos')
    # Tercera card = CONTEXTO (posición en el rango de 52 semanas, sin juicio de precio).
    if r_52:
        _hl_val, _hl_vtone = r_52[0], r_52[1]
    elif r_up:
        _hl_val, _hl_vtone = r_up[0], r_up[1]
    else:
        _hl_val, _hl_vtone = (r_pe[0], r_pe[1]) if r_pe else ("—", 'neu')
    _hlw = (CW - 2 * 9) / 3.0
    hl_row = Table([[
        _hl_card("FORTALEZA CLAVE", _hl_pos, 'pos', _hlw),
        _hl_card("A VIGILAR", _hl_watch, _hl_wtone, _hlw),
        _hl_card("CONTEXTO · 52 SEM." if r_52 else "PRECIO", _hl_val, _hl_vtone, _hlw),
    ]], colWidths=[CW / 3.0] * 3)
    hl_row.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (0, -1), 0), ('RIGHTPADDING', (-1, 0), (-1, -1), 0),
        ('LEFTPADDING', (1, 0), (-1, -1), 9), ('RIGHTPADDING', (0, 0), (-2, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))

    # Ensamblado de portada: las 4 bandas (título · panel de score · KPIs · "lo
    # esencial") separadas por GAPS VERTICALES IGUALES. El sobrante de altura se
    # reparte a partes iguales entre las 3 separaciones → distribución simétrica
    # y sin huecos desiguales, llenando la página. Las alturas naturales se miden
    # con .wrap() para que el reparto sea exacto por acción.
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
    for _i, _b in enumerate(_bands):
        story.append(_b)
        if _i < len(_bands) - 1:
            story.append(Spacer(1, _gap))
    story.append(PageBreak())

    # ════════════════ PÁGINA 2 — RESUMEN EJECUTIVO ════════════════
    story.extend(section_header("", "Resumen ejecutivo", S))
    story.append(Spacer(1, 3))

    # ── Grilla de metric-cards (valor + pill de estado + delta vs sector) ──
    _cellw = (CW - 8 * 2) / 3.0

    def _mvu(raw, fmt):
        if raw is None:
            return ("N/A", "")
        if fmt == 'pct':
            return (f"{raw * 100:.1f}", "%")
        if fmt == 'mult':
            return (f"{raw:.1f}", "x")
        return (fv(raw, 'money'), "")

    def _benchtxt(bench, fmt):
        if bench is None:
            return ""
        _vs = "vs mercado" if _mkt else "vs sector"
        return f"{_vs} {bench * 100:.1f}%" if fmt == 'pct' else f"{_vs} {bench:.1f}x"

    def _mkcard(label, raw, fmt, benchkey, higher):
        bench = sector_bench.get(benchkey) if benchkey else None
        r = _rvs(label, raw, bench, higher, 'pct' if fmt == 'pct' else 'mult') \
            if (bench and raw is not None) else None
        v, u = _mvu(raw, fmt)
        if r:
            pill, tone, _f, delta = r
            # etiqueta más corta para la pill (que no envuelva en la card)
            pill = {"Descuento profundo": "Gran descuento"}.get(pill, pill)
        else:
            pill, tone, delta = ("—" if raw is None else "En rango"), 'neu', ""
        return metric_card(label, v, u, pill, tone, delta, _benchtxt(bench, fmt), _cellw)

    # Etapa 6: la segunda fila son los múltiplos primarios del arquetipo.
    if archetype == "FINANCIAL":
        _val_cards = [_mkcard("P/B", xm.get("pb"), 'mult', "pb", False),
                      _mkcard("P/TBV", xm.get("ptbv"), 'mult', None, False),
                      _mkcard("Dividend yield", km.get("dividend_yield"), 'pct', None, True)]
    elif archetype == "REIT":
        _val_cards = [_mkcard("P/FFO", km.get("p_ffo"), 'mult', None, False),
                      _mkcard("Dividend yield", km.get("dividend_yield"), 'pct', None, True),
                      _mkcard("EV/EBITDA", km.get("ev_ebitda"), 'mult', "ev_ebitda", False)]
    elif archetype == "GROWTH_PRE_PROFIT":
        _val_cards = [_mkcard("EV/Ventas", xm.get("ev_sales"), 'mult', None, False),
                      _mkcard("FCF yield", km.get("fcf_yield"), 'pct', "fcf_yield", True),
                      _mkcard("Regla de 40", xm.get("rule_of_40"), 'pct', None, True)]
    elif archetype == "CYCLICAL":
        _val_cards = [_mkcard("EV/EBITDA normalizado", xm.get("ev_ebitda_normalized"), 'mult', "ev_ebitda", False),
                      _mkcard("FCF yield", km.get("fcf_yield"), 'pct', "fcf_yield", True),
                      _mkcard("P/FCF normalizado", xm.get("p_fcf_normalized"), 'mult', "pfcf", False)]
    else:
        _val_cards = [_mkcard("P/E (TTM)", km.get("pe"), 'mult', "pe", False),
                      _mkcard("FCF yield", km.get("fcf_yield"), 'pct', "fcf_yield", True),
                      _mkcard("EV/EBITDA", km.get("ev_ebitda"), 'mult', "ev_ebitda", False)]
    _cards = [
        _mkcard("Crecimiento ingresos", km.get("revenue_growth"), 'pct', "revenue_growth", True),
        _mkcard("Margen neto", km.get("net_margin"), 'pct', "net_margin", True),
        _mkcard("ROE", km.get("roe"), 'pct', "roe", True),
        *_val_cards,
    ]
    cg = Table([_cards[0:3], _cards[3:6]], colWidths=[CW / 3.0] * 3)
    cg.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (0, -1), 0), ('RIGHTPADDING', (-1, 0), (-1, -1), 0),
        ('LEFTPADDING', (1, 0), (-1, -1), 8), ('RIGHTPADDING', (0, 0), (-2, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 1), (-1, 1), 0),
    ]))

    # ── Radar por categoría + caja de "Lectura del análisis" ──
    def _cap(t):
        t = (t or "").strip().rstrip('.')
        return (t[0].upper() + t[1:] + ".") if t else ""

    if fin_health and isinstance(fin_health, dict) and fin_health.get("score") is not None:
        sol_short = (f"salud financiera bancaria de {fin_health['score']}/10 "
                     f"({fin_health.get('level', '')})")
    elif r_rw:
        sol_short = f"runway {r_rw[0].lower()}: {r_rw[2]}"
    elif altman.get("z_score") is not None and altman.get("available", True):
        _zmap = {'safe': 'zona segura', 'grey': 'zona gris', 'distress': 'zona de riesgo'}
        sol_short = f"Altman Z de {altman['z_score']:.2f} ({_zmap.get(altman.get('zone'), '')})"
        if r_ic:
            sol_short += f"; {r_ic[2]}"
    elif archetype == "REIT" and r_nde:
        sol_short = r_nde[2] + (f"; {r_ic[2]}" if r_ic else "")
    else:
        sol_short = r_de[2] if r_de else None

    # Etapa 9a: resumen ejecutivo construido alrededor del veredicto verbal:
    # VEREDICTO -> lo que sostiene la CALIDAD -> lo que explica el PRECIO -> CONFIANZA.
    exec_items = []
    _qcats = [(n, breakdown[n]) for n in cfg("thresholds.score.quality.categories")
              if n in breakdown and breakdown[n].get("conclusive", True) and breakdown[n].get("applicable", True)]
    _qcats.sort(key=lambda kv: kv[1].get("score", 0), reverse=True)
    _best = [f"{n} ({c['score']}/{c.get('max', 20)})" for n, c in _qcats[:2] if c.get("score", 0) >= 13]
    _weak = [f"{n} ({c['score']}/{c.get('max', 20)})" for n, c in _qcats[-1:] if c.get("score", 0) < 10]
    _vtxt = _vd.get("full") or _vd.get("text") or ""
    if _vtxt:
        exec_items.append(("VEREDICTO", _esc(
            f"{_vtxt}. Calidad {q_score if q_score is not None else '—'}/100 · precio "
            f"{p_score if p_score is not None else '—'}/100"
            + (f" (crudo {p_raw}, contraído hacia 50 por la confianza)" if _pa.get("contracted") else "") + ".")))
    _qtxt = []
    if _best:
        _qtxt.append("Destaca en " + " y ".join(_best))
    if _weak:
        _qtxt.append("el punto débil es " + _weak[0])
    if _qtxt:
        exec_items.append(("CALIDAD DEL NEGOCIO", _esc(_cap("; ".join(_qtxt)))))
    if not is_financial and r_spread:
        exec_items.append(("CREACIÓN DE VALOR", _esc(_cap(r_spread[2]))))
    elif r_roe:
        exec_items.append(("RENTABILIDAD", _esc(_cap(r_roe[2]))))
    else:   # REIT / pre-beneficio: los componentes de su rama (FFO, márgenes de su fase)
        _rb = [a for a in (breakdown.get("Rentabilidad") or {}).get("adjustments") or []
               if a.get("metric") not in ("No aplica", "Cobertura")]
        if _rb:
            exec_items.append(("RENTABILIDAD", _esc(_cap("; ".join(f"{a['metric']} {a['value']}: "
                                                                  f"{a['reason'].split(' - ')[0].lower()}"
                                                                  for a in _rb[:2])))))
    if sol_short:
        exec_items.append(("SOLIDEZ", _esc(_cap(sol_short))))
    _gro = " ".join(filter(None, [_cap(r_grev[2]) if r_grev else None, _cap(r_bb[2]) if r_bb else None]))
    if _gro.strip():
        exec_items.append(("CRECIMIENTO Y RETORNO", _esc(_gro)))
    # Precio: la lectura del múltiplo primario del arquetipo y la del DCF
    _r_val = r_pe if "pe" not in _na_keys else None
    _branch_val = next((a for a in (breakdown.get("Valoración") or {}).get("adjustments") or []
                        if a.get("metric") in _branch_metrics), None)
    if _r_val is None and _branch_val:
        _r_val = (None, None, f"{_branch_val['metric'].replace(' vs Sector', '').replace(' vs mercado', '')}: {_branch_val['reason']}")
    _val = (_cap(_r_val[2]) + (" " + _cap(r_up[2]) if r_up else "")) if _r_val else (_cap(r_up[2]) if r_up else "")
    if _val.strip():
        exec_items.append(("ATRACTIVO DEL PRECIO", _esc(_val)))
    _ctx = " ".join(filter(None, [_cap(r_52[2]) if r_52 else None, _cap(r_beta[2]) if r_beta else None]))
    if _ctx.strip():
        exec_items.append(("CONTEXTO DE MERCADO", _esc(_ctx)))
    if _conf.get("level"):
        exec_items.append(("CONFIANZA DEL VEREDICTO", _esc(
            f"{_conf['level'].capitalize()}"
            + (f": {_conf['reasons'][0]}" if _conf.get("reasons") else ": los métodos y los datos coinciden")
            + ". Contrae el atractivo del precio hacia 50; la calidad no se contrae.")))

    # ── Composición de las dos puntuaciones (etapa 9a: sustituye al radar de 5 ejes,
    # que mezclaba calidad y precio en un solo perfil). Izquierda: calidad y sus 4
    # categorías; derecha: precio y los componentes de Valoración (múltiplos y DCF).
    _bal_line = (f"<font color='{BRAND_TXT.hexval()}'><b>{n_str}</b> fortaleza{'s' if n_str != 1 else ''}</font>"
                 f"&nbsp;&nbsp;·&nbsp;&nbsp;<font color='{AMBER.hexval()}'><b>{n_warn}</b> advertencia{'s' if n_warn != 1 else ''}</font>"
                 f"&nbsp;&nbsp;·&nbsp;&nbsp;<font color='{RED.hexval()}'><b>{n_red}</b> riesgo{'s' if n_red != 1 else ''}</font>")
    _halfw = (CW - 24 - 18) / 2.0
    _lab_st = ParagraphStyle('cpl', fontName='Helvetica', fontSize=8.2, leading=10.5, textColor=BODY)
    _num_st = ParagraphStyle('cpn', fontName='Helvetica-Bold', fontSize=8.2, leading=10.5, alignment=TA_RIGHT)

    def _head(title, value, lvl, tone, extra=None):
        return [Paragraph(f"<font size='6.8' color='#77777f'><b>{title}</b></font><br/>"
                          f"<font size='17' color='{TONE_COLOR[tone].hexval()}'><b>"
                          f"{value if value is not None else '—'}</b></font><font size='9' color='#a5a5ac'>/100</font>"
                          f"&nbsp;&nbsp;<font size='8.4' color='{TONE_COLOR[tone].hexval()}'><b>{_esc(lvl or 'sin dato')}</b></font>"
                          + (f"<br/><font size='6.8' color='{AMBER.hexval()}'>{_esc(extra)}</font>" if extra else ""),
                          ParagraphStyle('cph', leading=13)), "", ""]

    def _bar_row(label, value, mx, signed=False):
        if signed:   # componente de Valoración: ajuste ± sobre la base 10/20
            col = BRAND if value > 0 else RED if value < 0 else MUTED
            return [Paragraph(_esc(label), _lab_st), hbar(min(100, abs(value) / 6 * 100), width=_halfw - 1.9 * inch,
                                                         height=5, fg=col),
                    Paragraph(f"<font color='{col.hexval()}'>{value:+d}</font>", _num_st)]
        pct_ = value / (mx or 20) * 100
        col = BRAND if pct_ >= 60 else AMBER if pct_ >= 40 else RED
        return [Paragraph(_esc(label), _lab_st), hbar(pct_, width=_halfw - 1.9 * inch, height=5, fg=col),
                Paragraph(f"{value}<font color='#a5a5ac'>/{mx}</font>", _num_st)]

    _qrows = [_head("CALIDAD DEL NEGOCIO", q_score, q_level, q_tone,
                    _q.get("basis") or ("baja confianza por cobertura" if _q.get("low_confidence") else None))]
    for n in cfg("thresholds.score.quality.categories"):
        c = breakdown.get(n)
        if c is None:
            continue
        if c.get("conclusive") is False:
            _qrows.append([Paragraph(_esc(n), _lab_st), Paragraph("no concluyente", _lab_st), Paragraph("n/c", _num_st)])
        else:
            _qrows.append(_bar_row(n, c.get("score", 0), c.get("max", 20)))
    _prows = [_head("ATRACTIVO DEL PRECIO", p_score, p_level, p_tone, _price_note)]
    for adj in (breakdown.get("Valoración") or {}).get("adjustments") or []:
        if adj.get("metric") in ("No aplica", "Cobertura") or not isinstance(adj.get("adjustment"), int) \
                or adj.get("in_block"):     # los miembros del bloque puntúan a través del bloque
            continue
        _prows.append(_bar_row(f"{adj['metric'].replace(' vs Sector', '').replace(' vs mercado', '')} · {adj.get('value', '')}",
                               adj["adjustment"], None, signed=True))

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
        [Paragraph("<font size='7.4' color='#9a9aa0'>Calidad: categorías 0–20 reescaladas a 100. Precio: Valoración "
                   "(base 10/20 + bloque de múltiplos y DCF) reescalada a 100 y contraída hacia 50 según la "
                   f"confianza.</font><br/><font size='8.5'>{_bal_line}</font>",
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
            f"<font size='6.6' color='{BRAND_TXT.hexval()}'><b>{_esc(label)}</b></font><br/>{text}", _exc_st)
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

    # ════════════════ PÁGINA 2 — VALORACIÓN ════════════════
    story.append(PageBreak())
    story.extend(section_header("01", "Valoración", S))
    val_txt = _join_sentences([
        r_pe[2] if r_pe else None,
        r_fcfy[2] if r_fcfy else None,
        r_graham[2] if r_graham else None,
    ])
    if not val_txt:   # la rama del arquetipo (P/B justificado, P/FFO, normalizados…)
        _bv = [a for a in (breakdown.get("Valoración") or {}).get("adjustments") or []
               if a.get("metric") in _branch_metrics]
        val_txt = _join_sentences([f"{a['metric'].replace(' vs Sector', '').replace(' vs mercado', '')}: "
                                   f"{a['reason'][0].lower()}{a['reason'][1:]}" for a in _bv[:2]])
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
        ("Earnings Yield (E/P)", km.get("earnings_yield"), None, True, "pct"),
        ("Dividend Yield", km.get("dividend_yield"), None, True, "pct"),
    ]
    # Etapa 6: lo que no aplica al arquetipo no se lee ("No aplica"), y la rama
    # añade sus múltiplos (P/B justificado, P/FFO, EV/Ventas, normalizados…).
    _mult_na = {"P/E (TTM)": "pe", "Earnings Yield (E/P)": "pe", "Forward P/E": "forward_pe", "PEG": "peg",
                "EV/EBITDA": "ev_ebitda",
                "P/FCF": "p_fcf", "FCF Yield": "p_fcf"}
    rows, reads = [], []
    norm = analysis.get("earnings_normalization") or {}
    for i, (lab, val, bench, hb, fm) in enumerate(mult_defs):
        if lab == "P/E (TTM)" and norm.get("pe_unreliable") and _mult_na.get(lab) not in _na_keys:
            # Etapa 7: con no recurrentes > umbral el P/E reportado no es fiable.
            rows.append([lab, fv(val, fm), fv(bench, fm) if bench else "—", "—",
                         f"No fiable ({norm['one_off_pct'] * 100:.0f}% no recurrente)"])
            reads.append((i, 'warn'))
            continue
        if _mult_na.get(lab) in _na_keys:
            rows.append([lab, fv(val, fm), fv(bench, fm) if bench else "—", "—", f"No aplica a {archetype}"])
            reads.append((i, 'neu'))
            continue
        r = _rvs(lab, val, bench, hb, fm) if bench else None
        rows.append([lab, fv(val, fm), fv(bench, fm) if bench else "—",
                     r[3] if r else "—", r[0] if r else "—"])
        if r:
            reads.append((i, r[1]))
    _sev_read = {"excellent": ("Favorable", 'pos'), "good": ("Favorable", 'pos'), "ok": ("En línea", 'neu'),
                 "moderate": ("Exigente", 'warn'), "severe": ("Desfavorable", 'neg')}
    for adj in (breakdown.get("Valoración") or {}).get("adjustments") or []:
        if adj.get("metric") in _branch_metrics:
            lab_r, tone_r = _sev_read.get(adj.get("severity"), ("—", 'neu'))
            rows.append([adj["metric"].replace(" vs Sector", "").replace(" vs mercado", ""), str(adj.get("value", "")),
                         "—", "—", lab_r])
            reads.append((len(rows) - 1, tone_r))
    if norm.get("pe_unreliable") and norm.get("pe_normalized") is not None and "pe" not in _na_keys:
        rows.append(["P/E normalizado", fv(norm["pe_normalized"], "mult"), "—", "—", "Sin no recurrentes"])
    story.append(data_table(
        ["MÚLTIPLO", "EMPRESA", _bcol, "BRECHA", "LECTURA"], rows,
        [1.9 * inch, 1.15 * inch, 1.15 * inch, 1.0 * inch, CW - 5.2 * inch],
        aligns=['LEFT', 'RIGHT', 'RIGHT', 'RIGHT', 'RIGHT'], reads=reads))
    if _mkt:
        _src = "; ".join(f"{k.replace('_', '/').upper()}: {v}" for k, v in (_vb.get("sources") or {}).items())
        story.append(Paragraph(_esc(
            f"Referencia: medianas y umbrales del mercado amplio (S&P 500), no los del sector "
            f"({_vb.get('reason')}). PROVISIONALES. Fuentes: {_src}. El resto de referencias de la columna "
            "MERCADO (Forward P/E, P/B, PEG, P/FCF, FCF yield, rentabilidad y márgenes) son la referencia general "
            "PROVISIONAL, fijada a mano y sin fuente, no medianas del S&P 500."), S['small']))
    # Etapa 7: beneficio normalizado (una línea cuando hay partidas no recurrentes aplicadas).
    if norm.get("applied") and norm.get("normalized_net_income") is not None and norm.get("differs", True):
        def _it_txt(it):
            lab = f"{it.get('label') or it['type']} ({it['type']}, confianza {it['confidence']})"
            if it.get("recurrent"):
                per = (f"{it.get('recurrent_years')} trimestres" if it["type"] == "inferida" else
                       f"{it.get('recurrent_years')} de los últimos {it.get('recurrence_window')} ejercicios")
                lab += (f", recurrente ({per}): "
                        + (f"solo el exceso sobre su promedio, {fv(it['net'], 'money')} netos" if it.get("net")
                           else "sin exceso sobre su promedio, no se ajusta"))
            else:
                lab += f": {fv(it['net'], 'money')} netos"
            return lab + ("" if it.get("applied") else ", bajo el umbral, no aplicada")
        _its = "; ".join(_it_txt(it) for it in norm.get("items") or [])
        _line = (f"Beneficio {norm.get('basis')}: reportado {fv(norm.get('reported_net_income'), 'money')}, "
                 f"normalizado {fv(norm.get('normalized_net_income'), 'money')} "
                 f"(no recurrentes {norm['one_off_pct'] * 100:.1f}% del beneficio; {_its}). "
                 + ("El score usa el beneficio normalizado." if norm.get("used_in_score") else ""))
        if norm.get("pe_unreliable") and norm.get("pe_normalized") is not None and "pe" not in _na_keys:
            _line += (f" P/E reportado {fv(norm.get('pe_reported'), 'mult')} no fiable; "
                      f"P/E normalizado {fv(norm['pe_normalized'], 'mult')}.")
        story.append(Spacer(1, 4))
        story.append(Paragraph(_esc(_line), S['small']))
    story.append(Spacer(1, 12))

    # Valor intrínseco
    story.append(Paragraph("Valor intrínseco", S['h2']))
    iv_txt = _join_sentences([r_up[2] if r_up else None,
                              (f"DCF (FCFF): {not_app['dcf'][0].lower()}{not_app['dcf'][1:]}" if not_app.get("dcf")
                               else None if r_up else "el modelo DCF no es aplicable con los datos disponibles"),
                              ("se valora sobre libros y retornos" if is_financial else None)])
    if iv_txt:
        story.append(Paragraph(iv_txt, S['body']))
    iv_rows = [["Precio de mercado", fv(price, "price"), ""]]
    if not_app.get("dcf"):
        iv_rows.append(["Valor justo DCF", "—", f"No aplica a {archetype}"])
    if _graham_shown:
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
    if _graham_shown:
        story.append(Paragraph(_esc(
            "Número de Graham: referencia del inversor defensivo (P/E 15 × P/B 1.5). Se muestra como referencia "
            "y no vota en la convergencia entre métodos."), S['small']))

    if dcf.get("fair_value") is not None:
        story.append(Spacer(1, 6))
        params = (f"Parámetros del modelo — WACC {fv(dcf.get('wacc'), 'pct')} · "
                  f"crecimiento {fv(dcf.get('growth_rate'), 'pct')} · "
                  f"terminal {fv(dcf.get('terminal_growth'), 'pct')}")
        vc = dcf.get("value_composition") or {}
        if vc.get("terminal_pct") is not None:
            params += f" · el valor terminal aporta el {vc['terminal_pct']:.0f}% del valor total"
        _nz = dcf.get("normalized") or {}
        if _nz.get("fcf_maintenance") is not None:
            params += (f" · FCF de mantenimiento {fv(_nz['fcf_maintenance'], 'money')} (flujo operativo − D&A como "
                       f"capex de mantenimiento, promedio de {_nz.get('fcf_maintenance_years')} ejercicios), frente al "
                       f"FCF normalizado {fv(_nz.get('fcf'), 'money')} (margen FCF promedio "
                       f"{fv(_nz.get('fcf_margin_avg'), 'pct')} × ingresos actuales, que incluye el capex de expansión"
                       + (f"; ciclo incompleto: {_nz.get('years')} ejercicios" if _nz.get("cycle_incomplete") else "")
                       + "): el DCF usa el de mantenimiento, con crecimiento normalizado de ciclo medio")
        story.append(Paragraph(_esc(params), S['small']))
        # Fiabilidad del DCF y su aporte a Valoración (etapa 8)
        _dcf_adj = next((a for a in (breakdown.get("Valoración") or {}).get("adjustments") or []
                         if a.get("metric") == "DCF (upside)"), None)
        if _rel.get("level"):
            _rl = f"Fiabilidad del DCF: {_rel['level']}"
            if _rel.get("reasons"):
                _rl += " (" + "; ".join(_rel["reasons"]) + ")"
            if _rel["level"] == "baja":
                _rl += ". " + (DCF_NO_RECONCILE if _rel.get("grid_contains_price") is False
                               else "DCF de fiabilidad baja: no se usa en el score") + "."
            elif _dcf_adj is not None:
                _cap_pts = (cfg("thresholds.score.valoracion.dcf_points_high") if _rel["level"] == "alta"
                            else cfg("thresholds.score.valoracion.dcf_points_medium"))[0]
                _rl += (f". Aporta {_dcf_adj['adjustment']:+d} puntos a Valoración "
                        f"(máximo ±{_cap_pts} con fiabilidad {_rel['level']}).")
            story.append(Spacer(1, 3))
            story.append(Paragraph(_esc(_rl), S['small']))
    elif dcf.get("reason"):
        story.append(Spacer(1, 6))
        story.append(Paragraph(_esc(f"DCF sin dato: {dcf['reason']}."), S['small']))
    # FINANCIAL (etapa 8): sin WACC; el P/B justificado usa Ke con la beta ajustada.
    if is_financial and xm.get("cost_of_equity") is not None:
        story.append(Spacer(1, 3))
        story.append(Paragraph(_esc(
            f"Ke {fv(xm['cost_of_equity'], 'pct')} = Rf {fv((analysis.get('risk_free') or {}).get('value'), 'pct')} + "
            f"β ajustada {xm.get('beta_adjusted', 0):.2f} (bruta {xm.get('beta_raw', 0):.2f}, Blume) × prima implícita "
            f"{fv(cfg('valuation.capm.market_risk_premium'), 'pct')}. FINANCIAL no usa WACC: se valora por P/B "
            "justificado con Ke."), S['small']))
    # WACC usado (etapa 8): el mismo en DCF, grid y spread ROIC−WACC.
    if _wacc.get("value") is not None:
        _w = _wacc
        _wl = (f"WACC {fv(_w['value'], 'pct')}"
               + (f" (acotado desde {fv(_w.get('raw'), 'pct')} al rango "
                  f"{fv(_w['bounds'][0], 'pct')}–{fv(_w['bounds'][1], 'pct')})" if _w.get("clamped") else "")
               + f" = {fv((_w.get('weights') or {}).get('equity'), 'pct')} × Ke {fv(_w.get('ke'), 'pct')} "
               f"(Rf {fv(_w.get('rf'), 'pct')} + β ajustada {_w.get('beta', 0):.2f} [bruta {_w.get('beta_raw', 0):.2f}, "
               f"Blume] × prima implícita {fv(_w.get('mrp'), 'pct')})")
        _rt = _w.get("rating") or {}
        if _w.get("kd") is not None:
            _wl += (f" + {fv((_w.get('weights') or {}).get('debt'), 'pct')} × Kd {fv(_w['kd'], 'pct')} × "
                    f"(1 − t {fv(_w.get('tax_rate'), 'pct')}). Kd = Rf + spread del rating sintético "
                    f"{_rt.get('rating')} (tabla de empresas {_rt.get('table')}"
                    + (f", cobertura {_rt['coverage']:.1f}x" if _rt.get("coverage") is not None and not _rt.get("flag") else "")
                    + ")" + (f"; {_rt['flag']}" if _rt.get("flag") else ""))
        else:
            _wl += " (sin deuda financiera: WACC = Ke)"
        _tx = analysis.get("tax_rate") or {}
        _wl += (f". t: {'tasa efectiva ' + str(_tx.get('period') or '') if _tx.get('source') == 'efectiva' else 'tipo legal'}"
                + (f" ({_tx['reason']})" if _tx.get("reason") else ""))
        if _w.get("rf_fallback"):
            _wl += f". Rf: {_w.get('rf_reason')}"
        elif _w.get("rf_source"):
            _wl += f". Rf: {_w['rf_source']} a {_w.get('rf_as_of')}"
        story.append(Spacer(1, 3))
        story.append(Paragraph(_esc(_wl + "."), S['small']))

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
                    gb = _PDF_BANDS["grid_color_bounds"]
                    if diff > gb[0]:    bg = colors.HexColor('#d9f3e6')
                    elif diff > gb[1]:  bg = colors.HexColor('#ecf9f2')
                    elif diff > -gb[1]: bg = colors.HexColor('#f6f6f4')
                    elif diff > -gb[0]: bg = colors.HexColor('#f9edea')
                    else:            bg = colors.HexColor('#f4dfdb')
                    cmds.append(('BACKGROUND', (di + 1, gi + 1), (di + 1, gi + 1), bg))
        if base_gi is not None and base_di is not None:
            cmds.append(('BOX', (base_di + 1, base_gi + 1), (base_di + 1, base_gi + 1), 1.4, BRAND))
        st.setStyle(TableStyle(cmds))
        story.append(st)
        if price:
            _trim = (sensitivity.get("trimmed") or {}).get("note")
            story.append(Paragraph(
                _esc(f"Precio actual: ${price:,.2f}. El recuadro verde marca el escenario base del modelo."
                     + (f" Grid asimétrico: {_trim}." if _trim else "")),
                S['small']))

    # Confianza del veredicto (etapa 8): se calcula y se muestra; no limita el score.
    if _conf.get("level"):
        story.append(Spacer(1, 8))
        story.append(Paragraph("Confianza del veredicto", S['h2']))
        _labels = {"convergence": "Convergencia entre métodos", "coverage": "Cobertura de datos",
                   "source": "Calidad de fuente", "stability": "Estabilidad del arquetipo"}
        _crows = []
        for _k, _dd in (_conf.get("dimensions") or {}).items():
            _txt = "; ".join(_dd.get("reasons") or []) or "sin incidencias"
            if _k == "convergence" and _dd.get("methods"):
                _txt = " · ".join(
                    f"{m['method']} {('%+.0f%%' % (m['upside'] * 100)) if m.get('upside') is not None else ('%+.2f' % m['signal'])}"
                    f" ({m.get('direction')}{'' if m.get('evaluable', True) else ', no evaluable'})"
                    for m in _dd["methods"] if m.get("signal") is not None) + ". " + _txt
            _crows.append([_labels.get(_k, _k), _dd["level"].replace("_", " ").capitalize(),
                           Paragraph(_esc(_txt), S['small'])])
        story.append(data_table(["DIMENSIÓN", "NIVEL", "MOTIVO"], _crows,
                                [1.9 * inch, 0.8 * inch, CW - 2.7 * inch], aligns=['LEFT', 'CENTER', 'LEFT']))
        story.append(Paragraph(_esc(
            f"Confianza del veredicto: {_conf['level']}"
            + (f" (techo en {_conf['level']} sin contraste entre métodos; sin techo sería {_conf['capped_from']})"
               if _conf.get("capped_from") else "")
            + (f". Contrae el atractivo del precio hacia 50 (factor {_pa.get('factor')}): crudo {p_raw}, mostrado "
               f"{p_score}" if _pa.get("factor") is not None else "")
            + ". La calidad del negocio no se contrae."), S['small']))

    # ════════════════ PÁGINA 3 — RENTABILIDAD + SOLIDEZ ════════════════
    story.append(PageBreak())
    story.extend(section_header("02", "Rentabilidad y eficiencia", S))
    rent_txt = _join_sentences([
        r_roe[2] if r_roe else None,
        (r_spread[2] if (r_spread and not is_financial) else None),
    ])
    if not rent_txt and archetype in ("REIT", "GROWTH_PRE_PROFIT"):
        _rb = [a for a in (breakdown.get("Rentabilidad") or {}).get("adjustments") or []
               if a.get("metric") not in ("No aplica", "Cobertura")]
        rent_txt = _join_sentences([f"{a['metric']} de {a['value']}: {a['reason'].split(' - ')[0].lower()}"
                                    for a in _rb])
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
    _ret_na = {"ROE": "roe", "ROA": "roa", "ROIC": "roic_wacc", "Margen bruto": "gross_margin",
               "Margen operativo": "operating_margin", "Margen neto": "net_margin"}
    for i, (lab, val, bench, hb, fm) in enumerate(ret_defs):
        if _ret_na.get(lab) in _na_keys:
            # Etapa 9a: lo que no aplica al arquetipo no se lee.
            rows.append([lab, fv(val, fm), "—", "—", f"No aplica a {archetype}"])
            reads.append((len(rows) - 1, 'neu'))
            continue
        if lab == "ROIC" and val is None and km.get("roic_reason"):
            rows.append([lab, "—", "—", "—", "No significativo"])
            reads.append((len(rows) - 1, 'neu'))
            continue
        r = _rvs(lab, val, bench, hb, fm) if bench else None
        rows.append([lab, fv(val, fm), fv(bench, fm) if bench else "—",
                     r[3] if r else "—", r[0] if r else "—"])
        if r:
            reads.append((i, r[1]))
    if not is_financial and km.get("roic_wacc_spread") is not None and r_spread:
        rows.append(["Spread ROIC − WACC", f"{km['roic_wacc_spread'] * 100:+.1f} pp", "> 0", "—", r_spread[0]])
        reads.append((len(rows) - 1, r_spread[1]))
    # Etapa 9a: métricas de rentabilidad de la rama (REIT: FFO; pre-beneficio: márgenes de su fase).
    _sev_tone = {"excellent": 'pos', "good": 'pos', "ok": 'neu', "moderate": 'warn', "severe": 'neg'}
    _sev_lab = {"excellent": "Excelente", "good": "Favorable", "ok": "En línea", "moderate": "Débil", "severe": "Muy débil"}
    for a in (breakdown.get("Rentabilidad") or {}).get("adjustments") or []:
        if archetype in ("REIT", "GROWTH_PRE_PROFIT") and a.get("metric") not in ("No aplica", "Cobertura", "Margen bruto"):
            rows.append([a["metric"], str(a.get("value", "")), "—", "—", _sev_lab.get(a.get("severity"), "—")])
            reads.append((len(rows) - 1, _sev_tone.get(a.get("severity"), 'neu')))
    # ROCE (etapa 6): solo MATURE y CYCLICAL; "No aplica" o "Sin dato", nunca 0%.
    _roce_state = km.get("roce_state")
    if _roce_state == "no_aplica":
        rows.append(["ROCE", "—", "—", "—", f"No aplica a {archetype}"])
        reads.append((len(rows) - 1, 'neu'))
    elif _roce_state == "sin_dato":
        rows.append(["ROCE", "—", "—", "—", "Sin dato"])
        reads.append((len(rows) - 1, 'neu'))
    elif _roce_state == "ok":
        rows.append(["ROCE (EBIT / capital empleado)", fv(km.get("roce"), "pct"), "—", "—", "Antes de impuestos"])
        if km.get("roce_avg") is not None:
            rows.append([f"ROCE promedio ({km.get('roce_years')} ejercicios"
                         + (", ciclo incompleto)" if km.get("roce_cycle_incomplete") else ")"),
                         fv(km.get("roce_avg"), "pct"), "—", "—", "Ciclo medio"])
    story.append(data_table(
        ["MÉTRICA", "EMPRESA", _bcol, "BRECHA", "LECTURA"], rows,
        [1.9 * inch, 1.15 * inch, 1.15 * inch, 1.0 * inch, CW - 5.2 * inch],
        aligns=['LEFT', 'RIGHT', 'RIGHT', 'RIGHT', 'RIGHT'], reads=reads))
    _div = km.get("roce_roic_divergence") or {}
    if _div.get("diverges"):
        story.append(Spacer(1, 4))
        story.append(Paragraph(_esc(
            f"Divergencia ROCE–ROIC: ROCE {fv(km.get('roce'), 'pct')} frente a ROIC {fv(km.get('roic'), 'pct')} "
            f"({_div['gap'] * 100:+.1f} pp, más de {cfg('thresholds.roce.divergence_pp') * 100:.0f} pp). "
            "Causas probables: " + "; ".join(_div.get("causes") or []) + "."), S['small']))

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
        r_rw[2] if r_rw else None,
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
        *([("Runway", None, "runway", r_rw)] if archetype == "GROWTH_PRE_PROFIT" else []),
        ("Current ratio", km.get("current_ratio"), "mult", r_cr),
        ("Quick ratio", km.get("quick_ratio"), "mult", None),
        ("Cash ratio", km.get("cash_ratio"), "mult", None),
        ("Deuda / Equity", km.get("de"), "mult", r_de),
        ("Deuda / Activos", km.get("debt_to_assets"), "pct", None),
        ("Deuda neta / EBITDA", km.get("net_debt_to_ebitda"), "mult", r_nde),
        ("Cobertura de intereses", km.get("interest_coverage"), "mult", r_ic),
        ("Payout sobre FFO" if km.get("payout_basis") == "ffo" else "Payout del dividendo",
         km.get("payout_ratio"), "pct", r_pay),
    ]
    rows, reads = [], []
    for lab, val, fm, rd in sol_defs:
        if (lab == "Cobertura de intereses" and ic_state == "no_significativo") or \
                (lab == "Deuda neta / EBITDA" and nde_state == "no_significativo"):
            rows.append([lab, "—", rd[0]])
            reads.append((len(rows) - 1, rd[1]))
            continue
        if fm == "runway":
            if r_rw:
                rows.append([lab, "Autofinanciada" if _rw["state"] == "autofinanciada" else f"{_rw['years']:.1f} años",
                             r_rw[0]])
                reads.append((len(rows) - 1, r_rw[1]))
            else:
                rows.append([lab, "—", "Sin dato"])
            continue
        if lab == "Current ratio" and "current_ratio" in _na_keys:
            rows.append([lab, "—", "No aplica"])     # REIT (etapa 7); FINANCIAL tiene su propia sección
            continue
        if val is None:
            continue
        i = len(rows)
        if is_financial and lab == "Deuda / Equity":
            rows.append([lab, "—", DE_NOT_APPLICABLE])
            continue
        if lab == "Cobertura de intereses" and ic_state == "negativa":
            rows.append([lab, IC_NEGATIVE, rd[0]])
            reads.append((i, rd[1]))
            continue
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
        ("Crecimiento de beneficios (YoY)", None if "eps_growth" in _na_keys else km.get("earnings_growth"), "pct",
         r_gearn),
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
    # Etapa 9a: BPA frente a ingresos, informativo (no puntúa: Crecimiento ya puntúa ambos).
    _evr = analysis.get("eps_vs_revenue_growth")
    if _evr:
        reads.append((len(rows), {"expansion": 'pos', "compresion": 'warn'}.get(_evr["state"], 'neu')))
        rows.append(["BPA frente a ingresos (informativo)", f"{_evr['gap'] * 100:+.1f} pp", _evr["label"]])
    if rows:
        story.append(data_table(["MÉTRICA", "VALOR", "LECTURA"], rows,
                                [3.2 * inch, 1.6 * inch, CW - 4.8 * inch],
                                aligns=['LEFT', 'RIGHT', 'RIGHT'], reads=reads))
    if _evr:
        story.append(Paragraph(_esc(
            f"BPA frente a ingresos: BPA {_evr['eps_growth'] * 100:+.1f}% frente a ingresos "
            f"{_evr['revenue_growth'] * 100:+.1f}% (los crecimientos que puntúa Crecimiento): {_evr['reading']}. "
            "Dato informativo, no puntúa: Crecimiento ya puntúa el BPA y los ingresos por separado."), S['small']))

    # Rango 52 semanas: posición del precio (contexto de mercado, etapa 9a)
    if pos52 is not None:
        story.append(Spacer(1, 10))
        story.append(Paragraph("Rango de precio · 52 semanas", S['h2']))
        # Etiqueta de EJE: es CONTEXTO (posición), ni precio (cara/barata) ni calidad.
        story.append(Paragraph(
            f"<font color='{MUTED.hexval()}'><b>CONTEXTO</b></font>"
            f"&nbsp;&nbsp;·&nbsp;&nbsp;Muestra dónde cotiza el precio dentro de su rango anual. Es contexto de "
            f"mercado: no es una señal de valoración ni mide la calidad del negocio.",
            ParagraphStyle('praxis', parent=S['small'], spaceAfter=4)))
        if r_52:
            story.append(Paragraph(_join_sentences([r_52[2]]), S['body']))
        bar = zone_bar_52(pos52, width=CW - 2.4 * inch, height=7)
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
        _z52 = (f"<font color='#77777f'>Precio actual {fv(price, 'price')} — posición {pos52:.0f}% del rango.</font>"
                + (f"&nbsp;&nbsp;<font color='{TONE_COLOR[r_52[1]].hexval()}'><b>{_esc(r_52[0])}</b></font>" if r_52 else ""))
        story.append(Paragraph(_z52, ParagraphStyle('rngc', parent=S['small'], alignment=TA_CENTER, spaceBefore=4)))
        story.append(Paragraph(
            "Tramos: mínimos, parte baja, zona media, parte alta y máximos. Es contexto de mercado: la posición en "
            "el rango no es una señal de valoración.",
            ParagraphStyle('rngz', parent=S['small'], alignment=TA_CENTER, textColor=FAINT, fontSize=6.8, spaceBefore=1)))

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
    if altman and altman.get("applicable") is False:
        _emit_card(model_card("n/a", 'neu', "Altman Z-Score", "No aplica", _esc(altman.get("interpretation", ""))))
        story.append(Spacer(1, 8))
        if r_rw:    # GROWTH_PRE_PROFIT: el runway sustituye al Altman en Solidez
            _rw_val = "FCF+" if _rw["state"] == "autofinanciada" else f"{_rw['years']:.1f}"   # años en el texto
            _emit_card(model_card(_rw_val, r_rw[1], "Runway", r_rw[0], _esc(
                f"{_cap(r_rw[2])} Runway = (caja + inversiones a corto plazo) / quema anual de FCF; "
                "sustituye al Altman en Solidez.")))
            story.append(Spacer(1, 8))
    elif altman and altman.get("available") is False and not is_financial \
            and (altman.get("details") or {}).get("reason") == "sin_dato":
        _emit_card(model_card("—", 'neu', "Altman Z-Score", "Sin dato",
                              _esc(f"{altman.get('interpretation', '')}. Altman exige todos sus componentes; "
                                   f"no se estima con ceros.")))
        story.append(Spacer(1, 8))
    elif altman and altman.get("z_score") is not None and not is_financial:
        z, zone = altman.get("z_score", 0), altman.get("zone", "grey")
        z_tone = 'pos' if zone == 'safe' else 'warn' if zone == 'grey' else 'neg'
        z_lab = "Zona segura" if zone == 'safe' else "Zona gris" if zone == 'grey' else "Zona de riesgo"
        _zd = altman.get("details") or {}  # umbrales del modelo usado (Z, Z' o Z'')
        _vars = ("EBIT y patrimonio contable frente al pasivo" if "Z''" in (altman.get("model") or "")
                 else "EBIT, valor de mercado y ventas")
        z_body = (f"{altman.get('interpretation', '')}. El modelo Altman Z pondera capital de trabajo, beneficios retenidos, "
                  f"{_vars} para estimar el riesgo de insolvencia a 2 años: por encima de "
                  f"{_zd.get('safe_threshold', 0):.2f} el riesgo es bajo; por debajo de {_zd.get('grey_threshold', 0):.2f}, elevado.")
        _emit_card(model_card(f"{z:.2f}", z_tone, "Altman Z-Score", z_lab, _esc(z_body)))
        story.append(Spacer(1, 8))

    if piotroski and piotroski.get("applicable") is False:
        _emit_card(model_card("n/a", 'neu', "Piotroski F-Score", "No aplica",
                              _esc(f"{piotroski.get('interpretation', '')}. El F-Score verifica mejoras contables "
                                   "(flujo operativo, liquidez, margen bruto, rotación) que no tienen sentido en "
                                   "este balance; no cuenta en Calidad.")))
    elif piotroski and piotroski.get("score") is not None:
        f_sc, f_max = piotroski.get("score", 0), piotroski.get("max_score", 9)
        f_n = piotroski.get("evaluated", f_max)
        f_scaled = piotroski.get("scaled_score")
        f_conclusive = piotroski.get("conclusive", True)
        f_for_tone = f_scaled if f_scaled is not None else f_sc
        # Escala única 8/6/4/2 (decisión 2 de la etapa 4): Fuerte/Bueno -> pos,
        # Neutral -> warn, Débil/Crítico -> neg.
        _pb = cfg("valuation.models.piotroski.bands")
        f_tone = ('neu' if not f_conclusive else
                  'pos' if f_for_tone >= _pb[1] else 'warn' if f_for_tone >= _pb[2] else 'neg')
        f_body = (f"{piotroski.get('interpretation', '')}. El F-Score de Piotroski verifica 9 señales contables de mejora "
                  f"en rentabilidad, estructura de capital y eficiencia operativa"
                  + (f" ({piotroski.get('fiscal_year')})" if piotroski.get("fiscal_year") else "") + ".")
        if f_n < f_max:
            # Cobertura (etapa 5): los criterios sin dato no cuentan como incumplidos.
            f_body += (f" Evaluados {f_n} de {f_max} criterios (el resto, sin dato)"
                       + (f"; resultado escalado a base {f_max}: {f_scaled:.1f}/{f_max}." if f_scaled is not None
                          else "; cobertura insuficiente para un resultado concluyente."))
        _emit_card(model_card(f"{f_sc}/{f_n}" if f_n < f_max else f"{f_sc}/{f_max}", f_tone, "Piotroski F-Score",
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
                state = crit.get("state") or ("cumple" if crit.get("passed") else "no_cumple")
                i = len(rows)
                rows.append([detail_labels.get(k, k.replace("_", " ").title()),
                             (crit.get("detail") or "")[:72],
                             {"cumple": "Cumple", "no_cumple": "No cumple", "sin_dato": "Sin dato"}[state]])
                reads.append((i, {"cumple": 'pos', "no_cumple": 'neg', "sin_dato": 'neu'}[state]))
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
        story.append(Paragraph("Desglose por categoría", S['h2']))
        story.append(Paragraph(
            "Cada categoría parte de una base neutral de 10/20. La columna Ajuste muestra cuánto suma o "
            "resta cada indicador según la banda en la que cae. Solidez, Rentabilidad, Calidad de ganancias y "
            "Crecimiento forman la calidad del negocio; Valoración, el atractivo del precio. Las categorías no "
            "concluyentes se excluyen y cada puntuación se reescala a 100 sobre las demás. En Valoración, P/E, "
            "Forward P/E, P/FCF, EV/EBITDA y PEG forman un solo bloque: su ajuste individual se muestra entre "
            "paréntesis y puntúa a través del Bloque de múltiplos (promedio de los ajustes reescalados a ±1, máximo "
            + " / ".join(f"±{m} con {i + 1}{'+' if i == 2 else ''}" for i, m in
                         enumerate(cfg('thresholds.score.valoracion.multiples_block_max_by_members')))
            + " miembros; en FINANCIAL, P/B y P/TBV forman su propio bloque)."
            + (f" {_esc(' · '.join(_cover_notes))}." if _cover_notes else ""), S['small']))
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
            tone = 'pos' if pctc >= 60 else 'warn' if pctc >= 40 else 'neg'
            bar_color = BRAND if tone == 'pos' else AMBER if tone == 'warn' else RED
            if cat.get("conclusive") is False:
                bd_rows.append([
                    Paragraph(_esc(cat_name), _cat_st),
                    Paragraph("<b>n/c</b>", ParagraphStyle('bdcs', fontName='Helvetica-Bold', fontSize=8.8,
                                                           leading=11, textColor=MUTED, alignment=TA_CENTER)),
                    Paragraph(_esc(f"No concluyente (cobertura {(cat.get('coverage') or 0):.0%}): "
                                   "excluida de su puntuación, que se reescala sobre las demás categorías"), _rea_st),
                ])
            else:
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
                if adj.get("metric") == "No aplica":
                    sign, tone_a = "n/a", 'neu'
                elif adj.get("in_block"):
                    # Lectura individual; puntúa a través del "Bloque de múltiplos".
                    sign, tone_a = f"({sign})", 'neu'
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
    _models = [m for k, m in (("altman", "Altman (1968)"), ("piotroski", "Piotroski (2000)"),
                              ("graham", "número de Graham"), ("dcf", "un DCF multietapa con WACC estimado por CAPM"))
               if k not in _na_keys and (k != "graham" or _graham_shown)]
    if archetype == "FINANCIAL":
        _models.append("P/B y P/TBV justificados por el retorno (Gordon)")
    elif archetype == "REIT":
        _models.append("P/FFO y rentabilidad sobre el FFO")
    _models_txt = ("los modelos de " + ", ".join(_models)) if _models else "los modelos de su arquetipo"
    story.append(Spacer(1, 14))
    story.append(HRFlowable(width="100%", thickness=0.5, color=HAIR))
    story.append(Spacer(1, 5))
    story.append(Paragraph(
        "<b>Metodología.</b> Este informe combina ratios TTM y del último ejercicio (fuente: Yahoo Finance) con "
        # Etapa 9a: solo los modelos que aplican al arquetipo.
        + _models_txt + " y "
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
