"""
Métricas por arquetipo (etapa 6): lo que cada rama necesita y el motor
genérico no calcula. Todo sale de los ejercicios anuales (_statements_fy) y
de key_metrics; un dato ausente queda en None con su motivo, nunca en 0.

  FINANCIAL          P/B y P/TBV frente a los justificados por ROE/ROTE
                     ((R − g) / (Ke − g), Ke por CAPM, g terminal del DCF),
                     estabilidad del ROE, eficiencia aproximada, CAGR del
                     valor en libros tangible y crecimiento de ingresos de
                     los estados (no de Finnhub: RECON §7.8).
  REIT               crecimiento POR ACCIÓN: CAGR del FFO por acción (FFO =
                     beneficio neto + D&A, la misma definición del P/FFO; acciones
                     en circulación de cada ejercicio, base del balance anual,
                     ajustada por splits) y del FCF por acción. El crecimiento
                     agregado de un REIT lo infla la emisión estructural.
  GROWTH_PRE_PROFIT  EV/Ventas y regla de 40 (CAGR real de ingresos + margen FCF);
                     EBITDA del último ejercicio para declarar EV/EBITDA "no aplica".
  CYCLICAL           EV/EBITDA, FCF y crecimiento normalizados con los
                     ejercicios disponibles ("ciclo incompleto" si < 5).
  ROCE               EBIT / (activos − pasivo corriente) en MATURE y CYCLICAL,
                     con el promedio de ciclo y la divergencia frente al ROIC.
"""
from typing import Any, Dict, List, Optional

from classify import CYCLICAL, FINANCIAL, GROWTH_PRE_PROFIT, REIT, not_applicable
from historical_metrics import fcf_cagr, mean, ratio_series, stdev, strict_cagr, yoy_growths
from settings import cfg

_V = cfg("valuation.archetypes")


def _first(values: Optional[List[Optional[float]]]) -> Optional[float]:
    return values[0] if values else None


def _pos(v: Optional[float]) -> bool:
    return v is not None and v > 0


def cost_of_equity(beta: Optional[float]) -> float:
    """Ke por CAPM (Rf + β·MRP) con los parámetros de la config."""
    c = cfg("valuation.capm")
    b = beta if beta is not None else c["default_beta"]
    return c["risk_free_rate"] + b * c["market_risk_premium"]


def justified_multiple(ret: Optional[float], ke: float, g: float) -> Optional[float]:
    """Múltiplo de libros justificado por el retorno: (R − g) / (Ke − g)."""
    if ret is None or ret <= g or ke <= g:
        return None
    return (ret - g) / (ke - g)


def _financial(st: Dict[str, Any], km: Dict[str, Any], beta: Optional[float]) -> Dict[str, Any]:
    ni, eq, tbv = st.get("net_income") or [], st.get("stockholders_equity") or [], st.get("tangible_book_value") or []
    rev = st.get("revenue") or []
    mcap = km.get("market_cap")
    ni0, eq0, tbv0, rev0 = _first(ni), _first(eq), _first(tbv), _first(rev)
    roe_series = ratio_series(ni, eq)
    roe_fy = _first(roe_series)
    rote = (ni0 / tbv0) if (ni0 is not None and _pos(tbv0)) else None
    ke, g = cost_of_equity(beta), cfg("valuation.dcf.terminal_growth")
    pb = (mcap / eq0) if (_pos(mcap) and _pos(eq0)) else None
    ptbv = (mcap / tbv0) if (_pos(mcap) and _pos(tbv0)) else None
    j_pb, j_ptbv = justified_multiple(roe_fy, ke, g), justified_multiple(rote, ke, g)

    # Gastos no financieros: la fila total si existe; si no, la suma de las
    # partidas bancarias desglosadas (exige al menos una partida bancaria).
    nie0, nie_why = _first(st.get("non_interest_expense") or []), None
    if nie0 is None:
        bank_rows = [_first(st.get(k) or []) for k in ("occupancy", "other_non_interest_expense")]
        sga0, prof0 = _first(st.get("sga") or []), _first(st.get("professional_services") or [])
        if any(x is not None for x in bank_rows) and sga0 is not None:
            nie0 = sga0 + sum(x for x in (*bank_rows, prof0) if x is not None)
        else:
            nie_why = "sin gastos no financieros desglosados en los estados"
    efficiency = (nie0 / rev0) if (nie0 is not None and _pos(rev0)) else None

    bv_series = tbv if (tbv and all(_pos(x) for x in tbv[:4])) else eq
    bv_growth, bv_why = strict_cagr(bv_series, 3)
    rev_yoy = _first(yoy_growths(rev))
    return {
        "cost_of_equity": ke, "terminal_growth": g,
        "roe_fy": roe_fy, "rote": rote, "pb": pb, "ptbv": ptbv,
        "pb_justified": j_pb, "ptbv_justified": j_ptbv,
        "pb_ratio": (pb / j_pb) if (pb is not None and j_pb) else None,
        "ptbv_ratio": (ptbv / j_ptbv) if (ptbv is not None and j_ptbv) else None,
        "roe_std": stdev(roe_series) if len([x for x in roe_series if x is not None]) >= 3 else None,
        "roe_years": len([x for x in roe_series if x is not None]),
        "efficiency_ratio": efficiency, "efficiency_reason": nie_why,
        "book_value_cagr_3y": bv_growth, "book_value_cagr_3y_reason": bv_why,
        "book_value_basis": "tangible" if bv_series is tbv else "contable",
        "revenue_growth_statements": rev_yoy,
    }


def _per_share(values: List[Optional[float]], shares: List[Optional[float]]) -> List[Optional[float]]:
    return [(v / s) if (v is not None and _pos(s)) else None for v, s in zip(values or [], shares or [])]


def _reit(st: Dict[str, Any]) -> Dict[str, Any]:
    ni, ebitda, ebit = st.get("net_income") or [], st.get("ebitda") or [], st.get("ebit") or []
    ffo = [(n + (a - b)) if (n is not None and a is not None and b is not None) else None
           for n, a, b in zip(ni, ebitda, ebit)]
    shares = st.get("ordinary_shares") or []
    ffo_ps = _per_share(ffo, shares)
    ffo_ps_cagr, ffo_ps_why = strict_cagr(ffo_ps, 3)
    fcf_ps_cagr, fcf_ps_why = fcf_cagr(_per_share(st.get("free_cash_flow") or [], shares))
    return {
        "ffo_series": ffo, "ffo_per_share_series": ffo_ps,
        "ffo_cagr_3y": strict_cagr(ffo, 3)[0],
        "ffo_per_share_cagr_3y": ffo_ps_cagr, "ffo_per_share_cagr_3y_reason": ffo_ps_why,
        "shares_cagr_3y": strict_cagr(shares, 3)[0],
        "fcf_per_share_cagr_3y": fcf_ps_cagr, "fcf_per_share_cagr_3y_reason": fcf_ps_why,
    }


def _growth_pre_profit(km: Dict[str, Any], revenue_cagr_3y: Optional[float]) -> Dict[str, Any]:
    fcf, rev = km.get("free_cash_flow"), km.get("revenue")
    fcf_margin = (fcf / rev) if (fcf is not None and _pos(rev)) else None
    r40 = (revenue_cagr_3y + fcf_margin) if (revenue_cagr_3y is not None and fcf_margin is not None) else None
    ev_sales = km.get("ev_revenue")
    return {"ev_sales": ev_sales if _pos(ev_sales) else None, "fcf_margin": fcf_margin,
            "revenue_cagr_3y": revenue_cagr_3y, "rule_of_40": r40, "ebitda": km.get("ebitda")}


def _cyclical(st: Dict[str, Any], km: Dict[str, Any]) -> Dict[str, Any]:
    rev = st.get("revenue") or []
    ebitda_avg = mean(st.get("ebitda") or [])
    years = len([x for x in rev if x is not None])
    ev, mcap, rev_now = km.get("enterprise_value"), km.get("market_cap"), km.get("revenue")
    fcf_margin_avg = mean(ratio_series(st.get("free_cash_flow") or [], rev))
    fcf_norm = (fcf_margin_avg * rev_now) if (fcf_margin_avg is not None and _pos(rev_now)) else None
    g_raw = mean(yoy_growths(rev))
    lo, hi = _V["cyclical_growth_bounds"]
    g = None if g_raw is None else min(hi, max(lo, g_raw))
    return {
        "cycle_years": years, "cycle_incomplete": years < _V["cycle_full_years"],
        "ebitda_avg": ebitda_avg,
        "ev_ebitda_normalized": (ev / ebitda_avg) if (_pos(ev) and _pos(ebitda_avg)) else None,
        "fcf_margin_avg": fcf_margin_avg, "fcf_normalized": fcf_norm,
        "p_fcf_normalized": (mcap / fcf_norm) if (_pos(mcap) and _pos(fcf_norm)) else None,
        "revenue_growth_normalized_raw": g_raw, "revenue_growth_normalized": g,
    }


def compute(archetype: str, statements_fy: Optional[Dict[str, Any]], key_metrics: Dict[str, Any], *,
            beta: Optional[float] = None, revenue_cagr_3y: Optional[float] = None) -> Dict[str, Any]:
    """Métricas de la rama del arquetipo ({} si la rama no necesita ninguna)."""
    st = statements_fy or {}
    if archetype == FINANCIAL:
        return _financial(st, key_metrics, beta)
    if archetype == GROWTH_PRE_PROFIT:
        return _growth_pre_profit(key_metrics, revenue_cagr_3y)
    if archetype == REIT:
        return _reit(st)
    if archetype == CYCLICAL:
        return _cyclical(st, key_metrics)
    return {}


# ═══════════════════════════ ROCE ═══════════════════════════
def roce(archetype: str, statements_fy: Optional[Dict[str, Any]], key_metrics: Dict[str, Any]) -> Dict[str, Any]:
    """ROCE = EBIT / (activos totales − pasivo corriente), antes de impuestos.

    No aplica a FINANCIAL ni a REIT. Capital empleado <= 0 o datos ausentes:
    sin dato (None con motivo), nunca 0%. En CYCLICAL añade el promedio de los
    ejercicios disponibles ("ciclo incompleto" si son menos de 5)."""
    na = not_applicable(archetype, "roce")
    if na:
        return {"roce": None, "state": "no_aplica", "reason": na}
    st = statements_fy or {}
    ebit = list(st.get("ebit") or [])
    oi = list(st.get("operating_income") or [])
    ta, cl = st.get("total_assets") or [], st.get("current_liabilities") or []
    n = max(len(ebit), len(oi))
    ebit = [(ebit[i] if i < len(ebit) and ebit[i] is not None else (oi[i] if i < len(oi) else None)) for i in range(n)]
    series = []
    for e, a, c in zip(ebit, ta, cl):
        ce = (a - c) if (a is not None and c is not None) else None
        series.append(e / ce if (e is not None and ce is not None and ce > 0) else None)
    cur = _first(series)
    out: Dict[str, Any] = {"roce": cur, "state": "ok" if cur is not None else "sin_dato",
                           "reason": None if cur is not None else
                           "capital empleado <= 0 o sin EBIT/activos/pasivo corriente del último ejercicio",
                           "series": series}
    if archetype == CYCLICAL:
        yrs = len([x for x in series if x is not None])
        out.update({"roce_avg": mean(series), "years": yrs, "cycle_incomplete": yrs < _V["cycle_full_years"]})

    # Divergencia frente al ROIC del motor (causas probables).
    roic = key_metrics.get("roic")
    T = cfg("thresholds.roce")
    if cur is not None and roic is not None:
        gap = cur - roic
        out["roic"], out["gap"] = roic, gap
        out["diverges"] = abs(gap) > T["divergence_pp"]
        if out["diverges"]:
            causes = []
            cash, assets = key_metrics.get("cash"), key_metrics.get("total_assets")
            share = (cash / assets) if (cash is not None and _pos(assets)) else None
            if gap < 0 and share is not None and share >= T["excess_cash_share"]:
                causes.append(f"caja excedente elevada ({share * 100:.0f}% de los activos) que infla el capital empleado")
            if gap > 0:
                causes.append("base fiscal distinta: el ROCE es antes de impuestos y el ROIC después")
            causes.append("capital distinto: el ROIC usa patrimonio + deuda − caja; el ROCE, activos − pasivo "
                          "corriente (incluye pasivos a largo plazo no financieros e intereses minoritarios)")
            out["causes"] = causes
    return out
