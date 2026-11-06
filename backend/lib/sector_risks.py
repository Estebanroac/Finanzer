"""
F13 · paso 10 (revisión de 110 empresas, decisión del usuario del 5-nov-2026): riesgos del sector en dos niveles,
siempre aparte y sin puntuar.

  · Nivel 1, de la empresa, solo con un dato que lo dispare. Hoy, la refinanciación: la deuda que vence en 24 meses
    (vencimientos del año 1 y 2, papel comercial y préstamos a corto del último balance anual en SEC EDGAR) supera la
    caja y el rating sintético del motor es especulativo. No en financieras, utilities ni REIT, que refinancian así
    por diseño (config sectors.sector_risks).
  · Nivel 2, de la industria: lista cerrada de los que un dato acota dentro de su industria (industria de Yahoo y
    estado de la sede en EDGAR), con la etiqueta «riesgo de la industria, no verificado en esta empresa».

Lo que no se puede medir con datos públicos gratuitos estructurados (concentración en un inquilino o un producto) se
dice y no se estima. Medida previa en las 543: docs/fiabilidad/F13_P10_RIESGOS_MEDIDA.md.
"""
import datetime as _dt
import re
from typing import Any, Dict, List, Optional

import numfmt
import sec_edgar as edgar
from settings import cfg

SOURCE = "SEC EDGAR (companyfacts: vencimientos de la deuda del último balance anual)"
INDUSTRY_LABEL = "riesgo de la industria, no verificado en esta empresa"


def debt_due(facts: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Vencimientos de la deuda al cierre del último ejercicio: {status, fy_end, values, concepts, due_24m}."""
    out: Dict[str, Any] = {"status": "sin_dato", "fy_end": None, "values": {}, "concepts": {}, "due_24m": None,
                           "reason": None, "source": SOURCE}
    if not facts:
        out["reason"] = "el emisor no tiene estados en XBRL en la SEC"
        return out
    tax, end = edgar.taxonomy(facts), edgar.latest_fy_end(facts)
    unit = edgar.reporting_unit(facts, tax)
    if tax != "us-gaap" or end is None or unit is None:
        out["reason"] = "sin balance anual en US GAAP (los vencimientos se leen de conceptos us-gaap)"
        return out
    out["fy_end"] = end
    for key, concept in edgar.MATURITIES.items():
        fs = (facts.get("facts") or {}).get(tax, {}).get(concept, {}).get("units", {}).get(unit) or []
        hits = [f for f in fs if f.get("form") in edgar.ANNUAL_FORMS and f.get("end") == end and not f.get("start")]
        if hits:
            f = max(hits, key=lambda x: (x.get("filed") or "", x.get("accn") or ""))
            out["values"][key], out["concepts"][key] = f["val"], f"{tax}:{concept}"
    v = out["values"]
    if v.get("due_y1") is None or v.get("due_y2") is None:
        out["reason"] = "el emisor no presenta los vencimientos de la deuda del año 1 y 2 con los conceptos estándar"
        return out
    out["due_24m"] = v["due_y1"] + v["due_y2"] + (v.get("commercial_paper") or 0.0) + (v.get("short_term_borrowings") or 0.0)
    out["status"] = "ok"
    return out


def _refinancing(due: Dict[str, Any], archetype: Optional[str], cash: Optional[float], rating: Optional[str],
                 coverage: Optional[float], today: Optional[str]) -> Optional[Dict[str, Any]]:
    C = cfg("sectors.sector_risks")
    if archetype in C["refinancing_excluded_archetypes"] or (due or {}).get("status") != "ok" or not cash or cash <= 0:
        return None
    if today and due.get("fy_end"):
        age = (_dt.date.fromisoformat(today[:10]) - _dt.date.fromisoformat(due["fy_end"][:10])).days
        if age > C["max_balance_age_days"]:
            return None
    if due["due_24m"] <= cash or rating not in C["speculative_ratings"]:
        return None
    v = due["values"]
    parts = [f"{numfmt.money(v['due_y1'])} en 12 meses", f"{numfmt.money(v['due_y2'])} el año siguiente"]
    if v.get("commercial_paper"):
        parts.append(f"{numfmt.money(v['commercial_paper'])} de papel comercial")
    if v.get("short_term_borrowings"):
        parts.append(f"{numfmt.money(v['short_term_borrowings'])} de préstamos a corto")
    cov = f", cobertura de intereses {coverage:.1f}x".replace("-", "−") if coverage is not None else ""
    return {"level": "empresa", "key": "refinanciacion", "title": "Refinanciación en 24 meses",
            "text": (f"Vencen {numfmt.money(due['due_24m'])} de deuda en los próximos 24 meses ({', '.join(parts)}; "
                     f"balance al {numfmt.date_long(due['fy_end'])}) frente a {numfmt.money(cash)} de caja, con un "
                     f"rating sintético {rating}{cov} (grado especulativo): tendrá que refinanciar y puede hacerlo en "
                     "condiciones caras."),
            "source": due["source"], "figures": {"due_24m": due["due_24m"], "cash": cash, "rating": rating}}


def _norm(industry: Optional[str]) -> str:
    """La industria de Yahoo llega con guion o con raya según la vía («Utilities—Diversified», «Utilities - …»)."""
    return re.sub(r"\s*[—–-]\s*", " - ", industry or "").strip().lower()


def _industry(industry: Optional[str], country: Optional[str], state: Optional[str]) -> List[Dict[str, Any]]:
    out = []
    for key, r in (cfg("sectors.sector_risks.industry") or {}).items():
        if (_norm(industry) in {_norm(x) for x in r["industries"]} and country == "United States"
                and state in r["states"]):
            out.append({"level": "industria", "key": key, "title": r["title"], "label": INDUSTRY_LABEL,
                        "text": (r["text"][0].upper() + r["text"][1:] + f". Se le aplica por su sede en "
                                 f"{(cfg('market.us_states') or {}).get(state, state)}; la sede no siempre es el "
                                 "territorio que sirve.")})
    return out


def build(*, archetype: Optional[str], industry: Optional[str], country: Optional[str], state: Optional[str],
          debt: Optional[Dict[str, Any]], cash: Optional[float], rating: Optional[str], coverage: Optional[float],
          today: Optional[str] = None) -> Dict[str, Any]:
    """{company: [...], industry: [...], not_measured, debt_due}: los riesgos del sector de la empresa (no puntúan)."""
    company = [x for x in (_refinancing(debt or {}, archetype, cash, rating, coverage, today),) if x]
    return {"company": company, "industry": _industry(industry, country, state),
            "not_measured": cfg("sectors.sector_risks.not_measured"), "debt_due": debt,
            "note": "Aparte y sin puntuar: ni la calidad ni el precio los cuentan."}
