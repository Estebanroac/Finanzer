"""
Rediseño E5: tokens del informe PDF (spec §5, tema claro) y tipografía.

Un solo lugar para el color, los tamaños y la geometría de la página. Los colores son los de la v4 (claro
institucional, sin degradados ni brillos); los tamaños siguen la preferencia del usuario por la legibilidad: cuerpo
10.5 pt con interlineado 1.45, tablas 9.5 pt, títulos de capítulo 18 pt y nada por debajo de 8 pt.

La fuente es Geist (licencia SIL OFL 1.1, `backend/assets/fonts/OFL.txt`), embebida desde los TTF de la release
oficial. Si los TTF no están, el informe sale en Helvetica (mismos tamaños) y `FONT_SOURCE` lo dice. La marca: el
logotipo «Finanzer» en Manrope 700 (SIL OFL 1.1, `backend/assets/fonts/OFL-Manrope.txt`, la instancia estática de
Google Fonts) junto al logo en su placa nocturna, en PNG, que genera `marca/exportar.mjs` (reportlab no dibuja SVG).
"""
import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ══════════════════════════════ color (spec §5, claro) ══════════════════════════════
PAPER = colors.HexColor("#F7F6F2")      # fondo de papel (tarjetas suaves)
SURFACE = colors.HexColor("#FFFFFF")    # página
CARD = colors.HexColor("#FBFAF7")       # relleno de tarjeta (papel aclarado, como la maqueta 5)
LINE = colors.HexColor("#E2E0DA")       # líneas y bordes
LINE_DOT = colors.HexColor("#D8D5CC")   # separadores punteados del índice
INK = colors.HexColor("#1B1D1F")        # títulos y cifras
TEXT_2 = colors.HexColor("#3A3D40")     # lectura
TEXT_3 = colors.HexColor("#6B6F73")     # secundario (contraste ≥ 4.5:1 sobre blanco)
GOOD = colors.HexColor("#16794A")       # bien / marca
WARN = colors.HexColor("#B07D1A")       # atención (rellenos)
WARN_TEXT = colors.HexColor("#8A6414")  # atención como texto: #B07D1A no llega a 4.5:1 sobre blanco
BAD = colors.HexColor("#B4532A")        # mal
NEUTRAL = colors.HexColor("#ECEAE4")    # neutro (rellenos)
# v4 (PM, color de las barras; los mismos de /v2): posición sin juicio y pesos, en azul pizarra (ni verde ni rojo)
POS_A = colors.HexColor("#D3E0EE")      # degradado de posición: extremo bajo
POS_B = colors.HexColor("#4F7FB0")      # degradado de posición: extremo alto
POS = colors.HexColor("#3F6E9E")        # relleno sin tono: peso de un segmento, la base de la escalera, un margen sin referencia

# Tintes apagados de cada tono para los tramos de las escalas y las pastillas (maqueta 5).
TINT = {
    "good": colors.HexColor("#BCD9C7"), "good_strong": colors.HexColor("#7FB79A"),
    "warn": colors.HexColor("#EFD3A6"), "bad": colors.HexColor("#E6B8A2"), "neutral": colors.HexColor("#E4E1D6"),
}
PILL_BG = {"good": colors.HexColor("#E8F2EC"), "warn": colors.HexColor("#F6EBD3"),
           "bad": colors.HexColor("#F7E6DD"), "neutral": NEUTRAL}
TONE_TEXT = {"good": GOOD, "warn": WARN_TEXT, "bad": BAD, "neutral": TEXT_2}

# Gráfica de precio: empresa en el verde de marca, mercado y sector en grises distinguibles por trazo.
SERIES_COLOR = {"company": GOOD, "market": colors.HexColor("#6B6F73"), "sector": colors.HexColor("#A39B85")}


def tone(t):
    """Tono del motor (pos/neg/warn/neu, o los de la v4) → tono del PDF (good/bad/warn/neutral)."""
    return {"pos": "good", "good": "good", "neg": "bad", "bad": "bad", "warn": "warn"}.get(t or "", "neutral")


# ══════════════════════════════ página (carta) ══════════════════════════════
PAGE_W, PAGE_H = letter
M_LR = 0.75 * inch            # 54 pt: margen lateral (cabecera y pie se alinean con él)
M_TOP = 0.8 * inch            # 57.6 pt: banda de cabecera por encima del marco
M_BOT = 0.72 * inch           # 51.8 pt: banda de pie por debajo del marco
CW = PAGE_W - 2 * M_LR        # ancho útil (504 pt)
CH = PAGE_H - M_TOP - M_BOT   # alto útil del marco
HEADER_Y = PAGE_H - 0.5 * inch    # línea base del texto de la cabecera
FOOTER_Y = 0.4 * inch             # línea base del texto del pie
RULE_GAP = 8                      # distancia de la línea fina de cabecera/pie a su texto

# ══════════════════════════════ tamaños (pt) ══════════════════════════════
BODY = 10.5
BODY_LEADING = round(BODY * 1.45, 2)    # 15.23
TABLE = 9.5
TABLE_LEADING = round(TABLE * 1.35, 2)
TITLE = 18                              # título de capítulo
TITLE_LEADING = 22
LABEL = 8                               # etiquetas en versalitas: el mínimo absoluto
LABEL_SPACING = 0.6                     # espaciado de las versalitas (≈ .08em)
SMALL = 9                               # notas y fuentes
SMALL_LEADING = 12.5
MIN_FONT = 8                            # nada por debajo (prueba con los tamaños de pdfium)
SPACE = (4, 8, 12, 16, 24, 32, 48)      # una sola escala de espaciado (spec §5)
RADIUS = 5                              # esquinas de tarjeta
GUTTER = 12                             # separación entre tarjetas de una fila

# Escala mínima a la que se admite encoger un bloque que debe caber en una página (portada, resumen).
MIN_SCALE = 0.85

# ══════════════════════════════ fuente ══════════════════════════════
FONTS_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "assets", "fonts"))
_GEIST = {"regular": "Geist-Regular.ttf", "medium": "Geist-Medium.ttf", "semibold": "Geist-SemiBold.ttf",
          "bold": "Geist-Bold.ttf"}
_HELV = {"regular": "Helvetica", "medium": "Helvetica", "semibold": "Helvetica-Bold", "bold": "Helvetica-Bold"}
FONT = dict(_HELV)
FONT_SOURCE = "Helvetica (Geist no encontrada)"


def register_fonts():
    """Registra Geist una vez (idempotente). Devuelve el mapa peso → nombre de fuente en uso."""
    global FONT_SOURCE
    if FONT["regular"] == "Geist":
        return FONT
    paths = {w: os.path.join(FONTS_DIR, f) for w, f in _GEIST.items()}
    if not all(os.path.isfile(p) for p in paths.values()):
        return FONT
    names = {"regular": "Geist", "medium": "Geist-Medium", "semibold": "Geist-SemiBold", "bold": "Geist-Bold"}
    for w, p in paths.items():
        if names[w] not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(names[w], p))
    # <b> en los párrafos = semibold (600, como la web); sin cursivas en el informe.
    pdfmetrics.registerFontFamily("Geist", normal="Geist", bold="Geist-SemiBold", italic="Geist",
                                  boldItalic="Geist-SemiBold")
    FONT.update(names)
    FONT_SOURCE = "Geist (SIL OFL 1.1)"
    return FONT


register_fonts()

# ── marca ──
_MANROPE = os.path.join(FONTS_DIR, "Manrope-Bold.ttf")
if os.path.isfile(_MANROPE):
    if "Manrope-Bold" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("Manrope-Bold", _MANROPE))
    FONT["brand"] = "Manrope-Bold"
else:                                            # sin Manrope, el nombre en la fuente del informe
    FONT["brand"] = FONT["semibold"]
_REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
BRAND_LOGO = next((p for p in (os.path.join(_REPO, "frontend", "public", "brand", "finanzer-logo.png"),
                               os.path.join(_REPO, "frontend", "out", "brand", "finanzer-logo.png")) if os.path.isfile(p)), None)
BRAND_LOGO_RATIO = 1                             # el logo en su placa cuadrada (marca/exportar.mjs)
