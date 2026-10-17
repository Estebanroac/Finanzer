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
  · convergencia: dirección y distancia entre los métodos evaluables: DCF (si su
    fiabilidad no es baja) y múltiplos frente al sector (las lecturas de
    Valoración, normalizadas a [−1, 1]); en FINANCIAL, P/B justificado (Gordon,
    intrínseco) y P/B frente al sector (relativo). Graham no vota: es una
    referencia del inversor defensivo. Señales opuestas -> baja; con un solo
    método evaluable, "no evaluable" y techo en media.
  · cobertura: componentes evaluados / aplicables del score (etapa 5).
  · calidad de fuente: lo que afecta al dato USADO. Datos rechazados, sospechosos o corregidos por la validación de
    entrada, ítems inferidos en la normalización y TTM con fallback al anual. Fase 4 (T2, causas reales): no cuentan
    las reglas que no son incidencias del dato usado (`source_ignored_rules`: el dato de otro periodo que no entra, la
    beta del proveedor cuando se usa la propia, las métricas no significativas por la economía de la empresa) ni los
    campos de Finnhub, que desde la 2b solo entran si casan con el corte (se listan en `finnhub_fields`).
  · estabilidad: CYCLICAL la reduce a baja; "posible cíclica" o clasificación
    ambigua, a media.
  · fuente oficial (fase 2b, D7): no pondera; un emisor sin estados en la SEC
    (EDGAR) pone techo en `no_official_source_cap` ("baja"). Sin verificación
    disponible (sin User-Agent o con EDGAR caído) no es culpa del emisor: sin techo.
Cada dimensión es alta/media/baja; la media ponderada (pesos en config) da el
nivel. Techo en media si la convergencia es media o baja (etapa 9a) o si cualquier otra dimensión es baja (fase 4,
T2: "alta" no convive con una debilidad clara, p. ej. una cíclica o datos rechazados). En la etapa 8 la confianza se calcula y se muestra: no limita el score
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
        medium.append("empresa cíclica: el FCF depende de la fase del ciclo")
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
    """Convergencia por DIRECCIÓN entre los métodos EVALUABLES (con señal; un DCF de
    fiabilidad baja no es evaluable: no concilia con el precio).
      alta    todos coinciden en dirección y la distancia entre señales < umbral;
      media   coinciden en dirección pero superan el umbral, o uno está en precio y
              otro tiene dirección (no coinciden, pero tampoco se oponen);
      baja    apuntan en direcciones opuestas (uno barata y otro cara);
      no_evaluable  menos de dos métodos evaluables: no hay contraste (fase 3, opción 3 de RECON
              §7.17: sin techo; solo la discrepancia o los datos débiles contraen la confianza)."""
    C = cfg("thresholds.confidence")
    for m in methods:
        m["evaluable"] = m.get("signal") is not None and m.get("reliability") != "baja"
        if m.get("signal") is not None:
            m["direction"] = _direction(m["signal"])
    ms = [m for m in methods if m["evaluable"]]
    excluded = [f"{m['method']} (fiabilidad baja)" for m in methods
                if m.get("signal") is not None and not m["evaluable"]]
    note = ([f"no evaluable: {', '.join(excluded)}"] if excluded else [])
    if len(ms) < 2:
        return {"level": "no_evaluable", "methods": methods,
                "reasons": [("un solo método evaluable (" + ms[0]["method"] + ")" if ms
                             else "ningún método evaluable") + ": no hay contraste"] + note}
    cheap = [m["method"] for m in ms if m["direction"] == "barata"]
    dear = [m["method"] for m in ms if m["direction"] == "cara"]
    if cheap and dear:
        return {"level": "baja", "methods": methods,
                "reasons": [f"direcciones opuestas: {', '.join(cheap)} {'dice' if len(cheap) == 1 else 'dicen'} "
                            f"barata y {', '.join(dear)} {'dice' if len(dear) == 1 else 'dicen'} cara"] + note}
    dirs = {m["direction"] for m in ms}
    if len(dirs) > 1:
        return {"level": "media", "methods": methods,
                "reasons": ["uno lo ve en precio y otro con dirección: no coinciden, sin oponerse"] + note}
    spread = max(m["signal"] for m in ms) - min(m["signal"] for m in ms)
    if spread >= C["convergence_spread_max"]:
        return {"level": "media", "methods": methods,
                "reasons": [f"coinciden ({next(iter(dirs))}) pero la distancia entre señales es {spread:.2f} "
                            f"(>= {C['convergence_spread_max']})"] + note}
    return {"level": "alta", "methods": methods,
            "reasons": [f"coinciden ({next(iter(dirs))}) con distancia {spread:.2f} "
                        f"(< {C['convergence_spread_max']})"] + note}


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
    # Etapa 9a: las sustituciones de política del arquetipo (p. ej. el crecimiento de una
    # financiera siempre desde los estados) no son incidencias de la fuente.
    # Fase 2b: un dato de otra fuente que NO entra por no ser del corte (Finnhub, periodo_incoherente "aviso") no es
    # una incidencia del dato usado: el análisis usa el del corte.
    # Fase 4 (T2; revisión de código F4, hallazgo 1): se excluye por REGLA, no por acción: "sin_dato" es también como
    # se rechaza un dato imposible (márgenes, unidades, saltos) y "aviso", a veces, un dato sospechoso que se usa.
    ignored = set(C["source_ignored_rules"])
    issues = [f"validación: {f.get('field')} ({f.get('rule')})" for f in input_flags or []
              if f.get("action") != "politica" and f.get("rule") not in ignored]
    if (normalization or {}).get("confidence") == "media":
        issues.append("beneficio normalizado con ítems inferidos (confianza media)")
    if (ttm or {}).get("basis") == "anual":
        issues.append("sin TTM: estados anuales (hasta 12 meses de retraso)")
    fh = sorted(k for k, v in (provenance_fields or {}).items() if (v or {}).get("source") == "finnhub")
    ok, mid = C["source_issue_bounds"]
    level = "alta" if len(issues) <= ok else ("media" if len(issues) <= mid else "baja")
    return {"level": level, "issues": len(issues), "reasons": issues, "finnhub_fields": fh}


def stability_dimension(archetype: Optional[str], classification: Dict[str, Any]) -> Dict[str, Any]:
    alerts = [a.get("code") for a in (classification or {}).get("alerts") or []]
    if archetype == "CYCLICAL":
        return {"level": "baja", "reasons": ["empresa cíclica: resultados ligados a la fase del ciclo"]}
    if "posible_ciclica" in alerts:
        return {"level": "media", "reasons": ["alerta de posible cíclica"]}
    low = (classification or {}).get("low_confidence")
    if low:     # fase 3 (T2): frontera, ciclicidad sin medir o ambigua, con su motivo
        return {"level": "media", "reasons": [low["detail"]]}
    if (classification or {}).get("ambiguous"):
        return {"level": "media", "reasons": ["clasificación ambigua"]}
    return {"level": "alta", "reasons": []}


def official_dimension(official: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Fase 2b (D7, F2_PRECEDENCIA §4): fuente oficial del emisor (data_provenance.official_source)."""
    o = official or {}
    if o.get("registered") is False:
        return {"level": "baja", "status": o.get("status"),
                "reasons": ["el emisor no presenta estados en la SEC (EDGAR): cifras de proveedores sin contrastar"]}
    if o.get("registered") is None:
        return {"level": "no_evaluable", "status": o.get("status") or "no_disponible", "reasons": []}
    return {"level": "alta", "status": o.get("status"), "reasons": []}


def verdict_confidence(dimensions: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Media ponderada de las cuatro dimensiones -> alta / media / baja con motivos (fuente_oficial no pondera:
    solo pone techo)."""
    C = cfg("thresholds.confidence")
    val = dict(zip(LEVELS, C["level_values"]))
    W = C["weights"]
    rated = {k: d for k, d in dimensions.items() if d["level"] in val and k in W}   # "no_evaluable" no pondera
    score = sum(W[k] * val[d["level"]] for k, d in rated.items()) / sum(W[k] for k in rated)
    hi, mid = C["overall_bounds"]
    level = "alta" if score >= hi else ("media" if score >= mid else "baja")
    labels = {"convergence": "convergencia", "coverage": "cobertura", "source": "calidad de fuente",
              "stability": "estabilidad", "fuente_oficial": "fuente oficial"}
    reasons = [f"{labels[k]} {d['level'].replace('_', ' ')}: " + "; ".join(d["reasons"])
               for k, d in dimensions.items() if d["level"] != "alta" and d.get("reasons")]
    capped = None
    conv = (dimensions.get("convergence") or {}).get("level")
    if conv == "no_evaluable":
        # Fase 3 (T3, D3, opción 3 de RECON §7.17): la mera ausencia de un segundo método NO contrae la confianza;
        # la contraen la discrepancia entre métodos (convergencia media o baja) y los datos débiles (las otras
        # dimensiones). Con el DCF inverso conectado, casi todos los análisis tienen ya dos métodos.
        cap = None
    elif conv is not None and conv != "alta":
        # Etapa 9a: "alta" exige convergencia alta (caso V local, RECON 7.13).
        cap, why = C["no_evaluable_cap"], f"la convergencia es {conv}: alta exige convergencia alta"
    else:
        cap = None
    caps = [(cap, why)] if cap else []
    weak = [labels[k] for k, d in dimensions.items()
            if k in W and k != "convergence" and d.get("level") == "baja"]
    if weak:
        caps.append((C["weak_dimension_cap"], f"{', '.join(weak)} baja, y alta exige que ninguna dimensión lo sea"))
    if (dimensions.get("fuente_oficial") or {}).get("level") == "baja":
        caps.append((C["no_official_source_cap"], "sin fuente oficial para verificar los datos"))
    for cap, why in caps:
        if LEVELS.index(level) < LEVELS.index(cap):
            capped, level = capped or level, cap
            reasons.append(f"techo en {cap}: {why}")
    return {"level": level, "score": score, "dimensions": dimensions, "reasons": reasons,
            "capped_from": capped, "limits_score": False}
