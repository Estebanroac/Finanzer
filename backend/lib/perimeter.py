"""
Cambio de perímetro declarado en los datos (fase 2b, T7): operaciones discontinuadas y ejercicios reexpresados.

UL (escisión de Magnum, 2025-12): el 20-F de 2026 reexpresa los ingresos de 2024 (60,761 → 52,479 millones de EUR) y
2023 (59,604 → 51,680) sin el negocio de helados, y lo presenta como operación discontinuada (3,798 en 2025, con la
escisión). Yahoo da los tres últimos ejercicios en el perímetro nuevo y el cuarto (2022: 60,073) en el anterior: el
CAGR a 3 años cruza el cambio. Aquí solo se detecta y se declara (data_provenance.perimeter); corregir el
crecimiento y el DCF con ello es de la fase 3.

Fuentes: las discontinuadas, de la fila anual de Yahoo ("Net Income Discontinuous Operations"); la reexpresión, de
EDGAR (los ingresos anuales del concepto preferido que cambian entre dos informes anuales más de `restated_rel_tol`)
y, con ella, en qué perímetro está cada ejercicio de la serie de Yahoo (el valor de EDGAR con el que casa). Solo
los ejercicios que usa el análisis (fase 3, T1b: con la historia larga de EDGAR, una reexpresión antigua no cuenta).
"""
import datetime as _dt
from typing import Any, Dict, List, Optional

import sec_edgar as edgar

_RESTATED_REL_TOL = 0.01      # una reexpresión de los ingresos de más de un 1% (por debajo, redondeos y tipos)
_MATCH_REL_TOL = 0.01         # casar un ejercicio de Yahoo con un valor de EDGAR
_CAGR_YEARS = 3               # el CAGR que puntúa: FY0 frente a FY3


def _annual_revenue(facts: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """{concepto, periodos: {(inicio, fin): [hechos de informes anuales]}} del concepto preferido de ingresos."""
    cands = edgar.candidates(facts, "revenue")
    if not cands:
        return None
    concept, fs = cands[0]
    by: Dict[tuple, List[Dict[str, Any]]] = {}
    for f in fs:
        if f.get("form") in edgar.ANNUAL_FORMS and f.get("start") and 350 <= (edgar._days(f) or 0) <= 380:
            by.setdefault((f["start"], f["end"]), []).append(f)
    return {"concept": concept, "periods": by}


def detect(info: Dict[str, Any], ed: Dict[str, Any], ctx=None, tol_days: int = 0) -> Dict[str, Any]:
    st = info.get("_statements_fy") or {}
    out: Dict[str, Any] = {"changed": False, "discontinued": [], "restated": [], "series": [], "mixed_cagr": False,
                           "note": None}
    for end, v in zip(st.get("inc_ends") or [], st.get("net_income_discontinued") or []):
        if v:
            out["discontinued"].append({"fy_end": end, "net_income": v, "source": "Yahoo"})
    facts = ed.get("facts") if ed.get("status") == "ok" else None
    rev = _annual_revenue(facts) if facts else None
    if rev:
        unit = edgar.reporting_unit(facts, edgar.taxonomy(facts))
        stmt_cur = (info.get("_currency") or {}).get("statements") or info.get("financialCurrency")
        conv = (lambda v, end: ctx.convert_amount(v, "flow", end=end)) \
            if (ctx is not None and getattr(ctx, "convert_currency", False)) else (lambda v, end: v)
        comparable = not (stmt_cur and unit != stmt_cur)
        # Solo los ejercicios que usa el análisis (la serie anual de Yahoo; sin ella, los `_CAGR_YEARS + 1` últimos
        # de EDGAR): companyfacts trae desde 2007 y una reexpresión de 2015 no cambia el perímetro de la serie que
        # usa el motor (fase 3, T1b).
        ends = [e for e in (st.get("inc_ends") or []) if e]
        oldest = (_dt.date.fromisoformat(min(ends)) - _dt.timedelta(days=tol_days)).isoformat() if ends else \
            (sorted({e for (_s, e) in rev["periods"]}, reverse=True)[:_CAGR_YEARS + 1] or [""])[-1]
        for (start, end), group in sorted(rev["periods"].items()):
            if end < oldest:
                continue
            vals = sorted({(f.get("filed") or "", f["val"], f["accn"]) for f in group})
            old, new = vals[0], vals[-1]
            if old[1] and abs(new[1] / old[1] - 1.0) > _RESTATED_REL_TOL:
                out["restated"].append({"fy_end": end, "concept": rev["concept"], "unit": unit, "previous": old[1],
                                        "previous_accn": old[2], "current": new[1], "current_accn": new[2],
                                        "change": new[1] / old[1] - 1.0})
        restated = {r["fy_end"]: r for r in out["restated"]}
        for end, y in zip(st.get("inc_ends") or [], st.get("revenue") or []):
            if y is None or not end or not comparable:
                continue
            day = _dt.date.fromisoformat(end)
            group = next((g for (s, e), g in rev["periods"].items()
                          if abs((_dt.date.fromisoformat(e) - day).days) <= tol_days), None)
            if not group:
                continue
            cur = max(group, key=lambda f: (f.get("filed") or "", f["accn"]))
            matches_cur = abs(conv(cur["val"], end) / y - 1.0) <= _MATCH_REL_TOL
            basis = "vigente" if matches_cur else (
                "perimetro_anterior" if any(abs(conv(f["val"], end) / y - 1.0) <= _MATCH_REL_TOL for f in group)
                else "sin_casar")
            out["series"].append({"fy_end": end, "basis": basis, "restated": cur["end"] in restated})
        # Perímetro anterior: un ejercicio que casa con un valor sustituido, o anterior a los reexpresados y que EDGAR
        # ya no presenta en el informe vigente (UL 2022: el 20-F de 2026 trae 2023–2025).
        if out["restated"]:
            first_restated = min(restated)
            for s in out["series"]:
                if s["basis"] == "vigente" and s["fy_end"] < first_restated and not s["restated"]:
                    latest = max(f.get("filed") or "" for g in rev["periods"].values() for f in g)
                    cur_years = {e for (b, e), g in rev["periods"].items()
                                 if any((f.get("filed") or "") == latest for f in g)}
                    if s["fy_end"] not in cur_years:
                        s["basis"] = "perimetro_anterior"
    window = out["series"][:_CAGR_YEARS + 1]
    out["mixed_cagr"] = len({s["basis"] for s in window if s["basis"] != "sin_casar"}) > 1
    out["changed"] = bool(out["restated"] or out["discontinued"])
    if out["changed"]:
        bits = []
        if out["restated"]:
            bits.append("ejercicios reexpresados " + ", ".join(r["fy_end"][:4] for r in out["restated"]))
        if out["discontinued"]:
            bits.append("operaciones discontinuadas en " + ", ".join(d["fy_end"][:4] for d in out["discontinued"]))
        out["note"] = ("estados reexpresados o con cambio de perímetro: " + "; ".join(bits)
                       + ("; el CAGR a 3 años de los ingresos mezcla las dos bases" if out["mixed_cagr"] else "")
                       + " (su corrección en el crecimiento y el DCF es de la fase 3)")
    return out
