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
    if se.get("method") in ("sin_empresa", "mediana_pares", "agregado_peso_menor"):
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


# ═══════════════════════ F11 · revisión externa de NU y NFLX (4-nov-2026) ═══════════════════════
# docs/fiabilidad/revision-nu-nflx-2026-11-04.md. Cada regla es un hallazgo verificado convertido en regla general: se
# mide en el universo ANTES de corregir.

def caida_avisada(a: Dict[str, Any], ctx: Dict[str, Any]) -> Result:
    """T3: una caída desde máximos en 1 año por debajo del umbral de la alerta («Caída pronunciada») sale en las
    alertas. La regla del motor (alert_interpretations._drawdown) lee un campo que no se rellena."""
    rule = "caida_avisada"
    dd = _num(_get(a, "market_context", "signals", "max_drawdown", "1", "value"))
    if dd is None:
        return Result(NOT_EVALUABLE, "sin caída máxima de 1 año en el contexto de mercado")
    thr = cfg("thresholds.alerts.drawdown.deep_below")
    if dd >= thr:
        return Result(OK)
    if any("caída pronunciada" in str(x.get("reason") or "").lower() for _, x in _alerts(a)):
        return Result(OK)
    if len((a.get("alerts") or {}).get("warnings") or []) >= cfg("thresholds.alerts.max_per_group"):
        # La alerta se evalúa, pero el grupo está lleno de advertencias de más peso (tope por grupo): no es un cable suelto.
        return Result(OK, f"grupo de advertencias lleno ({cfg('thresholds.alerts.max_per_group')}): la caída "
                          f"({_pct(dd)}) queda por debajo en peso")
    return _result(rule, [_violation(
        rule, dd / thr, f"cae {_pct(dd)} desde máximos en 1 año (umbral de la alerta {_pct(thr)}) sin alerta",
        "la alerta de caída lee `max_drawdown_1y`, que nadie rellena: la caída del contexto de mercado no llega",
        drawdown=dd, threshold=thr)])


def riesgo_critico_medido(a: Dict[str, Any], ctx: Dict[str, Any]) -> Result:
    """T3: con la variable crítica de su tipo sin medir (el riesgo de crédito de un banco), la cobertura no es «alta»."""
    rule = "riesgo_critico_medido"
    cr = a.get("credit_risk")
    if not isinstance(cr, dict):
        return Result(NOT_APPLICABLE, "sin riesgo de crédito en su tipo")
    cov = _get(a, "confidence", "dimensions", "coverage", "level")
    if cr.get("status") != "no_medido" or cov is None or LEVELS.get(cov, 0) < LEVELS["alta"]:
        return Result(OK)
    return _result(rule, [_violation(
        rule, 2, f"riesgo de crédito «no medido» con cobertura de datos «{cov}»",
        "la cobertura cuenta solo los componentes del score y el riesgo de crédito «informa, no puntúa»",
        credit_status=cr.get("status"), coverage=cov)])


def una_definicion_ttm_fy(a: Dict[str, Any], ctx: Dict[str, Any]) -> Result:
    """N2: si EDGAR sustituye la serie anual de un campo y el último ejercicio difiere de la fuente más de
    `data.edgar.fy_series_reconcile_rel`, el corte (TTM) de ese campo tampoco puede venir de la fuente."""
    rule, C = "una_definicion_ttm_fy", _C("una_definicion_ttm_fy")
    prim = _get(a, "data_provenance", "edgar", "primary", default={}) or {}
    rec = [r for r in prim.get("reconciliation") or [] if isinstance(r, dict)]
    if not rec:
        return Result(NOT_APPLICABLE, "sin discrepancias entre la serie anual de EDGAR y la de la fuente")
    # La diferencia que cambia lecturas (data.edgar.fy_series_definition_material_rel), en el ÚLTIMO ejercicio de los
    # estados: una diferencia antigua (D, EXE: 2023) no mezcla el corte con la serie.
    tol = cfg("data.edgar.fy_series_definition_material_rel")
    fields = _get(a, "data_provenance", "fields", default={}) or {}
    cut_keys = {c.get("field") for c in prim.get("cut") or [] if isinstance(c, dict)}
    last_fy = max((y.get("year") for y in a.get("yearly_financials") or [] if isinstance(y.get("year"), int)),
                  default=None)
    last: Dict[str, Dict[str, Any]] = {}
    for r in rec:
        f = r.get("field")
        if f and last_fy is not None and str(r.get("fy_end") or "")[:4] < str(last_fy):
            continue
        if f and str(r.get("fy_end") or "") >= str((last.get(f) or {}).get("fy_end") or ""):
            last[f] = r
    out = []
    for f, r in last.items():
        key = dict(C["cut_keys"]).get(f)
        d = _num(r.get("diff_rel"))
        if key is None or d is None or abs(d) <= tol or key in cut_keys:
            continue
        src = (fields.get(key) or {}).get("source")
        if src in (None, "sec_edgar"):
            continue
        out.append(_violation(
            rule, abs(d) / tol, f"{f}: el ejercicio {r.get('fy_end')} es de EDGAR ({r.get('concept')}) y difiere "
            f"{d:+.1%} de la fuente, pero el corte ({key}) viene de {src}",
            "dos definiciones del mismo campo: la historia de EDGAR y el TTM de la fuente (bruto frente a neto)",
            field=f, cut_key=key, cut_source=src, diff_rel=d))
    return _result(rule, out)


def implicito_mismo_modelo(a: Dict[str, Any], ctx: Dict[str, Any]) -> Result:
    """N1: con el P/B (o P/TBV) justificado en dos etapas, el retorno implícito y su sensibilidad usan el mismo modelo:
    la sensibilidad a ±0 pp reproduce el justificado."""
    rule, C = "implicito_mismo_modelo", _C("implicito_mismo_modelo")
    am = a.get("archetype_metrics") or {}
    ts, imp = am.get("two_stage") or {}, am.get("implied") or {}
    if not ts.get("applied"):
        return Result(NOT_APPLICABLE, "justificado de una etapa")
    if imp.get("state") != "ok":
        return Result(NOT_EVALUABLE, "sin retorno implícito")
    just = _num(am.get("ptbv_justified") if imp.get("metric") == "ROTE" else am.get("pb_justified"))
    s0 = next((_num(s.get("multiple_justified")) for s in imp.get("sensitivity") or []
               if _num(s.get("delta")) == 0), None)
    if not just or s0 is None:
        return Result(NOT_EVALUABLE, "sin múltiplo justificado o sin sensibilidad")
    dev = s0 / just - 1
    if abs(dev) <= C["tolerance"]:
        return Result(OK)
    return _result(rule, [_violation(
        rule, abs(dev) / C["tolerance"],
        f"{imp.get('metric')} implícito {_pct(_num(imp.get('implied')))} y su sensibilidad ({s0:.2f}x a ±0) de una etapa, "
        f"frente a un justificado de dos etapas de {just:.2f}x",
        "apply_two_stage actualiza los justificados pero no el implícito ni su sensibilidad",
        implied=_num(imp.get("implied")), sensitivity_0=s0, justified=just)])


def cota_aplicada(a: Dict[str, Any], ctx: Dict[str, Any]) -> Result:
    """T4: el crecimiento que puntúa no supera la cota que el propio motor declara (`growth_basis.*.bound`), y su rótulo
    («a 3 años») corresponde a la ventana usada."""
    rule = "cota_aplicada"
    gb = a.get("growth_basis") or {}
    out = []
    for key, prefix in _C("cota_aplicada")["series"]:
        m = gb.get(key) or {}
        x = next((x for x in _adjustments(a, "Crecimiento") if str(x.get("metric") or "").startswith(prefix)), None)
        raw = _num((x or {}).get("raw"))
        if raw is None:
            continue
        b = m.get("bound") or {}
        bv = _num(b.get("value"))
        if bv is not None and b.get("direction") == "superior" and raw > bv + 1e-6:
            out.append(_violation(
                rule, 1 + (raw - bv) / max(abs(bv), 0.05), f"«{x.get('metric')}» puntúa {_pct(raw)} "
                f"({x.get('adjustment'):+d}) con su cota superior en {_pct(bv)}",
                "la cota se declara y no se aplica (historical_metrics)", growth=raw, bound=bv, series=key))
        # Acotada por la tasa de punta a punta, la cifra que puntúa es la de la ventana de 3 años.
        w = None if m.get("capped") else re.match(r"FY(\d{4})\D+FY(\d{4})", str(m.get("window") or ""))
        n = re.search(r"a (\d+) años", str(x.get("metric")))
        if w and n and int(w.group(2)) - int(w.group(1)) != int(n.group(1)):
            out.append(_violation(
                rule, 1, f"«{x.get('metric')}» con la ventana {m.get('window')}",
                "el rótulo no dice la ventana real del método", window=m.get("window"), series=key))
    return _result(rule, out)


def _reference_value(bi: Dict[str, Any], col: str) -> Optional[float]:
    """El valor de la referencia que se usa: el de después de excluir a la empresa si hay exclusión, si no el publicado."""
    cols = _get(bi, "self_exclusion", "columns", default={}) or {}
    if col in cols:
        return _num((cols.get(col) or {}).get("after"))
    return _num((bi.get("published") or {}).get(col))


def referencia_representativa(a: Dict[str, Any], ctx: Dict[str, Any]) -> Result:
    """T1: la referencia de industria con la que se lee la empresa es representativa: sus ratios de beneficio no son
    ≈ 0 (una industria que casi no gana da brechas de miles de %) y, si son medianas de pares, los pares son de la región
    de la referencia."""
    rule, C = "referencia_representativa", _C("referencia_representativa")
    bi = _get(a, "benchmark", "industry", default={}) or {}
    if _get(a, "benchmark", "profile") == "market" or not bi:
        return Result(NOT_APPLICABLE, "la referencia es el mercado amplio")
    out = []
    used = _get(a, "benchmark", "values", default=None)
    for col in C["profit_columns"]:
        # La referencia que se usa (benchmark.values: F11 · T1 retira las no representativas, dicho); sin ella (salidas
        # anteriores), la de la industria.
        v = _num(used.get(col)) if isinstance(used, dict) else _reference_value(bi, col)
        if v is not None and abs(v) < C["min_abs"]:
            out.append(_violation(
                rule, C["min_abs"] / max(abs(v), C["min_abs"] / 5),
                f"referencia de {col} {_pct(v, 2)} ({bi.get('damodaran')}, {bi.get('region')}"
                f"{', sin la empresa' if (bi.get('self_exclusion') or {}).get('method') else ''})",
                "industria que casi no gana: la brecha de la empresa frente a ella no informa", column=col, value=v))
    se = bi.get("self_exclusion") or {}
    reg = bi.get("region")
    if se.get("method") == "mediana_pares" and reg not in (None, "global") and se.get("peers_scope") != reg:
        # F11 · T1: desde la corrección la salida dice el ámbito de los pares (`peers_scope`); sin él (salidas
        # anteriores), se reconstruye con el fichero de pares.
        import self_exclusion as _se
        sym = str(a.get("symbol") or "").upper()
        peers = [r for r in _se._load_peers()["rows"]
                 if r.get("damodaran_industry") == bi.get("damodaran") and r.get("symbol") != sym]
        other = [r for r in peers if r.get("damodaran_region") != reg]
        if se.get("peers_scope") == "todas" and peers and len(other) / len(peers) > C["max_other_region_share"]:
            pass         # no hay pares bastantes en su región: todas, DICHO en la nota (no es un cable suelto)
        elif peers and len(other) / len(peers) > C["max_other_region_share"]:
            out.append(_violation(
                rule, 1 + len(other) / len(peers), f"mediana de {len(peers)} pares de {bi.get('damodaran')} para una "
                f"referencia de la región «{reg}»: {len(other)} son de otras regiones",
                "el filtro de pares (self_exclusion.peer_median) mira la industria y no la región",
                peers=len(peers), other_region=len(other), region=reg))
    return _result(rule, out)


def voto_estable(a: Dict[str, Any], ctx: Dict[str, Any]) -> Result:
    """F1/T5: el DCF directo solo vota una dirección si el valor queda del mismo lado del precio con WACC ± 1 escalón de
    su propia rejilla de sensibilidad (al crecimiento base)."""
    rule = "voto_estable"
    x = next((x for x in _adjustments(a, "Valoración") if str(x.get("metric") or "").startswith("DCF directo")), None)
    if not x or not x.get("adjustment"):
        return Result(NOT_APPLICABLE, "el DCF directo no vota")
    s = a.get("sensitivity") or {}
    M, gi, di = s.get("matrix"), s.get("base_growth_idx"), s.get("base_discount_idx")
    price = _num(_get(s, "statistics", "current_price"))
    if not M or gi is None or di is None or not price:
        return Result(NOT_EVALUABLE, "sin rejilla de sensibilidad")
    row = M[gi]
    base = _num(row[di])
    side = [(j, _num(row[j])) for j in (di - 1, di + 1) if 0 <= j < len(row) and _num(row[j]) is not None]
    flips = [(j, v) for j, v in side if base is not None and (v - price) * (base - price) < 0]
    if not flips:
        return Result(OK)
    rates = s.get("discount_rates") or []
    return _result(rule, [_violation(
        rule, 2, f"el DCF vota {x.get('adjustment'):+d} ({x.get('value')}) pero con WACC "
        + ", ".join(f"{_pct(_num(rates[j]), 2) if j < len(rates) else j} vale {v:.2f}" for j, v in flips)
        + f" frente a un precio de {price:.2f}",
        "la dirección del DCF depende del coste de capital: debería leerse «en precio, sensible al WACC»",
        base=base, price=price, flips=[v for _, v in flips])])


def inverso_tasa_base(a: Dict[str, Any], ctx: Dict[str, Any]) -> Result:
    """F2: el DCF inverso no lee «barata» si la tasa base dice que menos de la mitad de las comparables sostuvo el
    crecimiento que exige el precio."""
    rule, C = "inverso_tasa_base", _C("inverso_tasa_base")
    m = _get(a, "reverse_dcf", "main", default={}) or {}
    if not m or m.get("band") not in C["cheap_bands"]:
        return Result(NOT_APPLICABLE, "el DCF inverso no lee «barata»")
    share = _num(_get(m, "base_rate", "share"))
    if share is None or share >= C["min_share"]:
        return Result(OK)
    votes = any("inverso" in str(x.get("metric") or "").lower() and x.get("adjustment") for x in _adjustments(a))
    return _result(rule, [_violation(
        rule, (C["min_share"] / max(share, 0.05)) * (2 if votes else 1),
        f"DCF inverso «{m.get('band')}» (regla {m.get('rule')}) con una tasa base del {share:.0%}"
        + (" y vota" if votes else " (no vota hoy)"),
        "con la tasa base entre 25 % y 75 % decide la historia propia, medida con otra métrica y otra ventana",
        share=share, rule_used=m.get("rule"), votes=votes)])


def convergencia_independiente(a: Dict[str, Any], ctx: Dict[str, Any]) -> Result:
    """T2: la convergencia «alta» no puede apoyarse en dos métodos con el mismo ancla (el ROE terminal del justificado
    sacado del mismo conjunto de referencia que el múltiplo relativo)."""
    rule = "convergencia_independiente"
    conv = _get(a, "confidence", "dimensions", "convergence", default={}) or {}
    if conv.get("level") != "alta":
        return Result(NOT_APPLICABLE, "convergencia no alta")
    kinds = {m.get("kind") for m in conv.get("methods") or [] if m.get("evaluable")}
    if not {"intrínseco", "relativo"} <= kinds:
        return Result(OK)
    am = a.get("archetype_metrics") or {}
    ts = am.get("two_stage") or {}
    anchor = _num(ts.get("industry_roe")) if ts.get("applied") else _num(am.get("roe_reference"))
    ref = _reference_value(_get(a, "benchmark", "industry", default={}) or {}, "roe")
    if anchor is None or ref is None or abs(anchor - ref) > 1e-4:
        return Result(OK)
    return _result(rule, [_violation(
        rule, 2, f"convergencia alta entre {' y '.join(m.get('method') for m in conv.get('methods') or [])}, con el ROE "
        f"terminal del intrínseco ({_pct(anchor, 2)}) igual al ROE de la referencia del relativo",
        "los dos métodos comparten la referencia de industria: un error en ella los mueve juntos y cuenta como "
        "confirmación", anchor=anchor, reference_roe=ref)])


def calidad_sin_saturar(a: Dict[str, Any], ctx: Dict[str, Any]) -> Result:
    """F4: Calidad de ganancias no puede estar en su máximo con la prueba de acumulaciones del Piotroski fallida (flujo
    operativo < beneficio neto)."""
    rule = "calidad_sin_saturar"
    cat = _get(a, "score", "breakdown", "Calidad de Ganancias", default={}) or {}
    eq = _get(a, "piotroski_f", "details", "earnings_quality", default={}) or {}
    if eq.get("state") != "no_cumple":
        return Result(NOT_APPLICABLE, "pasa (o no evalúa) la prueba de acumulaciones")
    sc, mx = _num(cat.get("score")), _num(cat.get("max"))
    if sc is None or mx is None or sc < mx:
        return Result(OK)
    return _result(rule, [_violation(
        rule, 2, f"Calidad de ganancias {sc:.0f}/{mx:.0f} con flujo operativo {_num(eq.get('cur')) / 1e9:.2f}B < "
        f"beneficio neto {_num(eq.get('prev')) / 1e9:.2f}B",
        "dos pruebas binarias (flujo operativo y FCF positivos) saturan la categoría sin mirar las acumulaciones",
        cfo=_num(eq.get("cur")), net_income=_num(eq.get("prev")))])


def forward_creible(a: Dict[str, Any], ctx: Dict[str, Any]) -> Result:
    """F3: la compresión del Forward P/E solo puntúa si el crecimiento del BPA que implica (frente al P/E con que se
    compara) es creíble."""
    rule, C = "forward_creible", _C("forward_creible")
    x = next((x for x in _adjustments(a, "Valoración") if x.get("metric") == "Forward P/E"), None)
    if not x or not x.get("adjustment") or (x.get("adjustment") or 0) <= 0:
        return Result(NOT_APPLICABLE, "el Forward P/E no suma")
    # Lo que se acredita (el forward creíble, F9 · R1c y F11 · F3), no el consenso en bruto.
    g = _num(x.get("credited_eps_growth"))
    if g is None:
        g = _num(x.get("implied_eps_growth"))
    if g is None or g <= C["max_implied_growth"]:
        return Result(OK)
    return _result(rule, [_violation(
        rule, g / C["max_implied_growth"], f"Forward P/E {x.get('value')} suma {x['adjustment']:+d} acreditando un "
        f"crecimiento del BPA del {_pct(g)} en un año (implícito en el consenso: "
        f"{_pct(_num(x.get('implied_eps_growth')))})",
        "el tope de credibilidad usa el CAGR histórico del BPA (o el consenso está en otra base que el P/E comparado)",
        implied_growth=g, credible_pe=_num(x.get("credible_forward_pe")))])


def beta_contrastada(a: Dict[str, Any], ctx: Dict[str, Any]) -> Result:
    """T5: la beta sustituta (de su industria) no queda fuera del intervalo ± k·EE de la beta propia que descartó."""
    rule, C = "beta_contrastada", _C("beta_contrastada")
    b = a.get("beta") or {}
    if b.get("source") == "propia":
        return Result(NOT_APPLICABLE, "usa la beta propia")
    own = b.get("own") or {}
    raw, se, used = _num(own.get("raw")), _num(own.get("se")), _num(b.get("adjusted"))
    if raw is None or se is None or used is None:
        return Result(NOT_EVALUABLE, "sin beta propia o sin su error estándar")
    r2 = _num(own.get("r2"))
    if r2 is None or r2 < C["min_r2"]:
        # KO, HSY, ABT (escaneo del 4-nov): R² ≈ 0 recalculado aparte; la propia no informa y no hay nada que contrastar.
        return Result(NOT_APPLICABLE, f"la regresión propia no explica el título (R² {r2})")
    lo, hi = raw - C["k_se"] * se, raw + C["k_se"] * se
    if lo <= used <= hi:
        return Result(OK)
    if b.get("contrast"):
        # F11 · T5: declarada (beta.contrast) y con la confianza a la baja: no es un vacío
        return Result(OK, "beta sustituta fuera de la propia, declarada y contada en la confianza")
    return _result(rule, [_violation(
        rule, 1 + min(abs(used - lo), abs(used - hi)) / max(se, 0.05),
        f"beta usada {used:.2f} ({b.get('source')}) fuera de la propia {raw:.2f} ± {C['k_se']:g}·{se:.2f}",
        "la beta de la industria sustituye a la propia sin contrastarse con ella", used=used, own=raw, se=se)])


def causalidad_sostenida(a: Dict[str, Any], ctx: Dict[str, Any]) -> Result:
    """T6: la narrativa de mercado no atribuye el movimiento a la empresa sin compararlo con su país (emisores con prima
    de riesgo país) ni a una sobrerreacción del mercado sin evidencia (con reacción negativa a sus resultados)."""
    rule = "causalidad_sostenida"
    mc = a.get("market_context") or {}
    out = []
    crp = _num(_get(a, "country_risk", "crp")) or 0.0
    foreign = _get(a, "country_risk", "country") not in (None, "United States")    # sede fuera de EE. UU.
    # F11 · T6: con la fuerza relativa frente al ETF de su país (signals.relative_strength_country) ya no es un vacío
    vs_country = _get(mc, "signals", "relative_strength_country", "status") == "ok"
    for r in mc.get("readings") or []:
        if r.get("key") == "relative_strength" and "propio de la empresa" in str(r.get("text") or "") and foreign \
                and not vs_country:
            out.append(_violation(
                rule, 1 + crp / 0.01, f"«{r.get('text')}» con prima de riesgo país {_pp(crp)} "
                f"({_get(a, 'country_risk', 'country')})",
                "la fuerza relativa se mide solo contra el ETF sectorial de EE. UU., no contra el de su país",
                crp=crp, etf=mc.get("sector_etf")))
    reaction = _num(_get(mc, "pead", "reaction"))
    for bh in mc.get("behavioral") or []:
        # F11 · T6: la sobrerreacción solo se cita con la última reacción a resultados no negativa
        if bh.get("kind") == "sobrerreaccion" and (reaction is None or reaction < 0):
            neg = reaction is not None and reaction < 0
            out.append(_violation(
                rule, 2 if neg else 1, "lectura de sobrerreacción del mercado"
                + (f" con reacción a sus últimos resultados de {_pct(reaction)}" if neg else ""),
                "la lectura conductual solo mira fundamentales pasados: no descarta que el precio descuente algo que el "
                "informe no mide", reaction=reaction))
    return _result(rule, out)


def metodo_citado_aplicable(a: Dict[str, Any], ctx: Dict[str, Any]) -> Result:
    """T7: el PDF no titula ni cita un método que su tipo excluye, no usa como ancla una métrica «No aplica» y cada fila
    lleva su propia definición."""
    rule = "metodo_citado_aplicable"
    text = ctx.get("pdf_text")
    if not text:
        return Result(NOT_EVALUABLE, "sin texto del PDF")
    na = set(_get(a, "display", "na_keys", default=[]) or [])
    out = []
    if "dcf" in na and re.search(r"DCF:\s*supuestos", text):
        out.append(_violation(rule, 1, "título «DCF: supuestos y fiabilidad» con el DCF «No aplica»",
                              "título fijo en pdf_v2/chapters.py", method="dcf"))
    if _get(a, "reverse_dcf", "applicable") is False and "Mauboussin" in text:
        out.append(_violation(rule, 1, "la metodología cita las tasas base del DCF inverso, que no aplica",
                              "metodología escrita a mano en pdf_v2/methodology.py", method="reverse_dcf"))
    if re.search(r"Precio de mercado\s+Puntuación de 0 a 100", text):
        out.append(_violation(rule, 1, "la fila «Precio de mercado» lleva la definición de la puntuación de atractivo",
                              "la fila usa la clave «price» en lugar de «share_price»", method="price_row"))
    if "net_margin" in na and re.search(r"exige persistencia.{0,200}?margen neto", text, re.I | re.S):
        out.append(_violation(rule, 1, "la persistencia de Calidad se ancla en el margen neto, que «No aplica»",
                              "persistence.py no consulta los «no aplica» del tipo", method="net_margin"))
    return _result(rule, out)


# ═══════════════════════ F13: revisión externa de 110 empresas (5-nov-2026) ═══════════════════════
# Una regla por hallazgo verificado en docs/fiabilidad/revision-110-2026-11-05.md (patrón del revisor entre corchetes).

def _hist(a: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Ejercicios de la historia de 10 años (EDGAR), del más antiguo al más reciente."""
    rows = [r for r in (_get(a, "history_10y", "rows", default=[]) or []) if isinstance(r, dict)]
    return sorted(rows, key=lambda r: r.get("year") or 0)


def _industry(a: Dict[str, Any]) -> str:
    return str(_get(a, "profile", "industry", default="") or "").strip().lower()


def _commodity(a: Dict[str, Any]) -> bool:
    return _industry(a) in set(_C("ciclica_por_industria")["commodity_industries"])


def rating_contable(a: Dict[str, Any], ctx: Dict[str, Any]) -> Result:
    """[3] El rating sintético no sale de un EBIT contable hundido por partidas sin caja: un rating de impago (o casi)
    con el beneficio operativo normalizado o la caja operativa positivos es incoherente, y lleva el WACC a su tope."""
    rule, C = "rating_contable", _C("rating_contable")
    w = a.get("wacc") or {}
    rt = _get(w, "rating", "rating")
    if not w.get("applicable", True) or rt is None:
        return Result(NOT_APPLICABLE, "sin WACC o sin rating sintético")
    if rt not in C["low_ratings"]:
        return Result(OK)
    km = a.get("key_metrics") or {}
    oin, ocf = _num(km.get("operating_income_normalized")), _num(km.get("operating_cash_flow"))
    if not ((oin is not None and oin > 0) or (ocf is not None and ocf > 0)):
        return Result(OK)
    wv = _num(w.get("value")) or 0.0
    return _result(rule, [_violation(
        rule, 1 + wv / 0.10, f"rating {rt} (cobertura {_num(_get(w, 'rating', 'coverage'))}) con EBIT normalizado "
        f"{oin} y flujo operativo {ocf}: WACC {_pct(wv)}{' (en su tope)' if w.get('clamped') else ''}"
        f"{' · ' + _archetype(a) if _archetype(a) == 'REIT' else ''}",
        "la cobertura usa el EBIT contable del TTM (deterioros sin caja; en REIT, la depreciación inmobiliaria) y el "
        "piso Ke ≥ Kd + 1 pp traslada el spread al Ke", rating=rt, wacc=wv, ebit_normalized=oin, ocf=ocf)])


def cautiva_separada(a: Dict[str, Any], ctx: Dict[str, Any]) -> Result:
    """[8] Si se detecta una financiera cautiva, su deuda no se trata como deuda industrial en la valoración."""
    rule = "cautiva_separada"
    cf = _get(a, "business_model", "captive_finance", default={}) or {}
    if not cf.get("detected"):
        return Result(NOT_APPLICABLE, "sin financiera cautiva detectada")
    cap = _get(a, "data_provenance", "debt", "components", "captive", default=None)
    if isinstance(cap, dict) and not cap.get("in_rule_debt", True):
        return Result(OK)
    km = a.get("key_metrics") or {}
    return _result(rule, [_violation(
        rule, 2, f"cautiva «{cf.get('segment') or '?'}» detectada; su deuda "
        + (f"({_num(cap.get('value'))}) se declara pero sigue en la deuda" if isinstance(cap, dict) else "no se separa")
        + f" (deuda neta/EBITDA {_num(km.get('net_debt_to_ebitda'))})",
        "separar la deuda depende de una lista manual (data.toml [edgar.captive]) y su uso en la valoración no está "
        "hecho; la filial presenta su propio 10-K", segment=cf.get("segment"), separated=isinstance(cap, dict))])


def inverso_una_vez(a: Dict[str, Any], ctx: Dict[str, Any]) -> Result:
    """[1a] El DCF inverso cuenta una sola vez en la convergencia: no puede ser método propio y a la vez lectura dentro
    de la señal de los múltiplos."""
    rule = "inverso_una_vez"
    meths = _get(a, "confidence", "dimensions", "convergence", "methods", default=[]) or []
    if not any(m.get("method") == "DCF inverso" for m in meths):
        return Result(NOT_APPLICABLE, "el DCF inverso no es método de la convergencia")
    inside = [m for m in meths if any("inverso" in str(k).lower() for k in (m.get("readings") or {}))]
    if not inside:
        return Result(OK)
    return _result(rule, [_violation(
        rule, 2, f"el DCF inverso es método y además lectura de «{inside[0].get('method')}» "
        f"(señal {_num(inside[0].get('signal'))}); convergencia {_get(a, 'confidence', 'dimensions', 'convergence', 'level')}",
        "la señal de múltiplos excluye las filas por nombre («DCF»), y con el directo no significativo o en REIT la fila "
        "se llama «DCF inverso (…)»", level=_get(a, "confidence", "level"))])


def _fragile(a: Dict[str, Any]) -> List[str]:
    """Señales de base frágil del veredicto de precio (F13 · paso 3)."""
    C, km, out = _C("confianza_base_fragil"), a.get("key_metrics") or {}, []
    fcf, ocf = _num(km.get("free_cash_flow")), _num(km.get("operating_cash_flow"))
    if fcf is not None and fcf < 0 and ocf is not None and ocf - fcf > max(ocf, 0):
        out.append(f"FCF {fcf / 1e9:.1f} B con capex mayor que el flujo operativo")
    if _get(a, "altman_z", "applicable") and _get(a, "altman_z", "zone") == "distress":
        out.append(f"Altman {_num(_get(a, 'altman_z', 'z_score'))} en zona de peligro")
    pen, fpe = _num(km.get("pe_normalized")), _num(km.get("forward_pe"))
    if pen and fpe and pen > 0 and fpe > 0 and abs(pen / fpe - 1) > C["max_pe_gap"]:
        out.append(f"P/E normalizado {pen:.1f}x frente a forward {fpe:.1f}x")
    if _get(a, "data_provenance", "staleness", "status") == "desfasado":
        out.append(f"estados desfasados ({_get(a, 'data_provenance', 'staleness', 'days_since_cut')} días)")
    return out


def confianza_base_fragil(a: Dict[str, Any], ctx: Dict[str, Any]) -> Result:
    """[1b, 1c, 11a] La confianza no es «alta» con una base frágil: caja negativa por capex, Altman en peligro, P/E
    normalizado lejos del forward o estados desfasados."""
    rule = "confianza_base_fragil"
    lvl = _get(a, "confidence", "level")
    if lvl is None or _get(a, "price_attractiveness", "level") is None:
        return Result(NOT_APPLICABLE, "sin veredicto de precio")
    f = _fragile(a)
    if lvl != "alta" or not f:
        return Result(OK)
    return _result(rule, [_violation(
        rule, 1 + len(f), f"confianza alta con: {'; '.join(f)}",
        "la confianza solo mira convergencia, cobertura, fuente, estabilidad y fuente oficial (valuation_confidence)",
        signals=f)])


def ciclica_por_industria(a: Dict[str, Any], ctx: Dict[str, Any]) -> Result:
    """[6] Un productor de materias primas es cíclico por su industria, aunque su historia de ventas no lo muestre."""
    rule = "ciclica_por_industria"
    if not _commodity(a):
        return Result(NOT_APPLICABLE, "no es productor de materias primas")
    arch = _archetype(a)
    if arch in ("CYCLICAL", "FINANCIAL", "REIT", "GROWTH_PRE_PROFIT"):
        return Result(OK)
    cyc = _get(a, "classification", "inputs", "cyclicality", default={}) or {}
    return _result(rule, [_violation(
        rule, 2, f"{_get(a, 'profile', 'industry')} clasificada {arch} (regla {_get(a, 'classification', 'rule')}; "
        f"años de perímetro descartados: {len(cyc.get('perimeter_years') or [])})",
        "con historia larga decide la de ventas (classify.py:540) y la lista de industrias es un elif que no se consulta",
        archetype=arch)])


def pico_ciclico(a: Dict[str, Any], ctx: Dict[str, Any]) -> Result:
    """[6] En una cíclica o productora de materias primas, un beneficio muy por encima de su mediana es pico aunque el
    consenso no lo confirme."""
    rule, C = "pico_ciclico", _C("pico_ciclico")
    if not (_archetype(a) == "CYCLICAL" or _commodity(a)):
        return Result(NOT_APPLICABLE, "ni cíclica ni materias primas")
    ep = a.get("earnings_peak") or {}
    r = _num(ep.get("ttm_over_median"))
    if r is None:
        h = [x for x in _hist(a) if _num(x.get("net_income")) is not None]
        if len(h) >= 4 and _num(h[-1]["net_income"]) and _num(h[-1]["net_income"]) > 0:
            med = statistics.median([_num(x["net_income"]) for x in h[-4:-1]])
            r = (_num(h[-1]["net_income"]) / med) if med and med > 0 else None
    if r is None:
        return Result(NOT_EVALUABLE, "sin beneficio frente a su mediana")
    if r < C["min_ratio"] or ep.get("flag"):
        return Result(OK)
    return _result(rule, [_violation(
        rule, r / C["min_ratio"], f"beneficio {r:.2f}× su mediana sin bandera de pico "
        f"(condiciones a={_get(ep, 'conditions', 'a')}, b={_get(ep, 'conditions', 'b')}; {_archetype(a)})",
        "el pico exige (a) y (b) (el consenso confirma la caída); en materias primas el consenso extrapola el precio",
        ratio=r)])


def referencia_acotada(a: Dict[str, Any], ctx: Dict[str, Any]) -> Result:
    """[4] La referencia que queda al quitar a la empresa es plausible: mismo signo que la publicada, no menor de un
    mínimo en los ratios de beneficio y dentro de un factor de la publicada."""
    rule, C = "referencia_acotada", _C("referencia_acotada")
    bi = _get(a, "benchmark", "industry", default={}) or {}
    used = _get(a, "benchmark", "values", default={}) or {}
    if _get(a, "benchmark", "profile") == "market" or not bi:
        return Result(NOT_APPLICABLE, "la referencia es el mercado amplio")
    cols = _get(bi, "self_exclusion", "columns", default={}) or {}
    out = []
    for col in C["profit_columns"]:
        v = _num(used.get(col))
        if v is None:
            continue
        pub = _num((cols.get(col) or {}).get("before"))
        if pub is None:
            pub = _num((bi.get("published") or {}).get(col))
        bad = []
        if v < C["min_value"]:
            bad.append(f"{_pct(v)} < {_pct(C['min_value'], 0)}")
        if col == "roe" and v > C["max_roe"]:
            bad.append(f"ROE de referencia {_pct(v)}")
        # frente a una publicada casi nula (Restaurantes, ROE 0,1 %) el factor no mide nada
        if pub and pub >= C["min_value"] and v > 0 and not (1 / C["max_factor"] <= v / pub <= C["max_factor"]):
            bad.append(f"{v / pub:.1f}× la publicada ({_pct(pub)})")
        if bad:
            out.append(_violation(rule, 2, f"referencia de {col}: " + "; ".join(bad)
                                  + f" ({bi.get('damodaran')}, {(bi.get('self_exclusion') or {}).get('method')})",
                                  "quitar a la empresa del agregado (self_exclusion) no tiene cota ni prueba de signo; "
                                  "la T1 solo retira |v| < 2 %", column=col, value=v, published=pub))
    return _result(rule, out)


def roe_bajo_coherente(a: Dict[str, Any], ctx: Dict[str, Any]) -> Result:
    """[4b] No se llama «bajo» a un ROE que cubre su coste del capital."""
    rule = "roe_bajo_coherente"
    km = a.get("key_metrics") or {}
    ke = _num(_get(a, "cost_of_equity", "value")) or _num(_get(a, "wacc", "ke"))
    hits = [x for _, x in _alerts(a) if "ROE" in str(x.get("reason") or "") and "bajo" in str(x.get("reason") or "")]
    if not hits:
        return Result(NOT_APPLICABLE, "sin alerta de ROE bajo")
    m = re.search(r"([−-]?\d+(?:[.,]\d+)?)%", str(hits[0].get("reason")))
    roe = float(m.group(1).replace(",", ".").replace("−", "-")) / 100 if m else _num(km.get("roe"))
    if roe is None or ke is None or roe < ke:
        return Result(OK)
    return _result(rule, [_violation(
        rule, roe / ke, f"«{hits[0].get('reason')}» con un ROE de {_pct(roe)} ≥ Ke {_pct(ke)} (referencia "
        f"{_pct(_num(_get(a, 'benchmark', 'values', 'roe')))})",
        "la alerta compara solo con la referencia de industria, sin suelo absoluto", roe=roe, ke=ke)])


def roe_patrimonio_infimo(a: Dict[str, Any], ctx: Dict[str, Any]) -> Result:
    """[4c] Con un patrimonio ínfimo frente a los activos, el ROE no mide nada: ni fortaleza ni cifra puntuable."""
    rule, C = "roe_patrimonio_infimo", _C("roe_patrimonio_infimo")
    if _archetype(a) == "FINANCIAL":
        return Result(NOT_APPLICABLE, "financiera: el apalancamiento es el negocio (su ROE tiene su propia lectura)")
    km = a.get("key_metrics") or {}
    eq, ta = _num(km.get("total_equity")), _num(km.get("total_assets"))
    if eq is None or ta is None or ta <= 0 or eq <= 0:
        return Result(NOT_APPLICABLE, "sin patrimonio positivo o sin activos")
    if eq / ta >= C["min_equity_to_assets"]:
        return Result(OK)
    strong = [x for k, x in _alerts(a) if k == "strengths" and "ROE" in str(x.get("reason") or "")]
    if km.get("roe") is None and not strong:
        return Result(OK)          # F13 · paso 5c: «no significativo», sin cifra ni fortaleza
    return _result(rule, [_violation(
        rule, C["min_equity_to_assets"] / max(eq / ta, 0.002), f"patrimonio {_pct(eq / ta)} de los activos con ROE "
        f"{_pct(_num(km.get('roe')))}" + (f"; fortaleza «{strong[0].get('reason')}»" if strong else ""),
        "solo el patrimonio negativo deja el ROE «n.s.»", equity_to_assets=eq / ta, strength=bool(strong))])


def utility_regulada(a: Dict[str, Any], ctx: Dict[str, Any]) -> Result:
    """[10a] En una utility regulada el retorno lo fija el regulador: ROIC < WACC no es «destruye valor» ni resta nota."""
    rule = "utility_regulada"
    if _archetype(a) != "UTILITY":
        return Result(NOT_APPLICABLE, "no es utility")
    hits = [x for _, x in _alerts(a) if "destruye valor" in str(x.get("reason") or "").lower()]
    adj = [x for x in _adjustments(a) if "ROIC" in str(x.get("metric") or "") and (x.get("adjustment") or 0) < 0]
    if not hits and not adj:
        return Result(OK)
    return _result(rule, [_violation(
        rule, 2, ("alerta «" + str(hits[0].get("reason")) + "»" if hits else "")
        + (f"{'; ' if hits else ''}{adj[0].get('metric')} {adj[0].get('adjustment'):+d} en la nota" if adj else ""),
        "UTILITY no tiene roic_wacc entre sus no aplicables (sectors.toml)", alert=bool(hits), scored=bool(adj))])


def normalizacion_utility(a: Dict[str, Any], ctx: Dict[str, Any]) -> Result:
    """[nuevo] En utilities, el «beneficio que la operación no explica» (créditos fiscales, AFUDC) puede ser recurrente:
    se mide cuánto quita."""
    rule, C = "normalizacion_utility", _C("normalizacion_utility")
    if _archetype(a) != "UTILITY":
        return Result(NOT_APPLICABLE, "no es utility")
    en = a.get("earnings_normalization") or {}
    rep, out = _num(en.get("reported_net_income")), _num(_get(en, "after_tax", "out")) or 0.0
    if not rep or rep <= 0 or not _get(en, "after_tax", "applied"):
        return Result(OK)
    if out / rep < C["min_share"]:
        return Result(OK)
    return _result(rule, [_violation(
        rule, (out / rep) / C["min_share"], f"quita {_pct(out / rep)} del beneficio ({out / 1e9:.2f} B) como no "
        f"explicado por la operación; P/E normalizado {_num(_get(a, 'key_metrics', 'pe_normalized'))} frente a forward "
        f"{_num(_get(a, 'key_metrics', 'forward_pe'))}",
        "hipótesis: créditos fiscales y AFUDC recurrentes leídos como no operativos (F10 · N1)", share=out / rep)])


def espectro_coherente(a: Dict[str, Any], ctx: Dict[str, Any]) -> Result:
    """[9a] El ajuste de espectro se aplica igual a todas las telecom."""
    rule = "espectro_coherente"
    sp = a.get("spectrum_adjustment")
    if not isinstance(sp, dict):
        return Result(NOT_APPLICABLE, "no es telecom con ajuste de espectro")
    if sp.get("status") == "ok":
        return Result(OK)
    return _result(rule, [_violation(
        rule, 2, f"espectro «{sp.get('status')}»: {str(sp.get('reason'))[:140]}",
        "la regla exige PaymentsToAcquireIntangibleAssets en 5 de 10 años; un emisor con extensión propia queda fuera",
        status=sp.get("status"))])


def perimetro_corregido(a: Dict[str, Any], ctx: Dict[str, Any]) -> Result:
    """[5] Un cambio de perímetro (escisiones, discontinuadas) no se lee como declive ni como ciclo."""
    rule = "perimetro_corregido"
    pr = _get(a, "data_provenance", "perimeter", default={}) or {}
    if not pr.get("changed") or not (pr.get("discontinued") or pr.get("restated")):
        return Result(NOT_APPLICABLE, "sin cambio de perímetro")
    g = _num(_get(a, "dcf", "growth_rate"))
    hist_cyc = _archetype(a) == "CYCLICAL" and _get(a, "classification", "rule") == "historia_ciclica"
    bad = []
    if g is not None and g < 0 and not pr.get("mixed_cagr"):
        bad.append(f"DCF con crecimiento {_pct(g)} sin corregir el perímetro")
    if hist_cyc:
        bad.append("cíclica por su historia")
    if not bad:
        return Result(OK)
    return _result(rule, [_violation(
        rule, 1 + len(bad), "; ".join(bad) + f" ({len(pr.get('discontinued') or [])} ejercicios con discontinuadas, "
        f"{len(pr.get('restated') or [])} re-expresiones)",
        "el perímetro homogéneo solo se aplica con años mezclados en la ventana (main.py:1193-1232); no llega al DCF ni "
        "al ciclo", growth=g, cyclical_by_history=hist_cyc)])


def ffo_sin_saltos(a: Dict[str, Any], ctx: Dict[str, Any]) -> Result:
    """[10d] La serie de FFO por acción de un REIT no tiene años negativos ni saltos que no sean del negocio."""
    rule, C = "ffo_sin_saltos", _C("ffo_sin_saltos")
    if _archetype(a) != "REIT":
        return Result(NOT_APPLICABLE, "no es REIT")
    s = [_num(x) for x in (_get(a, "archetype_metrics", "ffo_per_share_series", default=[]) or [])]
    s = [x for x in s if x is not None]
    if len(s) < 2:
        return Result(NOT_EVALUABLE, "sin serie de FFO por acción")
    bad = [x for x in s if x <= 0]
    pos = [x for x in s if x > 0]
    jump = max(pos) / min(pos) if len(pos) >= 2 else 1.0
    if not bad and jump <= C["max_range_factor"]:
        return Result(OK)
    return _result(rule, [_violation(
        rule, max(jump / C["max_range_factor"], 2 if bad else 1), f"FFO por acción {[round(x, 2) for x in s]} "
        f"(CAGR {_pct(_num(_get(a, 'archetype_metrics', 'ffo_per_share_cagr_3y')))})",
        "ganancias por venta de participadas y discontinuadas sin restar; el CAGR del FFO no pasa por el perímetro",
        series=s)])


def abstencion_sin_datos(a: Dict[str, Any], ctx: Dict[str, Any]) -> Result:
    """[11b] Sin perfil ni historial de precios no hay veredicto de precio."""
    rule = "abstencion_sin_datos"
    lvl = _get(a, "price_attractiveness", "level")
    if lvl is None:
        return Result(NOT_APPLICABLE, "sin veredicto de precio")
    rows = _num(_get(a, "data_provenance", "price_history", "rows"))
    unknown = str(_get(a, "profile", "sector", default="") or "") in ("", "Unknown")
    if not unknown and (rows is None or rows >= 20):
        return Result(OK)
    return _result(rule, [_violation(
        rule, 3, f"precio «{lvl}» con perfil {'vacío' if unknown else 'ok'} y {rows} sesiones de historial",
        "no hay regla de abstención (verdict.py)", unknown=unknown, rows=rows)])


def beta_sin_signo_negativo(a: Dict[str, Any], ctx: Dict[str, Any]) -> Result:
    """[nuevo] Una beta negativa de la fuente no entra en el CAPM."""
    rule = "beta_sin_signo_negativo"
    b = _num(_get(a, "wacc", "beta"))
    if b is None:
        return Result(NOT_APPLICABLE, "sin beta en el Ke")
    if b >= 0:
        return Result(OK)
    return _result(rule, [_violation(rule, 3, f"beta {b} (fuente {_get(a, 'beta', 'source')}) en el Ke",
                                     "sin historial propio, la beta de la fuente entra tal cual", beta=b)])


def flujo_por_intensidad(a: Dict[str, Any], ctx: Dict[str, Any]) -> Result:
    """[2] Una empresa que invierte mucho más de lo que repone no se valora con el FCF de hoy en un DCF y con el de
    mantenimiento en otra: la regla depende de la intensidad inversora, no del signo del FCF."""
    rule, C = "flujo_por_intensidad", _C("flujo_por_intensidad")
    if _archetype(a) in ("FINANCIAL", "REIT", "UTILITY", "CYCLICAL"):
        return Result(NOT_APPLICABLE, "tipo con otro flujo (FFO, P/B o mantenimiento medio)")
    km = a.get("key_metrics") or {}
    ocf, fcf = _num(km.get("operating_cash_flow")), _num(km.get("free_cash_flow"))
    if not ocf or ocf <= 0 or fcf is None:
        return Result(NOT_EVALUABLE, "sin flujo operativo positivo")
    ratio = (ocf - fcf) / ocf                   # capex del TTM sobre el flujo operativo (la medida del revisor)
    if ratio < C["min_capex_to_ocf"]:
        return Result(OK)
    basis = str(_get(a, "dcf", "fcf_basis", default="") or "")
    up = _num(_get(a, "dcf", "upside"))
    if not _get(a, "dcf", "available") or "mantenimiento" in basis.lower():
        return Result(OK)
    return _result(rule, [_violation(
        rule, ratio / C["min_capex_to_ocf"], f"capex {_pct(ratio, 0)} del flujo operativo (TTM) y DCF "
        f"directo con «{basis}» (upside {up if up is None else round(up)} %)",
        "el flujo de mantenimiento solo sustituye cuando FCF − SBC ≤ 0 (main.py:2291-2311)", ratio=ratio, upside=up)])


def crecimiento_dcf_representativo(a: Dict[str, Any], ctx: Dict[str, Any]) -> Result:
    """[7a] El crecimiento del DCF (ventas) no se aleja mucho del de los beneficios cuando el DCF da un resultado extremo."""
    rule, C = "crecimiento_dcf_representativo", _C("crecimiento_dcf_representativo")
    if not _get(a, "dcf", "available"):
        return Result(NOT_APPLICABLE, "sin DCF directo")
    g, up = _num(_get(a, "dcf", "growth_rate")), _num(_get(a, "dcf", "upside"))
    eg = _num(_get(a, "peg_basis", "eps_cagr_3y"))
    if g is None or up is None or eg is None or abs(up) < C["min_abs_upside"]:
        return Result(OK)
    if abs(eg - g) < C["max_gap"]:
        return Result(OK)
    return _result(rule, [_violation(
        rule, abs(eg - g) / C["max_gap"], f"DCF {up:+.0f} % con crecimiento {_pct(g)} ({_get(a, 'dcf', 'growth_source')})"
        f" y BPA {_pct(eg)} anual a 3 años",
        "el DCF solo recibe revenue_growth_3y (E7: tres impulsores)", growth=g, eps_growth=eg, upside=up)])


def base_inflada(a: Dict[str, Any], ctx: Dict[str, Any]) -> Result:
    """[paso 12] Un crecimiento a 3 años no se mide desde un año base inflado frente a la historia de la empresa (PFE:
    FCF desde 2022, el año de las vacunas)."""
    rule, C = "base_inflada", _C("base_inflada")
    h = _hist(a)
    if len(h) < C["min_years"]:
        return Result(NOT_EVALUABLE, "historia corta")
    out = []
    for key, label in C["series"]:
        vals = [(r.get("year"), _num(r.get(key))) for r in h if _num(r.get(key)) is not None]
        if len(vals) < C["min_years"]:
            continue
        base_y, base = vals[-4]
        last = vals[-1][1]
        others = [v for y, v in vals if y != base_y]
        med = statistics.median(others)
        if base is None or base <= 0 or med <= 0 or last is None:
            continue
        cagr = (last / base) ** (1 / 3) - 1 if last > 0 else None
        if base / med >= C["min_factor"] and (cagr is None or cagr < 0):
            out.append(_violation(rule, base / med / C["min_factor"], f"{label}: base {base_y} = {base / med:.1f}× la "
                                  f"mediana del resto ({len(others)} años); CAGR 3 a {_pct(cagr) if cagr is not None else 'n.s.'}",
                                  "el detector de base anómala solo mira bases deprimidas (F12 · D2)", series=key,
                                  factor=base / med))
    return _result(rule, out)


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
    "caida_avisada": (caida_avisada, "F11 · T3: una caída fuerte en 1 año sale en las alertas"),
    "riesgo_critico_medido": (riesgo_critico_medido, "F11 · T3: cobertura no «alta» con el riesgo crítico sin medir"),
    "una_definicion_ttm_fy": (una_definicion_ttm_fy, "F11 · N2: el TTM y la serie anual con la misma definición"),
    "implicito_mismo_modelo": (implicito_mismo_modelo, "F11 · N1: retorno implícito con el modelo del justificado"),
    "cota_aplicada": (cota_aplicada, "F11 · T4: el crecimiento puntuado respeta su cota y su rótulo"),
    "referencia_representativa": (referencia_representativa, "F11 · T1: referencia que gana algo y de su región"),
    "voto_estable": (voto_estable, "F11 · F1: el DCF no vota si ±1 escalón de WACC cruza el precio"),
    "inverso_tasa_base": (inverso_tasa_base, "F11 · F2: DCF inverso «barata» solo con tasa base ≥ 50 %"),
    "convergencia_independiente": (convergencia_independiente, "F11 · T2: convergencia alta sin ancla compartida"),
    "calidad_sin_saturar": (calidad_sin_saturar, "F11 · F4: Calidad no al máximo con acumulaciones fallidas"),
    "forward_creible": (forward_creible, "F11 · F3: compresión del forward solo con crecimiento implícito creíble"),
    "beta_contrastada": (beta_contrastada, "F11 · T5: beta sustituta dentro de la propia ± 2 EE"),
    "causalidad_sostenida": (causalidad_sostenida, "F11 · T6: narrativa causal con su evidencia"),
    "metodo_citado_aplicable": (metodo_citado_aplicable, "F11 · T7: el PDF no cita métodos que su tipo excluye"),
    "rating_contable": (rating_contable, "F13 · [3]: rating sintético sin EBIT contable hundido sin caja"),
    "cautiva_separada": (cautiva_separada, "F13 · [8]: la deuda de la financiera cautiva no es deuda industrial"),
    "inverso_una_vez": (inverso_una_vez, "F13 · [1a]: el DCF inverso cuenta una sola vez en la convergencia"),
    "confianza_base_fragil": (confianza_base_fragil, "F13 · [1b]: confianza no alta con base frágil"),
    "ciclica_por_industria": (ciclica_por_industria, "F13 · [6]: productor de materias primas = cíclico"),
    "pico_ciclico": (pico_ciclico, "F13 · [6]: pico de beneficio en cíclicas sin esperar al consenso"),
    "referencia_acotada": (referencia_acotada, "F13 · [4]: referencia sin la empresa plausible"),
    "roe_bajo_coherente": (roe_bajo_coherente, "F13 · [4b]: sin «ROE bajo» con ROE ≥ Ke"),
    "roe_patrimonio_infimo": (roe_patrimonio_infimo, "F13 · [4c]: ROE n.s. con patrimonio ínfimo"),
    "utility_regulada": (utility_regulada, "F13 · [10a]: utility sin «destruye valor» por ROIC < WACC"),
    "normalizacion_utility": (normalizacion_utility, "F13 · [nuevo]: lo que la normalización quita a una utility"),
    "espectro_coherente": (espectro_coherente, "F13 · [9a]: espectro igual en todas las telecom"),
    "perimetro_corregido": (perimetro_corregido, "F13 · [5]: escisiones sin leerse como declive o ciclo"),
    "ffo_sin_saltos": (ffo_sin_saltos, "F13 · [10d]: serie de FFO por acción sin saltos ni negativos"),
    "abstencion_sin_datos": (abstencion_sin_datos, "F13 · [11b]: sin veredicto de precio sin perfil ni historial"),
    "beta_sin_signo_negativo": (beta_sin_signo_negativo, "F13 · [nuevo]: beta negativa fuera del Ke"),
    "flujo_por_intensidad": (flujo_por_intensidad, "F13 · [2]: flujo del DCF según la intensidad inversora"),
    "crecimiento_dcf_representativo": (crecimiento_dcf_representativo, "F13 · [7a]: DCF extremo con ventas lejos del BPA"),
    "base_inflada": (base_inflada, "F13 · paso 12: crecimiento desde una base inflada"),
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
