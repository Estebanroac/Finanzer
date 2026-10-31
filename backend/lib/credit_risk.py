"""
F9 · R6 (revisión externa de NU, 27-oct-2026): el riesgo de crédito de un banco, con fuentes gratuitas.

Del XBRL del último informe anual en SEC EDGAR (companyfacts, US GAAP e IFRS; conceptos en sec_edgar.CREDIT), solo
los totales sin dimensiones:

- **Coste del riesgo** = gasto por pérdidas de crédito del ejercicio ÷ cartera media (la del cierre y la del anterior;
  sin la anterior, la del cierre, y se dice).
- **Provisión sobre cartera** = provisión para pérdidas de crédito ÷ cartera bruta, al cierre.
- **Morosidad a 90 días** (aún devengando) y **cartera en no devengo**, sobre la cartera bruta, si están etiquetadas.
- **Castigos netos** = fallidos menos recuperaciones del ejercicio ÷ cartera media.

En IFRS no hay concepto estándar para la cartera bruta ni para la provisión: la cartera es la neta y la provisión
queda sin dato. Muchos emisores (NU, 20-F) etiquetan su crédito con extensiones propias que la SEC no publica en
companyfacts: entonces el riesgo de crédito queda **no medido**, con su motivo, y el informe lo dice (un banco nunca
muestra «0 riesgos» sin haberlo medido). FDIC BankFind no se usa: mide cada banco de la licencia, no el grupo cotizado,
y para los grupos de EE. UU. el 10-K ya trae los totales.

measure(facts) -> {status: medido | no_medido, fy_end, taxonomy, loans_basis, cost_of_risk, allowance_ratio,
past_due_90_ratio, nonaccrual_ratio, net_charge_off_ratio, values, concepts, reason, source}
"""
from typing import Any, Dict, List, Optional

import sec_edgar as edgar

SOURCE = "SEC EDGAR (XBRL del informe anual: totales sin dimensiones)"
# Qué cubre el gasto, por el concepto del que sale (el informe lo nombra así).
EXPENSE_SCOPE = {
    "ProvisionForLoanLeaseAndOtherLosses": "provisión para pérdidas de préstamos y otras exposiciones",
    "AdjustmentsForImpairmentLossesReversalOfImpairmentLossesRecognisedInProfitOrLossFinancialAssets":
        "deterioro de los activos financieros (no solo de los préstamos)",
}
EXPENSE_LOANS = "gasto por pérdidas de crédito de la cartera de préstamos"
NOT_MEASURED = ("riesgo de crédito no medido: el XBRL del emisor en la SEC no trae {what} con conceptos estándar "
                "(muchos bancos los etiquetan con extensiones propias, que la SEC no publica)")


def _at(facts: Dict[str, Any], field: str, end: str) -> Optional[Dict[str, Any]]:
    """El valor del campo al cierre `end` (stock) o del ejercicio que acaba en `end` (flow), del primer concepto de
    sec_edgar.CREDIT que lo tenga; el filing más reciente si hay reexpresiones."""
    tax = edgar.taxonomy(facts)
    unit = edgar.reporting_unit(facts, tax)
    if tax is None or unit is None:
        return None
    kind, us, ifrs = edgar.CREDIT[field]
    for c in (us if tax == "us-gaap" else ifrs):
        fs = (facts.get("facts") or {}).get(tax, {}).get(c, {}).get("units", {}).get(unit) or []
        hits = [f for f in fs if f.get("form") in edgar.ANNUAL_FORMS and f.get("end") == end
                and (kind == "stock" or 350 <= (edgar._days(f) or 0) <= 380)]
        if hits:
            f = max(hits, key=lambda x: (x.get("filed") or "", x.get("accn") or ""))
            return {"value": f["val"], "concept": f"{tax}:{c}"}
    return None


def _prior_end(facts: Dict[str, Any], end: str) -> Optional[str]:
    """El cierre del ejercicio anterior con cartera (entre 350 y 380 días antes)."""
    tax = edgar.taxonomy(facts)
    unit = edgar.reporting_unit(facts, tax)
    _k, us, ifrs = edgar.CREDIT["loans"]
    ends: List[str] = []
    for c in (us if tax == "us-gaap" else ifrs):
        ends += [f["end"] for f in (facts.get("facts") or {}).get(tax, {}).get(c, {}).get("units", {}).get(unit) or []
                 if f.get("form") in edgar.ANNUAL_FORMS and f.get("end", "") < end]
    for e in sorted(set(ends), reverse=True):
        d = (edgar._date(end) - edgar._date(e)).days
        if 350 <= d <= 380:
            return e
    return None


def measure(facts: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    out: Dict[str, Any] = {"status": "no_medido", "fy_end": None, "taxonomy": None, "loans_basis": None,
                           "cost_of_risk": None, "allowance_ratio": None, "past_due_90_ratio": None,
                           "nonaccrual_ratio": None, "net_charge_off_ratio": None, "average_loans": False,
                           "values": {}, "concepts": {}, "reason": None, "source": SOURCE}
    if not facts:
        out["reason"] = "riesgo de crédito no medido: el emisor no tiene estados en XBRL en la SEC"
        return out
    end = edgar.latest_fy_end(facts)
    tax = edgar.taxonomy(facts)
    out.update(fy_end=end, taxonomy=tax)
    if end is None:
        out["reason"] = "riesgo de crédito no medido: sin un ejercicio cerrado en el XBRL del emisor"
        return out
    got = {k: _at(facts, k, end) for k in edgar.CREDIT}
    out["values"] = {k: (v or {}).get("value") for k, v in got.items()}
    out["concepts"] = {k: v["concept"] for k, v in got.items() if v}
    loans, exp = out["values"]["loans"], out["values"]["credit_loss_expense"]
    if not loans or loans <= 0 or exp is None:
        missing = " ni ".join(w for w, ok in (("la cartera de préstamos", bool(loans and loans > 0)),
                                              ("el gasto por pérdidas de crédito del ejercicio", exp is not None))
                              if not ok)
        out["reason"] = NOT_MEASURED.format(what=missing)
        return out
    out["loans_basis"] = "bruta" if tax == "us-gaap" else "neta de provisiones (IFRS)"
    out["expense_scope"] = EXPENSE_SCOPE.get(got["credit_loss_expense"]["concept"].split(":", 1)[1], EXPENSE_LOANS)
    prev = _prior_end(facts, end)
    prev_loans = (_at(facts, "loans", prev) or {}).get("value") if prev else None
    avg = (loans + prev_loans) / 2 if prev_loans and prev_loans > 0 else loans
    out["average_loans"] = bool(prev_loans and prev_loans > 0)
    v = out["values"]
    out.update(status="medido", cost_of_risk=exp / avg,
               allowance_ratio=(v["allowance"] / loans) if v["allowance"] is not None else None,
               past_due_90_ratio=(v["past_due_90"] / loans) if v["past_due_90"] is not None else None,
               nonaccrual_ratio=(v["nonaccrual"] / loans) if v["nonaccrual"] is not None else None,
               net_charge_off_ratio=(v["net_charge_offs"] / avg) if v["net_charge_offs"] is not None else None)
    return out
