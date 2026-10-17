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
  · **desplomes del BPA con caída de ingresos**: el BPA cae más de la mitad (o a negativo) el mismo ejercicio en que
    caen los ingresos. Un cargo puntual (PG 2019, JNJ 2017 y 2024) no viene con caída de ventas.

Las tres medidas del diseño (§1.2: caída máxima de pico a valle, amplitud del margen operativo y desplomes del BPA)
se siguen calculando y se informan, sin decidir.

Un cambio de perímetro no es un ciclo: la serie se corta en los ejercicios con operaciones discontinuadas materiales
(UL, JNJ, DOW) y cada tramo se mide por separado; el desplome del BPA de esos ejercicios no cuenta.

Funciones puras: el clasificador (lib/classify.py) decide con ellas y los umbrales de config (sectors.archetypes).
"""
from typing import Any, Dict, List, Optional, Tuple

from historical_metrics import cagr
from settings import cfg


def _series(hist: Dict[str, Any], field: str) -> List[Tuple[str, float]]:
    """[(fin de ejercicio, valor)] del más antiguo al más reciente."""
    vals = ((hist or {}).get(field) or {}).get("values") or []
    return sorted(((v["fy_end"], float(v["value"])) for v in vals if v.get("value") is not None), key=lambda x: x[0])


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


def measure(hist: Dict[str, Any]) -> Dict[str, Any]:
    """Medidas de ciclicidad de la historia anual (sin decidir): años, base (agregado o por acción), episodios de caída
    de ingresos, desplomes del BPA con caída de ingresos, ejercicios de perímetro y las medidas del diseño original."""
    C = cfg("sectors.archetypes.cyclicality")
    rev = _series(hist, "revenue")
    shares = _series(hist, "diluted_shares")
    cuts = perimeter_years(hist, C["discontinued_material_share"])
    out: Dict[str, Any] = {"years": len(rev), "first": rev[0][0] if rev else None, "last": rev[-1][0] if rev else None,
                           "basis": "agregado", "shares_cagr": None, "perimeter_years": cuts,
                           "decline_episodes": [], "eps_collapse_with_decline": [], "eps_years": 0,
                           "design": {}}
    sh = _align(rev, shares)
    if len(sh) >= 2 and sh[0][2] > 0 and sh[-1][2] > 0:
        n = int(sh[-1][0][:4]) - int(sh[0][0][:4])
        s_cagr = cagr(sh[-1][2], sh[0][2], n) if n > 0 else None
        out["shares_cagr"] = s_cagr
        if s_cagr is not None and s_cagr > cfg("thresholds.growth.per_share_min_shares_cagr"):
            rev = [(e, r / s) for e, r, s in sh]
            out["basis"] = "por_accion"
    out["decline_episodes"] = decline_episodes(rev, cuts, C["revenue_decline"])
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
    if thresholds and any(k in thresholds for k in ("revenue_decline", "eps_drop", "discontinued_material_share")):
        C = dict(cfg("sectors.archetypes.cyclicality"))
        C.update(thresholds)
        m = _measure_with(hist, C)
    else:
        m = measure(hist)
    return {"measures": m, **decide(m, thresholds)}


def _measure_with(hist: Dict[str, Any], C: Dict[str, Any]) -> Dict[str, Any]:
    rev = _series(hist, "revenue")
    sh = _align(rev, _series(hist, "diluted_shares"))
    cuts = perimeter_years(hist, C["discontinued_material_share"])
    if len(sh) >= 2 and sh[0][2] > 0 and sh[-1][2] > 0:
        n = int(sh[-1][0][:4]) - int(sh[0][0][:4])
        s_cagr = cagr(sh[-1][2], sh[0][2], n) if n > 0 else None
        if s_cagr is not None and s_cagr > cfg("thresholds.growth.per_share_min_shares_cagr"):
            rev = [(e, r / s) for e, r, s in sh]
    eps_ = decline_episodes(rev, cuts, C["revenue_decline"])
    down = {y for ep in eps_ for y in ep}
    eps = _series(hist, "diluted_eps")
    return {"years": len(_series(hist, "revenue")), "decline_episodes": eps_, "eps_years": len(eps),
            "eps_collapse_with_decline": [y for y in eps_shocks(eps, cuts, C["eps_drop"]) if y in down]}


def growth_profitable_measures(hist: Dict[str, Any]) -> Dict[str, Any]:
    """CAGR de los ingresos POR ACCIÓN a 3 y 5 años (acciones diluidas medias) de la historia; sin acciones, agregado."""
    rev = _series(hist, "revenue")
    sh = _align(rev, _series(hist, "diluted_shares"))
    basis = "por_accion" if len(sh) >= 4 else "agregado"
    ps = [r / s for _e, r, s in sh] if basis == "por_accion" else [v for _e, v in rev]
    out = {"basis": basis, "revenue_ps_cagr_3y": None, "revenue_ps_cagr_5y": None}
    if len(ps) >= 4 and ps[-4] > 0 and ps[-1] > 0:
        out["revenue_ps_cagr_3y"] = cagr(ps[-1], ps[-4], 3)
    if len(ps) >= 6 and ps[-6] > 0 and ps[-1] > 0:
        out["revenue_ps_cagr_5y"] = cagr(ps[-1], ps[-6], 5)
    return out
