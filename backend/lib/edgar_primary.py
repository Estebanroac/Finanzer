"""
SEC EDGAR como fuente principal, campo a campo (fase 3, T1b; D2).

D2: "EDGAR pasará a fuente principal campo a campo cuando la fase 3 cierre las definiciones". La parada 1 de la fase 3
las cerró (F3_T1_PARADA1 §1; aprobación del usuario en el registro #25 de la bitácora). Aquí manda EDGAR, en el corte
del análisis (`info["_as_of"]`) y en las filas anuales (`info["_statements_fy"]`), para:

  · **EBIT** (todos menos los bancos): el resultado operativo que **presenta el emisor** en su cuenta de resultados
    (`OperatingIncomeLoss`; IFRS `ProfitLossFromOperatingActivities`), no el que construye Yahoo (KO excluye "otros
    cargos operativos"; PLD resta las ganancias de promoción). Con él, **EBITDA = EBIT que presenta el emisor + D&A**
    (parada 1b, registro #27), en el corte y en las filas anuales. La fila anual "EBIT" de Yahoo (resultado antes de
    intereses e impuestos, con lo no operativo) no cambia: la usa el ROCE. En un banco el EBIT no aplica (su
    equivalente, el beneficio antes de provisiones, es de la T4);
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

import numfmt
import sec_edgar as edgar
from edgar_backup import _convert, _statement_currency

NOT_APPLICABLE_BANK_EBIT = "beneficio operativo de un banco: no aplica (su equivalente es el beneficio antes de provisiones)"


def _starts(value: str, prefixes) -> bool:
    return any(value.startswith(p) for p in prefixes)


BANK_IFRS15_REVENUE = ("en un banco, la NIIF solo etiqueta como ingresos las comisiones (NIIF 15, "
                       "RevenueFromContractsWithCustomers), no los ingresos totales con el margen de intereses")


def is_bank(info: Dict[str, Any]) -> bool:
    from classify import norm_industry
    return (str(info.get("sector") or "") == "Financial Services"
            and _starts(norm_industry(info.get("industry")) or "", cfg("sectors.archetypes.bank_prefixes")))


def bank_history(info: Dict[str, Any], history_fy: Dict[str, Any]) -> None:
    """F9 · R3: en un banco IFRS, la serie de «ingresos» de EDGAR con el concepto de la NIIF 15 son solo las comisiones
    (BCS: 11.1 mil millones frente a unos ingresos totales tres veces mayores). Ni la historia ni los estados la usan
    como ingresos: queda sin dato, con el motivo."""
    h = (history_fy or {}).get("revenue") or {}
    if is_bank(info) and any(v.get("concept") == "ifrs-full:RevenueFromContractsWithCustomers"
                             for v in h.get("values") or []):
        history_fy["revenue"] = {**h, "values": [], "reason": BANK_IFRS15_REVENUE}


def _rules(info: Dict[str, Any], facts: Dict[str, Any], symbol: Optional[str]) -> List[Dict[str, Any]]:
    """[(clave del corte, fila anual, campo de EDGAR, motivo)] que manda EDGAR para este emisor; y los que no, con
    su motivo, como {"skip": ...}."""
    from classify import norm_industry
    sector = str(info.get("sector") or "")
    industry = norm_industry(info.get("industry")) or ""         # como lib/classify.py ("Insurance—Diversified")
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
            if key == "operatingIncome" and ao["type"] == "ttm":
                # F10 · perímetro (Plan, 29-oct): el TTM del EBIT cuadra con la suma de sus trimestres (± 1 pp de los
                # ingresos del corte) o no se usa: con perímetros mezclados (HON) se queda el de la fuente, dicho.
                got = edgar.checked_field_value(facts, r["field"], _dt.date.fromisoformat(cut), tol,
                                                info.get("totalRevenue"))
                if got.get("value") is None:
                    if got.get("candidates", {}).get("reciente") is not None:
                        log["skipped"].append({"field": key, "reason": got["reason"],
                                               "candidates": got["candidates"], "quarters": got["quarters"]})
                        info["_ebit_not_homogeneous"] = got["reason"]
                    else:
                        log["skipped"].append({"field": key,
                                               "reason": f"EDGAR no lo tiene del periodo que acaba el {cut}"})
                    continue
            else:
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
                               "accns": got["accns"], "value": val, "replaced": old, "why": r["why"],
                               **({"check": got["check"]} if got.get("check") else {})})
            _follow(info, key, old, val, fields, cut, ao["type"])
        # Fase 7 (registro #36): beneficio operativo de aseguradoras y conglomerados. Las ganancias de inversiones
        # del corte (realizadas y no realizadas, ASC 321) se guardan para que la normalización las excluya del
        # beneficio con el que se valora (BRK-B: 39 mil millones antes de impuestos en 2025 sobre 67 de beneficio).
        from classify import norm_industry
        _ind = (norm_industry(info.get("industry")) or "").lower()
        # Los corredores de seguros no tienen float ni cartera propia: fuera (revisión, hallazgo G).
        if (any(r.get("why", "").startswith("ingresos sin ganancias de inversión") for r in rules)
                and "broker" not in _ind):
            gi = edgar.field_value(facts, "investment_gains", _dt.date.fromisoformat(cut), tol)
            if gi is not None:
                val = _convert(ctx, float(gi["value"]), "flow", cut)
                info["_investment_gains"] = {"value": val, "concept": gi["concept"], "how": gi["how"],
                                             "period_end": cut, "accns": gi["accns"]}
                log["investment_gains"] = dict(info["_investment_gains"])
            else:
                log["skipped"].append({"field": "investment_gains", "reason": (
                    "IFRS: sin concepto estándar de ganancias de inversiones en EDGAR" if edgar.taxonomy(facts) != "us-gaap"
                    else f"EDGAR no tiene las ganancias de inversiones del periodo que acaba el {cut}")})
        else:
            # F10 · Plan, 29-oct: en las demás, las ganancias de inversiones del corte nombran lo que N1/N1b pueden
            # recortar (NVDA: 30,55 B$); no son partida estructural
            gi = edgar.field_value(facts, "investment_gains", _dt.date.fromisoformat(cut), tol)
            if gi is not None:
                info["_named_gains"] = {"value": _convert(ctx, float(gi["value"]), "flow", cut),
                                        "concept": gi["concept"], "how": gi["how"], "period_end": cut,
                                        "accns": gi["accns"]}
        _da_reconcile(info, facts, ctx, cut, tol, log)
        # F10 · Plan, 29-oct: cargos y ventas del corte con etiquetas estándar (lo que las filas de Yahoo no recogen)
        ch = edgar.charges_ttm(facts, _dt.date.fromisoformat(cut), tol)
        if ch is not None:
            def cv(v, end):
                return _convert(ctx, float(v), "flow", end) if v else 0.0
            info["_edgar_charges"] = {
                "neg": cv(ch["neg"], cut), "pos": cv(ch["pos"], cut), "charges": cv(ch["charges"], cut),
                "detail": {c: cv(v, cut) for c, v in ch["detail"].items()},
                "annual": [{"end": a["end"], "neg": cv(a["neg"], a["end"]), "pos": cv(a["pos"], a["end"])}
                           for a in ch["annual"]], "period_end": cut}
            log["charges"] = {"detail": info["_edgar_charges"]["detail"], "period_end": cut}
    else:
        log["reason"] = "sin corte identificable (ruta quoteSummary): manda la fuente"
    _da_reconcile_fy(info, facts, ctx, tol, log)
    _apply_fy(info, facts, rules, ctx, tol, log)
    _apply_fy_series(info, facts, rules, ctx, tol, log)
    return log


def _apply_fy_series(info: Dict[str, Any], facts: Dict[str, Any], rules, ctx, tol: int, log: Dict[str, Any]) -> None:
    """F9 · R3 (decisión del PM, regla M5): una sola serie anual por campo en todo el informe. Los ingresos y el
    beneficio neto de cada ejercicio de los estados salen de la misma serie de EDGAR que la historia de 10 años
    (sec_edgar.annual_history), convertidos como los de la fuente, si EDGAR tiene TODOS los ejercicios de los estados;
    si le falta alguno, la fuente entera (nunca una serie con dos definiciones) y se dice por qué. NU: crecimiento de
    28.5% con los ingresos de Yahoo frente a 37.0% en la historia de EDGAR del mismo FY2025. Una fila que ya fija otra
    regla de EDGAR (ingresos netos de un banco de EE. UU., ingresos sin ganancias de una aseguradora) no se toca.
    Cada ejercicio que difiere más de `fy_series_reconcile_rel` queda en log["reconciliation"]."""
    st = info.get("_statements_fy")
    if not isinstance(st, dict):
        return
    done = {r["row"] for r in rules}
    rel = cfg("data.edgar.fy_series_reconcile_rel")
    log.setdefault("series", [])
    log.setdefault("reconciliation", [])
    for field in cfg("data.edgar.fy_series_fields"):
        if field in done:
            continue
        ends = [e for e in (st.get("inc_ends") or []) if e]
        old = list(st.get(field) or [])
        if not ends or not any(v is not None for v in old):
            continue
        _h = {field: edgar.annual_history(facts, field)}
        bank_history(info, _h)
        if _h[field].get("reason"):
            log["series"].append({"field": field, "source": "fuente", "reason": _h[field]["reason"]})
            continue
        hist = _h[field].get("values") or []
        by_end = {}
        for end in ends:
            d = _dt.date.fromisoformat(end)
            hit = next((h for h in hist if abs((_dt.date.fromisoformat(h["fy_end"]) - d).days) <= tol), None)
            if hit is not None:
                by_end[end] = hit
        missing = [e for e in ends if e not in by_end]
        # F10 · B2 (TKO, constituida en 2023): los ejercicios anteriores al primero que el emisor presenta en la SEC no
        # son suyos (la fuente da los de la predecesora): sin dato, con el motivo, y la serie es la de EDGAR. Un hueco
        # dentro de la historia de EDGAR sigue dejando la fuente entera.
        first = edgar.first_annual_period(facts)
        before = [e for e in missing if first and _dt.date.fromisoformat(e) < _dt.date.fromisoformat(first) -
                  _dt.timedelta(days=tol)]
        gaps = [e for e in missing if e not in before]
        if gaps:
            # F10 · B2 (BE: EDGAR sin el beneficio de 2024 y 2025): si en todos los ejercicios comunes EDGAR y la fuente
            # coinciden (± `fy_series_reconcile_rel`), son la misma definición: EDGAR da los suyos y la fuente los que
            # le faltan, y se dice. Si no coinciden, la fuente entera (nunca dos definiciones).
            src = dict(zip(ends, old + [None] * (len(ends) - len(old))))
            both = [e for e in by_end if src.get(e) is not None]
            same = both and all(abs(src[e] - _convert(ctx, float(by_end[e]["value"]), "flow", e))
                                <= rel * abs(_convert(ctx, float(by_end[e]["value"]), "flow", e)) for e in both)
            if not same or any(src.get(e) is None for e in gaps):
                log["series"].append({"field": field, "source": "fuente",
                                      "reason": f"EDGAR no tiene el ejercicio cerrado el {gaps[0]}: manda la fuente"})
                continue
            log.setdefault("filled_from_source", []).append(
                {"field": field, "years": gaps, "reason": f"EDGAR no los tiene; coinciden con la fuente (± {rel:.0%}) "
                                                         f"en los {len(both)} ejercicios comunes"})
        if len(before) == len(ends):
            log["series"].append({"field": field, "source": "fuente",
                                  "reason": "EDGAR no tiene ningún ejercicio de los estados: manda la fuente"})
            continue
        # Una definición por serie: un concepto que completa ejercicios de otro cuenta como el mismo solo si coincide
        # con él (sec_edgar.annual_history, `definition`).
        concepts = sorted({by_end[e].get("definition") or by_end[e]["concept"] for e in ends if e in by_end})
        if len(concepts) > 1:
            log["series"].append({"field": field, "source": "fuente",
                                  "reason": f"EDGAR usa dos conceptos en la ventana ({', '.join(concepts)}): manda la fuente"})
            continue
        new = [_convert(ctx, float(by_end[e]["value"]), "flow", e) if e in by_end else
               (dict(zip(ends, old)).get(e) if e in gaps else None) for e in ends]
        if before:
            log.setdefault("before_first_filing", []).append(
                {"field": field, "years": before, "first": first,
                 "reason": f"la empresa presenta sus cuentas en la SEC desde {first[:4]}"})
        for e, o, n in zip(ends, old + [None] * (len(ends) - len(old)), new):
            if o is not None and n and abs(o - n) > rel * abs(n):
                log["reconciliation"].append({"field": field, "fy_end": e, "edgar": n, "source": o,
                                              "diff_rel": (o - n) / abs(n), "concept": by_end[e]["concept"]})
        st[field] = new
        log["series"].append({"field": field, "source": "sec_edgar", "concepts": concepts,
                              "years": len(ends) - len(before) - len(gaps)})


DA_EXCLUDED = ("amortización de activos operativos recurrentes (contenido, software capitalizado…) sin respaldo como "
               "intangibles adquiridos")


def _da_split(info: Dict[str, Any], cut: str, tol: int) -> Optional[Dict[str, float]]:
    """Desglose del D&A de la fuente en el corte: el del TTM o, con el corte en un ejercicio, el de su fila anual."""
    sp = info.get("_da_split")
    if sp:
        return sp
    st = info.get("_statements_fy") or {}
    ends = st.get("cf_ends") or []
    if (info.get("_as_of") or {}).get("type") != "fy" or not ends or not ends[0] or \
            not edgar._near(ends[0], _dt.date.fromisoformat(cut), tol):
        return None
    row = {k: (st.get(r) or [None])[0] for k, r in (("total", "depreciation_amortization"),
                                                    ("depreciation", "da_depreciation"),
                                                    ("amortization", "da_amortization"))}
    return row if all(v is not None for v in row.values()) else None


def _da_reconcile(info: Dict[str, Any], facts: Dict[str, Any], ctx, cut: str, tol: int, log: Dict[str, Any]) -> None:
    """Escalera de márgenes de NFLX (decisión del PM, 30-oct): el EBITDA no lleva amortizaciones de activos operativos
    recurrentes. NFLX: el D&A de Yahoo (17,92 B$) lleva 17,53 de amortización del contenido, un coste que va en el coste
    de ventas y se paga cada año; el margen EBITDA (67,3 %) salía por encima del bruto (50,7 %). TTWO, el software
    capitalizado.

    Los conceptos de D&A de EDGAR no sirven como total (36 emisores solo etiquetan `Depreciation`; MCD usa un paraguas
    para una partida parcial), pero el desglose de la fuente cuadra con EDGAR en casi todos. Se compara la amortización
    de intangibles de la fuente con su respaldo en EDGAR (sec_edgar.da_split_ttm): el mayor de la amortización de
    intangibles adquiridos y el paraguas − la depreciación. Lo que no tiene respaldo:
      · si pasa de la materialidad de N1 (`nonoperating_tolerance_revenue` de los ingresos), sale del D&A y del EBITDA,
        con su nombre;
      · si no, no se toca y se declara «no verificable» (puede ser etiquetado parcial de EDGAR).
    -> log["da"] (data_provenance.edgar.primary.da)."""
    from yf_adapter import _tag_provenance
    if str(info.get("sector") or "") == "Financial Services":
        return                                     # el EBITDA no aplica a una financiera (MTB)
    sp, da = _da_split(info, cut, tol), info.get("depreciation")
    if not sp or da is None or not sp.get("total") or not sp.get("amortization") or sp["amortization"] <= 0:
        return
    f = abs(da) / abs(sp["total"])                 # a la moneda del análisis, como el D&A del corte
    dep, am = abs(sp["depreciation"]) * f, abs(sp["amortization"]) * f
    rev = info.get("totalRevenue")
    d = _da_decide(facts, ctx, cut, tol, dep, am, rev)
    if d["status"] != "excluido":
        log["da"] = d
        return
    excess = d["excluded"]
    new = da - excess if da >= 0 else da + excess
    info["depreciation"] = new
    fields = (info.get("_as_of") or {}).setdefault("fields", {})
    ptype = "ttm" if (info.get("_as_of") or {}).get("type") == "ttm" else "fy"
    fields["depreciation"] = {"period_end": cut, "period_type": ptype, "source": "derivado"}
    _tag_provenance(info, "derivado", f"D&A de la fuente sin la {DA_EXCLUDED}", paths=["depreciation"],
                    overwrite=True)
    if info.get("operatingIncome") is not None:
        info["ebitda"] = info["operatingIncome"] + abs(new)
        fields["ebitda"] = {"period_end": cut, "period_type": ptype, "source": "derivado"}
        _tag_provenance(info, "derivado", f"EBIT del corte + D&A sin la {DA_EXCLUDED}", paths=["ebitda"],
                        overwrite=True)
    log["da"] = dict(d, old=da, new=new, reason=(f"{DA_EXCLUDED}: {numfmt.money(excess, info.get('currency'))} "
                                                 f"({excess / abs(rev):.1%} de los ingresos) fuera del D&A del EBITDA"))


def _da_decide(facts: Dict[str, Any], ctx, end: str, tol: int, dep: float, am: float,
               rev: Optional[float]) -> Dict[str, Any]:
    """La regla de _da_reconcile para el periodo de doce meses que acaba en `end` (el corte o un ejercicio): la
    amortización de intangibles de la fuente (`am`, en la moneda del análisis) frente a su respaldo en EDGAR. ->
    {status: respaldado | no_verificable | excluido, amortization, support, unsupported | excluded, reason}."""
    e = edgar.da_split_ttm(facts, _dt.date.fromisoformat(end), tol)
    supports = [abs(_convert(ctx, float(e["amortization"]), "flow", end))] if e["amortization"] is not None else []
    if e["umbrella"] is not None:
        supports.append(max(abs(_convert(ctx, float(e["umbrella"]), "flow", end)) - dep, 0.0))
    if not supports:
        return {"status": "no_verificable", "amortization": am, "unsupported": am,
                "reason": "EDGAR no etiqueta ni la amortización de intangibles ni un D&A total del periodo: la "
                          "amortización de la fuente no se puede verificar"}
    support = max(supports)
    if am <= support * (1 + cfg("data.edgar.history_relay_rel_tol")):
        return {"status": "respaldado", "amortization": am, "support": support}
    excess = am - support
    mat = cfg("thresholds.normalization.nonoperating_tolerance_revenue")
    if not rev or excess <= mat * abs(rev):
        return {"status": "no_verificable", "amortization": am, "support": support, "unsupported": excess,
                "reason": (f"amortización de intangibles de la fuente sin respaldo en EDGAR por debajo del {mat:.0%} "
                           "de los ingresos: puede ser etiquetado parcial de EDGAR; no se toca")}
    return {"status": "excluido", "amortization": am, "support": support, "excluded": excess,
            "reason": f"{DA_EXCLUDED}: {excess / abs(rev):.1%} de los ingresos fuera del D&A del EBITDA"}


def _da_reconcile_fy(info: Dict[str, Any], facts: Dict[str, Any], ctx, tol: int, log: Dict[str, Any]) -> None:
    """La misma regla en cada ejercicio de los estados (decisión del PM, 30-oct: NFLX no puede enseñar un 32 % en el TTM
    y un 67 % en su historia): el D&A y el EBITDA de la fila anual sin la amortización sin respaldo en EDGAR de ese
    ejercicio. Sin EDGAR del ejercicio, «no verificable» y declarado. -> log["da_fy"]."""
    st = info.get("_statements_fy")
    if not isinstance(st, dict) or str(info.get("sector") or "") == "Financial Services":
        return
    cf_ends, inc_ends = st.get("cf_ends") or [], st.get("inc_ends") or []
    da, dep, am = (list(st.get(k) or []) for k in ("depreciation_amortization", "da_depreciation", "da_amortization"))
    ebitda, rev = st.get("ebitda"), st.get("revenue") or []
    out = []
    for j, end in enumerate(cf_ends):
        if not end or j >= len(am) or j >= len(dep) or j >= len(da) or not am[j] or am[j] <= 0 \
                or dep[j] is None or da[j] is None:
            continue
        i = inc_ends.index(end) if end in inc_ends else None
        d = _da_decide(facts, ctx, end, tol, abs(dep[j]), abs(am[j]), rev[i] if i is not None and i < len(rev) else None)
        if d["status"] == "excluido":
            x = d["excluded"]
            da[j] = da[j] - x if da[j] >= 0 else da[j] + x
            if isinstance(ebitda, list) and i is not None and i < len(ebitda) and ebitda[i] is not None:
                ebitda[i] = ebitda[i] - x
        out.append({"fy_end": end, **d})
    if out:
        st["depreciation_amortization"] = da
        log["da_fy"] = out


def _follow(info: Dict[str, Any], key: str, old, val, fields, cut, ptype) -> None:
    """Lo que depende del campo sustituido: el EBITDA (EBIT + D&A) y el FCF (OCF − capex)."""
    from yf_adapter import _tag_provenance
    if key == "operatingIncome" and info.get("depreciation") is not None:
        info["ebitda"] = val + abs(info["depreciation"])
        fields["ebitda"] = {"period_end": cut, "period_type": "ttm" if ptype == "ttm" else "fy", "source": "derivado"}
        _tag_provenance(info, "derivado", "EBIT que presenta el emisor (SEC EDGAR) + D&A del corte", paths=["ebitda"],
                        overwrite=True)
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
            if row == "operating_income":                  # EBITDA = EBIT del emisor + D&A del mismo ejercicio
                da, cf_ends, ebitda = (st.get("depreciation_amortization") or [], st.get("cf_ends") or [],
                                       st.get("ebitda"))
                j = cf_ends.index(end) if end in cf_ends else None
                if isinstance(ebitda, list) and i < len(ebitda) and j is not None and j < len(da) and da[j] is not None:
                    ebitda[i] = new + abs(da[j])
            if row == "capital_expenditure":
                ocf, fcf = st.get("operating_cash_flow") or [], st.get("free_cash_flow")
                if isinstance(fcf, list) and i < len(fcf) and i < len(ocf) and ocf[i] is not None:
                    fcf[i] = ocf[i] + (new if new <= 0 else -new)
        if changed:
            st[row] = vals
