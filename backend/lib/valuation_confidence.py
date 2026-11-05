"""
Fiabilidad del DCF y confianza del veredicto (etapa 8; spec Sección 3 y cambio 5).

FIABILIDAD DEL DCF (alta / media / baja, con motivos). F8 · E8: por la calidad de los insumos, nunca por si el valor
coincide con el precio; ver dcf_reliability.

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
import statistics
from typing import Any, Dict, List, Optional

import numfmt
from settings import cfg

LEVELS = ("alta", "media", "baja")


def _level_from(low: List[str], medium: List[str]) -> str:
    return "baja" if low else ("media" if medium else "alta")


# ═══════════════════════════ fiabilidad del DCF ═══════════════════════════
def fcf_margin_stability(history_fy: Optional[Dict[str, Any]], years: int) -> Optional[Dict[str, Any]]:
    """F8 · E8: margen FCF (OCF − capex sobre ingresos) de los `years` últimos ejercicios de EDGAR y su coeficiente de
    variación; None sin esos ejercicios completos."""
    import history_10y
    rows = [r for r in history_10y.build(history_fy, years)["rows"]
            if r.get("free_cash_flow") is not None and (r.get("revenue") or 0) > 0]
    if len(rows) < years:
        return None
    m = [r["free_cash_flow"] / r["revenue"] for r in rows[-years:]]
    mean = sum(m) / len(m)
    sd = (sum((x - mean) ** 2 for x in m) / len(m)) ** 0.5
    return {"margins": m, "years": [r["year"] for r in rows[-years:]], "mean": mean,
            "cv": (sd / abs(mean)) if mean else None}


def margin_deterioration(history_fy: Optional[Dict[str, Any]], current: Dict[str, Optional[float]],
                         years: int) -> Optional[Dict[str, Any]]:
    """F8 · E8 (criterio 5, PM 27-oct): margen operativo (o neto, sin operativo) TTM frente a la mediana de los `years`
    últimos ejercicios de EDGAR: caída relativa y cuántos de los últimos cambios anuales son bajadas. None sin datos."""
    import history_10y
    rows = history_10y.build(history_fy, years)["rows"][-years:]
    for key in ("operating_margin", "net_margin"):
        m = [r.get(key) for r in rows]
        cur = current.get(key)
        if len(m) == years and all(x is not None for x in m) and cur is not None:
            med = statistics.median(m)
            if med <= 0:
                return None
            return {"key": key, "median": med, "current": cur, "drop": (med - cur) / med,
                    "downs": sum(1 for a, b in zip(m, m[1:]) if b < a), "changes": len(m) - 1,
                    "years": [r["year"] for r in rows]}
    return None


def dcf_reliability(*, dcf: Optional[Dict[str, Any]], sensitivity: Optional[Dict[str, Any]],
                    price: Optional[float], archetype: Optional[str], possible_cyclical: bool,
                    fcf_flags: List[str], fcf_source: Optional[str],
                    history_fy: Optional[Dict[str, Any]] = None,
                    data_flags: Optional[List[str]] = None,
                    current_margins: Optional[Dict[str, Optional[float]]] = None) -> Optional[Dict[str, Any]]:
    """{level, reasons, criteria, grid_contains_price, central_contains_price} o None sin DCF.

    F8 · E8 (auditoría del 26-oct): la fiabilidad se juzga por los insumos, NUNCA por si el valor coincide con el
    precio (eso es la convergencia entre métodos). Parte de «alta» y cada criterio que falla resta un escalón:
      (1) el valor terminal pesa más de `terminal_minus_pct` (más de `terminal_max_pct`: baja directamente);
      (2) dispersión del bloque central de la tabla (caso base ± 1 casilla: g ± 2,5 pp, WACC ± 1 pp): máximo ÷ mínimo
          mayor que `central_dispersion_max`, o un valor ≤ 0;
      (3) margen FCF inestable: coeficiente de variación de los `fcf_margin_years` últimos ejercicios (EDGAR) mayor que
          `fcf_margin_cv_max`, o margen medio ≤ 0. Sin esos ejercicios, no se evalúa y se dice;
      (4) banderas de datos (beta sin verificar, pico de beneficio): un escalón entre todas;
      (5) crecimiento proyectado (g del DCF ≥ 0) con el margen en deterioro (PM, 27-oct): margen operativo (o neto) TTM
          por debajo de la mediana de 5 ejercicios en más de `margin_drop_min` y bajando en al menos `margin_drop_downs`
          de los 4 últimos cambios anuales. Con una caída de al menos el doble del umbral, baja directamente.
    El FCF de entrada marcado por la validación o inferido (no sale de los estados) es baja directamente. Una cíclica o
    una «posible cíclica» no pasan de media. Si la tabla contiene el precio se sigue informando, sin efecto."""
    if not dcf or dcf.get("fair_value") is None:
        return None
    R = cfg("thresholds.dcf_reliability")
    low: List[str] = []
    minus: List[str] = []
    cap: List[str] = []
    notes: List[str] = []
    s = sensitivity or {}
    vals = [v for row in (s.get("matrix") or []) for v in row if v is not None]
    in_grid = in_center = None
    if vals and price:
        in_grid = min(vals) <= price <= max(vals)
    gi, di, k = s.get("base_growth_idx"), s.get("base_discount_idx"), R["central_block"]
    block = []
    if gi is not None and di is not None:
        block = [v for i, row in enumerate(s.get("matrix") or []) if abs(i - gi) <= k
                 for j, v in enumerate(row) if abs(j - di) <= k and v is not None]
        if block and price:
            in_center = min(block) <= price <= max(block)
    # (1) valor terminal
    tv = ((dcf.get("value_composition") or {}).get("terminal_pct"))
    if tv is not None and tv > R["terminal_max_pct"]:
        low.append(f"el valor terminal pesa {tv:.0f}% (> {R['terminal_max_pct']}%)")
    elif tv is not None and tv > R["terminal_minus_pct"]:
        minus.append(f"el valor terminal pesa {tv:.0f}% (> {R['terminal_minus_pct']}%)")
    # (2) dispersión del bloque central
    if block:
        if min(block) <= 0:
            minus.append("con crecimiento ± 2,5 pp y WACC ± 1 pp el valor llega a ser ≤ 0")
        elif max(block) / min(block) > R["central_dispersion_max"]:
            minus.append(f"con crecimiento ± 2,5 pp y WACC ± 1 pp el valor va de {numfmt.price(min(block))} a "
                         f"{numfmt.price(max(block))} ({max(block) / min(block):.1f} veces, > "
                         f"{R['central_dispersion_max']:g})")
    # (3) estabilidad del margen FCF
    st = fcf_margin_stability(history_fy, R["fcf_margin_years"])
    if st is None:
        notes.append(f"estabilidad del margen FCF sin evaluar: EDGAR no trae {R['fcf_margin_years']} ejercicios")
    elif st["mean"] <= 0:
        minus.append(f"margen FCF medio de {R['fcf_margin_years']} ejercicios ≤ 0 ({st['mean']:.1%})")
    elif st["cv"] > R["fcf_margin_cv_max"]:
        minus.append(f"margen FCF inestable: de {min(st['margins']):.1%} a {max(st['margins']):.1%} en "
                     f"{R['fcf_margin_years']} ejercicios (variación {st['cv']:.2f} > {R['fcf_margin_cv_max']:g})")
    # (5) crecimiento proyectado con el margen en caída (el DCF de un impulsor no lo ve: E7, Fase B)
    md = margin_deterioration(history_fy, current_margins or {}, R["margin_trend_years"])
    g = dcf.get("growth_rate")
    if md and g is not None and g >= 0 and md["drop"] >= R["margin_drop_min"] and md["downs"] >= R["margin_drop_downs"]:
        _lbl = "margen operativo" if md["key"] == "operating_margin" else "margen neto"
        _txt = (f"el DCF proyecta crecimiento ({g:.1%}) con el margen en caída ({_lbl} {md['current']:.1%} frente a "
                f"una mediana de {md['median']:.1%} en {len(md['years'])} ejercicios, −{md['drop']:.0%}, y "
                f"{md['downs']} bajadas en {md['changes']} años); supuesto no verificado hasta el DCF de tres impulsores")
        (low if md["drop"] >= R["margin_drop_low_mult"] * R["margin_drop_min"] else minus).append(_txt)
    # (4) banderas de datos
    if data_flags:
        minus.append("banderas de datos: " + "; ".join(data_flags))
    if fcf_flags:
        low.append("el FCF de entrada viene marcado por la validación (" + "; ".join(fcf_flags) + ")")
    if fcf_source in R["inferred_sources"]:
        low.append(f"el FCF de entrada es inferido (fuente: {fcf_source}), no sale de los estados")
    if archetype == "CYCLICAL":
        cap.append("empresa cíclica: el FCF depende de la fase del ciclo")
    if possible_cyclical:
        cap.append("alerta de posible cíclica")
    worst = len(LEVELS) - 1
    steps = worst if low else min(worst, len(minus))
    if cap and steps < 1:
        steps = 1
    level = LEVELS[steps]
    reasons = low + minus + (cap if level != "alta" else [])
    return {"level": level, "reasons": reasons if level != "alta" else [],
            "criteria": {"terminal_pct": tv, "central_dispersion": (max(block) / min(block))
                         if block and min(block) > 0 else None,
                         "fcf_margin": st, "data_flags": data_flags or [], "margin_trend": md, "notes": notes},
            "grid_contains_price": in_grid, "central_contains_price": in_center}


# ═══════════════════════════ confianza del veredicto ═══════════════════════════
def dcf_wacc_flips(sensitivity: Optional[Dict[str, Any]]) -> List[Dict[str, float]]:
    """F11 · F1 (revisión de NFLX): con el crecimiento base, los WACC vecinos (± un escalón de la rejilla del propio DCF)
    en los que el valor queda al otro lado del precio que el del caso base. Vacía si la dirección no depende del WACC.
    NFLX: base 78,29 frente a 66,44; con WACC 9,43 % vale 65,86 (debajo del precio)."""
    s = sensitivity or {}
    M, gi, di = s.get("matrix"), s.get("base_growth_idx"), s.get("base_discount_idx")
    price = (s.get("statistics") or {}).get("current_price")
    if not M or gi is None or di is None or not price:
        return []
    row, rates = M[gi], s.get("discount_rates") or []
    base = row[di] if di < len(row) else None
    if base is None:
        return []
    return [{"wacc": rates[j] if j < len(rates) else None, "value": row[j]} for j in (di - 1, di + 1)
            if 0 <= j < len(row) and row[j] is not None and (row[j] - price) * (base - price) < 0]


def signal_from_upside(u: Optional[float]) -> Optional[float]:
    """Upside (fracción) -> señal en [−1, 1]."""
    if u is None:
        return None
    return max(-1.0, min(1.0, u / cfg("thresholds.confidence.upside_scale")))


def _direction(s: float) -> str:
    nb = cfg("thresholds.confidence.neutral_band")
    return "barata" if s > nb else ("cara" if s < -nb else "en precio")


def multiples_signal(items: List[Any], members: Optional[Dict[str, float]] = None) -> Optional[Dict[str, Any]]:
    """Señal de los múltiplos frente al sector a partir de los componentes de
    Valoración: cada ajuste normalizado por su máximo (positivo) o su mínimo
    (negativo), promediado. items = [(nombre, máx, mín, ajuste)].
    `readings` (F8 · E4): la lectura de cada múltiplo individual en [−1, 1], los del bloque (`members`, ya
    normalizados) y los de la rama, para que la convergencia vea si alguno contradice con lectura extrema."""
    skip = set(cfg("thresholds.confidence.excluded_multiple_components"))
    vals = []
    readings = dict(members or {})
    for name, mx, mn, adj in items:
        if name in skip or adj is None:
            continue
        v = adj / mx if (adj > 0 and mx) else (adj / abs(mn) if (adj < 0 and mn) else 0.0)
        vals.append(v)
        if name != "Bloque de múltiplos":
            readings[name] = v
    if not vals:
        return None
    return {"value": sum(vals) / len(vals), "components": len(vals), "readings": readings}


def convergence(methods: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Convergencia por DIRECCIÓN entre los métodos EVALUABLES (con señal; un DCF de
    fiabilidad baja no es evaluable: sus insumos no lo sostienen; F8 · E8).
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
    # F8 · E4 (auditoría del 26-oct, VZ): coincidir exige además que ningún múltiplo individual contradiga la dirección
    # común con una lectura extrema (VZ: «el DCF y los múltiplos coinciden (barata)» con el P/E «muy caro»).
    d = next(iter(dirs))
    ext = C["convergence_extreme_reading"]
    contrary = [(k, v) for m in ms for k, v in (m.get("readings") or {}).items()
                if (d == "barata" and v <= -ext) or (d == "cara" and v >= ext)]
    if contrary:
        return {"level": "media", "methods": methods, "contrary_extremes": dict(contrary),
                "reasons": [f"coinciden ({d}), pero {'lo contradice' if len(contrary) == 1 else 'lo contradicen'} "
                            f"con lectura extrema {', '.join(f'{k} ({v:+.2f})' for k, v in contrary)}"
                            .replace("-", "−")] + note}
    spread = max(m["signal"] for m in ms) - min(m["signal"] for m in ms)
    if spread >= C["convergence_spread_max"]:
        return {"level": "media", "methods": methods,
                "reasons": [f"coinciden ({next(iter(dirs))}) pero la distancia entre señales es {spread:.2f} "
                            f"(>= {C['convergence_spread_max']})"] + note}
    # F11 · T2 (revisión de NU): dos métodos que dependen de la misma referencia (`anchor`: el conjunto de industria o de
    # pares del que sacan su insumo dominante) no se confirman entre sí: un error en esa referencia los mueve juntos.
    by_anchor: Dict[str, List[str]] = {}
    for m in ms:
        if m.get("anchor"):
            by_anchor.setdefault(m["anchor_label"] if m.get("anchor_label") else m["anchor"], []).append(m["method"])
    shared = {a: ws for a, ws in by_anchor.items() if len(ws) > 1}
    if shared:
        a, ws = next(iter(shared.items()))
        return {"level": "media", "methods": methods, "shared_anchor": a,
                "reasons": [f"coinciden ({d}), pero {' y '.join(ws)} comparten la referencia ({a}): no son "
                            "independientes"] + note}
    return {"level": "alta", "methods": methods,
            "reasons": [f"coinciden ({next(iter(dirs))}) con distancia {spread:.2f} "
                        f"(< {C['convergence_spread_max']})"] + note}


def coverage_dimension(score_coverage: Optional[Dict[str, Any]], excluded: List[str],
                       staleness: Optional[Dict[str, Any]] = None,
                       unmeasured_critical: Optional[List[str]] = None) -> Dict[str, Any]:
    """Cobertura de los componentes del score. F8 · E6: con los estados desfasados más de `stale_coverage_days`
    (lib/edgar_backup.staleness), no pasa de «media». F11 · T3 (revisión de NU): tampoco con la variable crítica de su
    tipo sin medir (`unmeasured_critical`: el riesgo de crédito de un banco), aunque no puntúe."""
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
    if (staleness or {}).get("coverage_capped"):
        latest = staleness.get("edgar_latest") or {}
        date_long = numfmt.date_long
        reasons.append(f"estados desfasados: corte del {date_long(staleness.get('cut'))} "
                       f"({staleness.get('days_since_cut')} días) y EDGAR ya tiene el {latest.get('form')} del periodo "
                       f"cerrado el {date_long(latest.get('report_date'))}")
        if level == "alta":
            level = "media"
    if unmeasured_critical:
        reasons.append("sin medir: " + ", ".join(unmeasured_critical))
        if level == "alta":
            level = "media"
    return {"level": level, "coverage": cov, "reasons": reasons}


def source_dimension(*, input_flags: List[Dict[str, Any]], normalization: Optional[Dict[str, Any]],
                     ttm: Optional[Dict[str, Any]], provenance_fields: Dict[str, Any],
                     self_exclusion: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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
    _un = (normalization or {}).get("unexplained") or {}
    _ni = abs((normalization or {}).get("reported_net_income") or 0.0)
    # Plan, 29-oct: el beneficio que la operación no explica y que ninguna partida nombra no se recorta; se declara y,
    # si se distingue del beneficio (más de `label_min_diff`, como la etiqueta «normalizado»), baja la confianza. El
    # mayor de los dos: el exceso antes de impuestos vuelve a estar en el de después.
    if _ni and max(_un.get("pre_tax") or 0.0, _un.get("after_tax") or 0.0) / _ni > \
            cfg("thresholds.normalization.label_min_diff"):
        issues.append("beneficio por encima de lo que explica la operación sin partida que lo nombre (no se recorta)")
    if (self_exclusion or {}).get("degraded"):
        # F10 (PM, 29-oct; ENB): la referencia de la industria cayó a la mediana de los pares por un tiempo agotado de
        # EDGAR, no por la empresa: es una incidencia de la fuente y la confianza lo dice.
        issues.append(f"referencia de la industria degradada: {self_exclusion.get('reason')}")
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


def verdict_confidence(dimensions: Dict[str, Dict[str, Any]],
                       base_rate: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Media ponderada de las cuatro dimensiones -> alta / media / baja con motivos (fuente_oficial no pondera:
    solo pone techo). F8 · E11: la más baja de las dimensiones evaluadas pone techo a la confianza.
    F10 · N4: `base_rate` (la tasa base del DCF inverso: {share, g10, horizon_years, …}): si el crecimiento que exige
    el precio lo sostuvo menos de `base_rate_min_share` de las comparables, la confianza baja un escalón (de alta a
    media, de media a baja), después de los techos. El precio no se toca."""
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
    # F8 · E11 (auditoría del 26-oct, MRNA: cobertura baja con confianza media): la más baja manda, como dice la
    # metodología. Ninguna dimensión evaluada (la cobertura incluida) puede quedar por debajo de la confianza final;
    # es genérico: cualquier causa que baje una dimensión (p. ej. unos estados desfasados que bajan la cobertura) la
    # arrastra.
    worst = max((LEVELS.index(d["level"]) for k, d in rated.items()), default=0)
    if worst:
        low = [labels[k] for k, d in rated.items() if LEVELS.index(d["level"]) == worst]
        caps.append((LEVELS[worst], f"la más baja manda: {', '.join(low)} {LEVELS[worst]}"))
    if (dimensions.get("fuente_oficial") or {}).get("level") == "baja":
        caps.append((C["no_official_source_cap"], "sin fuente oficial para verificar los datos"))
    for cap, why in caps:
        if LEVELS.index(level) < LEVELS.index(cap):
            capped, level = capped or level, cap
            reasons.append(f"techo en {cap}: {why}")
    # La contracción del precio y de la calidad hacia 50 usa esta (`contraction_basis`): el escalón de las tasas base
    # baja la confianza que se muestra, no el precio (con él, las acciones que exigen un crecimiento casi imposible
    # saldrían más atractivas por la contracción; decisión del PM, F10 · N4 opción a).
    basis = level
    br = base_rate or {}
    stepped = None
    if br.get("share") is not None and br["share"] < C["base_rate_min_share"]:
        stepped = level
        if LEVELS.index(level) < len(LEVELS) - 1:
            level = LEVELS[LEVELS.index(level) + 1]
        g = br.get("g10")
        reasons.append(f"un escalón menos por las tasas base: el precio exige "
                       + (f"un {g:.1%} anual " if g is not None else "su crecimiento ")
                       + f"{br.get('horizon_years')} años, que sostuvo el {br['share']:.2%} de las comparables "
                       f"(< {C['base_rate_min_share']:.0%})" + ("" if stepped != level else "; ya estaba en baja"))
    return {"level": level, "score": score, "dimensions": dimensions, "reasons": reasons,
            "capped_from": capped, "limits_score": False, "contraction_basis": basis,
            "base_rate_step": ({"share": br.get("share"), "from": stepped, "to": level} if stepped else None)}
