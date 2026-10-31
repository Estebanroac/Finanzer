"""
Rediseño E5 (Task 4): los nueve capítulos del informe, los mismos de la página-historia de la web (mismo orden y
títulos que `frontend/src/v2/lib/story.ts`), con lo esencial de su página de profundidad (la selección de E3):
lectura, visual clave, tabla técnica completa y notas. Nada de lo que trae el informe actual (lib/pdf_report.py) se
pierde: lo prueba tests/test_pdf_v2_contenido.py.

Composición sin huecos: los capítulos van seguidos; un título nunca queda solo al pie (se lleva consigo
`keep_lines_after_title` líneas, config/pdf.toml) y las tablas se parten por filas.

Datos que publicará E2 (display.extended, segmentos, rivales en caché) entran por la misma interfaz que su ausencia:
sin dato, cada bloque dice su motivo.
"""
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from reportlab.platypus import CondPageBreak, PageBreak, Paragraph, Spacer

import segments as _segments
import names
from settings import cfg

from . import parts as P
from . import theme as T
from .definitions import meaning
from .doc import ChapterHeading, FloatGroup, Stack, Unit, esc, styles


@dataclass(frozen=True)
class Chapter:
    id: str
    nav: str
    title: Callable[[Dict[str, Any]], str]


CHAPTERS: List[Chapter] = [
    Chapter("empresa", "La empresa", lambda a: f"Qué es {(a.get('profile') or {}).get('name') or a.get('symbol')}"),
    Chapter("negocio", "Cómo gana dinero", lambda a: "De dónde vienen sus ingresos"),
    Chapter("accion", "La acción", lambda a: "Cómo se ha movido el precio"),
    Chapter("calidad", "Calidad", lambda a: "Qué tan buena es la empresa"),
    Chapter("valor", "Cuánto vale", lambda a: "Lo que exige el precio"),
    Chapter("rivales", "Rivales", lambda a: "Frente a su referencia"),
    Chapter("riesgos", "Riesgos", lambda a: "Qué puede salir mal"),
    Chapter("actualidad", "Actualidad", lambda a: "Qué está pasando"),
    Chapter("conclusion", "Conclusión", lambda a: "Nuestra lectura"),
]
METHODOLOGY = ("metodologia", "Metodología", "Cómo se hace este informe")
ANNEX = ("anexo", "Anexo · Detalle técnico", "Detalle técnico para auditoría")
GLOSSARY = ("glosario", "Glosario", "Qué quiere decir cada término")


def chapter_key(ch: Chapter) -> str:
    return f"cap-{ch.id}"


def toc_text(index: int, ch: Chapter) -> str:
    return f"{index} · {ch.nav}"


def toc_entries() -> List[tuple]:
    """(texto, clave) de cada entrada del índice, en orden."""
    out = [(toc_text(i, ch), chapter_key(ch)) for i, ch in enumerate(CHAPTERS, 1)]
    return out + [(METHODOLOGY[1], METHODOLOGY[0]), (ANNEX[1], ANNEX[0]), (GLOSSARY[1], GLOSSARY[0])]


# ══════════════════════════════ texto ══════════════════════════════
def _cap(t: str) -> str:
    return t[:1].upper() + t[1:]


def _dot(t: str) -> str:
    return t if re.search(r"[.…:]$", t) else f"{t}."


def _join(*xs: Optional[str]) -> str:
    return " ".join(_dot(_cap(x.strip())) for x in xs if x and x.strip())


def _sentences(t: Optional[str]) -> List[str]:
    return [x for x in re.split(r"(?<=\.)\s+", t or "") if x.strip()]


def _first(*xs: Optional[str]) -> str:
    return next((x for x in xs if x and x.strip()), "")


def _keep():
    return cfg("pdf.layout.keep_lines_after_title")


def body(text: str) -> Paragraph:
    return Paragraph(esc(text), styles()["body"])


def note(text: str) -> Paragraph:
    st = styles()["small"]
    return Paragraph(esc(text), st)


def bullet(text: str, tone: Optional[str] = None) -> Paragraph:
    tn = T.tone(tone)
    dot = T.TONE_TEXT[tn] if tn != "neutral" else T.TEXT_3
    st = P._ps("bul", "regular", T.BODY, leading=T.BODY_LEADING, color=T.TEXT_2)
    st.leftIndent, st.firstLineIndent, st.spaceAfter = 12, -12, 3
    return Paragraph(f"<font color='{dot.hexval()}'>●</font>&nbsp;&nbsp;{esc(text)}", st)


class SubTitle(Paragraph):
    """Subtítulo de sección: viaja con el bloque visual que le sigue (ver `floated`)."""
    is_title = True


def sub(title: str, space_before: float = T.SPACE[3]) -> list:
    """Subtítulo de una sección del capítulo; si no caben él y unas líneas detrás, pasa a la página siguiente."""
    st = P._ps("sub", "semibold", 12.5, leading=16, color=T.INK)
    st.spaceBefore, st.spaceAfter = space_before, 6
    return [CondPageBreak(space_before + 22 + _keep() * T.BODY_LEADING), SubTitle(esc(title), st)]


def absent(title: str, reason: str, space_before: float = T.SPACE[3]) -> list:
    """Bloque sin dato (revisión del PM de E5): en lugar de su subtítulo y una caja vacía, una sola línea con el título
    del bloque y el motivo en texto secundario; lo que sigue sube a ocupar el sitio."""
    line = P.missing_line(title, reason, space_before=space_before)
    line.style.spaceAfter = 2
    return [line]


# Bloques visuales indivisibles y altos: si no caben al pie, el texto que les sigue llena la página (FloatGroup).
FLOATS = (P.PriceChart, P.Piotroski, P.History10, P.SegmentBars, P.Sized, P.BarList, P.CategoryBars, Stack)


def floated(items: list) -> list:
    """Envuelve cada bloque visual (con su subtítulo, si lo precede) y lo que le sigue en el capítulo en un
    FloatGroup, de modo que un bloque que no cabe al pie no deje su hueco detrás."""
    for i, f in enumerate(items):
        if isinstance(f, FLOATS):
            prefix, unit = items[:i], f
            if prefix and isinstance(prefix[-1], SubTitle):
                unit = Stack([prefix[-1], f])
                prefix = prefix[:-1]
                if prefix and isinstance(prefix[-1], CondPageBreak):
                    prefix = prefix[:-1]
            return prefix + [FloatGroup(unit, floated(items[i + 1:]))]
    return items


def link(text: str, url: Optional[str]) -> str:
    """Texto enlazado si la URL es https; si no, el texto solo (la prueba exige https en todo enlace externo)."""
    if url and str(url).startswith("https://"):
        return f'<a href="{esc(url)}" color="{T.GOOD.hexval()}">{esc(text)}</a>'
    return esc(text)


# ══════════════════════════════ lectura de cada capítulo (como story.ts) ══════════════════════════════
def lead(ch: Chapter, a: Dict[str, Any], ctx: Optional[Dict[str, Any]] = None) -> str:
    """La lectura con la que abre cada capítulo: las mismas frases del motor que la página-historia de la web (`ctx`:
    los segmentos del capítulo 2, como en la web)."""
    d = a["display"]
    cover, s = d["cover"], d["sections"]
    prof = a.get("profile") or {}
    verdict = cover["verdict"]["text"]
    execs = {e["label"]: e["text"] for e in d["summary"]["exec_items"]}
    market = s.get("market") or {}
    if ch.id == "empresa":
        es = d.get("profile") or {}             # V7: sector e industria en español
        txt = _join(f"{prof.get('name')} opera en {names.inline(es.get('industry') or prof.get('industry'))} "
                    f"({names.inline(es.get('sector') or prof.get('sector'))})",
                    execs.get("CRECIMIENTO Y RETORNO"))
    elif ch.id == "negocio":
        # V7 · P4: de dónde vienen los ingresos lo dicen los segmentos (producto y geografía); el DuPont va en Calidad
        sm = _segments.summary((ctx or {}).get("segments"))
        txt = _join(sm.get("text"), sm.get("second_text")) if sm and sm.get("text") else \
            _join(_first(execs.get("RENTABILIDAD"), s["profitability"].get("intro")))
    elif ch.id == "accion":
        trend = next((r for r in market.get("rows") or [] if r.get("key") == "trend"), None)
        txt = _join(execs.get("CONTEXTO DE MERCADO"), (trend or {}).get("text")) or \
            _join((s["growth"].get("range52") or {}).get("caption"))
    elif ch.id == "calidad":
        txt = _join(cover["quality"].get("note"), execs.get("CALIDAD DEL NEGOCIO"),
                    (_sentences(execs.get("CREACIÓN DE VALOR")) or [None])[0])
    elif ch.id == "valor":
        rev = s["valuation"].get("reverse_dcf") or {}
        txt = _join(*[ln.get("text") for ln in rev.get("lines") or []]) or \
            _join(_first(execs.get("ATRACTIVO DEL PRECIO"), s["valuation"].get("intro")))
    elif ch.id == "rivales":
        comp = d["charts"]["comparison"]
        ref = [x for x in _sentences(comp.get("note")) if not x.startswith("Sin referencia")]
        txt = _join(f"Comparada con el agregado {d['benchmark']['ref']}, es mejor en {comp['better']} de "
                    f"{comp['total']} métricas", *ref)
    elif ch.id == "riesgos":
        watch = next((h for h in cover["highlights"] if h["kind"] == "watch"), None)
        txt = _join(execs.get("SOLIDEZ"), f"{_cap(watch['kicker'].lower())}: {watch['text']}" if watch else None)
    elif ch.id == "actualidad":
        txt = _join(market.get("note"))
    else:
        txt = _join(cover["verdict"].get("full") or verdict)
    return txt or verdict


# ══════════════════════════════ capítulos ══════════════════════════════
def _row_note(rows):
    """Lecturas completas de las filas (la tabla enseña la pastilla; la frase del motor va debajo)."""
    return [bullet(_cap(r["text"]), r.get("tone")) for r in rows if r.get("text") and r.get("state") == "con_dato"]


def _empresa(a, ctx):
    d = a["display"]
    cover = d["cover"]
    prof = a.get("profile") or {}
    ext = d.get("extended") or {}
    cp = ext.get("company_profile") or {}
    if cp.get("status") == "ok" and cp.get("rows"):
        rows = [[r["label"], r["value"]] for r in cp["rows"]]
        src = cp.get("source")
        reason = None
    else:
        # respaldo de Yahoo: solo los campos que hay (un campo ausente no ocupa una fila «Sin dato»); industria, sector y
        # país en español (display.profile, lib/names.py), como en la web
        es = d.get("profile") or {}
        rows = [[lab, es.get(k) or prof.get(k)] for lab, k in (("Industria", "industry"), ("Sector", "sector"),
                                                               ("País", "country"), ("Bolsa", "exchange"),
                                                               ("Moneda de cotización", "currency")) if prof.get(k)]
        src = "Yahoo Finance (perfil)"
        reason = cp.get("reason") or "la ficha oficial de EDGAR (SIC, sede, cierre fiscal) aún no llega en este análisis"
    if rows:
        out = sub("Ficha", space_before=T.SPACE[2])
        out.append(Stack([P.data_table(["Campo", "Valor"], rows, T.CW, (0.36, 0.64), align=["left", "left"]),
                          Spacer(1, 4), note(f"Fuente: {src}." + (f" Ficha oficial: {reason}." if reason else ""))]))
    else:
        out = absent("Ficha", f"sin datos del emisor: {reason}", space_before=T.SPACE[2])
    out += sub("Cifras clave")
    kpis = cover.get("kpis") or []
    cards = [P.FigureCard(k["label"], k["value"] if k.get("state") == "con_dato" else "Sin dato") for k in kpis]
    grid = []
    for i in range(0, len(cards), 4):
        if i:
            grid.append(Spacer(1, T.SPACE[1]))
        grid.append(P.equal_row(cards[i:i + 4]))
    if grid:
        out.append(Stack(grid))
    # F10 · B1: como la web, el porqué de cada cifra clave sin dato, bajo la rejilla
    for k in kpis:
        if k.get("state") != "con_dato" and k.get("text"):
            out.append(note(f"{k['label']}: {k['text'][:1].lower()}{k['text'][1:]}"))
    out += sub("Clasificación")
    out.append(body(f"Tipo de negocio: {cover['archetype_label']}."))
    for n in cover.get("classification_notes") or []:
        out.append(body(n))
    badge = cover.get("official_source_badge")
    if badge:
        out.append(bullet(f"{badge['label']}: {badge['tooltip']}", "warn"))
    for t in (cover.get("currency_note"), cover.get("as_of_note")):
        if t:
            out.append(note(t))
    for t in cover.get("data_notices") or []:
        out.append(bullet(f"Aviso. {t}", "warn"))
    if prof.get("description"):
        out += sub("Descripción del emisor")
        out.append(body(prof["description"]))
    return out


NA_LABELS = {"fcf_margin": "Margen FCF", "free_cash_flow": "Flujo de caja libre", "gross_margin": "Margen bruto",
             "operating_margin": "Margen operativo"}


def _negocio(a, ctx):
    d = a["display"]
    s = d["sections"]
    ext = d.get("extended") or {}
    # V7 · P4: el desglose por producto si el emisor lo publica (Apple: iPhone, Service…); la geografía va en la lectura
    # (con lo que cubren los segmentos si no son todos los ingresos, en la línea de la fuente)
    seg = P.SegmentBars(_segments.product_view(ctx.get("segments")),
                        note=(_segments.summary(ctx.get("segments")) or {}).get("coverage_note"))
    if seg.available():
        out = sub("Ingresos por segmento", space_before=T.SPACE[2]) + [seg]
    else:
        out = absent("Ingresos por segmento", f"sin desglose oficial: {seg.reason()}", space_before=T.SPACE[2])
    hist = P.History10(ext.get("history_10y"))
    out += (sub("Historia de 10 ejercicios") + [hist]) if hist.available() else \
        absent("Historia de 10 ejercicios", f"sin dato: {hist.reason()}")
    ml = d["charts"]["profitability"].get("margin_ladder") or {}
    steps = [x for x in ml.get("steps") or [] if x.get("state") == "con_dato" and x.get("pct") is not None]
    out += sub("Márgenes")
    if ml.get("revenue_txt") and steps:
        rows = [("Ingresos", 1.0, f"100% · {ml['revenue_txt']}", None)] + \
               [(x["label"], x["pct"], f"{x['pct_txt']} · {x['amount_txt']}", x.get("tone")) for x in steps]
        # v4 (PM): el color dice la lectura frente a su industria; la base y un margen sin referencia, en azul pizarra
        out.append(Stack([P.BarList(rows, value_w=130, neutral=T.POS), Spacer(1, 4),
                          note((f"Cada margen como parte de los ingresos {ml['period']['of']}." if ml.get("period")
                                else "Cada margen como parte de los ingresos.")
                               + " El color es su lectura frente a su industria; en azul, la base (los ingresos) y los "
                                 "márgenes sin comparación con la industria.")]))
    na = (s.get("historical") or {}).get("not_applicable") or {}
    for k, why in na.items():
        out.append(note(f"{NA_LABELS.get(k) or definition_title(k) or k}: {why}."))
    out += sub(s["profitability"].get("figures_title") or "Cifras de los estados financieros")
    fig = s["profitability"].get("figures") or []
    out.append(Stack([P.data_table(["Concepto", "Valor", "Concepto", "Valor"], fig, T.CW, (0.3, 0.2, 0.3, 0.2),
                                   align=["left", "right", "left", "right"], bold_first=False)]))
    return out


def definition_title(key):
    from .definitions import definition
    dd = definition(key)
    return dd["title"] if dd else None


def _accion(a, ctx):
    d = a["display"]
    s = d["sections"]
    prices = ctx.get("prices")
    sym = a.get("symbol")
    sector_etf = ((prices or {}).get("sector") or {}).get("symbol")
    chart = P.PriceChart(prices, sym, height=170, period="5y", sector_label=sector_etf,
                         title="Precio en 5 años · base 100")
    if chart.win["status"] == "ok":
        out = sub("Precio en 5 años", space_before=T.SPACE[2]) + [chart]
    else:
        out = absent("Precio en 5 años", f"gráfica no disponible: {chart.win['reason']}", space_before=T.SPACE[2])
    pr = P.period_returns(prices)
    if pr["status"] == "ok":
        out += sub("Rentabilidad por periodo")
        labels = {"company": sym, "market": "S&P 500", "sector": sector_etf or "ETF del sector"}
        head = ["Periodo"] + [labels[r] for r in pr["roles"]]
        rows = [[lab] + [P._fmt_ret(v[r]) if v[r] is not None else "—" for r in pr["roles"]] for lab, v in pr["rows"]]
        n = len(head)
        out.append(Stack([P.data_table(head, rows, T.CW, [0.34] + [0.66 / (n - 1)] * (n - 1)), Spacer(1, 4),
                          note("Rentabilidad con el cierre ajustado por dividendos y splits (Yahoo Finance), hasta "
                               f"{P._fmt_day(pr['end'])}. «—»: la serie no cubre el periodo completo.")]))
    else:
        out += absent("Rentabilidad por periodo", f"sin dato: {pr['reason']}")
    r52 = s["growth"].get("range52")
    # V4b: el subtítulo, su contexto y la barra van juntos (con la serie de 5 años del replay completa, la barra quedaba
    # sola arriba de la página siguiente, con la cifra del precio sin su rótulo)
    head = sub("Rango de 52 semanas")
    blk = head[1:]
    if r52:
        blk.append(note(f"Contexto · {r52['axis']}"))
        if r52.get("reading"):
            blk.append(body(_dot(_cap(r52["reading"]["text"]))))
        blk.append(Spacer(1, 4))
    blk.append(P.Range52(r52))
    out += head[:1]
    out.append(Stack([Unit(blk)] + ([Spacer(1, 4), note(f"{r52['caption']} {r52['zones_note']}")] if r52 else [])))
    mk = s.get("market")
    if mk:
        out += sub("Señales de mercado (contexto, no puntúan)")
        out.append(note(mk["note"]))
        if mk.get("status_note"):
            out.append(note(mk["status_note"]))
        if mk.get("rows"):
            out.append(Spacer(1, 4))
            out.append(P.data_table(["Señal", "Valor", "Lectura"],
                                    [[r["label"], r["value"], _cap(r["text"])] for r in mk["rows"]],
                                    T.CW, (0.26, 0.14, 0.6), align=["left", "right", "left"]))
        out.append(Spacer(1, 4))
        out.append(note(mk["source"]))
    return out


def _calidad(a, ctx):
    d = a["display"]
    s, cover = d["sections"], d["cover"]
    ext = d.get("extended") or {}
    q = cover["quality"]
    out = sub("Las cuatro categorías", space_before=T.SPACE[2])
    blk = [body(f"{q['title'].capitalize()}: {q['score'] if q['score'] is not None else '—'} / 100 · "
                f"{q.get('level') or 'sin dato'}.")]
    items = [i for i in cover["categories"][0]["items"]]
    blk.append(P.CategoryBars(items))
    for it in items:
        if not it.get("conclusive", True) and it.get("text"):
            blk.append(note(f"{it['name']}: {it['text']}"))
    cap = [x for x in _sentences(d["summary"]["composition"]["caption"]) if x.startswith("Calidad")]
    if cap:
        blk += [Spacer(1, 4), note(cap[0])]
    out.append(Stack(blk))
    pf = s["profitability"]
    out += sub("Rentabilidad y eficiencia")
    if pf.get("intro"):
        out.append(body(pf["intro"]))
        out.append(Spacer(1, 6))
    out.append(P.tech_table(pf["rows"], T.CW, header=pf["columns"], meaning=meaning))
    out.append(Spacer(1, 6))
    for t in (pf.get("divergence_note"),):
        if t:
            out.append(note(t))
    for qr in pf.get("quality_readings") or []:
        out.append(bullet(f"{qr['label']}. {qr['text']}", qr.get("tone")))
    so = s["solvency"]
    out += sub("Solidez financiera")
    if so.get("intro"):
        out.append(body(so["intro"]))
        out.append(Spacer(1, 6))
    if so.get("rows"):
        out.append(P.tech_table3(so["rows"], T.CW, header=so["columns"], meaning=meaning))
        out.append(Spacer(1, 6))
    out.append(note(so["balance"]))
    rw = d["charts"]["solvency"].get("runway")
    if rw and rw.get("state") == "con_dato":
        head = " · ".join(x for x in (rw.get("years_txt"), rw.get("reading")) if x)
        out.append(bullet(_join(f"Runway: {head}" if head else "Runway", rw.get("text")), rw.get("tone")))
    for qr in so.get("quality_readings") or []:
        out.append(bullet(f"{qr['label']}. {qr['text']}", qr.get("tone")))
    g = s["growth"]
    out += sub("Crecimiento y retorno al accionista")
    if g.get("intro"):
        out.append(body(g["intro"]))
        out.append(Spacer(1, 6))
    if g.get("rows"):
        out.append(P.tech_table3(g["rows"], T.CW, header=g["columns"], meaning=meaning))
        out.append(Spacer(1, 6))
    if g.get("eps_vs_revenue_note"):
        out.append(note(g["eps_vs_revenue_note"]))
    ins = s["institutional"]
    out += sub("Modelos institucionales")
    for card in ins.get("cards") or []:
        out.append(Stack([
            Paragraph(f"<b>{esc(card['title'])}</b> · <font color='{T.TONE_TEXT[T.tone(card['tone'])].hexval()}'>"
                      f"<b>{esc(card['value'])}</b> {esc(card['subtitle'])}</font>",
                      P._ps("ict", "regular", T.BODY, leading=T.BODY_LEADING, color=T.INK)),
            body(card["body"]), Spacer(1, 6)]))
    if ins.get("piotroski_criteria"):
        out += sub("Piotroski: los nueve criterios")
        out.append(P.Piotroski(ins["piotroski_criteria"], ext.get("piotroski_values")))
    bd = ins.get("breakdown")
    if bd:
        out += sub("Desglose de la puntuación por categoría")
        out.append(note(bd["intro"] + (f" {' · '.join(bd['coverage_notes'])}." if bd.get("coverage_notes") else "")))
        out.append(Spacer(1, 4))
        rows, tones = [], []
        for cat in bd["categories"]:
            head = f"{cat['score']}/{cat['max']}" if cat.get("conclusive") else "n/c"
            rows.append([cat["name"], "", head, cat.get("text") or ""])
            tones.append(cat.get("tone") if cat.get("conclusive") else None)
            for it in cat["items"]:
                rows.append([f"   {it['metric']}", it.get("value") or "", it["sign"], it["reason"]])
                tones.append(it.get("tone"))
        out.append(P.data_table(["Indicador", "Valor", "Ajuste", "Lectura del análisis"], rows, T.CW,
                                (0.27, 0.15, 0.1, 0.48), align=["left", "right", "center", "left"],
                                tones=tones, tone_col=2))
    return out


def _valor(a, ctx):
    d = a["display"]
    v = d["sections"]["valuation"]
    out = []
    rv = v.get("reverse_dcf")
    if rv:
        out += sub(rv["title"], space_before=T.SPACE[2])
        told = lead(CHAPTERS[4], a)   # la lectura del capítulo ya cuenta las frases del DCF inverso
        for ln in rv["lines"]:
            if _dot(_cap(ln["text"].strip())) in told:
                if ln.get("label"):
                    out.append(body(f"Lectura: {ln['label'].lower()}."))
            else:
                out.append(body((f"{ln['label']}. " if ln.get("label") else "") + ln["text"]))
        out.append(note(f"{rv['role']} {rv['method']}"))
    out += sub("Múltiplos frente a la referencia")
    if v.get("intro"):
        out.append(body(v["intro"]))
        out.append(Spacer(1, 6))
    out.append(P.tech_table(v["rows"], T.CW, header=v["columns"], meaning=meaning))
    out.append(Spacer(1, 6))
    for t in (v.get("market_note"), v.get("reference_note"), v.get("normalization_note")):
        if t:
            out.append(note(t))
    iv = v["intrinsic"]
    out += sub("Valor intrínseco y Graham")
    if iv.get("intro"):
        out.append(body(iv["intro"]))
        out.append(Spacer(1, 6))
    out.append(P.tech_table3(iv["rows"], T.CW, header=["Concepto", "Valor", "Lectura"], meaning=meaning))
    out.append(Spacer(1, 6))
    if iv.get("graham_note"):
        out.append(note(iv["graham_note"]))
    out += sub("DCF: supuestos y fiabilidad")
    for t in (v.get("dcf_params"), v.get("dcf_reliability"), v.get("dcf_missing"), v.get("ke_note"),
              v.get("wacc_note")):
        if t:
            out.append(note(t))
    wb = v.get("wacc_breakdown") or []
    if wb:
        out.append(Spacer(1, 6))
        half = (len(wb) + 1) // 2
        rows = [[wb[i]["label"], wb[i]["value"], *(([wb[i + half]["label"], wb[i + half]["value"]])
                                                    if i + half < len(wb) else ["", ""])] for i in range(half)]
        out.append(Stack([P.data_table(["Coste de capital", "Valor", "", "Valor"], rows, T.CW,
                                       (0.32, 0.16, 0.36, 0.16), align=["left", "right", "left", "right"],
                                       bold_first=False)]))
    sn = v.get("sensitivity")
    if sn:
        out += sub("Escenario base y sensibilidad del valor justo")
        blk = [note(sn["intro"]), Spacer(1, 6), *P.sensitivity_grid(sn, T.CW)]
        if sn.get("note"):
            blk += [Spacer(1, 4), note(sn["note"])]
        out.append(Stack(blk))
    out.append(Spacer(1, 6))
    out.append(note("Los escenarios con tus propios supuestos (crecimiento, WACC, margen) se exploran en la web: "
                    "no cambian el veredicto."))
    return out


_PENDING = {"en_cola": "aún en cola", "analizando": "aún analizándose", "sin_dato": "sin analizar"}


def _missing(peers):
    """F10 · N5: los rivales que no están en la tabla, cada uno con su motivo."""
    out = []
    for r in peers.get("rivals") or []:
        if r.get("status") == "listo" and r.get("summary"):
            continue
        if r.get("status") == "fallo":
            why = f"no se pudo analizar ({r['reason']})" if r.get("reason") else "no se pudo analizar"
        else:
            why = _PENDING.get(r.get("status"), "sin analizar")
        out.append(f"{r['symbol']}: {why}")
    return out


def _waited(peers):
    w = peers.get("waited_s")
    return f" tras esperar {w} s" if w else ""


def _no_rivals(peers):
    """F10 · N5: por qué el informe sale sin la tabla de rivales."""
    if not peers:
        return "consulta la web: este informe se generó sin leer sus rivales"
    if not peers.get("ranked"):
        return (f"consulta la web: la clasificación de sus rivales por tamaño aún no había terminado{_waited(peers)} al "
                "generar este informe" + (f" ({peers['note']})" if peers.get("note") else ""))
    if not peers.get("rivals"):
        return peers.get("note") or "sin rivales comparables en su industria"
    return (f"consulta la web: sus rivales aún no estaban analizados{_waited(peers)} al generar este informe ("
            + "; ".join(_missing(peers)) + ")")


def _rivales(a, ctx):
    d = a["display"]
    comp = d["charts"]["comparison"]
    peers = ctx.get("peers") or {}
    ready = [r for r in peers.get("rivals") or [] if r.get("status") == "listo" and r.get("summary")]
    if ready:
        out = sub("Rivales de la misma industria", space_before=T.SPACE[2])
        keys = [it["key"] for g in comp["groups"] for it in g["items"]][:4]
        labels = {it["key"]: it["label"] for g in comp["groups"] for it in g["items"]}
        # V7 · P5: la propia empresa en la primera fila (el resumen de la caché o, si no está, el de este análisis),
        # para leer los rivales frente a ella
        import analysis_queue as AQ
        own = peers.get("company") or AQ.summary(a)
        rows, notes = [], []
        for label, sm in [(f"{own.get('name') or a.get('symbol')} ({a.get('symbol')}) · esta empresa", own)] + [
                (f"{r['summary'].get('name') or r['symbol']} ({r['symbol']})", r["summary"]) for r in ready]:
            q, p = sm.get("quality") or {}, sm.get("price_score") or {}
            mt = sm.get("metrics") or {}
            rows.append([label, f"{q.get('score', '—')} · {q.get('level') or '—'}", f"{p.get('score', '—')} · {p.get('level') or '—'}"]
                        + [(mt.get(k) or {}).get("value_txt") or "Sin dato" for k in keys])
            notes += [f"{sm.get('symbol') or label}: {mt[k]['note']}." for k in keys if (mt.get(k) or {}).get("note")]
        out.append(P.data_table(["Empresa", "Calidad", "Precio"] + [labels[k] for k in keys], rows, T.CW,
                                [0.28, 0.14, 0.14] + [0.44 / max(len(keys), 1)] * len(keys)))
        for n_ in notes:
            out.append(note(n_))
        if peers.get("note"):
            out.append(note(peers["note"]))
        miss = _missing(peers)
        if miss:
            out.append(note(f"Faltan en la tabla{_waited(peers)} al generar este informe: " + "; ".join(miss)
                            + ". La web los muestra cuando terminan."))
    else:
        out = absent("Rivales de la misma industria", _no_rivals(ctx.get("peers")), space_before=T.SPACE[2])
    out += sub("Frente al agregado de su referencia")   # V7 · P5: Damodaran publica agregados de la industria, no medianas
    out.append(body(f"Mejor que la referencia en {comp['better']} de {comp['total']} métricas."))
    rows, tones = [], []
    for g in comp["groups"]:
        for it in g["items"]:
            rows.append([f"{it['label']}", it.get("value_txt") or "—", it.get("bench_txt") or "—",
                         it.get("gap_txt") or "—", it.get("reading") or ""])
            tones.append(it.get("tone"))
    if rows:
        out.append(P.data_table(["Métrica", "Empresa", "Referencia", "Brecha", "Lectura"], rows, T.CW,
                                (0.3, 0.15, 0.15, 0.13, 0.27), align=["left", "right", "right", "right", "left"],
                                tones=tones, tone_col=4))
        out.append(Spacer(1, 4))
    for t in (comp.get("note"), comp.get("market_note")):
        if t:
            out.append(note(t))
    return out


def _riesgos(a, ctx):
    d = a["display"]
    s, cover = d["sections"], d["cover"]
    conf = d.get("confidence") or {}
    out = []
    pm = s["valuation"].get("premortem")
    if pm:
        out += sub(pm["title"], space_before=T.SPACE[2])
        for it in pm["items"]:
            out.append(bullet(_cap(it)))
        out.append(note(pm["note"]))
    al = s["alerts"]
    ct = al["counts"]
    out += sub("Alertas y señales")
    plural = lambda n, w: f"{n} {w}{'s' if n != 1 else ''}"  # noqa: E731
    unm = f" ({ct['unmeasured']})" if ct.get("unmeasured") else ""   # F9 · R6: banco sin el crédito medido
    out.append(body(f"{plural(ct['red_flags'], 'riesgo')}{unm} · {plural(ct['warnings'], 'advertencia')} · "
                    f"{plural(ct['strengths'], 'fortaleza')}."))
    any_items = False
    for grp in al["groups"]:
        if not grp["items"]:
            continue
        any_items = True
        # el rótulo del grupo no queda solo al pie: pasa con (al menos) las dos primeras líneas de su primer aviso
        out.append(CondPageBreak(T.BODY_LEADING + 2 * (T.TABLE_LEADING + 1) + 4))
        out.append(Paragraph(f"<font color='{T.TONE_TEXT[T.tone(grp['tone'])].hexval()}'><b>{esc(grp['title'])}</b>"
                             f"</font>", P._ps("agt", "semibold", T.BODY, leading=T.BODY_LEADING, color=T.INK)))
        for it in grp["items"]:
            txt = f"<b>{esc(it['category'])}: {esc(it['reason'])}</b>" + \
                  (f"<br/><font color='{T.TEXT_3.hexval()}'>{esc(it['detail'])}</font>" if it.get("detail") else "")
            st = P._ps("ait", "regular", T.TABLE, leading=T.TABLE_LEADING + 1, color=T.INK)
            st.leftIndent, st.spaceAfter = 12, 4
            out.append(Paragraph(txt, st))
    if not any_items:
        out.append(body("No se detectaron alertas significativas."))
    out += sub("Lo que no sabemos: la confianza del veredicto")
    if conf:
        out.append(body(conf["summary"]))
        out.append(Spacer(1, 6))
        out.append(Stack([P.data_table(["Dimensión", "Nivel", "Motivo"],
                                       [[x["label"], x["level"], x["text"]] for x in conf["dimensions"]],
                                       T.CW, (0.28, 0.12, 0.6), align=["left", "center", "left"])]))
        for t in conf.get("plain") or []:
            out.append(bullet(t, "warn"))
    for t in cover.get("coverage_notes") or []:
        out.append(bullet(f"Cobertura parcial: {t}", "warn"))
    return out


def _actualidad(a, ctx):
    d = a["display"]
    mk = d["sections"].get("market") or {}
    ext = d.get("extended") or {}
    news = ext.get("news") or mk.get("news") or []
    if news:
        out = sub("Noticias", space_before=T.SPACE[2])
        for n in news:
            meta = " · ".join(x for x in (n.get("date"), n.get("source"),
                                          "en inglés" if (n.get("lang") or "").lower().startswith("en") else None) if x)
            st = P._ps("nw", "semibold", T.BODY, leading=T.BODY_LEADING, color=T.INK)
            st.spaceAfter = 1
            out.append(Paragraph(link(n["headline"], n.get("url")), st))
            out.append(Paragraph(esc(meta) + (f" — {esc(n['summary'])}" if n.get("summary") else ""),
                                 P._ps("nwm", "regular", T.SMALL, leading=T.SMALL_LEADING, color=T.TEXT_3)))
            out.append(Spacer(1, 6))
        if mk.get("news_note"):
            out.append(note(mk["news_note"]))
    else:
        out = absent("Noticias", "sin noticias recientes" + (f": {mk['news_note']}" if mk.get("news_note") else ""),
                     space_before=T.SPACE[2])
    ne = ext.get("next_earnings") or {}
    if ne.get("status") == "ok" and ne.get("date_txt"):
        out += sub("Próximos resultados")
        out.append(body(f"{ne['date_txt']} ({ne.get('kind') or 'fecha'})." + (f" {ne['basis']}" if ne.get("basis") else "")))
    else:
        out += absent("Próximos resultados", "sin fecha anunciada: " + (
            ne.get("reason") or "el análisis aún no trae el calendario de resultados"))
    if mk.get("pead_note"):
        out.append(note(mk["pead_note"]))
    if mk.get("behavioral"):
        out += sub(mk.get("behavioral_title") or "Lectura conductual del mercado")
        for t in mk["behavioral"]:
            out.append(bullet(t))
    return out


def _conclusion(a, ctx):
    d = a["display"]
    cover, comp = d["cover"], d["summary"]["composition"]
    conf = d.get("confidence") or {}
    out = sub("Composición de las dos puntuaciones", space_before=T.SPACE[2])
    rows = []
    for blk in (comp["quality"], comp["price"]):
        rows.append((f"{blk['title'].capitalize()}", (blk["score"] or 0) / 100 if blk["score"] is not None else None,
                     f"{blk['score'] if blk['score'] is not None else '—'}/100 · {blk.get('level') or 'sin dato'}",
                     blk.get("tone")))
        for r in blk["rows"]:
            if r["kind"] == "signed":
                rows.append((f"   {r['label']}", abs(r["value"]) / comp["price"]["signed_max"],
                             f"{r['value']:+d}".replace("-", "−"), r.get("tone")))
            elif r["kind"] == "nc":
                rows.append((f"   {r['label']}", None, "no concluyente", None))
            else:
                rows.append((f"   {r['label']}", r["pct"] / 100, f"{r['value']}/{r['max']}", r.get("tone")))
    ac = d["summary"]["alert_counts"]
    out.append(Stack([P.BarList(rows, value_w=130), Spacer(1, 4), note(comp["caption"]),
                      note(f"{ac['strengths']} fortalezas · {ac['warnings']} advertencias · "
                           f"{ac['red_flags']} riesgos"
                           + (f" ({ac['unmeasured']})." if ac.get("unmeasured") else "."))]))
    out += sub("Qué vigilar")
    for h in cover.get("highlights") or []:
        out.append(bullet(f"{_cap(h['kicker'].lower())}: {h['text']}", h.get("tone")))
    for t in conf.get("plain") or []:
        out.append(bullet(f"Confianza: {t}", "warn"))
    return out


BUILDERS = {"empresa": _empresa, "negocio": _negocio, "accion": _accion, "calidad": _calidad, "valor": _valor,
            "rivales": _rivales, "riesgos": _riesgos, "actualidad": _actualidad, "conclusion": _conclusion}


def heading_block(key, eyebrow, title, toc, space_before=T.SPACE[4], new_page=False) -> list:
    """Título de capítulo: si no caben él y unas líneas de lectura, empieza en la página siguiente. Con `new_page`,
    siempre en una página nueva (y lo declara: ver ChapterHeading)."""
    h = ChapterHeading(key, eyebrow, title, toc, space_before=space_before, new_page=new_page)
    return [PageBreak(), h] if new_page else [CondPageBreak(space_before + 40 + _keep() * T.BODY_LEADING), h]


def chapters(a: Dict[str, Any], ctx: Optional[Dict[str, Any]] = None) -> list:
    """Los nueve capítulos seguidos (sin páginas a medio llenar). `ctx`: datos fuera del análisis (prices,
    segments, peers), cada uno opcional."""
    ctx = ctx or {}
    out = []
    for i, ch in enumerate(CHAPTERS, 1):
        out += heading_block(chapter_key(ch), toc_text(i, ch), ch.title(a), toc_text(i, ch))
        out.append(body(lead(ch, a, ctx)))
        out += floated(BUILDERS[ch.id](a, ctx))
    return out
