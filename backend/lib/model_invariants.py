"""
Modelo general: reglas de cordura sobre la salida del análisis de CUALQUIER empresa.

Cada regla mira el análisis (`a`, la salida de main._compute_analysis) y, si lo tiene, el contexto (`ctx`: el texto del
PDF y las capitalizaciones del universo por industria de Damodaran) y devuelve un `Result`:

    state       "ok" | "violacion" | "no_aplica" | "no_evaluable"
    reason      por qué no aplica o no se puede evaluar (None si se evaluó)
    violations  [{rule, magnitude, severity, detail, cause, values}]

`magnitude` mide cuánto se pasa (1 = justo en el umbral; acotada a invariants.max_magnitude) y `severity` es
peso × magnitud, para ordenar las más graves del universo. Umbrales y pesos: config/invariants.toml.

Estas reglas MIDEN: no cambian ninguna puntuación ni ninguna salida del motor. Distinto de tests/invariants.py, que son
los contratos de la salida (estructura, vocabulario, textos) y fallan la suite: aquí una violación es un hallazgo del
modelo, con su causa probable, para que el PM decida la corrección.

    import model_invariants as invariants
    res = invariants.evaluate(a, pdf_text=texto, universe=caps)    # {regla: Result}
"""
import json
import math
import os
import re
import statistics
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple

from settings import cfg

OK, VIOLATION, NOT_APPLICABLE, NOT_EVALUABLE = "ok", "violacion", "no_aplica", "no_evaluable"
LEVELS = {"baja": 0, "media": 1, "alta": 2}
EMPTY_STATES = ("no_aplica", "sin_dato", "no_significativo")
# Campos de un bloque del display que NO son su motivo (rótulos, cifras, tono); cualquier otro texto no genérico sí.
_NOT_REASON = {"key", "label", "title", "value", "value_txt", "state", "tone", "unit", "pill", "kicker", "kind",
               "subtitle", "delta", "gap", "format", "role", "method", "zone", "basis"}
_GENERIC_READINGS = re.compile(r"^(—|-|n/?a|no aplica|sin dato|no significativo|n\.s\.)\.?$", re.I)


def _coherence():
    """tests/coherence.py (F9 · R3), sin moverlo: lo usan los tests de F9 y otras ramas lo tocan."""
    here = os.path.dirname(os.path.abspath(__file__))
    tests = os.path.normpath(os.path.join(here, "..", "tests"))
    if tests not in sys.path:
        sys.path.append(tests)
    import coherence
    return coherence


def _C(rule: str) -> Dict[str, Any]:
    return cfg(f"invariants.{rule}")


def _num(x: Any) -> Optional[float]:
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        return None
    return float(x) if math.isfinite(x) else None


def _get(o: Any, *path, default=None):
    for k in path:
        if not isinstance(o, dict):
            return default
        o = o.get(k)
    return default if o is None else o


def _pct(x: Optional[float], d: int = 1) -> str:
    return "—" if x is None else f"{x * 100:.{d}f}%".replace("-", "−")


def _pp(x: Optional[float]) -> str:
    return "—" if x is None else f"{x * 100:+.1f} pp".replace("-", "−")


class Result(dict):
    """{state, reason, violations}: dict para que se serialice tal cual."""

    def __init__(self, state: str, reason: Optional[str] = None, violations: Optional[List[Dict[str, Any]]] = None):
        super().__init__(state=state, reason=reason, violations=violations or [])


def _violation(rule: str, magnitude: float, detail: str, cause: str, **values) -> Dict[str, Any]:
    cap = cfg("invariants.max_magnitude")
    m = max(1.0, min(cap, float(magnitude))) if math.isfinite(magnitude) else cap
    return {"rule": rule, "magnitude": round(m, 3), "severity": round(_C(rule)["weight"] * m, 3),
            "detail": detail, "cause": cause, "values": values}


def _result(rule: str, violations: List[Dict[str, Any]]) -> Result:
    return Result(VIOLATION if violations else OK, None, violations)


def _archetype(a: Dict[str, Any]) -> Optional[str]:
    return _get(a, "classification", "archetype")


def _adjustments(a: Dict[str, Any], category: Optional[str] = None) -> List[Dict[str, Any]]:
    bd = _get(a, "score", "breakdown", default={}) or {}
    cats = [category] if category else list(bd)
    return [x for c in cats for x in (_get(bd, c, "adjustments", default=[]) or [])]


def _display_rows(a: Dict[str, Any]) -> List[Dict[str, Any]]:
    S = _get(a, "display", "sections", default={}) or {}
    out = []
    for sec in ("valuation", "profitability", "solvency", "growth"):
        out += list(_get(S, sec, "rows", default=[]) or [])
    out += list(_get(S, "valuation", "intrinsic", "rows", default=[]) or [])
    return out


def _row(a: Dict[str, Any], key: str) -> Optional[Dict[str, Any]]:
    return next((r for r in _display_rows(a) if r.get("key") == key), None)


def _alerts(a: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
    al = a.get("alerts") or {}
    return [(k, x) for k in ("strengths", "warnings", "red_flags") for x in (al.get(k) or []) if isinstance(x, dict)]


# ═══════════════════════ 1. Margen neto frente a su techo operativo ═══════════════════════

def margen_neto_techo(a: Dict[str, Any], ctx: Dict[str, Any]) -> Result:
    """Margen neto ≤ (margen operativo + resultado financiero neto / ingresos) × (1 − t) + tolerancia. Se comprueban el
    margen que se enseña (reportado) y el que puntúa (normalizado, si la normalización entró en el score)."""
    rule, C = "margen_neto_techo", _C("margen_neto_techo")
    km = a.get("key_metrics") or {}
    if _archetype(a) == "FINANCIAL":
        return Result(NOT_APPLICABLE, "financiera: el margen operativo no aplica (los intereses son su negocio)")
    if "net_margin" in (_get(a, "display", "na_keys", default=[]) or []):
        return Result(NOT_APPLICABLE, "el margen neto no aplica a su tipo (ni puntúa ni se enseña)")
    rev, om = _num(km.get("revenue")), _num(km.get("operating_margin"))
    nm_rep, ni_norm = _num(km.get("net_margin")), _num(km.get("net_income_normalized"))
    if not rev or rev <= 0 or om is None or nm_rep is None:
        return Result(NOT_EVALUABLE, "sin ingresos, margen operativo o margen neto")
    t = _num(_get(a, "tax_rate", "rate"))
    t_src = "tipo efectivo" if t is not None else "tipo por defecto"
    if t is None:
        t = cfg("thresholds.normalization.default_tax_rate")
    t = max(0.0, min(1.0, t))
    nii = _num(km.get("net_interest_income"))
    en = a.get("earnings_normalization") or {}
    coh = en.get("coherence") or {}
    if _num(coh.get("operating_income")) is not None and _num(coh.get("revenue")):
        # F10 · N1: las piezas del mismo periodo que el beneficio; las participadas cuentan como operación (KO).
        crev = _num(coh["revenue"])
        fin = ((_num(coh.get("net_interest")) or 0.0) + (_num(coh.get("equity_income")) or 0.0)) / crev
        fin_src = "financieros netos + participadas (piezas de F10 · N1)"
        if _num(coh.get("tax_rate")) is not None:
            t, t_src = _num(coh["tax_rate"]), "tipo efectivo acotado (F10 · N1)"
    elif nii is not None:
        fin, fin_src = nii / rev, "resultado financiero neto de los estados"
    else:
        cash, rf = _num(km.get("cash")) or 0.0, _num(_get(a, "risk_free", "value")) or _num(_get(a, "wacc", "rf")) or 0.0
        fin, fin_src = max(0.0, cash * rf) / rev, "cota: caja × Rf (sin fila de resultado financiero)"
    scored = (ni_norm / rev) if (ni_norm is not None and en.get("used_in_score")) else nm_rep
    # El margen normalizado devuelve los cargos no recurrentes que quitó (antes de impuestos): si estaban en el resultado
    # operativo (un deterioro), su techo es el del operativo sin ellos. Cota generosa: todos los cargos devueltos.
    charges = -sum(_num(i.get("gross")) or 0.0 for i in en.get("items") or []
                   if isinstance(i, dict) and i.get("applied") and (_num(i.get("gross")) or 0.0) < 0)
    base = {"mostrado": (om + fin) * (1 - t), "puntuado": (om + charges / rev + fin) * (1 - t)}
    at = en.get("after_tax") or {}
    if _num(at.get("operating_income")) is not None and _num(at.get("revenue")):
        # F10 · N1b (alineado con normalize.after_tax): el operativo de la suma trimestral, los financieros netos y las
        # participadas, al tipo normalizado (mediana de los tipos efectivos), más los minoritarios; el que puntúa,
        # además con los cargos devueltos. El mismo techo que aplica la normalización.
        arev = _num(at["revenue"])
        om = _num(at["operating_income"]) / arev
        fin = ((_num(at.get("net_interest")) or 0.0) + (_num(at.get("equity_income")) or 0.0)) / arev
        mi = (_num(at.get("minority_interests")) or 0.0) / arev
        t = _num(at.get("tax_rate")) if _num(at.get("tax_rate")) is not None else t
        charges = (_num(at.get("charges_back")) or 0.0)
        fin_src = "financieros netos + participadas, minoritarios aparte (piezas de F10 · N1b, suma trimestral)"
        t_src = f"tipo normalizado (F10 · N1b: {at.get('tax_source')})"

        def _ceil(core):
            return (core * (1 - t) if core > 0 else core) + mi
        base = {"mostrado": _ceil(om + fin), "puntuado": _ceil(om + charges / arev + fin)}
        rev = arev
        if ni_norm is not None and en.get("used_in_score"):
            scored = ni_norm / arev     # el que puntúa, sobre los mismos ingresos que su techo (la normalización lo
            #                             corta justo ahí: sobre los ingresos de Yahoo quedaba una décima por encima)
        if _num(at.get("explained")) is not None and _num(at.get("tolerance")) is not None:
            # F10 · N1b final (decisión del PM, 29-oct: solo se recorta lo nombrable; el resto se declara en
            # `unexplained`): el techo es el de la propia normalización, explained + tolerancia, más lo declarado; si la
            # normalización no entra en el score, también lo que nombró sin recortarlo (`out`). Solo lo que pasa de ahí,
            # sin nombre ni declaración, es violación.
            used = bool(en.get("used_in_score")) and ni_norm is not None
            income = ni_norm if used else (nm_rep * arev)
            declared = (_num(at.get("unexplained")) or 0.0) + (0.0 if used else (_num(at.get("out")) or 0.0))
            ceiling_inc = _num(at["explained"]) + _num(at["tolerance"]) + declared
            undeclared = income - ceiling_inc
            if undeclared <= 1e-9 * max(1.0, abs(arev)):
                return Result(OK)
            which = "puntuado" if used else "mostrado"
            return _result(rule, [_violation(
                rule, (undeclared / arev) / C["tolerance_pp"],
                f"margen neto {which} {_pct(income / arev)} frente a un techo de {_pct(ceiling_inc / arev)} (el de la "
                f"normalización, F10 · N1b: explicado {_num(at['explained']) / 1e9:.2f}B + tolerancia "
                f"{_num(at['tolerance']) / 1e9:.2f}B + declarado sin nombre {declared / 1e9:.2f}B)",
                f"beneficio por encima de lo que explica la operación, sin partida que lo nombre y sin declarar: "
                f"≈ {undeclared / 1e9:.2f} B",
                net_margin_shown=nm_rep, net_margin_scored=income / arev, operating_margin=om, financial=fin, tax=t,
                ceiling=ceiling_inc / arev, excess_income=undeclared, declared=declared)])
    # Con la normalización aplicada (y dicha en el informe), el reportado se enseña marcado: se mide el que puntúa.
    marked = bool(en.get("used_in_score") and en.get("applied") and scored is not None and abs(scored - nm_rep) > 1e-9)
    cand = ([] if marked else [("mostrado", nm_rep)]) + (
        [("puntuado", scored)] if scored is not None and abs(scored - nm_rep) > 1e-9 else [])
    # (1e-9: el normalizado que N1b corta justo en su techo no es una violación por el redondeo; ARM, MKC, RDDT, RIO)
    over = [(w, v) for w, v in cand if v > base[w] + C["tolerance_pp"] + 1e-9]
    if not over:
        return Result(OK)
    which, v = max(over, key=lambda x: x[1] - base[x[0]])
    ceiling = base[which] + C["tolerance_pp"]
    excess = v - base[which]
    ni_excess = excess * rev
    norm = _num(en.get("one_off_net")) if en.get("used_in_score") else None
    cause = (f"beneficio no operativo que la normalización no quita (otros ingresos, ganancias de inversiones o partidas "
             f"fiscales): ≈ {ni_excess / 1e9:.2f} B por encima de lo que explica la operación"
             + (f"; la normalización solo quitó {norm / 1e9:.2f} B" if norm else ""))
    return _result(rule, [_violation(
        rule, excess / C["tolerance_pp"],
        f"margen neto {which} {_pct(v)} frente a un techo de {_pct(ceiling)} (operativo {_pct(om)}"
        + (f" + cargos devueltos {_pct(charges / rev)}" if which == "puntuado" and charges else "") + ", financiero "
        f"{_pct(fin)} [{fin_src}], t {_pct(t)} [{t_src}], tolerancia {C['tolerance_pp'] * 100:.0f} pp)",
        cause, net_margin_shown=nm_rep, net_margin_scored=scored, operating_margin=om, financial=fin, tax=t,
        ceiling=ceiling, excess_income=ni_excess)])


# ═══════════════════════ 1b. Una sola verdad para el margen operativo ═══════════════════════

def margen_operativo_unico(a: Dict[str, Any], ctx: Dict[str, Any]) -> Result:
    """El margen operativo que se enseña y puntúa (key_metrics: el de EDGAR, us-gaap:OperatingIncomeLoss en TTM = FY +
    acumulado − acumulado del año anterior; sin TTM trimestral, el operatingIncome de quoteSummary; lo dice
    `data_provenance.fields.operatingIncome`) frente al de las piezas con que la normalización mide el beneficio (F10 ·
    N1/N1b: la fila trimestral «Operating Income» de Yahoo, sumada en 4 trimestres). Más de `tolerance_pp` de diferencia
    es una cifra con dos verdades (FIX: 7,9 % de EDGAR frente a 16,7 % de Yahoo; el bueno, 16,7 %: docs/modelo/
    VERIF_MARGEN_OPERATIVO_2026-10-29.md). Dice si el margen enseñado puntúa (Rentabilidad)."""
    rule, C = "margen_operativo_unico", _C("margen_operativo_unico")
    if _archetype(a) == "FINANCIAL":
        return Result(NOT_APPLICABLE, "financiera: el margen operativo no aplica")
    if "operating_margin" in (_get(a, "display", "na_keys", default=[]) or []):
        return Result(NOT_APPLICABLE, "el margen operativo no aplica a su tipo")
    shown = _num((a.get("key_metrics") or {}).get("operating_margin"))
    en = a.get("earnings_normalization") or {}
    src = next((p for p in (en.get("after_tax"), en.get("coherence"))
                if p and _num(p.get("operating_income")) is not None and _num(p.get("revenue"))), None)
    if shown is None or src is None:
        return Result(NOT_EVALUABLE, "sin margen operativo enseñado o sin las piezas trimestrales de Yahoo")
    pieces = _num(src["operating_income"]) / _num(src["revenue"])
    gap = abs(shown - pieces)
    _prov = (_get(a, "data_provenance", "fields", "operatingIncome", default={}) or {}).get("source")
    shown_src = ("EDGAR, TTM" if _prov == "sec_edgar" else "Yahoo, quoteSummary" if _prov else "fuente sin dato")
    if gap <= C["tolerance_pp"]:
        return Result(OK)
    row = next((x for x in _get(a, "score", "breakdown", "Rentabilidad", "adjustments", default=[]) or []
                if str(x.get("metric") or "").startswith("Margen operativo")), None)
    scores = bool(row) and row.get("adjustment") not in (None, 0) and "No aplica" not in str(row.get("value"))
    return _result(rule, [_violation(
        rule, gap / C["tolerance_pp"],
        f"margen operativo enseñado {_pct(shown)} ({shown_src}) frente a {_pct(pieces)} de las piezas de la "
        f"normalización (Yahoo, suma de 4 trimestres) "
        f"({gap * 100:.1f} pp > {C['tolerance_pp'] * 100:.0f} pp)"
        + (f"; puntúa en Rentabilidad ({row.get('adjustment'):+})" if scores else "; no puntúa"),
        "dos fuentes del mismo margen y periodo: el que se enseña (y puntúa) no es el que usa la normalización",
        shown=shown, shown_source=_prov, pieces=pieces, gap=gap, scores=scores)])


def ebitda_sin_amortizacion_operativa(a: Dict[str, Any], ctx: Dict[str, Any]) -> Result:
    """Escalera de márgenes de NFLX (PM, 30-oct): el D&A del EBITDA no lleva amortizaciones de activos operativos
    recurrentes (contenido, software capitalizado). La regla (lib/edgar_primary._da_reconcile) compara la amortización de
    intangibles de la fuente con su respaldo en EDGAR (intangibles adquiridos) y quita lo que no tiene respaldo por encima
    de la materialidad de N1 (`thresholds.normalization.nonoperating_tolerance_revenue`). Violación: una amortización
    sin respaldo, medida contra EDGAR, por encima de esa materialidad, que sigue en el EBITDA. Lo que EDGAR no permite
    verificar (sin etiquetas) se declara y no es violación."""
    rule = "ebitda_sin_amortizacion_operativa"
    if _archetype(a) == "FINANCIAL":
        return Result(NOT_APPLICABLE, "financiera: el EBITDA no aplica")
    da = _get(a, "data_provenance", "edgar", "primary", "da", default=None)
    if not da:
        return Result(NOT_EVALUABLE, "sin el desglose del D&A de la fuente (o sin EDGAR)")
    rev = _num((a.get("key_metrics") or {}).get("revenue"))
    left, support = _num(da.get("unsupported")), _num(da.get("support"))
    mat = cfg("thresholds.normalization.nonoperating_tolerance_revenue")
    if da.get("status") != "no_verificable" or support is None or not rev or left is None or left <= mat * abs(rev):
        return Result(OK)
    return _result(rule, [_violation(
        rule, left / (mat * abs(rev)),
        f"amortización de intangibles sin respaldo en EDGAR de {_pct(left / abs(rev))} de los ingresos (> "
        f"{mat:.0%}) dentro del D&A del EBITDA",
        "amortización de activos operativos recurrentes sumada al EBITDA: infla el margen EBITDA y abarata el EV/EBITDA",
        unsupported=left, support=support, revenue=rev)])


# ═══════════════════════ 2. Ke frente a Kd ═══════════════════════

def ke_sobre_kd(a: Dict[str, Any], ctx: Dict[str, Any]) -> Result:
    rule, C = "ke_sobre_kd", _C("ke_sobre_kd")
    coe, w = a.get("cost_of_equity") or {}, a.get("wacc") or {}
    ke = _num(coe.get("value")) if coe.get("value") is not None else _num(w.get("ke"))
    kd = _num(coe.get("kd")) if coe.get("kd") is not None else _num(w.get("kd"))
    if ke is None:
        return Result(NOT_EVALUABLE, "sin coste del equity")
    if kd is None:
        return Result(NOT_APPLICABLE, "sin coste de la deuda (sin deuda o sin rating sintético)")
    if ke >= kd + C["min_gap"] - 1e-9:
        return Result(OK)
    gap = ke - kd
    return _result(rule, [_violation(
        rule, (C["min_gap"] - gap) / C["min_gap"],
        f"Ke {_pct(ke, 2)} frente a Kd {_pct(kd, 2)}: diferencia {_pp(gap)} (< {C['min_gap'] * 100:.0f} pp)",
        "el suelo «Kd + 1 pp» del coste del equity no se aplicó (o el Kd que lo fija no es el del WACC)",
        ke=ke, kd=kd)])


# ═══════════════════════ 3. Beta en rango o sustituida ═══════════════════════

def beta_en_rango(a: Dict[str, Any], ctx: Dict[str, Any]) -> Result:
    rule, C = "beta_en_rango", _C("beta_en_rango")
    b, km, w = a.get("beta") or {}, a.get("key_metrics") or {}, a.get("wacc") or {}
    used = _num(w.get("beta")) if w.get("beta") is not None else _num(km.get("beta_ke"))
    if used is None:
        used = _num(b.get("adjusted"))
    if used is None:
        return Result(NOT_EVALUABLE, "sin beta en el coste del equity")
    out = []
    if b.get("source") == "propia":
        F = cfg("market.beta_choice")
        own = b.get("own") or {}
        raw, r2, se = _num(own.get("raw")), _num(own.get("r2")), _num(own.get("se"))
        fails = []
        if raw is None or not (F["own_range"][0] <= raw <= F["own_range"][1]):
            fails.append(f"beta bruta {raw} fuera de {list(F['own_range'])}")
        if r2 is None or r2 < F["min_r2"]:
            fails.append(f"R² {r2} < {F['min_r2']}")
        if se is None or se > F["max_se"]:
            fails.append(f"error estándar {se} > {F['max_se']}")
        if fails:
            out.append(_violation(rule, 1 + len(fails), "beta propia que no pasa los filtros del motor: " + "; ".join(fails),
                                  "la elección de la beta (lib/beta.py) usó la propia sin sustituirla", used=used))
    elif not b.get("reason"):
        out.append(_violation(rule, 1, f"beta sustituta ({b.get('source')}) sin motivo declarado",
                              "la beta de abajo hacia arriba o del sector no dice por qué sustituye a la propia",
                              used=used))
    lo, hi = C["used_range"]
    if not (lo <= used <= hi):
        dist = (lo - used) if used < lo else (used - hi)
        out.append(_violation(
            rule, 1 + dist / 0.1, f"beta usada en el Ke {used:.2f} fuera de [{lo}, {hi}] (origen: {b.get('source')})",
            ("beta del sector o de abajo hacia arriba fuera del rango que el motor exige a la propia: el Ke depende del "
             "suelo, no del riesgo medido" if b.get("source") != "propia" else
             "beta propia extrema que pasó los filtros"), used=used, source=b.get("source")))
    return _result(rule, out)


# ═══════════════════════ 4. g terminal ≤ Rf ═══════════════════════

def g_terminal_bajo_rf(a: Dict[str, Any], ctx: Dict[str, Any]) -> Result:
    rule, C = "g_terminal_bajo_rf", _C("g_terminal_bajo_rf")
    d = a.get("dcf") or {}
    g = _num(d.get("terminal_growth"))
    if not d.get("available") or g is None:
        return Result(NOT_APPLICABLE, "sin DCF directo")
    rf = _num(_get(a, "wacc", "rf")) or _num(_get(a, "risk_free", "value"))
    if rf is None:
        return Result(NOT_EVALUABLE, "sin tasa libre de riesgo")
    if g <= rf + C["tolerance"]:
        return Result(OK)
    return _result(rule, [_violation(rule, 1 + (g - rf) / 0.005, f"g terminal {_pct(g, 2)} > Rf {_pct(rf, 2)}",
                                     "el crecimiento perpetuo supera al de la economía nominal sin riesgo", g=g, rf=rf)])


# ═══════════════════════ 5. Capitalización = precio × acciones ═══════════════════════

def capitalizacion(a: Dict[str, Any], ctx: Dict[str, Any]) -> Result:
    rule, C = "capitalizacion", _C("capitalizacion")
    km = a.get("key_metrics") or {}
    mc, price, sh = _num(km.get("market_cap")), _num(a.get("price")), _num(km.get("shares_outstanding"))
    if not mc or not price or not sh:
        return Result(NOT_EVALUABLE, "sin capitalización, precio o acciones")
    out = []
    dev = mc / (price * sh) - 1
    if abs(dev) > C["tolerance"]:
        out.append(_violation(
            rule, abs(dev) / C["tolerance"],
            f"capitalización {mc / 1e9:.2f} B frente a precio × acciones {price * sh / 1e9:.2f} B ({dev:+.1%})",
            "acciones de otra clase o de otra fecha, factor del ADR o moneda del precio distinta de la de las acciones",
            market_cap=mc, price=price, shares=sh, deviation=dev))
    pmc = _num(_get(a, "profile", "market_cap"))
    if pmc and abs(pmc / mc - 1) > C["tolerance"]:
        out.append(_violation(rule, abs(pmc / mc - 1) / C["tolerance"],
                              f"capitalización del perfil {pmc / 1e9:.2f} B frente a la de las métricas {mc / 1e9:.2f} B",
                              "dos fuentes de capitalización en el mismo informe", profile=pmc, key_metrics=mc))
    return _result(rule, out)


# ═══════════════════════ 6. ROE n.s. con patrimonio ≤ 0 ═══════════════════════

def roe_patrimonio_negativo(a: Dict[str, Any], ctx: Dict[str, Any]) -> Result:
    rule = "roe_patrimonio_negativo"
    te = _num(_get(a, "key_metrics", "total_equity"))
    if te is None:
        return Result(NOT_EVALUABLE, "sin patrimonio")
    if te > 0:
        return Result(NOT_APPLICABLE, "patrimonio positivo")
    out = []
    for x in _adjustments(a, "Rentabilidad"):
        m = str(x.get("metric") or "")
        if m.startswith("ROE") and (x.get("adjustment") or 0) != 0:
            out.append(_violation(rule, 2, f"«{m}» puntúa {x['adjustment']:+d} con patrimonio {te / 1e9:.2f} B",
                                  "el ROE sobre un patrimonio ≤ 0 no tiene sentido (signo invertido o recompras) y "
                                  "debería salir n.s.", equity=te, value=x.get("value")))
    r = _row(a, "roe")
    coh = _coherence()
    if r and r.get("state") == "con_dato" and coh.parse(r.get("value")):
        out.append(_violation(rule, 1, f"ROE mostrado como cifra ({r['value']}) con patrimonio {te / 1e9:.2f} B",
                              "la fila del ROE no se marca no significativa", equity=te, shown=r.get("value")))
    return _result(rule, out)


# ═══════════════════════ 7. PEG n.s. con crecimiento ≤ 0 ═══════════════════════

def peg_crecimiento_no_positivo(a: Dict[str, Any], ctx: Dict[str, Any]) -> Result:
    rule = "peg_crecimiento_no_positivo"
    scored = [x for x in _adjustments(a, "Valoración") if x.get("metric") == "PEG"]
    shown = _row(a, "peg")
    if not scored and not (shown and shown.get("state") == "con_dato"):
        return Result(NOT_APPLICABLE, "sin PEG que puntúe o se enseñe")
    g = _num(_get(a, "peg_basis", "eps_cagr_3y"))
    if g is None:
        for x in _adjustments(a, "Crecimiento"):
            if str(x.get("metric") or "").startswith("Crecimiento del BPA") and _num(x.get("raw")) is not None:
                g = _num(x.get("raw"))
    if g is None:
        return Result(NOT_EVALUABLE, "sin crecimiento del BPA en el informe")
    if g > 0:
        return Result(NOT_APPLICABLE, "crecimiento del BPA positivo")
    out = []
    for x in _adjustments(a, "Valoración"):
        if x.get("metric") == "PEG" and not str(x.get("value") or "").lower().startswith("no "):
            out.append(_violation(rule, 2, f"PEG {x.get('value')} puntúa ({x.get('adjustment'):+d}) con el BPA del "
                                           f"informe en {_pct(g)}",
                                  "el PEG de la fuente supone un crecimiento que el informe no ve", growth=g))
    r = _row(a, "peg")
    if r and r.get("state") == "con_dato" and _coherence().parse(r.get("value")):
        out.append(_violation(rule, 1, f"PEG mostrado ({r['value']}) con el BPA del informe en {_pct(g)}",
                              "la fila del PEG no se marca no significativa", growth=g, shown=r.get("value")))
    return _result(rule, out)


# ═══════════════════════ 8. Una sola cifra por métrica ═══════════════════════

def cifra_unica(a: Dict[str, Any], ctx: Dict[str, Any]) -> Result:
    rule, C = "cifra_unica", _C("cifra_unica")
    if "display" not in a:
        return Result(NOT_EVALUABLE, "sin display")
    coh = _coherence()
    out = []
    for x, y in coh.conflicts(coh.display_figures(a)):
        rel = abs(x[3] - y[3]) / max(abs(x[3]), abs(y[3]), 1e-12)
        out.append(_violation(rule, 1 + 10 * rel, f"{x[0]} ({x[2]}): {x[3]:g} en {x[5]} frente a {y[3]:g} en {y[5]}",
                              "dos cálculos o dos redondeos de la misma cifra en el display", metric=x[0]))
    text = ctx.get("pdf_text")
    for lab, unit, val, near in (coh.pdf_conflicts(text, a) if text else []):
        out.append(_violation(rule, 2, f"PDF: «{lab}» {near} frente a {val:g}{unit} en el display",
                              "el PDF imprime otra cifra que la web", metric=lab))
    res = _result(rule, out[:C["max_listed"]])
    res["count"] = len(out)
    if not text:
        res["reason"] = "solo el display (sin texto del PDF)"
    return res


# ═══════════════════════ 9. Peso de la empresa en su referencia de industria ═══════════════════════

def peso_en_referencia(a: Dict[str, Any], ctx: Dict[str, Any]) -> Result:
    """Con `ctx["universe"]`: {"firm": {símbolo: (industria, región)}, "caps": {(industria, región): suma}}. La suma es la
    de las empresas del universo (S&P 500 + ADR) en esa industria de Damodaran: menor que la de Damodaran, así que el
    peso es una COTA SUPERIOR (se declara)."""
    rule, C = "peso_en_referencia", _C("peso_en_referencia")
    U = ctx.get("universe")
    bi = _get(a, "benchmark", "industry", default={}) or {}
    if _get(a, "benchmark", "profile") == "market" or bi.get("basis") not in ("industria", "industria_global"):
        return Result(NOT_APPLICABLE, f"la referencia no es el agregado de una industria ({bi.get('basis') or 'sin industria'})")
    # F10 · N2: la salida dice si la referencia ya es el agregado sin la empresa (o la mediana de sus pares) y con qué
    # peso, medido con las cifras de Damodaran: eso manda sobre la cota del universo.
    se = bi.get("self_exclusion") or {}
    if se.get("method") in ("sin_empresa", "mediana_pares"):
        return Result(OK, f"la referencia no la incluye ({se['method']}; pesa "
                          f"{'—' if se.get('weight') is None else format(se['weight'], '.0%')} del agregado)")
    if se.get("method") == "no_figura":
        return Result(NOT_APPLICABLE, "Damodaran no la cuenta en el agregado de la referencia")
    if not U:
        return Result(NOT_EVALUABLE, "sin las capitalizaciones del universo por industria")
    sym = a.get("symbol")
    f = U["firm"].get(sym)
    mc = _num(_get(a, "key_metrics", "market_cap"))
    if not f or not mc:
        return Result(NOT_EVALUABLE, "la empresa no figura en el universo o sin capitalización")
    ind = bi.get("damodaran")
    reg = bi.get("region") if bi.get("basis") == "industria" else "global"
    if f[0] != ind:
        return Result(NOT_APPLICABLE, f"Damodaran la clasifica en {f[0]}, no en la industria de la referencia ({ind})")
    total = U["caps"].get((ind, reg)) if reg != "global" else sum(v for (i, _), v in U["caps"].items() if i == ind)
    n = (U.get("counts") or {}).get((ind, reg)) if reg != "global" else sum(
        v for (i, _), v in (U.get("counts") or {}).items() if i == ind)
    if not total:
        return Result(NOT_EVALUABLE, f"sin capitalizaciones de {ind} en el universo")
    if n is not None and n < C["min_universe_peers"]:
        return Result(NOT_EVALUABLE, f"solo {n} empresa(s) del universo en {ind} ({reg}): la cota no informa")
    share = mc / max(total, mc)
    if share <= C["max_share"]:
        return Result(OK)
    return _result(rule, [_violation(
        rule, share / C["max_share"],
        f"pesa hasta un {share:.0%} del agregado de {ind} ({reg}) con el que se compara (cota superior: suma de las "
        f"{U.get('counts', {}).get((ind, reg), '¿?')} empresas del universo en esa industria)",
        "la referencia de industria es en buena parte la propia empresa: la brecha frente a la industria (P/E, "
        "EV/EBITDA, márgenes) se mide contra sí misma", share=share, industry=ind, region=reg, market_cap=mc,
        universe_total=total)])


# ═══════════════════════ 10. Crecimiento robusto ═══════════════════════

def _anomalous_base(series: List[Optional[float]]) -> Optional[float]:
    """Base / mediana del resto si el año base es anómalo según el motor (thresholds.growth.anomalous_base_ratio)."""
    if len(series) < 2 or any(v is None for v in series):
        return None
    start, rest = series[0], [v for v in series[1:]]
    med = statistics.median(rest)
    if start is None or start <= 0 or med <= 0:
        return None
    r = start / med
    return r if r < cfg("thresholds.growth.anomalous_base_ratio") else None


def crecimiento_robusto(a: Dict[str, Any], ctx: Dict[str, Any]) -> Result:
    rule, C = "crecimiento_robusto", _C("crecimiento_robusto")
    gb = a.get("growth_basis") or {}
    out = []
    for key, what in (("revenue_cagr", "ingresos"), ("fcf_cagr", "FCF")):
        m = gb.get(key) or {}
        if m.get("anomalous_base") and m.get("method") == "cagr":
            out.append(_violation(rule, 2, f"crecimiento de {what} por CAGR con el año base marcado anómalo",
                                  "el método robusto no se aplicó aunque el motor marcó la base", series=what))
    win = re.match(r"FY(\d{4})\D+FY(\d{4})", str(gb.get("revenue_window") or ""))
    # El año base es anómalo para el BPA si lo es su beneficio (la regla del motor, aplicada al beneficio neto de la
    # ventana). La marca del informe en los ingresos o el FCF es contexto: no hace anómalo al BPA (un banco con los
    # ingresos brutos inflados por los tipos, FITB, no tiene el beneficio en un valle).
    marked = [w for k, w in (("revenue_cagr", "ingresos"), ("fcf_cagr", "FCF")) if (gb.get(k) or {}).get("anomalous_base")]
    ratio = None
    if win:
        y0, y1 = int(win.group(1)), int(win.group(2))
        by = {y.get("year"): y for y in a.get("yearly_financials") or [] if isinstance(y, dict)}
        ni = [_num((by.get(y) or {}).get("net_income")) for y in range(y0, y1 + 1)]
        ratio = _anomalous_base(ni)
    if ratio is None:
        return _result(rule, out) if out else Result(OK)
    robust = re.compile("|".join(re.escape(x) for x in C["robust_markers"]), re.I)
    # F10 · crecimiento desde una base anómala: el método del BPA publicado (growth_basis.eps_cagr). Robusto = sin base
    # anómala en el propio BPA o con la regresión de la serie larga de EDGAR.
    eps_robust = (gb.get("eps_cagr") or {}).get("robust") is True
    why = ", ".join(filter(None, [f"el informe marca la base de {' y '.join(marked)}" if marked else "",
                                  f"el beneficio del año base es el {ratio:.0%} de la mediana del resto" if ratio else ""]))
    for x in _adjustments(a, "Crecimiento"):
        m = str(x.get("metric") or "")
        if m.startswith("Crecimiento del BPA") and _num(x.get("raw")) is not None and not eps_robust \
                and not robust.search(str(x.get("reason") or "")):
            out.append(_violation(rule, 2 + min(3.0, abs(_num(x.get("raw")) or 0)),
                                  f"«{m}» {x.get('value')} puntúa {x.get('adjustment'):+d} con un CAGR desde "
                                  f"{gb.get('revenue_window', '').split('–')[0]} ({why})",
                                  "el BPA no usa el método robusto que ya usan los ingresos", growth=_num(x.get("raw"))))
    peg_g = _num(_get(a, "peg_basis", "eps_cagr_3y"))
    for x in _adjustments(a, "Valoración"):
        if x.get("metric") == "PEG" and peg_g is not None and (x.get("adjustment") or 0) != 0 and not eps_robust:
            out.append(_violation(rule, 2, f"PEG {x.get('value')} puntúa {x['adjustment']:+d} sobre un crecimiento del BPA "
                                           f"de {_pct(peg_g)} desde la base anómala ({why})",
                                  "el PEG hereda el CAGR del BPA desde un año valle", growth=peg_g))
    return _result(rule, out)


# ═══════════════════════ 11. Alertas coherentes con las cifras ═══════════════════════

_NUM_IN_TEXT = re.compile(r"([+\-−]?\d[\d,]*(?:\.\d+)?)\s?(%|x|pp)?")


def _alert_key(text: str) -> Optional[str]:
    t = text.lower()
    if any(m in t for m in _C("alertas_coherentes")["other_basis_markers"]):
        return None
    for pat, key in _C("alertas_coherentes")["labels"]:
        if re.search(pat, t):
            return key
    return None


def alertas_coherentes(a: Dict[str, Any], ctx: Dict[str, Any]) -> Result:
    rule = "alertas_coherentes"
    if "display" not in a:
        return Result(NOT_EVALUABLE, "sin display")
    coh = _coherence()
    figs: Dict[str, List[Tuple[float, str, float]]] = {}
    for f in coh.display_figures(a):
        if f[2] == "corte":
            figs.setdefault(f[0], []).append((f[3], f[1], f[4]))
    out = []
    for kind, x in _alerts(a):
        reason = str(x.get("reason") or "")
        label, _, tail = reason.partition(" — ")
        key = _alert_key(label) or _alert_key(tail)
        if not key:
            continue
        m = _NUM_IN_TEXT.search(tail) if tail else None
        if m and key in figs:
            s = m.group(1).replace("−", "-").replace(",", "")
            unit = m.group(2) or ""
            dec = len(s.split(".")[1]) if "." in s else 0
            v, tol = float(s), 0.5 * 10 ** -dec
            same = [f for f in figs[key] if f[1] == unit or (unit == "" and f[1] in ("", "x"))]
            if same and not any(abs(v - f[0]) <= tol + f[2] + 1e-9 for f in same):
                out.append(_violation(rule, 2, f"{kind}: «{reason}» frente a {key} = "
                                               f"{', '.join(sorted({f'{f[0]:g}{f[1]}' for f in same}))} en el display",
                                      "la alerta se calculó con otra cifra (otro periodo, otra base o antes de un ajuste)",
                                      key=key, alert=v))
        r = _row(a, key)
        if r and r.get("state") == "con_dato":
            bad = (kind == "strengths" and r.get("tone") == "neg") or (kind != "strengths" and r.get("tone") == "pos")
            if bad:
                out.append(_violation(rule, 1, f"{kind}: «{reason}» con la fila {key} en tono {r.get('tone')} "
                                               f"({r.get('reading')})",
                                      "la alerta y la lectura de la fila usan umbrales o referencias distintos",
                                      key=key, tone=r.get("tone")))
    return _result(rule, out)


# ═══════════════════════ 12. Una sola beta ═══════════════════════

def beta_unica(a: Dict[str, Any], ctx: Dict[str, Any]) -> Result:
    rule, C = "beta_unica", _C("beta_unica")
    km, w = a.get("key_metrics") or {}, a.get("wacc") or {}
    layers = {"wacc": _num(w.get("beta")) if w.get("applicable") is not False else None,
              "ke": _num(km.get("beta_ke")), "beta.adjusted": _num(_get(a, "beta", "adjusted")),
              "p/b justificado": _num(_get(a, "archetype_metrics", "beta_adjusted"))}
    layers = {k: v for k, v in layers.items() if v is not None}
    if not layers:
        return Result(NOT_EVALUABLE, "sin beta en el cálculo")
    out = []
    lo, hi = min(layers.values()), max(layers.values())
    if hi - lo > C["tolerance"]:
        out.append(_violation(rule, 1 + (hi - lo) / 0.05, "betas distintas en el cálculo: "
                              + ", ".join(f"{k} {v:.3f}" for k, v in layers.items()),
                              "cada capa toma la beta de un sitio (bruta, ajustada o de otra fuente)", **layers))
    used = layers.get("ke", lo)
    shown = []
    if "display" in a:
        shown += [(f[3], f[4], f[5]) for f in _coherence().display_figures(a) if f[0] == "beta"]
    for kind, x in _alerts(a):
        m = re.search(r"\bbeta\s+([\d.]+)", str(x.get("reason") or ""), re.I)
        if m:
            s = m.group(1).rstrip(".")
            dec = len(s.split(".")[1]) if "." in s else 0
            shown.append((float(s), 0.5 * 10 ** -dec, f"alerta: {x.get('reason')}"))
    for v, tol, where in shown:
        if abs(v - used) > tol + C["tolerance"]:
            out.append(_violation(rule, 1 + abs(v - used) / 0.05, f"beta {v:g} en {where} frente a {used:.3f} en el Ke",
                                  "el informe enseña una beta (la bruta o la del proveedor) y calcula con otra",
                                  shown=v, used=used))
    return _result(rule, out)


# ═══════════════════════ 13. Estados al día o marcados ═══════════════════════

def estados_al_dia(a: Dict[str, Any], ctx: Dict[str, Any]) -> Result:
    rule, C = "estados_al_dia", _C("estados_al_dia")
    dp = a.get("data_provenance") or {}
    st, ao = dp.get("staleness") or {}, dp.get("as_of") or {}
    days = _num(st.get("days_since_cut"))
    if days is None and ao.get("date") and ctx.get("today"):
        import datetime as _dt
        days = (_dt.date.fromisoformat(ctx["today"]) - _dt.date.fromisoformat(ao["date"][:10])).days
    limit = C["max_days_fy"] if ao.get("type") == "fy" else C["max_days_ttm"]
    mark = st.get("text")
    blob = json.dumps(a.get("display") or {}, ensure_ascii=False)
    visible = bool(mark) and (mark in blob or "desfasad" in blob.lower() or "desfasad" in (ctx.get("pdf_text") or "").lower())
    out = []
    if st.get("status") == "desfasado" and not visible:
        out.append(_violation(rule, 2, f"estados desfasados ({days} días; la SEC ya tiene "
                                       f"{_get(st, 'edgar_latest', 'form')}) sin la marca en el informe",
                              "la marca de frescura no llega al display", days=days))
    if days is not None and days > limit and not visible:
        out.append(_violation(rule, days / limit, f"cifras de hace {days:.0f} días (corte {ao.get('date')}, "
                                                  f"{ao.get('type')}; límite {limit}) sin marca de antigüedad "
                                                  f"(frescura: {st.get('status')})",
                              "la fuente no trae el último periodo y EDGAR no lo detecta (sin CIK, 6-K sin XBRL o sin "
                              "filings)", days=days, status=st.get("status")))
    if not (days is not None or st.get("status")):
        return Result(NOT_EVALUABLE, "sin fecha de corte")
    return _result(rule, out)


# ═══════════════════════ 14. Confianza ≤ cobertura ═══════════════════════

def confianza_cobertura(a: Dict[str, Any], ctx: Dict[str, Any]) -> Result:
    rule = "confianza_cobertura"
    conf = a.get("confidence") or {}
    lvl = conf.get("level")
    cov_lvl = _get(conf, "dimensions", "coverage", "level")
    cov_val = _num(_get(conf, "dimensions", "coverage", "coverage"))
    if cov_lvl is None:
        sc = a.get("score_coverage") or {}
        n = sum((c or {}).get("components") or 0 for c in sc.values())
        ev = sum((c or {}).get("evaluated") or 0 for c in sc.values())
        if n:
            cov_val = ev / n
            b = cfg("thresholds.confidence.coverage_bounds")
            cov_lvl = "alta" if cov_val >= b[0] else "media" if cov_val >= b[1] else "baja"
    if lvl not in LEVELS or cov_lvl not in LEVELS:
        return Result(NOT_EVALUABLE, "sin nivel de confianza o de cobertura")
    if LEVELS[lvl] <= LEVELS[cov_lvl]:
        return Result(OK)
    return _result(rule, [_violation(rule, 1 + LEVELS[lvl] - LEVELS[cov_lvl],
                                     f"confianza {lvl} con cobertura {cov_lvl} ({_pct(cov_val, 0)} de los componentes)",
                                     "la confianza es una media ponderada: convergencia, fuente y estabilidad compensan "
                                     "la cobertura (no hay techo por cobertura)", confidence=lvl, coverage=cov_lvl)])


# ═══════════════════════ 15. Cada vacío con su motivo ═══════════════════════

def _has_reason(d: Dict[str, Any], n: int) -> bool:
    """Algún texto del bloque que no sea un rótulo, una cifra ni una lectura genérica («No aplica», «—»)."""
    coh = _coherence()
    for k, v in d.items():
        if k in _NOT_REASON or not isinstance(v, str):
            continue
        v = v.strip()
        if len(v) >= n and not _GENERIC_READINGS.match(v) and coh.parse(v) is None:
            return True
    return False


def motivo_de_vacio(a: Dict[str, Any], ctx: Dict[str, Any]) -> Result:
    rule, C = "motivo_de_vacio", _C("motivo_de_vacio")
    n = C["min_reason_chars"]
    out = []
    for cat, c in (a.get("score_coverage") or {}).items():
        c = c or {}
        for name in c.get("missing") or []:
            if not (c.get("missing_reasons") or {}).get(name):
                out.append(_violation(rule, 1, f"{cat}: «{name}» sin dato y sin motivo",
                                      "el componente no recibe motivo al registrarse en la cobertura",
                                      category=cat, component=name))
        for kind in ("not_applicable", "not_significant"):
            for name, why in (c.get(kind) or {}).items():
                if not isinstance(why, str) or len(why.strip()) < n:
                    out.append(_violation(rule, 1, f"{cat}: «{name}» {kind} sin motivo", "motivo vacío",
                                          category=cat, component=name))

    def walk(o, p):
        if isinstance(o, dict):
            if o.get("state") in EMPTY_STATES and not _has_reason(o, n):
                out.append(_violation(rule, 1, f"{p or 'display'}: {o.get('key') or o.get('label') or ''} "
                                               f"«{o.get('state')}» sin motivo",
                                      "el bloque del display sale vacío sin decir por qué", path=p))
            for k, v in o.items():
                walk(v, f"{p}.{k}" if p else k)
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f"{p}[{i}]")
    walk(a.get("display") or {}, "")
    res = _result(rule, out[:C["max_listed"]])
    res["count"] = len(out)
    # Por campo (todos, no solo los listados): «score · Valoración · P/FCF» o «display · summary.cards[] · roe».
    fields: Dict[str, int] = {}
    for v in out:
        x = v["values"]
        path = re.sub(r"\[\d+\]", "[]", x.get("path") or "")
        k = (f"score · {x['category']} · {x['component']}" if "component" in x else
             f"display · {path} · " + v["detail"].split(": ", 1)[-1].split(" «")[0].strip())
        fields[k] = fields.get(k, 0) + 1
    res["fields"] = fields
    return res


RULES: Dict[str, Tuple[Callable[[Dict[str, Any], Dict[str, Any]], Result], str]] = {
    "margen_neto_techo": (margen_neto_techo, "Margen neto ≤ (operativo + financiero neto) × (1 − t) + tolerancia"),
    "margen_operativo_unico": (margen_operativo_unico, "Margen operativo: el enseñado (EDGAR TTM) frente a las piezas "
                                                       "de la normalización (Yahoo trimestral) ± 3 pp"),
    "ebitda_sin_amortizacion_operativa": (ebitda_sin_amortizacion_operativa, "El D&A del EBITDA sin amortizaciones "
                                                                             "de activos operativos recurrentes"),
    "ke_sobre_kd": (ke_sobre_kd, "Ke ≥ Kd + 1 pp"),
    "beta_en_rango": (beta_en_rango, "Beta en rango o sustituida"),
    "g_terminal_bajo_rf": (g_terminal_bajo_rf, "g terminal ≤ Rf"),
    "capitalizacion": (capitalizacion, "Capitalización = precio × acciones ± 2 %"),
    "roe_patrimonio_negativo": (roe_patrimonio_negativo, "ROE n.s. si el patrimonio ≤ 0"),
    "peg_crecimiento_no_positivo": (peg_crecimiento_no_positivo, "PEG n.s. si el crecimiento del BPA ≤ 0"),
    "cifra_unica": (cifra_unica, "Una sola cifra por métrica en display y PDF"),
    "peso_en_referencia": (peso_en_referencia, "La empresa no pesa más de X % en su referencia de industria"),
    "crecimiento_robusto": (crecimiento_robusto, "El crecimiento puntuado no es un CAGR desde un año anómalo"),
    "alertas_coherentes": (alertas_coherentes, "Ninguna fortaleza o alerta contradice una cifra mostrada"),
    "beta_unica": (beta_unica, "Una misma beta en todas las capas"),
    "estados_al_dia": (estados_al_dia, "Estados no desfasados sin marca"),
    "confianza_cobertura": (confianza_cobertura, "Confianza ≤ cobertura"),
    "motivo_de_vacio": (motivo_de_vacio, "Cada «no aplica» o «sin dato» lleva su motivo"),
}


def evaluate(a: Dict[str, Any], pdf_text: Optional[str] = None, universe: Optional[Dict[str, Any]] = None,
             today: Optional[str] = None, rules: Optional[List[str]] = None) -> Dict[str, Result]:
    """Todas las reglas (o `rules`) sobre un análisis. Una regla que lanza queda «no_evaluable» con la excepción: el
    escaneo no se corta por una salida con una forma inesperada."""
    ctx = {"pdf_text": pdf_text, "universe": universe, "today": today}
    out: Dict[str, Result] = {}
    for name in rules or RULES:
        fn = RULES[name][0]
        try:
            out[name] = fn(a, ctx)
        except Exception as e:  # noqa: BLE001 — se anota y se sigue
            out[name] = Result(NOT_EVALUABLE, f"la regla falló: {type(e).__name__}: {e}")
    return out
