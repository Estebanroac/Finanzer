"""
Fiabilidad del DCF y confianza del veredicto (etapa 8; spec Sección 3 y cambio 5).

FIABILIDAD DEL DCF (alta / media / baja, con motivos):
  baja   el grid completo no contiene el precio (ninguna combinación razonable de
         crecimiento y WACC lo reconcilia); el valor terminal pesa más de
         terminal_max_pct; o el FCF de entrada viene marcado por la validación o
         es inferido (no sale de los estados).
  media  el precio está en el grid pero fuera del bloque central (caso base ±1);
         el arquetipo es CYCLICAL; o hay alerta de "posible cíclica".
  alta   el resto.

CONFIANZA DEL VEREDICTO = f(convergencia, cobertura, calidad de fuente, estabilidad)
  · convergencia: dirección y magnitud de DCF, múltiplos frente al sector (las
    lecturas de Valoración, normalizadas a [−1, 1]) y Graham si aplica. Señales
    opuestas (una dice barata y otra cara) -> baja.
  · cobertura: componentes evaluados / aplicables del score (etapa 5).
  · calidad de fuente: flags de validación de entrada, ítems inferidos en la
    normalización, TTM con fallback al anual, campos de Finnhub en lugar de los
    estados.
  · estabilidad: CYCLICAL la reduce a baja; "posible cíclica" o clasificación
    ambigua, a media.
Cada dimensión es alta/media/baja; la media ponderada (pesos en config) da el
nivel. En la etapa 8 la confianza se calcula y se muestra: no limita el score
(el techo condicionado por la confianza es de la etapa 9).
"""
from typing import Any, Dict, List, Optional

from settings import cfg

LEVELS = ("alta", "media", "baja")


def _level_from(low: List[str], medium: List[str]) -> str:
    return "baja" if low else ("media" if medium else "alta")


# ═══════════════════════════ fiabilidad del DCF ═══════════════════════════
def dcf_reliability(*, dcf: Optional[Dict[str, Any]], sensitivity: Optional[Dict[str, Any]],
                    price: Optional[float], archetype: Optional[str], possible_cyclical: bool,
                    fcf_flags: List[str], fcf_source: Optional[str]) -> Optional[Dict[str, Any]]:
    """{level, reasons, grid_contains_price, central_contains_price} o None sin DCF."""
    if not dcf or dcf.get("fair_value") is None:
        return None
    R = cfg("thresholds.dcf_reliability")
    low: List[str] = []
    medium: List[str] = []
    s = sensitivity or {}
    vals = [v for row in (s.get("matrix") or []) for v in row if v is not None]
    in_grid = in_center = None
    if vals and price:
        lo, hi = min(vals), max(vals)
        in_grid = lo <= price <= hi
        if not in_grid:
            low.append(f"el grid completo ({lo:.2f}–{hi:.2f}) no contiene el precio ({price:.2f}): ninguna "
                       "combinación razonable de crecimiento y WACC lo reconcilia")
        gi, di, k = s.get("base_growth_idx"), s.get("base_discount_idx"), R["central_block"]
        if gi is not None and di is not None:
            block = [v for i, row in enumerate(s["matrix"]) if abs(i - gi) <= k
                     for j, v in enumerate(row) if abs(j - di) <= k and v is not None]
            in_center = bool(block) and min(block) <= price <= max(block)
            if in_grid and not in_center:
                medium.append(f"el precio está en el grid pero fuera del caso base ±{k} "
                              f"({min(block):.2f}–{max(block):.2f})")
    tv = ((dcf.get("value_composition") or {}).get("terminal_pct"))
    if tv is not None and tv > R["terminal_max_pct"]:
        low.append(f"el valor terminal pesa {tv:.0f}% (> {R['terminal_max_pct']}%)")
    if fcf_flags:
        low.append("el FCF de entrada viene marcado por la validación (" + "; ".join(fcf_flags) + ")")
    if fcf_source in R["inferred_sources"]:
        low.append(f"el FCF de entrada es inferido (fuente: {fcf_source}), no sale de los estados")
    if archetype == "CYCLICAL":
        medium.append("arquetipo CYCLICAL: el FCF depende de la fase del ciclo")
    if possible_cyclical:
        medium.append("alerta de posible cíclica")
    level = _level_from(low, medium)
    return {"level": level, "reasons": low if level == "baja" else medium,
            "grid_contains_price": in_grid, "central_contains_price": in_center}


# ═══════════════════════════ confianza del veredicto ═══════════════════════════
def signal_from_upside(u: Optional[float]) -> Optional[float]:
    """Upside (fracción) -> señal en [−1, 1]."""
    if u is None:
        return None
    return max(-1.0, min(1.0, u / cfg("thresholds.confidence.upside_scale")))


def _direction(s: float) -> str:
    nb = cfg("thresholds.confidence.neutral_band")
    return "barata" if s > nb else ("cara" if s < -nb else "en precio")


def multiples_signal(items: List[Any]) -> Optional[Dict[str, Any]]:
    """Señal de los múltiplos frente al sector a partir de los componentes de
    Valoración: cada ajuste normalizado por su máximo (positivo) o su mínimo
    (negativo), promediado. items = [(nombre, máx, mín, ajuste)]."""
    skip = set(cfg("thresholds.confidence.excluded_multiple_components"))
    vals = []
    for name, mx, mn, adj in items:
        if name in skip or adj is None:
            continue
        vals.append(adj / mx if (adj > 0 and mx) else (adj / abs(mn) if (adj < 0 and mn) else 0.0))
    if not vals:
        return None
    return {"value": sum(vals) / len(vals), "components": len(vals)}


def convergence(methods: List[Dict[str, Any]]) -> Dict[str, Any]:
    C = cfg("thresholds.confidence")
    ms = [m for m in methods if m.get("signal") is not None]
    for m in ms:
        m["direction"] = _direction(m["signal"])
    if len(ms) < 2:
        return {"level": "media", "methods": ms,
                "reasons": ["un solo método de valoración disponible: no hay contraste"] if ms
                else ["sin métodos de valoración con dato"]}
    cheap = [m["method"] for m in ms if m["direction"] == "barata"]
    dear = [m["method"] for m in ms if m["direction"] == "cara"]
    if cheap and dear:
        return {"level": "baja", "methods": ms,
                "reasons": [f"direcciones opuestas: {', '.join(cheap)} {'dice' if len(cheap) == 1 else 'dicen'} "
                            f"barata y {', '.join(dear)} {'dice' if len(dear) == 1 else 'dicen'} cara"]}
    spread = max(m["signal"] for m in ms) - min(m["signal"] for m in ms)
    if spread > C["convergence_spread_max"]:
        return {"level": "media", "methods": ms,
                "reasons": [f"misma dirección o neutras, pero magnitudes muy distintas (dispersión {spread:.2f})"]}
    dirs = {m["direction"] for m in ms}
    if len(dirs) > 1:
        return {"level": "media", "methods": ms,
                "reasons": ["unos métodos apuntan en una dirección y otros la ven en precio"]}
    weak = [m["method"] for m in ms if m.get("reliability") == "baja"]
    if weak:   # un método no fiable no puede confirmar el veredicto de los demás
        return {"level": "media", "methods": ms,
                "reasons": [f"los métodos coinciden ({next(iter(dirs))}), pero {', '.join(weak)} tiene fiabilidad "
                            "baja y no confirma el veredicto"]}
    return {"level": "alta", "methods": ms, "reasons": [f"los métodos coinciden: {next(iter(dirs))}"]}


def coverage_dimension(score_coverage: Optional[Dict[str, Any]], excluded: List[str]) -> Dict[str, Any]:
    C = cfg("thresholds.confidence")
    n = ev = 0
    for rep in (score_coverage or {}).values():
        if isinstance(rep, dict):
            n += rep.get("components") or 0
            ev += rep.get("evaluated") or 0
    cov = (ev / n) if n else None
    reasons = []
    if excluded:
        reasons.append("categorías excluidas por cobertura: " + ", ".join(excluded))
    if cov is None:
        return {"level": "baja", "coverage": None, "reasons": reasons + ["sin componentes evaluables"]}
    hi, mid = C["coverage_bounds"]
    level = "alta" if cov >= hi else ("media" if cov >= mid else "baja")
    if excluded:
        level = "baja"
    if level != "alta":
        reasons.append(f"{ev} de {n} componentes del score con dato ({cov:.0%})")
    return {"level": level, "coverage": cov, "reasons": reasons}


def source_dimension(*, input_flags: List[Dict[str, Any]], normalization: Optional[Dict[str, Any]],
                     ttm: Optional[Dict[str, Any]], provenance_fields: Dict[str, Any]) -> Dict[str, Any]:
    C = cfg("thresholds.confidence")
    issues = [f"validación: {f.get('field')} ({f.get('rule')})" for f in input_flags or []]
    if (normalization or {}).get("confidence") == "media":
        issues.append("beneficio normalizado con ítems inferidos (confianza media)")
    if (ttm or {}).get("basis") == "anual":
        issues.append("sin TTM: estados anuales (hasta 12 meses de retraso)")
    fh = sorted(k for k, v in (provenance_fields or {}).items() if (v or {}).get("source") == "finnhub")
    if fh:
        issues.append(f"{len(fh)} campos de Finnhub en lugar de los estados")
    ok, mid = C["source_issue_bounds"]
    level = "alta" if len(issues) <= ok else ("media" if len(issues) <= mid else "baja")
    return {"level": level, "issues": len(issues), "reasons": issues, "finnhub_fields": fh}


def stability_dimension(archetype: Optional[str], classification: Dict[str, Any]) -> Dict[str, Any]:
    alerts = [a.get("code") for a in (classification or {}).get("alerts") or []]
    if archetype == "CYCLICAL":
        return {"level": "baja", "reasons": ["arquetipo CYCLICAL: resultados ligados a la fase del ciclo"]}
    if "posible_ciclica" in alerts:
        return {"level": "media", "reasons": ["alerta de posible cíclica"]}
    if (classification or {}).get("ambiguous"):
        return {"level": "media", "reasons": ["clasificación ambigua"]}
    return {"level": "alta", "reasons": []}


def verdict_confidence(dimensions: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Media ponderada de las cuatro dimensiones -> alta / media / baja con motivos."""
    C = cfg("thresholds.confidence")
    val = dict(zip(LEVELS, C["level_values"]))
    W = C["weights"]
    score = sum(W[k] * val[d["level"]] for k, d in dimensions.items()) / sum(W[k] for k in dimensions)
    hi, mid = C["overall_bounds"]
    level = "alta" if score >= hi else ("media" if score >= mid else "baja")
    labels = {"convergence": "convergencia", "coverage": "cobertura", "source": "calidad de fuente",
              "stability": "estabilidad"}
    reasons = [f"{labels[k]} {d['level']}: " + "; ".join(d["reasons"])
               for k, d in dimensions.items() if d["level"] != "alta" and d.get("reasons")]
    return {"level": level, "score": score, "dimensions": dimensions, "reasons": reasons,
            "limits_score": False}
