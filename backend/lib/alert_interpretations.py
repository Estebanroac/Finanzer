"""
Finanzer — Motor de interpretación de señales (el "cerebro")
============================================================
Convierte los ratios crudos en FORTALEZAS / ADVERTENCIAS / RIESGOS con una
interpretación ADAPTATIVA de 1-2 líneas por ítem, con la fórmula:

    [qué es] + [por qué importa] + [matiz según magnitud / sector]

Determinista (sin LLM): la "inteligencia" vive en las bandas y el contexto,
igual que las lecturas read_* del PDF. Cada señal se gradúa por magnitud (no es
un umbral binario) y se adapta al sector (usa SECTOR_THRESHOLDS).

Salida: build_signals(...) -> {"red_flags": [...], "warnings": [...], "strengths": [...]}
Cada ítem: {"category", "reason" (headline), "detail" (1-2 líneas)} — misma
estructura que consumen el frontend (AlertGroup) y el PDF (alert_block).
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

try:
    from .financial_ratios import (SECTOR_THRESHOLDS, ThresholdConfig, growth_for_bands,
                                   interest_coverage_state, net_debt_ebitda_state)
    from .classify import CYCLICAL, FINANCIAL, GROWTH_PRE_PROFIT, MATURE, REIT, not_applicable
except ImportError:  # ejecución como script suelto
    from financial_ratios import (SECTOR_THRESHOLDS, ThresholdConfig, growth_for_bands,
                                  interest_coverage_state, net_debt_ebitda_state)
    from classify import CYCLICAL, FINANCIAL, GROWTH_PRE_PROFIT, MATURE, REIT, not_applicable


import re

from numfmt import MINUS, signed_pct
from settings import cfg

_A = cfg("thresholds.alerts")
_SC_SOLIDEZ = cfg("thresholds.score.solidez")   # bandas de deuda neta/EBITDA de REIT (etapa 9a)


# ── formato ──────────────────────────────────────────────────────────────
def _pct(v: Optional[float], dec: int = 1) -> str:
    return "N/A" if v is None else f"{v * 100:.{dec}f}%"


def _x(v: Optional[float], dec: int = 1) -> str:
    return "N/A" if v is None else f"{v:.{dec}f}x"


def _years_ebitda(nde: float) -> str:
    """Redacta la deuda neta/EBITDA como 'años de EBITDA'."""
    return "menos de un año" if nde < 1 else f"~{nde:.0f} año{'s' if nde >= _A['years_ebitda_plural_from'] else ''}"


# ── contexto ─────────────────────────────────────────────────────────────
class Ctx:
    """Vista unificada de los datos para los interpretadores."""

    def __init__(self, ratios, contextual, *, sector, real_sector,
                 roic_wacc_spread=None, altman=None, piotroski=None, dcf=None,
                 archetype=MATURE, archetype_values=None):
        self.r = ratios or {}
        self.c = contextual or {}
        self.sector = sector or "default"
        self.real_sector = real_sector or ""
        self.t: ThresholdConfig = SECTOR_THRESHOLDS.get(sector, SECTOR_THRESHOLDS["default"])
        # sector "market": el arquetipo contradice al sector de Yahoo y todo lo sectorial
        # (umbrales y medianas) es del mercado amplio (main._select_benchmark).
        self.market = self.sector == "market"
        self.del_ref = "del mercado" if self.market else "del sector"
        # Etapa 9a: ratios calculados con el beneficio normalizado (main, etapa 7): el
        # texto lo indica ("ROE normalizado 55.9%").
        self.norm = set((contextual or {}).get("normalized_metrics") or [])
        # Etapa 6: el arquetipo del clasificador único, no el nombre del sector.
        self.archetype = archetype or MATURE
        self.xv = archetype_values or {}
        self.is_financial = self.archetype == FINANCIAL
        self.spread = roic_wacc_spread
        self.altman = altman or {}
        self.piotroski = piotroski or {}
        self.dcf = dcf or {}

    def nl(self, key: str) -> str:
        """" normalizado" si el ratio sale del beneficio normalizado (etapa 9a)."""
        return " normalizado" if key in self.norm else ""

    def na(self, key) -> bool:
        """¿El componente no aplica al arquetipo? (entonces no se emite señal)."""
        return bool(not_applicable(self.archetype, key))

    def g(self, key, default=None):
        """Lee de ratios y cae a contextual."""
        v = self.r.get(key)
        if v is None:
            v = self.c.get(key)
        return default if v is None else v


def _sig(kind: str, category: str, headline: str, detail: str, weight: int) -> Dict[str, Any]:
    # Etapa 9b: sin doble guion ("— -33%" -> "−33%") en ningún titular.
    headline = re.sub(r" — -(?=[\d$])", " " + MINUS, headline)
    return {"kind": kind, "category": category, "reason": headline,
            "detail": detail, "weight": weight}


# ══════════════════════════════════════════════════════════════════════════
# INTERPRETADORES  (cada uno devuelve un Signal o None)
# Categorías alineadas con el desglose: Valoración, Rentabilidad, Solidez
# financiera, Flujo de caja, Crecimiento, Valor intrínseco, Riesgo de mercado.
# ══════════════════════════════════════════════════════════════════════════

# ── VALORACIÓN ────────────────────────────────────────────────────────────
def _pe(ctx: Ctx):
    pe = ctx.g("pe")
    T = _A["pe"]
    if pe is None or ctx.na("pe"):   # P/E no es métrica primaria (FINANCIAL, REIT, pre-beneficio, cíclica)
        return None
    if pe < 0:
        return _sig("risk", "Valoración", "P/E no significativo — pérdidas",
                    "La empresa no tiene beneficios positivos en los últimos doce meses, así que el "
                    "P/E no es interpretable; la valoración depende de que vuelva a generar utilidades.", T["w_loss"])
    sector_pe = ctx.c.get("sector_pe")
    _ref_txt = "del mercado (S&P 500)" if ctx.market else "del sector"
    peg = ctx.g("peg")
    # brecha vs sector (si hay dato) o umbral absoluto
    ref = sector_pe if (sector_pe and sector_pe > 0) else None
    dev = (pe - ref) / ref if ref else None
    if (dev is not None and dev > T["premium_dev"]) or pe > T["premium_abs"]:
        # ¿el crecimiento lo justifica? (PEG / spread)
        justified = (peg is not None and 0 < peg < T["justify_peg_max"]) or (ctx.spread is not None and ctx.spread > T["justify_spread_min"])
        base = (f"El mercado paga {pe:.1f}x beneficios{' normalizados' if ctx.nl('pe') else ''}"
                + (f", un {dev*100:+.0f}% sobre la mediana {_ref_txt} ({ref:.1f}x)" if ref else ", un múltiplo exigente"))
        if pe > T["strong_abs"] or (dev is not None and dev > T["strong_dev"]):
            if justified:
                return _sig("warning", "Valoración", f"Valoración exigente — P/E{ctx.nl('pe')} {pe:.1f}x",
                            base + ". Es un precio alto que el mercado sostiene por su crecimiento y retornos; "
                            "deja poco margen de error: cualquier decepción en resultados puede corregir con fuerza.", T["w_demanding"])
            return _sig("risk", "Valoración", f"Sobrevaloración — P/E{ctx.nl('pe')} {pe:.1f}x",
                        base + ". A este nivel el precio ya descuenta un escenario muy optimista; el riesgo de "
                        "corrección ante cualquier tropiezo en resultados es elevado.", T["w_overvalued"])
        # moderado: si el crecimiento lo justifica, no es alerta (evita chocar con
        # el DCF); si no, es una advertencia de prima.
        if justified:
            return None
        return _sig("warning", "Valoración", f"Prima sobre {'el mercado' if ctx.market else 'el sector'} — P/E{ctx.nl('pe')} {pe:.1f}x",
                    base + ". Conviene verificar que el crecimiento y los márgenes justifiquen pagar por encima de sus pares.", T["w_premium"])
    if ref and dev is not None and dev < T["discount_dev"]:
        return _sig("strength", "Valoración", f"Cotiza con descuento — P/E{ctx.nl('pe')} {pe:.1f}x",
                    f"Paga {pe:.1f}x beneficios{' normalizados' if ctx.nl('pe') else ''} frente a {ref:.1f}x {ctx.del_ref} ({dev*100:.0f}%): un descuento que puede ser "
                    "oportunidad si los fundamentos acompañan, o reflejar un riesgo que el mercado ya percibe.", T["w_discount"])
    return None


def _ev_ebitda(ctx: Ctx):
    ev = ctx.g("ev_ebitda")
    sec = ctx.c.get("sector_ev_ebitda")
    _mkt = ctx.market
    norm = ""
    if ctx.archetype == CYCLICAL:   # sobre EBITDA normalizado de ciclo medio
        ev, norm = ctx.xv.get("ev_ebitda_normalized"), " normalizado"
    # EV/EBITDA no es una métrica significativa para bancos/aseguradoras.
    if ev is None or ev <= 0 or ctx.na("ev_ebitda"):
        return None
    T = _A["ev_ebitda"]
    if ev > T["high_abs"]:
        return _sig("warning", "Valoración", f"EV/EBITDA{norm} alto — {ev:.1f}x",
                    f"El valor de empresa equivale a {ev:.1f} veces su EBITDA anual, un múltiplo caro en términos absolutos "
                    "que exige un crecimiento sostenido para no defraudar.", T["w_high"])
    if sec and sec > 0 and ev > T["premium_mult"] * sec:
        return _sig("warning", "Valoración", f"EV/EBITDA{norm} sobre el {'mercado' if _mkt else 'sector'} — {ev:.1f}x",
                    f"Se paga {ev:.1f}x EBITDA frente a {sec:.1f}x {'de la mediana del mercado' if _mkt else 'de sus pares'} ({(ev-sec)/sec*100:+.0f}%): el mercado le "
                    "asigna una prima que conviene contrastar con su ventaja competitiva.", T["w_premium"])
    if sec and sec > 0 and ev < T["discount_mult"] * sec:
        return _sig("strength", "Valoración", f"EV/EBITDA{norm} barato — {ev:.1f}x",
                    f"Cotiza a {ev:.1f}x EBITDA frente a {sec:.1f}x {'del mercado' if _mkt else 'del sector'}: valoración atractiva sobre flujo operativo, "
                    "a validar que no responda a un deterioro del negocio.", T["w_discount"])
    return None


def _fcf_yield(ctx: Ctx):
    fy = ctx.g("fcf_yield")
    if fy is None or ctx.na("p_fcf"):   # sin lectura de FCF en FINANCIAL ni REIT
        return None
    if fy < 0:
        return None  # se cubre en flujo de caja (quema de caja)
    t = ctx.t
    if fy < t.fcf_yield_low:
        return _sig("warning", "Valoración", f"FCF yield bajo — {_pct(fy)}",
                    f"Por cada dólar invertido en la acción, el negocio genera solo {_pct(fy)} de caja libre: se está "
                    "pagando caro cada dólar de flujo, habitual en compañías de alto crecimiento o valoración exigente.", _A["fcf_yield"]["w_low"])
    if fy >= t.fcf_yield_high:
        return _sig("strength", "Valoración", f"FCF yield atractivo — {_pct(fy)}",
                    f"El negocio genera {_pct(fy)} de caja libre sobre su capitalización: un rendimiento alto que da margen "
                    "para dividendos, recompras o reducir deuda sin depender del mercado.", _A["fcf_yield"]["w_high"])
    return None


def _peg(ctx: Ctx):
    peg = ctx.g("peg")
    # PEG > 5 casi siempre es un artefacto (crecimiento cercano a cero infla el
    # denominador); en financieras el PEG es poco fiable. Se descartan.
    T = _A["peg"]
    if peg is None or peg <= 0 or peg > T["artifact_above"] or ctx.na("peg"):
        return None
    if peg < T["attractive_below"]:
        return _sig("strength", "Valoración", f"PEG atractivo — {peg:.2f}",
                    f"Ajustado por su crecimiento esperado, el P/E resulta barato (PEG {peg:.2f} < 1): se paga menos de 1x "
                    "por cada punto de crecimiento, señal clásica de crecimiento a precio razonable (GARP).", T["w_attractive"])
    if peg > T["high_above"]:
        return _sig("warning", "Valoración", f"PEG elevado — {peg:.2f}",
                    f"El precio va muy por delante del crecimiento previsto (PEG {peg:.2f} > 2): incluso creciendo, "
                    "tardaría en 'justificar' su múltiplo actual.", T["w_high"])
    return None


def _dcf(ctx: Ctx):
    up = ctx.dcf.get("upside")
    fv = ctx.dcf.get("fair_value")
    if up is None or fv is None:
        return None
    T = _A["dcf"]
    rel = ctx.dcf.get("reliability") or {}
    if rel.get("level") == "baja" and (up >= T["upside_moderate"] or up <= -T["upside_moderate"]):
        # Etapa 8: un DCF de fiabilidad baja no es una señal de valor: se avisa de que
        # no concilia, sin presentarlo como infra- o sobrevaloración.
        return _sig("warning", "Valor intrínseco", f"DCF no concluyente {signed_pct(up)} (fiabilidad baja)",
                    f"El DCF estima ${fv:,.0f} ({signed_pct(up)} frente al precio), pero " + "; ".join(rel.get("reasons") or [])
                    + ". No se usa en el score.", T["w_premium"])
    if up >= T["upside_strong"]:
        return _sig("strength", "Valor intrínseco", f"Infravalorada según DCF {signed_pct(up)}",
                    f"El descuento de flujos estima un valor justo de ${fv:,.0f}, un {up:.0f}% por encima del precio: hay "
                    "margen de seguridad si se cumplen los supuestos de crecimiento y rentabilidad del modelo.", T["w_undervalued"])
    if up >= T["upside_moderate"]:
        return _sig("strength", "Valor intrínseco", f"Cotiza bajo su valor justo {signed_pct(up)}",
                    f"El DCF sitúa el valor intrínseco en ${fv:,.0f} (+{up:.0f}% sobre el precio): potencial teórico "
                    "moderado, condicionado a que el negocio ejecute según lo previsto.", T["w_below_fair"])
    if up <= -T["upside_strong"]:
        return _sig("risk", "Valor intrínseco", f"Sobrevalorada según DCF {signed_pct(up)}",
                    f"El precio excede en {abs(up):.0f}% el valor justo estimado por el DCF (${fv:,.0f}): sostenerlo exige "
                    "asumir escenarios de crecimiento muy optimistas.", T["w_overvalued"])
    if up <= -T["upside_moderate"]:
        return _sig("warning", "Valor intrínseco", f"Prima sobre el valor justo {signed_pct(up)}",
                    f"El precio está un {abs(up):.0f}% por encima del valor intrínseco estimado (${fv:,.0f}): el mercado ya "
                    "paga buena parte del crecimiento futuro.", T["w_premium"])
    return None


# ── RENTABILIDAD ──────────────────────────────────────────────────────────
def _roe(ctx: Ctx):
    roe = ctx.g("roe")
    roa = ctx.g("roa")
    if roe is None or ctx.na("roe"):   # etapa 9a: REIT (sobre FFO) y pre-beneficio no leen el ROE
        return None
    T = _A["roe"]
    if roe < 0 and roa is not None and roa > T["negative_equity_min_roa"]:
        return _sig("strength", "Rentabilidad", f"ROE{ctx.nl('roe')} negativo por recompras, no por pérdidas",
                    f"El ROE es negativo por un patrimonio contable erosionado por recompras agresivas, no por pérdidas: el "
                    f"ROA de {_pct(roa)} confirma que los activos siguen siendo rentables.", T["w_buyback_negative"])
    if roe < 0:
        return _sig("risk", "Rentabilidad", f"ROE{ctx.nl('roe')} negativo — {_pct(roe)}",
                    f"La empresa destruye valor para el accionista: no genera retorno sobre su patrimonio. Conviene "
                    "revisar si es puntual o refleja un deterioro sostenido del negocio.", T["w_negative"])
    t = ctx.t
    if roe >= T["exceptional"]:
        return _sig("strength", "Rentabilidad", f"ROE{ctx.nl('roe')} excepcional — {_pct(roe)}",
                    f"Genera {_pct(roe)}{ctx.nl('roe') and ' (normalizado)'} de retorno sobre el patrimonio, muy por encima del umbral de excelencia {ctx.del_ref} "
                    f"({_pct(t.roe_high, 0)}). Un nivel tan alto suele estar amplificado por una base de patrimonio reducida "
                    "por recompras acumuladas, más que por rentabilidad operativa pura.", T["w_exceptional"])
    if roe >= t.roe_high:
        return _sig("strength", "Rentabilidad", f"ROE{ctx.nl('roe')} elevado — {_pct(roe)}",
                    f"Genera {_pct(roe)}{ctx.nl('roe') and ' (normalizado)'} de retorno sobre el patrimonio, por encima del umbral de excelencia {ctx.del_ref} "
                    f"({_pct(t.roe_high, 0)}): uso muy eficiente del capital de los accionistas.", T["w_high"])
    if roe < t.roe_low:
        return _sig("warning", "Rentabilidad", f"ROE{ctx.nl('roe')} bajo — {_pct(roe)}",
                    f"El retorno sobre el patrimonio{ctx.nl('roe')} ({_pct(roe)}) queda por debajo del mínimo {ctx.del_ref} "
                    f"({_pct(t.roe_low, 0)}): el capital de los accionistas no se está remunerando con holgura.", T["w_low"])
    return None


def _spread(ctx: Ctx):
    sp = ctx.spread
    if sp is None or ctx.na("roic_wacc"):
        return None
    roic = ctx.g("roic")
    wacc = ctx.g("wacc")
    if wacc is None and roic is not None:
        wacc = roic - sp  # deriva el WACC del spread si no viene explícito
    tail = ""
    if roic is not None and wacc is not None:
        tail = f" (ROIC {_pct(roic)} vs WACC {_pct(wacc)})"
    T = _A["spread"]
    if sp >= T["strong"]:
        return _sig("strength", "Rentabilidad", f"Crea mucho valor — spread +{_pct(sp)}",
                    f"El retorno sobre el capital invertido supera con holgura su costo{tail}: cada dólar reinvertido crea "
                    "valor económico sustancial, el rasgo de un negocio con ventaja competitiva duradera.", T["w_strong"])
    if sp >= T["positive"]:
        return _sig("strength", "Rentabilidad", f"Crea valor — spread +{_pct(sp)}",
                    f"El ROIC supera al costo de capital{tail}: la reinversión genera valor, no solo crecimiento.", T["w_positive"])
    if sp < 0:
        return _sig("risk", "Rentabilidad", f"Destruye valor — spread {_pct(sp)}",
                    f"El retorno sobre el capital invertido no cubre su costo{tail}: crecer a estos retornos destruye valor "
                    "para el accionista en lugar de crearlo.", T["w_negative"])
    return None


def _margins(ctx: Ctx):
    """Margen neto/operativo/bruto — emite la señal más informativa disponible."""
    t = ctx.t
    nm = None if ctx.na("net_margin") else ctx.g("net_margin")       # etapa 9a: no aplica en REIT / pre-beneficio
    gm = None if ctx.na("gross_margin") else ctx.g("gross_margin")   # ni el bruto en REIT (arrendamiento neto)
    T = _A["margins"]
    out = []
    if nm is not None:
        if nm < 0:
            out.append(_sig("risk", "Rentabilidad", f"Margen neto{ctx.nl('net_margin')} negativo — {_pct(nm)}",
                            "La empresa pierde dinero a nivel neto: cada dólar vendido no cubre el total de costos, "
                            "gastos, intereses e impuestos. Insostenible si se prolonga.", T["w_net_negative"]))
        elif nm >= t.net_margin_low * T["net_solid_mult"]:
            out.append(_sig("strength", "Rentabilidad", f"Margen neto{ctx.nl('net_margin')} sólido — {_pct(nm)}",
                            f"De cada dólar vendido quedan {nm*100:.0f} centavos de beneficio tras todos los costos: señala "
                            "poder de fijación de precios y eficiencia por encima de la media "
                            + ("del mercado." if ctx.market else "de su sector."), T["w_net_solid"]))
        elif nm < t.net_margin_low:
            out.append(_sig("warning", "Rentabilidad", f"Margen neto{ctx.nl('net_margin')} estrecho — {_pct(nm)}",
                            f"Solo {nm*100:.1f} centavos de cada dólar vendido llegan a beneficio: márgenes finos que dejan "
                            "poco colchón ante subidas de costos o presión competitiva.", T["w_net_thin"]))
    if gm is not None and gm > T["gross_high"]:
        out.append(_sig("strength", "Rentabilidad", f"Margen bruto muy alto — {_pct(gm)}",
                        f"Retiene {gm*100:.0f}% de cada venta tras el costo directo del producto: un margen bruto así suele "
                        "reflejar marca fuerte, tecnología propia o poder de precios difícil de replicar.", T["w_gross_high"]))
    # devolver la de mayor peso (evita saturar con 3 de rentabilidad)
    return max(out, key=lambda s: s["weight"]) if out else None


# ── SOLIDEZ FINANCIERA ────────────────────────────────────────────────────
def _leverage(ctx: Ctx):
    nde = ctx.g("net_debt_to_ebitda")
    if nde is None or ctx.na("net_debt_ebitda"):
        return None
    T = _A["leverage"]
    state = net_debt_ebitda_state(ctx.g("ebitda"), ctx.g("net_debt"))
    if state == "no_significativo":
        # EBITDA <= 0: la ratio no se lee; la caja neta solo si caja > deuda total.
        nd = ctx.g("net_debt")
        if nd is not None and nd < 0:
            return _sig("strength", "Solidez financiera", "Caja neta — sin deuda financiera neta",
                        "La empresa tiene más efectivo que deuda: posición de caja neta que le da flexibilidad para "
                        "invertir, resistir ciclos o retribuir al accionista sin depender de la financiación externa.",
                        T["w_net_cash"])
        return None
    if nde < 0:
        return _sig("strength", "Solidez financiera", "Caja neta — sin deuda financiera neta",
                    "La empresa tiene más efectivo que deuda: posición de caja neta que le da flexibilidad para invertir, "
                    "resistir ciclos o retribuir al accionista sin depender de la financiación externa.", T["w_net_cash"])
    t = ctx.t
    if ctx.archetype == REIT:
        # Etapa 9a: bandas de REIT (las mismas que Solidez): un REIT con grado de inversión
        # opera en 5–6.5x; advertencia por encima de 7.5x y riesgo por encima de 9x.
        b = _SC_SOLIDEZ["reit_nde_bounds"]
        if nde > b[2]:
            sev = "risk" if nde > b[3] else "warning"
            return _sig(sev, "Solidez financiera", f"Apalancamiento elevado para un REIT — {nde:.1f}x EBITDA",
                        f"Harían falta {_years_ebitda(nde)} de EBITDA íntegro para saldar la deuda neta, por encima del "
                        f"rango habitual de un REIT con grado de inversión (hasta {b[1]:.1f}x): conviene vigilar la "
                        "cobertura de intereses y el calendario de vencimientos.",
                        T["w_high_risk"] if sev == "risk" else T["w_high_warning"])
        if nde <= b[0]:
            return _sig("strength", "Solidez financiera", f"Apalancamiento conservador para un REIT — {nde:.1f}x EBITDA",
                        f"La deuda neta equivale a {_years_ebitda(nde)} de EBITDA, por debajo del rango habitual de un "
                        "REIT: holgura para financiar adquisiciones sin tensionar el balance.", T["w_low"])
        return None
    if nde > t.net_debt_ebitda_high:
        sev = "risk" if nde > t.net_debt_ebitda_high * T["risk_mult"] else "warning"
        w = T["w_high_risk"] if sev == "risk" else T["w_high_warning"]
        return _sig(sev, "Solidez financiera", f"Apalancamiento elevado — {nde:.1f}x EBITDA",
                    f"Harían falta {_years_ebitda(nde)} de EBITDA íntegro para saldar la deuda neta. Por encima de "
                    f"{t.net_debt_ebitda_high:.0f}x el margen ante una caída de resultados o una subida de tipos se estrecha: "
                    "conviene vigilar la cobertura de intereses y el calendario de vencimientos.", w)
    if nde < t.net_debt_ebitda_low:
        return _sig("strength", "Solidez financiera", f"Deuda baja — {nde:.1f}x EBITDA",
                    f"La deuda neta equivale a {_years_ebitda(nde)} de EBITDA, un nivel cómodo que deja holgura financiera y "
                    "capacidad de maniobra ante imprevistos.", T["w_low"])
    return None


def _coverage(ctx: Ctx):
    ic = ctx.g("interest_coverage")
    if ic is None or ctx.na("interest_coverage"):
        return None
    T = _A["coverage"]
    state = interest_coverage_state(ic, ctx.g("net_debt"))
    if state == "no_significativo":
        return None  # EBIT < 0 con caja neta: los intereses se pagan con caja
    if state == "negativa":
        return _sig("risk", "Solidez financiera", "Cobertura de intereses negativa (EBIT < 0)",
                    "El resultado operativo es negativo y la empresa tiene deuda neta: los intereses no se pagan con el "
                    "negocio, sino con caja o nueva financiación.", T["w_critical"])
    if ic < T["critical_below"]:
        return _sig("risk", "Solidez financiera", f"Cobertura de intereses crítica — {ic:.1f}x",
                    f"El beneficio operativo apenas cubre {ic:.1f} veces el gasto por intereses: un margen peligrosamente "
                    "fino que deja a la empresa muy expuesta ante cualquier caída del resultado operativo.", T["w_critical"])
    t = ctx.t
    if ic < t.interest_coverage_low:
        return _sig("warning", "Solidez financiera", f"Cobertura de intereses justa — {ic:.1f}x",
                    f"El resultado operativo cubre {ic:.1f}x el gasto por intereses, por debajo del mínimo cómodo "
                    f"({t.interest_coverage_low:.0f}x): deja poco margen si los beneficios se resienten.", T["w_tight"])
    if ic > T["comfortable_above"]:
        return _sig("strength", "Solidez financiera", f"Deuda fácilmente servible — cobertura {ic:.0f}x",
                    f"El beneficio operativo cubre {ic:.0f} veces el gasto por intereses: la carga financiera es holgada y "
                    "no compromete la operación.", T["w_comfortable"])
    return None


def _liquidity(ctx: Ctx):
    cr = ctx.g("current_ratio")
    if cr is None or ctx.na("current_ratio"):
        return None
    t = ctx.t
    if cr < t.current_ratio_low:
        return _sig("warning", "Solidez financiera", f"Liquidez ajustada — current ratio {cr:.2f}x",
                    f"Los activos corrientes cubren solo {cr:.2f}x los pasivos de corto plazo: la empresa podría tensionarse "
                    "para atender sus obligaciones inmediatas si el flujo de caja se resiente. Habitual y manejable en "
                    "negocios con caja muy predecible.", _A["liquidity"]["w_tight"])
    if cr > _A["liquidity"]["ample_above"]:
        return _sig("strength", "Solidez financiera", f"Liquidez muy holgada — current ratio {cr:.2f}x",
                    f"Los activos corrientes multiplican por {cr:.1f} los pasivos de corto plazo: cero tensión de caja, "
                    "aunque un exceso tan amplio podría señalar capital ocioso que no se está reinvirtiendo.", _A["liquidity"]["w_ample"])
    return None


def _altman(ctx: Ctx):
    z = ctx.altman.get("z_score")
    zone = ctx.altman.get("zone")
    if z is None or ctx.na("altman") or ctx.altman.get("available") is False:
        return None
    # Umbrales del modelo realmente usado (Z, Z' o Z''), no los del Z original.
    det = ctx.altman.get("details") or {}
    safe_t, grey_t = det.get("safe_threshold"), det.get("grey_threshold")
    if zone == "distress":
        return _sig("risk", "Solidez financiera", f"Riesgo de insolvencia — Altman Z {z:.2f}",
                    f"El modelo de Altman sitúa a la empresa en zona de riesgo (Z {z:.2f} < {grey_t:.2f}), donde históricamente se "
                    "concentran las compañías con problemas de solvencia a 2 años. Señal de alerta que exige revisar deuda y "
                    "generación de caja.", _A["altman"]["w_distress"])
    if zone == "safe":
        return _sig("strength", "Solidez financiera", f"Solvencia sólida — Altman Z {z:.2f}",
                    f"El Altman Z de {z:.2f} (> {safe_t:.2f}) ubica a la empresa en zona segura: baja probabilidad estadística de "
                    "problemas de solvencia según el modelo.", _A["altman"]["w_safe"])
    return None


def _runway(ctx: Ctx):
    """GROWTH_PRE_PROFIT: el runway sustituye al Altman (que no aplica)."""
    rw = ctx.xv.get("runway") if ctx.archetype == GROWTH_PRE_PROFIT else None
    if not rw or rw.get("state") not in ("autofinanciada", "runway"):
        return None
    W, b = _A["runway"], cfg("thresholds.score.solidez.runway_bounds")
    if rw["state"] == "autofinanciada" and rw.get("sbc_exceeds_fcf"):
        # Etapa 9a: autofinanciada en caja, pero la SBC (mayor que el FCF) se paga con dilución.
        return _sig("strength", "Solidez financiera", "Autofinanciada en caja — FCF TTM positivo",
                    "El flujo de caja libre de los últimos doce meses es positivo: la empresa no consume caja para "
                    "operar. Pero la compensación en acciones "
                    + (f"({rw['sbc_to_revenue']:.1%} de los ingresos) " if rw.get("sbc_to_revenue") is not None else "")
                    + "supera ese FCF y se paga con dilución del accionista: el FCF no cubre su coste económico "
                      "completo.", W["w_self_funded"])
    if rw["state"] == "autofinanciada":
        return _sig("strength", "Solidez financiera", "Autofinanciada — FCF TTM positivo",
                    "El flujo de caja libre de los últimos doce meses es positivo: la empresa financia su crecimiento "
                    "sin consumir caja ni depender de nuevas rondas de capital o deuda.", W["w_self_funded"])
    y = rw["years"]
    if y >= b[0]:
        return _sig("strength", "Solidez financiera", f"Runway holgado — {y:.1f} años",
                    f"La caja y las inversiones a corto plazo cubren {y:.1f} años de quema de FCF.", W["w_self_funded"])
    if y >= b[2] and y < b[1]:
        return _sig("warning", "Solidez financiera", f"Runway ajustado — {y:.1f} años",
                    f"La caja y las inversiones a corto plazo cubren {y:.1f} años de quema de FCF: tendrá que "
                    "financiarse (deuda o ampliación de capital) dentro del horizonte del plan.", W["w_tight"])
    if y < b[2]:
        return _sig("risk", "Solidez financiera", f"Runway crítico — {y:.1f} años",
                    f"La caja y las inversiones a corto plazo cubren menos de un año de quema de FCF ({y:.1f}): "
                    "necesita financiación urgente, probablemente dilutiva.", W["w_short"])
    return None


# ── FLUJO DE CAJA ─────────────────────────────────────────────────────────
def _fcf(ctx: Ctx):
    if ctx.na("fcf"):   # FINANCIAL: el flujo de caja de un banco no mide calidad ni solvencia
        return None
    fcf = ctx.g("fcf") if ctx.g("fcf") is not None else ctx.g("free_cash_flow")
    neg_years = ctx.c.get("fcf_trend_negative_years")
    T = _A["fcf"]
    if neg_years is not None and neg_years >= T["recurrent_negative_years"]:
        note = "" if ctx.archetype == GROWTH_PRE_PROFIT else " Si no es una fase de inversión deliberada, compromete la autofinanciación."
        return _sig("risk", "Flujo de caja", f"Quema de caja recurrente — {neg_years} años",
                    f"La empresa lleva {neg_years} años consecutivos con flujo de caja libre negativo: consume más efectivo "
                    f"del que genera.{note}", T["w_recurrent"])
    if fcf is not None and fcf < 0:
        if ctx.archetype == GROWTH_PRE_PROFIT:   # etapa 9b: el arquetipo, no la etiqueta "growth"
            return _sig("warning", "Flujo de caja", "Flujo de caja libre negativo",
                        "La empresa quema caja, algo esperable en una fase de fuerte inversión para crecer; la clave es que "
                        "esa inversión se traduzca en ingresos y márgenes futuros.", T["w_negative_growth"])
        return _sig("risk", "Flujo de caja", "Flujo de caja libre negativo",
                    "El negocio consume más efectivo del que genera tras invertir: depende de caja acumulada, deuda o "
                    "ampliaciones para sostenerse. Sostenible solo de forma transitoria.", T["w_negative"])
    return None


def _earnings_quality(ctx: Ctx):
    q = ctx.g("fcf_to_net_income")
    if q is None or ctx.na("fcf_to_ni"):
        return None
    ni = ctx.g("net_income")
    if ni is not None and ni <= 0:   # regla M (etapa 9a): sin beneficio el ratio no es significativo
        return None
    T = _A["earnings_quality"]
    if q < T["low_below"]:
        return _sig("warning", "Flujo de caja", "Calidad del beneficio baja",
                    f"El flujo de caja libre equivale a menos de la mitad del beneficio contable (FCF/BN{ctx.nl('fcf_to_net_income')} {q:.0%}): parte de "
                    "las utilidades no se está convirtiendo en caja real, señal a vigilar (devengos, capex o capital de "
                    "trabajo).", T["w_low"])
    if q > T["high_above"]:
        return _sig("strength", "Flujo de caja", "Beneficio de alta calidad",
                    f"El flujo de caja libre supera al beneficio contable (FCF/BN{ctx.nl('fcf_to_net_income')} {q:.0%}): las utilidades se convierten "
                    "íntegramente en efectivo, señal de contabilidad conservadora y negocio que 'respira' caja.", T["w_high"])
    return None


# ── CRECIMIENTO ───────────────────────────────────────────────────────────
def _growth(ctx: Ctx):
    g3 = ctx.c.get("revenue_cagr_3y")
    if g3 is None:
        return None
    if ctx.archetype == CYCLICAL and ctx.xv.get("revenue_growth_normalized") is not None:
        return None   # cíclica: el crecimiento es de ciclo medio, no una señal interanual
    if ctx.archetype == REIT:   # el dato es el CAGR 3 años del FFO por acción, no ingresos interanuales
        if growth_for_bands(g3) < 0:
            return _sig("warning", "Crecimiento", f"FFO por acción en descenso — {_pct(g3)} anual (3 años)",
                        f"El FFO por acción cae un {_pct(abs(g3))} anual en tres años: la emisión de acciones crece más "
                        "deprisa que los fondos de operación, y diluye al accionista.", _A["growth"]["w_contraction"])
        if g3 > _A["growth"]["strong_above"]:
            return _sig("strength", "Crecimiento", f"FFO por acción en fuerte alza — +{_pct(g3)} anual (3 años)",
                        f"El FFO por acción crece {_pct(g3)} anual en tres años, por encima de la emisión de acciones.",
                        _A["growth"]["w_strong"])
        return None
    if growth_for_bands(g3) < 0:   # entre −2% y 0: plano, no contracción
        return _sig("warning", "Crecimiento", f"Ingresos en contracción — {_pct(g3)} anual (3 años)",
                    f"Las ventas caen un {_pct(abs(g3))} anual en tres años (CAGR): un negocio que se encoge "
                    "presiona márgenes y valoración salvo que sea un bache puntual con catalizador de recuperación.", _A["growth"]["w_contraction"])
    if g3 > _A["growth"]["strong_above"]:
        return _sig("strength", "Crecimiento", f"Crecimiento fuerte — ingresos +{_pct(g3)} anual (3 años)",
                    f"Los ingresos crecen {_pct(g3)} anual en tres años (CAGR): ritmo de expansión elevado que, si mantiene "
                    "márgenes, es el principal motor de creación de valor a largo plazo.", _A["growth"]["w_strong"])
    return None


def _eps_growth(ctx: Ctx):
    e3 = ctx.c.get("eps_cagr_3y")
    if e3 is None or ctx.na("eps_growth"):
        return None
    T = _A["eps_growth"]
    if e3 < T["decline_below"]:
        return _sig("warning", "Crecimiento", f"Beneficio por acción en descenso — {_pct(e3)} anual (3 años)",
                    f"El BPA cae {_pct(abs(e3))} anual en tres años (CAGR): la rentabilidad por acción se erosiona, ya sea por menores "
                    "beneficios o por dilución. Contrasta con la evolución de ingresos para ubicar la causa.", T["w_decline"])
    if e3 > T["strong_above"]:
        return _sig("strength", "Crecimiento", f"BPA en fuerte expansión — +{_pct(e3)} anual (3 años)",
                    f"El beneficio por acción crece {_pct(e3)} anual en tres años (CAGR): la rentabilidad para el accionista se "
                    "acelera, a menudo apoyada en apalancamiento operativo o recompras.", T["w_strong"])
    return None


def _piotroski(ctx: Ctx):
    # Escala única sobre el valor ESCALADO a base 9; sin señal si no concluyente
    # o si no aplica al arquetipo (FINANCIAL, REIT).
    if ctx.piotroski.get("conclusive") is False or ctx.na("piotroski"):
        return None
    f_raw = ctx.piotroski.get("score")
    f = ctx.piotroski.get("scaled_score", f_raw)
    if f is None:
        return None
    n = ctx.piotroski.get("evaluated", 9)
    f_txt = f"{f_raw}/9" if n == 9 else f"{f_raw}/{n} evaluados"
    de_txt = "de las 9 señales" if n == 9 else f"de las {n} señales evaluadas"
    fy = ctx.piotroski.get("fiscal_year")
    yr = f" ({fy})" if fy else ""
    T = _A["piotroski"]
    if f >= T["strong_min"]:
        return _sig("strength", "Crecimiento", f"Fortaleza financiera excepcional — Piotroski {f_txt}",
                    f"Cumple {f_raw} {de_txt} de Piotroski{yr} sobre mejora en rentabilidad, estructura de capital y "
                    "eficiencia: un perfil de salud financiera en clara mejora año contra año.", T["w_strong"])
    if f <= T["weak_max"]:
        return _sig("risk", "Crecimiento", f"Debilidad financiera — Piotroski {f_txt}",
                    f"Solo cumple {f_raw} {de_txt} de Piotroski{yr}: múltiples indicadores contables de rentabilidad, "
                    "deuda o eficiencia se están deteriorando en el último ejercicio.", T["w_weak"])
    return None


def _deterioration(ctx: Ctx):
    reasons = []
    r5 = ctx.c.get("revenue_cagr_5y")
    om3 = ctx.c.get("operating_margin_change_3y")
    ny = ctx.c.get("fcf_trend_negative_years")
    if r5 is not None and r5 < 0:
        reasons.append(f"ingresos decrecientes a 5 años ({_pct(r5)})")
    T = _A["deterioration"]
    if om3 is not None and om3 < T["margin_drop_below"]:
        reasons.append(f"márgenes operativos en caída ({_pct(om3)} en 3 años)")
    if ny is not None and ny >= T["negative_fcf_years"]:
        reasons.append(f"FCF negativo {ny} años")
    if len(reasons) >= T["min_signals"]:
        return _sig("risk", "Deterioro estructural", "Deterioro estructural del negocio",
                    "Coinciden varias señales de fondo: " + "; ".join(reasons) + ". Cuando se dan juntas, suelen apuntar a "
                    "un debilitamiento sostenido del negocio, no a un mal trimestre puntual.", T["w"])
    return None


# ── RIESGO DE MERCADO ─────────────────────────────────────────────────────
def _beta(ctx: Ctx):
    b = ctx.g("beta")
    if b is None:
        return None
    t = ctx.t
    if b > t.beta_high:
        return _sig("warning", "Riesgo de mercado", f"Volatilidad elevada — Beta {b:.2f}",
                    f"La acción amplifica ~{(b-1)*100:.0f}% los movimientos del mercado: cae más en las correcciones y sube "
                    "más en los rallies. Razonable con horizonte largo y tolerancia al riesgo; resta si buscas estabilidad.", _A["beta"]["w_high"])
    if b < t.beta_low:
        return _sig("strength", "Riesgo de mercado", f"Perfil defensivo — Beta {b:.2f}",
                    f"Con beta {b:.2f}, la acción se mueve menos que el mercado y tiende a amortiguar las caídas: un perfil "
                    "más estable, útil para reducir la volatilidad de una cartera.", _A["beta"]["w_low"])
    return None


def _drawdown(ctx: Ctx):
    dd = ctx.c.get("max_drawdown_1y")
    if dd is None or dd >= _A["drawdown"]["deep_below"]:
        return None
    return _sig("warning", "Riesgo de mercado", f"Caída pronunciada en el año — {_pct(dd)}",
                f"La acción ha llegado a caer {_pct(abs(dd))} desde máximos en el último año: una corrección profunda que "
                "puede ser oportunidad si el negocio sigue intacto, o el mercado anticipando un deterioro.", _A["drawdown"]["w"])


INTERPRETERS = [
    _pe, _ev_ebitda, _fcf_yield, _peg, _dcf,
    _roe, _spread, _margins,
    _leverage, _coverage, _liquidity, _altman, _runway,
    _fcf, _earnings_quality,
    _growth, _eps_growth, _piotroski, _deterioration,
    _beta, _drawdown,
]


# ══════════════════════════════════════════════════════════════════════════
# ORQUESTADOR
# ══════════════════════════════════════════════════════════════════════════
def build_signals(ratios: Dict[str, Any], contextual: Dict[str, Any], *,
                  sector: str = "default", real_sector: str = "",
                  roic_wacc_spread: Optional[float] = None,
                  altman: Optional[dict] = None, piotroski: Optional[dict] = None,
                  dcf: Optional[dict] = None,
                  archetype: str = MATURE, archetype_values: Optional[dict] = None) -> Dict[str, List[dict]]:
    """Ejecuta todos los interpretadores y agrupa por tipo, ordenando por peso.

    Devuelve {"red_flags", "warnings", "strengths"} con ítems
    {"category", "reason", "detail"} listos para el frontend y el PDF.
    """
    ctx = Ctx(ratios, contextual, sector=sector, real_sector=real_sector,
              roic_wacc_spread=roic_wacc_spread, altman=altman,
              piotroski=piotroski, dcf=dcf,
              archetype=archetype, archetype_values=archetype_values)

    buckets = {"risk": [], "warning": [], "strength": []}
    for interp in INTERPRETERS:
        try:
            s = interp(ctx)
        except Exception:
            s = None
        if s and s["kind"] in buckets:
            buckets[s["kind"]].append(s)

    def _clean(items, cap=_A["max_per_group"]):
        # ordena por materialidad (peso) y limita para mantener la lista de alto
        # valor, sin saturar con señales menores.
        items.sort(key=lambda s: s["weight"], reverse=True)
        return [{"category": s["category"], "reason": s["reason"], "detail": s["detail"]} for s in items[:cap]]

    return {
        "red_flags": _clean(buckets["risk"]),
        "warnings": _clean(buckets["warning"]),
        "strengths": _clean(buckets["strength"]),
    }
