"""
F8 · E3 (auditoría externa del 26-oct-2026): FFO de los REIT según la definición de Nareit, y AFFO con su fórmula.

    FFO (Nareit) = beneficio neto + D&A − ganancias (+ pérdidas) por venta de inmuebles + deterioros de inmuebles
    AFFO         = FFO − rentas lineales − capex recurrente      (sin definición estándar: la fórmula se muestra)

Antes el motor usaba beneficio neto + D&A: las ganancias por venta de inmuebles, que un REIT como PLD realiza todos los
años, inflaban el FFO (PLD, TTM al 2T-2026: 6.940 millones frente a 6.449 del FFO Nareit que publica; registro
F8_INDEPENDIENTES §E3).

De dónde salen los ajustes: del estado de flujos tal como lo presentó el emisor en su 10-K y sus 10-Q (SEC; servido por
Finnhub /stock/financials-reported, gratuito). Es donde el emisor concilia el beneficio con el flujo de operaciones, con
sus conceptos estándar o propios (PLD: `pld_GainsOnOtherDispositionsOfInvestmentsInRealEstateNet`, que companyfacts no
publica). Es el estado completo: una partida que no aparece vale 0 en ese periodo. Las partidas se reconocen por el
nombre del concepto con las reglas de config/data.toml [reit_ffo]. Sin ese estado no hay FFO Nareit: companyfacts no dice
si al emisor le falta alguna partida propia, así que no hace de respaldo ("sin dato" con su motivo).

EDGAR concilia: el flujo de operaciones de cada estado usado debe estar en companyfacts (o en los filings que aún no
trae) y coincidir con él (±`reconcile_rel_tol`); si no, no se usa. Así EDGAR valida también la moneda y el periodo.

D&A: la de los estados del motor (toda la D&A; el XBRL no separa la inmobiliaria). Lo que Nareit también ajusta y el
XBRL no da (la parte de la D&A de las participadas y de los minoritarios) no se estima: se declara.

FFO del emisor como referencia: ninguna fuente gratuita lo da estructurado (Finnhub gratuito no tiene FFO: /stock/metric
no lo trae y /stock/earnings es el BPA; el 8-K de resultados lo publica en el comunicado, en HTML o imágenes, sin XBRL).
No se compara y se declara (`NO_REFERENCE`).
"""
import datetime as _dt
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

import numfmt
from settings import cfg

GAINS, IMPAIRMENT, STRAIGHT_LINE, RECURRING_CAPEX = "gains", "impairment", "straight_line", "recurring_capex"
ITEMS = (GAINS, IMPAIRMENT, STRAIGHT_LINE, RECURRING_CAPEX)
LABELS = {GAINS: "ventas de inmuebles", IMPAIRMENT: "deterioros de inmuebles", STRAIGHT_LINE: "rentas lineales",
          RECURRING_CAPEX: "capex recurrente"}
_OCF = re.compile(r"^NetCashProvidedByUsedInOperatingActivities", re.I)
_PROFIT_LOSS = re.compile(r"^ProfitLoss$", re.I)     # beneficio consolidado, con la parte de los minoritarios
SOURCE = "estado de flujos presentado por el emisor (10-K/10-Q, SEC; Finnhub /stock/financials-reported)"
NO_REFERENCE = ("FFO publicado por el emisor: sin fuente gratuita y estructurada (Finnhub gratuito no lo da y el 8-K de "
                "resultados lo publica sin XBRL); no se compara")
JV_REASON = "tiene participadas materiales cuyo FFO no se puede ajustar con los datos públicos estructurados"
NOT_FROM_XBRL = ("no incluye lo que Nareit también ajusta y el XBRL no separa: la D&A no inmobiliaria y la parte de "
                 "participadas y minoritarios")


def _local(concept: str) -> str:
    """Nombre del concepto sin el prefijo de la taxonomía ("us-gaap_X", "pld_X", "us-gaap:X" -> "X")."""
    return re.split(r"[_:]", concept, maxsplit=1)[-1] if concept else ""


def _rules(item: str) -> Tuple[List[re.Pattern], List[re.Pattern]]:
    return ([re.compile(p, re.I) for p in cfg(f"data.reit_ffo.{item}_include")],
            [re.compile(p, re.I) for p in cfg(f"data.reit_ffo.{item}_exclude")])


def item_of(concept: str) -> Optional[str]:
    """Ajuste al que pertenece una partida del estado de flujos, o None. Las ganancias van antes que los deterioros:
    una partida que mezcla venta y deterioro (IRM: `GainLossOnSalesOfAssetsAndAssetImpairmentCharges`) es una
    ganancia neta."""
    name = _local(concept)
    for item in ITEMS:
        inc, exc = _rules(item)
        if any(r.search(name) for r in inc) and not any(r.search(name) for r in exc):
            return item
    return None


def _equity_method(concept: str) -> bool:
    return any(re.search(p, _local(concept), re.I) for p in cfg("data.reit_ffo.equity_method_include"))


def keep(concept: str) -> bool:
    """Lo que se guarda de cada estado: las partidas de los ajustes, el resultado de participadas y el flujo de
    operaciones (para conciliar)."""
    return (item_of(concept) is not None or _equity_method(concept) or bool(_OCF.match(_local(concept)))
            or bool(_PROFIT_LOSS.match(_local(concept))))


def applies(industry: Optional[str]) -> bool:
    """El FFO se resuelve para los emisores de industria REIT (la misma regla que el arquetipo, lib/classify.py)."""
    from classify import reit_industry
    return reit_industry(industry)


# ───────────────────────── periodos ─────────────────────────

def _d(s: str) -> _dt.date:
    return _dt.date.fromisoformat(s)


def _dur(e: Dict[str, Any]) -> int:
    return (_d(e["end"]) - _d(e["start"])).days


def _pick(entries: List[Dict[str, Any]], end: _dt.date, lo: int, hi: int, tol: int,
          dur: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """El estado que acaba en `end` (± tol días) con una duración en [lo, hi] (o ± tol de `dur`), el último presentado."""
    ok = [e for e in entries if e.get("start") and e.get("end") and abs((_d(e["end"]) - end).days) <= tol
          and (lo <= _dur(e) <= hi if dur is None else abs(_dur(e) - dur) <= tol)]
    return max(ok, key=lambda e: (e.get("filed") or "", e.get("accn") or "")) if ok else None


def _parts(annual: List[Dict[str, Any]], quarterly: List[Dict[str, Any]], cut: _dt.date,
           tol: int) -> Optional[Tuple[List[Tuple[int, Dict[str, Any]]], str]]:
    """Doce meses que acaban en `cut`: el ejercicio que acaba ahí o el anterior + el acumulado del año − el acumulado
    del año anterior (como sec_edgar.flow_ttm)."""
    fy = _pick(annual, cut, 350, 380, tol)
    if fy:
        return [(1, fy)], f"ejercicio {fy['start']} a {fy['end']} ({fy['form']} {fy['accn']})"
    ytd = _pick(quarterly, cut, 80, 349, tol)
    if not ytd:
        return None
    prev_fy = _pick(annual, _d(ytd["start"]) - _dt.timedelta(days=1), 350, 380, tol)
    prev_ytd = _pick(quarterly, _d(ytd["end"]) - _dt.timedelta(days=365), 0, 0, tol, dur=_dur(ytd))
    if not prev_fy or not prev_ytd:
        return None
    how = (f"ejercicio {prev_fy['start']} a {prev_fy['end']} ({prev_fy['form']} {prev_fy['accn']}) + acumulado "
           f"{ytd['start']} a {ytd['end']} ({ytd['form']} {ytd['accn']}) − acumulado {prev_ytd['start']} a "
           f"{prev_ytd['end']} ({prev_ytd['form']} {prev_ytd['accn']})")
    return [(1, prev_fy), (1, ytd), (-1, prev_ytd)], how


def _items(entry: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """{ajuste: {value, lines}} de un estado (una partida ausente vale 0), {"ocf": valor o None} y {"equity_method":
    resultado de participadas}."""
    out = {i: {"value": 0.0, "lines": []} for i in ITEMS}
    out["ocf"], out["equity_method"], out["profit_loss"] = None, 0.0, None
    for ln in entry.get("lines") or []:
        try:
            v = float(ln.get("value"))
        except (TypeError, ValueError):
            continue
        c = str(ln.get("concept") or "")
        if _OCF.match(_local(c)):
            out["ocf"] = v if out["ocf"] is None else out["ocf"]
            continue
        if _equity_method(c):
            out["equity_method"] += v
            continue
        if _PROFIT_LOSS.match(_local(c)):
            out["profit_loss"] = v if out["profit_loss"] is None else out["profit_loss"]
            continue
        it = item_of(c)
        if it:
            out[it]["value"] += v
            out[it]["lines"].append({"concept": c, "label": ln.get("label"), "value": v})
    return out


# ───────────────────────── conciliación con EDGAR ─────────────────────────

def _edgar_ocf(facts: Optional[Dict[str, Any]], entry: Dict[str, Any], tol: int) -> Optional[float]:
    """Flujo de operaciones de companyfacts del mismo periodo que el estado (mismo inicio, fin ± tol), o None."""
    if not facts:
        return None
    import sec_edgar as edgar
    for _c, fs in edgar.candidates(facts, "operating_cash_flow"):
        got = [f for f in fs if f.get("start") == entry["start"] and abs((_d(f["end"]) - _d(entry["end"])).days) <= tol]
        if got:
            return float(max(got, key=lambda f: (f.get("filed") or "", f.get("accn") or ""))["val"])
    return None


def _latest_edgar_filed(facts: Optional[Dict[str, Any]]) -> str:
    """Fecha del último informe del que companyfacts trae el flujo de operaciones ("" sin hechos)."""
    if not facts:
        return ""
    import sec_edgar as edgar
    return max((f.get("filed") or "" for _c, fs in edgar.candidates(facts, "operating_cash_flow") for f in fs),
               default="")


def _reconcile(facts, entries: List[Dict[str, Any]], tol: int) -> Dict[str, Any]:
    """Cada estado usado, su flujo de operaciones frente al de EDGAR. status: "conciliado" (EDGAR tiene todos y
    coinciden), "conciliado_parcial" (coinciden los que EDGAR tiene y los que le faltan se presentaron después de su
    último informe: aún no le han llegado), "no_conciliado" (alguno no coincide) o "sin_hecho_edgar" (a EDGAR le falta
    alguno que ya debería tener).

    F13 · paso 7 (revisión de 110 empresas, PLD): companyfacts publica un informe días después que la fuente del estado
    presentado. Exigirlo hacía que el FFO de PLD saliera o no según el día (confianza alta o baja en la misma jornada)."""
    rel = cfg("data.reit_ffo.reconcile_rel_tol")
    last = _latest_edgar_filed(facts)
    detail, seen, bad, pending, missing = [], 0, [], 0, 0
    for e in entries:
        mine, theirs = _items(e)["ocf"], _edgar_ocf(facts, e, tol)
        row = {"accn": e.get("accn"), "period": f"{e['start']} a {e['end']}", "ocf_presented": mine, "ocf_edgar": theirs}
        if theirs is not None and mine is not None:
            seen += 1
            row["ok"] = abs(mine - theirs) <= rel * max(abs(theirs), 1.0)
            if not row["ok"]:
                bad.append(row)
        elif last and (e.get("filed") or "") > last:
            row["pending"] = f"presentado el {e.get('filed')}, después del último informe que trae EDGAR ({last})"
            pending += 1
        else:
            missing += 1
        detail.append(row)
    status = ("no_conciliado" if bad else "conciliado" if seen == len(entries) else
              "conciliado_parcial" if seen and not missing and pending else "sin_hecho_edgar")
    return {"status": status, "detail": detail}


# ───────────────────────── resolución ─────────────────────────

def no_data(reason: str) -> Dict[str, Any]:
    return {"status": "sin_dato", "reason": reason, "source": SOURCE, "reference": NO_REFERENCE}


def resolve(symbol: str, info: Dict[str, Any], facts: Optional[Dict[str, Any]], ctx=None,
            fetch: Optional[Callable[[str, str], Optional[list]]] = None) -> Dict[str, Any]:
    """Ajustes Nareit del corte del análisis (TTM o ejercicio) y de cada ejercicio, en la moneda del precio.
    {status: "ok"|"sin_dato", reason, period: {cut, how}, items: {ajuste: {value, lines}}, fy: {fin: {ajuste: valor}},
    reconciliation, source, reference}."""
    from edgar_backup import _convert, _statement_currency
    if fetch is None:
        import finnhub_fallback as fh
        if not fh.is_enabled():
            return no_data("sin clave de Finnhub: no se puede leer el estado de flujos que presentó el emisor")
        fetch = lambda s, freq: fh.financials_reported(s, freq, keep)   # noqa: E731
    ao = info.get("_as_of") or {}
    if ao.get("type") not in ("ttm", "fy") or not ao.get("date"):
        return no_data("sin corte identificable de los estados")
    cut = _d(ao["date"])
    tol = cfg("data.edgar.report_date_tolerance_days")
    annual, quarterly = fetch(symbol, "annual"), fetch(symbol, "quarterly")
    if not annual:
        return no_data("la fuente no devolvió los 10-K presentados por el emisor")
    if not facts:
        return no_data("sin los hechos de EDGAR con los que conciliar el estado presentado")
    import sec_edgar as edgar
    unit, stmt_cur = edgar.reporting_unit(facts, edgar.taxonomy(facts)), _statement_currency(info)
    if unit is None or (stmt_cur and unit != stmt_cur):
        return no_data(f"EDGAR presenta los estados en {unit} y la fuente en {stmt_cur}: no se mezclan")
    got = _parts(annual, quarterly or [], cut, tol)
    if got is None:
        return no_data(f"no hay estados presentados que cubran los doce meses hasta el {ao['date']}")
    parts, how = got
    rec = _reconcile(facts, [e for _s, e in parts], tol)
    if rec["status"] not in ("conciliado", "conciliado_parcial"):
        out = no_data("el flujo de operaciones del estado presentado no coincide con el de EDGAR del mismo periodo"
                      if rec["status"] == "no_conciliado" else
                      "EDGAR no tiene el flujo de operaciones de alguno de los estados presentados: no se puede conciliar")
        out["reconciliation"] = rec
        return out
    items: Dict[str, Dict[str, Any]] = {}
    for it in ITEMS:
        total, lines = 0.0, []
        for sign, e in parts:
            x = _items(e)[it]
            total += sign * x["value"]
            lines += [dict(ln, sign=sign, accn=e.get("accn")) for ln in x["lines"]]
        items[it] = {"value": _convert(ctx, total, "flow", ao["date"]), "lines": lines}
    jv = _convert(ctx, sum(sign * _items(e)["equity_method"] for sign, e in parts), "flow", ao["date"])
    pls = [_items(e)["profit_loss"] for _s, e in parts]
    consolidated = (_convert(ctx, sum(sign * v for (sign, _e), v in zip(parts, pls)), "flow", ao["date"])
                    if all(v is not None for v in pls) else None)
    fy = {}
    for e in annual:
        if e.get("start") and e.get("end") and 350 <= _dur(e) <= 380:
            if e["end"] not in fy or (e.get("filed") or "") > fy[e["end"]]["_filed"]:
                vals = _items(e)
                fy[e["end"]] = {"_filed": e.get("filed") or "",
                                **{it: _convert(ctx, vals[it]["value"], "flow", e["end"]) for it in ITEMS},
                                "equity_method": _convert(ctx, vals["equity_method"], "flow", e["end"])}
    for v in fy.values():
        v.pop("_filed", None)
    return {"status": "ok", "reason": None, "period": {"cut": ao["date"], "how": how}, "items": items, "fy": fy,
            "equity_method_income": jv, "consolidated_net_income": consolidated,
            "reconciliation": rec, "source": SOURCE, "reference": NO_REFERENCE}


def _fy_entry(res: Optional[Dict[str, Any]], fy_end: Optional[str], tol: Optional[int]) -> Optional[Dict[str, Any]]:
    if not res or res.get("status") != "ok" or not fy_end:
        return None
    tol = cfg("data.edgar.report_date_tolerance_days") if tol is None else tol
    near = [k for k in (res.get("fy") or {}) if abs((_d(k) - _d(fy_end)).days) <= tol]
    return res["fy"][min(near, key=lambda k: abs((_d(k) - _d(fy_end)).days))] if near else None


def fy_adjustment(res: Optional[Dict[str, Any]], fy_end: Optional[str], tol: Optional[int] = None) -> Optional[float]:
    """Ajuste Nareit del ejercicio que acaba en `fy_end` (− ganancias por venta + deterioros), o None sin dato."""
    v = _fy_entry(res, fy_end, tol)
    return None if v is None else -v[GAINS] + v[IMPAIRMENT]


def jv_material(jv: Optional[float], ffo: Optional[float]) -> bool:
    """El resultado de participadas pesa al menos `ffo_jv_material_pct` del FFO calculado: su parte de la D&A, que
    Nareit suma y el XBRL no separa, mueve el FFO tanto que no se puede dar como cálculo propio."""
    if not jv or ffo is None:
        return False
    return abs(jv) >= cfg("data.reit_ffo.ffo_jv_material_pct") * abs(ffo)


def jv_reason(jv: float, ffo: float) -> str:
    share = f"{100 * abs(jv) / abs(ffo):.1f} %".replace(".", ",") if ffo else "—"
    pct = f"{100 * cfg('data.reit_ffo.ffo_jv_material_pct'):.0f} %"
    return (f"FFO según Nareit sin dato: {JV_REASON} (resultado de participadas: {numfmt.money(jv)}, el {share} del FFO "
            f"calculado; umbral: {pct})")


def fy_ffo(res: Optional[Dict[str, Any]], fy_end: Optional[str], base: Optional[float],
           tol: Optional[int] = None) -> Tuple[Optional[float], Optional[str]]:
    """FFO Nareit del ejercicio que acaba en `fy_end` a partir de `base` (beneficio + D&A): (valor, None), o
    (None, motivo) si falta el ajuste o las participadas del ejercicio son materiales."""
    v = _fy_entry(res, fy_end, tol)
    if base is None or v is None:
        return None, None
    ffo = base - v[GAINS] + v[IMPAIRMENT]
    if jv_material(v.get("equity_method"), ffo):
        return None, jv_reason(v["equity_method"], ffo)
    return ffo, None


# ───────────────────────── FFO y AFFO ─────────────────────────

def compute(net_income: Optional[float], da: Optional[float], res: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """FFO (Nareit) y AFFO del corte, con sus componentes y su fórmula. {ffo, affo, components, formula,
    affo_formula, ffo_reason, affo_reason, period, source, reference, reconciliation}."""
    out: Dict[str, Any] = {"ffo": None, "affo": None, "components": None, "ffo_reason": None, "affo_reason": None,
                           "source": SOURCE, "reference": NO_REFERENCE, "not_included": NOT_FROM_XBRL,
                           "period": (res or {}).get("period"), "reconciliation": (res or {}).get("reconciliation")}
    if not res or res.get("status") != "ok":
        out["ffo_reason"] = out["affo_reason"] = (f"FFO según Nareit sin dato: {(res or {}).get('reason') or 'sin los ajustes del emisor'}")
        return out
    if net_income is None or da is None:
        out["ffo_reason"] = out["affo_reason"] = "FFO según Nareit sin dato: falta el beneficio neto o la D&A del corte"
        return out
    it = res["items"]
    g, imp = it[GAINS]["value"], it[IMPAIRMENT]["value"]
    da = abs(da)
    ffo = net_income + da - g + imp
    out["ffo"] = ffo
    out["components"] = {"net_income": net_income, "da": da, GAINS: g, IMPAIRMENT: imp,
                         STRAIGHT_LINE: it[STRAIGHT_LINE]["value"], RECURRING_CAPEX: it[RECURRING_CAPEX]["value"],
                         "lines": {k: it[k]["lines"] for k in ITEMS}}
    out["formula"] = "FFO (Nareit) = beneficio neto + D&A − ventas de inmuebles + deterioros de inmuebles"
    m = numfmt.money
    out["formula_values"] = (f"{m(net_income)} + {m(da)} − ({m(g)}) + {m(imp)} = {m(ffo)}")
    # Lo que Nareit también ajusta y el XBRL no separa: la parte de la D&A de las participadas (que el FFO no suma) y
    # la de los minoritarios (que el FFO no resta). Con participadas materiales, sin dato (decisión del 27-oct-2026);
    # por debajo, se avisa si pesan.
    jv = res.get("equity_method_income") or 0.0
    cons = res.get("consolidated_net_income")
    nci = (cons - net_income) if cons is not None else None
    out["equity_method_income"], out["minority_income"] = jv, nci
    if jv_material(jv, ffo):
        out["ffo"] = None
        out["ffo_reason"] = out["affo_reason"] = jv_reason(jv, ffo)
        out["jv_material"] = True
        return out
    material = cfg("data.reit_ffo.equity_method_material_share") * abs(ffo)
    parts = []
    if ffo and abs(jv) >= material:
        parts.append(f"participadas (resultado del periodo: {numfmt.money(jv)}; Nareit suma su parte de la D&A, así que "
                     "este FFO puede quedarse corto)")
    if ffo and nci is not None and abs(nci) >= material:
        parts.append(f"minoritarios (su parte del beneficio: {numfmt.money(nci)}; Nareit resta su parte de la D&A, así "
                     "que este FFO puede pasarse)")
    out["equity_method_warning"] = (("el XBRL no separa lo que Nareit ajusta de las " + " y de los ".join(parts)
                                     + ": el FFO que publica el emisor puede diferir") if parts else None)
    if not it[RECURRING_CAPEX]["lines"]:
        out["affo_reason"] = ("AFFO sin dato: el estado de flujos del emisor no separa el capex recurrente (mejoras de "
                              "inmuebles en explotación, comisiones y obras de inquilinos)")
        return out
    out["affo"] = ffo - it[STRAIGHT_LINE]["value"] - it[RECURRING_CAPEX]["value"]
    out["affo_formula"] = "AFFO = FFO − rentas lineales − capex recurrente"
    out["affo_formula_values"] = (f"{m(ffo)} − ({m(it[STRAIGHT_LINE]['value'])}) − ({m(it[RECURRING_CAPEX]['value'])}) "
                                  f"= {m(out['affo'])}")
    return out


def apply(ratios: Dict[str, Any], km: Dict[str, Any], d: Dict[str, Any], res: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Sustituye el FFO de `ratios` y `key_metrics` (BN + D&A) por el FFO según Nareit, con el P/FFO y el payout que
    salen de él, y añade el AFFO. Devuelve el bloque `reit_ffo` del análisis."""
    from financial_ratios import ffo_depreciation, ffo_payout_ratio, price_to_ffo, safe_div
    r = compute(d.get("net_income"), ffo_depreciation(d, ratios.get("ebitda")), res)
    shares, price = d.get("shares_outstanding"), d.get("price")
    ffo_ps = safe_div(r["ffo"], shares) if r["ffo"] is not None else None
    affo_ps = safe_div(r["affo"], shares) if r["affo"] is not None else None
    vals = {"ffo": r["ffo"], "ffo_per_share": ffo_ps, "p_ffo": price_to_ffo(price, ffo_ps),
            "ffo_payout": ffo_payout_ratio(d.get("dividends_paid"), r["ffo"])}
    ratios.update(vals)
    km.update({k: vals[k] for k in ("ffo", "p_ffo", "ffo_payout")})
    km.update(affo=r["affo"], p_affo=price_to_ffo(price, affo_ps))
    return dict(r, ffo_per_share=ffo_ps, affo_per_share=affo_ps)
