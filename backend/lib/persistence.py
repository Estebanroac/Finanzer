"""
Persistencia del tramo alto de la calidad (fase 4, T1; PLAN_FIABILIDAD §4.1: "100 debe ser raro").

Una categoría llega hoy a 20/20 con las cifras del último ejercicio. Lo extraordinario no es un buen año: es un buen
negocio sostenido (Mauboussin, persistencia del ROIC). La calidad por encima del codo (80, `quality_persistence.knee`;
hasta F8 · E11 era el umbral de "excelente", que ahora es 85) solo cuenta en proporción a la persistencia de las
categorías que la llevan ahí:

    calidad = 80 + (calidad − 80) × persistencia

donde la persistencia es la media de la de cada categoría ponderada por sus puntos por encima de 16/20 (su parte del
tramo alto). Hasta el codo no cambia; lo que está por encima (lo extraordinario) exige historia. Cada categoría mide su
ancla en los últimos `window` ejercicios:

  · **Rentabilidad**: el margen operativo de cada ejercicio es positivo y al menos `margin_ratio` del actual (¿es el
    margen de hoy un pico o lo de siempre?). En financieras, el margen neto (sin beneficio operativo).
  · **Crecimiento**: los ingresos crecen frente al ejercicio anterior (crecimiento compuesto sin retrocesos).
  · **Calidad de ganancias**: el flujo operativo cubre el beneficio neto y el FCF es positivo (beneficio que se
    convierte en caja). En financieras, sin pérdidas (su flujo operativo no mide la calidad del beneficio).
  · **Solidez**: sin ancla. La historia de EDGAR no trae el balance de cada ejercicio, y la solidez es un estado del
    balance de hoy: pondera con persistencia 1, y se dice.

Persistencia = ejercicios que cumplen / ejercicios de la ventana. Un ejercicio sin dato no prueba nada: cuenta como
no cumplido (sin historia no se puede afirmar lo extraordinario). Los ejercicios con cambio de perímetro (operaciones
discontinuadas materiales) salen de la ventana. Historia anual de EDGAR (`info["_history_fy"]`) o, sin ella, la de los
estados de Yahoo (4 ejercicios: la persistencia queda acotada y se dice).
"""
from typing import Any, Dict, List, Optional, Tuple

from cyclicality import _series, perimeter_years
from settings import cfg

FINANCIAL = "FINANCIAL"
_CATS = ("Rentabilidad", "Crecimiento", "Calidad de Ganancias")


def _cfg(key: str):
    return cfg(f"thresholds.quality_persistence.{key}")


_STMT_FIELDS = (("revenue", "revenue", "inc"), ("operating_income", "operating_income", "inc"),
                ("net_income", "net_income", "inc"), ("operating_cash_flow", "operating_cash_flow", "cf"),
                ("capex", "capital_expenditure", "cf"))


def history_from_statements(st: Dict[str, Any]) -> Dict[str, Any]:
    """Historia con la forma de lib/sec_edgar.annual_history desde los estados anuales de Yahoo (más reciente
    primero; `inc_ends` / `cf_ends` son las fechas de cierre, o los ejercicios `*_years` si no las hay)."""
    st = st or {}
    out: Dict[str, Any] = {}
    for field, src, stmt in _STMT_FIELDS:
        vals = st.get(src) or []
        ends = st.get(f"{stmt}_ends") or [f"{y}-12-31" if y is not None else None for y in st.get(f"{stmt}_years") or []]
        out[field] = {"values": [{"fy_end": str(e)[:10], "value": abs(v) if field == "capex" else v}
                                 for e, v in zip(ends, vals) if e and v is not None]}
    return out


# F8 (historia de 10 años): campos cuya definición depende del emisor (el resultado operativo que presenta, su capex).
# Si EDGAR no los trae, no se completan con los de Yahoo (que los calcula a su manera): la persistencia no se mide
# sobre ellos y lo dice (Rentabilidad: margen neto; Calidad de ganancias: sin la prueba del FCF).
EDGAR_ONLY = ("operating_income", "capex")


def merge_history(hist: Optional[Dict[str, Any]], st: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """La historia de EDGAR completada con los estados en los ejercicios que no trae (un concepto que deja de
    usarse, como los ingresos IFRS de un banco desde 2018: SAN). Un ejercicio de los estados se añade si ninguno de
    EDGAR cierra a menos de medio año de él. Los campos de EDGAR_ONLY no se completan."""
    from cyclicality import fiscal_years_between
    out = {k: {"values": list((v or {}).get("values") or []), "reason": (v or {}).get("reason")}
           for k, v in (hist or {}).items()}
    for field, items in history_from_statements(st).items():
        if field in EDGAR_ONLY and hist:
            continue
        cur = out.setdefault(field, {"values": []})["values"]
        have = [x["fy_end"] for x in cur]
        for x in items["values"]:
            if not any(fiscal_years_between(min(h, x["fy_end"]), max(h, x["fy_end"])) == 0 for h in have):
                cur.append(x)
    return out


def _last(series: List[Tuple[str, float]], n: int) -> List[Tuple[str, float]]:
    return series[-n:] if n > 0 else []


def _year(e: str) -> str:
    return e[:4]


def measure(hist: Optional[Dict[str, Any]], archetype: str, source: str,
            not_applicable: tuple = (), roe_by_year: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """{categoría: {persistence, years_ok, years, anchor, text}} para las categorías con ancla, más `window`,
    `source` y `perimeter` (ejercicios fuera de la ventana).

    F11 · T7 (revisión de NU): una financiera cuyo subtipo no admite el margen neto (`not_applicable`, el de
    classify.subtype_not_applicable: banco) ancla la Rentabilidad en su ROE de cada ejercicio (`roe_by_year`, el de
    archetype_metrics); sin él, la Rentabilidad no se mide (nunca con una métrica «No aplica»)."""
    window = int(_cfg("window"))
    ratio = float(_cfg("margin_ratio"))
    fin = archetype == FINANCIAL
    hist = hist or {}
    out: Dict[str, Any] = {"window": window, "source": source}
    # Ejercicios canónicos: un cierre por año fiscal con dato en cualquier serie (EDGAR y los estados pueden fechar
    # el mismo ejercicio con días de diferencia). Cada serie se lee por ejercicio, no por la fecha exacta.
    from cyclicality import fiscal_years_between
    _all = sorted({e for f in ("revenue", "operating_income", "net_income", "operating_cash_flow")
                   for e, _v in _series(hist, f)})
    canon: List[str] = []
    for e in reversed(_all):
        if not any(fiscal_years_between(min(e, x), max(e, x)) == 0 for x in canon):
            canon.append(e)
    canon.sort()

    def _canon(e: str) -> Optional[str]:
        return next((c for c in canon if fiscal_years_between(min(e, c), max(e, c)) == 0), None)

    def fy(field: str) -> Dict[str, float]:
        return {c: v for c, v in ((_canon(e), v) for e, v in _series(hist, field)) if c is not None}

    cuts = {c for c in (_canon(e) for e in perimeter_years(
        hist, cfg("sectors.archetypes.cyclicality.discontinued_material_share"))) if c}
    out["perimeter"] = sorted(_year(e) for e in cuts)
    # Ventana: los `window` últimos ejercicios (una serie que se corta, como los ingresos IFRS de un banco, no ancla
    # la ventana en el pasado), sin los de cambio de perímetro.
    # Los `window` últimos ejercicios fiscales (por fecha): un año sin dato en ninguna serie cuenta y no cumple.
    ends = [e for e in canon if fiscal_years_between(e, canon[-1]) < window] if canon else []
    evaluable = [e for e in ends if e not in cuts]
    den = len(evaluable) + (window - len(ends))   # sin dato: cuenta y no cumple
    if den <= 0:
        return out
    rv = fy("revenue")

    if fin and "net_margin" in not_applicable:
        _rentabilidad_roe(out, roe_by_year, _canon, ends, evaluable, den, ratio)
    else:
        _rentabilidad_margen(out, fy, rv, fin, ends, evaluable, den, ratio)

    # Crecimiento: ingresos por encima del ejercicio anterior.
    # El ejercicio anterior, solo si es el inmediato (revisión F4, hallazgo 7: con un año sin dato no se compara con
    # el de dos años antes).
    prev = {c1: rv[c0] for c0, c1 in zip(canon, canon[1:]) if c0 in rv and fiscal_years_between(c0, c1) == 1}
    ok = [e for e in evaluable if prev.get(e) and e in rv and rv[e] > prev[e]]
    out["Crecimiento"] = {"persistence": len(ok) / den, "years_ok": [_year(e) for e in sorted(ok)],
                          "years": [_year(e) for e in evaluable], "anchor": "ingresos",
                          "rule": "ingresos por encima del ejercicio anterior"}
    _calidad(out, fy, fin, evaluable, den)
    out["denominator"] = den
    return out


def _rentabilidad_roe(out, roe_by_year, _canon, ends, evaluable, den, ratio) -> None:
    """F11 · T7: ROE de cada ejercicio frente al del último (sin él, la Rentabilidad no se mide)."""
    roe = {c: x["roe"] for c, x in ((_canon(x["fy_end"]), x) for x in roe_by_year or []) if c is not None}
    all_r = {e: roe[e] for e in ends if e in roe}
    if not all_r:
        return
    last = all_r[max(all_r)]
    ok = [e for e, r in all_r.items() if e in evaluable and last > 0 and r > 0 and r >= ratio * last]
    out["Rentabilidad"] = {
        "persistence": len(ok) / den, "years_ok": [_year(e) for e in sorted(ok)],
        "years": [_year(e) for e in evaluable], "anchor": "ROE",
        "rule": f"ROE positivo y al menos el {ratio:.0%} del último ({_pct(last)})"}


def _rentabilidad_margen(out, fy, rv, fin, ends, evaluable, den, ratio) -> None:
    # Rentabilidad: margen de cada ejercicio frente al del último.
    num = fy("net_income" if fin else "operating_income")
    no_op = None
    if not fin and len([e for e in evaluable if e in num]) < 2:          # sin operativo en la historia: margen neto
        num, fin_margin = fy("net_income"), True
        no_op = "sin resultado operativo en la SEC"
    else:
        fin_margin = fin
    # El margen de referencia es el del último ejercicio con dato, aunque sea de cambio de perímetro: es el negocio de
    # hoy. Cumplen los ejercicios evaluables.
    all_m = {e: num[e] / rv[e] for e in ends if e in num and rv.get(e)}
    last = all_m[max(all_m)] if all_m else None
    margins = {e: m for e, m in all_m.items() if e in evaluable}
    ok = [e for e, m in margins.items() if last is not None and last > 0 and m > 0 and m >= ratio * last]
    lab = "margen neto" if fin_margin else "margen operativo"
    out["Rentabilidad"] = {
        "persistence": len(ok) / den, "years_ok": [_year(e) for e in sorted(ok)],
        "years": [_year(e) for e in evaluable], "anchor": lab,
        "rule": ((f"{lab} positivo y al menos el {ratio:.0%} del último ({_pct(last)})" if last is not None
                  else f"{lab} (sin dato en la ventana)") + (f" ({no_op})" if no_op else ""))}


def _calidad(out, fy, fin, evaluable, den) -> None:
    # Calidad de ganancias: el beneficio se convierte en caja.
    ni = fy("net_income")
    if fin:
        ok = [e for e in evaluable if ni.get(e) is not None and ni[e] > 0]
        rule = "beneficio neto positivo (sin pérdidas)"
    else:
        ocf, capex = fy("operating_cash_flow"), fy("capex")
        if evaluable and not any(e in capex for e in evaluable):
            # F8: sin capex en la SEC en toda la ventana (conceptos propios del emisor), la prueba del FCF no se hace:
            # sin dato no es «no cumple».
            ok = [e for e in evaluable if ocf.get(e) is not None and ni.get(e) is not None and ocf[e] >= ni[e]]
            rule = "flujo operativo ≥ beneficio neto (FCF sin dato: el capex no está en la SEC con un concepto estándar)"
        else:
            ok = [e for e in evaluable if ocf.get(e) is not None and ni.get(e) is not None and capex.get(e) is not None
                  and ocf[e] >= ni[e] and ocf[e] - abs(capex[e]) > 0]
            rule = "flujo operativo ≥ beneficio neto y FCF positivo"
    out["Calidad de Ganancias"] = {"persistence": len(ok) / den, "years_ok": [_year(e) for e in sorted(ok)],
                                   "years": [_year(e) for e in evaluable], "anchor": "conversión en caja",
                                   "rule": rule}


def _pct(x: Optional[float]) -> str:
    return "—" if x is None else f"{x * 100:.1f}%".replace("-", "−")


def adjust_quality(q: Dict[str, Any], categories: List[Dict[str, Any]], meas: Optional[Dict[str, Any]]) -> None:
    """Limita la calidad por encima del codo (`quality_persistence.knee`) a la persistencia (in situ en `q`): `score_before`, `persistence`
    (ponderada), `by_category` y la frase `text`."""
    if not meas or q.get("score") is None:
        return
    # F8 · E11: el codo es suyo (80), no el umbral de «excelente»: subir la etiqueta no afloja la persistencia.
    top = cfg("thresholds.quality_persistence.knee")
    knee = top * cfg("thresholds.score.category.max") / cfg("thresholds.score.total.max")
    inc = [c for c in categories if c.get("category") in cfg("thresholds.score.quality.categories")
           and c.get("conclusive", True) and c.get("applicable", True)]
    rows, wsum, psum = [], 0.0, 0.0
    for c in inc:
        surplus = max(0.0, float(c.get("score") or 0) - knee)
        m = meas.get(c["category"])
        p = m["persistence"] if m else 1.0
        rows.append({"category": c["category"], "surplus": surplus, "persistence": p if m else None,
                     "years_ok": (m or {}).get("years_ok"), "rule": (m or {}).get("rule"),
                     "anchor": (m or {}).get("anchor")})
        wsum += surplus
        psum += surplus * p
    s = q["score"]
    q["persistence"] = {"by_category": rows, "window": meas.get("window"), "denominator": meas.get("denominator"),
                        "source": meas.get("source"), "applied": False}
    if s <= top or wsum <= 0:
        return
    p = psum / wsum
    new = round(top + (s - top) * p)
    q["persistence"].update(weighted=p, score_before=s, applied=new < s)
    if new < s:
        q["score"] = new
        n = meas.get("denominator")
        parts = [f"{r['category'].lower()}: {r['rule']} en {len(r['years_ok'] or [])} de {n} ejercicios"
                 for r in rows if r["surplus"] > 0 and r["persistence"] is not None and r["persistence"] < 1]
        # F10 · N6 (revisión de NVDA): el codo nombra su umbral, que no es el de «excelente» (desde F8 · E11).
        exc = cfg("thresholds.score.quality.bands")[0]
        q["persistence"]["short"] = (f"Por encima de {top:.0f} (umbral de persistencia; «excelente» empieza en "
                                     f"{exc:.0f}), la calidad exige persistencia: {s} → {new}.")
        body = "; ".join(parts)
        t = q["persistence"]["short"] + " " + body[:1].upper() + body[1:] + "."
        if meas.get("source") == "estados":
            t += " Sin la historia de la SEC, con los 4 ejercicios de los estados: la persistencia queda acotada."
        q["persistence"]["text"] = t
