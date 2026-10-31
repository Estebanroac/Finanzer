"""Rediseño E2a: historia de los últimos ejercicios (10 por defecto) desde la historia anual de EDGAR que ya trae el
análisis (sec_edgar.history → yinfo["_history_fy"]). Función pura, sin red. En la moneda de los estados (la unidad de
EDGAR), sin convertir: la ficha dice la moneda."""
import datetime as _dt
from typing import Any, Dict, List, Optional

from settings import cfg

SOURCE = "SEC EDGAR (companyfacts: ejercicios completos de los informes anuales)"
_FIELDS = ("revenue", "operating_income", "net_income", "diluted_eps", "operating_cash_flow", "capex")


def _by_end(history_fy: Dict[str, Any], field: str) -> Dict[str, float]:
    return {v["fy_end"]: v["value"] for v in ((history_fy.get(field) or {}).get("values") or [])
            if v.get("value") is not None}


def _ratio(a: Optional[float], b: Optional[float]) -> Optional[float]:
    return a / b if a is not None and b is not None and b > 0 else None


def _fiscal_year(fy_end: str) -> int:
    """V4b: el año del ejercicio. Uno de 52/53 semanas que cierra en los primeros días de enero (JNJ: 1-ene-2023) es el
    del año anterior; con el año de la fecha de cierre, la ficha repetía un año y se saltaba otro."""
    d = _dt.date.fromisoformat(fy_end)
    return d.year - 1 if d.month == 1 and d.day <= cfg("market.history.fy_year_shift_days") else d.year


def build(history_fy: Optional[Dict[str, Any]], years: int, missing_reason: Optional[str] = None) -> Dict[str, Any]:
    cols = {f: _by_end(history_fy or {}, f) for f in _FIELDS}
    ends = sorted(set(cols["revenue"]) | set(cols["net_income"]) | set(cols["operating_cash_flow"]))
    if not ends:
        return {"status": "sin_dato", "currency": None, "source": SOURCE, "rows": [],
                "reason": missing_reason or "EDGAR no trae la historia anual del emisor"}
    rows: List[Dict[str, Any]] = []
    tol = cfg("market.history.fy_gap_tolerance_days")
    for i, e in enumerate(ends):
        rev, ocf, capex = cols["revenue"].get(e), cols["operating_cash_flow"].get(e), cols["capex"].get(e)
        # El ejercicio anterior de la lista solo cuenta si cierra a un año (± `fy_gap_tolerance_days`): si EDGAR no trae
        # un ejercicio, el crecimiento no se mide contra dos años atrás como si fuera anual (la fila lo marca).
        gap = bool(i) and abs((_dt.date.fromisoformat(e) - _dt.date.fromisoformat(ends[i - 1])).days - 365) > tol
        prev_rev = cols["revenue"].get(ends[i - 1]) if i and not gap else None
        rows.append({"year": _fiscal_year(e), "fy_end": e, "revenue": rev,
                     "operating_income": cols["operating_income"].get(e), "net_income": cols["net_income"].get(e),
                     "diluted_eps": cols["diluted_eps"].get(e), "operating_cash_flow": ocf, "capex": capex,
                     "free_cash_flow": ocf - abs(capex) if ocf is not None and capex is not None else None,
                     "operating_margin": _ratio(cols["operating_income"].get(e), rev),
                     "net_margin": _ratio(cols["net_income"].get(e), rev),
                     "revenue_growth": (rev / prev_rev - 1) if rev is not None and prev_rev and prev_rev > 0 else None,
                     "gap_before": gap})
    rows = rows[-years:]
    return {"status": "ok", "currency": (history_fy.get("revenue") or history_fy.get("net_income") or {}).get("unit"),
            "source": SOURCE, "rows": rows,
            "reason": None if len(rows) >= years else f"EDGAR trae {len(rows)} ejercicios",
            "field_reasons": field_reasons(history_fy, rows), "relays": relays(history_fy)}


_WHAT = {"revenue": "los ingresos", "operating_income": "el resultado operativo", "diluted_eps": "el BPA diluido", "capex": "el capex",
         "net_income": "el beneficio neto", "operating_cash_flow": "el flujo operativo"}


def field_reasons(history_fy: Optional[Dict[str, Any]], rows: List[Dict[str, Any]]) -> Dict[str, str]:
    """F8: por qué falta un campo en todos los ejercicios de la ventana (la causa; la ficha antepone «EDGAR no trae…»):
    el emisor no lo presenta con un concepto
    estándar (lib/sec_edgar.HISTORY_MISSING), solo hasta un ejercicio anterior, o la otra taxonomía no coincide tras el
    cambio de norma. Sin dato, no se completa con otra fuente."""
    out: Dict[str, str] = {}
    for f, what in _WHAT.items():
        if not rows or any(r.get(f) is not None for r in rows):
            continue
        h = (history_fy or {}).get(f) or {}
        vals = [v["fy_end"] for v in h.get("values") or []]
        if h.get("reason"):
            out[f] = h["reason"]
        elif vals:
            out[f] = (f"el emisor solo lo presentó con el concepto XBRL estándar hasta el ejercicio "
                      f"{_fiscal_year(max(vals))}")
        else:
            out[f] = "el emisor no lo presenta con un concepto XBRL estándar"
    for f in ("operating_cash_flow", "net_income", "operating_income"):
        rej = ((history_fy or {}).get(f) or {}).get("cross_taxonomy_rejected")
        if rej and any(r.get(f) is None for r in rows) and f not in out:
            out[f] = (f"antes del cambio de norma no se toma de la otra taxonomía: en el ejercicio "
                      f"{_fiscal_year(rej['fy_end'])}, que presentan las dos, no coincide")
    return out


def relays(history_fy: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """F8: los conceptos de relevo y los ejercicios de la otra taxonomía que completan la historia (declarados)."""
    out = []
    for f, h in (history_fy or {}).items():
        for r in (h or {}).get("relay") or []:
            out.append({"field": f, **r})
        ct = (h or {}).get("cross_taxonomy")
        if ct and f in _WHAT:
            out.append({"field": f, "concept": ct["taxonomy"], "years": ct["years"], "last": ct["until"],
                        "how": ("ejercicios anteriores al cambio de norma desde la otra taxonomía"
                                + (f", que coincide en el ejercicio {_fiscal_year(ct['verified_on'])}"
                                   if ct.get("verified_on") else ""))})
    return out
