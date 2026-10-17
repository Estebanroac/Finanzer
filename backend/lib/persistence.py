"""
Persistencia del tramo alto de la calidad (fase 4, T1; PLAN_FIABILIDAD §4.1: "100 debe ser raro").

Una categoría llega hoy a 20/20 con las cifras del último ejercicio. Lo extraordinario no es un buen año: es un buen
negocio sostenido (Mauboussin, persistencia del ROIC). La calidad por encima del umbral de "excelente" (80, la primera
banda de score.quality) solo cuenta en proporción a la persistencia de las categorías que la llevan ahí:

    calidad = 80 + (calidad − 80) × persistencia

donde la persistencia es la media de la de cada categoría ponderada por sus puntos por encima de 16/20 (su parte del
tramo alto). "Excelente" no cambia; lo que está por encima (lo extraordinario) exige historia. Cada categoría mide su
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


def history_from_statements(st: Dict[str, Any]) -> Dict[str, Any]:
    """Historia con la forma de lib/sec_edgar.annual_history desde los estados anuales de Yahoo (más reciente
    primero; `inc_years` / `cf_years` son los ejercicios)."""
    st = st or {}
    out: Dict[str, Any] = {}
    for field, src, yk in (("revenue", "revenue", "inc_years"), ("operating_income", "operating_income", "inc_years"),
                           ("net_income", "net_income", "inc_years"),
                           ("operating_cash_flow", "operating_cash_flow", "cf_years"),
                           ("capex", "capital_expenditure", "cf_years")):
        vals, yrs = st.get(src) or [], st.get(yk) or []
        out[field] = {"values": [{"fy_end": f"{y}-12-31", "value": abs(v) if field == "capex" else v}
                                 for y, v in zip(yrs, vals) if y is not None and v is not None]}
    return out


def _last(series: List[Tuple[str, float]], n: int) -> List[Tuple[str, float]]:
    return series[-n:] if n > 0 else []


def _year(e: str) -> str:
    return e[:4]


def measure(hist: Optional[Dict[str, Any]], archetype: str, source: str) -> Dict[str, Any]:
    """{categoría: {persistence, years_ok, years, anchor, text}} para las categorías con ancla, más `window`,
    `source` y `perimeter` (ejercicios fuera de la ventana)."""
    window = int(_cfg("window"))
    ratio = float(_cfg("margin_ratio"))
    fin = archetype == FINANCIAL
    hist = hist or {}
    cuts = set(perimeter_years(hist, cfg("sectors.archetypes.cyclicality.discontinued_material_share")))
    rev = _series(hist, "revenue")
    out: Dict[str, Any] = {"window": window, "source": source, "perimeter": sorted(_year(e) for e in cuts)}
    # Ventana: los `window` últimos ejercicios con ingresos, sin los de cambio de perímetro.
    ends = [e for e, _ in rev][-window:]
    evaluable = [e for e in ends if e not in cuts]
    den = len([e for e in ends if e not in cuts]) + (window - len(ends))   # sin dato: cuenta y no cumple
    if den <= 0:
        return out
    rv = dict(rev)

    # Rentabilidad: margen de cada ejercicio frente al del último.
    num = dict(_series(hist, "net_income" if fin else "operating_income"))
    if not fin and len([e for e in evaluable if e in num]) < 2:          # sin operativo en la historia: margen neto
        num, fin_margin = dict(_series(hist, "net_income")), True
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
        "rule": f"{lab} positivo y al menos el {ratio:.0%} del último ({_pct(last)})" if last is not None else None}

    # Crecimiento: ingresos por encima del ejercicio anterior.
    prev = {}
    for (_e0, v0), (e1, _v1) in zip(rev, rev[1:]):
        prev[e1] = v0
    ok = [e for e in evaluable if e in prev and prev[e] and rv[e] > prev[e]]
    out["Crecimiento"] = {"persistence": len(ok) / den, "years_ok": [_year(e) for e in sorted(ok)],
                          "years": [_year(e) for e in evaluable], "anchor": "ingresos",
                          "rule": "ingresos por encima del ejercicio anterior"}

    # Calidad de ganancias: el beneficio se convierte en caja.
    ni = dict(_series(hist, "net_income"))
    if fin:
        ok = [e for e in evaluable if ni.get(e) is not None and ni[e] > 0]
        rule = "beneficio neto positivo (sin pérdidas)"
    else:
        ocf, capex = dict(_series(hist, "operating_cash_flow")), dict(_series(hist, "capex"))
        ok = [e for e in evaluable if ocf.get(e) is not None and ni.get(e) is not None and capex.get(e) is not None
              and ocf[e] >= ni[e] and ocf[e] - abs(capex[e]) > 0]
        rule = "flujo operativo ≥ beneficio neto y FCF positivo"
    out["Calidad de Ganancias"] = {"persistence": len(ok) / den, "years_ok": [_year(e) for e in sorted(ok)],
                                   "years": [_year(e) for e in evaluable], "anchor": "conversión en caja",
                                   "rule": rule}
    out["denominator"] = den
    return out


def _pct(x: Optional[float]) -> str:
    return "—" if x is None else f"{x * 100:.1f}%".replace("-", "−")


def adjust_quality(q: Dict[str, Any], categories: List[Dict[str, Any]], meas: Optional[Dict[str, Any]]) -> None:
    """Limita la calidad por encima de "excelente" a la persistencia (in situ en `q`): `score_before`, `persistence`
    (ponderada), `by_category` y la frase `text`."""
    if not meas or q.get("score") is None:
        return
    top = cfg("thresholds.score.quality.bands")[0]
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
        q["persistence"]["short"] = f"Por encima de {top:.0f}, la calidad exige persistencia: {s} → {new}."
        body = "; ".join(parts)
        t = q["persistence"]["short"] + " " + body[:1].upper() + body[1:] + "."
        if meas.get("source") == "estados":
            t += " Sin la historia de la SEC, con los 4 ejercicios de los estados: la persistencia queda acotada."
        q["persistence"]["text"] = t
