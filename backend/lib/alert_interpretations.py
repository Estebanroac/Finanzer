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
    from .financial_ratios import SECTOR_THRESHOLDS, ThresholdConfig, is_financial_sector
except ImportError:  # ejecución como script suelto
    from financial_ratios import SECTOR_THRESHOLDS, ThresholdConfig, is_financial_sector


# ── formato ──────────────────────────────────────────────────────────────
def _pct(v: Optional[float], dec: int = 1) -> str:
    return "N/A" if v is None else f"{v * 100:.{dec}f}%"


def _x(v: Optional[float], dec: int = 1) -> str:
    return "N/A" if v is None else f"{v:.{dec}f}x"


def _years_ebitda(nde: float) -> str:
    """Redacta la deuda neta/EBITDA como 'años de EBITDA'."""
    return "menos de un año" if nde < 1 else f"~{nde:.0f} año{'s' if nde >= 1.5 else ''}"


# ── contexto ─────────────────────────────────────────────────────────────
class Ctx:
    """Vista unificada de los datos para los interpretadores."""

    def __init__(self, ratios, contextual, *, sector, real_sector,
                 roic_wacc_spread=None, altman=None, piotroski=None, dcf=None,
                 is_growth=False):
        self.r = ratios or {}
        self.c = contextual or {}
        self.sector = sector or "default"
        self.real_sector = real_sector or ""
        self.t: ThresholdConfig = SECTOR_THRESHOLDS.get(sector, SECTOR_THRESHOLDS["default"])
        self.is_financial = is_financial_sector(real_sector) or is_financial_sector(sector)
        self.is_growth = bool(is_growth)
        self.spread = roic_wacc_spread
        self.altman = altman or {}
        self.piotroski = piotroski or {}
        self.dcf = dcf or {}

    def g(self, key, default=None):
        """Lee de ratios y cae a contextual."""
        v = self.r.get(key)
        if v is None:
            v = self.c.get(key)
        return default if v is None else v


def _sig(kind: str, category: str, headline: str, detail: str, weight: int) -> Dict[str, Any]:
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
    if pe is None:
        return None
    if pe < 0:
        return _sig("risk", "Valoración", "P/E no significativo — pérdidas",
                    "La empresa no tiene beneficios positivos en los últimos doce meses, así que el "
                    "P/E no es interpretable; la valoración depende de que vuelva a generar utilidades.", 60)
    sector_pe = ctx.c.get("sector_pe")
    peg = ctx.g("peg")
    # brecha vs sector (si hay dato) o umbral absoluto
    ref = sector_pe if (sector_pe and sector_pe > 0) else None
    dev = (pe - ref) / ref if ref else None
    if (dev is not None and dev > 0.30) or pe > 35:
        # ¿el crecimiento lo justifica? (PEG / spread)
        justified = (peg is not None and 0 < peg < 1.5) or (ctx.spread is not None and ctx.spread > 0.05)
        base = (f"El mercado paga {pe:.1f}x beneficios"
                + (f", un {dev*100:+.0f}% sobre la mediana del sector ({ref:.1f}x)" if ref else ", un múltiplo exigente"))
        if pe > 50 or (dev is not None and dev > 0.6):
            if justified:
                return _sig("warning", "Valoración", f"Valoración exigente — P/E {pe:.1f}x",
                            base + ". Es un precio alto que el mercado sostiene por su crecimiento y retornos; "
                            "deja poco margen de error: cualquier decepción en resultados puede corregir con fuerza.", 62)
            return _sig("risk", "Valoración", f"Sobrevaloración — P/E {pe:.1f}x",
                        base + ". A este nivel el precio ya descuenta un escenario muy optimista; el riesgo de "
                        "corrección ante cualquier tropiezo en resultados es elevado.", 68)
        # moderado: si el crecimiento lo justifica, no es alerta (evita chocar con
        # el DCF); si no, es una advertencia de prima.
        if justified:
            return None
        return _sig("warning", "Valoración", f"Prima sobre el sector — P/E {pe:.1f}x",
                    base + ". Conviene verificar que el crecimiento y los márgenes justifiquen pagar por encima de sus pares.", 48)
    if ref and dev is not None and dev < -0.20:
        return _sig("strength", "Valoración", f"Cotiza con descuento — P/E {pe:.1f}x",
                    f"Paga {pe:.1f}x beneficios frente a {ref:.1f}x del sector ({dev*100:.0f}%): un descuento que puede ser "
                    "oportunidad si los fundamentos acompañan, o reflejar un riesgo que el mercado ya percibe.", 40)
    return None


def _ev_ebitda(ctx: Ctx):
    ev = ctx.g("ev_ebitda")
    sec = ctx.c.get("sector_ev_ebitda")
    # EV/EBITDA no es una métrica significativa para bancos/aseguradoras.
    if ev is None or ev <= 0 or ctx.is_financial:
        return None
    if ev > 25:
        return _sig("warning", "Valoración", f"EV/EBITDA alto — {ev:.1f}x",
                    f"El valor de empresa equivale a {ev:.1f} veces su EBITDA anual, un múltiplo caro en términos absolutos "
                    "que exige un crecimiento sostenido para no defraudar.", 44)
    if sec and sec > 0 and ev > 1.3 * sec:
        return _sig("warning", "Valoración", f"EV/EBITDA sobre el sector — {ev:.1f}x",
                    f"Se paga {ev:.1f}x EBITDA frente a {sec:.1f}x de sus pares ({(ev-sec)/sec*100:+.0f}%): el mercado le "
                    "asigna una prima que conviene contrastar con su ventaja competitiva.", 38)
    if sec and sec > 0 and ev < 0.7 * sec:
        return _sig("strength", "Valoración", f"EV/EBITDA barato — {ev:.1f}x",
                    f"Cotiza a {ev:.1f}x EBITDA frente a {sec:.1f}x del sector: valoración atractiva sobre flujo operativo, "
                    "a validar que no responda a un deterioro del negocio.", 34)
    return None


def _fcf_yield(ctx: Ctx):
    fy = ctx.g("fcf_yield")
    if fy is None:
        return None
    if fy < 0:
        return None  # se cubre en flujo de caja (quema de caja)
    t = ctx.t
    if fy < t.fcf_yield_low:
        return _sig("warning", "Valoración", f"FCF yield bajo — {_pct(fy)}",
                    f"Por cada dólar invertido en la acción, el negocio genera solo {_pct(fy)} de caja libre: se está "
                    "pagando caro cada dólar de flujo, habitual en compañías de alto crecimiento o valoración exigente.", 42)
    if fy >= t.fcf_yield_high:
        return _sig("strength", "Valoración", f"FCF yield atractivo — {_pct(fy)}",
                    f"El negocio genera {_pct(fy)} de caja libre sobre su capitalización: un rendimiento alto que da margen "
                    "para dividendos, recompras o reducir deuda sin depender del mercado.", 46)
    return None


def _peg(ctx: Ctx):
    peg = ctx.g("peg")
    # PEG > 5 casi siempre es un artefacto (crecimiento cercano a cero infla el
    # denominador); en financieras el PEG es poco fiable. Se descartan.
    if peg is None or peg <= 0 or peg > 5 or ctx.is_financial:
        return None
    if peg < 1.0:
        return _sig("strength", "Valoración", f"PEG atractivo — {peg:.2f}",
                    f"Ajustado por su crecimiento esperado, el P/E resulta barato (PEG {peg:.2f} < 1): se paga menos de 1x "
                    "por cada punto de crecimiento, señal clásica de crecimiento a precio razonable (GARP).", 36)
    if peg > 2.0:
        return _sig("warning", "Valoración", f"PEG elevado — {peg:.2f}",
                    f"El precio va muy por delante del crecimiento previsto (PEG {peg:.2f} > 2): incluso creciendo, "
                    "tardaría en 'justificar' su múltiplo actual.", 34)
    return None


def _dcf(ctx: Ctx):
    up = ctx.dcf.get("upside")
    fv = ctx.dcf.get("fair_value")
    if up is None or fv is None:
        return None
    if up >= 30:
        return _sig("strength", "Valor intrínseco", f"Infravalorada según DCF — +{up:.0f}%",
                    f"El descuento de flujos estima un valor justo de ${fv:,.0f}, un {up:.0f}% por encima del precio: hay "
                    "margen de seguridad si se cumplen los supuestos de crecimiento y rentabilidad del modelo.", 52)
    if up >= 15:
        return _sig("strength", "Valor intrínseco", f"Cotiza bajo su valor justo — +{up:.0f}%",
                    f"El DCF sitúa el valor intrínseco en ${fv:,.0f} (+{up:.0f}% sobre el precio): potencial teórico "
                    "moderado, condicionado a que el negocio ejecute según lo previsto.", 40)
    if up <= -30:
        return _sig("risk", "Valor intrínseco", f"Sobrevalorada según DCF — {up:.0f}%",
                    f"El precio excede en {abs(up):.0f}% el valor justo estimado por el DCF (${fv:,.0f}): sostenerlo exige "
                    "asumir escenarios de crecimiento muy optimistas.", 58)
    if up <= -15:
        return _sig("warning", "Valor intrínseco", f"Prima sobre el valor justo — {up:.0f}%",
                    f"El precio está un {abs(up):.0f}% por encima del valor intrínseco estimado (${fv:,.0f}): el mercado ya "
                    "paga buena parte del crecimiento futuro.", 40)
    return None


# ── RENTABILIDAD ──────────────────────────────────────────────────────────
def _roe(ctx: Ctx):
    roe = ctx.g("roe")
    roa = ctx.g("roa")
    if roe is None:
        return None
    if roe < 0 and roa is not None and roa > 0.03:
        return _sig("strength", "Rentabilidad", "ROE negativo por recompras, no por pérdidas",
                    f"El ROE es negativo por un patrimonio contable erosionado por recompras agresivas, no por pérdidas: el "
                    f"ROA de {_pct(roa)} confirma que los activos siguen siendo rentables.", 30)
    if roe < 0:
        return _sig("risk", "Rentabilidad", f"ROE negativo — {_pct(roe)}",
                    f"La empresa destruye valor para el accionista: no genera retorno sobre su patrimonio. Conviene "
                    "revisar si es puntual o refleja un deterioro sostenido del negocio.", 55)
    t = ctx.t
    if roe >= 0.40:
        return _sig("strength", "Rentabilidad", f"ROE excepcional — {_pct(roe)}",
                    f"Genera {_pct(roe)} de retorno sobre el patrimonio, muy por encima del umbral de excelencia del sector "
                    f"({_pct(t.roe_high, 0)}). Un nivel tan alto suele estar amplificado por una base de patrimonio reducida "
                    "por recompras acumuladas, más que por rentabilidad operativa pura.", 44)
    if roe >= t.roe_high:
        return _sig("strength", "Rentabilidad", f"ROE elevado — {_pct(roe)}",
                    f"Genera {_pct(roe)} de retorno sobre el patrimonio, por encima del umbral de excelencia del sector "
                    f"({_pct(t.roe_high, 0)}): uso muy eficiente del capital de los accionistas.", 44)
    if roe < t.roe_low:
        return _sig("warning", "Rentabilidad", f"ROE bajo — {_pct(roe)}",
                    f"El retorno sobre el patrimonio ({_pct(roe)}) queda por debajo del mínimo del sector "
                    f"({_pct(t.roe_low, 0)}): el capital de los accionistas no se está remunerando con holgura.", 40)
    return None


def _spread(ctx: Ctx):
    sp = ctx.spread
    if sp is None or ctx.is_financial:
        return None
    roic = ctx.g("roic")
    wacc = ctx.g("wacc")
    if wacc is None and roic is not None:
        wacc = roic - sp  # deriva el WACC del spread si no viene explícito
    tail = ""
    if roic is not None and wacc is not None:
        tail = f" (ROIC {_pct(roic)} vs WACC {_pct(wacc)})"
    if sp >= 0.10:
        return _sig("strength", "Rentabilidad", f"Crea mucho valor — spread +{_pct(sp)}",
                    f"El retorno sobre el capital invertido supera con holgura su costo{tail}: cada dólar reinvertido crea "
                    "valor económico sustancial, el rasgo de un negocio con ventaja competitiva duradera.", 50)
    if sp >= 0.03:
        return _sig("strength", "Rentabilidad", f"Crea valor — spread +{_pct(sp)}",
                    f"El ROIC supera al costo de capital{tail}: la reinversión genera valor, no solo crecimiento.", 42)
    if sp < 0:
        return _sig("risk", "Rentabilidad", f"Destruye valor — spread {_pct(sp)}",
                    f"El retorno sobre el capital invertido no cubre su costo{tail}: crecer a estos retornos destruye valor "
                    "para el accionista en lugar de crearlo.", 56)
    return None


def _margins(ctx: Ctx):
    """Margen neto/operativo/bruto — emite la señal más informativa disponible."""
    t = ctx.t
    nm = ctx.g("net_margin")
    gm = ctx.g("gross_margin")
    out = []
    if nm is not None:
        if nm < 0:
            out.append(_sig("risk", "Rentabilidad", f"Margen neto negativo — {_pct(nm)}",
                            "La empresa pierde dinero a nivel neto: cada dólar vendido no cubre el total de costos, "
                            "gastos, intereses e impuestos. Insostenible si se prolonga.", 54))
        elif nm >= t.net_margin_low * 1.5:
            out.append(_sig("strength", "Rentabilidad", f"Margen neto sólido — {_pct(nm)}",
                            f"De cada dólar vendido quedan {nm*100:.0f} centavos de beneficio tras todos los costos: señala "
                            "poder de fijación de precios y eficiencia por encima de la media de su sector.", 38))
        elif nm < t.net_margin_low:
            out.append(_sig("warning", "Rentabilidad", f"Margen neto estrecho — {_pct(nm)}",
                            f"Solo {nm*100:.1f} centavos de cada dólar vendido llegan a beneficio: márgenes finos que dejan "
                            "poco colchón ante subidas de costos o presión competitiva.", 36))
    if gm is not None and gm > 0.60:
        out.append(_sig("strength", "Rentabilidad", f"Margen bruto muy alto — {_pct(gm)}",
                        f"Retiene {gm*100:.0f}% de cada venta tras el costo directo del producto: un margen bruto así suele "
                        "reflejar marca fuerte, tecnología propia o poder de precios difícil de replicar.", 34))
    # devolver la de mayor peso (evita saturar con 3 de rentabilidad)
    return max(out, key=lambda s: s["weight"]) if out else None


# ── SOLIDEZ FINANCIERA ────────────────────────────────────────────────────
def _leverage(ctx: Ctx):
    nde = ctx.g("net_debt_to_ebitda")
    if nde is None or ctx.is_financial:
        return None
    if nde < 0:
        return _sig("strength", "Solidez financiera", "Caja neta — sin deuda financiera neta",
                    "La empresa tiene más efectivo que deuda: posición de caja neta que le da flexibilidad para invertir, "
                    "resistir ciclos o retribuir al accionista sin depender de la financiación externa.", 40)
    t = ctx.t
    if nde > t.net_debt_ebitda_high:
        sev = "risk" if nde > t.net_debt_ebitda_high * 1.5 else "warning"
        w = 66 if sev == "risk" else 50
        return _sig(sev, "Solidez financiera", f"Apalancamiento elevado — {nde:.1f}x EBITDA",
                    f"Harían falta {_years_ebitda(nde)} de EBITDA íntegro para saldar la deuda neta. Por encima de "
                    f"{t.net_debt_ebitda_high:.0f}x el margen ante una caída de resultados o una subida de tipos se estrecha: "
                    "conviene vigilar la cobertura de intereses y el calendario de vencimientos.", w)
    if nde < t.net_debt_ebitda_low:
        return _sig("strength", "Solidez financiera", f"Deuda baja — {nde:.1f}x EBITDA",
                    f"La deuda neta equivale a {_years_ebitda(nde)} de EBITDA, un nivel cómodo que deja holgura financiera y "
                    "capacidad de maniobra ante imprevistos.", 30)
    return None


def _coverage(ctx: Ctx):
    ic = ctx.g("interest_coverage")
    if ic is None or ctx.is_financial:
        return None
    if ic < 1.5:
        return _sig("risk", "Solidez financiera", f"Cobertura de intereses crítica — {ic:.1f}x",
                    f"El beneficio operativo apenas cubre {ic:.1f} veces el gasto por intereses: un margen peligrosamente "
                    "fino que deja a la empresa muy expuesta ante cualquier caída del resultado operativo.", 64)
    t = ctx.t
    if ic < t.interest_coverage_low:
        return _sig("warning", "Solidez financiera", f"Cobertura de intereses justa — {ic:.1f}x",
                    f"El resultado operativo cubre {ic:.1f}x el gasto por intereses, por debajo del mínimo cómodo "
                    f"({t.interest_coverage_low:.0f}x): deja poco margen si los beneficios se resienten.", 46)
    if ic > 12:
        return _sig("strength", "Solidez financiera", f"Deuda fácilmente servible — cobertura {ic:.0f}x",
                    f"El beneficio operativo cubre {ic:.0f} veces el gasto por intereses: la carga financiera es holgada y "
                    "no compromete la operación.", 28)
    return None


def _liquidity(ctx: Ctx):
    cr = ctx.g("current_ratio")
    if cr is None or ctx.is_financial:
        return None
    t = ctx.t
    if cr < t.current_ratio_low:
        return _sig("warning", "Solidez financiera", f"Liquidez ajustada — current ratio {cr:.2f}x",
                    f"Los activos corrientes cubren solo {cr:.2f}x los pasivos de corto plazo: la empresa podría tensionarse "
                    "para atender sus obligaciones inmediatas si el flujo de caja se resiente. Habitual y manejable en "
                    "negocios con caja muy predecible.", 44)
    if cr > 3:
        return _sig("strength", "Solidez financiera", f"Liquidez muy holgada — current ratio {cr:.2f}x",
                    f"Los activos corrientes multiplican por {cr:.1f} los pasivos de corto plazo: cero tensión de caja, "
                    "aunque un exceso tan amplio podría señalar capital ocioso que no se está reinvirtiendo.", 26)
    return None


def _altman(ctx: Ctx):
    z = ctx.altman.get("z_score")
    zone = ctx.altman.get("zone")
    if z is None or ctx.is_financial:
        return None
    if zone == "distress":
        return _sig("risk", "Solidez financiera", f"Riesgo de insolvencia — Altman Z {z:.2f}",
                    f"El modelo de Altman sitúa a la empresa en zona de riesgo (Z {z:.2f} < 1.81), donde históricamente se "
                    "concentran las compañías con problemas de solvencia a 2 años. Señal de alerta que exige revisar deuda y "
                    "generación de caja.", 90)
    if zone == "safe":
        return _sig("strength", "Solidez financiera", f"Solvencia sólida — Altman Z {z:.2f}",
                    f"El Altman Z de {z:.2f} (> 2.99) ubica a la empresa en zona segura: baja probabilidad estadística de "
                    "problemas de solvencia según el modelo.", 32)
    return None


# ── FLUJO DE CAJA ─────────────────────────────────────────────────────────
def _fcf(ctx: Ctx):
    fcf = ctx.g("fcf") if ctx.g("fcf") is not None else ctx.g("free_cash_flow")
    neg_years = ctx.c.get("fcf_trend_negative_years")
    if neg_years is not None and neg_years >= 2:
        note = "" if ctx.is_growth else " Si no es una fase de inversión deliberada, compromete la autofinanciación."
        return _sig("risk", "Flujo de caja", f"Quema de caja recurrente — {neg_years} años",
                    f"La empresa lleva {neg_years} años consecutivos con flujo de caja libre negativo: consume más efectivo "
                    f"del que genera.{note}", 70)
    if fcf is not None and fcf < 0:
        if ctx.is_growth:
            return _sig("warning", "Flujo de caja", "Flujo de caja libre negativo",
                        "La empresa quema caja, algo esperable en una fase de fuerte inversión para crecer; la clave es que "
                        "esa inversión se traduzca en ingresos y márgenes futuros.", 40)
        return _sig("risk", "Flujo de caja", "Flujo de caja libre negativo",
                    "El negocio consume más efectivo del que genera tras invertir: depende de caja acumulada, deuda o "
                    "ampliaciones para sostenerse. Sostenible solo de forma transitoria.", 58)
    return None


def _earnings_quality(ctx: Ctx):
    q = ctx.g("fcf_to_net_income")
    if q is None:
        return None
    if q < 0.5:
        return _sig("warning", "Flujo de caja", "Calidad del beneficio baja",
                    f"El flujo de caja libre equivale a menos de la mitad del beneficio contable (FCF/BN {q:.0%}): parte de "
                    "las utilidades no se está convirtiendo en caja real, señal a vigilar (devengos, capex o capital de "
                    "trabajo).", 44)
    if q > 1.0:
        return _sig("strength", "Flujo de caja", "Beneficio de alta calidad",
                    f"El flujo de caja libre supera al beneficio contable (FCF/BN {q:.0%}): las utilidades se convierten "
                    "íntegramente en efectivo, señal de contabilidad conservadora y negocio que 'respira' caja.", 32)
    return None


# ── CRECIMIENTO ───────────────────────────────────────────────────────────
def _growth(ctx: Ctx):
    g3 = ctx.c.get("revenue_cagr_3y")
    if g3 is None:
        return None
    if g3 < 0:
        return _sig("warning", "Crecimiento", f"Ingresos en contracción — {_pct(g3)} anual",
                    f"Las ventas caen a un ritmo del {_pct(abs(g3))} anual en los últimos 3 años: un negocio que se encoge "
                    "presiona márgenes y valoración salvo que sea un bache puntual con catalizador de recuperación.", 50)
    if g3 > 0.15:
        return _sig("strength", "Crecimiento", f"Crecimiento fuerte — ingresos +{_pct(g3)} anual",
                    f"Los ingresos crecen {_pct(g3)} anual compuesto en 3 años: ritmo de expansión elevado que, si mantiene "
                    "márgenes, es el principal motor de creación de valor a largo plazo.", 42)
    return None


def _eps_growth(ctx: Ctx):
    e3 = ctx.c.get("eps_cagr_3y")
    if e3 is None:
        return None
    if e3 < -0.05:
        return _sig("warning", "Crecimiento", f"Beneficio por acción en descenso — {_pct(e3)} anual",
                    f"El BPA cae {_pct(abs(e3))} anual en 3 años: la rentabilidad por acción se erosiona, ya sea por menores "
                    "beneficios o por dilución. Contrasta con la evolución de ingresos para ubicar la causa.", 40)
    if e3 > 0.15:
        return _sig("strength", "Crecimiento", f"BPA en fuerte expansión — +{_pct(e3)} anual",
                    f"El beneficio por acción crece {_pct(e3)} anual compuesto: la rentabilidad para el accionista se "
                    "acelera, a menudo apoyada en apalancamiento operativo o recompras.", 34)
    return None


def _piotroski(ctx: Ctx):
    f = ctx.piotroski.get("score")
    if f is None:
        return None
    fy = ctx.piotroski.get("fiscal_year")
    yr = f" ({fy})" if fy else ""
    if f >= 8:
        return _sig("strength", "Crecimiento", f"Fortaleza financiera excepcional — Piotroski {f}/9",
                    f"Cumple {f} de las 9 señales de Piotroski{yr} sobre mejora en rentabilidad, estructura de capital y "
                    "eficiencia: un perfil de salud financiera en clara mejora año contra año.", 40)
    if f <= 2:
        return _sig("risk", "Crecimiento", f"Debilidad financiera — Piotroski {f}/9",
                    f"Solo cumple {f} de las 9 señales de Piotroski{yr}: múltiples indicadores contables de rentabilidad, "
                    "deuda o eficiencia se están deteriorando en el último ejercicio.", 60)
    return None


def _deterioration(ctx: Ctx):
    reasons = []
    r5 = ctx.c.get("revenue_cagr_5y")
    om3 = ctx.c.get("operating_margin_change_3y")
    ny = ctx.c.get("fcf_trend_negative_years")
    if r5 is not None and r5 < 0:
        reasons.append(f"ingresos decrecientes a 5 años ({_pct(r5)})")
    if om3 is not None and om3 < -0.03:
        reasons.append(f"márgenes operativos en caída ({_pct(om3)} en 3 años)")
    if ny is not None and ny >= 2:
        reasons.append(f"FCF negativo {ny} años")
    if len(reasons) >= 2:
        return _sig("risk", "Deterioro estructural", "Deterioro estructural del negocio",
                    "Coinciden varias señales de fondo: " + "; ".join(reasons) + ". Cuando se dan juntas, suelen apuntar a "
                    "un debilitamiento sostenido del negocio, no a un mal trimestre puntual.", 80)
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
                    "más en los rallies. Razonable con horizonte largo y tolerancia al riesgo; resta si buscas estabilidad.", 38)
    if b < t.beta_low:
        return _sig("strength", "Riesgo de mercado", f"Perfil defensivo — Beta {b:.2f}",
                    f"Con beta {b:.2f}, la acción se mueve menos que el mercado y tiende a amortiguar las caídas: un perfil "
                    "más estable, útil para reducir la volatilidad de una cartera.", 28)
    return None


def _drawdown(ctx: Ctx):
    dd = ctx.c.get("max_drawdown_1y")
    if dd is None or dd >= -0.30:
        return None
    return _sig("warning", "Riesgo de mercado", f"Caída pronunciada en el año — {_pct(dd)}",
                f"La acción ha llegado a caer {_pct(abs(dd))} desde máximos en el último año: una corrección profunda que "
                "puede ser oportunidad si el negocio sigue intacto, o el mercado anticipando un deterioro.", 34)


INTERPRETERS = [
    _pe, _ev_ebitda, _fcf_yield, _peg, _dcf,
    _roe, _spread, _margins,
    _leverage, _coverage, _liquidity, _altman,
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
                  dcf: Optional[dict] = None, is_growth: bool = False) -> Dict[str, List[dict]]:
    """Ejecuta todos los interpretadores y agrupa por tipo, ordenando por peso.

    Devuelve {"red_flags", "warnings", "strengths"} con ítems
    {"category", "reason", "detail"} listos para el frontend y el PDF.
    """
    ctx = Ctx(ratios, contextual, sector=sector, real_sector=real_sector,
              roic_wacc_spread=roic_wacc_spread, altman=altman,
              piotroski=piotroski, dcf=dcf, is_growth=is_growth)

    buckets = {"risk": [], "warning": [], "strength": []}
    for interp in INTERPRETERS:
        try:
            s = interp(ctx)
        except Exception:
            s = None
        if s and s["kind"] in buckets:
            buckets[s["kind"]].append(s)

    def _clean(items, cap=6):
        # ordena por materialidad (peso) y limita para mantener la lista de alto
        # valor, sin saturar con señales menores.
        items.sort(key=lambda s: s["weight"], reverse=True)
        return [{"category": s["category"], "reason": s["reason"], "detail": s["detail"]} for s in items[:cap]]

    return {
        "red_flags": _clean(buckets["risk"]),
        "warnings": _clean(buckets["warning"]),
        "strengths": _clean(buckets["strength"]),
    }
