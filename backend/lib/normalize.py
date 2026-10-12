"""
Normalización de ganancias (etapa 7; spec cambio 3, RECON C1-C2, §6.3).

Dos niveles de confianza:

1. EXPLÍCITAS (confianza alta): filas de Yahoo de partidas no recurrentes.
   Jerarquía para no contar dos veces (se usa el PRIMER nivel con dato):
     a) Total Unusual Items
     b) Total Unusual Items Excluding Goodwill
     c) Special Income Charges + ganancias por venta (Security, PPE, Business)
     d) componentes sueltos: ganancias por venta − (Restructuring, Write Off,
        Impairment, Other Special Charges)
   CONVENCIÓN DE SIGNOS: todo ítem se expresa como EFECTO SOBRE EL BENEFICIO
   (+ = ganancia que infló el beneficio, − = cargo que lo redujo). Yahoo mezcla
   dos convenciones: las filas "de resultado" (Total Unusual Items, Special
   Income Charges, Gain On Sale…) ya vienen con ese signo; las filas "de gasto"
   (Restructuring, Write Off, Impairment, Other Special Charges) vienen con el
   cargo en positivo y se cambian de signo. Por eso en JPM Special Income
   Charges (+) y Other Special Charges (−) tienen signos opuestos y son
   coherentes (RECON §6.3). Efecto fiscal: Tax Effect Of Unusual Items (mismo
   signo que el ítem bruto) si existe; si no, el tipo efectivo.
   Con ítems explícitos identificados, el score usa SIEMPRE el beneficio normalizado.

2. INFERIDAS (confianza media): picos de resultado no operativo. Por trimestre,
   no operativo = beneficio antes de impuestos − resultado operativo. Un
   trimestre del TTM es pico si su z-score robusto frente a los DEMÁS trimestres
   disponibles (mediana y MAD) supera el umbral, y si el exceso es material
   frente al beneficio antes de impuestos TTM. El exceso neto (por el tipo
   efectivo TTM) solo normaliza el beneficio si supera one_off_pct; siempre baja
   la confianza. Un trimestre con ítems explícitos no se infiere (ya está contado).
   Caso de control: NFLX 1T-26 (+2.59B frente a ~−0.14B habitual, RECON C1).

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


def explicit_items(rows: Dict[str, Optional[float]]) -> Dict[str, Any]:
    """Ítems explícitos de UN periodo (TTM ya sumado o un ejercicio).

    rows: {fila de Yahoo: valor}. Devuelve {gross, tax_effect, level, components}
    con gross en convención "efecto sobre el beneficio"."""
    def g(r):
        return rows.get(r)
    comps: List[Dict[str, Any]] = []
    for level, row in (("total_unusual_items", "Total Unusual Items"),
                       ("total_unusual_items_ex_goodwill", "Total Unusual Items Excluding Goodwill")):
        if g(row) is not None:
            return {"gross": g(row), "tax_effect": g("Tax Effect Of Unusual Items"), "level": level,
                    "components": [{"row": row, "effect": g(row)}]}
    if g("Special Income Charges") is not None:
        comps.append({"row": "Special Income Charges", "effect": g("Special Income Charges")})
        comps += [{"row": r, "effect": g(r)} for r in GAINS if g(r) is not None]
        level = "special_income_charges"
    else:
        comps += [{"row": r, "effect": g(r)} for r in GAINS if g(r) is not None]
        comps += [{"row": r, "effect": -g(r)} for r in EXPENSE_SIGNED if g(r) is not None]
        level = "componentes"
    gross = _sum([c["effect"] for c in comps])
    if gross is None:
        return {"gross": None, "tax_effect": None, "level": None, "components": []}
    return {"gross": gross, "tax_effect": g("Tax Effect Of Unusual Items"), "level": level, "components": comps}


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
    peaks = []
    for i in range(min(ttm_quarters, n)):
        x = nonop[i]
        if x is None:
            continue
        if i < len(unusual) and unusual[i] not in (None, 0):
            continue    # trimestre con ítems explícitos: ya contado (sin doble conteo)
        others = [v for j, v in enumerate(nonop) if j != i and v is not None]
        z = robust_z(x, others, floor)
        excess = x - _median(others) if others else None
        material = (excess is not None and pre_ttm and abs(excess) >= C["min_share_of_pretax"] * abs(pre_ttm))
        if z is not None and abs(z) > C["robust_z"] and material:
            peaks.append({"quarter": dates[i] if i < len(dates) else None, "nonoperating": x,
                          "typical": _median(others), "gross": excess, "net": excess * (1 - t_eff),
                          "z": z, "tax_rate": t_eff})
    return {"available": True, "reason": None, "peaks": peaks, "tax_rate": t_eff}


def normalize(*, net_income: Optional[float], explicit_rows: Dict[str, Optional[float]],
              quarterly: Optional[Dict[str, Any]], basis: str,
              tax_rate_fallback: Optional[float] = None) -> Dict[str, Any]:
    """Beneficio reportado y normalizado, ítems con tipo/confianza/origen y one_off_pct."""
    C = cfg("thresholds.normalization")
    items: List[Dict[str, Any]] = []
    ex = explicit_items(explicit_rows or {})
    if ex["gross"] not in (None, 0):
        if ex["tax_effect"] is not None:
            net, tax_src = ex["gross"] - ex["tax_effect"], "Tax Effect Of Unusual Items"
        else:
            t = tax_rate_fallback if tax_rate_fallback is not None else C["default_tax_rate"]
            net, tax_src = ex["gross"] * (1 - t), f"tipo efectivo {t:.1%}"
        items.append({"type": "explicita", "confidence": "alta", "origin": f"Yahoo: {ex['level']} ({basis})",
                      "gross": ex["gross"], "net": net, "tax_source": tax_src, "components": ex["components"],
                      "applied": True})
    inferred = infer_peaks(quarterly) if quarterly else {"available": False, "reason": "sin estados trimestrales",
                                                         "peaks": []}
    ni = net_income
    for p in inferred["peaks"]:
        share = abs(p["net"]) / abs(ni) if ni else None
        items.append({"type": "inferida", "confidence": "media",
                      "origin": f"pico de resultado no operativo en el trimestre {p['quarter']} "
                                f"(z robusto {p['z']:.1f}; habitual {p['typical'] / 1e9:+.2f}B frente a "
                                f"{p['nonoperating'] / 1e9:+.2f}B)",
                      "gross": p["gross"], "net": p["net"], "tax_source": f"tipo efectivo TTM {p['tax_rate']:.1%}",
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
