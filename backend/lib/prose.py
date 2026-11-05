"""V7 (puntuación del motor): qué textos de `display` son frases y cómo se unen.

Una sola declaración para el generador (`close_sentences`, al final de `display.build_display`) y para el guardián
(`tests/guardian.py`, reglas `puntuacion_doble` y `frase_sin_cierre`):

- **frase**: termina en su puntuación (`.`, `)`, `»`, `…`, `?` o `!`). El generador la cierra; las webs y los PDF no
  añaden otro punto (cierran solo lo que no está cerrado).
- **etiqueta**: nombre de fila, valor, lectura corta («Superior», «Prima elevada»), título o rango; sin punto.
- **titular**: titular corto que encabeza un detalle (alertas, «Qué vigilar», veredicto); sin punto.
- **fragmento**: va dentro de otra frase que lo cierra quien la compone (la lista de modelos de la metodología, el
  motivo tras «Sin noticias recientes:», los puntos del pre-mortem que continúan «Esta lectura sería errónea si…»).
- **externo**: texto de un tercero (titulares y resúmenes de noticias, ficha de la SEC); no se toca.

Con 3 palabras o menos, un texto es etiqueta. Un campo de 4 palabras o más que no esté declarado aquí lo marca el
guardián: hay que declararlo antes de que llegue al lector.

Las uniones de frases no producen «.;», «;.» ni «..»: `join_clauses` quita el punto de cada parte antes del «; ».
"""
import re
from typing import Any, Iterable, Optional

END = re.compile(r"[.)»…?!]$")
DOUBLE = re.compile(r"\.;|;\.|(?<![.…])\.\.(?!\.)")
SHORT_WORDS = 3

# Claves que siempre son etiqueta, estén donde estén.
LABEL_KEYS = frozenset({
    "label", "title", "metric", "value", "value_txt", "bench", "bench_txt", "ref", "kicker", "date_txt",
    "question", "range", "basis", "reading", "status", "tooltip", "source", "pe_label", "caption_short",
    "behavioral_title", "axis_label",
})

# (patrón de la ruta, clase). Primera coincidencia gana; las rutas son las de `walk` (".a.b[].c").
DECLARED = [
    # externos
    (r"\.extended\.news(_featured)?\[\]\.(headline|summary)", "externo"),
    (r"\.sections\.market\.news\[\]\.(headline|summary)", "externo"),
    (r"\.extended\.company_profile\.rows\[\]\.value", "externo"),
    # titulares cortos
    (r"\.sections\.alerts\.groups\[\]\.items\[\]\.reason", "titular"),
    (r"\.cover\.highlights\[\]\.text", "titular"),
    (r"\.cover\.verdict\.text", "titular"),
    # V4-F8: la nota de una puntuación en forma corta (la cabecera; la frase completa va en `note`)
    (r"\.cover\.(quality|price)\.note_short", "titular"),
    (r"\.annex\.title", "titular"),
    # fragmentos que cierra quien los compone
    (r"\.methodology\.(models\[\]|models_text|ratios_text|contraction_text)", "fragmento"),
    (r"\.sections\.valuation\.premortem\.items\[\]", "fragmento"),
    (r"\.(cover|sections\.institutional\.breakdown)\.coverage_notes\[\]", "fragmento"),
    (r"\.sections\.market\.news_note", "fragmento"),
    # F8 · P3: el rango del bloque central de la tabla de sensibilidad (la web lo cierra tras «Valor $X: »)
    (r"\.charts\.valuation\.fair_value\.central_text", "fragmento"),
    (r"\.extended\.(company_profile|history_10y)\.reason", "fragmento"),
    # V4b: por qué falta una cifra de un ejercicio (la ficha lo pone tras el nombre del dato, como el motivo de arriba)
    (r"\.extended\.history_10y\.rows\[\]\.reasons\.\w+", "fragmento"),
    # etiquetas con clave de texto (celdas, fórmulas y líneas de datos)
    (r"\.cover\.categories\[\]\.items\[\]\.text", "etiqueta"),
    (r"\.sections\.solvency\.balance", "etiqueta"),
    (r"\.charts\.valuation\.scored\[\]\.reason", "etiqueta"),
    (r"\.sections\.profitability\.figures\[\]\[\]", "etiqueta"),
    (r"\.sections\.valuation\.sensitivity\.band_labels\[\]", "etiqueta"),
    (r"\.sections\.historical\.not_applicable\.\w+", "etiqueta"),
    (r"\.summary\.cards\[\]\.bench", "etiqueta"),
    (r"\.cover\.verdict\.(confidence_text|full)", "etiqueta"),
    (r"\.confidence\.verdict_text", "etiqueta"),
    (r"\.profile\.(sector|industry)", "etiqueta"),
    # F9 · R3: el periodo de las cifras (título de la tabla; «de los últimos doce meses (TTM, a …)» va tras «ingresos»)
    (r"\.sections\.profitability\.figures_title", "titular"),
    (r"\.charts\.profitability\.margin_ladder\.period\.of", "fragmento"),
    (r"\.charts\.historical\.series\[\]\.cagr_note", "etiqueta"),
    # F10 · B1: el motivo de un ejercicio sin cifra, bajo la celda (como la variación)
    (r"\.charts\.historical\.series\[\]\.points\[\]\.reason", "etiqueta"),
    (r"\.charts\.historical\.growth_currency_note", "frase"),
    # F8 · P3: cada texto del anexo es una o varias frases completas (la clasificación las une con prose.sentences)
    (r"\.annex\.items\[\]\.text", "frase"),
    # frases (lo demás con 4 palabras o más que no es etiqueta por su clave)
    (r"\.charts\.growth\[\]\.reading", "frase"),
    (r".*\.(text|note|notes\[\]|reason|detail|body|intro|summary|status_note|dcf_params|dcf_missing|"
     r"dcf_reliability|roce_reading|divergence_note|normalization_note|reference_note|market_note|wacc_note|"
     r"ke_note|graham_note|eps_vs_revenue_note|zones_note|axis|caption|pead_note|role|method|as_of_note|"
     r"currency_note|data_notices\[\]|classification_notes\[\]|confidence_reasons\[\]|plain\[\]|behavioral\[\])",
     "frase"),
]
_DECLARED = [(re.compile(p), k) for p, k in DECLARED]


def kind(path: str, text: str) -> Optional[str]:
    """Clase del texto `text` en `path` (ruta de `walk`); None si un texto largo no está declarado."""
    if len(text.split()) <= SHORT_WORDS:
        return "etiqueta"
    for rx, k in _DECLARED:
        if rx.fullmatch(path):
            return k
    last = re.sub(r"\[\]$", "", path.rsplit(".", 1)[-1])
    return "etiqueta" if last in LABEL_KEYS else None


def walk(o: Any, p: str = ""):
    """(ruta, texto) de cada cadena de `o`."""
    if isinstance(o, dict):
        for k, v in o.items():
            yield from walk(v, f"{p}.{k}")
    elif isinstance(o, list):
        for v in o:
            yield from walk(v, f"{p}[]")
    elif isinstance(o, str):
        yield p, o


def close(t: Optional[str]) -> Optional[str]:
    """La frase con su punto final (sin duplicarlo; «;», «,» o «:» finales se sustituyen)."""
    if not t or not t.strip():
        return t
    s = t.rstrip()
    if END.search(s):
        return s
    return s.rstrip(";,:").rstrip() + "."


def sentences(parts: Iterable[Optional[str]]) -> Optional[str]:
    """Varias frases seguidas en un solo texto: cada una con mayúscula inicial y su punto final (F8 · P3: el detalle de
    la clasificación del anexo, cuyas partes vienen de motivos escritos para ir dentro de otra frase)."""
    xs = [close(x.strip()[0].upper() + x.strip()[1:]) for x in parts if x and x.strip()]
    # Una frase que acaba en «)» o «»» está cerrada sola, pero seguida de otra necesita su punto: «(banco). Su historia…».
    return " ".join(x if (i == len(xs) - 1 or x.endswith((".", "…", "?", "!"))) else x + "."
                    for i, x in enumerate(xs)) or None


def clause(t: str) -> str:
    """Una frase como parte de otra (antes de «; »): sin su punto final (los «…» se quedan)."""
    s = t.strip()
    return s[:-1].rstrip() if s.endswith(".") and not s.endswith("..") else s


def join_clauses(parts: Iterable[Optional[str]], sep: str = "; ") -> Optional[str]:
    """Une frases con «; »: la primera conserva su mayúscula, las siguientes van en minúscula y el conjunto se cierra
    con un punto. Sin «.;» ni «;.»."""
    xs = [clause(x) for x in parts if x and x.strip()]
    if not xs:
        return None
    return close(sep.join(x if i == 0 else x[0].lower() + x[1:] for i, x in enumerate(xs)))


def close_sentences(o: Any, p: str = "") -> Any:
    """Cierra en sitio cada frase declarada de `o` (el `display`)."""
    if isinstance(o, dict):
        for k, v in o.items():
            if isinstance(v, str):
                if kind(f"{p}.{k}", v) == "frase":
                    o[k] = close(v)
            else:
                close_sentences(v, f"{p}.{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            if isinstance(v, str):
                if kind(f"{p}[]", v) == "frase":
                    o[i] = close(v)
            else:
                close_sentences(v, f"{p}[]")
    return o
