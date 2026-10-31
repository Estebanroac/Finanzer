"""
Ciclicidad y crecimiento rentable medidos con la historia real (fase 3, T2; D4; F3_DISENO_METODO §1.2–§1.3).

D4: "la ciclicidad se mide con la historia real (10+ ejercicios de EDGAR, caídas de ingresos y márgenes) y va antes
que el crecimiento". La industria de Yahoo es un indicio, no una prueba: con historia suficiente manda el
comportamiento observado. Historia anual de EDGAR (`info["_history_fy"]`, lib/sec_edgar.annual_history: moneda de
los estados, sin convertir; ingresos por acción si las acciones crecieron más que
`thresholds.growth.per_share_min_shares_cagr` al año).

Lo que decide (propuesta de la T2, F3_T2_PARADA2: las medidas del diseño, medidas en el panel, confunden el ciclo con
cargos puntuales, reestructuraciones y márgenes que se expanden al crecer):

  · **episodios de caída de ingresos**: ejercicios con los ingresos al menos un `revenue_decline` por debajo del
    anterior; los consecutivos son un solo episodio. Un ciclo se repite: XOM 2009, 2015–16 y 2020; CAT 2009,
    2015–16 y 2020. Una reestructuración es un episodio (KO, refranquicia 2016–18);
  · **apalancamiento operativo**: un episodio solo es ciclo si el margen operativo cae al menos `margin_drop` (2
    puntos) frente al ejercicio anterior. Una caída de ventas con el margen estable o al alza es perímetro (KO 2017,
    refranquicia: el margen sube) o un choque sin apalancamiento (KO 2020). Sin margen en la historia, cuenta;
  · **desplomes del BPA con caída de ingresos**: el BPA cae más de la mitad (o a negativo) el mismo ejercicio en que
    caen los ingresos. Un cargo puntual (PG 2019, JNJ 2017 y 2024) no viene con caída de ventas.

Las tres medidas del diseño (§1.2: caída máxima de pico a valle, amplitud del margen operativo y desplomes del BPA)
se siguen calculando y se informan, sin decidir.

Un cambio de perímetro no es un ciclo: la serie se corta en los ejercicios con operaciones discontinuadas materiales
(UL, JNJ, DOW) y cada tramo se mide por separado; el desplome del BPA de esos ejercicios no cuenta.

Funciones puras: el clasificador (lib/classify.py) decide con ellas y los umbrales de config (sectors.archetypes).
"""
import datetime as _dt
from typing import Any, Dict, List, Optional, Tuple

from historical_metrics import cagr
from settings import cfg


def fiscal_years_between(e0: str, e1: str) -> int:
    """Ejercicios entre dos fechas de cierre: días / 365.25, redondeado. Con ejercicios de 52/53 semanas (cierre el
    sábado más cercano al 31-dic: FY2020 → 2021-01-02, FY2021 → 2022-01-01) el año de la fecha no es el ejercicio."""
    from datetime import date
    d0, d1 = date.fromisoformat(e0[:10]), date.fromisoformat(e1[:10])
    return int(round((d1 - d0).days / 365.25))


def fy_label(end: str) -> str:
    """V7 (M2/M6): "FY2022" a partir de la fecha de cierre. Un ejercicio de 52/53 semanas que cierra en la primera
    semana de enero es del año anterior (JNJ: FY2022 → 2023-01-01)."""
    from datetime import date
    d = date.fromisoformat(str(end)[:10])
    return f"FY{d.year - 1 if (d.month == 1 and d.day <= 7) else d.year}"


def _series(hist: Dict[str, Any], field: str) -> List[Tuple[str, float]]:
    """[(fin de ejercicio, valor)] del más antiguo al más reciente."""
    vals = ((hist or {}).get(field) or {}).get("values") or []
    return sorted(((v["fy_end"], float(v["value"])) for v in vals if v.get("value") is not None), key=lambda x: x[0])


def _shares(hist: Dict[str, Any]) -> List[Tuple[str, float]]:
    """Acciones diluidas medias: solo las positivas. V2 (fuentes reales): una cuenta de 0 acciones (CEG, el ejercicio
    antes de su escisión en 2022) es un dato vacío, no un divisor: dividía por cero y tumbaba el análisis."""
    return [(e, v) for e, v in _series(hist, "diluted_shares") if v > 0]


def _align(a: List[Tuple[str, float]], b: List[Tuple[str, float]]) -> List[Tuple[str, float, float]]:
    bd = dict(b)
    return [(e, x, bd[e]) for e, x in a if e in bd]


def perimeter_years(hist: Dict[str, Any], material_share: float) -> List[str]:
    """Ejercicios con operaciones discontinuadas materiales: |discontinuadas| ≥ material_share × |beneficio|."""
    ni = dict(_series(hist, "net_income"))
    out = []
    for e, d in _series(hist, "discontinued"):
        base = abs(ni.get(e) or 0.0)
        if d and (base == 0 or abs(d) >= material_share * base):
            out.append(e)
    return out


def share_breaks(hist: Dict[str, Any], thr: float) -> List[str]:
    """Ejercicios en que las acciones diluidas medias crecen al menos `thr` frente al anterior: ruptura del capital
    (conversión de preferentes en la salida a bolsa, fusión pagada en acciones). Antes de ella, el BPA y los ingresos
    por acción no son comparables con los de después."""
    sh = _shares(hist)
    return [e for (_e0, a), (e, b) in zip(sh, sh[1:]) if a > 0 and b >= (1.0 + thr) * a]


def _segments(series: List[Tuple[str, float]], cuts: List[str]) -> List[List[Tuple[str, float]]]:
    """Tramos de la serie separados en los ejercicios de cambio de perímetro (el ejercicio del cambio abre tramo)."""
    segs, cur = [], []
    for e, v in series:
        if e in cuts and cur:
            segs.append(cur)
            cur = []
        cur.append((e, v))
    if cur:
        segs.append(cur)
    return segs


def max_drawdown(values: List[float]) -> Optional[float]:
    """Mayor caída desde un máximo anterior (fracción), sobre valores positivos; None con menos de 2."""
    v = [x for x in values if x is not None and x > 0]
    if len(v) < 2:
        return None
    peak, dd = v[0], 0.0
    for x in v[1:]:
        dd = max(dd, 1.0 - x / peak)
        peak = max(peak, x)
    return dd


def margin_amplitude(margins: List[float]) -> Optional[float]:
    """(máximo − mínimo) / |media| del margen operativo; None si la media es 0."""
    if not margins:
        return None
    m = sum(margins) / len(margins)
    return (max(margins) - min(margins)) / abs(m) if m else None


def eps_shocks(eps: List[Tuple[str, float]], skip: List[str], drop: float) -> List[str]:
    """Ejercicios con BPA negativo o que cae más de `drop` desde un BPA positivo (fuera de los de perímetro)."""
    out = []
    for (_e0, a), (e1, b) in zip(eps, eps[1:]):
        if e1 in skip or a <= 0:
            continue
        if b < 0 or b < (1.0 - drop) * a:
            out.append(e1)
    return out


def decline_episodes(series: List[Tuple[str, float]], cuts: List[str], thr: float) -> List[List[str]]:
    """Episodios de caída de ingresos: ejercicios con caída interanual ≥ thr; los consecutivos forman uno. La caída en
    un ejercicio de cambio de perímetro no cuenta."""
    eps_: List[List[str]] = []
    prev_down = False
    for (e0, a), (e1, b) in zip(series, series[1:]):
        down = a > 0 and b <= (1.0 - thr) * a and e1 not in cuts
        if down:
            if prev_down:
                eps_[-1].append(e1)
            else:
                eps_.append([e1])
        prev_down = down
    return eps_


def confirm_episodes(hist: Dict[str, Any], episodes: List[List[str]], thr: float) -> Tuple[List[List[str]],
                                                                                    List[Dict[str, Any]]]:
    """Episodios que son ciclo: el margen operativo del peor ejercicio del episodio cae al menos `thr` frente al
    ejercicio anterior (apalancamiento operativo). Sin margen, el episodio cuenta (se declara). Devuelve (episodios
    confirmados, detalle de cada episodio con sus márgenes)."""
    rev = _series(hist, "revenue")
    ends = [e for e, _v in rev]
    rd = dict(rev)
    oi = dict(_series(hist, "operating_income"))

    def mg(e):
        return oi[e] / rd[e] if e in oi and rd.get(e) else None
    kept, detail = [], []
    for ep in episodes:
        i = ends.index(ep[0]) if ep[0] in ends else 0
        pre = ends[i - 1] if i > 0 else None
        m0 = mg(pre) if pre else None
        lows = [x for x in (mg(e) for e in ep) if x is not None]
        m1 = min(lows) if lows else None
        if m0 is None or m1 is None:
            ok, why = True, "sin margen operativo en la historia"
        else:
            ok = (m0 - m1) >= thr
            why = None if ok else "margen estable o al alza"
        detail.append({"years": ep, "margin_before": m0, "margin_trough": m1, "counts": ok, "why": why})
        if ok:
            kept.append(ep)
    return kept, detail


def measure(hist: Dict[str, Any]) -> Dict[str, Any]:
    """Medidas de ciclicidad de la historia anual (sin decidir): años, base (agregado o por acción), episodios de caída
    de ingresos, desplomes del BPA con caída de ingresos, ejercicios de perímetro y las medidas del diseño original."""
    C = cfg("sectors.archetypes.cyclicality")
    rev = _series(hist, "revenue")
    shares = _shares(hist)
    cuts = perimeter_years(hist, C["discontinued_material_share"])
    out: Dict[str, Any] = {"years": len(rev), "first": rev[0][0] if rev else None, "last": rev[-1][0] if rev else None,
                           "basis": "agregado", "shares_cagr": None, "perimeter_years": cuts,
                           "share_breaks": [], "decline_episodes": [], "episode_margins": [], "eps_collapse_with_decline": [], "eps_years": 0,
                           "design": {}}
    sh = _align(rev, shares)
    if len(sh) >= 2 and sh[0][2] > 0 and sh[-1][2] > 0:
        n = fiscal_years_between(sh[0][0], sh[-1][0])
        s_cagr = cagr(sh[-1][2], sh[0][2], n) if n > 0 else None
        out["shares_cagr"] = s_cagr
        if s_cagr is not None and s_cagr > cfg("thresholds.growth.per_share_min_shares_cagr"):
            rev = [(e, r / s) for e, r, s in sh]
            out["basis"] = "por_accion"
            out["share_breaks"] = share_breaks(hist, C["share_break"])
            cuts = sorted(set(cuts) | set(out["share_breaks"]))
    out["decline_episodes"], out["episode_margins"] = confirm_episodes(
        hist, decline_episodes(rev, cuts, C["revenue_decline"]), C["margin_drop"])
    down = {y for ep in out["decline_episodes"] for y in ep}
    eps = _series(hist, "diluted_eps")
    out["eps_years"] = len(eps)
    shocks = eps_shocks(eps, cuts, C["eps_drop"])
    out["eps_collapse_with_decline"] = [y for y in shocks if y in down]
    # Medidas del diseño original (§1.2), informativas.
    dds = [max_drawdown([v for _e, v in seg]) for seg in _segments(rev, cuts)]
    dds = [d for d in dds if d is not None]
    ebit = _series(hist, "operating_income")
    margins = [oi / r for _e, oi, r in _align(ebit, _series(hist, "revenue")) if r > 0]
    out["design"] = {"revenue_drawdown": max(dds) if dds else None, "op_margin_amplitude": margin_amplitude(margins),
                     "margin_years": len(margins), "eps_shock_years": shocks}
    return out


def decide(m: Dict[str, Any], thresholds: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    """¿Cíclica por su historia? {cyclical, enough, triggers}. `thresholds` permite la sensibilidad (±20%); el umbral
    de caída cambia los episodios, así que con él se vuelve a medir (`remeasure`)."""
    C = dict(cfg("sectors.archetypes.cyclicality"))
    C.update(thresholds or {})
    enough = (m.get("years") or 0) >= C["min_years"]
    trig = []
    if enough:
        if len(m.get("decline_episodes") or []) >= C["min_decline_episodes"]:
            trig.append("caidas_de_ingresos_repetidas")
        if len(m.get("eps_collapse_with_decline") or []) >= C["min_eps_collapses"]:
            trig.append("desplomes_del_bpa_con_caida_de_ingresos")
    return {"cyclical": bool(trig), "enough": enough, "triggers": trig}


def classify_history(hist: Dict[str, Any], thresholds: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    """measure + decide con umbrales distintos de los de config (sensibilidad): el umbral de caída de ingresos y el de
    desplome del BPA cambian lo medido."""
    if thresholds and any(k in thresholds for k in ("revenue_decline", "eps_drop", "discontinued_material_share", "share_break",
                                          "margin_drop")):
        C = dict(cfg("sectors.archetypes.cyclicality"))
        C.update(thresholds)
        m = _measure_with(hist, C)
    else:
        m = measure(hist)
    return {"measures": m, **decide(m, thresholds)}


def _measure_with(hist: Dict[str, Any], C: Dict[str, Any]) -> Dict[str, Any]:
    rev = _series(hist, "revenue")
    sh = _align(rev, _shares(hist))
    cuts = perimeter_years(hist, C["discontinued_material_share"])
    if len(sh) >= 2 and sh[0][2] > 0 and sh[-1][2] > 0:
        n = fiscal_years_between(sh[0][0], sh[-1][0])
        s_cagr = cagr(sh[-1][2], sh[0][2], n) if n > 0 else None
        if s_cagr is not None and s_cagr > cfg("thresholds.growth.per_share_min_shares_cagr"):
            rev = [(e, r / s) for e, r, s in sh]
            cuts = sorted(set(cuts) | set(share_breaks(hist, C["share_break"])))
    eps_, _d = confirm_episodes(hist, decline_episodes(rev, cuts, C["revenue_decline"]), C["margin_drop"])
    down = {y for ep in eps_ for y in ep}
    eps = _series(hist, "diluted_eps")
    return {"years": len(_series(hist, "revenue")), "decline_episodes": eps_, "eps_years": len(eps),
            "eps_collapse_with_decline": [y for y in eps_shocks(eps, cuts, C["eps_drop"]) if y in down]}


def growth_profitable_measures(hist: Dict[str, Any]) -> Dict[str, Any]:
    """CAGR de los ingresos POR ACCIÓN a 3 y 5 años (acciones diluidas medias) de la historia; sin acciones, agregado.
    Solo desde la última ruptura del capital (share_breaks): a través de ella el cociente no es comparable."""
    rev = _series(hist, "revenue")
    sh = _align(rev, _shares(hist))
    brk = share_breaks(hist, cfg("sectors.archetypes.cyclicality.share_break"))
    if brk:
        sh = [x for x in sh if x[0] >= brk[-1]]
    basis = "por_accion" if len(sh) >= 4 else "agregado"
    pts = [(e, r / s) for e, r, s in sh] if basis == "por_accion" else rev
    out = {"basis": basis, "revenue_ps_cagr_3y": None, "revenue_ps_cagr_5y": None, "share_break": brk[-1] if brk else None}
    # T7: el ejercicio de hace exactamente N años, por la fecha de cierre (una serie con huecos no cuenta puntos).
    if pts:
        from historical_metrics import robust_growth
        e1, v1 = pts[-1]
        by_n = {fiscal_years_between(e, e1): v for e, v in pts}
        long = {"values": [{"fy_end": e, "value": v} for e, v in pts]}
        for n, key in ((3, "revenue_ps_cagr_3y"), (5, "revenue_ps_cagr_5y")):
            v0 = by_n.get(n)
            if v0 is not None and v0 > 0 and v1 > 0:
                # F10 · crecimiento desde una base anómala: el tipo no se decide con una tasa que dependa del año
                # anómalo (regresión con la serie larga de la propia historia, o sin tasa).
                r = robust_growth([by_n.get(k) for k in range(n + 1)], n, what="ingresos por acción",
                                  strict_ends_only=True, long=long, end=e1)
                out[key] = r["value"]
                if r.get("anomalous_base"):
                    out[key.replace("revenue_ps_cagr", "method")] = {k: r.get(k)
                                                                     for k in ("method", "robust", "note", "reason")}
                if out[key] is None:
                    continue
                # V7 (M2): los ejercicios de la ventana, para que el texto diga su periodo ("FY2022–FY2025"); con la
                # serie larga, los de la regresión y cuántos son (classify.growth_span lo dice).
                if r.get("method") == "log_lineal_edgar":
                    out[key.replace("revenue_ps_cagr", "window")] = r.get("window")
                    out[key.replace("revenue_ps_cagr", "years")] = r.get("years_used")
                    continue
                e0 = next(e for e, v in pts if fiscal_years_between(e, e1) == n)
                out[key.replace("revenue_ps_cagr", "window")] = f"{fy_label(e0)}–{fy_label(e1)}"
    return out


def revenue_ps_cagr_long(hist: Dict[str, Any], max_years: int = 10, min_years: int = 5) -> Dict[str, Any]:
    """CAGR de los ingresos por acción en la ventana más larga disponible de `min_years` a `max_years` años, desde la
    última ruptura del capital (fase 3, T3: segunda referencia del DCF inverso, §8.1). Sin acciones, agregado."""
    rev = _series(hist or {}, "revenue")
    sh = _align(rev, _shares(hist or {}))
    brk = share_breaks(hist or {}, cfg("sectors.archetypes.cyclicality.share_break"))
    if brk:
        sh = [x for x in sh if x[0] >= brk[-1]]
    basis = "por_accion" if len(sh) >= min_years + 1 else "agregado"
    pts = [(e, r / s) for e, r, s in sh] if basis == "por_accion" else rev
    out = {"cagr": None, "years": None, "basis": basis, "from": None, "to": None}
    if not pts:
        return out
    # T7: los años salen de las fechas de cierre (NOW: acciones sin dato en 2014–2016; contar puntos daba 9 años
    # entre 2013 y 2025). El primer ejercicio dentro de la ventana de `max_years`, con al menos `min_years`.
    e1, v1 = pts[-1]
    cand = [(e, v) for e, v in pts[:-1] if min_years <= fiscal_years_between(e, e1) <= max_years]
    if not cand:
        return out
    e0, v0 = cand[0]
    n = fiscal_years_between(e0, e1)
    if v0 > 0 and v1 > 0:
        out.update(cagr=cagr(v1, v0, n), years=n, **{"from": e0, "to": e1})
    return out


def eps_mid_cycle(hist: Dict[str, Any], p0: str, p1: str) -> Dict[str, Any]:
    """F8 (auditoría externa; PM, 27-oct-2026): crecimiento del BPA de ciclo medio entre los picos `p0` y `p1`.

    Antes era el BPA de los dos picos de INGRESOS, y un pico de ventas puede ser un valle del BPA: SHEL 2015 (0,30 $,
    caída del petróleo) daba +52 % anual. Ahora es el BPA medio de la primera mitad de los ejercicios del ciclo frente al
    de la segunda (con un número impar, el central queda fuera), anualizado entre los centros de cada mitad. Las pérdidas
    entran en la media, porque son parte del ciclo; ningún ejercicio aislado decide. Sin tasa si una mitad tiene menos
    de `eps_half_min_years` ejercicios con BPA o si su media no es positiva."""
    pts = [(e, v) for e, v in _series(hist, "diluted_eps") if p0 <= e <= p1]
    k = len(pts) // 2
    out: Dict[str, Any] = {"cagr": None, "reason": None, "halves": None}
    if k < cfg("sectors.archetypes.cyclicality.eps_half_min_years"):
        out["reason"] = "sin BPA en suficientes ejercicios de cada mitad del ciclo"
        return out
    a, b = pts[:k], pts[-k:]
    ma, mb = sum(v for _e, v in a) / k, sum(v for _e, v in b) / k
    ca = sum(_dt.date.fromisoformat(e).toordinal() for e, _v in a) / k
    cb = sum(_dt.date.fromisoformat(e).toordinal() for e, _v in b) / k
    years = (cb - ca) / 365.25
    out["halves"] = {"first": [a[0][0], a[-1][0]], "second": [b[0][0], b[-1][0]], "mean_first": ma,
                     "mean_second": mb, "years": years}
    if ma <= 0 or mb <= 0:
        out["reason"] = "el BPA medio de una mitad del ciclo no es positivo (pérdidas): no hay tasa de crecimiento"
        return out
    out["cagr"] = (mb / ma) ** (1 / years) - 1
    return out


def mid_cycle_growth(hist: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Crecimiento de ciclo medio con 10+ ejercicios (fase 3, T5; F3_DISENO §4): la tendencia entre los PICOS del
    ciclo, el ejercicio anterior a cada episodio de caída confirmado (sustituye a la cota −5%/+10%, que queda para la
    historia corta). Entre el primer y el último pico (al menos `min_cycle_years` años): un ciclo completo o más.
    Misma base que la medida (por acción si las acciones crecieron). BPA: entre las medias de las dos mitades del
    ciclo (F8, eps_mid_cycle; antes, en los dos picos de ingresos). Margen operativo de ciclo medio: la media de los
    ejercicios del ciclo. None sin dos picos."""
    m = measure(hist)
    if (m.get("years") or 0) < cfg("sectors.archetypes.cyclicality.min_years"):
        return None
    rev = _series(hist, "revenue")
    if m["basis"] == "por_accion":
        rev = [(e, r / s) for e, r, s in _align(rev, _shares(hist))]
    rd = dict(rev)
    ends = [e for e, _v in rev]
    peaks = []
    for ep in m["decline_episodes"]:
        if ep[0] in ends and ends.index(ep[0]) > 0:
            peaks.append(ends[ends.index(ep[0]) - 1])
    if len(peaks) < 2:
        return None
    p0, p1 = peaks[0], peaks[-1]
    n = fiscal_years_between(p0, p1)
    if n < cfg("sectors.archetypes.cyclicality.min_cycle_years") or rd[p0] <= 0 or rd[p1] <= 0:
        return None
    eps = eps_mid_cycle(hist, p0, p1)
    oi, rv = dict(_series(hist, "operating_income")), dict(_series(hist, "revenue"))
    window = [e for e in ends if p0 <= e <= p1]
    margins = [oi[e] / rv[e] for e in window if e in oi and rv.get(e)]
    return {"cagr": cagr(rd[p1], rd[p0], n), "from": p0, "to": p1, "years": n, "peaks": peaks, "basis": m["basis"],
            "eps_cagr": eps["cagr"], "eps_reason": eps["reason"], "eps_halves": eps["halves"],
            "eps_method": "medias_de_mitades",
            "op_margin_mid_cycle": (sum(margins) / len(margins)) if margins else None,
            "margin_years": len(margins), "method": "pico_a_pico"}
