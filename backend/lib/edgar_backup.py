"""
Respaldo de SEC EDGAR del mismo corte y fuente oficial del emisor (fase 2b, T4).

D2 manda: Yahoo es la fuente principal de los estados; EDGAR solo entra para lo que Yahoo no da **del mismo corte**
(F2_PRECEDENCIA §2.1, escenario B con respaldo). Dos sitios:

  · el corte del análisis (`info["_as_of"]`): un campo de los estados que falta o que es de otro periodo (lo que la
    regla `periodo_incoherente` de validate descartaría) toma el valor de EDGAR de ese corte: un flujo, los doce meses
    que acaban en él (el ejercicio, o el ejercicio anterior + el acumulado del año − el acumulado del año anterior);
    un saldo, el de esa fecha. Queda con `source = "sec_edgar"` en data_provenance y su periodo en `as_of`;
  · las filas anuales (`info["_statements_fy"]`, las del Altman, el Piotroski y los CAGR): un ejercicio sin dato
    toma el de EDGAR que acaba en la misma fecha.

Nunca sustituye un dato de Yahoo del mismo periodo. Lo que no respalda, con su motivo: el beneficio operativo de un
banco y el capex de un REIT (definiciones de la fase 3, D2), la deuda (T5) y lo que EDGAR no tenga de ese periodo.

Importes en la moneda de los estados de EDGAR; si la cotización va en otra, se convierten como los de Yahoo
(lib/currency: saldo al cierre de la fecha, flujos al promedio de los doce meses).

`official_source` resume D7 (F2_PRECEDENCIA §4): emisor con estados en la SEC, sin ellos (aviso y techo de confianza
"baja") o sin verificación disponible (sin User-Agent o con EDGAR caído: nota, sin techo).
"""
import datetime as _dt
from typing import Any, Dict, List, Optional

from settings import cfg

import sec_edgar as edgar

# Campo del corte (info) -> campo de EDGAR (sec_edgar.CONCEPTS)
CUT_FIELDS = {
    "totalRevenue": "revenue", "grossProfits": "gross_profit", "operatingIncome": "operating_income",
    "netIncome": "net_income", "interestExpense": "interest_expense", "depreciation": "depreciation",
    "operatingCashflow": "operating_cash_flow", "capitalExpenditures": "capex", "dividendsPaid": "dividends_paid",
    "totalAssets": "total_assets", "totalCurrentAssets": "current_assets",
    "totalCurrentLiabilities": "current_liabilities", "totalLiab": "total_liabilities",
    "retainedEarnings": "retained_earnings", "inventory": "inventories", "totalStockholderEquity": "equity_parent",
}
# Fila anual (info["_statements_fy"]) -> (estado de Yahoo de sus fechas, campo de EDGAR)
FY_ROWS = {
    "revenue": ("inc", "revenue"), "gross_profit": ("inc", "gross_profit"),
    "operating_income": ("inc", "operating_income"), "net_income": ("inc", "net_income"),
    "total_assets": ("bs", "total_assets"), "current_assets": ("bs", "current_assets"),
    "current_liabilities": ("bs", "current_liabilities"), "total_liabilities": ("bs", "total_liabilities"),
    "stockholders_equity": ("bs", "equity_parent"), "retained_earnings": ("bs", "retained_earnings"),
    "operating_cash_flow": ("cf", "operating_cash_flow"), "capital_expenditure": ("cf", "capex"),
    "depreciation_amortization": ("cf", "depreciation"),
}
OFFICIAL_SOURCE_NOTICE = ("Sin fuente oficial para verificar: el emisor no presenta estados en la SEC (EDGAR). Las "
                          "cifras son de proveedores de datos y no se han contrastado.")
UNAVAILABLE_NOTE = "verificación oficial no disponible"


def _excluded(field: str, info: Dict[str, Any]) -> Optional[str]:
    """Campos cuya definición está pendiente (D2: "EDGAR pasará a fuente principal campo a campo cuando la fase 3
    cierre las definiciones (deuda, capex, EBIT bancario)")."""
    sector = str(info.get("sector") or "")
    industry = str(info.get("industry") or "").lower()       # como lib/classify.py
    if field == "operating_income" and sector == "Financial Services" and any(
            industry.startswith(p) for p in cfg("sectors.archetypes.bank_prefixes")):
        return "beneficio operativo de un banco: definición del EBIT bancario pendiente (fase 3)"
    if field == "capex" and sector == "Real Estate":
        return "capex de un REIT (mejoras frente a adquisiciones): definición pendiente (fase 3)"
    return None


def _convert(ctx, value: float, kind: str, end: str) -> float:
    if ctx is None or not getattr(ctx, "convert_currency", False):
        return value
    return ctx.convert_amount(value, "balance" if kind == "stock" else "flow", end=end)


def _statement_currency(info: Dict[str, Any]) -> Optional[str]:
    cur = info.get("_currency") or {}
    return cur.get("statements") or info.get("financialCurrency") or info.get("currency")


def apply(info: Dict[str, Any], ed: Dict[str, Any], ctx=None) -> Dict[str, Any]:
    """Respalda en `info` lo que Yahoo no da del mismo corte. Devuelve el registro (-> data_provenance.edgar.backup):
    {cut: [...], fy: [...], skipped: [...], reason}."""
    from yf_adapter import _tag_provenance
    log: Dict[str, Any] = {"cut": [], "fy": [], "skipped": [], "reason": None}
    facts = ed.get("facts")
    if ed.get("status") != "ok" or not facts:
        log["reason"] = ed.get("facts_reason") or ed.get("reason") or "sin hechos de EDGAR"
        return log
    unit = edgar.reporting_unit(facts, edgar.taxonomy(facts))
    stmt_cur = _statement_currency(info)
    if unit is None or (stmt_cur and unit != stmt_cur):
        log["reason"] = f"EDGAR presenta los estados en {unit} y Yahoo en {stmt_cur}: no se mezclan"
        return log
    tol = cfg("data.edgar.report_date_tolerance_days")
    ao = info.get("_as_of") or {}
    fields = ao.setdefault("fields", {})
    cut = ao.get("date")
    if ao.get("type") in ("ttm", "fy") and cut:
        fy_dates = info.get("_fy_dates") or {}
        for key, field in CUT_FIELDS.items():
            kind = edgar.CONCEPTS[field][0]
            at = cut if (ao["type"] == "ttm" or kind == "flow") else (fy_dates.get("bs") or cut)
            have = fields.get(key) or {}
            if info.get(key) is not None and have.get("period_end") in (None, at):
                continue            # Yahoo lo da del mismo corte (o de periodo desconocido: ruta quoteSummary)
            why = _excluded(field, info)
            if why:
                log["skipped"].append({"field": key, "reason": why})
                continue
            r = edgar.field_value(facts, field, _dt.date.fromisoformat(at), tol)
            if r is None:
                if info.get(key) is None or have.get("period_end") not in (None, at):
                    log["skipped"].append({"field": key, "reason": f"EDGAR no lo tiene del periodo que acaba el {at}"})
                continue
            val = _convert(ctx, float(r["value"]), kind, at)
            info[key] = val
            ptype = ("ttm" if ao["type"] == "ttm" else "fy") if kind == "flow" else \
                ("balance" if ao["type"] == "ttm" else "fy_balance")
            fields[key] = {"period_end": at, "period_type": ptype, "source": "sec_edgar"}
            _tag_provenance(info, "sec_edgar", f"SEC EDGAR ({r['concept']}): {r['how']}", paths=[key], overwrite=True)
            log["cut"].append({"field": key, "concept": r["concept"], "period_end": at, "how": r["how"],
                               "accns": r["accns"], "value": val})
        backed = {x["field"] for x in log["cut"]}
        if backed & {"operatingCashflow", "capitalExpenditures"}:
            ocf, capex = info.get("operatingCashflow"), info.get("capitalExpenditures")
            if ocf is not None and capex is not None:
                info["freeCashflow"] = ocf + capex if capex <= 0 else ocf - capex
                fields["freeCashflow"] = {"period_end": cut, "period_type": "ttm" if ao["type"] == "ttm" else "fy",
                                          "source": "derivado"}
                _tag_provenance(info, "derivado", "flujo de operaciones − capex del corte (respaldo de SEC EDGAR)",
                                paths=["freeCashflow"], overwrite=True)
    else:
        log["reason"] = "sin corte identificable (ruta quoteSummary): no se respalda"
    _apply_fy(info, facts, ctx, tol, log)
    return log


def _apply_fy(info: Dict[str, Any], facts: Dict[str, Any], ctx, tol: int, log: Dict[str, Any]) -> None:
    st = info.get("_statements_fy")
    if not isinstance(st, dict):
        return
    # Solo los ejercicios que usa el análisis (`fy_backup_years`: el Piotroski compara FY0 con FY1 y los CAGR van a 3
    # años, 4 puntos): el respaldo cubre huecos de esos ejercicios, no amplía la historia (Yahoo da 4 ejercicios y
    # deja casi vacía la quinta columna). TM: Yahoo trae la columna del FY1 entera vacía.
    years = cfg("data.edgar.fy_backup_years")
    covered = {stmt: set(range(years)) for stmt in ("inc", "bs", "cf")}
    for row, (stmt, field) in FY_ROWS.items():
        ends = st.get(f"{stmt}_ends") or []
        vals = list(st.get(row) or [])
        if not ends or all(i < len(vals) and vals[i] is not None for i in covered[stmt]):
            continue
        why = _excluded(field, info)
        if why:
            log["skipped"].append({"field": f"FY.{row}", "reason": why})
            continue
        vals += [None] * (len(ends) - len(vals))
        changed = False
        for i, end in enumerate(ends):
            if vals[i] is not None or not end or i not in covered[stmt]:
                continue
            r = edgar.field_value(facts, field, _dt.date.fromisoformat(end), tol)
            if r is None or "acumulado" in r["how"]:
                continue        # en las filas anuales solo el ejercicio entero (nunca un TTM construido)
            vals[i] = _convert(ctx, float(r["value"]), edgar.CONCEPTS[field][0], end)
            changed = True
            log["fy"].append({"field": f"FY.{row}", "fy_end": end, "concept": r["concept"], "how": r["how"],
                              "accns": r["accns"], "value": vals[i]})
        if changed:
            st[row] = vals
    # FCF anual = OCF − capex donde el respaldo completó uno de los dos y la fila no lo trae
    if any(x["field"] in ("FY.operating_cash_flow", "FY.capital_expenditure") for x in log["fy"]):
        ocf, capex = st.get("operating_cash_flow") or [], st.get("capital_expenditure") or []
        fcf = list(st.get("free_cash_flow") or [])
        n = max(len(ocf), len(capex))
        fcf += [None] * (n - len(fcf))
        for i in range(n):
            o = ocf[i] if i < len(ocf) else None
            c = capex[i] if i < len(capex) else None
            if fcf[i] is None and o is not None and c is not None:
                fcf[i] = o + c if c <= 0 else o - c
        st["free_cash_flow"] = fcf


EBIT_ESTIMATED = "estimado por la fuente"


def ebit_check(info: Dict[str, Any], ed: Dict[str, Any], ctx=None) -> Optional[Dict[str, Any]]:
    """F2_PRECEDENCIA §2.1, escenario B (D2): el beneficio operativo sigue siendo el de Yahoo, pero si difiere más de
    `ebit_estimate_rel_tol` del que presenta el emisor en EDGAR (mismo corte) se marca "estimado por la fuente" y se
    declaran los dos. Yahoo construye su "Operating Income" (KO, PLD, AMT, NEE, DUK, FCX, CRWD, UL, V en la 2a).
    -> data_provenance.ebit; display lo rotula."""
    from yf_adapter import _tag_provenance
    ao = info.get("_as_of") or {}
    cut, ebit = ao.get("date"), info.get("operatingIncome")
    per = (ao.get("fields") or {}).get("operatingIncome") or {}
    if ebit is None or not cut or ao.get("type") not in ("ttm", "fy") or per.get("source") == "sec_edgar":
        return None
    why = _excluded("operating_income", info)
    if why:
        return {"status": "excluido", "reason": why}
    facts = ed.get("facts") if ed.get("status") == "ok" else None
    if not facts:
        return {"status": "sin_edgar", "reason": ed.get("facts_reason") or ed.get("reason") or "sin hechos de EDGAR"}
    unit, stmt_cur = edgar.reporting_unit(facts, edgar.taxonomy(facts)), _statement_currency(info)
    if stmt_cur and unit != stmt_cur:
        return {"status": "sin_edgar", "reason": f"EDGAR presenta en {unit} y Yahoo en {stmt_cur}"}
    r = edgar.field_value(facts, "operating_income", _dt.date.fromisoformat(cut),
                          cfg("data.edgar.report_date_tolerance_days"))
    if r is None:
        return {"status": "sin_edgar", "reason": f"EDGAR no tiene el beneficio operativo del periodo que acaba el {cut}"}
    ev = _convert(ctx, float(r["value"]), "flow", cut)
    diff = (ebit - ev) / abs(ev) if ev else None
    out = {"status": "coincide", "source_value": ebit, "edgar_value": ev, "diff": diff, "concept": r["concept"],
           "how": r["how"], "accns": r["accns"], "period_end": cut,
           "tolerance": cfg("data.edgar.ebit_estimate_rel_tol")}
    if diff is None or abs(diff) > out["tolerance"]:
        out["status"] = "estimado"
        prev = ((info.get("_provenance") or {}).get("operatingIncome") or {})
        _tag_provenance(info, prev.get("source") or "yfinance_statements",
                        f"{prev.get('detail') or 'Yahoo'} · {EBIT_ESTIMATED}: difiere un {diff:+.1%} del que presenta "
                        f"el emisor en SEC EDGAR ({r['concept']}, {ev:,.0f})" if diff is not None else
                        f"{prev.get('detail') or 'Yahoo'} · {EBIT_ESTIMATED}: EDGAR da 0",
                        paths=["operatingIncome"], overwrite=True)
    return out


def official_source(ed: Dict[str, Any], today: _dt.date) -> Dict[str, Any]:
    """D7: {registered, status, cik, reason, fy, note} -> data_provenance.official_source.

    status: "registrado" (estados al día en EDGAR) · "verificado_fy" (con CIK, pero el último informe anual tiene
    más de `annual_stale_months` meses o EDGAR va por detrás: nota, sin techo) · "sin_fuente_oficial" (sin CIK o
    sin estados XBRL: aviso y techo "baja") · "no_disponible" (sin User-Agent o con EDGAR caído: nota, sin techo)."""
    st = ed.get("status")
    if st == "sin_cik":
        return {"registered": False, "status": "sin_fuente_oficial", "cik": None, "reason": ed.get("reason"),
                "fy": None, "note": OFFICIAL_SOURCE_NOTICE}
    if st == "ok" and ed.get("facts_status") == "sin_estados":
        return {"registered": False, "status": "sin_fuente_oficial", "cik": ed.get("cik"),
                "reason": ed.get("facts_reason"), "fy": None, "note": OFFICIAL_SOURCE_NOTICE}
    if st != "ok" or ed.get("facts_status") != "ok":
        return {"registered": None, "status": "no_disponible", "cik": ed.get("cik"),
                "reason": ed.get("facts_reason") or ed.get("reason"), "fy": None, "note": UNAVAILABLE_NOTE}
    facts = ed.get("facts") or {}
    fy_end = edgar.latest_fy_end(facts)
    fy = fy_end[:4] if fy_end else None
    annual = [f for f in ed.get("filings") or [] if f["form"] in edgar.ANNUAL_FORMS]
    last_annual = annual[0]["filingDate"] if annual else None
    months = cfg("data.edgar.annual_stale_months")
    stale = last_annual is None or (today - _dt.date.fromisoformat(last_annual)).days > months * 30.44
    unread = [p for p in ed.get("pending_filings") or [] if not p.get("read")]
    out = {"registered": True, "status": "registrado", "cik": ed.get("cik"), "reason": None, "fy": fy,
           "fy_end": fy_end, "last_annual_filing": last_annual, "note": None}
    if stale or unread:
        why = (f"el último informe anual en EDGAR es del {last_annual}" if stale and last_annual else
               "no hay informe anual reciente en EDGAR" if stale else
               f"EDGAR aún no incorpora el {unread[-1]['form']} del {unread[-1]['date']}")
        out.update(status="verificado_fy", reason=why,
                   note=f"Verificado con el FY {fy}: {why}." if fy else f"Verificación oficial parcial: {why}.")
    return out
