"""
Capa de presentación compartida (etapa 9b)
==========================================
El PDF y la web dicen exactamente lo mismo: todo lo que se LEE de una métrica
(estado, lectura, tono, frase), las métricas de portada por arquetipo, la
fortaleza clave / a vigilar / contexto, las filas de cada sección y los textos
se calculan UNA vez aquí, a partir del análisis, y se exponen en el JSON como
`display`. lib/pdf_report.py solo maqueta este bloque; el frontend solo lo pinta.

Estados de una fila (STATES): con_dato, sin_dato, no_aplica, no_significativo.
Tonos: pos, neg, warn, neu (None = sin lectura coloreada).

Uso: build_display(analysis, sector_bench) -> dict serializable a JSON.
"""
import math
import re
from typing import Any, Dict, Optional

from settings import cfg
from financial_ratios import IC_NEGATIVE, NET_CASH_TEXT, SECTOR_THRESHOLDS, ThresholdConfig, growth_for_bands
from classify import archetype_label, not_applicable_text
import numfmt
from numfmt import money as _money, price as _price
from plain_language import confidence_reasons, plain_reasons, translate as _plain_reason
from claims import active as _claims_active, claim as _claim, declares as _declares, record as _record

_PDF_BANDS = cfg("thresholds.pdf")  # bandas de las lecturas del informe
DE_NOT_APPLICABLE = "No aplica a entidades financieras"
DCF_NO_RECONCILE = ("El DCF no concilia con el precio bajo ningún supuesto razonable; "
                    "no se usa en el score")

STATES = ("con_dato", "sin_dato", "no_aplica", "no_significativo")
STATE_LABELS = {"con_dato": "Con dato", "sin_dato": "Sin dato", "no_aplica": "No aplica",
                "no_significativo": "No significativo"}
ARCHETYPES = ("FINANCIAL", "REIT", "UTILITY", "GROWTH_PRE_PROFIT", "CYCLICAL", "GROWTH_PROFITABLE", "MATURE")

# ══════════════════════ NARRATIVA ADAPTATIVA (bandas) ══════════════════════
# Cada lector devuelve (etiqueta_corta, tono, frase) o None si no hay dato.
# tono ∈ {pos, neg, warn, neu} → color en tablas y acentos del texto.

def _rec(r, *cl):
    """Fase 1 (guardián narrativo): declara las afirmaciones de una lectura (etiqueta y frase). Sin efecto en la
    salida; solo registra si hay un colector activo (tests)."""
    if r is not None and _claims_active():
        _record(r[0], *cl, source="display.lectura")
        _record(r[2], *cl, source="display.lectura")
    return r


_COV_METRICS = ("Cobertura Intereses", "Cobertura de intereses")


def _metric_claims(a, metric):
    """Fase 1 (guardián): afirmaciones que hace un texto del desglose según su métrica."""
    km, arch = a.get("key_metrics") or {}, (a.get("classification") or {}).get("archetype")
    m = str(metric or "")
    if m in _COV_METRICS:
        st = km.get("interest_coverage_state")
        cl = [_claim("coverage", state=st)] + ([_claim("no_interest_burden")] if st == "sin_carga" else [])
        if st in ("negativa", "no_significativo"):
            cl += [_claim("ebit_negative"), _claim("net_debt" if st == "negativa" else "net_cash")]
        return cl
    if m.startswith("Deuda neta"):
        nd = km.get("net_debt")
        return [] if nd is None else [_claim("net_cash" if nd < 0 else "net_debt")]
    if m.startswith("Deuda/Equity") and (km.get("net_debt") or 0) < 0:
        # El D/E con caja neta no puntúa y el motivo lo dice ("no significativo con caja neta").
        return [_claim("net_cash", field="key_metrics.net_debt"), _claim("vs_bench")]
    if "ROIC" in m and "WACC" in m:
        return [_claim("spread")]
    if m.startswith("DCF"):
        return [_claim("dcf_upside"), _claim("dcf_rel")]
    if m.startswith("Altman"):
        return [_claim("altman_zone")]
    if m.startswith("Runway"):
        return [_claim("runway")]
    if m.startswith("Mejora"):            # "+27.8 pp interanual": variación de un año a otro
        return [_claim("basis", per="interanual", metric=m)]
    if m.startswith(("Crecimiento", "Retorno total")):
        bd = ((a.get("score") or {}).get("breakdown") or {}).get("Crecimiento") or {}
        adj = next((x for x in bd.get("adjustments") or [] if x.get("metric") == m), {})
        return [_claim("growth", field=f"score.breakdown.Crecimiento[{m}].raw", value=adj.get("raw"),
                       cycle=arch == "CYCLICAL", cagr=arch != "CYCLICAL", what=m)]
    return [_claim("vs_bench")]


def _declare_engine_texts(a, D):
    """Fase 1 (guardián narrativo): declara las afirmaciones de los textos del motor que `display` pasa al
    informe (desglose, tarjetas institucionales, nota del WACC, confianza, filas y etiquetas). Sin efecto en la
    salida: solo registra con un colector activo."""
    km = a.get("key_metrics") or {}
    S = D.get("sections") or {}
    for cat in ((S.get("institutional") or {}).get("breakdown") or {}).get("categories") or []:
        for it in cat.get("items") or []:
            cl = _metric_claims(a, it.get("metric"))
            _record(it.get("reason"), *cl, source="display.desglose")
            _record(it.get("value"), *cl, source="display.desglose")
    alt = a.get("altman_z") or {}
    for c in (S.get("institutional") or {}).get("cards") or []:
        if c.get("key") == "altman":
            for k in ("subtitle", "body", "value"):
                _record(c.get(k), _claim("altman_zone"), source="display.institucional")
    ro = ((D.get("charts") or {}).get("profitability") or {}).get("roce") or {}   # fase 1 (punto 9)
    for k, fld in (("label", "roce"), ("value_txt", "roce")):
        _record(ro.get(k), _claim("roce", field=f"key_metrics.{fld}"), source="display.charts")
    for k in ("label", "value_txt"):
        _record((ro.get("avg") or {}).get(k), _claim("roce", field="key_metrics.roce_avg"), source="display.charts")
    al = ((D.get("charts") or {}).get("institutional") or {}).get("altman") or {}
    for k in ("zone", "text"):
        _record(al.get(k), _claim("altman_zone"), source="display.charts")
    if alt.get("z_score") is not None:
        _zm = {"safe": "zona segura", "grey": "zona gris", "distress": "zona de riesgo"}
        _record(f"Altman Z de {alt['z_score']:.2f} ({_zm.get(alt.get('zone'), '')})", _claim("altman_zone"),
                source="display.resumen")
    # Nota del WACC: el rating sintético cita la regla M ("EBIT < 0 con caja neta / deuda neta").
    flag = str(((a.get("wacc") or {}).get("rating") or {}).get("flag") or "")
    wcl = []
    if "EBIT < 0" in flag:
        wcl = [_claim("ebit_negative"), _claim("net_cash" if "caja neta" in flag else "net_debt")]
    V = S.get("valuation") or {}
    _record(V.get("wacc_note"), *wcl, source="display.wacc")
    _record(flag, *wcl, source="display.wacc")
    _record(V.get("dcf_reliability"), _claim("dcf_rel"), source="display.dcf")
    # Confianza: fiabilidad del DCF citada y contracción del precio.
    pa, C = a.get("price_attractiveness") or {}, D.get("confidence") or {}
    ccl = [_claim("dcf_rel"), _claim("price_contraction", raw=pa.get("score_raw"), score=pa.get("score"),
                                     confidence=pa.get("confidence"), factor=pa.get("factor"))]
    for d in C.get("dimensions") or []:
        _record(d.get("text"), *ccl, source="display.confianza")
    for r in C.get("reasons") or []:
        _record(r.get("detail"), *ccl, source="display.confianza")
    _record(C.get("summary"), *ccl, source="display.confianza")
    # Filas con estado propio (cobertura, runway, deuda neta/EBITDA) y etiquetas con base temporal.
    rcl = {"interest_coverage": _metric_claims(a, "Cobertura Intereses"), "runway": [_claim("runway")],
           "roce": [_claim("roce", field="key_metrics.roce")], "roce_avg": [_claim("roce", field="key_metrics.roce_avg")],
           "net_debt_to_ebitda": _metric_claims(a, "Deuda neta/EBITDA")}
    for sec in ("solvency", "growth", "profitability", "valuation"):
        for r in (S.get(sec) or {}).get("rows") or []:
            cl = list(rcl.get(r.get("key"), []))
            lab = str(r.get("label") or "")
            if "(interanual)" in lab or " interanual" in str(r.get("text") or ""):
                cl.append(_claim("basis", per="interanual", metric=r.get("key")))
            if "(último ejercicio)" in lab:                 # fase 2b (T7): FY0 frente a FY1 de los estados
                cl.append(_claim("basis", per="último ejercicio", metric=r.get("key")))
            if "(3 años)" in lab:
                cl.append(_claim("basis", per="3 años", metric=r.get("key")))
            for k in ("label", "value", "reading", "text"):
                _record(r.get(k), *cl, source=f"display.{sec}")
    for c in (D.get("summary") or {}).get("cards") or []:
        if "(3 años)" in str(c.get("label")):
            _record(c.get("label"), _claim("basis", per="3 años", metric=c.get("key")), source="display.tarjetas")
    for g in ((D.get("charts") or {}).get("comparison") or {}).get("groups") or []:
        for it in g.get("items") or []:
            if "(3 años)" in str(it.get("label")):
                _record(it.get("label"), _claim("basis", per="3 años", metric=it.get("key")), source="display.charts")
    pio = (S.get("institutional") or {}).get("piotroski_criteria") or []
    for c in pio:
        for k in ("label", "detail"):
            _record(c.get(k), _claim("piotroski", criterion=c.get("label"), state=c.get("state")),
                    source="display.piotroski")
    cls = a.get("classification") or {}
    inp = cls.get("inputs") or {}
    for t in (D.get("cover") or {}).get("classification_notes") or []:
        _record(t, _claim("archetype", value=cls.get("archetype")),
                _claim("growth", field="classification.inputs.revenue_cagr_3y", value=inp.get("revenue_cagr_3y"),
                       cagr=True, what="ingresos"), source="display.clasificacion")
    ev = a.get("eps_vs_revenue_growth") or {}
    if ev:
        ecl = [_claim("eps_vs_revenue", eps=ev.get("eps_growth"), revenue=ev.get("revenue_growth"),
                      state=ev.get("state"))]
        G = S.get("growth") or {}
        _record(G.get("eps_vs_revenue_note"), *ecl, source="display.crecimiento")
        for r in G.get("rows") or []:
            if str(r.get("text") or "").lower().startswith("el bpa crece"):
                _record(r.get("text"), *ecl, source="display.crecimiento")


def _pct(v, dec=1):
    return f"{v * 100:.{dec}f}%"


def _vs_claims(name, val, bench, higher_better, fmt="mult", ref="del sector", result=None):
    return [_claim("vs_bench", metric=name, value=val, bench=bench, ref=ref, higher_better=higher_better),
            *([_claim("basis", per="3 años", metric=name)] if "(3 años)" in str(name) else [])]


@_declares(_vs_claims, source="display.read_vs_sector")
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


def read_current(cr, bm=None):
    if cr is None: return None
    bm = bm or {}
    if bm.get("applies"):
        # Fase 3 (T6, §5): circulante negativo estructural de la industria.
        h = f" (mediana de sus ejercicios anteriores {bm['median_prior']:.2f}x)" if bm.get("median_prior") else ""
        return ("Estructural", 'neu', f"el current ratio de {cr:.2f}x es normal en un negocio que cobra antes de "
                                      f"pagar: no empeora frente a su historia{h}")
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


def read_coverage(ic, state=None, utility=False):
    # Etapa 5: EBIT < 0 con caja neta -> no significativa; con deuda neta ->
    # riesgo, sin presentar la cifra negativa como si fuera una cobertura.
    if state == "sin_carga":   # fase 1: EBIT > 0 e ingresos financieros netos
        return ("Sin carga financiera", 'pos', "sin carga financiera neta: los ingresos financieros cubren los "
                "gastos financieros y el resultado operativo es positivo")
    if state == "no_significativo":
        return ("No significativa", 'neu', "con EBIT negativo y caja neta, la cobertura de intereses no es "
                "significativa: los intereses se pagan con caja")
    if ic is None: return None
    if state == "negativa":
        return ("Riesgo", 'neg', "el resultado operativo es negativo (EBIT < 0) y la empresa tiene deuda neta: "
                "los intereses no se cubren con el negocio")
    if utility:   # etapa 11b: bandas de utility regulada del score (utility_coverage_*)
        b = cfg("thresholds.score.solidez.utility_coverage_bounds")
        if ic >= b[0]: return ("Fuerte", 'pos', f"la cobertura de intereses ({ic:.1f}x) es fuerte para una utility "
                                               "regulada")
        if ic >= b[1]: return ("Adecuada", 'pos', f"la cobertura de intereses ({ic:.1f}x) es adecuada para una utility "
                                                  "regulada")
        if ic >= b[2]: return ("En línea", 'neu', f"la cobertura de intereses ({ic:.1f}x) está en línea con las "
                                                  "utilities reguladas")
        if ic >= b[3]: return ("Ajustada", 'warn', f"la cobertura de intereses ({ic:.1f}x) es ajustada incluso para "
                                                   "una utility")
        return ("Riesgo", 'neg', f"la cobertura de intereses ({ic:.1f}x) es baja incluso para una utility regulada")
    b = cfg("thresholds.score.solidez.coverage_bounds")   # las del score
    if ic >= b[0]:  return ("Muy holgada", 'pos', f"la deuda es fácilmente servible: cobertura de intereses de {ic:.1f}x")
    if ic >= b[1]:  return ("Sólida", 'pos', f"el beneficio operativo cubre {ic:.1f} veces el gasto por intereses")
    if ic >= b[2]:  return ("Aceptable", 'neu', f"la cobertura de intereses ({ic:.1f}x) es aceptable")
    if ic >= b[3]:  return ("Justa", 'warn', f"la cobertura de intereses ({ic:.1f}x) deja poco margen ante caídas del beneficio operativo")
    return ("Crítica", 'neg', f"la cobertura de intereses ({ic:.1f}x) es críticamente baja")


def _fx_txt(rate: float, fin: str, px: str) -> str:
    """Tipo de cambio legible: "1 USD = 31.87 TWD" o "1 EUR = 1.1665 USD"."""
    return f"1 {px} = {1 / rate:,.2f} {fin}" if rate < 1 else f"1 {fin} = {rate:,.4f} {px}"


def currency_note(cur) -> Optional[str]:
    """Etapa 11b: qué se reexpresó para poner los estados en la unidad del precio."""
    if not cur:
        return None
    parts = []
    fin, px = cur.get("statements"), cur.get("price")
    if cur.get("converted") and fin and px:
        rates = []
        if cur.get("ttm_rate"):
            rates.append(f"TTM: {_fx_txt(cur['ttm_rate'], fin, px)}")
        br = cur.get("balance_rate") or {}
        if br.get("rate"):
            rates.append(f"balance al {br['date']}: {_fx_txt(br['rate'], fin, px)}")
        parts.append(f"Estados financieros en {fin} convertidos a {px}, la moneda de la cotización, con el tipo de "
                     f"cambio de Yahoo ({', '.join(cur.get('fx_symbols') or [])}): el balance al cierre de cada período "
                     "y los resultados y flujos al promedio del período"
                     + (f" ({'; '.join(rates)})" if rates else "") + ".")
    sc = cur.get("share_class") or {}
    f = sc.get("factor")
    basis = sc.get("basis")
    if sc.get("applied") and f:
        off = sc.get("official") or {}
        if basis == "oficial":
            dep = off.get("depositary")
            if off.get("origin") == "portada_20f":
                who = f"factor de la portada del {off.get('source', '').split(' (')[0] or '20-F'} en SEC EDGAR"
            else:
                who = f"factor del depositario, {dep}" if dep and dep != "—" else "factor oficial del emisor"
            parts.append("Cifras por acción en la clase que cotiza: "
                         + (f"cada título cotizado equivale a {f:,.0f} {off.get('share_class') or 'acciones'} "
                            f"({who})." if f > 1 else
                            f"cada título cotizado equivale a {f:g} {off.get('share_class') or 'acciones'} ({who})."
                            if off.get("adr") else
                            f"los estados cuentan otra clase de acciones, y cada una equivale a {1 / f:,.0f} "
                            f"títulos cotizados ({who})."))
        else:
            parts.append("Cifras por acción en la clase que cotiza: "
                         + (f"cada título cotizado equivale a {f:,.2f} acciones de los estados"
                            if f > 1 else
                            f"los estados cuentan otra clase de acciones, y cada una equivale a {1 / f:,.0f} "
                            "títulos cotizados")
                         + " (factor deducido de las acciones, sin verificar con el depositario).")
    gap = sc.get("implied_check") or {}
    if gap.get("deviation") is not None and sc.get("statement_shares_date"):
        dev = gap["deviation"]
        change = 1.0 / (1.0 + dev) - 1.0       # acciones de hoy frente a las del balance
        parts.append(f"Desde el balance del {sc['statement_shares_date']} la empresa tiene un {abs(change):.1%} "
                     f"{'menos' if change < 0 else 'más'} de acciones "
                     f"({'recompras' if change < 0 else 'emisiones'}); el valor por acción usa las de hoy.")
    return " ".join(parts) or None


BANK_LEVERAGE_NA = ("En un banco la deuda (subordinada, depósitos y emisiones) es parte del negocio: su "
                    "apalancamiento se mide con capital, no con esta ratio.")
PENDING_RESULTS_TEXT = "La empresa publicó resultados el {date}; este análisis aún no los incorpora"


def as_of_note(ao) -> Optional[str]:
    """Fase 2b (T3): de qué fecha son los estados del análisis."""
    if not ao or not ao.get("date"):
        return None
    d = numfmt.date_long(ao["date"])
    if ao.get("type") == "ttm":
        return f"Estados financieros a {d} (últimos doce meses)."
    if ao.get("type") == "fy":
        return f"Estados financieros del ejercicio cerrado el {d} (sin trimestres completos más recientes)."
    return None


def data_notices(a) -> list:
    """Fase 2b (T3): avisos de datos de la portada (PDF) y de la cabecera (web)."""
    out = []
    pr = (a.get("data_provenance") or {}).get("pending_results")
    if pr and pr.get("date"):
        txt = PENDING_RESULTS_TEXT.format(date=numfmt.date_long(pr["date"]))
        if pr.get("form") is None:
            txt += " (según el calendario de resultados)"
        out.append(txt + ".")
    gone = [f for f in a.get("data_validation") or [] if f.get("rule") == "periodo_incoherente"
            and f.get("action") == "sin_dato"]
    if gone:
        names = sorted({_FIELD_NAMES.get(f["field"], f["field"]) for f in gone})
        out.append("Sin dato del corte, descartados por ser de otro periodo: " + ", ".join(names) + ".")
    # Fase 2b (T4, D7): emisor sin estados en la SEC: aviso literal de F2_PRECEDENCIA §4.
    off = (a.get("data_provenance") or {}).get("official_source") or {}
    if off.get("registered") is False and off.get("note"):
        out.append(off["note"])
    return out


def beta_text(adjusted: Optional[float], raw: Optional[float], source: Optional[str]) -> str:
    """Fase 2b (T6): qué beta entra en el Ke y de dónde sale (lib/beta.py)."""
    adj = f"{adjusted:.2f}" if adjusted is not None else "—"
    if source == "sector":
        return f"β del sector {adj} [Damodaran, enero de 2026; sin Blume: es una media de industria]"
    rw = f"{raw:.2f}" if raw is not None else "—"
    who = {"propia": "propia, 2 años semanales frente al S&P 500", "fuente": "de la fuente, sin verificar"}.get(
        source, "de la fuente")
    return f"β ajustada {adj} [bruta {rw}, {who}, Blume]"


def official_source_badge(a) -> Optional[dict]:
    """Fase 2b (D7): insignia de la cabecera web junto a la confianza, con el aviso como tooltip."""
    off = (a.get("data_provenance") or {}).get("official_source") or {}
    if off.get("registered") is False:
        return {"label": "Sin fuente oficial", "tooltip": off.get("note")}
    return None


EBIT_ESTIMATED_SUFFIX = " (estimado por la fuente)"


def ebit_estimated(a) -> Optional[dict]:
    """F2_PRECEDENCIA §2.1: el beneficio operativo de la fuente difiere del que presenta el emisor en EDGAR (> 2%)."""
    e = (a.get("data_provenance") or {}).get("ebit") or {}
    return e if e.get("status") == "estimado" else None


def official_source_annex(a) -> list:
    """Fase 2b (T4): filas del anexo técnico: fuente oficial (D7) y campos respaldados con SEC EDGAR."""
    dp = a.get("data_provenance") or {}
    off = dp.get("official_source") or {}
    items = []
    eb = ebit_estimated(a)
    if eb:
        items.append({"label": "Beneficio operativo", "text": (
            f"estimado por la fuente: el del proveedor de datos difiere un {eb['diff']:+.1%} del que presenta el emisor "
            f"en SEC EDGAR ({eb['concept']}, {fv(eb['edgar_value'], 'money')} en los doce meses al "
            f"{eb['period_end']}). Se usa el del proveedor (D2) y se marca." if eb.get("diff") is not None else
            "estimado por la fuente: EDGAR no da una cifra comparable.")})
    if off:
        if off.get("registered") is False:
            txt = f"no. {off.get('note')} Motivo: {off.get('reason')}."
        elif off.get("registered") is None:
            txt = f"{off.get('note') or 'verificación oficial no disponible'} ({off.get('reason')})."
        else:
            txt = (f"sí, SEC EDGAR (CIK {off.get('cik')}); último ejercicio en EDGAR: FY {off.get('fy')}"
                   + (f" ({off.get('note')})" if off.get("note") else "") + ".")
        items.append({"label": "Fuente oficial", "text": txt})
    dt = dp.get("debt") or {}
    if dt:
        names = {"borrowings": "préstamos y bonos", "commercial_paper": "papel comercial (dentro de los préstamos)",
                 "finance_leases": "arrendamiento financiero", "operating_leases": "arrendamiento operativo",
                 "leases_in_source_total": "arrendamientos que la fuente sumaba", "leases_ifrs16": "arrendamientos IFRS 16",
                 "subordinated": "deuda subordinada", "captive": "financiera cautiva"}
        parts = []
        for k, c in (dt.get("components") or {}).items():
            if c.get("value") is None:
                continue
            txt = f"{names.get(k, k)} {numfmt.money(c['value'])} ({'dentro' if c.get('in_rule_debt') else 'fuera'}"
            if c.get("note"):
                txt += f"; {c['note']}"
            parts.append(txt + ")")
        head = (f"deuda de la regla {numfmt.money(dt['total'])} (la fuente daba {numfmt.money(dt['source_total'])})"
                if dt.get("applied") else
                (f"deuda {numfmt.money(dt['total'])}" if dt.get("total") is not None else "sin deuda total"))
        items.append({"label": "Deuda coherente con el EBITDA (arrendamiento dentro solo si su coste no está en el "
                               "EBITDA)",
                      "text": "; ".join([head] + parts + list(dt.get("notes") or [])) + "."})
    bk = (dp.get("edgar") or {}).get("backup") or {}
    rows = [f"{_FIELD_NAMES.get(x['field'], x['field'])} ({x['concept']}; {x['how']})" for x in bk.get("cut") or []]
    rows += [f"{_fy_field_name(x['field'])} del ejercicio cerrado el {x['fy_end']} ({x['concept']})"
             for x in bk.get("fy") or []]
    if rows:
        items.append({"label": "Respaldo de SEC EDGAR (lo que Yahoo no da del mismo corte)",
                      "text": "; ".join(rows) + "."})
    return items


# Fase 6 (PLAN §4: "registro de qué fuente aportó cada campo: exponerlo en el anexo").
_SOURCE_NAMES = (("yfinance_statements", "estados de Yahoo (yfinance)"), ("sec_edgar", "SEC EDGAR"),
                 ("finnhub", "Finnhub"), ("yahoo_quotesummary", "Yahoo (cotización y perfil)"),
                 ("derivado", "calculados con otros datos del análisis"),
                 ("politica_arquetipo", "fijados por la regla del arquetipo"),
                 ("sin_dato", "sin dato utilizable (ausente o de otro periodo)"))
_COUNT_ONLY = {"yfinance_statements", "derivado"}
_PROV_MAX_NAMES = 8


def provenance_annex(a) -> Optional[Dict[str, str]]:
    """Fila del anexo técnico: campos del análisis por fuente. El mismo dato en varias rutas internas (p. ej.
    `forwardPE` y `_yahoo_ratios.forwardPE`) cuenta una vez, con la fuente de la última ruta registrada."""
    fields = (a.get("data_provenance") or {}).get("fields") or {}
    by_src: Dict[str, Dict[str, None]] = {}
    for k, v in fields.items():
        leaf = str(k).rsplit(".", 1)[-1]
        by_src.setdefault(str((v or {}).get("source")), {})[leaf] = None
    if not by_src:
        return None
    known = [c for c, _ in _SOURCE_NAMES]
    parts = []
    for code in known + sorted(c for c in by_src if c not in known):
        names = list(by_src.get(code) or ())
        if not names:
            continue
        label = dict(_SOURCE_NAMES).get(code, code)
        if code in _COUNT_ONLY:
            parts.append(f"{label}: {len(names)} campos")
            continue
        shown = [_FIELD_NAMES.get(n) or _MORE_FIELD_NAMES.get(n) or n for n in names[:_PROV_MAX_NAMES]]
        rest = len(names) - len(shown)
        parts.append(f"{label}: {len(names)} ({', '.join(shown)}{f' y {rest} más' if rest else ''})")
    return {"label": "Procedencia de los datos (campos del análisis por fuente)", "text": "; ".join(parts) + "."}


_MORE_FIELD_NAMES = {
    "forwardPE": "P/E adelantado", "forwardEps": "BPA estimado", "pegRatio": "PEG", "currentRatio": "liquidez corriente",
    "current_ratio": "liquidez corriente", "quickRatio": "prueba ácida", "interestCoverage": "cobertura de intereses",
    "interest_coverage": "cobertura de intereses", "payoutRatio": "payout", "inventoryTurnover": "rotación de existencias",
    "dividendRate": "dividendo por acción", "dividendYield": "rentabilidad por dividendo", "totalCash": "caja total",
    "beta": "beta", "industry": "industria", "sector": "sector", "revenueGrowth": "crecimiento de ingresos",
    "earningsGrowth": "crecimiento del beneficio", "capitalLeaseObligations": "arrendamiento financiero",
    "commercialPaper": "papel comercial", "ltd": "deuda a largo plazo", "gross_margin": "margen bruto",
    "asset_turnover": "rotación del activo", "pe": "P/E", "ev_ebitda": "EV/EBITDA",
    "net_debt_to_ebitda": "deuda neta/EBITDA", "p_ffo": "P/FFO", "de": "deuda/patrimonio",
    "debt_to_assets": "deuda/activo", "enterprise_value": "valor de empresa", "ev_revenue": "EV/ventas",
    "net_debt": "deuda neta", "long_term_debt": "deuda a largo plazo",
}


def _fy_field_name(field: str) -> str:
    """`FY.retained_earnings` -> "beneficios retenidos" (antes salía el código: "ejercicio a retained_earnings")."""
    key = str(field).split(".", 1)[-1]
    return _FY_FIELD_NAMES.get(key) or _FIELD_NAMES.get(key) or _MORE_FIELD_NAMES.get(key) or key


_FY_FIELD_NAMES = {"retained_earnings": "beneficios retenidos", "total_liabilities": "pasivo total",
                   "total_assets": "activo", "revenue": "ingresos", "net_income": "beneficio neto",
                   "operating_income": "beneficio operativo", "operating_cash_flow": "flujo de operaciones",
                   "capex": "inversión (capex)", "depreciation": "amortizaciones", "total_debt": "deuda total",
                   "stockholders_equity": "patrimonio", "current_assets": "activo corriente",
                   "current_liabilities": "pasivo corriente", "gross_profit": "beneficio bruto",
                   "interest_expense": "gastos financieros", "shares": "acciones"}


_FIELD_NAMES = {
    "totalRevenue": "ingresos", "grossProfits": "beneficio bruto", "operatingIncome": "beneficio operativo",
    "netIncome": "beneficio neto", "ebitda": "EBITDA", "interestExpense": "gastos financieros",
    "netInterestIncome": "resultado financiero", "depreciation": "amortizaciones",
    "operatingCashflow": "flujo de operaciones", "capitalExpenditures": "inversión (capex)",
    "freeCashflow": "flujo de caja libre", "dividendsPaid": "dividendos pagados",
    "stockBasedCompensation": "pagos en acciones", "totalAssets": "activo", "totalCurrentAssets": "activo corriente",
    "totalCurrentLiabilities": "pasivo corriente", "totalDebt": "deuda total", "longTermDebt": "deuda a largo plazo",
    "totalStockholderEquity": "patrimonio", "totalLiab": "pasivo", "retainedEarnings": "beneficios retenidos",
    "inventory": "existencias", "cash": "caja",
}


def dividend_text(d) -> Optional[str]:
    """Fase 2b (T2): qué dividendo indicado hay detrás del yield y lo que encontró el control en los dos sentidos."""
    if not d or d.get("rate") in (None, 0.0):
        return None
    how = {"pagos": ("suma de los pagos ordinarios del último año" if d.get("basis") == "suma_ultimo_ciclo"
                     else "último pago ordinario por su frecuencia"),
           "fuente_local_convertida": "dividendo de la cotización local convertido a la del precio"}.get(
        d.get("source"), "último dividendo declarado por su frecuencia")
    cur = d.get("currency") or "USD"
    parts = [f"{_num_txt(d['rate'])} {cur} al año por {d.get('unit') or 'título'} ({how})"]
    parts += list(d.get("notes") or [])
    return "; ".join(parts)


def _num_txt(x: float) -> str:
    return f"{x:,.4f}".rstrip("0").rstrip(".") if abs(x) < 1 else f"{x:,.2f}"


def nde_bounds(th) -> list:
    """Deuda neta / EBITDA (empresa no regulada): [baja <, elevada ≥, alta ≥], los umbrales de las alertas."""
    hi = th.net_debt_ebitda_high
    return [th.net_debt_ebitda_low, hi, hi * cfg("thresholds.alerts.leverage.risk_mult")]


def beta_bounds(th) -> list:
    """Beta: [defensiva <, volátil ≥, muy volátil ≥]: beta_low y beta_high del sector, los de la alerta."""
    return [th.beta_low, _PDF_BANDS["beta_market_upper"], th.beta_high]


def read_nde(nde, state=None, net_debt=None, reit=False, utility=False, th=None):
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
    if utility:   # etapa 11b: bandas de utility regulada del score (utility_nde_*)
        b = cfg("thresholds.score.solidez.utility_nde_bounds")
        if nde <= b[0]: return ("Conservadora", 'pos', f"la deuda neta ({nde:.1f}x EBITDA) es conservadora para una "
                                                       "utility regulada")
        if nde <= b[1]: return ("Adecuada", 'pos', f"la deuda neta ({nde:.1f}x EBITDA) está en el rango habitual de "
                                                   f"una utility con grado de inversión (hasta {b[1]:.1f}x)")
        if nde <= b[2]: return ("En línea", 'neu', f"la deuda neta ({nde:.1f}x EBITDA) está en línea con las utilities "
                                                   "reguladas")
        if nde <= b[3]: return ("Elevada", 'warn', f"la deuda neta ({nde:.1f}x EBITDA) es elevada para una utility")
        return ("Alta", 'neg', f"la deuda neta ({nde:.1f}x EBITDA) es alta incluso para una utility regulada")
    # Fase 4 (mapa, bandas paralelas): las de las alertas, una sola fuente: baja < net_debt_ebitda_low del sector;
    # elevada > net_debt_ebitda_high; alta > high × alerts.leverage.risk_mult.
    lo, hi, risk = nde_bounds(th or ThresholdConfig())
    if nde < lo:      return ("Baja", 'pos', f"la deuda neta equivale a {nde:.1f}x EBITDA, un nivel bajo")
    if nde < hi:      return ("Moderada", 'neu', f"la deuda neta ({nde:.1f}x EBITDA) es manejable")
    if nde < risk:    return ("Elevada", 'warn', f"la deuda neta ({nde:.1f}x EBITDA) es elevada")
    return ("Alta", 'neg', f"la deuda neta ({nde:.1f}x EBITDA) es alta y condiciona la flexibilidad financiera")


def read_runway(rw):
    """Runway de GROWTH_PRE_PROFIT (etapa 7): (etiqueta, tono, frase) o None sin dato."""
    if not rw or rw.get("state") not in ("autofinanciada", "runway"):
        return None
    if rw["state"] == "autofinanciada" and rw.get("sbc_exceeds_fcf"):
        return ("Autofinanciada en caja", 'pos',
                "el FCF de los últimos doce meses es positivo: la empresa no consume caja; la compensación en acciones"
                + (f" ({rw['sbc_to_revenue']:.1%} de los ingresos)" if rw.get("sbc_to_revenue") is not None else "")
                + " supera ese FCF y se paga con dilución")
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


def read_growth(g, what="los ingresos", kind="revenue", cycle=False, cagr=False):
    """cycle=True (CYCLICAL, etapa 9a): crecimiento de ciclo medio (promedio interanual de
    los ejercicios disponibles), no el interanual de un tramo del ciclo. cagr=True (etapa
    9b): la tasa anual compuesta a 3 años, la cifra que puntúa Crecimiento."""
    if g is None: return None
    per = "anual de ciclo medio" if cycle else ("anual en 3 años" if cagr else "interanual")
    if cycle:   # fase 1: en la cota del modelo, la cifra no es un dato medido y el texto lo dice
        lo, hi = cfg("valuation.archetypes.cyclical_growth_bounds")
        if math.isclose(g, lo):
            per += " (acotado al mínimo que admite el modelo)"
        elif math.isclose(g, hi):
            per += " (acotado al máximo que admite el modelo)"
    pl = what.startswith(("los ", "las "))      # concordancia: "los ingresos se contraen" / "el BPA se contrae"
    contrae, crece = ("se contraen", "crecen") if pl else ("se contrae", "crece")
    plano = "están prácticamente planos" if pl else "está prácticamente plano"
    if growth_for_bands(g) < 0:   # entre −2% y 0: plano (estancamiento), no contracción
        return ("Contracción", 'neg', f"{what} {contrae} un {_pct(abs(g))} {per}")
    b = cfg(f"thresholds.score.crecimiento.{kind}_bounds")   # las del score (ingresos o BPA)
    if cycle:
        if g >= b[1]: return ("Sólido", 'pos', f"{what} {crece} {_pct(g)} {per}, un ritmo sólido a lo largo del ciclo")
        if g >= b[2]: return ("Moderado", 'neu', f"{what} {crece} {_pct(g)} {per}, un ritmo moderado")
        return ("Plano", 'warn', f"{what} {plano} a lo largo del ciclo ({_pct(g)} {per})")
    sfx = f" {per}" if cagr else ""
    if g >= b[0]: return ("Acelerado", 'pos', f"{what} {crece} {_pct(g)}{sfx}, un ritmo acelerado propio de compañías growth")
    if g >= b[1]: return ("Sólido", 'pos', f"{what} {crece} {_pct(g)}{sfx}, un ritmo sólido")
    if g >= b[2]: return ("Moderado", 'neu', f"{what} {crece} {_pct(g)}{sfx}, un ritmo moderado")
    return ("Plano", 'warn', f"{what} {plano} ({_pct(g)}{sfx})")


# Etapa 9c: con el precio por encima del valor justo, la frase dice si algún escenario del grid de
# sensibilidad lo alcanza (dentro: parte alta del grid) o ninguno (fuera del grid). Nunca "muy optimistas"
# cuando el grid contiene el precio.
GRID_ABOVE = "ningún supuesto razonable lo justifica (el precio queda fuera del rango de sensibilidad del DCF)"
GRID_INSIDE = ("requiere supuestos exigentes pero posibles (el precio cae en la parte alta del rango de "
               "sensibilidad del DCF)")


def _grid_clause(in_grid):
    return f": {GRID_ABOVE}" if in_grid is False else f": {GRID_INSIDE}" if in_grid is True else ""


def read_upside(up, in_grid=None):
    """Upside del DCF en %: las bandas del DCF en Valoración (thresholds.score.valoracion).
    `in_grid`: si el grid de sensibilidad contiene el precio (None si no hay grid)."""
    if up is None: return None
    b = [x * 100 for x in cfg("thresholds.score.valoracion.dcf_upside_bounds")]
    if up >= b[0]:   return ("Muy infravalorada", 'pos', f"el modelo DCF sugiere un descuento sustancial: potencial teórico de +{up:.0f}% hasta el valor justo estimado")
    if up >= b[1]:   return ("Infravalorada", 'pos', f"el precio cotiza por debajo del valor intrínseco estimado (potencial teórico de +{up:.0f}%)")
    if up >= b[2]:   return ("Precio justo", 'neu', f"el precio cotiza en torno al valor justo estimado por el DCF ({'+' if up > 0 else ''}{up:.0f}%)")
    if up >= b[3]:   return ("Prima", 'warn', f"el precio incorpora una prima de {abs(up):.0f}% sobre el valor intrínseco estimado{_grid_clause(in_grid)}")
    return ("Sobrevalorada", 'neg', f"el precio excede en {abs(up):.0f}% el valor intrínseco estimado{_grid_clause(in_grid)}")


def read_graham(m):
    if m is None: return None
    if m >= _PDF_BANDS["graham_discount"]:  return ("Descuento Graham", 'pos', f"cotiza {_pct(m, 0)} por debajo del número de Graham, criterio clásico de valor")
    if m >= 0:     return ("Cerca de Graham", 'neu', f"cotiza cerca del número de Graham (margen de {_pct(m, 0)})")
    return ("Sobre Graham", 'warn',
            f"cotiza {_pct(abs(m), 0)} por encima del número de Graham — habitual en compañías de calidad/crecimiento, "
            "donde este criterio de 1949 resulta demasiado restrictivo")


def read_beta(b, th=None):
    if b is None: return None
    # Fase 4 (mapa, bandas paralelas): defensiva y muy volátil son los umbrales de la alerta (beta_low / beta_high del
    # sector); "de mercado" hasta el punto medio del informe.
    bb = beta_bounds(th or ThresholdConfig())
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



# ══════════════════════════════ FORMATO ══════════════════════════════
# Fase 1 (T3.2): el motor conserva sus códigos; la presentación habla castellano. Sin dato: "—", como en las filas
# "no significativa" (nunca "N/A").
NO_DATA = "—"
FIN_HEALTH_LEVEL_ES = {"STRONG": "Sólida", "GOOD": "Buena", "NEUTRAL": "Neutral", "WEAK": "Débil"}


def _es_value(v):
    """Valor que llega del motor ya formateado: "N/A" se presenta como "—"."""
    return NO_DATA if v == "N/A" else v


def fv(val, fmt="num"):
    if val is None:
        return NO_DATA
    try:
        v = float(val)
        if fmt == "pct":   return f"{v * 100:.2f}%"
        if fmt == "mult":  return f"{v:.2f}x"
        if fmt == "price": return _price(v)    # etapa 9b: el signo va antes del símbolo (−$1.10)
        if fmt == "money": return _money(v)
        return f"{v:,.2f}"
    except (TypeError, ValueError):
        return NO_DATA


def join_sentences(parts):
    """Une frases en un párrafo fluido: Mayúscula inicial + '. ' y cierre (sin escapar)."""
    parts = [p for p in parts if p]
    if not parts:
        return None
    out = []
    for p in parts:
        p = p.strip().rstrip('.')
        out.append(p[0].upper() + p[1:])
    return '. '.join(out) + '.'


def cap(t):
    t = (t or "").strip().rstrip('.')
    return (t[0].upper() + t[1:] + ".") if t else ""


def category_tone(pct):
    """Tono de una categoría (puntos / máximo, en %): thresholds.pdf.category_tone_bounds."""
    b = _PDF_BANDS["category_tone_bounds"]
    return 'pos' if pct >= b[0] else 'warn' if pct >= b[1] else 'neg'


def _rd(r):
    """Lectura (etiqueta, tono, frase[, brecha]) -> dict del JSON."""
    if r is None:
        return None
    return {"label": r[0], "tone": r[1], "text": r[2]}


def _row(key, label, value, reading="—", tone=None, state="con_dato", bench=None, gap=None, text=None):
    # Fase 1 (decisión del usuario, registro #14): lo que no aplica no se cita con cifra, tampoco en las tablas
    # (antes, etapa 9b, la fila mostraba la cifra con "No aplica": FCF yield de BCS 29.31%). "—" y el motivo.
    if state == "no_aplica" or str(reading or "").startswith("No aplica"):
        value, gap = NO_DATA, (None if gap is None else "—")
    return {"key": key, "label": label, "value": value, "bench": bench, "gap": gap,
            "reading": reading, "tone": tone, "state": state, "text": text}


def _clean_metric(m):
    return m.replace(" vs Sector", "").replace(" vs mercado", "")


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


# Múltiplos propios de cada rama (filas del score de Valoración).
BRANCH_METRICS = ("P/B frente a ROE", "P/TBV frente a ROTE", "P/FFO (REIT)", "Rentabilidad por dividendo (REIT)",
                  "Rentabilidad por dividendo (utility)",
                  "EV/Ventas", "Regla de 40", "EV/EBITDA normalizado vs Sector",
                  "EV/EBITDA normalizado vs mercado", "P/FCF normalizado")
_SEV_READ = {"excellent": ("Favorable", 'pos'), "good": ("Favorable", 'pos'), "ok": ("En línea", 'neu'),
             "moderate": ("Exigente", 'warn'), "severe": ("Desfavorable", 'neg')}
_SEV_TONE = {"excellent": 'pos', "good": 'pos', "ok": 'neu', "moderate": 'warn', "severe": 'neg'}
_SEV_LAB = {"excellent": "Excelente", "good": "Favorable", "ok": "En línea", "moderate": "Débil", "severe": "Muy débil"}
PIOTROSKI_LABELS = {
    "roa_positive": "ROA positivo", "cfo_positive": "Flujo de caja operativo positivo",
    "roa_improved": "ROA en mejora", "earnings_quality": "Calidad del beneficio (flujo operativo frente a beneficio neto)",
    "debt_reduced": "Reducción de deuda a largo plazo", "current_ratio_improved": "Liquidez en mejora",
    "no_dilution": "Sin dilución de acciones", "gross_margin_improved": "Margen bruto en mejora",
    "asset_turnover_improved": "Rotación de activos en mejora",
}


def na_keys(analysis):
    """Componentes que no aplican al arquetipo (+ EV/EBITDA con EBITDA <= 0 en pre-beneficio)."""
    archetype = (analysis.get("classification") or {}).get("archetype") or "MATURE"
    xm = analysis.get("archetype_metrics") or {}
    keys = set(cfg(f"sectors.archetypes.not_applicable.{archetype}") if archetype in ARCHETYPES else ())
    if archetype == "GROWTH_PRE_PROFIT" and xm.get("ebitda") is not None and xm["ebitda"] <= 0:
        keys.add("ev_ebitda")   # EBITDA <= 0: EV/EBITDA no aplica (etapa 6)
    return keys


# ══════════════════════════════ BLOQUE DISPLAY ══════════════════════════════
_REVERSE_BANDS = {"barata": ("Barata", "pos"), "en_precio": ("En precio", "neu"), "exigente": ("Exigente", "warn"),
                  "muy_exigente": ("Muy exigente", "neg")}


def _market_block(a: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Fase 5 (D5: solo contexto): señales de mercado y lectura conductual (lib/market_context.py), con la
    afirmación de cada frase. Tono neutro siempre (efecto marco, PLAN §2.3)."""
    mc = a.get("market_context") or {}
    if not mc:
        return None
    rows = []
    for r in mc.get("readings") or []:
        _record(r["text"], _claim("market_signal", field=r["field"], value=r["num"], signal=r["key"]),
                source="display.market")
        rows.append({"key": r["key"], "label": r["label"], "value": r["value"], "text": r["text"], "tone": 'neu'})
    beh = []
    for b in mc.get("behavioral") or []:
        _record(b["text"], _claim("behavioral", field=b["field"], value=b["num"], kind_b=b["kind"]),
                source="display.market")
        beh.append(b["text"])
    bad = {k: v for k, v in (mc.get("series_status") or {}).items() if v != "ok"}
    status = (("Sin señales: " if not rows else "Señales parciales: ")
              + "; ".join(f"la serie {'de la empresa' if k == 'company' else 'del índice' if k == 'market' else 'del sector'} "
                          f"es {v.replace('_', ' ')}" for k, v in bad.items())) if bad else None
    return {"title": "Contexto de mercado", "note": mc.get("note"), "rows": rows, "status_note": status,
            "behavioral_title": "Lectura conductual del mercado", "behavioral": beh,
            "news": (mc.get("news") or {}).get("items") or [],
            "news_note": ((f"Titulares de los últimos {(mc.get('news') or {}).get('days')} días (Finnhub), sin "
                           "interpretación: no puntúan." if (mc.get("news") or {}).get("items") else
                           (mc.get("news") or {}).get("reason")) if mc.get("news") else None),
            "pead_note": ("La deriva tras los resultados (PEAD) no se lee: hace falta la sorpresa del BPA frente al "
                          "consenso y no hay fuente con fecha para ella."),
            "source": (f"Serie diaria de Yahoo Finance (cierre ajustado por dividendos y splits, 2 años), S&P 500 y "
                       f"ETF del sector ({mc.get('sector_etf')}).")}


def _premortem_block(a: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Fase 4 (T3): "Esta lectura sería errónea si…" (lib/premortem.py), con la afirmación de cada condición."""
    pm = a.get("premortem") or {}
    if not pm.get("items"):
        return None
    for it in pm["items"]:
        _record(it["text"], _claim("premortem", field=it.get("field"), value=it.get("value"), kind_pm=it.get("kind")),
                source="display.premortem")
    return {"title": pm["title"], "items": [it["text"] for it in pm["items"]],
            "note": "Condiciones que invalidarían la lectura de hoy, con la cifra que las mide: no son previsiones."}


def _shown_archetype_label(a: Dict[str, Any], archetype: Optional[str]) -> str:
    """Etiqueta del arquetipo para el usuario; en FINANCIAL, el subtipo (fase 3, T4/T7: banco, aseguradora,
    conglomerado o entidad financiera) en lugar de "Banco/aseguradora"."""
    sub = (a.get("classification") or {}).get("subtype_label")
    return sub if (archetype == "FINANCIAL" and sub) else archetype_label(archetype)


def _implied_return_block(a: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Financieras (fase 3, T4; F3_DISENO §3, §8.8): el ROTE (banco) o ROE (aseguradora, conglomerado) que descuenta
    el precio frente al que obtiene, con la sensibilidad del múltiplo justificado a ±2 pp."""
    x = (a.get("archetype_metrics") or {}).get("implied") or {}
    if x.get("implied") is None or x.get("own") is None:
        return None
    m, sub = x["metric"], x.get("subtype")

    def pct(v):
        return f"{v * 100:.1f}%".replace("-", "−")
    who = {"banco": "el banco obtiene", "aseguradora": "la aseguradora obtuvo",
           "conglomerado": "el conglomerado obtuvo", "utility": "la utility obtuvo"}.get(sub, "la entidad obtuvo")
    if m == "ROTE":
        own_txt = f"{who} un {pct(x['own'])} en el último ejercicio" + (
            " (ajustado por AT1)" if x.get("at1") else "") + (
            f"; {pct(x['own_avg'])} de media en {x['own_years']} ejercicios" if x.get("own_years", 0) > 1 else "")
        mult_txt = "veces el valor contable tangible"
    else:
        own_txt = f"{who} un {pct(x['own'])} de media en {x['own_years']} ejercicios"
        mult_txt = "veces el valor contable"
    text = f"El precio descuenta un {m} sostenido del {pct(x['implied'])}; {own_txt}."
    _record(text, _claim("implied_return", field="archetype_metrics.implied.implied", value=x["implied"],
                         own=x["own"], band=x.get("band")), source="display.implied_return")
    lab, tone = _REVERSE_BANDS.get(x.get("band"), (None, "neu"))
    lines = [{"text": text, "label": lab, "tone": tone}]
    sens = [r for r in x.get("sensitivity") or [] if r.get("delta") in (min(r2["delta"] for r2 in x["sensitivity"]),
                                                                          max(r2["delta"] for r2 in x["sensitivity"]))]
    parts = [f"con un {m} del {pct(r['return'])}, {r['multiple_justified']:.2f} {mult_txt}"
             for r in sens if r.get("multiple_justified") is not None]
    if parts:
        lines.append({"text": "Sensibilidad (±2 pp): se justificaría " + "; ".join(parts) + f" (hoy cotiza a "
                              f"{x['multiple']:.2f}).", "label": None, "tone": "neu"})
    extra = {"aseguradora": "Ratio combinado: sin dato (no hay una fuente estructurada que lo dé).",
             "conglomerado": ("Conglomerado: la propia empresa usa el valor contable como referencia; la suma de "
                              "partes no se calcula."),
             "utility": ("Utility regulada: el regulador fija el retorno sobre su base de activos; su FCF es negativo "
                         "por diseño (invierte en la base), así que no hay DCF."),
             "banco": None}.get(sub)
    return {"title": f"{m} que descuenta el precio", "lines": lines,
            "role": ("Lectura del método intrínseco del banco (P/TBV frente a ROTE)." if m == "ROTE" else
                     "Lectura del método intrínseco (P/B frente al ROE medio del ciclo).") + (f" {extra}" if extra else ""),
            "method": "Gordon: P/TBV = (ROTE − g) / (Ke − g), despejado para el ROTE (igual con P/B y ROE)."}


def _reverse_block(a: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Bloque del DCF inverso (fase 3, T3): la frase de cada lectura (pasa por el guardián), su banda y el papel
    que tiene en el veredicto. None si no aplica (con el motivo en el análisis)."""
    rv = a.get("reverse_dcf") or {}
    m = rv.get("main") or {}
    if not rv.get("applicable") or not m.get("text"):
        return None
    lines = []
    for key, x in (("main", m), ("ttm", rv.get("ttm") or {})):
        if not x.get("text"):
            continue
        txt = x["text"] if key == "main" else "Con el flujo del periodo: " + x["text"][0].lower() + x["text"][1:]
        _record(txt, _claim("implied_growth", field=f"reverse_dcf.{key}.g10", value=x.get("g10"), band=x.get("band")),
                source="display.reverse_dcf")
        lab, tone = _REVERSE_BANDS.get(x.get("band"), (None, "neu"))
        lines.append({"text": txt, "label": lab, "tone": tone})
    if not lines:
        return None
    adj = next((x for x in (((a.get("score") or {}).get("breakdown") or {}).get("Valoración") or {}).get("adjustments")
                or [] if str(x.get("metric", "")).startswith("DCF inverso")
                or str(x.get("reason", "")).startswith("El DCF directo no concilia")), None)
    _metric = str((adj or {}).get("metric", ""))
    role = ("Es el método intrínseco del veredicto: el DCF directo no concilia con el precio"
            if (adj is not None and str(adj.get("reason", "")).startswith("El DCF directo"))
            else "Es el método intrínseco del veredicto: el DCF directo no es significativo (FCF − SBC ≤ 0), así que "
                 "se valora el flujo de mantenimiento" if "flujo de mantenimiento" in _metric
            else ("Es el método intrínseco del veredicto: el DCF directo no es significativo ("
                  + str((a.get("dcf") or {}).get("reason") or "sin valor por acción positivo") + ")")
            if (a.get("dcf") or {}).get("not_significant") and adj is not None
            else "Es el método intrínseco del veredicto: sin DCF directo, se valora el FFO por acción"
            if adj is not None else "Contraste del DCF directo: no puntúa")
    if adj is not None:
        role += f" (aporta {adj['adjustment']:+d} puntos a Valoración)."
    else:
        role += "."
    return {"title": "Crecimiento que exige el precio (DCF inverso)", "lines": lines, "role": role,
            "method": ("Misma estructura que el DCF directo (crecimiento constante 5 años y convergencia al "
                       "terminal en los 5 siguientes). Referencia principal: tasas base de Mauboussin y Callahan "
                       "(2021) por tamaño e industria; segunda: la historia propia.")}


def build_display(analysis: Dict[str, Any], sector_bench: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    a = analysis
    if sector_bench is None:
        sector_bench = (a.get("benchmark") or {}).get("values") or {}
    # Benchmark de los múltiplos (main._select_benchmark): sector o mercado amplio.
    _vb = a.get("benchmark") or {}
    _mkt = _vb.get("profile") == "market"
    _ref = "del mercado (S&P 500)" if _mkt else "del sector"
    _bcol = "MERCADO" if _mkt else "SECTOR"
    # Fase 1 (#20): "(TTM)" solo con ratios TTM; sin 4 trimestres consecutivos la base es el último ejercicio.
    _annual = ((a.get("data_provenance") or {}).get("ttm") or {}).get("basis") == "anual"
    _PE = "P/E (último ejercicio)" if _annual else "P/E (TTM)"

    def _rvs(*args, **k):
        return read_vs_sector(*args, ref=_ref, **k)

    km = a.get("key_metrics", {}) or {}
    price = a.get("price")
    score = a.get("score") or {}
    dcf = a.get("dcf") or {}
    graham = a.get("graham_number")
    graham_margin = a.get("graham_margin")
    altman = a.get("altman_z") or {}
    piotroski = a.get("piotroski_f") or {}
    fin_health = a.get("financial_health")
    alerts = a.get("alerts") or {}
    sensitivity = a.get("sensitivity") or {}
    classification = a.get("classification") or {}
    archetype = classification.get("archetype") or "MATURE"
    not_app = a.get("not_applicable") or {}
    is_financial = archetype == "FINANCIAL"
    xm = a.get("archetype_metrics") or {}
    _na_keys = na_keys(a)
    norm = a.get("earnings_normalization") or {}

    # posición en rango 52 semanas
    h52, l52 = km.get("price_52w_high"), km.get("price_52w_low")
    pos52 = None
    if h52 and l52 and price and (h52 - l52) > 0:
        pos52 = (price - l52) / (h52 - l52) * 100

    breakdown = score.get("breakdown") or {}
    # Etapa 9a: dos puntuaciones, nunca un total único.
    _q = a.get("quality") or {}
    _pa = a.get("price_attractiveness") or {}
    _vd = a.get("verdict") or {}
    q_score, q_level = _q.get("score"), _q.get("level")
    p_score, p_raw, p_level = _pa.get("score"), _pa.get("score_raw"), _pa.get("level")
    q_tone, p_tone = quality_tone(q_level), price_tone(p_level)
    cover_notes = []                    # cobertura parcial de cualquiera de las dos
    if _q.get("basis"):
        cover_notes.append(f"Calidad {_q['basis']}" + (f" ({', '.join(_q.get('excluded_categories') or [])} "
                                                     "no concluyente)" if _q.get("excluded_categories") else ""))
    if _q.get("low_coverage_categories"):
        cover_notes.append("cobertura baja en " + ", ".join(_q["low_coverage_categories"]))
    if _pa.get("basis") or (p_score is None and breakdown):
        cover_notes.append("Precio sin dato: Valoración no concluyente")
    # Etapa 9b: sin jerga ("crudo / contraído"): sin ajustar X → ajustado a Y por confianza media.
    price_note = (f"sin ajustar {p_raw} → ajustado a {p_score} por confianza {_pa.get('confidence')}"
                  if _pa.get("contracted") else None)
    # Fase 4 (T2; mapa, efecto frontera): a 2 puntos o menos de otro nivel, se dice.
    _bq, _bp = (_q.get("border") or {}).get("text"), (_pa.get("border") or {}).get("text")
    for _part, _src, _key in (("quality", _q, "quality"), ("price", _pa, "price_attractiveness")):
        _b = _src.get("border") or {}
        if _b.get("text"):
            _record(_b["text"], _claim("level_border", field=f"{_key}.border.points", value=_b.get("points"),
                                       part=_part), source="display.border")
    if _bp:
        price_note = (price_note + "; " if price_note else "") + _bp

    n_red = len(alerts.get("red_flags") or [])
    n_warn = len(alerts.get("warnings") or [])
    n_str = len(alerts.get("strengths") or [])

    # ── lecturas adaptativas (se usan en resumen, secciones y tablas) ──
    # P/E <= 0 llega como None marcado "no significativo" (validate_outputs):
    # la lectura "Sin beneficios" se conserva a partir del flag de validación.
    _nosig = {f.get("field", "").split(".", 1)[-1]: f for f in (a.get("data_validation") or [])
              if f.get("field", "").startswith("key_metrics.")
              and f.get("rule") in ("multiplo_no_significativo", "ratio_no_significativa")}
    _pe_flag = _nosig.get("pe") if (_nosig.get("pe") or {}).get("rule") == "multiplo_no_significativo" else None
    _pe_in = km.get("pe") if km.get("pe") is not None or not _pe_flag else _pe_flag.get("old")
    r_pe = read_pe(_pe_in, sector_bench.get("pe"), km.get("roic_wacc_spread"), ref=_ref)
    # Bandas del score (ROE, D/E): las del sector o, con el perfil market, las del mercado.
    _thkey = _vb.get("thresholds_key") or (a.get("sector_info") or {}).get("mapped_sector") or "default"
    _th = SECTOR_THRESHOLDS.get(_thkey, ThresholdConfig())
    r_roe = read_roe(km.get("roe"), km.get("roa"), _th, market=_mkt)
    r_spread = read_spread(km.get("roic_wacc_spread"), km.get("roic"), km.get("wacc"))
    # Etapa 8: fiabilidad del DCF. Con fiabilidad baja la lectura lo dice y el DCF no puntúa.
    _rel = dcf.get("reliability") or {}
    # Fuera del grid con fiabilidad baja, DCF_NO_RECONCILE ya lo dice: sin repetirlo en la frase.
    _in_grid = _rel.get("grid_contains_price")
    r_up = read_upside(dcf.get("upside"), None if (_rel.get("level") == "baja" and _in_grid is False) else _in_grid)
    if r_up and _rel.get("level") == "baja":
        r_up = (r_up[0] + " (fiabilidad baja)", 'neu',
                r_up[2] + ". " + (DCF_NO_RECONCILE if _rel.get("grid_contains_price") is False
                                  else "DCF de fiabilidad baja: no se usa en el score"))
    _conf = a.get("confidence") or {}
    _wacc = a.get("wacc") or {}
    r_graham = read_graham(graham_margin)
    r_cr = None if "current_ratio" in _na_keys else read_current(
        km.get("current_ratio"), ((a.get("business_model") or {}).get("current_ratio")))
    _rw = xm.get("runway") if archetype == "GROWTH_PRE_PROFIT" else None
    r_rw = read_runway(_rw)
    # D/E contable sin lectura en financieras (los depósitos son pasivo): decisión de la etapa 4.
    r_de = None if is_financial else read_de(km.get("de"), _th.debt_equity_high, km.get("interest_coverage"),
                                             market=_mkt)
    de_mode = "financial" if is_financial else "score"
    # Etapa 9a: el D/E no puntúa en REIT (informativo) ni con caja neta (regla M); la lectura lo dice.
    if r_de and archetype == "REIT":
        de_mode = "informativo"
        r_de = ("Informativo", 'neu', f"el D/E de {km['de']:.2f}x es informativo: en un REIT el apalancamiento se "
                                      "mide por la deuda neta/EBITDA")
    elif "de" in _na_keys and not is_financial:
        # Etapa 11b (UTILITY): el D/E genérico no aplica; el apalancamiento va por deuda neta/EBITDA.
        de_mode, r_de = "no_aplica", None
    elif r_de and (km.get("net_debt") or 0) < 0:
        de_mode = "no_significativo"
        r_de = ("No significativo", 'neu', f"con caja neta, el D/E ({km['de']:.2f}x) no mide apalancamiento")
    ic_state = km.get("interest_coverage_state")
    r_ic = read_coverage(km.get("interest_coverage"), ic_state, utility=archetype == "UTILITY")
    nde_state = km.get("net_debt_to_ebitda_state")
    r_nde = read_nde(km.get("net_debt_to_ebitda"), nde_state, km.get("net_debt"), reit=archetype == "REIT",
                     utility=archetype == "UTILITY", th=_th)
    r_pay = read_payout(km.get("payout_ratio"), km.get("payout_basis"))
    _cyc = archetype == "CYCLICAL"
    # Etapa 9b: los textos citan la cifra que PUNTÚA Crecimiento (su ajuste del desglose
    # lleva el valor en `raw`): CAGR a 3 años, ciclo medio en CYCLICAL, retorno total por
    # acción en REIT. El interanual de la fuente queda solo en la tabla, rotulado.
    _gadj = {x.get("metric"): x for x in (breakdown.get("Crecimiento") or {}).get("adjustments") or []}
    _rev_adj = (_gadj.get("Crecimiento Ingresos 3Y") or _gadj.get("Retorno total (dividendo + FFO por acción)")
                or _gadj.get("Retorno total (dividendo + ingresos por acción)")
                or _gadj.get("Retorno total (dividendo + ingresos)"))
    _eps_adj = _gadj.get("Crecimiento EPS 3Y")
    g_rev = (_rev_adj or {}).get("raw")
    # Con dilución o recompras relevantes el score mide los ingresos POR ACCIÓN (etapa 7): se rotula.
    _rev_ps = "ingresos" in ((a.get("growth_basis") or {}).get("applied_to") or [])
    g_eps = None if "eps_growth" in _na_keys else (_eps_adj or {}).get("raw")
    if archetype == "REIT":
        r_grev = None
        if _rev_adj and g_rev is not None:
            r_grev = (_SEV_LAB.get(_rev_adj.get("severity"), "—"), _SEV_TONE.get(_rev_adj.get("severity"), 'neu'),
                      f"el retorno total por acción (dividendo más crecimiento del FFO por acción en 3 años) es del "
                      f"{_pct(g_rev)}")
        r_gearn = None
    else:
        r_grev = read_growth(g_rev, "los ingresos por acción" if _rev_ps else "los ingresos", cycle=_cyc,
                             cagr=not _cyc)
        r_gearn = read_growth(g_eps, "el BPA", "eps", cycle=_cyc, cagr=not _cyc)
    r_beta = read_beta(km.get("beta"), _th)
    r_52 = read_pos52(pos52)
    r_bb = read_buyback(km.get("buyback_yield"))
    r_fcfy = read_fcf_yield(km.get("fcf_yield"))
    # Etapa 9a: ningún texto cita una métrica que no aplica al arquetipo; el Número de
    # Graham no se muestra donde el P/E no aplica.
    # ── Fase 1 (guardián narrativo): afirmaciones de cada lectura, con el campo que las respalda ──
    if _claims_active():
        _rec(r_pe, _claim("vs_bench", metric="pe", field="key_metrics.pe", value=_pe_in, bench=sector_bench.get("pe"),
                          ref=_ref, higher_better=False),
             _claim("spread", field="key_metrics.roic_wacc_spread", value=km.get("roic_wacc_spread")))
        _rec(r_roe, _claim("figure", field="key_metrics.roe", value=km.get("roe"), fmt="pct"))
        _rec(r_spread, _claim("spread", field="key_metrics.roic_wacc_spread", value=km.get("roic_wacc_spread")))
        _rec(r_up, _claim("dcf_upside", field="dcf.upside", value=dcf.get("upside")),
             _claim("dcf_rel", field="dcf.reliability.level", value=_rel.get("level")))
        _rec(r_graham, _claim("graham", field="graham_margin", value=graham_margin))
        _rec(r_cr, _claim("figure", field="key_metrics.current_ratio", value=km.get("current_ratio"), fmt="mult2"))
        _rec(r_rw, _claim("runway", field="archetype_metrics.runway", value=_rw))
        _rec(r_de, _claim("figure", field="key_metrics.de", value=km.get("de"), fmt="mult2"),
             *([_claim("net_cash", field="key_metrics.net_debt")] if de_mode == "no_significativo" else []))
        _ic_claims = [_claim("coverage", field="key_metrics.interest_coverage", value=km.get("interest_coverage"),
                             state=ic_state)]
        if ic_state == "sin_carga":
            _ic_claims.append(_claim("no_interest_burden"))
        if ic_state in ("no_significativo", "negativa"):
            _ic_claims.append(_claim("ebit_negative", field="key_metrics.operating_income"))
            _ic_claims.append(_claim("net_cash" if ic_state == "no_significativo" else "net_debt",
                                     field="key_metrics.net_debt"))
        _rec(r_ic, *_ic_claims)
        _rec(r_nde, _claim("nde", field="key_metrics.net_debt_to_ebitda", value=km.get("net_debt_to_ebitda"),
                           state=nde_state),
             *([_claim("net_cash", field="key_metrics.net_debt")]
               if (km.get("net_debt") or 0) < 0 and r_nde and "caja neta" in r_nde[2] else []))
        _rec(r_pay, _claim("payout", field="key_metrics.payout_ratio", value=km.get("payout_ratio"),
                           basis=km.get("payout_basis")))
        for _r, _adj, _what in ((r_grev, _rev_adj, "ingresos"), (r_gearn, _eps_adj, "bpa")):
            if _adj:
                _rec(_r, _claim("growth", field=f"score.breakdown.Crecimiento[{_adj.get('metric')}].raw",
                                value=_adj.get("raw"), what=_what, cycle=_cyc, cagr=not _cyc,
                                archetype=archetype))
        _rec(r_beta, _claim("figure", field="key_metrics.beta", value=km.get("beta"), fmt="num2"))
        _rec(r_52, _claim("pos52", field="pos52", value=pos52))
        _rec(r_bb, _claim("buyback", field="key_metrics.buyback_yield", value=km.get("buyback_yield")))
        _rec(r_fcfy, _claim("figure", field="key_metrics.fcf_yield", value=km.get("fcf_yield"), fmt="pct"))
        _record(price_note, _claim("price_contraction", field="price_attractiveness",
                                   raw=p_raw, score=p_score, confidence=_pa.get("confidence")), source="display")
    graham_shown = graham is not None and not ({"graham", "pe"} & _na_keys)
    if "pe" in _na_keys:
        r_pe = None
    if "p_fcf" in _na_keys or _cyc:   # CYCLICAL: se lee el P/FCF normalizado, no el TTM
        r_fcfy = None
    if not graham_shown:
        r_graham = None
    if "roe" in _na_keys:
        r_roe = None
    if "roic_wacc" in _na_keys:
        r_spread = None
    if "eps_growth" in _na_keys:
        r_gearn = None

    # Estado de una métrica suelta (KPIs y tarjetas): no aplica / no significativo / sin dato.
    _comp = {"pe": "pe", "roe": "roe", "net_margin": "net_margin", "fcf_yield": "p_fcf", "ev_ebitda": "ev_ebitda",
             "gross_margin": "gross_margin", "earnings_growth": "eps_growth"}

    def _state(key, raw):
        if _comp.get(key) in _na_keys:
            return "no_aplica"
        if raw is not None:
            return "con_dato"
        if key in _nosig or km.get(f"{key}_state") == "no_significativo":
            return "no_significativo"
        return "sin_dato"

    readings = {k: _rd(v) for k, v in (
        ("pe", r_pe), ("roe", r_roe), ("roic_wacc_spread", r_spread), ("dcf_upside", r_up),
        ("graham", r_graham), ("current_ratio", r_cr), ("runway", r_rw), ("de", r_de),
        ("interest_coverage", r_ic), ("net_debt_to_ebitda", r_nde), ("payout_ratio", r_pay),
        ("revenue_growth", r_grev), ("earnings_growth", r_gearn), ("beta", r_beta), ("pos52", r_52),
        ("buyback_yield", r_bb), ("fcf_yield", r_fcfy))}

    # ════════════════ PORTADA ════════════════
    # Etapa 9b: motivo de la clasificación en prosa (reason_plain); el código del arquetipo y
    # el motivo técnico quedan en classification_detail (detalle técnico).
    cls_notes, cls_detail = [], []
    if classification.get("reason"):
        _plain = classification.get("reason_plain") or classification["reason"]
        _lab = archetype_label(archetype) + ": "
        if _plain.startswith(_lab):        # la etiqueta ya va delante (chip / negrita): no se repite
            _plain = _plain[len(_lab)].upper() + _plain[len(_lab) + 1:]
        cls_notes = [_plain]
        if classification.get("low_confidence"):      # fase 3 (T2): con su motivo
            cls_notes.append(classification["low_confidence"]["plain"])
        elif classification.get("ambiguous"):
            cls_notes.append("Clasificación ambigua: confianza baja.")
        cls_notes += [x.get("detail_plain") or x.get("detail") for x in classification.get("alerts") or []
                      if x.get("detail_plain") or x.get("detail")]
        cls_detail = [f"Arquetipo {archetype} (regla {classification.get('rule')}): {classification['reason']}"]
        cls_detail += [x.get("detail") for x in classification.get("alerts") or [] if x.get("detail")]

    def _cat_items(cats):
        out = []
        for cat_name in cats:
            cat = breakdown.get(cat_name)
            if cat is None:
                continue
            cs, cm = cat.get("score", 0), cat.get("max", 20) or 20
            pctc = cs / cm * 100
            conclusive = cat.get("conclusive") is not False
            out.append({"name": cat_name, "score": cs, "max": cm, "pct": pctc,
                        "tone": category_tone(pctc) if conclusive else 'neu',
                        "conclusive": conclusive, "coverage": cat.get("coverage"),
                        "applicable": cat.get("applicable", True),
                        "text": (None if conclusive else
                                 f"No concluyente · cobertura {(cat.get('coverage') or 0):.0%}")})
        return out

    cat_groups = [{"title": "CALIDAD DEL NEGOCIO", "items": _cat_items(cfg("thresholds.score.quality.categories"))},
                  {"title": "ATRACTIVO DEL PRECIO", "items": _cat_items(cfg("thresholds.score.price.categories"))}]

    plain = plain_reasons(_conf)
    conf_tone = {'alta': 'pos', 'media': 'warn', 'baja': 'neg'}.get(_conf.get('level'), 'neu')

    # KPIs: los indicadores primarios del arquetipo (un banco nunca recibe P/E ni FCF
    # como métrica primaria; un REIT, P/FFO…).
    def _k(raw, fmt, label, key):
        return (fv(raw, fmt), label, key, raw)

    _k_common = [_k(price, "price", "Precio", "price"), _k(km.get("market_cap"), "money", "Market cap", "market_cap")]
    # La ajustada (Blume) va en el detalle del WACC; la del sector ya es la que entra (fase 2b, T6).
    _beta = _k(km.get("beta"), "num", "Beta del sector" if (a.get("beta") or {}).get("source") == "sector"
               else "Beta bruta", "beta")
    _nde = _k(km.get("net_debt_to_ebitda"), "mult", "Deuda neta/EBITDA", "net_debt_to_ebitda")
    # Fase 1: un múltiplo negativo no es un nivel. Con caja neta, la tarjeta dice "Caja neta" y su importe (como la
    # lectura de la fila de Solidez); con EBITDA negativo y deuda neta, sin cifra.
    if (km.get("net_debt_to_ebitda") or 0) < 0:
        _nd = km.get("net_debt")
        _nde = (_k(-_nd, "money", "Caja neta", "net_cash") if (_nd is not None and _nd < 0)
                else (NO_DATA, "Deuda neta/EBITDA", "net_debt_to_ebitda", None))
    if archetype == "FINANCIAL":
        _k_arch = [_k(xm.get("pb"), "mult", "P/B", "pb"), _k(km.get("roe"), "pct", "ROE", "roe"),
                   _k(km.get("net_margin"), "pct", "Margen neto", "net_margin"),
                   _k(xm.get("ptbv"), "mult", "P/TBV", "ptbv"),
                   _k(km.get("dividend_yield"), "pct", "Dividend yield", "dividend_yield"), _beta]
    elif archetype == "REIT":
        _k_arch = [_k(km.get("p_ffo"), "mult", "P/FFO", "p_ffo"),
                   _k(km.get("dividend_yield"), "pct", "Dividend yield", "dividend_yield"),
                   _k(km.get("ffo_payout"), "pct", "Payout sobre FFO", "payout_ratio"),
                   _k(km.get("de"), "mult", "Deuda/Equity", "de"), _nde, _beta]
    elif archetype == "UTILITY":
        _k_arch = [_k(km.get("pe"), "mult", "P/E", "pe"),
                   _k(km.get("dividend_yield"), "pct", "Dividend yield", "dividend_yield"),
                   _k(km.get("payout_ratio"), "pct", "Payout del dividendo", "payout_ratio"),
                   _nde, _k(km.get("roe"), "pct", "ROE", "roe"), _beta]
    elif archetype == "GROWTH_PRE_PROFIT":
        _r40 = xm.get("rule_of_40")
        _k_arch = [_k(xm.get("ev_sales"), "mult", "EV/Ventas", "ev_sales"),
                   (f"{_r40 * 100:.0f}" if _r40 is not None else NO_DATA, "Regla de 40", "rule_of_40", _r40),
                   # Etapa 9a: el margen neto no aplica a pre-beneficio; el bruto sí.
                   _k(km.get("gross_margin"), "pct", "Margen bruto", "gross_margin"),
                   _k(km.get("fcf_yield"), "pct", "FCF yield", "fcf_yield"), _nde, _beta]
    elif archetype == "CYCLICAL":
        _k_arch = [_k(xm.get("ev_ebitda_normalized"), "mult", "EV/EBITDA normalizado", "ev_ebitda_normalized"),
                   _k(km.get("roe"), "pct", "ROE", "roe"), _k(km.get("net_margin"), "pct", "Margen neto", "net_margin"),
                   _k(km.get("fcf_yield"), "pct", "FCF yield", "fcf_yield"), _nde, _beta]
    else:
        _k_arch = [_k(km.get("pe"), "mult", _PE, "pe"), _k(km.get("roe"), "pct", "ROE", "roe"),
                   _k(km.get("net_margin"), "pct", "Margen neto", "net_margin"),
                   _k(km.get("fcf_yield"), "pct", "FCF yield", "fcf_yield"), _nde, _beta]
    kpis = _k_common + _k_arch
    # Etapa 9a: la portada muestra las cifras REPORTADAS; si el score usa el beneficio
    # normalizado, lo dice la etiqueta (el normalizado va en el desglose, etiquetado).
    if norm.get("differs"):
        _rep = {_PE: _PE.replace("P/E", "P/E reportado"), "ROE": "ROE reportado", "Margen neto": "Margen neto reportado"}
        kpis = [(v, _rep.get(l, l), k, r) for v, l, k, r in kpis]

    # "Lo esencial" (fortaleza clave · a vigilar · contexto), desde señales
    _S = alerts.get("strengths") or []
    _R = alerts.get("red_flags") or []
    _W = alerts.get("warnings") or []
    _watch = _R[0] if _R else (_W[0] if _W else None)
    # Tercera card = CONTEXTO (posición en el rango de 52 semanas, sin juicio de precio).
    if r_52:
        _hl3 = ("CONTEXTO · 52 SEM.", r_52[0], r_52[1])
    elif r_up:
        _hl3 = ("PRECIO", r_up[0], r_up[1])
    else:
        _hl3 = ("PRECIO",) + ((r_pe[0], r_pe[1]) if r_pe else ("—", 'neu'))
    highlights = [
        {"kind": "strength", "kicker": "FORTALEZA CLAVE",
         "text": _S[0]["reason"] if _S else "Fundamentos sólidos en la mayoría de categorías", "tone": 'pos'},
        {"kind": "watch", "kicker": "A VIGILAR", "text": _watch["reason"] if _watch else "Sin alertas relevantes",
         "tone": 'neg' if _R else ('warn' if _W else 'pos')},
        {"kind": "context", "kicker": _hl3[0], "text": _hl3[1], "tone": _hl3[2]},
    ]

    # Fase 4 (T1): por encima de "excelente", la calidad limitada por la persistencia (lib/persistence.py).
    _pq = _q.get("persistence") or {}
    _persist_txt = _pq.get("text") if _pq.get("applied") else None
    _persist_short = _pq.get("short") if _pq.get("applied") else None
    for _t in (_persist_txt, _persist_short):
        if _t:
            _record(_t, _claim("quality_persistence", field="quality.persistence.weighted", value=_pq.get("weighted")),
                    source="display.quality")
    cover = {
        # Etapa 11b: conversión de moneda y clase de acciones aplicada a los estados (o None).
        "currency_note": currency_note((a.get("data_provenance") or {}).get("currency")),
        # Fase 2b (T3): fecha de los datos (corte) y avisos de datos (resultados publicados no incorporados, datos
        # de otro periodo descartados).
        "as_of_note": as_of_note((a.get("data_provenance") or {}).get("as_of")),
        "data_notices": data_notices(a),
        "official_source_badge": official_source_badge(a),
        "archetype": archetype,
        "archetype_label": _shown_archetype_label(a, archetype),
        "classification_notes": cls_notes,
        "quality": {"title": "CALIDAD DEL NEGOCIO", "question": "¿es buena la empresa?", "score": q_score,
                    "level": q_level, "tone": q_tone,
                    "note": "; ".join(x for x in (("baja confianza: " + "; ".join(_q.get("low_confidence_reasons") or [])
                                                   if _q.get("low_confidence") else _persist_txt), _bq) if x) or None},
        "price": {"title": "ATRACTIVO DEL PRECIO", "question": "¿está cara hoy?", "score": p_score, "raw": p_raw,
                  "contracted": bool(_pa.get("contracted")), "level": p_level, "tone": p_tone, "note": price_note},
        "categories": cat_groups,
        "verdict": {"text": _vd.get("text") or "Sin veredicto", "full": _vd.get("full"),
                    "confidence_text": _vd.get("confidence_text"), "confidence_tone": conf_tone},
        "confidence_reasons": plain[:3],
        "coverage_notes": cover_notes,
        "kpis": [{"key": k, "label": l, "value": v, "state": _state(k, r)} for v, l, k, r in kpis],
        "highlights": highlights,
    }

    # ════════════════ RESUMEN EJECUTIVO ════════════════
    def _mvu(raw, fmt):
        if raw is None:
            return (NO_DATA, "")
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

    def _mkcard(key, label, raw, fmt, benchkey, higher):
        if _state(key, raw) == "no_aplica":
            # Etapa 9b: lo que no aplica al arquetipo no se lee tampoco en las tarjetas
            # (antes: "Muy inferior" frente al sector para el ROE de un REIT o de un pre-beneficio).
            # Fase 1: sin cifra (antes la tarjeta decía "No aplica" y pintaba el valor: AMT margen neto 31.1%);
            # el motivo va en la línea de referencia.
            return {"key": key, "label": label, "value": NO_DATA, "unit": "", "pill": "No aplica", "tone": 'neu',
                    "delta": "", "bench": not_applicable_text(archetype), "state": "no_aplica"}
        bench = sector_bench.get(benchkey) if benchkey else None
        r = _rvs(label, raw, bench, higher, 'pct' if fmt == 'pct' else 'mult') \
            if (bench and raw is not None) else None
        v, u = _mvu(raw, fmt)
        if r:
            pill, tone, _f, delta = r
            # etiqueta más corta para la pill (que no envuelva en la card)
            short = {"Descuento profundo": "Gran descuento"}.get(pill)
            if short:   # fase 1: la etiqueta acortada lleva la misma afirmación que la lectura (BCS, guardián)
                _record(short, *_vs_claims(label, raw, bench, higher), source="display.tarjetas")
                pill = short
        else:
            pill, tone, delta = ("—" if raw is None else "En rango"), 'neu', ""
        return {"key": key, "label": label, "value": v, "unit": u, "pill": pill, "tone": tone, "delta": delta,
                "bench": _benchtxt(bench, fmt), "state": _state(key, raw)}

    # Etapa 6: la segunda fila son los múltiplos primarios del arquetipo.
    if archetype == "FINANCIAL":
        _val_cards = [_mkcard("pb", "P/B", xm.get("pb"), 'mult', "pb", False),
                      _mkcard("ptbv", "P/TBV", xm.get("ptbv"), 'mult', None, False),
                      _mkcard("dividend_yield", "Dividend yield", km.get("dividend_yield"), 'pct', None, True)]
    elif archetype == "REIT":
        _val_cards = [_mkcard("p_ffo", "P/FFO", km.get("p_ffo"), 'mult', None, False),
                      _mkcard("dividend_yield", "Dividend yield", km.get("dividend_yield"), 'pct', None, True),
                      _mkcard("ev_ebitda", "EV/EBITDA", km.get("ev_ebitda"), 'mult', "ev_ebitda", False)]
    elif archetype == "UTILITY":
        _val_cards = [_mkcard("pe", _PE, km.get("pe"), 'mult', "pe", False),
                      _mkcard("dividend_yield", "Dividend yield", km.get("dividend_yield"), 'pct', None, True),
                      _mkcard("forward_pe", "Forward P/E", km.get("forward_pe"), 'mult', "forward_pe", False)]
    elif archetype == "GROWTH_PRE_PROFIT":
        _val_cards = [_mkcard("ev_sales", "EV/Ventas", xm.get("ev_sales"), 'mult', None, False),
                      _mkcard("fcf_yield", "FCF yield", km.get("fcf_yield"), 'pct', "fcf_yield", True),
                      _mkcard("rule_of_40", "Regla de 40", xm.get("rule_of_40"), 'pct', None, True)]
    elif archetype == "CYCLICAL":
        _val_cards = [_mkcard("ev_ebitda_normalized", "EV/EBITDA normalizado", xm.get("ev_ebitda_normalized"),
                              'mult', "ev_ebitda", False),
                      _mkcard("fcf_yield", "FCF yield", km.get("fcf_yield"), 'pct', "fcf_yield", True),
                      _mkcard("p_fcf_normalized", "P/FCF normalizado", xm.get("p_fcf_normalized"), 'mult', "pfcf",
                              False)]
    else:
        _val_cards = [_mkcard("pe", _PE, km.get("pe"), 'mult', "pe", False),
                      _mkcard("fcf_yield", "FCF yield", km.get("fcf_yield"), 'pct', "fcf_yield", True),
                      _mkcard("ev_ebitda", "EV/EBITDA", km.get("ev_ebitda"), 'mult', "ev_ebitda", False)]
    cards = [
        # Etapa 9b: la cifra que puntúa Crecimiento, con su etiqueta (no el interanual de la fuente).
        (_mkcard("revenue_growth", "Retorno total (3 años)", g_rev, 'pct', None, True) if archetype == "REIT" else
         _mkcard("revenue_growth", ("Crecimiento ingresos (ciclo medio)" if _cyc else
                                    "Crecimiento ingresos por acción (3 años)" if _rev_ps else
                                    "Crecimiento ingresos (3 años)"),
                 g_rev, 'pct', "revenue_growth", True)),
        _mkcard("net_margin", "Margen neto", km.get("net_margin"), 'pct', "net_margin", True),
        _mkcard("roe", "ROE", km.get("roe"), 'pct', "roe", True),
        *_val_cards,
    ]

    if fin_health and isinstance(fin_health, dict) and fin_health.get("score") is not None:
        sol_short = (f"salud financiera bancaria de {fin_health['score']}/10 "
                     f"({FIN_HEALTH_LEVEL_ES.get(fin_health.get('level'), '').lower()})")
    elif r_rw:
        sol_short = f"runway {r_rw[0].lower()}: {r_rw[2]}"
    elif altman.get("z_score") is not None and altman.get("available", True):
        _zmap = {'safe': 'zona segura', 'grey': 'zona gris', 'distress': 'zona de riesgo'}
        sol_short = f"Altman Z de {altman['z_score']:.2f} ({_zmap.get(altman.get('zone'), '')})"
        if r_ic:
            sol_short += f"; {r_ic[2]}"
    elif archetype in ("REIT", "UTILITY") and r_nde:
        sol_short = r_nde[2] + (f"; {r_ic[2]}" if r_ic else "")
    else:
        sol_short = r_de[2] if r_de else None

    # Etapa 9a: resumen ejecutivo construido alrededor del veredicto verbal:
    # VEREDICTO -> lo que sostiene la CALIDAD -> lo que explica el PRECIO -> CONFIANZA.
    # Fase 1 (punto 9): ROCE visible. Sin bandas propias (fase 4): la lectura es la comparación con el ROIC, con el
    # umbral de divergencia que ya existía (thresholds.roce.divergence_pp).
    _roce, _roic = km.get("roce"), km.get("roic")
    _rdiv = km.get("roce_roic_divergence") or {}
    roce_vs_roic = roce_reading = roce_sentence = None
    if km.get("roce_state") == "ok" and _roce is not None:
        if _roic is not None and _rdiv:
            _gp = _rdiv.get("gap") or 0.0
            roce_vs_roic = (f"{abs(_gp) * 100:.1f} pp {'por debajo' if _gp < 0 else 'por encima'} del ROIC "
                            f"({fv(_roic, 'pct')})" if _rdiv.get("diverges") else f"en línea con el ROIC ({fv(_roic, 'pct')})")
            roce_reading = (None if _rdiv.get("diverges") else
                            f"ROCE {fv(_roce, 'pct')} en línea con el ROIC {fv(_roic, 'pct')} ({_gp * 100:+.1f} pp, "
                            f"dentro de {cfg('thresholds.roce.divergence_pp') * 100:.0f} pp).")
        _avg = km.get("roce_avg")
        roce_sentence = (f"ROCE {fv(_roce, 'pct')} (EBIT / capital empleado, antes de impuestos)"
                         + (f", {roce_vs_roic}" if roce_vs_roic else "")
                         + (f"; ROCE promedio del ciclo {fv(_avg, 'pct')} ({km.get('roce_years')} ejercicios"
                            + (", ciclo incompleto" if km.get("roce_cycle_incomplete") else "") + ")"
                            if _avg is not None else "") + ".")
        _record(roce_sentence, _claim("roce"), source="display.roce")
        _record(roce_reading, _claim("roce"), source="display.roce")
    exec_items = []
    _qcats = [(n, breakdown[n]) for n in cfg("thresholds.score.quality.categories")
              if n in breakdown and breakdown[n].get("conclusive", True) and breakdown[n].get("applicable", True)]
    _qcats.sort(key=lambda kv: kv[1].get("score", 0), reverse=True)
    _eb = _PDF_BANDS["exec_category_bounds"]
    _best = [f"{n} ({c['score']}/{c.get('max', 20)})" for n, c in _qcats[:2] if c.get("score", 0) >= _eb[0]]
    _weak = [f"{n} ({c['score']}/{c.get('max', 20)})" for n, c in _qcats[-1:] if c.get("score", 0) < _eb[1]]
    _vtxt = _vd.get("full") or _vd.get("text") or ""
    if _vtxt:
        exec_items.append(("VEREDICTO",
                           f"{_vtxt}. Calidad {q_score if q_score is not None else '—'}/100 · precio "
                           f"{p_score if p_score is not None else '—'}/100"
                           + (f" ({price_note})" if price_note else "") + "."))
    _qtxt = []
    if _best:
        _qtxt.append("Destaca en " + " y ".join(_best))
    if _weak:
        _qtxt.append("el punto débil es " + _weak[0])
    if _qtxt:
        exec_items.append(("CALIDAD DEL NEGOCIO", cap("; ".join(_qtxt))))
    if not is_financial and r_spread:
        exec_items.append(("CREACIÓN DE VALOR", join_sentences([cap(r_spread[2]), roce_sentence])
                           if roce_sentence else cap(r_spread[2])))
    elif r_roe:
        exec_items.append(("RENTABILIDAD", cap(r_roe[2])))
    else:   # REIT / pre-beneficio: los componentes de su rama (FFO, márgenes de su fase)
        _rb = [x for x in (breakdown.get("Rentabilidad") or {}).get("adjustments") or []
               if x.get("metric") not in ("No aplica", "Cobertura")]
        if _rb:
            exec_items.append(("RENTABILIDAD", cap("; ".join(f"{x['metric']} {x['value']}: "
                                                            f"{x['reason'].split(' - ')[0].lower()}"
                                                            for x in _rb[:2]))))
    if sol_short:
        exec_items.append(("SOLIDEZ", cap(sol_short)))
    _gro = " ".join(filter(None, [cap(r_grev[2]) if r_grev else None, cap(r_bb[2]) if r_bb else None]))
    if _gro.strip():
        exec_items.append(("CRECIMIENTO Y RETORNO", _gro))
    # Precio: la lectura del múltiplo primario del arquetipo y la del DCF
    _r_val = r_pe if "pe" not in _na_keys else None
    _branch_val = next((x for x in (breakdown.get("Valoración") or {}).get("adjustments") or []
                        if x.get("metric") in BRANCH_METRICS), None)
    if _r_val is None and _branch_val:
        _r_val = (None, None, f"{_clean_metric(_branch_val['metric'])}: {_branch_val['reason']}")
    _val = (cap(_r_val[2]) + (" " + cap(r_up[2]) if r_up else "")) if _r_val else (cap(r_up[2]) if r_up else "")
    if archetype == "FINANCIAL" and _branch_val:
        # Fase 3 (T4): en un banco o una aseguradora manda el P/B frente a su retorno (método intrínseco); el P/E,
        # que sí le aplica (registro #14), va detrás.
        _val = join_sentences([cap(f"{_clean_metric(_branch_val['metric'])}: {_branch_val['reason']}"),
                               cap(r_pe[2]) if (r_pe and "pe" not in _na_keys) else None])
    if _val.strip():
        exec_items.append(("ATRACTIVO DEL PRECIO", _val))
    _ctx = " ".join(filter(None, [cap(r_52[2]) if r_52 else None, cap(r_beta[2]) if r_beta else None]))
    if _ctx.strip():
        exec_items.append(("CONTEXTO DE MERCADO", _ctx))
    if _conf.get("level"):
        _p0 = plain[0].rstrip(".") if plain else None
        exec_items.append(("CONFIANZA DEL VEREDICTO",
                           f"{_conf['level'].capitalize()}"
                           + (f": {_p0[0].lower()}{_p0[1:]}" if _p0 else ": los métodos y los datos coinciden")
                           + ". Contrae el atractivo del precio hacia 50; la calidad no se contrae."))

    # Composición de las dos puntuaciones (sustituye al radar de 5 ejes).
    _qrows = []
    for n in cfg("thresholds.score.quality.categories"):
        c = breakdown.get(n)
        if c is None:
            continue
        if c.get("conclusive") is False:
            _qrows.append({"label": n, "kind": "nc"})
        else:
            _mx = c.get("max", 20)
            _cpct = c.get("score", 0) / (_mx or 20) * 100
            _qrows.append({"label": n, "kind": "bar", "value": c.get("score", 0), "max": _mx, "pct": _cpct,
                           "tone": category_tone(_cpct)})
    _prows = []
    for adj in (breakdown.get("Valoración") or {}).get("adjustments") or []:
        if adj.get("metric") in ("No aplica", "Cobertura") or not isinstance(adj.get("adjustment"), int) \
                or adj.get("in_block"):     # los miembros del bloque puntúan a través del bloque
            continue
        v = adj["adjustment"]
        _prows.append({"label": f"{_clean_metric(adj['metric'])} · {adj.get('value', '')}", "kind": "signed",
                       "value": v, "tone": 'pos' if v > 0 else 'neg' if v < 0 else 'neu'})
    composition = {
        "quality": {"title": "CALIDAD DEL NEGOCIO", "score": q_score, "level": q_level, "tone": q_tone,
                    "note": _q.get("basis") or ("baja confianza por cobertura" if _q.get("low_confidence")
                                                else _persist_short),
                    "rows": _qrows},
        "price": {"title": "ATRACTIVO DEL PRECIO", "score": p_score, "level": p_level, "tone": p_tone,
                  "note": price_note, "rows": _prows,
                  "signed_max": max(cfg("thresholds.score.valoracion.multiples_block_max_by_members"))},
        "caption": ("Calidad: categorías 0–20 reescaladas a 100. Precio: Valoración (base 10/20 + bloque de "
                    "múltiplos y DCF) reescalada a 100 y contraída hacia 50 según la confianza."),
    }
    summary = {"cards": cards, "exec_items": [{"label": l, "text": t} for l, t in exec_items],
               "composition": composition,
               "alert_counts": {"red_flags": n_red, "warnings": n_warn, "strengths": n_str}}

    # ════════════════ 01 VALORACIÓN ════════════════
    val_txt = join_sentences([r_pe[2] if r_pe else None, r_fcfy[2] if r_fcfy else None,
                              r_graham[2] if r_graham else None])
    if not val_txt:   # la rama del arquetipo (P/B justificado, P/FFO, normalizados…)
        _bv = [x for x in (breakdown.get("Valoración") or {}).get("adjustments") or []
               if x.get("metric") in BRANCH_METRICS]
        val_txt = join_sentences([f"{_clean_metric(x['metric'])}: {x['reason'][0].lower()}{x['reason'][1:]}"
                                  for x in _bv[:2]])
    mult_defs = [
        ("pe", _PE, km.get("pe"), sector_bench.get("pe"), False, "mult"),
        ("forward_pe", "Forward P/E", km.get("forward_pe"), sector_bench.get("forward_pe"), False, "mult"),
        ("pb", "P/B", km.get("pb"), sector_bench.get("pb"), False, "mult"),
        ("ps", "P/S", km.get("ps"), None, False, "mult"),
        ("peg", ("PEG (BPA a 3 años)" if (a.get("peg_basis") or {}).get("note", "").startswith("PEG a 3 años")
                 else "PEG (de mercado)" if a.get("peg_basis") else "PEG"),
         km.get("peg"), sector_bench.get("peg"), False, "mult"),
        ("ev_ebitda", "EV/EBITDA", km.get("ev_ebitda"), sector_bench.get("ev_ebitda"), False, "mult"),
        ("pfcf", "P/FCF", km.get("pfcf"), sector_bench.get("pfcf"), False, "mult"),
        ("fcf_yield", "FCF Yield", km.get("fcf_yield"), sector_bench.get("fcf_yield"), True, "pct"),
        ("earnings_yield", "Earnings Yield (E/P)", km.get("earnings_yield"), None, True, "pct"),
        ("dividend_yield", "Dividend Yield", km.get("dividend_yield"), None, True, "pct"),
    ]
    # Etapa 6: lo que no aplica al arquetipo no se lee ("No aplica"), y la rama
    # añade sus múltiplos (P/B justificado, P/FFO, EV/Ventas, normalizados…).
    _mult_na = {"pe": "pe", "earnings_yield": "pe", "forward_pe": "forward_pe", "peg": "peg",
                "ev_ebitda": "ev_ebitda", "pfcf": "p_fcf", "fcf_yield": "p_fcf"}
    mrows = []
    for key, lab, val, bench, hb, fm in mult_defs:
        bstr = fv(bench, fm) if bench else "—"
        if key == "pe" and norm.get("pe_unreliable") and _mult_na.get(key) not in _na_keys:
            # Etapa 7: con no recurrentes > umbral el P/E reportado no es fiable.
            mrows.append(_row(key, lab, fv(val, fm), f"No fiable ({norm['one_off_pct'] * 100:.0f}% no recurrente)",
                              'warn', "con_dato", bstr, "—"))
            continue
        if _mult_na.get(key) in _na_keys:
            mrows.append(_row(key, lab, fv(val, fm), not_applicable_text(archetype), 'neu', "no_aplica", bstr, "—",
                              text=(not_app.get(_mult_na[key]) or None)))
            continue
        r = _rvs(lab, val, bench, hb, fm) if bench else None
        state = "con_dato" if val is not None else ("no_significativo" if key in _nosig else "sin_dato")
        mrows.append(_row(key, lab, fv(val, fm), r[0] if r else "—", r[1] if r else None, state, bstr,
                          r[3] if r else "—", r[2] if r else (_nosig[key]["reason"] if key in _nosig else None)))
    for adj in (breakdown.get("Valoración") or {}).get("adjustments") or []:
        if adj.get("metric") in BRANCH_METRICS:
            lab_r, tone_r = _SEV_READ.get(adj.get("severity"), ("—", 'neu'))
            mrows.append(_row(_slug(_clean_metric(adj["metric"])), _clean_metric(adj["metric"]),
                              str(adj.get("value", "")), lab_r, tone_r, "con_dato", "—", "—", adj.get("reason")))
    if norm.get("pe_unreliable") and norm.get("pe_normalized") is not None and "pe" not in _na_keys:
        mrows.append(_row("pe_normalized", "P/E normalizado", fv(norm["pe_normalized"], "mult"),
                          "Sin no recurrentes", None, "con_dato", "—", "—"))
    market_note = None
    if _mkt:
        _src = "; ".join(f"{k.replace('_', '/').upper()}: {v}" for k, v in (_vb.get("sources") or {}).items())
        market_note = (f"Referencia: medianas y umbrales del mercado amplio (S&P 500), no los del sector "
                       f"({_vb.get('reason')}). PROVISIONALES. Fuentes: {_src}. El resto de referencias de la columna "
                       "MERCADO (Forward P/E, P/B, PEG, P/FCF, FCF yield, rentabilidad y márgenes) son la referencia "
                       "general PROVISIONAL, fijada a mano y sin fuente, no medianas del S&P 500.")
    # Etapa 7: beneficio normalizado (una línea cuando hay partidas no recurrentes aplicadas).
    norm_note = None
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
        norm_note = (f"Beneficio {norm.get('basis')}: reportado {fv(norm.get('reported_net_income'), 'money')}, "
                     f"normalizado {fv(norm.get('normalized_net_income'), 'money')} "
                     f"(no recurrentes {norm['one_off_pct'] * 100:.1f}% del beneficio; {_its}). "
                     + ("El score usa el beneficio normalizado." if norm.get("used_in_score") else ""))
        if norm.get("pe_unreliable") and norm.get("pe_normalized") is not None and "pe" not in _na_keys:
            norm_note += (f" P/E reportado {fv(norm.get('pe_reported'), 'mult')} no fiable; "
                          f"P/E normalizado {fv(norm['pe_normalized'], 'mult')}.")

    # Valor intrínseco
    _dcf_st = a.get("dcf_status") or {}
    _dcf_ns = _dcf_st.get("reason") if _dcf_st.get("state") == "no_significativo" else None
    iv_txt = join_sentences([r_up[2] if r_up else None,
                             (f"DCF (FCFF): {not_app['dcf'][0].lower()}{not_app['dcf'][1:]}" if not_app.get("dcf")
                              else f"DCF (FCFF) no significativo: {_dcf_ns}" if _dcf_ns
                              else None if r_up else "el modelo DCF no es aplicable con los datos disponibles"),
                             ("se valora sobre libros y retornos" if is_financial else None)])
    iv_rows = [_row("price", "Precio de mercado", fv(price, "price"), "")]
    if not_app.get("dcf"):
        iv_rows.append(_row("dcf_fair_value", "Valor justo DCF", "—", not_applicable_text(archetype), None, "no_aplica",
                            text=not_app.get("dcf")))
    elif _dcf_ns:
        # Etapa 11b: FCF base <= 0 o capital <= 0: sin valor razonable (nunca uno negativo).
        iv_rows.append(_row("dcf_fair_value", "Valor justo DCF", "—", "No significativo", None, "no_significativo",
                            text=_dcf_ns))
    if graham_shown:
        iv_rows.append(_row("graham", "Número de Graham", fv(graham, "price"), r_graham[0] if r_graham else "",
                            r_graham[1] if r_graham else None, text=r_graham[2] if r_graham else None))
    if dcf.get("fair_value") is not None:
        iv_rows.append(_row("dcf_fair_value", "Valor justo DCF", fv(dcf.get("fair_value"), "price"), ""))
        iv_rows.append(_row("dcf_upside", "Potencial vs precio (upside)",
                            (f"{dcf['upside']:+.1f}%" if dcf.get("upside") is not None else NO_DATA),
                            r_up[0] if r_up else "", r_up[1] if r_up else None,
                            text=r_up[2] if r_up else None))
        if dcf.get("margin_of_safety") is not None:
            iv_rows.append(_row("margin_of_safety", "Margen de seguridad", fv(dcf.get("margin_of_safety"), "pct"), ""))
    graham_note = ("Número de Graham: referencia del inversor defensivo (P/E 15 × P/B 1.5). Se muestra como "
                   "referencia y no vota en la convergencia entre métodos.") if graham_shown else None

    dcf_params = dcf_reliability_line = dcf_missing = None
    if dcf.get("fair_value") is not None:
        dcf_params = (f"Parámetros del modelo — WACC {fv(dcf.get('wacc'), 'pct')} · "
                      f"crecimiento {fv(dcf.get('growth_rate'), 'pct')}"
                      + (f" ({dcf['growth_basis']})" if dcf.get("growth_basis") else "") + " · "
                      f"terminal {fv(dcf.get('terminal_growth'), 'pct')}")
        if a.get("dcf_growth_blend"):
            # Fase 3 (T5): la mezcla declarada del interanual y del CAGR a 3 años (afirma su base temporal).
            _record(dcf_params, _claim("basis", metric="dcf.growth_rate", per="mezcla interanual y 3 años"),
                    _claim("growth", field="dcf.growth_rate", value=dcf.get("growth_rate")),
                    source="display.dcf_params")
        vc = dcf.get("value_composition") or {}
        if vc.get("terminal_pct") is not None:
            dcf_params += f" · el valor terminal aporta el {vc['terminal_pct']:.0f}% del valor total"
        _nz = dcf.get("normalized") or {}
        if _nz.get("fcf_maintenance") is not None:
            dcf_params += (f" · FCF de mantenimiento {fv(_nz['fcf_maintenance'], 'money')} (flujo operativo − D&A "
                           f"como capex de mantenimiento, promedio de {_nz.get('fcf_maintenance_years')} ejercicios), "
                           f"frente al FCF normalizado {fv(_nz.get('fcf'), 'money')} (margen FCF promedio "
                           f"{fv(_nz.get('fcf_margin_avg'), 'pct')} × ingresos actuales, que incluye el capex de "
                           "expansión"
                           + (f"; ciclo incompleto: {_nz.get('years')} ejercicios" if _nz.get("cycle_incomplete")
                              else "")
                           + "): el DCF usa el de mantenimiento, con crecimiento normalizado de ciclo medio")
        # Fiabilidad del DCF y su aporte a Valoración (etapa 8)
        _dcf_adj = next((x for x in (breakdown.get("Valoración") or {}).get("adjustments") or []
                         if x.get("metric") == "DCF (upside)"), None)
        if _rel.get("level"):
            _rl = f"Fiabilidad del DCF: {_rel['level']}"
            if _rel.get("reasons"):
                _rl += " (" + "; ".join(_rel["reasons"]) + ")"
            if _rel["level"] == "baja" and _dcf_adj is not None and \
                    str(_dcf_adj.get("reason") or "").startswith("El DCF directo no concilia"):
                # Fase 3 (T3, §2.3): el DCF inverso sustituye al directo como método intrínseco.
                _rl += (". El DCF directo no concilia con el precio: el método intrínseco es el DCF inverso, que "
                        f"aporta {_dcf_adj['adjustment']:+d} puntos a Valoración.")
            elif _rel["level"] == "baja":
                _rl += ". " + (DCF_NO_RECONCILE if _rel.get("grid_contains_price") is False
                               else "DCF de fiabilidad baja: no se usa en el score") + "."
            elif _dcf_adj is not None:
                _cap_pts = (cfg("thresholds.score.valoracion.dcf_points_high") if _rel["level"] == "alta"
                            else cfg("thresholds.score.valoracion.dcf_points_medium"))[0]
                _rl += (f". Aporta {_dcf_adj['adjustment']:+d} puntos a Valoración "
                        f"(máximo ±{_cap_pts} con fiabilidad {_rel['level']}).")
            dcf_reliability_line = _rl
    elif _dcf_ns:
        dcf_missing = f"DCF no significativo: {_dcf_ns}."
    elif dcf.get("reason"):
        dcf_missing = f"DCF sin dato: {dcf['reason']}."
    # Fase 3 (T3, D3): crecimiento que exige el precio (DCF inverso), con sus dos referencias.
    reverse_block = _reverse_block(a) or _implied_return_block(a)
    # FINANCIAL (etapa 8): sin WACC; el P/B justificado usa Ke con la beta ajustada.
    ke_note = None
    if is_financial and xm.get("cost_of_equity") is not None:
        ke_note = (f"Ke {fv(xm['cost_of_equity'], 'pct')} = Rf {fv((a.get('risk_free') or {}).get('value'), 'pct')} + "
                   f"{beta_text(xm.get('beta_adjusted'), xm.get('beta_raw'), (a.get('beta') or {}).get('source'))} × prima "
                   f"implícita {fv(cfg('valuation.capm.market_risk_premium'), 'pct')}. Bancos y aseguradoras no usan "
                   "WACC: se valoran por P/B justificado con Ke.")
    # WACC usado (etapa 8): el mismo en DCF, grid y spread ROIC−WACC.
    wacc_note = None
    if _wacc.get("value") is not None:
        _w = _wacc
        _wl = (f"WACC {fv(_w['value'], 'pct')}"
               + (f" (acotado desde {fv(_w.get('raw'), 'pct')} al rango "
                  f"{fv(_w['bounds'][0], 'pct')}–{fv(_w['bounds'][1], 'pct')})" if _w.get("clamped") else "")
               + f" = {fv((_w.get('weights') or {}).get('equity'), 'pct')} × Ke {fv(_w.get('ke'), 'pct')} "
               f"(Rf {fv(_w.get('rf'), 'pct')} + {beta_text(_w.get('beta'), _w.get('beta_raw'), (a.get('beta') or {}).get('source'))}"
               f" × prima implícita {fv(_w.get('mrp'), 'pct')})")
        _rt = _w.get("rating") or {}
        if _w.get("kd") is not None:
            _wl += (f" + {fv((_w.get('weights') or {}).get('debt'), 'pct')} × Kd {fv(_w['kd'], 'pct')} × "
                    f"(1 − t {fv(_w.get('tax_rate'), 'pct')}). Kd = Rf + spread del rating sintético "
                    f"{_rt.get('rating')} (tabla de empresas {_rt.get('table')}"
                    + (f", cobertura {_rt['coverage']:.1f}x" if _rt.get("coverage") is not None and not _rt.get("flag")
                       else "")
                    + ")" + (f"; {_rt['flag']}" if _rt.get("flag") else ""))
        else:
            _wl += " (sin deuda financiera: WACC = Ke)"
        _tx = a.get("tax_rate") or {}
        _wl += (f". t: {'tasa efectiva ' + str(_tx.get('period') or '') if _tx.get('source') == 'efectiva' else 'tipo legal'}"
                + (f" ({_tx['reason']})" if _tx.get("reason") else ""))
        if _w.get("rf_fallback"):
            _wl += f". Rf: {_w.get('rf_reason')}"
        elif _w.get("rf_source"):
            _wl += f". Rf: {_w['rf_source']} a {_w.get('rf_as_of')}"
        wacc_note = _wl + "."
        # Desglose estructurado para el desplegable de la web (mismos números).
    wacc_breakdown = None
    if _wacc.get("value") is not None:
        _w = _wacc
        wacc_breakdown = [
            {"label": "WACC", "value": fv(_w["value"], "pct")},
            {"label": "Peso del patrimonio", "value": fv((_w.get("weights") or {}).get("equity"), "pct")},
            {"label": "Coste del patrimonio (Ke)", "value": fv(_w.get("ke"), "pct")},
            {"label": "Tasa libre de riesgo (Rf)", "value": fv(_w.get("rf"), "pct")},
            *([{"label": "Beta del sector (Damodaran, sin Blume)", "value": f"{_w.get('beta', 0):.2f}"}]
              if _w.get("beta_raw") is None else
              [{"label": "Beta bruta" + {"propia": " (propia, 2 años)", "fuente": " (de la fuente, sin verificar)"}.get(
                  (a.get("beta") or {}).get("source"), ""), "value": f"{_w.get('beta_raw', 0):.2f}"},
               {"label": "Beta ajustada (Blume)", "value": f"{_w.get('beta', 0):.2f}"}]),
            {"label": "Prima de mercado implícita", "value": fv(_w.get("mrp"), "pct")},
        ]
        if _w.get("kd") is not None:
            wacc_breakdown += [
                {"label": "Peso de la deuda", "value": fv((_w.get("weights") or {}).get("debt"), "pct")},
                {"label": "Coste de la deuda (Kd)", "value": fv(_w["kd"], "pct")},
                {"label": "Rating sintético", "value": str((_w.get("rating") or {}).get("rating"))},
                {"label": "Tipo impositivo (t)", "value": fv(_w.get("tax_rate"), "pct")},
            ]

    # Sensibilidad DCF: banda de color de cada celda (thresholds.pdf.grid_color_bounds).
    sens = None
    matrix = sensitivity.get("matrix") or []
    if matrix:
        gb = _PDF_BANDS["grid_color_bounds"]

        def _band(v):
            if v is None or not price:
                return None
            diff = (v - price) / price * 100
            return 0 if diff > gb[0] else 1 if diff > gb[1] else 2 if diff > -gb[1] else 3 if diff > -gb[0] else 4
        g_rates = sensitivity.get("growth_rates") or []
        d_rates = sensitivity.get("discount_rates") or []
        _trim = (sensitivity.get("trimmed") or {}).get("note")
        sens = {
            "intro": ("Valor justo estimado según crecimiento (filas) y tasa de descuento (columnas). "
                      "Verde: escenario por encima del precio actual; rojo: por debajo."),
            "corner": "CREC. \\ WACC",
            "columns": [f"{dr * 100:.1f}%" for dr in d_rates],
            "rows": [{"label": f"{g_rates[gi] * 100:.1f}%",
                      # Etapa 11b: signo antes del símbolo ("−$8", no "$-8"), como en el resto del informe.
                      "cells": [{"value": numfmt.whole(v), "band": _band(v),
                                 "base": gi == sensitivity.get("base_growth_idx")
                                 and di == sensitivity.get("base_discount_idx")}
                                for di, v in enumerate(row)]}
                     for gi, row in enumerate(matrix)],
            "base_growth_idx": sensitivity.get("base_growth_idx"),
            "base_discount_idx": sensitivity.get("base_discount_idx"),
            "band_labels": [f"> +{gb[0]}% sobre el precio", f"+{gb[1]}% a +{gb[0]}%", f"±{gb[1]}%",
                            f"−{gb[1]}% a −{gb[0]}%", f"< −{gb[0]}% bajo el precio"],
            "note": (f"Precio actual: ${price:,.2f}. El recuadro verde marca el escenario base del modelo."
                     + (f" Grid asimétrico: {_trim}." if _trim else "")) if price else None,
        }

    # Confianza del veredicto (etapa 8): técnica, con sus dimensiones (sección 01 del PDF).
    confidence, annex_conf = None, []

    def _method_name(m):   # fase 1 (#6): con referencia de mercado, el método no se llama "frente al sector"
        return m.replace("frente al sector", "frente al mercado") if _mkt else m
    if _conf.get("level"):
        _labels = {"convergence": "Convergencia entre métodos", "coverage": "Cobertura de datos",
                   "source": "Calidad de fuente", "stability": "Estabilidad del arquetipo",
                   "fuente_oficial": "Fuente oficial (SEC)"}
        dims, annex_conf = [], []
        for _k, _dd in (_conf.get("dimensions") or {}).items():
            if _k == "fuente_oficial" and _dd.get("level") != "baja":
                continue        # fase 2b (D7): no pondera; solo se muestra cuando pone techo
            # Fase 1 (D1): en la tabla, el motivo en lenguaje llano; el técnico, al anexo del final del PDF.
            _plain_txt = list(dict.fromkeys(t for t in map(_plain_reason, _dd.get("reasons") or []) if t))
            _txt = " ".join(_plain_txt) or "Sin incidencias."
            if _dd.get("reasons"):
                annex_conf.append({"label": f"Confianza · {_labels.get(_k, _k)} ({_dd['level'].replace('_', ' ')})",
                                   "text": "; ".join(_dd["reasons"])})
            if _k == "convergence" and _dd.get("methods"):
                _txt = " · ".join(
                    f"{_method_name(m['method'])} {('%+.0f%%' % (m['upside'] * 100)) if m.get('upside') is not None else ('%+.2f' % m['signal'])}"
                    f" ({m.get('direction')}{'' if m.get('evaluable', True) else ', no evaluable'})"
                    for m in _dd["methods"] if m.get("signal") is not None) + ". " + _txt
            dims.append({"key": _k, "label": _labels.get(_k, _k), "level": _dd["level"].replace("_", " ").capitalize(),
                         "text": _txt})
        confidence = {
            "level": _conf["level"], "tone": conf_tone, "verdict_text": _vd.get("confidence_text"),
            "plain": plain, "dimensions": dims,
            "reasons": [{k: v for k, v in r.items() if k != "detail"} for r in confidence_reasons(_conf)],
            "summary": (f"Confianza del veredicto: {_conf['level']}"
                        # Fase 4 (T2): el motivo del techo es el que lo puso (convergencia, una dimensión baja o la
                        # fuente oficial), no uno fijo.
                        + (f" (techo en {_conf['level']}: "
                           + ("; ".join(r.split(": ", 1)[1] for r in _conf.get("reasons") or []
                                        if r.startswith(f"techo en {_conf['level']}: ")) or "techo de la confianza")
                           + f"; sin techo sería {_conf['capped_from']})" if _conf.get("capped_from") else "")
                        + (f". Contrae el atractivo del precio hacia 50 (factor {_pa.get('factor')}): sin ajustar "
                           f"{p_raw} → ajustado a {p_score}" if _pa.get("factor") is not None else "")
                        + ". La calidad del negocio no se contrae."),
        }

    # Etapa 9b: las medianas sectoriales están fijadas a mano: la web lo dice junto a la tabla.
    provisional_note = (None if _mkt else
                        "Medianas del sector: referencia PROVISIONAL, fijada a mano (no son medianas calculadas).")
    valuation = {"intro": val_txt, "columns": ["MÚLTIPLO", "EMPRESA", _bcol, "BRECHA", "LECTURA"],
                 "rows": mrows, "market_note": market_note, "provisional_note": provisional_note, "normalization_note": norm_note,
                 "intrinsic": {"intro": iv_txt, "rows": iv_rows, "graham_note": graham_note},
                 "dcf_params": dcf_params, "dcf_reliability": dcf_reliability_line,
                 "dcf_reliability_level": _rel.get("level"),
                 "dcf_reliability_tone": {"alta": 'pos', "media": 'warn', "baja": 'neg'}.get(_rel.get("level")),
                 "dcf_missing": dcf_missing,
                 "reverse_dcf": reverse_block,
                 "premortem": _premortem_block(a),
                 "ke_note": ke_note, "wacc_note": wacc_note, "wacc_breakdown": wacc_breakdown,
                 "sensitivity": sens}

    # ════════════════ 02 RENTABILIDAD ════════════════
    rent_txt = join_sentences([r_roe[2] if r_roe else None, (r_spread[2] if (r_spread and not is_financial) else None)])
    if not rent_txt and archetype in ("REIT", "GROWTH_PRE_PROFIT"):
        _rb = [x for x in (breakdown.get("Rentabilidad") or {}).get("adjustments") or []
               if x.get("metric") not in ("No aplica", "Cobertura")]
        rent_txt = join_sentences([f"{x['metric']} de {x['value']}: {x['reason'].split(' (')[0].lower()}"
                                   + (f", {x['reason'].split(' - ', 1)[1]}" if ' - ' in x['reason'] else "")
                                   for x in _rb])
    ret_defs = [
        ("roe", "ROE", km.get("roe"), sector_bench.get("roe"), True, "pct"),
        ("roa", "ROA", km.get("roa"), sector_bench.get("roa"), True, "pct"),
        ("roic", "ROIC", km.get("roic"), sector_bench.get("roic"), True, "pct"),
        ("gross_margin", "Margen bruto", km.get("gross_margin"), sector_bench.get("gross_margin"), True, "pct"),
        ("operating_margin", "Margen operativo" + (EBIT_ESTIMATED_SUFFIX if ebit_estimated(a) else ""),
         km.get("operating_margin"), sector_bench.get("operating_margin"), True, "pct"),
        ("net_margin", "Margen neto", km.get("net_margin"), sector_bench.get("net_margin"), True, "pct"),
    ]
    _ret_na = {"roe": "roe", "roa": "roa", "roic": "roic_wacc", "gross_margin": "gross_margin",
               "operating_margin": "operating_margin", "net_margin": "net_margin"}
    prows = []
    for key, lab, val, bench, hb, fm in ret_defs:
        if _ret_na.get(key) in _na_keys:
            # Etapa 9a: lo que no aplica al arquetipo no se lee.
            prows.append(_row(key, lab, fv(val, fm), not_applicable_text(archetype), 'neu', "no_aplica", "—", "—",
                              not_app.get(_ret_na[key]) or None))
            continue
        if key == "roic" and val is None and km.get("roic_reason"):
            prows.append(_row(key, lab, "—", "No significativo", 'neu', "no_significativo", "—", "—",
                              km.get("roic_reason")))
            continue
        r = _rvs(lab, val, bench, hb, fm) if bench else None
        prows.append(_row(key, lab, fv(val, fm), r[0] if r else "—", r[1] if r else None,
                          "con_dato" if val is not None else "sin_dato", fv(bench, fm) if bench else "—",
                          r[3] if r else "—", r[2] if r else None))
    if not is_financial and km.get("roic_wacc_spread") is not None and r_spread:
        prows.append(_row("roic_wacc_spread", "Spread ROIC − WACC", f"{km['roic_wacc_spread'] * 100:+.1f} pp",
                          r_spread[0], r_spread[1], "con_dato", "> 0", "—", r_spread[2]))
    # Etapa 9a: métricas de rentabilidad de la rama (REIT: FFO; pre-beneficio: márgenes de su fase).
    for x in (breakdown.get("Rentabilidad") or {}).get("adjustments") or []:
        if archetype in ("REIT", "GROWTH_PRE_PROFIT") and x.get("metric") not in ("No aplica", "Cobertura",
                                                                                  "Margen bruto", "Margen operativo"):
            prows.append(_row(_slug(x["metric"]), x["metric"], str(x.get("value", "")),
                              _SEV_LAB.get(x.get("severity"), "—"), _SEV_TONE.get(x.get("severity"), 'neu'),
                              "con_dato", "—", "—", x.get("reason")))
    # ROCE (etapa 6): solo MATURE y CYCLICAL; "No aplica" o "Sin dato", nunca 0%.
    _roce_state = km.get("roce_state")
    if _roce_state == "no_aplica":
        prows.append(_row("roce", "ROCE", "—", not_applicable_text(archetype), 'neu', "no_aplica", "—", "—"))
    elif _roce_state == "sin_dato":
        prows.append(_row("roce", "ROCE", "—", "Sin dato", 'neu', "sin_dato", "—", "—"))
    elif _roce_state == "ok":
        prows.append(_row("roce", "ROCE (EBIT / capital empleado)", fv(km.get("roce"), "pct"), "Antes de impuestos",
                          None, "con_dato", "—", "—"))
        if km.get("roce_avg") is not None:
            prows.append(_row("roce_avg", f"ROCE promedio ({km.get('roce_years')} ejercicios"
                              + (", ciclo incompleto)" if km.get("roce_cycle_incomplete") else ")"),
                              fv(km.get("roce_avg"), "pct"), "Ciclo medio", None, "con_dato", "—", "—"))
    _div = km.get("roce_roic_divergence") or {}
    div_note = None
    if _div.get("diverges"):
        div_note = (f"Divergencia ROCE–ROIC: ROCE {fv(km.get('roce'), 'pct')} frente a ROIC {fv(km.get('roic'), 'pct')} "
                    f"({_div['gap'] * 100:+.1f} pp, más de {cfg('thresholds.roce.divergence_pp') * 100:.0f} pp). "
                    "Causas probables: " + "; ".join(_div.get("causes") or []) + ".")
    # Etapa 9b: lo que no aplica al arquetipo (OCF y FCF en bancos) lo dice, no "N/A".
    _na_txt = not_applicable_text(archetype)
    def _fig(raw, comp):
        return _na_txt if (raw is None and comp in _na_keys) else fv(raw, "money")
    figures = [["Ingresos", fv(km.get("revenue"), "money"), "EBITDA", _fig(km.get("ebitda"), "ev_ebitda")],
               ["Beneficio operativo" + (EBIT_ESTIMATED_SUFFIX if ebit_estimated(a) else ""),
                _fig(km.get("operating_income"), "operating_margin"), "Beneficio neto",
                fv(km.get("net_income"), "money")],
               ["Flujo de caja operativo", _na_txt if "ocf" in _na_keys else fv(km.get("operating_cash_flow"), "money"),
                "Flujo de caja libre", _na_txt if "fcf" in _na_keys else fv(km.get("free_cash_flow"), "money")],
               ["EPS", fv(km.get("eps"), "price"), "Valor en libros / acción", fv(km.get("book_value_per_share"), "price")]]
    _record(div_note, _claim("roce"), source="display.roce")
    # Fase 3 (T6): lecturas de calidad que informan (no puntúan): DuPont, margen FCF con tendencia, SBC, regla de 40.
    _qrd = a.get("quality_readings") or {}
    _QR_FIELDS = {"dupont": ("DuPont del ROE", "current.roe"), "fcf_margin": ("Margen FCF con tendencia", "latest"),
                  "sbc_cost": ("Compensación en acciones", "sbc_to_revenue"),
                  "rule_of_40": ("Regla de 40", "value"), "coverage": ("Cobertura de intereses", "ebit")}

    def _qr_items(keys):
        items = []
        for k in keys:
            x = _qrd.get(k) or {}
            if not x.get("text"):
                continue
            lab, path = _QR_FIELDS[k]
            val = x
            for part in path.split("."):
                val = (val or {}).get(part) if isinstance(val, dict) else None
            _record(x["text"], _claim("figure", field=f"quality_readings.{k}.{path}", value=val),
                    source="display.quality_readings")
            tone = ({"mejora": "pos", "empeora": "warn"}.get(x.get("direction"), "neu") if k == "fcf_margin"
                    else ("pos" if x.get("meets") else "warn") if k == "rule_of_40" else "neu")
            items.append({"key": k, "label": lab, "text": x["text"], "tone": tone})
        return items
    profitability = {"intro": rent_txt, "columns": ["MÉTRICA", "EMPRESA", _bcol, "BRECHA", "LECTURA"],
                     "rows": prows, "divergence_note": div_note, "figures": figures,
                     "quality_readings": _qr_items(("dupont", "fcf_margin", "sbc_cost", "rule_of_40")),
                     # fase 1 (punto 9): lectura del ROCE = comparación con el ROIC (nota de divergencia o "en línea")
                     "roce_reading": div_note or roce_reading}

    # ════════════════ 03 SOLIDEZ ════════════════
    # En REIT manda la deuda neta/EBITDA; el D/E (informativo) va detrás.
    _lev = [r_nde, r_de] if archetype in ("REIT", "UTILITY") else [r_de, r_nde]
    sol_txt = join_sentences([r_rw[2] if r_rw else None, r_cr[2] if r_cr else None, *[r[2] for r in _lev if r],
                              r_ic[2] if r_ic else None, r_pay[2] if r_pay else None])
    sol_defs = [
        *([("runway", "Runway", None, "runway", r_rw)] if archetype == "GROWTH_PRE_PROFIT" else []),
        ("current_ratio", "Current ratio", km.get("current_ratio"), "mult", r_cr),
        ("quick_ratio", "Quick ratio", km.get("quick_ratio"), "mult", None),
        ("cash_ratio", "Cash ratio", km.get("cash_ratio"), "mult", None),
        ("de", "Deuda / Equity", km.get("de"), "mult", r_de),
        ("debt_to_assets", "Deuda / Activos", km.get("debt_to_assets"), "pct", None),
        ("net_debt_to_ebitda", "Deuda neta / EBITDA", km.get("net_debt_to_ebitda"), "mult", r_nde),
        ("interest_coverage", "Cobertura de intereses", km.get("interest_coverage"), "mult", r_ic),
        ("payout_ratio", "Payout sobre FFO" if km.get("payout_basis") == "ffo" else "Payout del dividendo",
         km.get("payout_ratio"), "pct", r_pay),
    ]
    srows = []
    # Fase 2b (T5): en un banco, D/E y deuda / activos no se calculan (main: su deuda no entra en las ratios de
    # apalancamiento de empresa); la fila queda como "No aplica" con el motivo.
    _bank_na = {k.split(".", 1)[1] for k, v in ((a.get("data_provenance") or {}).get("fields") or {}).items()
                if k.startswith("key_metrics.") and (v or {}).get("source") == "politica_arquetipo"}
    for key, lab, val, fm, rd in sol_defs:
        if key in ("de", "debt_to_assets") and key in _bank_na:
            srows.append(_row(key, lab, "—", DE_NOT_APPLICABLE if key == "de" else "No aplica", None, "no_aplica",
                              text=BANK_LEVERAGE_NA))
            continue
        if key == "interest_coverage" and ic_state == "sin_carga" and rd:   # fase 1: ratio sin sentido, lectura +
            # con_dato: la web pinta la lectura ("Sin carga financiera"), no el estado ("No significativo")
            srows.append(_row(key, lab, "Sin carga", rd[0], rd[1], "con_dato", text=rd[2]))
            continue
        if (key == "interest_coverage" and ic_state == "no_significativo") or \
                (key == "net_debt_to_ebitda" and nde_state == "no_significativo"):
            srows.append(_row(key, lab, "—", rd[0], rd[1], "no_significativo", text=rd[2]))
            continue
        if fm == "runway":
            if r_rw:
                srows.append(_row(key, lab, "Autofinanciada" if _rw["state"] == "autofinanciada"
                                  else f"{_rw['years']:.1f} años", r_rw[0], r_rw[1], text=r_rw[2]))
            else:
                srows.append(_row(key, lab, "—", "Sin dato", None, "sin_dato"))
            continue
        if key == "current_ratio" and "current_ratio" in _na_keys:
            srows.append(_row(key, lab, "—", "No aplica", None, "no_aplica",
                              text=not_app.get("current_ratio") or None))   # REIT (etapa 7)
            continue
        if val is None:
            continue
        if is_financial and key == "de":
            srows.append(_row(key, lab, "—", DE_NOT_APPLICABLE, None, "no_aplica"))
            continue
        if key == "de" and de_mode == "no_aplica":   # etapa 11b: UTILITY
            srows.append(_row(key, lab, "—", "No aplica", None, "no_aplica", text=not_app.get("de") or None))
            continue
        if key == "interest_coverage" and ic_state == "negativa":
            srows.append(_row(key, lab, IC_NEGATIVE, rd[0], rd[1], text=rd[2]))
            continue
        state = "no_significativo" if (key == "de" and de_mode == "no_significativo") else "con_dato"
        srows.append(_row(key, lab, fv(val, fm), rd[0] if rd else "—", rd[1] if rd else None, state,
                          text=rd[2] if rd else None))
    balance = (f"Balance — deuda total {fv(km.get('total_debt'), 'money')} · caja {fv(km.get('cash'), 'money')} · "
               f"patrimonio {fv(km.get('total_equity'), 'money')} · activos {fv(km.get('total_assets'), 'money')}")
    _dprov = (a.get("data_provenance") or {}).get("debt") or {}
    if _dprov.get("captive_excluded"):
        balance += (f". La deuda no incluye la de la financiera cautiva ({fv(_dprov['captive_excluded'], 'money')}): "
                    "financia su cartera de clientes, no la actividad industrial")
    elif _dprov.get("captive_unseparable"):
        balance += (f". La deuda incluye la de la financiera cautiva ({_dprov['captive_unseparable']}), que no se "
                    "puede separar con datos estructurados: el apalancamiento de la actividad industrial es menor")
    solvency = {"intro": sol_txt, "columns": ["MÉTRICA", "VALOR", "LECTURA"], "rows": srows, "balance": balance,
                "quality_readings": _qr_items(("coverage",))}

    # ════════════════ 04 CRECIMIENTO ════════════════
    gro_txt = join_sentences([r_grev[2] if r_grev else None, r_gearn[2] if r_gearn else None,
                              r_bb[2] if r_bb else None])
    # Etapa 9b: primero la cifra que PUNTÚA (CAGR a 3 años, ciclo medio en CYCLICAL, retorno
    # total por acción en REIT) con su lectura; el interanual de la fuente, informativo y rotulado.
    _per = "ciclo medio" if _cyc else "CAGR 3 años"
    _eps_na = "eps_growth" in _na_keys
    gro_defs = [
        (("total_return", "Retorno total por acción (dividendo + FFO por acción, 3 años)", g_rev, "pct", r_grev)
         if archetype == "REIT" else
         ("revenue_growth", f"Crecimiento de ingresos{' por acción' if _rev_ps else ''} ({_per})", g_rev, "pct",
          r_grev)),
        ("revenue_growth_yoy", "Crecimiento de ingresos (último ejercicio)", km.get("revenue_growth"), "pct", None),
        ("earnings_growth", f"Crecimiento del BPA ({_per})", None if _eps_na else g_eps, "pct", r_gearn),
        ("earnings_growth_yoy", "Crecimiento del BPA (último ejercicio)", None if _eps_na else km.get("earnings_growth"),
         "pct", None),
        ("buyback_yield", "Buyback yield (recompras netas)", km.get("buyback_yield"), "pct", r_bb),
        ("shareholder_yield", "Shareholder yield (div. + recompras)", km.get("shareholder_yield"), "pct", None),
        ("dividend_yield", "Dividend yield", km.get("dividend_yield"), "pct", None),
    ]
    grows = []
    # Fase 2b (T2): el dividendo indicado llega en la moneda y la clase del precio; su fila dice cuánto es al año, de
    # dónde sale y lo que el control en los dos sentidos encontró (subida, extraordinario, recorte). "Sin dato" solo
    # si la empresa paga y ninguna fuente cuadra, con el motivo; el shareholder yield lo sigue.
    _div = (a.get("data_provenance") or {}).get("dividend") or {}
    _dy_bad = next((f for f in a.get("data_validation") or [] if f.get("rule") == "dividendo_sin_fuente"), None)
    for key, lab, val, fm, rd in gro_defs:
        if val is None and _dy_bad and key in ("dividend_yield", "shareholder_yield"):
            grows.append(_row(key, lab, NO_DATA, "Sin dato", None, "sin_dato",
                              text=_dy_bad["reason"].replace("; sin dato, no puntúa", "") + "; no puntúa"))
            continue
        if val is None:
            continue
        txt = rd[2] if rd else None
        if key == "dividend_yield":
            txt = dividend_text(_div) or txt
        grows.append(_row(key, lab, fv(val, fm), rd[0] if rd else "—", rd[1] if rd else None, text=txt))
    # Fase 3 (T4, §1.4): en un banco, el margen de intereses aparte de los ingresos netos que puntúan (informativo).
    _nii_g = xm.get("net_interest_income_cagr_3y") if classification.get("subtype") == "banco" else None
    if _nii_g is not None:
        _nii_sh = xm.get("net_interest_income_share")
        _nii_txt = (f"el margen de intereses {'crece' if _nii_g >= 0 else 'se contrae'} un {_pct(abs(_nii_g))} anual "
                    "en 3 años" + (f" y es el {_pct(_nii_sh, 0)} de los ingresos netos" if _nii_sh else "")
                    + "; informativo, no puntúa")
        r_nii = ("Informativo", 'neu', _nii_txt)
        if _claims_active():
            _rec(r_nii, _claim("growth", field="archetype_metrics.net_interest_income_cagr_3y", value=_nii_g,
                               what="margen_intereses", cagr=True, archetype=archetype))
        _at = next((i + 1 for i, r in enumerate(grows) if r.get("key") == "revenue_growth_yoy"), len(grows))
        grows.insert(_at, _row("net_interest_income_growth", "Margen de intereses (CAGR 3 años)", fv(_nii_g, "pct"),
                               "—", None, text=_nii_txt))
    # Etapa 9a: BPA frente a ingresos, informativo (no puntúa: Crecimiento ya puntúa ambos).
    _evr = a.get("eps_vs_revenue_growth")
    evr_note = None
    if _evr:
        grows.append(_row("eps_vs_revenue", "BPA frente a ingresos (informativo)", f"{_evr['gap'] * 100:+.1f} pp",
                          _evr["label"], {"expansion": 'pos', "compresion": 'warn'}.get(_evr["state"], 'neu'),
                          text=_evr.get("reading")))
        evr_note = (f"BPA frente a ingresos: BPA {_evr['eps_growth'] * 100:+.1f}% frente a ingresos "
                    f"{_evr['revenue_growth'] * 100:+.1f}% (los crecimientos que puntúa Crecimiento): {_evr['reading']}. "
                    "Dato informativo, no puntúa: Crecimiento ya puntúa el BPA y los ingresos por separado.")
    # Por acción (REIT, etapa 6) y ajuste SBC (pre-beneficio, etapa 9a): dato que ya puntúa Crecimiento.
    growth_extra = []
    for x in (breakdown.get("Crecimiento") or {}).get("adjustments") or []:
        if x.get("metric") in ("No aplica", "Cobertura"):
            continue
        growth_extra.append({"metric": x.get("metric"), "value": str(x.get("value", "")), "reason": x.get("reason")})
    range52 = None
    if pos52 is not None:
        _e = [0, *_PDF_BANDS["pos52_bounds"], 100]
        range52 = {
            "pos": pos52, "low": fv(l52, "price"), "high": fv(h52, "price"), "price": fv(price, "price"),
            "zones": [{"from": lo, "to": hi} for lo, hi in zip(_e, _e[1:])],
            "axis": ("Muestra dónde cotiza el precio dentro de su rango anual. Es contexto de mercado: no es una "
                     "señal de valoración ni mide la calidad del negocio."),
            "reading": _rd(r_52),
            "caption": f"Precio actual {fv(price, 'price')} — posición {pos52:.0f}% del rango.",
            "zones_note": ("Tramos: mínimos, parte baja, zona media, parte alta y máximos. Es contexto de mercado: la "
                           "posición en el rango no es una señal de valoración."),
        }
    growth = {"intro": gro_txt, "columns": ["MÉTRICA", "VALOR", "LECTURA"], "rows": grows,
              "eps_vs_revenue_note": evr_note, "score_components": growth_extra, "range52": range52}

    # ════════════════ 05 EVALUACIÓN INSTITUCIONAL ════════════════
    inst_cards = []
    if fin_health and isinstance(fin_health, dict) and fin_health.get("score") is not None:
        fh_tone = 'pos' if fin_health.get("level") in ("STRONG", "GOOD") else \
                  'warn' if fin_health.get("level") == "NEUTRAL" else 'neg'
        det_txt = " · ".join(d.get("detail", "") for d in (fin_health.get("details") or [])[:4])
        inst_cards.append({"key": "financial_health", "value": f"{fin_health['score']}/10", "tone": fh_tone,
                           "title": "Salud financiera (sector financiero)", "subtitle": FIN_HEALTH_LEVEL_ES.get(fin_health.get("level"), ""),
                           "state": "con_dato",
                           "body": (fin_health.get("interpretation", "") + ". " + det_txt).strip()})
    if altman and altman.get("applicable") is False:
        inst_cards.append({"key": "altman", "value": "n/a", "tone": 'neu', "title": "Altman Z-Score",
                           "subtitle": "No aplica", "state": "no_aplica", "body": altman.get("interpretation", "")})
        if r_rw:    # GROWTH_PRE_PROFIT: el runway sustituye al Altman en Solidez
            inst_cards.append({"key": "runway", "value": "FCF+" if _rw["state"] == "autofinanciada"
                               else f"{_rw['years']:.1f}", "tone": r_rw[1], "title": "Runway", "subtitle": r_rw[0],
                               "state": "con_dato",
                               "body": (f"{cap(r_rw[2])} Runway = (caja + inversiones a corto plazo) / quema anual "
                                        "de FCF; sustituye al Altman en Solidez.")})
    elif altman and altman.get("available") is False and not is_financial \
            and (altman.get("details") or {}).get("reason") == "sin_dato":
        inst_cards.append({"key": "altman", "value": "—", "tone": 'neu', "title": "Altman Z-Score",
                           "subtitle": "Sin dato", "state": "sin_dato",
                           "body": f"{altman.get('interpretation', '')}. Altman exige todos sus componentes; "
                                   f"no se estima con ceros."})
    elif altman and altman.get("z_score") is not None and not is_financial:
        z, zone = altman.get("z_score", 0), altman.get("zone", "grey")
        z_tone = 'pos' if zone == 'safe' else 'warn' if zone == 'grey' else 'neg'
        z_lab = "Zona segura" if zone == 'safe' else "Zona gris" if zone == 'grey' else "Zona de riesgo"
        _zd = altman.get("details") or {}  # umbrales del modelo usado (Z, Z' o Z'')
        _vars = ("EBIT y patrimonio contable frente al pasivo" if "Z''" in (altman.get("model") or "")
                 else "EBIT, valor de mercado y ventas")
        _alt_ref = bool((a.get("business_model") or {}).get("altman_referential"))
        inst_cards.append({"key": "altman", "value": f"{z:.2f}", "tone": 'neu' if _alt_ref else z_tone,
                           "title": "Altman Z-Score",
                           "subtitle": ("Referencial" if _alt_ref else z_lab), "state": "con_dato",
                           "body": (f"{altman.get('interpretation', '')}. El modelo Altman Z pondera capital de trabajo, "
                                    f"beneficios retenidos, {_vars} para estimar el riesgo de insolvencia a 2 años: por "
                                    f"encima de {_zd.get('safe_threshold', 0):.2f} el riesgo es bajo; por debajo de "
                                    f"{_zd.get('grey_threshold', 0):.2f}, elevado."
                                    + (" En esta industria es solo una referencia: el modelo se calibró con "
                                       "manufactureras de circulante positivo y aquí pesan los arrendamientos y el "
                                       "circulante negativo estructural; no puntúa en Solidez." if _alt_ref else ""))})
    pio_criteria = []
    if piotroski and piotroski.get("applicable") is False:
        inst_cards.append({"key": "piotroski", "value": "n/a", "tone": 'neu', "title": "Piotroski F-Score",
                           "subtitle": "No aplica", "state": "no_aplica",
                           "body": (f"{piotroski.get('interpretation', '')}. El F-Score verifica mejoras contables "
                                    "(flujo operativo, liquidez, margen bruto, rotación) que no tienen sentido en "
                                    "este balance; no cuenta en Calidad.")})
    elif piotroski and piotroski.get("score") is not None:
        f_sc, f_max = piotroski.get("score", 0), piotroski.get("max_score", 9)
        f_n = piotroski.get("evaluated", f_max)
        f_scaled = piotroski.get("scaled_score")
        f_conclusive = piotroski.get("conclusive", True)
        f_for_tone = f_scaled if f_scaled is not None else f_sc
        # Escala única 8/6/4/2 (decisión 2 de la etapa 4).
        _pb = cfg("valuation.models.piotroski.bands")
        f_tone = ('neu' if not f_conclusive else
                  'pos' if f_for_tone >= _pb[1] else 'warn' if f_for_tone >= _pb[2] else 'neg')
        f_body = (f"{piotroski.get('interpretation', '')}. El F-Score de Piotroski verifica 9 señales contables de "
                  f"mejora en rentabilidad, estructura de capital y eficiencia operativa"
                  + (f" ({piotroski.get('fiscal_year')})" if piotroski.get("fiscal_year") else "") + ".")
        if f_n < f_max:
            # Cobertura (etapa 5): los criterios sin dato no cuentan como incumplidos.
            f_body += (f" Evaluados {f_n} de {f_max} criterios (el resto, sin dato)"
                       + (f"; resultado escalado a base {f_max}: {f_scaled:.1f}/{f_max}." if f_scaled is not None
                          else "; cobertura insuficiente para un resultado concluyente."))
        _pcav = (a.get("business_model") or {}).get("piotroski_caveat")
        if _pcav:       # fase 3 (T6, §5): qué criterios informan poco en la industria
            f_body += " " + _pcav
        inst_cards.append({"key": "piotroski", "value": f"{f_sc}/{f_n}" if f_n < f_max else f"{f_sc}/{f_max}",
                           "tone": f_tone, "title": "Piotroski F-Score", "subtitle": str(piotroski.get("level", "")),
                           "state": "con_dato", "body": f_body})
        # Fase 2b (T3, base temporal única): los criterios comparan ejercicios (FY frente a FY), no el TTM del resto
        # del informe; cada detalle lo dice (AAPL: "el flujo operativo no llega al beneficio" es del FY2025, y el TTM
        # da OCF/beneficio 1.06).
        _fy0 = str(piotroski.get("fiscal_year") or "").split(" ")[0]
        for k, crit in (piotroski.get("details") or {}).items():
            st = crit.get("state") or ("cumple" if crit.get("passed") else "no_cumple")
            pio_criteria.append({"key": k, "label": PIOTROSKI_LABELS.get(k, k.replace("_", " ").title()),
                                 "detail": (f"{_fy0}: " if _fy0.startswith("FY") else "") + (crit.get("detail") or "")[:72],
                                 "status": {"cumple": "Cumple", "no_cumple": "No cumple", "sin_dato": "Sin dato"}[st],
                                 "tone": {"cumple": 'pos', "no_cumple": 'neg', "sin_dato": 'neu'}[st]})

    # Desglose por categoría (anexo de la sección 05)
    bd = None
    if breakdown:
        _mx = cfg('thresholds.score.valoracion.multiples_block_max_by_members')
        bd_intro = ("Cada categoría parte de una base neutral de 10/20. La columna Ajuste muestra cuánto suma o "
                    "resta cada indicador según la banda en la que cae. Solidez, Rentabilidad, Calidad de ganancias y "
                    "Crecimiento forman la calidad del negocio; Valoración, el atractivo del precio. Las categorías no "
                    "concluyentes se excluyen y cada puntuación se reescala a 100 sobre las demás. En Valoración, P/E, "
                    "Forward P/E, P/FCF, EV/EBITDA y PEG forman un solo bloque: su ajuste individual se muestra entre "
                    "paréntesis y puntúa a través del Bloque de múltiplos (promedio de los ajustes reescalados a ±1, "
                    "máximo "
                    + " / ".join(f"±{m} con {i + 1}{'+' if i == 2 else ''}" for i, m in enumerate(_mx))
                    + " miembros; en bancos y aseguradoras, P/B y P/TBV forman su propio bloque).")
        bd_cats = []
        for cat_name, cat in breakdown.items():
            cs, cm = cat.get("score", 0), cat.get("max", 20) or 20
            pctc = cs / cm * 100
            conclusive = cat.get("conclusive") is not False
            items = []
            for adj in cat.get("adjustments") or []:
                v = adj.get("adjustment", 0)
                sev = adj.get("severity", "")
                if v > 0:
                    tone_a = 'pos'
                elif v < 0:
                    tone_a = 'neg' if sev in ("severe", "critical") else 'warn'
                else:
                    tone_a = 'neu'
                sign = f"+{v}" if v > 0 else str(v)
                state = "con_dato"
                if adj.get("metric") == "No aplica":
                    sign, tone_a, state = "n/a", 'neu', "no_aplica"
                elif adj.get("in_block"):
                    # Lectura individual; puntúa a través del "Bloque de múltiplos".
                    sign, tone_a = f"({sign})", 'neu'
                items.append({"metric": adj.get("metric", ""), "value": _es_value(adj.get("value", "")), "sign": sign,
                              "tone": tone_a, "reason": adj.get("reason", ""), "in_block": bool(adj.get("in_block")),
                              "state": state})
            bd_cats.append({"name": cat_name, "score": cs, "max": cm, "pct": pctc,
                            "tone": category_tone(pctc), "conclusive": conclusive,
                            "group": ("quality" if cat_name in cfg("thresholds.score.quality.categories")
                                      else "price" if cat_name in cfg("thresholds.score.price.categories") else None),
                            "text": (None if conclusive else
                                     f"No concluyente (cobertura {(cat.get('coverage') or 0):.0%}): excluida de su "
                                     "puntuación, que se reescala sobre las demás categorías"),
                            "items": items})
        bd = {"intro": bd_intro, "coverage_notes": cover_notes, "categories": bd_cats}
    institutional = {"cards": inst_cards, "piotroski_criteria": pio_criteria, "breakdown": bd}

    # ════════════════ 06 ALERTAS ════════════════
    alert_groups = [{"key": k, "title": t, "tone": tn,
                     "items": [{"category": x.get("category", ""), "reason": x.get("reason", ""),
                                "detail": x.get("detail", "") if x.get("detail") != x.get("reason") else ""}
                               for x in alerts.get(k) or []]}
                    for k, t, tn in (("red_flags", "Riesgos", 'neg'), ("warnings", "Advertencias", 'warn'),
                                     ("strengths", "Fortalezas", 'pos'))]

    # Metodología
    _models = [m for k, m in (("altman", "Altman (1968)"), ("piotroski", "Piotroski (2000)"),
                              ("graham", "número de Graham"), ("dcf", "un DCF multietapa con WACC estimado por CAPM"))
               if k not in _na_keys and (k != "graham" or graham_shown)]
    if archetype == "FINANCIAL":
        _models.append("P/B y P/TBV justificados por el retorno (Gordon)")
    elif archetype == "REIT":
        _models.append("P/FFO y rentabilidad sobre el FFO")
    elif archetype == "UTILITY":
        _models.append("P/E frente al sector y rentabilidad por dividendo")
    models_txt = ("los modelos de " + ", ".join(_models)) if _models else "los modelos de su arquetipo"

    D = {
        "version": 1,
        "archetype": archetype,
        "archetype_label": _shown_archetype_label(a, archetype),
        "na_keys": sorted(_na_keys),
        "benchmark": {"profile": "market" if _mkt else "sector", "ref": _ref, "column": _bcol,
                      "vs": "vs mercado" if _mkt else "vs sector", "thresholds_key": _thkey},
        "readings": readings,
        "cover": cover,
        "summary": summary,
        "confidence": confidence,
        # Fase 1 (D1): códigos y motivos técnicos, solo en el anexo final del PDF ("Detalle técnico para
        # auditoría"). La web no lo muestra.
        "annex": {"title": "Detalle técnico para auditoría",
                  "items": [{"label": "Clasificación", "text": t} for t in cls_detail]
                           + annex_conf + official_source_annex(a)
                           + [r for r in (provenance_annex(a),) if r]},
        "sections": {"market": _market_block(a), "valuation": valuation, "profitability": profitability,
                     "solvency": solvency,
                     "growth": growth, "institutional": institutional,
                     # Histórico (dato bruto): columnas que no aplican al arquetipo, con su texto.
                     "historical": {"not_applicable": {
                         f: not_applicable_text(archetype)
                         for f, comp in (("free_cash_flow", "fcf"), ("fcf_margin", "fcf"),
                                         ("gross_margin", "gross_margin"), ("operating_margin", "operating_margin"))
                         if comp in _na_keys}},
                     "alerts": {"counts": summary["alert_counts"], "groups": alert_groups}},
        "methodology": {"models": _models, "models_text": models_txt,
                        "ratios_text": "ratios del último ejercicio" if _annual else "ratios TTM y del último ejercicio"},
        "pe_label": _PE,
        "tooltips": band_tooltips(a, sector_bench, _th, _mkt, _ref, _na_keys, de_mode, _cyc),
    }
    # Etapa 9c: datos numéricos de los gráficos de la web (zonas de la misma config que las lecturas).
    from display_charts import build_charts
    D["charts"] = build_charts(a, D, sector_bench, th=_th, market=_mkt, de_mode=de_mode)
    if _claims_active():   # fase 1 (guardián narrativo): sin efecto en la salida
        _declare_engine_texts(a, D)
    return D


# ══════════════════════ BANDAS DE LOS TOOLTIPS (decisión C) ══════════════════════
# El tooltip de una métrica muestra SOLO las bandas aplicadas a esta empresa (su
# arquetipo y su benchmark), generadas desde la misma config que usa cada lector de
# arriba. tests/test_display.py comprueba, banda a banda, que el lector devuelve la
# etiqueta de la banda para un valor dentro de ella.
def _f_pct(v):
    s = f"{v * 100:.1f}".rstrip("0").rstrip(".")
    return f"{s}%"


def _f_mult(v):
    return f"{v:.1f}x"


def _f_num(v):
    return f"{v:.2f}"


def _f_years(v):
    return f"{v:.1f} años"


def _f_pp(v):
    return f"{v * 100:.0f}%"


def _desc(bounds, labels, tones, f, strict=False):
    """Tramos 'mayor es mejor' (≥ b0, b1–b0, …, < b_last). strict: '>' en lugar de '≥'."""
    ge = ">" if strict else "≥"
    out = [{"range": f"{ge} {f(bounds[0])}", "label": labels[0], "tone": tones[0]}]
    for i in range(1, len(bounds)):
        out.append({"range": f"{f(bounds[i])} – {f(bounds[i - 1])}", "label": labels[i], "tone": tones[i]})
    out.append({"range": f"< {f(bounds[-1])}", "label": labels[len(bounds)], "tone": tones[len(bounds)]})
    return out


def _asc(bounds, labels, tones, f, strict=False):
    """Tramos 'menor es mejor' (≤ b0, b0–b1, …, > b_last). strict: '<' en lugar de '≤'."""
    le, gt = ("<", "≥") if strict else ("≤", ">")
    out = [{"range": f"{le} {f(bounds[0])}", "label": labels[0], "tone": tones[0]}]
    for i in range(1, len(bounds)):
        out.append({"range": f"{f(bounds[i - 1])} – {f(bounds[i])}", "label": labels[i], "tone": tones[i]})
    out.append({"range": f"{gt} {f(bounds[-1])}", "label": labels[len(bounds)], "tone": tones[len(bounds)]})
    return out


def vs_bench_bands(bench, higher, fmt="mult"):
    """Bandas de la lectura frente a la mediana (read_vs_sector) expresadas en el valor de la métrica."""
    if bench in (None, 0):
        return []
    b0, b1 = _PDF_BANDS["vs_sector_bounds"]
    f = _f_pct if fmt == "pct" else _f_mult
    at = lambda d: bench + d / 100 * abs(bench)   # noqa: E731
    if higher:
        return _desc([at(b0), at(b1), at(-b1), at(-b0)],
                     ["Muy superior", "Superior", "En línea", "Inferior", "Muy inferior"],
                     ['pos', 'pos', 'neu', 'warn', 'neg'], f)
    return [{"range": f"≤ {f(at(-b0))}", "label": "Descuento profundo", "tone": 'pos'},
            {"range": f"{f(at(-b0))} – {f(at(-b1))}", "label": "Descuento", "tone": 'pos'},
            {"range": f"{f(at(-b1))} – {f(at(b1))}", "label": "En línea", "tone": 'neu'},
            {"range": f"{f(at(b1))} – {f(at(b0))}", "label": "Prima moderada", "tone": 'warn'},
            {"range": f"≥ {f(at(b0))}", "label": "Prima elevada", "tone": 'neg'}]


def score_bands(key, *, th=None, reit=False, utility=False, ffo=False, cycle=False, kind="revenue",
                de_threshold=None):
    """Bandas de la lectura de `key` (las del score donde la métrica puntúa)."""
    if key == "roe":
        T = cfg("thresholds.score.rentabilidad")
        th = th or ThresholdConfig()
        return _desc([th.roe_high * T["roe_high_mult"], th.roe_high, th.roe_low, T["roe_floor"], 0],
                     ["Excepcional", "Alto", "Competitivo", "Bajo", "Débil", "Negativo"],
                     ['pos', 'pos', 'neu', 'warn', 'neg', 'neg'], _f_pct)
    if key == "roic_wacc_spread":
        return _desc(cfg("thresholds.score.rentabilidad.spread_bounds"),
                     ["Crea mucho valor", "Crea valor", "Marginal", "Al límite", "Destruye valor"],
                     ['pos', 'pos', 'neu', 'warn', 'neg'], _f_pct)
    if key == "current_ratio":
        return _desc(cfg("thresholds.score.solidez.current_bounds"),
                     ["Holgada", "Sólida", "Justa", "Ajustada", "Tensión"],
                     ['pos', 'pos', 'neu', 'warn', 'neg'], _f_mult)
    if key == "de":
        T = cfg("thresholds.score.solidez")
        t = de_threshold or ThresholdConfig().debt_equity_high
        m = T["de_mults"]
        out = _asc([t * m[0], t, t * m[1], t * m[2]], ["Conservador", "Controlado", "Aceptable", "Elevado", "Alto"],
                   ['pos', 'pos', 'neu', 'warn', 'neg'], _f_mult)
        out[-1]["label"] += f" (Alto, servible con cobertura ≥ {T['de_mitigation_coverage']:.0f}x)"
        return [{"range": "< 0", "label": "Equity negativo", "tone": 'warn'}] + out
    if key == "interest_coverage" and utility:
        return _desc(cfg("thresholds.score.solidez.utility_coverage_bounds"),
                     ["Fuerte", "Adecuada", "En línea", "Ajustada", "Riesgo"],
                     ['pos', 'pos', 'neu', 'warn', 'neg'], _f_mult)
    if key == "interest_coverage":
        return _desc(cfg("thresholds.score.solidez.coverage_bounds"),
                     ["Muy holgada", "Sólida", "Aceptable", "Justa", "Crítica"],
                     ['pos', 'pos', 'neu', 'warn', 'neg'], _f_mult)
    if key == "net_debt_to_ebitda":
        cash = [{"range": "< 0x", "label": "Caja neta", "tone": 'pos'}]
        if reit or utility:
            return cash + _asc(cfg(f"thresholds.score.solidez.{'reit' if reit else 'utility'}_nde_bounds"),
                               ["Conservadora", "Adecuada", "En línea", "Elevada", "Alta"],
                               ['pos', 'pos', 'neu', 'warn', 'neg'], _f_mult)
        th = th or ThresholdConfig()
        return cash + _asc(nde_bounds(th), ["Baja", "Moderada", "Elevada", "Alta"],
                           ['pos', 'neu', 'warn', 'neg'], _f_mult, strict=True)
    if key == "runway":
        return ([{"range": "FCF > 0", "label": "Autofinanciada", "tone": 'pos'}]
                + _desc(cfg("thresholds.score.solidez.runway_bounds"), ["Holgado", "Cómodo", "Ajustado", "Crítico"],
                        ['pos', 'pos', 'warn', 'neg'], _f_years))
    if key == "payout_ratio":
        if ffo:
            return ([{"range": "< 0%", "label": "FFO negativo", "tone": 'neg'}]
                    + _asc(cfg("thresholds.score.calidad.reit_ffo_payout_bounds"),
                           ["Holgado", "Cubierto", "Justo", "Insostenible"], ['pos', 'pos', 'warn', 'neg'], _f_pp))
        b = _PDF_BANDS["payout_bounds"]
        return [{"range": "< 0%", "label": "Con pérdidas", "tone": 'neg'},
                {"range": f"< {_f_pp(b[0])}", "label": "Conservador", "tone": 'pos'},
                {"range": f"{_f_pp(b[0])} – {_f_pp(b[1])}", "label": "Sostenible", "tone": 'pos'},
                {"range": f"{_f_pp(b[1])} – {_f_pp(b[2])}", "label": "Exigente", "tone": 'warn'},
                {"range": f"{_f_pp(b[2])} – {_f_pp(b[3])}", "label": "Muy exigente", "tone": 'warn'},
                {"range": f"> {_f_pp(b[3])}", "label": "Insostenible", "tone": 'neg'}]
    if key in ("revenue_growth", "earnings_growth"):
        b = cfg(f"thresholds.score.crecimiento.{kind}_bounds")
        tol = cfg("thresholds.score.crecimiento.flat_tolerance")
        if cycle:
            out = _desc([b[1], b[2]], ["Sólido", "Moderado", "Plano"], ['pos', 'neu', 'warn'], _f_pct)
        else:
            out = _desc(list(b), ["Acelerado", "Sólido", "Moderado", "Plano"], ['pos', 'pos', 'neu', 'warn'], _f_pct)
        out[-1]["range"] = f"{_f_pct(-tol)} – {_f_pct(b[2])}"
        return out + [{"range": f"< {_f_pct(-tol)}", "label": "Contracción", "tone": 'neg'}]
    if key == "dcf_upside":
        return _desc([x * 100 for x in cfg("thresholds.score.valoracion.dcf_upside_bounds")],
                     ["Muy infravalorada", "Infravalorada", "Precio justo", "Prima", "Sobrevalorada"],
                     ['pos', 'pos', 'neu', 'warn', 'neg'], lambda v: f"{v:+.0f}%")
    if key == "graham":
        return _desc([_PDF_BANDS["graham_discount"], 0], ["Descuento Graham", "Cerca de Graham", "Sobre Graham"],
                     ['pos', 'neu', 'warn'], _f_pp)
    if key == "beta":
        return _asc(beta_bounds(th or ThresholdConfig()), ["Defensiva", "De mercado", "Volátil", "Muy volátil"],
                    ['pos', 'neu', 'warn', 'neg'], _f_num, strict=True)
    if key == "pos52":
        e = [0, *_PDF_BANDS["pos52_bounds"], 100]
        labs = ["En mínimos de 52 semanas", "Parte baja del rango", "Zona media del rango", "Parte alta del rango",
                "En máximos de 52 semanas"]
        return [{"range": f"{lo}% – {hi}%", "label": lab, "tone": 'neu'} for lo, hi, lab in zip(e, e[1:], labs)]
    if key == "buyback_yield":
        b = _PDF_BANDS["buyback_bounds"]
        return [{"range": f"≥ {_f_pct(b[0])}", "label": "Recompra intensiva", "tone": 'pos'},
                {"range": f"{_f_pct(b[1])} – {_f_pct(b[0])}", "label": "Recompra neta", "tone": 'pos'},
                {"range": f"{_f_pct(-b[1])} – {_f_pct(b[1])}", "label": "Neutra", "tone": 'neu'},
                {"range": f"≤ {_f_pct(-b[1])}", "label": "Dilución", "tone": 'neg'}]
    if key == "fcf_yield":
        b = _PDF_BANDS["fcf_yield_bounds"]
        return [{"range": "< 0%", "label": "Negativo", "tone": 'neg'},
                {"range": f"0% – {_f_pct(b[0])}", "label": "Bajo", "tone": 'warn'},
                {"range": f"{_f_pct(b[0])} – {_f_pct(b[1])}", "label": "Razonable", "tone": 'neu'},
                {"range": f"{_f_pct(b[1])} – {_f_pct(b[2])}", "label": "Atractivo", "tone": 'pos'},
                {"range": f"≥ {_f_pct(b[2])}", "label": "Alto", "tone": 'pos'}]
    raise KeyError(key)


def _score_level_bands(kind):
    b, labels = cfg(f"thresholds.score.{kind}.bands"), cfg(f"thresholds.score.{kind}.labels")
    tone = quality_tone if kind == "quality" else price_tone
    return _desc(list(b), list(labels), [tone(x) for x in labels], lambda v: f"{v:g}")


def band_tooltips(a, sector_bench, th, mkt, ref, na, de_mode, cyc):
    """{clave de métrica: {"tables": [{"title", "bands": [...]}], "note"}} con las bandas aplicadas."""
    km = a.get("key_metrics") or {}
    archetype = (a.get("classification") or {}).get("archetype") or "MATURE"
    reit = archetype == "REIT"
    utility = archetype == "UTILITY"
    who = "del mercado (S&P 500)" if mkt else "del sector"
    out: Dict[str, Any] = {}

    def add(key, title, bands, note=None):
        e = out.setdefault(key, {"tables": [], "note": None})
        if bands:
            e["tables"].append({"title": title, "bands": bands})
        if note:
            e["note"] = note

    # Frente a la mediana (columna LECTURA de las tablas de múltiplos y de rentabilidad).
    vs = [("pe", "pe", False, "mult", "pe"), ("forward_pe", "forward_pe", False, "mult", "forward_pe"),
          ("pb", "pb", False, "mult", None), ("peg", "peg", False, "mult", "peg"),
          ("ev_ebitda", "ev_ebitda", False, "mult", "ev_ebitda"), ("pfcf", "pfcf", False, "mult", "p_fcf"),
          ("fcf_yield", "fcf_yield", True, "pct", "p_fcf"), ("roe", "roe", True, "pct", "roe"),
          ("roa", "roa", True, "pct", "roa"), ("roic", "roic", True, "pct", "roic_wacc"),
          ("gross_margin", "gross_margin", True, "pct", "gross_margin"),
          ("operating_margin", "operating_margin", True, "pct", "operating_margin"),
          ("net_margin", "net_margin", True, "pct", "net_margin"),
          ("revenue_growth", "revenue_growth", True, "pct", None)]
    for key, bkey, hb, fm, nak in vs:
        if nak and nak in na:
            add(key, "", [], f"{not_applicable_text(archetype)}: no se lee.")
            continue
        bench = sector_bench.get(bkey)
        if bench:
            add(key, f"Frente a la mediana {who} ({_f_pct(bench) if fm == 'pct' else _f_mult(bench)})",
                vs_bench_bands(bench, hb, fm))
    # Bandas del score (texto de las secciones y del resumen).
    if "roe" not in na:
        add("roe", f"Bandas del score ({'mercado' if mkt else 'sector'})", score_bands("roe", th=th))
    if "roic_wacc" not in na and not archetype == "FINANCIAL":
        add("roic_wacc_spread", "Spread ROIC − WACC", score_bands("roic_wacc_spread"))
    if "current_ratio" not in na:
        add("current_ratio", "Bandas del score", score_bands("current_ratio"))
    else:
        add("current_ratio", "", [], f"{not_applicable_text(archetype)}.")
    if de_mode == "score":
        add("de", f"Bandas del score (umbral {who} {th.debt_equity_high:.1f}x)",
            score_bands("de", de_threshold=th.debt_equity_high))
    elif de_mode == "informativo":
        add("de", "", [], "Informativo: en un REIT el apalancamiento se mide por la deuda neta/EBITDA.")
    elif de_mode == "no_significativo":
        add("de", "", [], "No significativo: con caja neta, el D/E no mide apalancamiento.")
    elif de_mode == "no_aplica":
        add("de", "", [], f"{not_applicable_text(archetype)}: el apalancamiento se mide por la deuda neta/EBITDA.")
    else:
        add("de", "", [], DE_NOT_APPLICABLE + ".")
    add("interest_coverage", "Bandas de utility regulada" if utility else "Bandas del score",
        score_bands("interest_coverage", utility=utility))
    add("net_debt_to_ebitda", "Bandas de REIT" if reit else "Bandas de utility regulada" if utility
        else f"Umbrales del sector ({who})", score_bands("net_debt_to_ebitda", reit=reit, utility=utility, th=th))
    if archetype == "GROWTH_PRE_PROFIT":
        add("runway", "Años de caja frente a la quema de FCF", score_bands("runway"))
    ffo = km.get("payout_basis") == "ffo"
    add("payout_ratio", "Sobre el FFO" if ffo else "Sobre el beneficio", score_bands("payout_ratio", ffo=ffo))
    add("revenue_growth", "Bandas del score" + (" (ciclo medio)" if cyc else ""),
        score_bands("revenue_growth", cycle=cyc, kind="revenue"))
    if "eps_growth" not in na:
        add("earnings_growth", "Bandas del score" + (" (ciclo medio)" if cyc else ""),
            score_bands("earnings_growth", cycle=cyc, kind="eps"))
    else:
        add("earnings_growth", "", [], f"{not_applicable_text(archetype)}.")
    if not (a.get("not_applicable") or {}).get("dcf"):
        add("dcf_upside", "Bandas del DCF en Valoración", score_bands("dcf_upside"))
    if "graham" not in na and "pe" not in na:
        add("graham", "Margen frente al número de Graham", score_bands("graham"))
    add("beta", f"Umbrales del sector ({who})", score_bands("beta", th=th))
    add("pos52", "Posición en el rango (contexto, sin juicio de precio)", score_bands("pos52"))
    add("buyback_yield", "Bandas del informe", score_bands("buyback_yield"))
    if "p_fcf" not in na and not cyc:
        add("fcf_yield", "Bandas del informe", score_bands("fcf_yield"))
    add("quality", "Calidad del negocio (0–100)", _score_level_bands("quality"))
    add("price", "Atractivo del precio (0–100, contraído por la confianza)", _score_level_bands("price"))
    cb = _PDF_BANDS["category_tone_bounds"]
    add("category", "Puntos de la categoría sobre su máximo",
        _desc(list(cb), ["Fuerte", "Media", "Débil"], ['pos', 'warn', 'neg'], lambda v: f"{v:g}%"))
    pb = cfg("valuation.models.piotroski.bands")
    add("piotroski", "F-Score (0–9)", _desc([pb[1], pb[2]], ["Fuerte / bueno", "Neutral", "Débil / crítico"],
                                           ['pos', 'warn', 'neg'], lambda v: f"{v:g}"))
    _zd = (a.get("altman_z") or {}).get("details") or {}
    if _zd.get("safe_threshold") is not None and _zd.get("grey_threshold") is not None:
        add("altman", f"Umbrales del modelo {(a.get('altman_z') or {}).get('model') or 'Z'}",
            _desc([_zd["safe_threshold"], _zd["grey_threshold"]], ["Zona segura", "Zona gris", "Zona de riesgo"],
                  ['pos', 'warn', 'neg'], _f_num))
    return out
