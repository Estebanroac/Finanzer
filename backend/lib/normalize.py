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

REIT: el FFO (P/FFO, FFO por acción) se calcula SIEMPRE sobre el beneficio
REPORTADO (FFO = BN + D&A − ganancias por venta, financial_ratios.
funds_from_operations); el beneficio normalizado nunca entra en el FFO. Así las
ganancias por venta no se restan dos veces (una en el FFO y otra al normalizar).
"""
from typing import Any, Dict, List, Optional

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


def normalize(*, net_income: Optional[float], explicit_rows: Dict[str, Optional[float]],
              quarterly: Optional[Dict[str, Any]], basis: str,
              tax_rate_fallback: Optional[float] = None,
              annual_rows: Optional[Dict[str, List[Optional[float]]]] = None) -> Dict[str, Any]:
    """Beneficio reportado y normalizado, ítems con tipo/confianza/origen y one_off_pct.
    annual_rows: {fila de Yahoo: serie anual (más reciente primero)} para la recurrencia."""
    C = cfg("thresholds.normalization")
    items: List[Dict[str, Any]] = []
    ex = typed_items(explicit_rows or {}, annual_rows)
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
    applied_net = sum(i["net"] for i in items if i["applied"])
    has_explicit = any(i["type"] == "explicita" for i in items)
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
        "pe_unreliable": one_off is not None and one_off > C["one_off_pct"],
        "applied": has_explicit or has_inferred,
        "confidence": ("media" if has_inferred else "alta") if (has_explicit or has_inferred) else None,
        "inference": {"available": inferred["available"], "reason": inferred.get("reason")},
    }
