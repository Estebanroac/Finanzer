"""
Deuda coherente con el EBITDA (fase 2b, T5; F2_PRECEDENCIA §2.3).

Regla: un arrendamiento entra en la deuda si y solo si su coste no está restado del EBITDA.
  · IFRS 16 (todos) y US GAAP financiero: amortización + intereses, por debajo del EBITDA → en la deuda;
  · US GAAP operativo: alquiler lineal dentro de los gastos operativos (ya restado del EBITDA) → fuera.

La deuda de la regla alimenta todo lo que lee `info["totalDebt"]`: deuda neta, deuda neta / EBITDA, EV, D/E, WACC,
ROIC y el puente del DCF. En el Altman (X4) de un emisor US GAAP el pasivo operativo por arrendamiento sale del pasivo
(su alquiler ya está en el EBIT de X3): `info["_statements_fy"]["operating_lease_liabilities"]`, que lee main.

Fuentes (D2: Yahoo principal; EDGAR para lo que Yahoo no da):
  · préstamos y bonos (con el papel comercial): la deuda total de Yahoo menos su fila "Capital Lease Obligations",
    que en EE. UU. es el arrendamiento operativo y a veces el financiero (MSFT 16,532 millones = su pasivo operativo
    no corriente; MU 3,324 = financiero 2,670 + operativo no corriente 654). O, verificado en su 10-Q del 2T-2026:
    notas 25,092 + préstamos 2,760 + línea de crédito y papel comercial 2,763 + hipotecas 37 = 30,652 = Yahoo;
  · arrendamiento financiero y operativo: EDGAR, saldo del corte o, si el emisor solo los etiqueta en el 10-K (DUK),
    el del último informe anual con aviso de fecha;
  · emisor IFRS: la deuda total de Yahoo ya lleva los arrendamientos (UL, SHEL): es la de la regla;
  · sin EDGAR (sin User-Agent, emisor sin estados en la SEC o sin corte): la deuda de la fuente, con nota.

Componentes solo declarados (sin efecto en las ratios en la 2b): deuda subordinada (en un banco, toda su deuda queda
fuera de las ratios de apalancamiento de empresa: lo hace main) y deuda de la financiera cautiva (CAT; usarla en la
valoración es de la fase 3).
"""
import datetime as _dt
from typing import Any, Dict, Optional

from settings import cfg

import sec_edgar as edgar


def _conv(ctx, value: Optional[float], end: Optional[str]) -> Optional[float]:
    if value is None or ctx is None or not getattr(ctx, "convert_currency", False):
        return value
    return ctx.convert_amount(value, "balance", end=end)


def apply(info: Dict[str, Any], ed: Dict[str, Any], ctx=None) -> Dict[str, Any]:
    """Deuda de la regla en info["totalDebt"] y sus componentes en el registro (-> data_provenance.debt)."""
    from yf_adapter import _tag_provenance
    total = info.get("totalDebt")
    ao = info.get("_as_of") or {}
    fields = ao.get("fields") or {}
    at = (fields.get("totalDebt") or {}).get("period_end") or ao.get("date")
    out: Dict[str, Any] = {"rule": "un arrendamiento entra en la deuda si y solo si su coste no está restado del EBITDA",
                           "source_total": total, "date": at, "standard": None, "total": total, "applied": False,
                           "components": {}, "notes": []}
    comps = out["components"]
    if info.get("commercialPaper") is not None:
        comps["commercial_paper"] = {"value": info["commercialPaper"], "source": "Yahoo", "in_rule_debt": True}
    facts = ed.get("facts") if ed.get("status") == "ok" else None
    tax = edgar.taxonomy(facts) if facts else None
    out["standard"] = tax
    cap = ed.get("captive") or {}
    if cap.get("status") == "ok":
        comps["captive"] = {"value": _conv(ctx, cap["value"], cap["date"]), "name": cap["name"], "date": cap["date"],
                            "source": f"SEC EDGAR ({cap['form']} {cap['accn']}, segmento {cap['name']})",
                            "parts": cap["parts"], "in_rule_debt": True,
                            "note": "deuda de la financiera cautiva: solo se separa y se declara (su uso en la "
                                    "valoración es de la fase 3)"}
    elif cap:
        out["notes"].append(f"deuda de la financiera cautiva sin dato: {cap.get('reason')}")
    if total is None or not at:
        out["notes"].append("sin deuda total de la fuente con fecha: no se aplica la regla")
        return out
    if facts is None or tax is None:
        out["notes"].append("sin desglose oficial de arrendamientos (EDGAR no disponible para este emisor): deuda "
                            "de la fuente")
        return out
    unit = edgar.reporting_unit(facts, tax)
    stmt_cur = (info.get("_currency") or {}).get("statements") or info.get("financialCurrency") or info.get("currency")
    if stmt_cur and unit != stmt_cur:
        out["notes"].append(f"EDGAR presenta en {unit} y Yahoo en {stmt_cur}: deuda de la fuente")
        return out
    tol = cfg("data.edgar.report_date_tolerance_days")
    day = _dt.date.fromisoformat(at)

    def part(name):
        r = edgar.debt_part(facts, name, day, tol, latest_before=True)
        if r is None:
            return None
        r = dict(r)
        r["value"] = _conv(ctx, r["value"], r["period"])
        if r["basis"] == "ultimo_anual":
            r["note"] = f"del último informe anual ({r['period']}): el emisor no lo etiqueta en el filing del corte"
        return r
    sub = part("subordinated")
    if sub:
        comps["subordinated"] = {**sub, "source": "SEC EDGAR", "in_rule_debt": True,
                                 "note": "en un banco, fuera de las ratios de apalancamiento de empresa (fase 3)"}
    if tax == "ifrs-full":
        leases = part("leases")
        if leases:
            comps["leases_ifrs16"] = {**leases, "source": "SEC EDGAR", "in_rule_debt": True}
        out["notes"].append("IFRS 16: los arrendamientos ya están en la deuda de la fuente (regla cumplida)")
        return out
    # US GAAP
    clo = info.get("capitalLeaseObligations")
    clo_end = (fields.get("capitalLeaseObligations") or {}).get("period_end")
    if clo is not None and clo_end not in (None, at):
        out["notes"].append(f"la fila de arrendamientos de Yahoo es de otro periodo ({clo_end}): el balance del corte no "
                            "la trae y la deuda total no la incluye")
        clo = None
    ol, fl = part("operating_leases"), part("finance_leases")
    in_lines = edgar.debt_part(facts, "debt_with_finance_leases", day, tol) is not None   # balance del corte
    # La fila de arrendamientos de Yahoo: la parte que cabe en el operativo de EDGAR es operativa; el resto, financiero
    # (MSFT: 16,532 = su operativo no corriente; MU: 3,324 = operativo 654 + financiero 2,670). Sin el operativo de
    # EDGAR, toda la fila se toma como operativa (el caso dominante en EE. UU.).
    ol_in = min(clo or 0.0, ol["value"]) if ol else (clo or 0.0)
    fl_in_row = (clo or 0.0) - ol_in
    # El financiero entra si no está ya ni en esa fila ni en las líneas de deuda del emisor (XOM presenta
    # LongTermDebtAndCapitalLeaseObligations: Yahoo ya lo suma).
    fl_missing = 0.0 if (not fl or in_lines) else max(0.0, fl["value"] - fl_in_row)
    borrowings = total - (clo or 0.0)
    comps["borrowings"] = {"value": borrowings, "source": "Yahoo (deuda total − su fila de arrendamientos)",
                           "in_rule_debt": True}
    if clo:
        comps["leases_in_source_total"] = {"value": clo, "source": "Yahoo (Capital Lease Obligations)",
                                           "in_rule_debt": False, "operating": ol_in, "finance": fl_in_row}
    if ol:
        comps["operating_leases"] = {**ol, "source": "SEC EDGAR", "in_rule_debt": False,
                                     "note": "US GAAP: su alquiler ya está restado del EBITDA"}
    if fl:
        note = ("ya dentro de la deuda que presenta el emisor" if in_lines and not fl_in_row else
                "en parte en la fila de arrendamientos de la fuente" if fl_in_row and fl_missing else
                "ya en la fila de arrendamientos de la fuente" if fl_in_row else None)
        comps["finance_leases"] = {**fl, "source": "SEC EDGAR", "in_rule_debt": True, "added": fl_missing,
                                   **({"note": " · ".join(x for x in (fl.get("note"), note) if x)}
                                      if (note or fl.get("note")) else {})}
    rule = total - ol_in + fl_missing
    out.update(total=rule, applied=True)
    info["totalDebt"] = rule
    _tag_provenance(info, "derivado",
                    "deuda coherente con el EBITDA: préstamos y bonos (Yahoo, sin sus arrendamientos) + arrendamiento "
                    "financiero (SEC EDGAR); el operativo queda fuera (US GAAP, su alquiler ya está en el EBITDA)",
                    paths=["totalDebt"], overwrite=True)
    # Fase 3 (T6, F3_DISENO §8.6): la deuda de la financiera cautiva (CAT) financia su cartera de préstamos y
    # arrendamientos a clientes, no la actividad industrial: queda fuera de la deuda neta del DCF y de las ratios de
    # apalancamiento (la práctica de las propias empresas: CAT presenta "ME&T" sin Financial Products). Solo con el
    # dato de la cautiva del mismo corte.
    capc = comps.get("captive")
    if capc and capc.get("value") and abs((_dt.date.fromisoformat(capc["date"]) - day).days) <= tol:
        industrial = rule - capc["value"]
        capc["in_rule_debt"] = False
        capc["note"] = ("deuda de la financiera cautiva: fuera de la deuda industrial (deuda neta del DCF y ratios "
                        "de apalancamiento; F3_DISENO §8.6). Su cartera de clientes, que la respalda, tampoco se valora "
                        "en el DCF industrial")
        out.update(total=industrial, total_with_captive=rule, captive_excluded=capc["value"])
        info["totalDebt"] = industrial
        _tag_provenance(info, "derivado",
                        "deuda industrial: la deuda coherente con el EBITDA sin la de la financiera cautiva "
                        f"({capc['name']}, SEC EDGAR)", paths=["totalDebt"], overwrite=True)
    elif capc:
        out["notes"].append(f"deuda de la financiera cautiva de otro corte ({capc['date']} frente a {at}): no se separa")
    _operating_leases_fy(info, facts, ctx, tol)
    return out


def _operating_leases_fy(info: Dict[str, Any], facts: Dict[str, Any], ctx, tol: int) -> None:
    """Pasivo operativo por arrendamiento al cierre de cada ejercicio (Altman X4 en US GAAP)."""
    st = info.get("_statements_fy")
    if not isinstance(st, dict):
        return
    vals = []
    for end in st.get("bs_ends") or []:
        r = edgar.debt_part(facts, "operating_leases", _dt.date.fromisoformat(end), tol)
        vals.append(_conv(ctx, r["value"], end) if r else None)
    st["operating_lease_liabilities"] = vals
