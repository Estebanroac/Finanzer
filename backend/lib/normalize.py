"""
Normalización de ganancias (etapa 7; spec cambio 3, RECON C1-C2, §6.3).

Dos niveles de confianza:

1. EXPLÍCITAS (confianza alta): filas de Yahoo de partidas no recurrentes.
   Tipos, sin contar dos veces (typed_items):
     a) con Total Unusual Items (o su versión sin goodwill): sus componentes
        Special Income Charges + ganancias por venta (Security, PPE, Business)
        si cuadran con el total (components_tolerance); si no, el total como
        un único tipo;
     b) sin total: Special Income Charges + ganancias por venta;
     c) componentes sueltos: ganancias por venta − (Restructuring, Write Off,
        Impairment, Other Special Charges)
   CONVENCIÓN DE SIGNOS: todo ítem se expresa como EFECTO SOBRE EL BENEFICIO
   (+ = ganancia que infló el beneficio, − = cargo que lo redujo). Yahoo mezcla
   dos convenciones: las filas "de resultado" (Total Unusual Items, Special
   Income Charges, Gain On Sale…) ya vienen con ese signo; las filas "de gasto"
   (Restructuring, Write Off, Impairment, Other Special Charges) vienen con el
   cargo en positivo y se cambian de signo. Por eso en JPM Special Income
   Charges (+) y Other Special Charges (−) tienen signos opuestos y son
   coherentes (RECON §6.3). Efecto fiscal: Tax Effect Of Unusual Items (mismo
   signo que el ítem bruto, repartido en proporción entre los tipos) si existe;
   si no, el tipo efectivo.
   Con ítems explícitos identificados, el score usa SIEMPRE el beneficio normalizado.

2. INFERIDAS (confianza media): picos de resultado no operativo. Por trimestre,
   no operativo = beneficio antes de impuestos − resultado operativo. Un
   trimestre del TTM es pico si su z-score robusto frente a los DEMÁS trimestres
   disponibles (mediana y MAD) supera el umbral, y si el exceso es material
   frente al beneficio antes de impuestos TTM. El exceso neto (por el tipo
   efectivo TTM) solo normaliza el beneficio si supera one_off_pct; siempre baja
   la confianza. Un trimestre con ítems explícitos no se infiere (ya está contado).
   Caso de control: NFLX 1T-26 (+2.59B frente a ~−0.14B habitual, RECON C1).

RECURRENCIA (prueba previa a normalizar): una partida del mismo TIPO y signo
que aparece en recurrence_min_years o más de los últimos recurrence_window
ejercicios anuales es recurrente: solo se normaliza el EXCESO del periodo actual
sobre su promedio en esos ejercicios, no la partida completa. Tipos: los
componentes de Yahoo (Special Income Charges = cargos especiales: deterioros,
litigios, reestructuración; ganancias por venta de valores, de activos fijos,
de negocios) cuando cuadran con Total Unusual Items; si no cuadran (JPM, FCX:
su Special Income Charges ya es el total), el total es un único tipo. Los picos
inferidos también: si el mismo pico (mismo signo) se repite en
recurrence_min_years o más trimestres de la historia, solo cuenta el exceso.

one_off_pct = |ítems no recurrentes netos| / |beneficio neto|. Si supera el
umbral, el P/E reportado se marca como no fiable y se muestra el normalizado.

COHERENCIA CON LA OPERACIÓN (F10 · N1, revisión del informe de NVIDIA): tras todo lo anterior, el beneficio no
puede superar lo que explican la operación y la caja. Antes de impuestos, de minoritarios y de discontinuadas: no
operativo = beneficio antes de impuestos − (resultado operativo + financieros netos + participadas por puesta en
equivalencia). Lo que, descontadas las ganancias ya normalizadas, pasa de `nonoperating_tolerance_revenue` de los
ingresos son ganancias no operativas que las filas de partidas inusuales no recogen (NVDA, TTM a julio de 2026:
ganancias de sus inversiones en acciones de 15,9 B$ en el trimestre de abril, en «otros ingresos» sin marcar): salen
del beneficio que puntúa, netas al tipo efectivo, sin prueba de recurrencia (no las explica el negocio), y se dicen
con su cifra. Las participadas cuentan como operación (KO y sus embotelladoras: recurrentes). No se aplica con
partidas estructurales (aseguradoras y conglomerados: su cartera ya sale entera) ni donde el margen operativo no
aplica (bancos, REIT).

REIT: el FFO (P/FFO, FFO por acción) se calcula SIEMPRE sobre el beneficio
REPORTADO (FFO = BN + D&A − ganancias por venta, financial_ratios.
funds_from_operations); el beneficio normalizado nunca entra en el FFO. Así las
ganancias por venta no se restan dos veces (una en el FFO y otra al normalizar).
"""
from typing import Any, Dict, List, Optional, Tuple

from settings import cfg

INCOME_SIGNED = ("Special Income Charges", "Gain On Sale Of Security", "Gain On Sale Of Ppe",
                 "Gain On Sale Of Business")
EXPENSE_SIGNED = ("Restructuring And Mergern Acquisition", "Write Off", "Asset Impairment Charge",
                  "Impairment Of Capital Assets", "Other Special Charges")
GAINS = ("Gain On Sale Of Security", "Gain On Sale Of Ppe", "Gain On Sale Of Business")


def _sum(values: List[Optional[float]]) -> Optional[float]:
    v = [x for x in values if x is not None]
    return sum(v) if v else None


TYPE_LABELS = {
    "Total Unusual Items": "partidas no recurrentes (total de Yahoo)",
    "Total Unusual Items Excluding Goodwill": "partidas no recurrentes (total de Yahoo, sin goodwill)",
    "Special Income Charges": "cargos especiales (deterioros, litigios, reestructuración)",
    "Gain On Sale Of Security": "ganancias por venta de valores",
    "Gain On Sale Of Ppe": "ganancias por venta de activos fijos",
    "Gain On Sale Of Business": "ganancias por venta de negocios",
    "Restructuring And Mergern Acquisition": "reestructuración y M&A",
    "Write Off": "amortizaciones extraordinarias (write-off)",
    "Asset Impairment Charge": "deterioros de activos",
    "Impairment Of Capital Assets": "deterioros de activos",
    "Other Special Charges": "otros cargos especiales",
}


def _effect(row: str, value: Optional[float]) -> Optional[float]:
    """Valor de Yahoo -> efecto sobre el beneficio (convención del módulo)."""
    if value is None:
        return None
    return -value if row in EXPENSE_SIGNED else value


def _components_match(total: Optional[float], sic: Optional[float], gains: List[Optional[float]]) -> bool:
    C = cfg("thresholds.normalization")
    if total is None or sic is None:
        return False
    return abs(sic + sum(v for v in gains if v is not None) - total) <= \
        max(C["components_tolerance"] * abs(total), C["components_tolerance_abs"])


def typed_items(rows: Dict[str, Optional[float]],
                annual_rows: Optional[Dict[str, List[Optional[float]]]] = None) -> Dict[str, Any]:
    """Partidas explícitas por TIPO (sin doble conteo) con su efecto sobre el beneficio.
    Los componentes solo valen como tipos si cuadran con el total en el periodo Y en
    cada ejercicio de la ventana de recurrencia (un tipo debe significar lo mismo cada año)."""
    C = cfg("thresholds.normalization")
    g = rows.get
    annual_rows = annual_rows or {}
    total_row = next((r for r in ("Total Unusual Items", "Total Unusual Items Excluding Goodwill")
                      if g(r) is not None), None)
    gains = [r for r in GAINS if g(r) is not None]
    sic = g("Special Income Charges")
    if total_row:
        def _year(k):
            def at(r):
                v = annual_rows.get(r) or []
                return v[k] if k < len(v) else None
            return at(total_row), at("Special Income Charges"), [at(r) for r in gains]
        years = [_year(k) for k in range(C["recurrence_window"])]
        match = _components_match(g(total_row), sic, [g(r) for r in gains]) and \
            all(_components_match(*y) for y in years if y[0] is not None)
        if match:
            types, level = ["Special Income Charges", *gains], "componentes_del_total"
        else:
            types, level = [total_row], total_row.lower().replace(" ", "_")
    elif sic is not None:
        types, level = ["Special Income Charges", *gains], "special_income_charges"
    else:
        types = [*gains, *[r for r in EXPENSE_SIGNED if g(r) is not None]]
        level = "componentes"
    items = [{"row": r, "label": TYPE_LABELS.get(r, r), "effect": _effect(r, g(r))} for r in types]
    items = [i for i in items if i["effect"] not in (None, 0)]
    return {"types": items, "level": level, "tax_effect": g("Tax Effect Of Unusual Items"),
            "gross": sum(i["effect"] for i in items) if items else None}


def recurrence(effect: float, annual: List[Optional[float]]) -> Dict[str, Any]:
    """¿El tipo es recurrente? Mismo signo en >= recurrence_min_years de los últimos
    recurrence_window ejercicios. Si lo es, el exceso sobre su promedio en esos años."""
    C = cfg("thresholds.normalization")
    window = [v for v in (annual or [])[:C["recurrence_window"]] if v is not None]
    same = [v for v in window if v != 0 and (v > 0) == (effect > 0)]
    if len(same) < C["recurrence_min_years"]:
        return {"recurrent": False, "years": len(same), "average": None, "excess": effect}
    avg = sum(same) / len(same)
    excess = (1 if effect > 0 else -1) * max(0.0, abs(effect) - abs(avg))
    return {"recurrent": True, "years": len(same), "average": avg, "excess": excess}


def robust_z(x: float, others: List[float], floor: float) -> Optional[float]:
    """(x − mediana) / (1.4826 · MAD) frente a los demás valores; MAD con suelo."""
    if len(others) < 3:
        return None
    s = sorted(others)
    n = len(s)
    med = s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2
    dev = sorted(abs(v - med) for v in s)
    mad = dev[n // 2] if n % 2 else (dev[n // 2 - 1] + dev[n // 2]) / 2
    scale = max(1.4826 * mad, floor)
    return (x - med) / scale if scale > 0 else None


def _median(v: List[float]) -> float:
    s = sorted(v)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def infer_peaks(q: Dict[str, Any], ttm_quarters: int = 4) -> Dict[str, Any]:
    """Picos de resultado no operativo en los trimestres del TTM."""
    C = cfg("thresholds.normalization")
    dates = q.get("dates") or []
    pre, op = q.get("Pretax Income") or [], q.get("Operating Income") or []
    tax = q.get("Tax Provision") or []
    unusual = q.get("Total Unusual Items") or q.get("Special Income Charges") or []
    n = min(len(pre), len(op))
    nonop = [(pre[i] - op[i]) if (pre[i] is not None and op[i] is not None) else None for i in range(n)]
    if len([x for x in nonop if x is not None]) < C["min_quarters"]:
        return {"available": False, "reason": f"menos de {C['min_quarters']} trimestres con resultado "
                                              "operativo y beneficio antes de impuestos", "peaks": []}
    pre_ttm = _sum(pre[:ttm_quarters])
    tax_ttm = _sum(tax[:ttm_quarters])
    lo, hi = C["tax_rate_bounds"]
    t_eff = (tax_ttm / pre_ttm) if (pre_ttm and tax_ttm is not None and pre_ttm > 0) else C["default_tax_rate"]
    t_eff = min(hi, max(lo, t_eff))
    floor = C["mad_floor_share_of_pretax"] * abs(pre_ttm or 0) / ttm_quarters

    def _is_peak(i):
        x = nonop[i]
        if x is None or (i < len(unusual) and unusual[i] not in (None, 0)):
            return None
        others = [v for j, v in enumerate(nonop) if j != i and v is not None]
        z = robust_z(x, others, floor)
        excess = x - _median(others) if others else None
        material = (excess is not None and pre_ttm and abs(excess) >= C["min_share_of_pretax"] * abs(pre_ttm))
        return (z, excess) if (z is not None and abs(z) > C["robust_z"] and material) else None

    all_peaks = {i: _is_peak(i) for i in range(n)}     # trimestres con ítems explícitos: no (sin doble conteo)
    peaks = []
    for i in range(min(ttm_quarters, n)):
        if not all_peaks[i]:
            continue
        z, excess = all_peaks[i]
        # Recurrencia: el mismo pico (mismo signo) en >= recurrence_min_years trimestres -> solo el exceso.
        same = [p[1] for p in all_peaks.values() if p and (p[1] > 0) == (excess > 0)]
        rec = len(same) >= C["recurrence_min_years"]
        gross = (1 if excess > 0 else -1) * max(0.0, abs(excess) - abs(sum(same) / len(same))) if rec else excess
        others = [v for j, v in enumerate(nonop) if j != i and v is not None]
        peaks.append({"quarter": dates[i] if i < len(dates) else None, "nonoperating": nonop[i],
                      "typical": _median(others), "peak_gross": excess, "gross": gross,
                      "net": gross * (1 - t_eff), "z": z, "tax_rate": t_eff,
                      "recurrent": rec, "repeats": len(same)})
    return {"available": True, "reason": None, "peaks": peaks, "tax_rate": t_eff}


def operating_pe(net_income: Optional[float], structural_net: float, market_cap: Optional[float]) -> Dict[str, Any]:
    """Fase 7 (registro #36; revisión, hallazgo A): P/E y E/P de una aseguradora o un conglomerado sobre su beneficio
    OPERATIVO (reportado − ganancias netas de la cartera). Operativo ≤ 0: sin P/E, aunque el reportado sea positivo;
    reportado negativo por minusvalías y operativo positivo: P/E operativo (BRK 2022)."""
    ni_op = (net_income - structural_net) if net_income is not None else None
    pe = (market_cap / ni_op) if (market_cap and ni_op is not None and ni_op > 0) else None
    return {"net_income_operating": ni_op, "pe": pe,
            "earnings_yield": (ni_op / market_cap) if (market_cap and ni_op is not None) else None,
            "basis": "operativo" if pe else "operativo_negativo"}


def coherence(parts: Optional[Dict[str, Optional[float]]], already_gross: float = 0.0) -> Dict[str, Any]:
    """F10 · N1: ganancias no operativas que la operación no explica. `parts` (del MISMO periodo que el beneficio):
    operating_income, net_interest (financieros netos), equity_income (participadas), pretax, tax y revenue.
    Se mira antes de impuestos, de minoritarios y de operaciones discontinuadas: no operativo = beneficio antes de
    impuestos − (operativo + financieros netos + participadas). Es la regla «beneficio frente a (operativo + financieros
    netos) × (1 − t)» sobre el beneficio continuado antes de minoritarios, para que los créditos fiscales y la parte
    de los minoritarios (NEE) o un negocio escindido (UL) no se tomen por ganancias. `already_gross`: las ganancias
    (antes de impuestos) que ya salieron por otras filas (NVDA, julio: 7,77 B$ de Yahoo): no se cuentan dos veces.
    Sale lo que pasa de `nonoperating_tolerance_revenue` de los ingresos, neto al tipo efectivo acotado.

    Plan, 29-oct: solo se recorta lo que se puede nombrar. El recorte es el menor del exceso y de las ganancias no
    operativas que presenta el emisor (`named_gains`: las ganancias de inversiones de EDGAR, NVDA 30,55 B$), sin las ya
    normalizadas. El exceso que nada nombra («otros ingresos» de una utility, D) no se recorta: queda en `unexplained`,
    se declara y baja la confianza."""
    C = cfg("thresholds.normalization")
    out: Dict[str, Any] = {"applied": False, "out": 0.0, "reason": None}
    p = parts or {}
    op, rev, pt, tx = p.get("operating_income"), p.get("revenue"), p.get("pretax"), p.get("tax")
    if op is None or rev is None or pt is None or tx is None:
        out["reason"] = "sin resultado operativo, ingresos o impuestos del mismo periodo"
        return out
    if pt <= 0 or rev <= 0:
        out["reason"] = "beneficio antes de impuestos no positivo: nada que inflen las ganancias no operativas"
        return out
    lo, hi = C["tax_rate_bounds"]
    t = min(max(tx / pt, lo), hi)
    nint, eq = p.get("net_interest") or 0.0, p.get("equity_income") or 0.0
    nonop = pt - (op + nint + eq)
    tol = C["nonoperating_tolerance_revenue"] * rev
    residual = nonop - already_gross
    excess = max(0.0, residual - tol)
    named = max(0.0, (p.get("named_gains") or 0.0) - already_gross)
    gross = min(excess, named)
    out.update(operating_income=op, net_interest=nint, equity_income=eq, pretax=pt, revenue=rev, tax_rate=t,
               tax_source=f"tipo efectivo {t:.1%}" + ("" if lo < tx / pt < hi else " (acotado)"),
               nonoperating=nonop, already_normalized=already_gross, residual=residual, tolerance=tol,
               excess=excess, named=named, gross=gross, unexplained=excess - gross, out=gross * (1 - t))
    out["applied"] = out["out"] > 0
    return out


def tax_rate_normalized(pretax: Optional[float], tax: Optional[float],
                        history: Optional[List[Tuple[Optional[float], Optional[float]]]] = None) -> Dict[str, Any]:
    """F10 · N1b: el tipo con que se lee el beneficio después de impuestos. La mediana de los tipos efectivos del periodo
    y de los últimos ejercicios (`history`: [(beneficio antes de impuestos, impuestos)], el más reciente primero), hasta
    `tax_median_years`, de los que tienen beneficio antes de impuestos positivo y un tipo no negativo (acotado arriba
    a `tax_rate_bounds`): un tipo negativo es un beneficio fiscal, no un tipo. Un beneficio fiscal puntual queda fuera
    por la mediana; uno recurrente (créditos fiscales de una utility) es su tipo. Con menos de `tax_median_min` tipos
    válidos, el tipo legal (`valuation.tax.statutory_rate`)."""
    C = cfg("thresholds.normalization")
    hi = C["tax_rate_bounds"][1]
    pairs = [(pretax, tax)] + list(history or [])
    rates = [min(t / p, hi) for p, t in pairs[:C["tax_median_years"]]
             if p is not None and t is not None and p > 0 and t >= 0]
    cur = (tax / pretax) if (pretax and tax is not None and pretax > 0) else None
    if len(rates) < C["tax_median_min"]:
        r = cfg("valuation.tax.statutory_rate")
        return {"rate": r, "period_rate": cur, "rates": rates,
                "source": f"tipo legal {r:.1%} (solo {len(rates)} tipos efectivos válidos en el periodo y los últimos "
                          f"ejercicios; hacen falta {C['tax_median_min']})"}
    srt = sorted(rates)
    n = len(srt)
    r = srt[n // 2] if n % 2 else (srt[n // 2 - 1] + srt[n // 2]) / 2
    return {"rate": r, "period_rate": cur, "rates": rates,
            "source": f"mediana de {n} tipos efectivos (el periodo y los últimos ejercicios) {r:.1%}"}


def after_tax(parts: Optional[Dict[str, Any]], income: float, charges_back: float = 0.0,
              named_gains_left: float = 0.0) -> Dict[str, Any]:
    """F10 · N1b: el beneficio (continuado, tras las demás partidas) frente a lo que explica la operación después de
    impuestos: (operativo + cargos devueltos + financieros netos + participadas) × (1 − t normalizada) + minoritarios
    (la parte del resultado de los minoritarios, como se reporta: con minoritarios que absorben pérdidas, NEE, el
    beneficio del accionista supera al consolidado; es una atribución, no una ganancia). Lo que pasa de
    `nonoperating_tolerance_revenue` de los ingresos sale (ya es neto de impuestos): participadas netas de impuestos
    (FIS), beneficios fiscales puntuales (UBER) u otros ingresos después del beneficio antes de impuestos. Continua.

    Plan, 29-oct: solo se recorta lo que se puede nombrar: el menor del exceso y de (participadas netas de impuestos +
    beneficio fiscal frente al tipo normalizado, con beneficio antes de impuestos positivo + las ganancias nombradas que
    N1 no recortó, `named_gains_left`, netas). El resto queda en `unexplained` (ECHO: un deterioro sin etiqueta dentro
    del operativo no se toma por ganancia)."""
    C = cfg("thresholds.normalization")
    p = parts or {}
    op, rev = p.get("operating_income"), p.get("revenue")
    if op is None or rev is None or rev <= 0:
        return {"applied": False, "out": 0.0, "reason": "sin resultado operativo o ingresos del mismo periodo"}
    tr = tax_rate_normalized(p.get("pretax"), p.get("tax"), p.get("tax_history"))
    nint, eq = p.get("net_interest") or 0.0, p.get("equity_income") or 0.0
    core = op + charges_back + nint + eq
    mi = p.get("minority_interests") or 0.0
    explained = (core * (1 - tr["rate"]) if core > 0 else core) + mi
    tol = C["nonoperating_tolerance_revenue"] * rev
    excess = max(0.0, income - explained - tol)
    pt, tx = p.get("pretax"), p.get("tax")
    tax_named = max(0.0, tr["rate"] * pt - tx) if (pt is not None and tx is not None and pt > 0) else 0.0
    eq_named = max(0.0, p.get("equity_income_net_of_tax") or 0.0)
    gains_named = max(0.0, named_gains_left) * (1 - tr["rate"])
    named = eq_named + tax_named + gains_named
    out = min(excess, named)
    return {"applied": out > 0, "out": out, "income": income, "operating_income": op, "charges_back": charges_back,
            "net_interest": nint, "equity_income": eq, "equity_income_net_of_tax": p.get("equity_income_net_of_tax"),
            "minority_interests": mi,
            "revenue": rev, "tax_rate": tr["rate"], "tax_source": tr["source"], "period_tax_rate": tr["period_rate"],
            "explained": explained, "tolerance": tol, "excess": excess, "named": named,
            "named_equity_net_of_tax": eq_named, "named_tax_benefit": tax_named, "named_gains": gains_named,
            "unexplained": excess - out, "reason": None}


def pieces_operating_income(cut_value: Optional[float], cut_field: Optional[Dict[str, Any]], cut: Optional[str],
                            yahoo_quarterly: Optional[float]) -> Dict[str, Any]:
    """F10 · margen operativo con una sola verdad: el resultado operativo de las piezas de la normalización es el del
    corte, el mismo que se enseña y puntúa (el EBIT que presenta el emisor en SEC EDGAR, fuente principal desde la fase
    3; si no, la suma de los 4 trimestres de Yahoo), cuando es de doce meses que acaban en el mismo corte que los
    trimestres. Si no, la fila trimestral de Yahoo, como respaldo declarado. -> {value, source, yahoo_quarterly}."""
    f = cut_field or {}
    if cut_value is not None and cut and f.get("period_type") == "ttm" and f.get("period_end") == cut:
        src = ("SEC EDGAR: el EBIT que presenta el emisor, el del corte (el que se enseña)"
               if f.get("source") == "sec_edgar" else "Yahoo: suma de los 4 trimestres del corte (el que se enseña)")
        return {"value": cut_value, "source": src, "yahoo_quarterly": yahoo_quarterly}
    return {"value": yahoo_quarterly, "yahoo_quarterly": yahoo_quarterly,
            "source": "respaldo: Yahoo, suma de los 4 trimestres (el resultado operativo del corte no es de ese periodo)"}


def operating(operating_income: Optional[float], revenue: Optional[float], items: List[Dict[str, Any]],
              pretax: Optional[float] = None, net_interest: Optional[float] = None,
              equity_income: Optional[float] = None, known_inside: float = 0.0) -> Dict[str, Any]:
    """F10 · margen operativo con una sola verdad: el resultado operativo sin las partidas que la normalización ya quita
    del beneficio y que pueden ir DENTRO de él (`operating_item_types`: cargos especiales, reestructuración, deterioros,
    ventas de negocios o de activos fijos, y el total de Yahoo cuando sus componentes no cuadran), con su signo (en las
    dos direcciones: SOLV, la ganancia de la venta de P&F) y solo lo aplicado (el exceso no recurrente), como el margen
    neto. Las ganancias por venta de valores van siempre debajo del operativo.

    Dentro o debajo del operativo: las filas de Yahoo no lo dicen (WDC: +5,77 B$ de «Special Income Charges» que son la
    ganancia de su participación en Sandisk, debajo del operativo). Lo dice la identidad del estado: no operativo =
    beneficio antes de impuestos − (operativo + financieros netos + participadas), sin las partidas no operativas ya
    identificadas. Ese no operativo solo explica partidas de su mismo signo (un no operativo positivo, ganancias; uno
    negativo, cargos), hasta su importe: esas van debajo; las demás estaban dentro. Sin beneficio antes de impuestos no
    se puede mirar: se toman dentro (`below_the_line` None). Los cargos que corroboran las etiquetas operativas de EDGAR
    (`known_inside`, ≤ 0: deterioros, reestructuración, litigios, I+D adquirida; Plan, 29-oct) están dentro sin más (ABBV:
    su no operativo negativo, de pagos contingentes, no los explica); la identidad reparte solo el resto.

    Por debajo de `label_min_diff` del mayor de los dos, el normalizado no se distingue del reportado (differs=False)."""
    C = cfg("thresholds.normalization")
    types = set(C["operating_item_types"])
    applied = [i for i in items if i.get("applied") and i.get("type") == "explicita" and i.get("gross")]
    its = [i for i in applied if i.get("item_type") in types]
    tagged = sum(i["gross"] for i in its)
    below = None
    if pretax is not None and operating_income is not None:
        rest = (pretax - (operating_income + (net_interest or 0.0) + (equity_income or 0.0))
                - sum(i["gross"] for i in applied if i.get("item_type") not in types))
        pos = sum(i["gross"] for i in its if i["gross"] > 0)
        neg = sum(i["gross"] for i in its if i["gross"] < 0)
        neg_unknown = neg - max(neg, min(0.0, known_inside or 0.0))     # lo que EDGAR no corrobora
        below = min(pos, rest) if rest > 0 else max(neg_unknown, rest)
    gross = tagged - (below or 0.0)
    norm = (operating_income - gross) if operating_income is not None else None
    ok = bool(revenue) and revenue > 0
    differs = bool(norm is not None and its and abs(gross) > C["label_min_diff"] * max(abs(operating_income),
                                                                                         abs(norm)))
    return {"reported": operating_income, "normalized": norm, "revenue": revenue, "gross": gross,
            "tagged": tagged, "below_the_line": below,
            "margin_reported": operating_income / revenue if (ok and operating_income is not None) else None,
            "margin_normalized": norm / revenue if (ok and norm is not None) else None, "differs": differs,
            "items": [{"item_type": i["item_type"], "label": i.get("label"), "gross": i["gross"]} for i in its]}


def fy_operating(statements_fy: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """F10 · margen operativo con una sola verdad (verificación de «Modelo general», regla 4): sin corte trimestral, el
    margen operativo sale de los estados del último ejercicio (el EBIT que presenta el emisor, si EDGAR lo tiene), los
    mismos que usan las piezas de la normalización, no del `operatingIncome` de quoteSummary, que es otra definición o
    periodo (CRL: 604 M$ frente a 25 M$ presentados; FDXF: −508 M$ frente a 540 M$). -> {value, operating_income,
    revenue, year} o None sin las dos cifras del ejercicio."""
    st = statements_fy or {}
    oi = (st.get("operating_income") or [None])[0]
    rev = (st.get("revenue") or [None])[0]
    if oi is None or not rev or rev <= 0:
        return None
    return {"value": oi / rev, "operating_income": oi, "revenue": rev, "year": (st.get("inc_years") or [None])[0]}


def _unreliable(ni, struct_net, other_net, limit):
    base = (ni - struct_net) if ni is not None else None
    return bool(base and other_net and abs(other_net) / abs(base) > limit)


def normalize(*, net_income: Optional[float], explicit_rows: Dict[str, Optional[float]],
              quarterly: Optional[Dict[str, Any]], basis: str,
              tax_rate_fallback: Optional[float] = None,
              annual_rows: Optional[Dict[str, List[Optional[float]]]] = None,
              investment_gains: Optional[Dict[str, Any]] = None,
              coherence_parts: Optional[Dict[str, Optional[float]]] = None,
              discontinued: Optional[Dict[str, Any]] = None,
              edgar_charges: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Beneficio reportado y normalizado, ítems con tipo/confianza/origen y one_off_pct.
    annual_rows: {fila de Yahoo: serie anual (más reciente primero)} para la recurrencia.
    investment_gains (fase 7, registro #36): ganancias de inversiones del periodo de una aseguradora o un
    conglomerado ({value, concept, how}, de SEC EDGAR). Ítem ESTRUCTURAL: se excluye entero, sin prueba de recurrencia
    (se repiten cada año: no son inusuales, son otra actividad), después de impuestos al tipo legal. Con él, las
    ganancias por venta de valores de Yahoo no se cuentan otra vez, y un total de partidas inusuales que las incluya
    tampoco.
    coherence_parts (F10 · N1): las piezas de la coherencia con la operación (ver `coherence`); None: no se mira (sin
    ellas, o donde no aplica). Con ellas, también después de impuestos (F10 · N1b, `after_tax`; `tax_history` y
    `equity_income_net_of_tax` en las piezas).
    discontinued (F10 · N1b): resultado de operaciones discontinuadas del periodo ({value, source, period_total}, neto
    de impuestos): el normalizado parte del beneficio de operaciones continuadas; sale entero (sin tolerancia) y se dice.
    Solo si el beneficio usado las lleva: más cerca del total del periodo (`period_total`, con discontinuadas) que del
    total sin ellas; si no (ya es el continuado) o sin el total, se dicen sin restarlas.
    edgar_charges (F10 · Plan, 29-oct): cargos y ventas del periodo con etiquetas estándar de EDGAR
    (`sec_edgar.charges_ttm`). Sale, por signo, solo lo que identifican de más frente a las filas operativas de Yahoo
    (sin doble conteo), con la prueba de recurrencia sobre su serie anual."""
    C = cfg("thresholds.normalization")
    items: List[Dict[str, Any]] = []
    rows = dict(explicit_rows or {})
    dv = (discontinued or {}).get("value")
    if dv:
        tot = discontinued.get("period_total")
        inside = (tot is not None and net_income is not None
                  and abs(net_income - tot) <= abs(net_income - (tot - dv)))
        how = ("el normalizado parte del beneficio de operaciones continuadas" if inside else
               ("el beneficio usado ya es el de operaciones continuadas" if tot is not None and net_income is not None
                else "sin el total del periodo para saber si el beneficio usado las lleva")
               + (f" ({net_income / 1e9:.2f}B frente a {tot / 1e9:.2f}B con ellas)"
                  if tot is not None and net_income is not None else "") + ": no se restan")
        items.append({"type": "discontinuadas", "confidence": "alta", "applied": inside,
                      "item_type": "operaciones_discontinuadas", "label": "resultado de operaciones discontinuadas",
                      "origin": f"{discontinued.get('source')}: {dv / 1e9:+.2f}B ({basis}); {how}",
                      "period_gross": dv, "gross": dv, "net": dv, "tax_source": "neto de impuestos (como se reporta)",
                      "recurrent": False, "recurrent_years": None, "recurrent_average": None,
                      "recurrence_window": None})
    structural = investment_gains if (investment_gains or {}).get("value") not in (None, 0) else None
    if structural:
        # Sin doble conteo (revisión, hallazgo C): las ganancias por venta de valores de Yahoo salen, y también del
        # total de partidas inusuales si lo trae; el resto (deterioros, reestructuraciones…) se sigue normalizando.
        sec = rows.pop("Gain On Sale Of Security", None)
        for tr in ("Total Unusual Items", "Total Unusual Items Excluding Goodwill"):
            if rows.get(tr) is not None and sec is not None:
                rows[tr] = rows[tr] - sec
        # Tipo efectivo del ejercicio si es plausible (emisores de Bermudas o Suiza en US GAAP), si no el legal
        lo, hi = cfg("valuation.tax.effective_bounds")
        t = (tax_rate_fallback if (tax_rate_fallback is not None and lo <= tax_rate_fallback <= hi)
             else cfg("valuation.tax.statutory_rate"))
        g = float(structural["value"])
        items.append({"type": "estructural", "confidence": "alta", "applied": True,
                      "item_type": "ganancias_de_inversiones",
                      "label": "ganancias de inversiones (realizadas y no realizadas)",
                      "origin": f"SEC EDGAR ({structural.get('concept')}): {structural.get('how')} · beneficio operativo "
                                "de una aseguradora o un conglomerado: sin las ganancias de su cartera",
                      "period_gross": g, "gross": g, "net": g * (1 - t),
                      "tax_source": f"tipo {t:.1%}", "recurrent": True, "recurrent_years": None,
                      "recurrent_average": None, "recurrence_window": None})
    ex = typed_items(rows, annual_rows)
    if ex["gross"] not in (None, 0):
        # Efecto fiscal: tipo implícito de Yahoo (Tax Effect / bruto) aplicado a cada tipo,
        # si es un tipo plausible (tax_rate_bounds); si no (o con bruto ~0 por tipos de signo
        # contrario que se compensan), el tipo efectivo.
        lo, hi = C["tax_rate_bounds"]
        implied = ex["tax_effect"] / ex["gross"] if ex["tax_effect"] is not None else None
        if implied is not None and lo <= implied <= hi:
            t, tax_src = implied, f"Tax Effect Of Unusual Items (tipo implícito {implied:.1%})"
        else:
            t = tax_rate_fallback if tax_rate_fallback is not None else C["default_tax_rate"]
            tax_src = f"tipo efectivo {t:.1%}"
        keep = 1 - t
        for it in ex["types"]:
            annual = [_effect(it["row"], v) for v in (annual_rows or {}).get(it["row"], [])]
            rec = recurrence(it["effect"], annual)
            items.append({
                "type": "explicita", "confidence": "alta", "applied": True,
                "item_type": it["row"], "label": it["label"],
                "origin": f"Yahoo: {it['row']} ({basis}; nivel {ex['level']})",
                "period_gross": it["effect"], "gross": rec["excess"], "net": rec["excess"] * keep,
                "tax_source": tax_src, "recurrent": rec["recurrent"], "recurrent_years": rec["years"],
                "recurrent_average": rec["average"], "recurrence_window": C["recurrence_window"],
            })
    ec = edgar_charges or {}
    if ec and not structural:
        # F10 · Plan, 29-oct: lo que EDGAR identifica de más (GIS, ABBV, INTC), por signo, frente a todas las filas de
        # Yahoo (DLR: su venta de inmuebles va en «Gain On Sale Of Security») y, las ganancias por venta, frente a las
        # discontinuadas aplicadas, en bruto (MLM: la venta a Quikrete ya sale como discontinuada); la misma prueba de
        # recurrencia y el mismo tipo que las explícitas (sin ellas, el efectivo)
        ytypes = ex["types"]
        t_e = tax_rate_fallback if tax_rate_fallback is not None else C["default_tax_rate"]
        disc = sum(i["gross"] for i in items if i["type"] == "discontinuadas" and i["applied"] and i["gross"] > 0)
        for key, extra, label in (
                ("neg", min(0.0, (ec.get("neg") or 0.0) - sum(i["effect"] for i in ytypes if i["effect"] < 0)),
                 "cargos que presenta el emisor y no recogen las filas de Yahoo (deterioros, reestructuración, "
                 "litigios, I+D adquirida)"),
                ("pos", max(0.0, (ec.get("pos") or 0.0) - sum(i["effect"] for i in ytypes if i["effect"] > 0)
                        - disc / (1 - t_e)),
                 "ganancias por venta de negocios o activos que presenta el emisor y no recogen las filas de Yahoo")):
            if not extra:
                continue
            rec = recurrence(extra, [a.get(key) for a in ec.get("annual") or []])
            tags = ", ".join(f"{c} {v / 1e9:+.2f}B" for c, v in (ec.get("detail") or {}).items())
            items.append({"type": "explicita", "confidence": "alta", "applied": True,
                          "item_type": "EDGAR: cargos" if key == "neg" else "EDGAR: ventas", "label": label,
                          "origin": f"SEC EDGAR, etiquetas estándar ({basis}): {tags}; de más frente a Yahoo "
                                    f"{extra / 1e9:+.2f}B",
                          "period_gross": extra, "gross": rec["excess"], "net": rec["excess"] * (1 - t_e),
                          "tax_source": f"tipo efectivo {t_e:.1%}", "recurrent": rec["recurrent"],
                          "recurrent_years": rec["years"], "recurrent_average": rec["average"],
                          "recurrence_window": C["recurrence_window"]})
    if structural:
        # Revisión, hallazgo B: en una aseguradora el resultado no operativo ES su cartera (ya excluida entera): no
        # se infieren picos de él (se restaría dos veces).
        inferred = {"available": False, "peaks": [],
                    "reason": "aseguradora o conglomerado: el resultado no operativo es la cartera, ya excluida"}
    else:
        inferred = infer_peaks(quarterly) if quarterly else {"available": False, "reason": "sin estados trimestrales",
                                                             "peaks": []}
    ni = net_income
    for p in inferred["peaks"]:
        share = abs(p["net"]) / abs(ni) if ni else None
        items.append({"type": "inferida", "confidence": "media", "item_type": "pico_no_operativo",
                      "label": "pico de resultado no operativo",
                      "origin": f"pico de resultado no operativo en el trimestre {p['quarter']} "
                                f"(z robusto {p['z']:.1f}; habitual {p['typical'] / 1e9:+.2f}B frente a "
                                f"{p['nonoperating'] / 1e9:+.2f}B)",
                      "period_gross": p["peak_gross"], "gross": p["gross"], "net": p["net"],
                      "tax_source": f"tipo efectivo TTM {p['tax_rate']:.1%}",
                      "recurrent": p["recurrent"], "recurrent_years": p["repeats"],
                      "applied": share is not None and share > C["one_off_pct"]})
    co = None
    if coherence_parts is not None and not structural and ni is not None:
        # Ganancias ya normalizadas por otras filas (las positivas: los cargos van dentro del resultado operativo).
        done = sum(i["gross"] for i in items if i["applied"] and (i.get("gross") or 0) > 0
                   and i["type"] != "discontinuadas")
        co = coherence(coherence_parts, done)
        if co["applied"]:
            items.append({"type": "coherencia", "confidence": "alta", "applied": True,
                          "item_type": "ganancias_no_operativas",
                          "label": "ganancias no operativas que la operación no explica",
                          "origin": (f"beneficio antes de impuestos {co['pretax'] / 1e9:.2f}B frente a resultado "
                                     f"operativo {co['operating_income'] / 1e9:.2f}B + financieros netos "
                                     f"{co['net_interest'] / 1e9:+.2f}B + participadas "
                                     f"{co['equity_income'] / 1e9:+.2f}B: {co['nonoperating'] / 1e9:.2f}B no "
                                     f"operativos" + (f", {done / 1e9:.2f}B ya normalizados" if done else "")
                                     + f"; sale lo que pasa del {C['nonoperating_tolerance_revenue']:.0%} de los "
                                     f"ingresos ({co['tolerance'] / 1e9:.2f}B), hasta lo que nombran las ganancias de "
                                     f"inversiones que presenta el emisor ({co['named'] / 1e9:.2f}B sin las ya "
                                     f"normalizadas)" + (f"; {co['unexplained'] / 1e9:.2f}B sin partida que los nombre "
                                                         "no se recortan" if co["unexplained"] > 0 else "")),
                          "period_gross": co["residual"], "gross": co["gross"], "net": co["out"],
                          "tax_source": co["tax_source"], "recurrent": False, "recurrent_years": None,
                          "recurrent_average": None, "recurrence_window": None})
    at = None
    if coherence_parts is not None and not structural and ni is not None:
        # F10 · N1b: después de impuestos, sobre el beneficio que queda tras las demás partidas; los cargos que se
        # devuelven (deterioros dentro del resultado operativo) suben el techo.
        back = -sum(i["gross"] for i in items if i["applied"] and i["type"] in ("explicita", "inferida")
                    and (i.get("gross") or 0) < 0)
        left = max(0.0, (co or {}).get("named", max(0.0, (coherence_parts.get("named_gains") or 0.0)))
                   - (co or {}).get("gross", 0.0))
        at = after_tax(coherence_parts, ni - sum(i["net"] for i in items if i["applied"]), back, left)
        if at["applied"]:
            pt_rate = at["period_tax_rate"]
            why = []
            if at.get("equity_income_net_of_tax"):
                why.append(f"participadas netas de impuestos {at['equity_income_net_of_tax'] / 1e9:+.2f}B")
            if pt_rate is None or pt_rate < 0:
                why.append("tipo efectivo del periodo " + ("negativo" if pt_rate is not None else "no calculable")
                           + " (un beneficio fiscal)")
            elif abs(pt_rate - at["tax_rate"]) > 1e-9:
                why.append(f"tipo efectivo del periodo {pt_rate:.1%}")
            items.append({"type": "despues_de_impuestos", "confidence": "alta", "applied": True,
                          "item_type": "beneficio_despues_de_impuestos",
                          "label": "beneficio que la operación no explica después de impuestos",
                          "origin": (f"beneficio {at['income'] / 1e9:.2f}B frente a (operativo "
                                     f"{at['operating_income'] / 1e9:.2f}B"
                                     + (f" + cargos devueltos {at['charges_back'] / 1e9:.2f}B" if at["charges_back"]
                                        else "")
                                     + f" + financieros netos {at['net_interest'] / 1e9:+.2f}B + participadas "
                                     f"{at['equity_income'] / 1e9:+.2f}B) × (1 − {at['tax_rate']:.1%})"
                                     + (f" + minoritarios {at['minority_interests'] / 1e9:+.2f}B"
                                        if at["minority_interests"] else "") + " = "
                                     f"{at['explained'] / 1e9:.2f}B ({at['tax_source']}); sale lo que pasa del "
                                     f"{C['nonoperating_tolerance_revenue']:.0%} de los ingresos "
                                     f"({at['tolerance'] / 1e9:.2f}B)" + (": " + ", ".join(why) if why else "")
                                     + "; hasta lo nombrado: " + ", ".join(
                                         x for x in (
                                             f"participadas netas de impuestos {at['named_equity_net_of_tax'] / 1e9:.2f}B"
                                             if at["named_equity_net_of_tax"] else "",
                                             f"beneficio fiscal frente al tipo normalizado "
                                             f"{at['named_tax_benefit'] / 1e9:.2f}B" if at["named_tax_benefit"] else "",
                                             f"ganancias de inversiones netas {at['named_gains'] / 1e9:.2f}B"
                                             if at["named_gains"] else "") if x)
                                     + (f"; {at['unexplained'] / 1e9:.2f}B sin partida que los nombre no se recortan"
                                        if at["unexplained"] > 0 else "")),
                          "period_gross": at["out"], "gross": at["out"], "net": at["out"],
                          "tax_source": at["tax_source"], "recurrent": False, "recurrent_years": None,
                          "recurrent_average": None, "recurrence_window": None})
    applied_net = sum(i["net"] for i in items if i["applied"])
    struct_net = sum(i["net"] for i in items if i["applied"] and i["type"] == "estructural")
    has_explicit = any(i["type"] in ("explicita", "estructural", "coherencia", "despues_de_impuestos")
                       or (i["type"] == "discontinuadas" and i["applied"]) for i in items)
    has_inferred = any(i["type"] == "inferida" and i["applied"] for i in items)
    normalized = (ni - applied_net) if (ni is not None and (has_explicit or has_inferred)) else ni
    one_off = (abs(applied_net) / abs(ni)) if (ni and (has_explicit or has_inferred)) else (0.0 if ni else None)
    return {
        "basis": basis,
        "reported_net_income": ni,
        "normalized_net_income": normalized,
        "items": items,
        "one_off_net": applied_net if (has_explicit or has_inferred) else 0.0,
        "one_off_pct": one_off,
        # El P/E de una aseguradora ya es el operativo (main.py): su fiabilidad depende solo de lo demás.
        "pe_unreliable": _unreliable(ni, struct_net, applied_net - struct_net, C["one_off_pct"]),
        "structural_net": struct_net,
        "applied": has_explicit or has_inferred,
        "confidence": ("media" if has_inferred else "alta") if (has_explicit or has_inferred) else None,
        "inference": {"available": inferred["available"], "reason": inferred.get("reason")},
        "coherence": co,
        "after_tax": at,
        # Plan, 29-oct: el exceso sobre el techo que ninguna partida nombra: no se recorta, se declara (baja la confianza)
        "unexplained": {"pre_tax": (co or {}).get("unexplained") or 0.0, "after_tax": (at or {}).get("unexplained") or 0.0},
    }
