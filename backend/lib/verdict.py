"""
Calidad del negocio y atractivo del precio (etapa 9a; spec fallo 6, cambio 4).

Dos puntuaciones 0–100, nunca un escalar único:
  · Calidad  = Solidez + Rentabilidad + Calidad de ganancias + Crecimiento.
  · Precio   = Valoración (múltiplos + aporte acotado del DCF).
Cada una se reescala a 100 sobre sus categorías concluyentes y aplicables (el
mecanismo de cobertura y "no aplica" de las etapas 5–6). Sin ninguna, sin dato.

El precio se CONTRAE hacia el neutro según la confianza del veredicto de
valoración: mostrado = 50 + (crudo − 50) × factor (1.0 alta, 0.75 media, 0.5
baja). F8 · E11: la calidad se contrae solo con confianza baja (factor 0.85); antes
no se contraía nunca.

Veredicto verbal: "Calidad [nivel] · precio [nivel]" + la confianza con su motivo
principal, p. ej. "(confianza media: el DCF directo y los múltiplos discrepan)".
"""
from typing import Any, Dict, List, Optional

from settings import cfg


def _level(value: Optional[float], bands, labels) -> Optional[str]:
    if value is None:
        return None
    return next((labels[i] for i, b in enumerate(bands) if value >= b), labels[-1])


def border(value: Optional[float], bands, labels) -> Optional[Dict[str, Any]]:
    """Fase 4 (T2; mapa, efecto frontera de NVO): el nivel vecino si `value` está a `border_points` o menos de un
    umbral. Un cambio pequeño en los datos o en los supuestos (10 pb de Rf) cambiaría el nivel: se dice."""
    if value is None:
        return None
    k = cfg("thresholds.score.border_points")
    best = None
    for i, b in enumerate(bands):
        d = value - b
        # puntos que faltan para cruzar (el umbral pertenece a la banda alta): por encima, bajar d + 1; por debajo, −d
        pts = int(round(d + 1 if d >= 0 else -d))
        if pts <= k and (best is None or pts < best[0]):
            # por encima del umbral i, el vecino es la banda de abajo (i + 1); por debajo, la de arriba (i)
            best = (pts, labels[i + 1] if d >= 0 else labels[i])
    if best is None:
        return None
    pts, nb = best
    return {"neighbor": nb, "points": pts,
            "text": f"En la frontera con «{nb}» (a {pts} punto{'s' if pts != 1 else ''}): "
                    "un cambio pequeño en los datos o en los supuestos cambiaría el nivel"}


def part_score(categories: List[Dict[str, Any]], names: List[str]) -> Dict[str, Any]:
    """Reescala a 0–100 las categorías `names` concluyentes y aplicables."""
    mx = cfg("thresholds.score.category.max")
    cats = [c for c in categories if c.get("category") in names]
    inc = [c for c in cats if c.get("conclusive", True) and c.get("applicable", True)]
    score = round(sum(c["score"] for c in inc) * cfg("thresholds.score.total.max") / (mx * len(inc))) if inc else None
    excluded = [c["category"] for c in cats if c.get("applicable", True) and not c.get("conclusive", True)]
    not_app = [c["category"] for c in cats if not c.get("applicable", True)]
    low = [c["category"] for c in inc if (c.get("coverage") or {}).get("low_confidence")]
    return {
        "score": score,
        "components": [{"category": c["category"], "score": c["score"], "max": c.get("max_score", mx),
                        "included": c in inc} for c in cats],
        "categories_included": len(inc), "categories_total": len(cats),
        "partial": bool(cats) and len(inc) < len(cats),
        "basis": (f"calculado sobre {len(inc)} de {len(cats)} categorías" if cats and len(inc) < len(cats)
                  else None),
        "excluded_categories": excluded, "not_applicable_categories": not_app,
        "low_coverage_categories": low,
    }


def quality(categories: List[Dict[str, Any]]) -> Dict[str, Any]:
    Q = cfg("thresholds.score.quality")
    q = part_score(categories, Q["categories"])
    q["level"] = _level(q["score"], Q["bands"], Q["labels"])
    q["border"] = border(q["score"], Q["bands"], Q["labels"])
    reasons = []
    if q["excluded_categories"]:
        reasons.append("categorías no concluyentes: " + ", ".join(q["excluded_categories"]))
    if q["low_coverage_categories"]:
        reasons.append("cobertura baja en " + ", ".join(q["low_coverage_categories"]))
    q["low_confidence"] = bool(reasons)
    q["low_confidence_reasons"] = reasons
    return q


def contract_quality(q: Dict[str, Any], confidence_level: Optional[str]) -> Dict[str, Any]:
    """F8 · E11 (auditoría del 26-oct, XOM: confianza baja con calidad 82 «excelente» sin contraer): con confianza
    baja la calidad también se contrae hacia el neutro, mostrada = 50 + (cruda − 50) × factor
    (`thresholds.score.quality.confidence_factor`; solo baja). Idempotente: parte siempre de la cruda."""
    Q = cfg("thresholds.score.quality")
    raw = q.get("score_raw", q.get("score"))
    factor = Q["confidence_factor"].get(confidence_level) if confidence_level else None
    shown = None if raw is None else (raw if factor is None else round(Q["neutral"] + (raw - Q["neutral"]) * factor))
    return {**q, "score_raw": raw, "score": shown, "factor": factor, "contracted": raw is not None and shown != raw,
            "level": _level(shown, Q["bands"], Q["labels"]), "level_raw": _level(raw, Q["bands"], Q["labels"]),
            "border": border(shown, Q["bands"], Q["labels"])}


def price_contraction_basis(conf: Optional[Dict[str, Any]], categories: List[Dict[str, Any]]) -> Optional[str]:
    """Revisión de COST (hallazgo 4): la confianza con la que se contraen el precio y la calidad hacia 50. Solo contraen
    los limitadores que contradicen el veredicto o lo vuelven incierto (discrepancia entre métodos, datos débiles,
    dependencia de Ke); uno que apunta en su misma dirección no. El escalón de las tasas base (F10 · N4) apunta a «caro»:
    no contrae un precio crudo por debajo del neutro (lo acercaría a 50: más atractivo) y sí uno por encima, al que
    contradice."""
    c = conf or {}
    basis = c.get("contraction_basis") or c.get("level")
    if not c.get("base_rate_step") or basis == c.get("level"):
        return basis
    P = cfg("thresholds.score.price")
    raw = part_score(categories, P["categories"]).get("score")
    return c["level"] if raw is not None and raw > P["neutral"] else basis


def price(categories: List[Dict[str, Any]], confidence_level: Optional[str],
          methods: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Precio crudo, factor de la confianza y precio mostrado (contraído hacia el neutro).
    F15 · R11 (regla global de las expectativas golden): ningún método solo lleva el precio a «muy exigente». Si menos de
    dos métodos evaluables de la convergencia la ven cara, el precio crudo no baja del umbral de «exigente» (DLR: P/FFO y
    EV/EBITDA, un solo método, «muy exigente» con el DCF inverso en precio)."""
    P = cfg("thresholds.score.price")
    p = part_score(categories, P["categories"])
    raw = p.pop("score")
    if raw is not None and methods is not None and raw < P["bands"][-1]:
        n_cara = sum(1 for m in methods if m.get("evaluable") and m.get("direction") == "cara")
        if n_cara < P["very_demanding_min_methods"]:
            p["single_method_floor"] = {"from": raw, "to": P["bands"][-1], "methods_cara": n_cara}
            raw = P["bands"][-1]
    factor = P["confidence_factor"].get(confidence_level) if confidence_level else None
    shown = None if raw is None else (raw if factor is None else round(P["neutral"] + (raw - P["neutral"]) * factor))
    p.update(score_raw=raw, score=shown, factor=factor, confidence=confidence_level,
             contracted=(raw is not None and shown != raw),
             level=_level(shown, P["bands"], P["labels"]), level_raw=_level(raw, P["bands"], P["labels"]),
             border=border(shown, P["bands"], P["labels"]))
    return p


def abstention(price_history: Optional[Dict[str, Any]], sector: Optional[str]) -> Optional[str]:
    """F13 · paso 8: motivo para no dar veredicto de precio, o None. El precio no es de hoy si la cotización lleva más
    de `abstain_stale_days` sin sesiones frente al mercado, o si no hay perfil ni `abstain_min_sessions` sesiones (EA y
    WBD: empresas en una operación corporativa, con un solo precio de hace meses)."""
    import datetime as _dt
    P = cfg("thresholds.score.price")
    ph = price_history or {}
    last, mkt = ph.get("last_date"), (ph.get("market") or {}).get("last_date")
    if last and mkt:
        gap = (_dt.date.fromisoformat(str(mkt)[:10]) - _dt.date.fromisoformat(str(last)[:10])).days
        if gap > P["abstain_stale_days"]:
            import numfmt
            return (f"la cotización no tiene sesiones desde el {numfmt.date_long(str(last)[:10])}, {gap} días antes que "
                    "el mercado: el precio no es de hoy y no se compara con el valor")
    rows = ph.get("rows")
    if str(sector or "") in ("", "Unknown") and rows is not None and rows < P["abstain_min_sessions"]:
        return (f"sin perfil de la empresa y con {rows} sesiones de historial de precios (hacen falta "
                f"{P['abstain_min_sessions']}): no hay base para un veredicto de precio")
    return None


def abstain(p: Dict[str, Any], reason: str) -> Dict[str, Any]:
    """El precio sin veredicto (nivel y puntuación vacíos), con su motivo; la puntuación cruda queda como referencia."""
    return {**p, "score": None, "level": None, "level_raw": None, "border": None, "contracted": False,
            "abstained": reason}


def reprice(p: Dict[str, Any], confidence_level: Optional[str]) -> Dict[str, Any]:
    """F8 · E1: el mismo precio crudo con otra confianza (la prueba de sensibilidad de Ke la baja un escalón)."""
    if p.get("abstained"):          # F13 · paso 8: sin veredicto de precio no hay nada que recalcular
        return {**p, "confidence": confidence_level}
    if p.get("rule") == "L1":       # F16: la confianza no mueve el precio
        # Fase 1 · pendientes (7-nov-2026): la lectura de valoración sí se reevalúa con la confianza nueva, como en la
        # versión probada (A): la alerta de valoración extrema se dispara con esa lectura (lib/alert_groups.py)
        rd = p.get("valuation_reading")
        return {**p, "confidence": confidence_level,
                **({"valuation_reading": reprice(rd, confidence_level)} if rd else {})}
    P = cfg("thresholds.score.price")
    raw = p.get("score_raw")
    factor = P["confidence_factor"].get(confidence_level) if confidence_level else None
    shown = None if raw is None else (raw if factor is None else round(P["neutral"] + (raw - P["neutral"]) * factor))
    return {**p, "score": shown, "factor": factor, "confidence": confidence_level,
            "contracted": (raw is not None and shown != raw), "level": _level(shown, P["bands"], P["labels"]),
            "border": border(shown, P["bands"], P["labels"])}


def confidence_phrase(conf: Optional[Dict[str, Any]]) -> Optional[str]:
    """Motivo principal de la confianza en lenguaje llano (para el veredicto)."""
    if not conf or not conf.get("level"):
        return None
    dims = conf.get("dimensions") or {}
    conv = dims.get("convergence") or {}
    ev = [m for m in conv.get("methods") or [] if m.get("evaluable")]
    methods = [m["method"] for m in ev]
    # PM (V7): siempre de qué DCF se habla («el DCF directo», como la fila de la tarjeta; el inverso ya se nombra así)
    names = {"DCF": "el DCF directo", "múltiplos frente al sector": "los múltiplos",
             "P/B justificado (Gordon)": "el P/B justificado", "P/B frente al sector": "el P/B del sector"}
    pair = " y ".join(names.get(m, m) for m in methods)
    dirs = [m.get("direction") for m in ev]
    lvl = conv.get("level")
    if conf["level"] == "alta":
        return f"{pair} coinciden" if pair else "los métodos coinciden"
    if conf.get("ke_dependent"):
        return "el nivel de precio cambia con ±1 pp de coste del capital"
    if conf.get("base_rate_step") and conf.get("contraction_basis") != conf["level"]:
        # F10 · N4: el escalón de las tasas base es lo que la bajó
        return "casi ninguna comparable sostuvo el crecimiento que exige el precio"
    if lvl == "baja":
        return f"{pair} discrepan"
    if lvl == "no_evaluable":
        return "un solo método de valoración evaluable, sin contraste"
    for key, txt in (("source", "datos de fuente con incidencias"), ("stability", "negocio cíclico"),
                     ("coverage", "cobertura de datos parcial")):
        if (dims.get(key) or {}).get("level") == "baja":
            return txt
    if lvl == "media":
        if len(set(dirs)) > 1 and all(dirs):         # uno en precio y otro con dirección
            return " y ".join(f"{names.get(m['method'], m['method'])} {'la ve' if i == 0 else ''} {m['direction']}"
                              .replace("  ", " ") for i, m in enumerate(ev))
        return f"{pair} coinciden en dirección pero no en magnitud" if pair else "convergencia parcial"
    if (dims.get("source") or {}).get("level") == "media":
        return "datos de fuente con incidencias"
    return "convergencia parcial"


def verdict(q: Dict[str, Any], p: Dict[str, Any], conf: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """F14 · paso 4 (segunda revisión externa, 2.2): si la contracción hacia 50 cambia la banda del precio, el veredicto
    dice las dos («precio entre razonable y atractivo»): con confianza baja, «razonable» se leía como un precio justo
    cuando era «no se puede decidir» (VZ, CSCO y BRK-B venían de «exigente»; T y NUE, de «atractivo»)."""
    ql, pl = q.get("level"), p.get("level")
    pr = p.get("level_raw") if (p.get("contracted") and p.get("level_raw") not in (None, pl)) else None
    l1_none = p.get("rule") == "L1" and not pl and bool(p.get("reason"))     # F16: sin P/E, sin veredicto y el motivo
    ptxt = f"entre {pl} y {pr}" if (pl and pr) else (pl or ('sin veredicto' if (p.get('abstained') or l1_none)
                                                            else 'sin dato'))
    text = f"Calidad {ql or 'sin dato'} · precio {ptxt}"
    # Fase 1 · pendientes (decisión del usuario, 7-nov-2026): la consistencia (dos niveles), no la confianza
    import consistency as _cons
    cons = _cons.compute(conf)
    ctext = _cons.text(cons)
    if p.get("abstained"):          # F13 · paso 8: el motivo de la abstención, no la confianza de un precio que no hay
        ctext = f"({p['abstained']})"
    elif l1_none:
        ctext = f"({p['reason']})"
    return {"text": text, "confidence_text": ctext, "full": text + (f" {ctext}" if ctext else ""),
            "quality_level": ql, "price_level": pl, "price_level_raw": pr,
            "consistency": (cons or {}).get("level")}
