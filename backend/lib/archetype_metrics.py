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
from cost_of_capital import adjusted_beta as _blume, cost_of_equity as _ke
from settings import cfg

_V = cfg("valuation.archetypes")


def _first(values: Optional[List[Optional[float]]]) -> Optional[float]:
    return values[0] if values else None


def _pos(v: Optional[float]) -> bool:
    return v is not None and v > 0


def cost_of_equity(beta: Optional[float], rf: Optional[float] = None) -> float:
    """Ke por CAPM (Rf + β·MRP): el mismo Rf que el WACC (etapa 8, cost_of_capital)."""
    return _ke(beta, cfg("valuation.capm.risk_free_rate") if rf is None else rf)


def justified_multiple(ret: Optional[float], ke: float, g: float) -> Optional[float]:
    """Múltiplo de libros justificado por el retorno: (R − g) / (Ke − g)."""
    if ret is None or ret <= g or ke <= g:
        return None
    return (ret - g) / (ke - g)


def _financial(st: Dict[str, Any], km: Dict[str, Any], beta: Optional[float],
               rf: Optional[float] = None) -> Dict[str, Any]:
    ni, eq, tbv = st.get("net_income") or [], st.get("stockholders_equity") or [], st.get("tangible_book_value") or []
    rev = st.get("revenue") or []
    mcap = km.get("market_cap")
    ni0, eq0, tbv0, rev0 = _first(ni), _first(eq), _first(tbv), _first(rev)
    roe_series = ratio_series(ni, eq)
    roe_fy = _first(roe_series)
    rote = (ni0 / tbv0) if (ni0 is not None and _pos(tbv0)) else None
    ke, g = cost_of_equity(beta, rf), cfg("valuation.dcf.terminal_growth")   # β ajustada de Blume
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
        "beta_raw": beta if beta is not None else cfg("valuation.capm.default_beta"),
        "beta_adjusted": _blume(beta),
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


def _reit(st: Dict[str, Any], km: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    ni, ebitda, ebit = st.get("net_income") or [], st.get("ebitda") or [], st.get("ebit") or []
    ffo = [(n + (a - b)) if (n is not None and a is not None and b is not None) else None
           for n, a, b in zip(ni, ebitda, ebit)]
    shares = st.get("ordinary_shares") or []
    ffo_ps = _per_share(ffo, shares)
    ffo_ps_cagr, ffo_ps_why = strict_cagr(ffo_ps, 3)
    fcf_ps_cagr, fcf_ps_why = fcf_cagr(_per_share(st.get("free_cash_flow") or [], shares))
    # Etapa 9a: rentabilidad sobre el FFO (TTM, la misma definición del P/FFO).
    km = km or {}
    ffo_ttm, eq, rev = km.get("ffo"), km.get("total_equity"), km.get("revenue")
    return {
        "ffo_ttm": ffo_ttm,
        "ffo_to_equity": (ffo_ttm / eq) if (ffo_ttm is not None and _pos(eq)) else None,
        "ffo_margin": (ffo_ttm / rev) if (ffo_ttm is not None and _pos(rev)) else None,
        "ffo_series": ffo, "ffo_per_share_series": ffo_ps,
        "ffo_cagr_3y": strict_cagr(ffo, 3)[0],
        "ffo_per_share_cagr_3y": ffo_ps_cagr, "ffo_per_share_cagr_3y_reason": ffo_ps_why,
        "shares_cagr_3y": strict_cagr(shares, 3)[0],
        "fcf_per_share_cagr_3y": fcf_ps_cagr, "fcf_per_share_cagr_3y_reason": fcf_ps_why,
    }


def runway(fcf: Optional[float], liquidity: Optional[float]) -> Dict[str, Any]:
    """Runway de una GROWTH_PRE_PROFIT (etapa 7): FCF TTM >= 0 -> autofinanciada;
    FCF < 0 -> (caja + inversiones a corto plazo) / quema anual de FCF, en años."""
    if fcf is None:
        return {"state": "sin_dato", "years": None, "reason": "sin FCF TTM", "liquidity": liquidity, "fcf": None}
    if fcf >= 0:
        return {"state": "autofinanciada", "years": None, "reason": None, "liquidity": liquidity, "fcf": fcf}
    if liquidity is None:
        return {"state": "sin_dato", "years": None, "reason": "sin caja ni inversiones a corto plazo",
                "liquidity": None, "fcf": fcf}
    return {"state": "runway", "years": max(0.0, liquidity) / -fcf, "reason": None, "liquidity": liquidity, "fcf": fcf}


def sbc_adjustment(*, fcf: Optional[float], revenue: Optional[float], fcf_is_ttm: bool,
                   sbc_ttm: Optional[float], st: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """FCF − compensación en acciones (SBC), en el MISMO periodo que el FCF (etapa 9a).

    La SBC es un gasto real que no sale de caja (se paga en dilución): en una
    pre-beneficio suele ser mayor que todo su FCF. FCF TTM -> SBC TTM (4 trimestres);
    si no, el último ejercicio de los estados (FCF, SBC e ingresos del mismo año).
    Sin SBC del periodo: sin dato con motivo (nunca el FCF bruto)."""
    st = st or {}
    if fcf_is_ttm:
        if sbc_ttm is None:
            return {"value": None, "basis": "TTM", "reason": "sin SBC TTM (fila Stock Based Compensation de los 4 "
                                                             "últimos trimestres): no se usa el FCF bruto"}
        f, s, rev = fcf, sbc_ttm, revenue
        basis = "TTM"
    else:
        f, s, rev = _first(st.get("free_cash_flow")), _first(st.get("stock_based_compensation")), _first(st.get("revenue"))
        basis = f"FY{(st.get('cf_years') or ['?'])[0]}"
        if s is None:
            return {"value": None, "basis": basis, "reason": "sin fila Stock Based Compensation en el estado de flujos: "
                                                             "no se usa el FCF bruto"}
    if f is None or not _pos(rev):
        return {"value": None, "basis": basis, "reason": "sin FCF o ingresos del periodo"}
    return {"value": f - s, "basis": basis, "reason": None, "sbc": s, "fcf": f, "revenue": rev,
            "sbc_to_revenue": s / rev, "fcf_margin_raw": f / rev, "fcf_margin_adjusted": (f - s) / rev}


def _growth_pre_profit(km: Dict[str, Any], revenue_cagr_3y: Optional[float],
                       st: Optional[Dict[str, Any]] = None, sbc: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    fcf, rev = km.get("free_cash_flow"), km.get("revenue")
    # Etapa 9a: margen FCF y regla de 40 sobre FCF − SBC (sin SBC: sin dato con motivo).
    # El runway sigue en caja pura (FCF sin ajustar): mide liquidez.
    sbc = sbc or {}
    fcf_margin = sbc.get("fcf_margin_adjusted")
    rw = runway(fcf, km.get("cash"))
    # Etapa 9a: autofinanciada en CAJA; si la SBC supera el FCF, el coste económico se paga con dilución.
    rw["sbc_to_revenue"] = sbc.get("sbc_to_revenue")
    rw["sbc_exceeds_fcf"] = bool(sbc.get("sbc") is not None and sbc.get("fcf") is not None and sbc["sbc"] > sbc["fcf"])
    # Etapa 9a: mejora interanual del margen operativo (últimos dos ejercicios).
    om = ratio_series((st or {}).get("operating_income") or [], (st or {}).get("revenue") or [])
    om0, om1 = (om[0] if len(om) > 0 else None), (om[1] if len(om) > 1 else None)
    r40 = (revenue_cagr_3y + fcf_margin) if (revenue_cagr_3y is not None and fcf_margin is not None) else None
    ev_sales = km.get("ev_revenue")
    # key_metrics.cash = fila "Cash Cash Equivalents And Short Term Investments"
    # (caja + inversiones a corto plazo) del último balance.
    return {"ev_sales": ev_sales if _pos(ev_sales) else None, "fcf_margin": fcf_margin,
            "fcf_margin_basis": "FCF − SBC", "fcf_margin_reason": sbc.get("reason"),
            "fcf_margin_raw": (fcf / rev) if (fcf is not None and _pos(rev)) else None,
            "revenue_cagr_3y": revenue_cagr_3y, "rule_of_40": r40, "ebitda": km.get("ebitda"),
            "runway": rw, "gross_margin": km.get("gross_margin"),
            "fcf_minus_sbc": sbc.get("value"), "sbc": sbc.get("sbc"), "sbc_to_revenue": sbc.get("sbc_to_revenue"),
            "operating_margin_fy": om0, "operating_margin_fy_prior": om1,
            "operating_margin_change": (om0 - om1) if (om0 is not None and om1 is not None) else None,
            "operating_margin_change_reason": (None if (om0 is not None and om1 is not None)
                                               else "sin margen operativo de los dos últimos ejercicios")}


def maintenance_fcf(st: Dict[str, Any]) -> Dict[str, Any]:
    """FCF de mantenimiento (etapa 8, CYCLICAL): OCF − capex de mantenimiento por
    ejercicio, con el capex de mantenimiento aproximado por la D&A (DD&A en
    extractivas) y sin superar el capex real del año; promedio de los ejercicios
    disponibles. Excluye el capex de expansión, que el FCF normalizado incluye."""
    ocf, capex = st.get("operating_cash_flow") or [], st.get("capital_expenditure") or []
    da = st.get("depreciation_amortization") or []
    series = []
    for o, c, d in zip(ocf, capex, da):
        if o is None or d is None:
            series.append(None)
            continue
        m = min(abs(d), abs(c)) if c is not None else abs(d)
        series.append(o - m)
    vals = [x for x in series if x is not None]
    return {"value": mean(vals) if vals else None, "years": len(vals), "series": series,
            "reason": None if vals else "sin flujo operativo y D&A del mismo ejercicio"}


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
    # Etapa 9a: el BPA de ciclo medio con la misma regla que los ingresos (promedio
    # interanual de los ejercicios disponibles, acotado): un CAGR punta a punta
    # depende de la fase del ciclo (FCX: 2021 fue pico).
    eps = st.get("diluted_eps") or _per_share(st.get("net_income") or [], st.get("ordinary_shares") or [])
    e_raw = mean(yoy_growths(eps))
    e = None if e_raw is None else min(hi, max(lo, e_raw))
    maint = maintenance_fcf(st)
    return {
        "fcf_maintenance": maint["value"], "fcf_maintenance_years": maint["years"],
        "fcf_maintenance_series": maint["series"], "fcf_maintenance_reason": maint["reason"],
        "cycle_years": years, "cycle_incomplete": years < _V["cycle_full_years"],
        "ebitda_avg": ebitda_avg,
        "ev_ebitda_normalized": (ev / ebitda_avg) if (_pos(ev) and _pos(ebitda_avg)) else None,
        "fcf_margin_avg": fcf_margin_avg, "fcf_normalized": fcf_norm,
        # Etapa 9a: P/FCF normalizado sobre el FCF de MANTENIMIENTO, el mismo que usa el DCF.
        "p_fcf_normalized": (mcap / maint["value"]) if (_pos(mcap) and _pos(maint["value"])) else None,
        "p_fcf_normalized_basis": "fcf_mantenimiento",
        "revenue_growth_normalized_raw": g_raw, "revenue_growth_normalized": g,
        "eps_growth_normalized_raw": e_raw, "eps_growth_normalized": e,
        "eps_cycle_years": len([x for x in eps if x is not None]),
    }


def compute(archetype: str, statements_fy: Optional[Dict[str, Any]], key_metrics: Dict[str, Any], *,
            beta: Optional[float] = None, revenue_cagr_3y: Optional[float] = None,
            rf: Optional[float] = None, sbc: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Métricas de la rama del arquetipo ({} si la rama no necesita ninguna)."""
    st = statements_fy or {}
    if archetype == FINANCIAL:
        return _financial(st, key_metrics, beta, rf)
    if archetype == GROWTH_PRE_PROFIT:
        return _growth_pre_profit(key_metrics, revenue_cagr_3y, st, sbc)
    if archetype == REIT:
        return _reit(st, key_metrics)
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
