"""
Rediseño E5 (Task 5): metodología y anexo técnico del informe.

Metodología: fuentes con enlace al original (SEC EDGAR, Yahoo Finance, Finnhub, A. Damodaran), periodo de cada dato,
cómo se calculan las dos puntuaciones y la confianza (con las bandas del motor, de `config/thresholds.toml`), los
modelos y sus referencias, y el aviso legal del informe actual.

Anexo (después del título «Detalle técnico para auditoría», que el guardián trata como zona técnica): el detalle del
motor (`display.annex`) y los rangos de referencia aplicados a esta empresa en cada métrica (`display.tooltips`), con el
significado de la métrica (definiciones de la web).
"""
from typing import Any, Dict, List

from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

from numfmt import date_long
from settings import cfg

from . import parts as P
from . import theme as T
from .chapters import ANNEX, GLOSSARY, METHODOLOGY, bullet, heading_block, link, note, sub
from .definitions import definition, first_sentence
from .doc import esc, styles

DAMODARAN_URL = "https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datacurrent.html"
FINNHUB_URL = "https://finnhub.io/docs/api"
EDGAR_SEARCH = "https://www.sec.gov/edgar/search/"
DISCLAIMER = ("Documento generado automáticamente por Finanzer. La información puede contener errores u omisiones y "
              "no constituye asesoría financiera, recomendación de inversión ni oferta de valores. Verifique los datos y "
              "consulte a un profesional antes de invertir.")


def _edgar_url(a) -> str:
    cik = ((a.get("data_provenance") or {}).get("edgar") or {}).get("cik")
    return (f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={int(cik):010d}&type=10-K"
            if cik else EDGAR_SEARCH)


def _src(text_html: str) -> Paragraph:
    st = P._ps("msrc", "regular", T.BODY, leading=T.BODY_LEADING, color=T.TEXT_2)
    st.leftIndent, st.firstLineIndent, st.spaceAfter = 12, -12, 3
    return Paragraph(f"<font color='{T.TEXT_3.hexval()}'>●</font>&nbsp;&nbsp;{text_html}", st)


def _bands(kind: str) -> str:
    b, labels = cfg(f"thresholds.score.{kind}.bands"), cfg(f"thresholds.score.{kind}.labels")
    return " · ".join(f"{lab} ≥ {b[i]}" if i < len(b) else f"{lab} por debajo de {b[-1]}"
                      for i, lab in enumerate(labels))


def methodology(a: Dict[str, Any], ctx: Dict[str, Any]) -> list:
    from display import contraction_text
    d = a["display"]
    m = d["methodology"]
    sym = a.get("symbol") or ""
    bench = (a.get("benchmark") or {}).get("industry") or {}
    edgar = ((a.get("data_provenance") or {}).get("edgar") or {})
    # F11 · T7: lo que se cita sale de lo que aplica a su tipo y de la referencia que de verdad se usó.
    has_dcf = "dcf" not in (d.get("na_keys") or [])
    intrinsic = "DCF" if has_dcf else "valor justificado sobre libros" if (
        (a.get("classification") or {}).get("archetype") == "FINANCIAL") else "su modelo intrínseco"
    peers = (bench.get("self_exclusion") or {}).get("method") == "mediana_pares"
    ref_txt = ("medianas de sus pares del universo, en la industria en que la clasifica A. Damodaran" if peers
               else "agregados de A. Damodaran, NYU Stern")
    out = heading_block(METHODOLOGY[0], METHODOLOGY[1], METHODOLOGY[2], METHODOLOGY[1])
    out.append(Paragraph(esc(
        "Este informe combina " + m["ratios_text"] + " (fuente: Yahoo Finance) con " + m["models_text"]
        + " y dos puntuaciones Finanzer de 0 a 100: calidad del negocio (solidez, rentabilidad, calidad de ganancias "
        f"y crecimiento) y atractivo del precio (valoración por múltiplos y {intrinsic}, " + contraction_text() + "). "
        "Las lecturas se generan automáticamente según la banda en la que cae cada indicador frente a "
        f"umbrales canónicos y a la referencia de su industria ({ref_txt}), o "
        "la del mercado amplio cuando el arquetipo de la empresa contradice a su sector."), styles()["body"]))

    out += sub("Fuentes")
    out.append(_src(link("SEC EDGAR", _edgar_url(a)) + esc(
        ": estados oficiales del emisor (XBRL de los 10-K, 10-Q y 20-F) para verificar y completar las cifras"
        + (f"; CIK {edgar['cik']}." if edgar.get("cik") else "; este emisor no presenta estados en la SEC."))))
    out.append(_src(link("Yahoo Finance", f"https://finance.yahoo.com/quote/{sym}") + esc(
        ": cotización, perfil, estados de los proveedores y serie diaria de precios (cierre ajustado por dividendos y "
        "splits) de la empresa, del S&P 500 y del ETF sectorial de referencia.")))
    out.append(_src(link("Finnhub", FINNHUB_URL) + esc(
        ": fuente secundaria de ratios que faltan en la principal, consenso de beneficios y noticias de la empresa.")))
    out.append(_src(link("A. Damodaran (NYU Stern)", bench.get("url") or DAMODARAN_URL) + esc(
        (f": la clasificación por industria (industria «{bench.get('damodaran')}»). La referencia de este informe no es "
         "su agregado sino la mediana de los pares del universo en esa industria, sin la empresa (ver la nota de la "
         "tabla de múltiplos)." if peers else
         ": medianas y agregados por industria y región que sirven de referencia"
         + (f" (industria «{bench['damodaran']}», {bench.get('region_label') or ''}, {bench.get('firms')} empresas,"
            f" datos del {date_long(bench['as_of'])})" if bench.get("damodaran") and bench.get("as_of") else "")
         + "."))))

    out += sub("Periodo de cada dato")
    cover = d["cover"]
    rows = []
    if cover.get("as_of_note"):
        rows.append(["Estados financieros", cover["as_of_note"]])
    from .cover import price_session, short_date
    if price_session(a):
        rows.append(["Precio y rango de 52 semanas", f"Sesión del {short_date(price_session(a))}."])
    rows.append(["Ratios", f"{m['ratios_text'][:1].upper()}{m['ratios_text'][1:]}."])
    _pd = (bench.get("self_exclusion") or {}).get("peers_date")
    if peers and _pd:
        rows.append(["Referencia de la industria", f"Mediana de pares (Yahoo Finance), datos del {date_long(_pd)}."])
    elif bench.get("as_of"):
        rows.append(["Referencia de la industria", f"Damodaran, datos del {date_long(bench['as_of'])}."])
    mk = d["sections"].get("market") or {}
    if mk.get("source"):
        rows.append(["Contexto de mercado", mk["source"]])
    out.append(P.data_table(["Dato", "Periodo"], rows, T.CW, (0.3, 0.7), align=["left", "left"]))

    out += sub("Cómo se calculan las puntuaciones")
    base = cfg("thresholds.score.category")
    factors = cfg("thresholds.score.price.confidence_factor")
    out.append(bullet(
        f"Calidad del negocio: {len(cfg('thresholds.score.quality.categories'))} categorías (solidez, rentabilidad, "
        f"calidad de ganancias y crecimiento) que parten de {base['base']}/{base['max']} y suman o restan según la "
        f"banda de cada indicador; se reescalan a 100. Niveles: {_bands('quality')}."))
    out.append(bullet(
        f"Atractivo del precio: la categoría de Valoración (múltiplos frente a la referencia y {intrinsic}) reescalada a "
        f"100 y "
        f"acercada a {cfg('thresholds.score.price.neutral')} según la confianza del veredicto: "
        + " · ".join(f"{k} ×{v:g}" for k, v in factors.items())
        + ". Solo contraen los limitadores que contradicen el veredicto o lo vuelven incierto (la discrepancia entre "
          "métodos, los datos débiles, la dependencia del coste del capital); uno que apunta en su misma dirección no "
          f"contrae: las tasas base de un precio exigente. Niveles: {_bands('price')}."))
    out.append(bullet(
        "Confianza del veredicto: convergencia entre métodos de valoración, cobertura de datos, calidad de la fuente y "
        "estabilidad del tipo de empresa; la más baja manda."))
    out.append(bullet("Una categoría con menos de la mitad de sus componentes con dato no es concluyente: se excluye "
                      "y la puntuación se reescala sobre las demás."))

    out += sub("Modelos y referencias")
    for mdl in m.get("models") or []:
        out.append(bullet(mdl[:1].upper() + mdl[1:] + "."))
    if (a.get("reverse_dcf") or {}).get("applicable") is not False:
        out.append(bullet("Tasas base de crecimiento por tamaño e industria: Mauboussin y Callahan (2021), para el DCF "
                          "inverso."))
    out.append(Spacer(1, T.SPACE[1]))
    out.append(note(DISCLAIMER))
    return out


def annex(a: Dict[str, Any]) -> list:
    d = a["display"]
    ax = d.get("annex") or {}
    out = heading_block(ANNEX[0], "Anexo", ax.get("title") or ANNEX[2], ANNEX[1])
    items = ax.get("items") or []
    if not items:
        out.append(note("El análisis no trae detalle técnico para esta empresa."))
    for it in items:
        st = P._ps("ax", "regular", T.SMALL, leading=T.SMALL_LEADING, color=T.TEXT_2)
        st.spaceAfter = 4
        out.append(Paragraph(f"<b>{esc(it['label'])}:</b> {esc(it['text'])}", st))
    tips = d.get("tooltips") or {}
    if tips:
        out += sub("Rangos de referencia del motor para esta empresa")
        out.append(note("Las bandas con las que el motor lee cada métrica de esta empresa (según su tipo de negocio y "
                        "su referencia), con el significado de la métrica."))
        out.append(Spacer(1, 4))
        rows: List[list] = []
        for key, tip in tips.items():
            dd = definition(key) or {}
            name = dd.get("title") or key
            for tb in tip.get("tables") or []:
                bands = " · ".join(f"{b['label']} {b['range']}" for b in tb.get("bands") or [])
                rows.append([name, f"{tb.get('title') or ''}: {bands}" + (f" {tip['note']}" if tip.get("note") else "")])
                name = ""
        out.append(P.data_table(["Métrica", "Bandas"], rows, T.CW, (0.3, 0.7), align=["left", "left"]))
    return out


GLOSSARY_GUTTER = 16


def glossary_terms() -> List[tuple]:
    """(título, primera frase) de cada término del glosario, en el orden de `pdf.glossary.keys`; una clave sin
    definición no sale."""
    out = []
    for key in cfg("pdf.glossary")["keys"]:
        d = definition(key) or {}
        if d.get("title") and d.get("description"):
            out.append((d["title"], first_sentence(d["description"])))
    return out


def glossary() -> list:
    """V7 · P3: glosario de una página al final del informe (la jerga que usa, con las definiciones de la web), en dos
    columnas que se leen de arriba abajo."""
    terms = glossary_terms()
    if not terms:
        return []
    st = P._ps("gl", "regular", T.SMALL, leading=T.SMALL_LEADING, color=T.TEXT_2)
    cells = [Paragraph(f'<font name="{T.FONT["semibold"]}" color="#{T.INK.hexval()[2:]}">{esc(t)}.</font> {esc(x)}', st)
             for t, x in terms]
    half = (len(cells) + 1) // 2
    rows = [[cells[i], cells[i + half] if i + half < len(cells) else ""] for i in range(half)]
    col = (T.CW - GLOSSARY_GUTTER) / 2
    table = Table(rows, colWidths=[col + GLOSSARY_GUTTER / 2, col + GLOSSARY_GUTTER / 2])
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (0, -1), 0), ("RIGHTPADDING", (0, 0), (0, -1), GLOSSARY_GUTTER / 2),
        ("LEFTPADDING", (1, 0), (1, -1), GLOSSARY_GUTTER / 2), ("RIGHTPADDING", (1, 0), (1, -1), 0),
    ]))
    out = heading_block(GLOSSARY[0], cfg("pdf.glossary")["title"], GLOSSARY[2], GLOSSARY[1], new_page=True)
    out.append(note("Los términos que usa este informe, con la misma definición que el «?» de la web."))
    out.append(Spacer(1, T.SPACE[2]))
    out.append(table)
    return out
