"""
Calidad del negocio y atractivo del precio (etapa 9a; spec fallo 6, cambio 4).

Dos puntuaciones 0–100, nunca un escalar único:
  · Calidad  = Solidez + Rentabilidad + Calidad de ganancias + Crecimiento.
  · Precio   = Valoración (múltiplos + aporte acotado del DCF).
Cada una se reescala a 100 sobre sus categorías concluyentes y aplicables (el
mecanismo de cobertura y "no aplica" de las etapas 5–6). Sin ninguna, sin dato.

El precio se CONTRAE hacia el neutro según la confianza del veredicto de
valoración: mostrado = 50 + (crudo − 50) × factor (1.0 alta, 0.75 media, 0.5
baja). La calidad no se contrae por la convergencia de métodos: solo se marca de
baja confianza si su cobertura es baja (etapa 5).

Veredicto verbal: "Calidad [nivel] · precio [nivel]" + la confianza con su motivo
principal, p. ej. "(confianza media: el DCF y los múltiplos discrepan)".
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
            "text": f"en la frontera con «{nb}» (a {pts} punto{'s' if pts != 1 else ''}): "
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


def price(categories: List[Dict[str, Any]], confidence_level: Optional[str]) -> Dict[str, Any]:
    """Precio crudo, factor de la confianza y precio mostrado (contraído hacia el neutro)."""
    P = cfg("thresholds.score.price")
    p = part_score(categories, P["categories"])
    raw = p.pop("score")
    factor = P["confidence_factor"].get(confidence_level) if confidence_level else None
    shown = None if raw is None else (raw if factor is None else round(P["neutral"] + (raw - P["neutral"]) * factor))
    p.update(score_raw=raw, score=shown, factor=factor, confidence=confidence_level,
             contracted=(raw is not None and shown != raw),
             level=_level(shown, P["bands"], P["labels"]), level_raw=_level(raw, P["bands"], P["labels"]),
             border=border(shown, P["bands"], P["labels"]))
    return p


def confidence_phrase(conf: Optional[Dict[str, Any]]) -> Optional[str]:
    """Motivo principal de la confianza en lenguaje llano (para el veredicto)."""
    if not conf or not conf.get("level"):
        return None
    dims = conf.get("dimensions") or {}
    conv = dims.get("convergence") or {}
    ev = [m for m in conv.get("methods") or [] if m.get("evaluable")]
    methods = [m["method"] for m in ev]
    names = {"DCF": "el DCF", "múltiplos frente al sector": "los múltiplos",
             "P/B justificado (Gordon)": "el P/B justificado", "P/B frente al sector": "el P/B del sector"}
    pair = " y ".join(names.get(m, m) for m in methods)
    dirs = [m.get("direction") for m in ev]
    lvl = conv.get("level")
    if conf["level"] == "alta":
        return f"{pair} coinciden" if pair else "los métodos coinciden"
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
    ql, pl = q.get("level"), p.get("level")
    text = f"Calidad {ql or 'sin dato'} · precio {pl or 'sin dato'}"
    why = confidence_phrase(conf)
    ctext = f"(confianza {conf['level']}: {why})" if (conf and conf.get("level") and why) else None
    return {"text": text, "confidence_text": ctext, "full": text + (f" {ctext}" if ctext else ""),
            "quality_level": ql, "price_level": pl, "confidence": (conf or {}).get("level")}
