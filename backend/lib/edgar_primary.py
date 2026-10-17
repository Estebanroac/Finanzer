"""
SEC EDGAR como fuente principal, campo a campo (fase 3, T1b; D2).

D2: "EDGAR pasará a fuente principal campo a campo cuando la fase 3 cierre las definiciones". La parada 1 de la fase 3
las cerró (F3_T1_PARADA1 §1; aprobación del usuario en el registro #25 de la bitácora). Aquí manda EDGAR, en el corte
del análisis (`info["_as_of"]`) y en las filas anuales (`info["_statements_fy"]`), para:

  · **EBIT** (todos menos los bancos): el resultado operativo que **presenta el emisor** en su cuenta de resultados
    (`OperatingIncomeLoss`; IFRS `ProfitLossFromOperatingActivities`), no el que construye Yahoo (KO excluye "otros
    cargos operativos"; PLD resta las ganancias de promoción). Solo el resultado operativo (TTM y fila anual
    `operating_income`): la fila anual "EBIT" de Yahoo (resultado antes de intereses e impuestos, con lo no
    operativo) y el EBITDA siguen con su definición, que no se decidió en la parada 1 (el ROCE y el FFO de los REIT
    los usan). En un banco el EBIT no aplica (su equivalente, el beneficio antes de provisiones, es de la T4);
  · **ingresos de aseguradoras y conglomerados**: los ingresos sin las ganancias de inversión (BRK-B: Yahoo suma
    `GainLossOnInvestments` a `Revenues`);
  · **ingresos de bancos de EE. UU.**: los ingresos netos totales (margen de intereses + ingresos no financieros). Los
    bancos IFRS no tienen etiqueta estándar para "total income" (BCS): se quedan con la fuente;
  · **capex de emisores con financiera cautiva** (`data.edgar.captive`): sin el equipo que la cautiva arrienda a
    terceros (`PaymentsToAcquireEquipmentOnLease`), coherente con sacar su deuda de la industrial (2b, T5). El FCF se
    recalcula.

Si EDGAR no tiene el periodo (20-F sin trimestres), el dato de la fuente se queda; el EBIT, marcado "estimado por la
fuente" por `edgar_backup.ebit_check`. Nunca mezcla monedas. Importes convertidos como los de la fuente
(lib/currency: flujos al promedio de los doce meses).
"""
import datetime as _dt
from typing import Any, Dict, List, Optional

from settings import cfg

import sec_edgar as edgar
from edgar_backup import _convert, _statement_currency

NOT_APPLICABLE_BANK_EBIT = "beneficio operativo de un banco: no aplica (su equivalente es el beneficio antes de provisiones)"


def _starts(value: str, prefixes) -> bool:
    return any(value.startswith(p) for p in prefixes)


def _rules(info: Dict[str, Any], facts: Dict[str, Any], symbol: Optional[str]) -> List[Dict[str, Any]]:
    """[(clave del corte, fila anual, campo de EDGAR, motivo)] que manda EDGAR para este emisor; y los que no, con
    su motivo, como {"skip": ...}."""
    sector = str(info.get("sector") or "")
    industry = str(info.get("industry") or "").lower()          # como lib/classify.py
    fin = sector == "Financial Services"
    bank = fin and _starts(industry, cfg("sectors.archetypes.bank_prefixes"))
    insurer = fin and _starts(industry, cfg("sectors.archetypes.insurance_prefixes"))
    out = []
    if bank:
        out.append({"skip": "operatingIncome", "reason": NOT_APPLICABLE_BANK_EBIT})
    else:
        out.append({"key": "operatingIncome", "row": "operating_income", "field": "operating_income",
                    "why": "EBIT que presenta el emisor (F3_T1_PARADA1 §1)"})
    if insurer:
        out.append({"key": "totalRevenue", "row": "revenue", "field": "revenue",
                    "why": "ingresos sin ganancias de inversión (aseguradora o conglomerado)"})
    elif bank and edgar.taxonomy(facts) == "us-gaap":
        out.append({"key": "totalRevenue", "row": "revenue", "field": "revenue",
                    "why": "ingresos netos totales de un banco"})
    if symbol and symbol.upper() in (cfg("data.edgar.captive") or {}):
        out.append({"key": "capitalExpenditures", "row": "capital_expenditure", "field": "capex",
                    "why": "capex sin el equipo que la financiera cautiva arrienda a terceros"})
    return out


def apply(info: Dict[str, Any], ed: Dict[str, Any], ctx=None, symbol: Optional[str] = None) -> Dict[str, Any]:
    """Pone en `info` el valor de EDGAR de los campos en los que manda. Devuelve el registro
    (-> data_provenance.edgar.primary): {cut: [...], fy: [...], skipped: [...], reason}."""
    from yf_adapter import _tag_provenance
    log: Dict[str, Any] = {"cut": [], "fy": [], "skipped": [], "reason": None}
    facts = ed.get("facts")
    if ed.get("status") != "ok" or not facts:
        log["reason"] = ed.get("facts_reason") or ed.get("reason") or "sin hechos de EDGAR"
        return log
    unit = edgar.reporting_unit(facts, edgar.taxonomy(facts))
    stmt_cur = _statement_currency(info)
    if unit is None or (stmt_cur and unit != stmt_cur):
        log["reason"] = f"EDGAR presenta los estados en {unit} y la fuente en {stmt_cur}: no se mezclan"
        return log
    tol = cfg("data.edgar.report_date_tolerance_days")
    rules = _rules(info, facts, symbol or info.get("symbol"))
    for r in rules:
        if "skip" in r:
            log["skipped"].append({"field": r["skip"], "reason": r["reason"]})
    rules = [r for r in rules if "key" in r]
    ao = info.get("_as_of") or {}
    cut = ao.get("date")
    if ao.get("type") in ("ttm", "fy") and cut:
        fields = ao.setdefault("fields", {})
        for r in rules:
            key = r["key"]
            got = edgar.field_value(facts, r["field"], _dt.date.fromisoformat(cut), tol)
            if got is None:
                log["skipped"].append({"field": key, "reason": f"EDGAR no lo tiene del periodo que acaba el {cut}"})
                continue
            old = info.get(key)
            val = _convert(ctx, float(got["value"]), "flow", cut)
            info[key] = val
            fields[key] = {"period_end": cut, "period_type": "ttm" if ao["type"] == "ttm" else "fy",
                           "source": "sec_edgar"}
            _tag_provenance(info, "sec_edgar", f"SEC EDGAR, fuente principal ({got['concept']}): {got['how']} · "
                                               f"{r['why']}", paths=[key], overwrite=True)
            log["cut"].append({"field": key, "concept": got["concept"], "period_end": cut, "how": got["how"],
                               "accns": got["accns"], "value": val, "replaced": old, "why": r["why"]})
            _follow(info, key, old, val, fields, cut, ao["type"])
    else:
        log["reason"] = "sin corte identificable (ruta quoteSummary): manda la fuente"
    _apply_fy(info, facts, rules, ctx, tol, log)
    return log


def _follow(info: Dict[str, Any], key: str, old, val, fields, cut, ptype) -> None:
    """Lo que depende del campo sustituido: el FCF (OCF − capex)."""
    from yf_adapter import _tag_provenance
    if key == "capitalExpenditures" and info.get("operatingCashflow") is not None:
        info["freeCashflow"] = info["operatingCashflow"] + (val if val <= 0 else -val)
        fields["freeCashflow"] = {"period_end": cut, "period_type": "ttm" if ptype == "ttm" else "fy",
                                  "source": "derivado"}
        _tag_provenance(info, "derivado", "flujo de operaciones − capex de SEC EDGAR (sin el equipo arrendado de la "
                                          "cautiva)", paths=["freeCashflow"], overwrite=True)


def _apply_fy(info: Dict[str, Any], facts: Dict[str, Any], rules, ctx, tol: int, log: Dict[str, Any]) -> None:
    """Filas anuales: cada ejercicio que EDGAR tiene entero (nunca un TTM construido) manda."""
    st = info.get("_statements_fy")
    if not isinstance(st, dict):
        return
    stmt_of = {"operating_income": "inc", "revenue": "inc", "capital_expenditure": "cf"}
    for r in rules:
        row = r["row"]
        ends = st.get(f"{stmt_of[row]}_ends") or []
        vals = list(st.get(row) or [])
        if not ends:
            continue
        vals += [None] * (len(ends) - len(vals))
        changed = False
        for i, end in enumerate(ends):
            if not end:
                continue
            got = edgar.field_value(facts, r["field"], _dt.date.fromisoformat(end), tol)
            if got is None or "acumulado" in got["how"]:
                continue
            new = _convert(ctx, float(got["value"]), "flow", end)
            old = vals[i]
            vals[i] = new
            changed = True
            log["fy"].append({"field": f"FY.{row}", "fy_end": end, "concept": got["concept"], "how": got["how"],
                              "accns": got["accns"], "value": new, "replaced": old})
            if row == "capital_expenditure":
                ocf, fcf = st.get("operating_cash_flow") or [], st.get("free_cash_flow")
                if isinstance(fcf, list) and i < len(fcf) and i < len(ocf) and ocf[i] is not None:
                    fcf[i] = ocf[i] + (new if new <= 0 else -new)
        if changed:
            st[row] = vals
