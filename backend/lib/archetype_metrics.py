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
from historical_metrics import bound_decides, fcf_cagr, is_anomalous_not_significant, mean, ratio_series, stdev, strict_cagr, yoy_growths
from cost_of_capital import adjusted_beta as _blume, equity_cost as _ke
from history_10y import _by_end
from settings import cfg

_V = cfg("valuation.archetypes")


def _first(values: Optional[List[Optional[float]]]) -> Optional[float]:
    return values[0] if values else None


def _pos(v: Optional[float]) -> bool:
    return v is not None and v > 0


def _num(v: Any) -> Optional[float]:
    return float(v) if isinstance(v, (int, float)) and v == v else None


def cost_of_equity(beta: Optional[float], rf: Optional[float] = None, preadjusted: bool = False,
                   ke: Optional[float] = None) -> float:
    """Ke por CAPM (Rf + β·MRP) con sus pisos: el mismo Rf que el WACC (etapa 8, cost_of_capital). F8 · E1: `ke`, el
    único del análisis (con el piso de Kd si hay deuda), manda cuando llega."""
    if ke is not None:
        return ke
    return _ke(beta, cfg("valuation.capm.risk_free_rate") if rf is None else rf, None, preadjusted)["value"]


def justified_multiple(ret: Optional[float], ke: float, g: float) -> Optional[float]:
    """Múltiplo de libros justificado por el retorno: (R − g) / (Ke − g)."""
    if ret is None or ret <= g or ke <= g:
        return None
    return (ret - g) / (ke - g)


def two_stage_multiple(ret: float, g_high: float, years: int, ret_stable: float, g: float,
                       ke: float) -> Optional[float]:
    """F9 · R1b: múltiplo de libros justificado en dos etapas (Damodaran, P/BV de dos etapas), con la convención del de
    una etapa, (R − g) / (Ke − g): el beneficio de cada año es el retorno sobre el valor en libros del año anterior.
    Durante `years` el valor en libros crece a `g_high` con el retorno `ret` (reparto 1 − g_high / ret); después,
    crecimiento `g` con el retorno estable `ret_stable` (reparto 1 − g / ret_stable):

        P/B = ret·po₁·[1 − ((1+g₁)/(1+Ke))ⁿ] / (Ke − g₁) + ret_s·po₂·(1+g₁)ⁿ / [(Ke − g)·(1+Ke)ⁿ]

    Con g₁ = g y ret_s = ret es exactamente el de una etapa."""
    if ret <= 0 or ret_stable <= g or ke <= g or g_high > ret:
        return None
    po1, po2 = 1 - g_high / ret, 1 - g / ret_stable
    q = (1 + g_high) / (1 + ke)
    first = ret * po1 * (years / (1 + ke) if abs(ke - g_high) < 1e-12 else (1 - q ** years) / (ke - g_high))
    second = ret_stable * po2 * (1 + g_high) ** years / ((ke - g) * (1 + ke) ** years)
    return first + second


def apply_two_stage(xm: Dict[str, Any], industry_roe: Optional[float], payout: Optional[float],
                    dividend_yield: Optional[float], roe_source: Optional[str] = None,
                    roe_anchor: Optional[str] = None) -> Dict[str, Any]:
    """F9 · R1b (revisión externa de NU; supuestos del PM del 27-oct): con el valor en libros creciendo por encima de
    `bv_growth_threshold`, el P/B (y el P/TBV) justificado pasa a dos etapas. Etapa alta de `years` años con
    g₁ = mín(crecimiento observado del valor en libros, ROE × retención); después g (el terminal de siempre) con el ROE
    de la industria regional de Damodaran, que converge (mantener un ROE alto para siempre es el supuesto que la
    auditoría criticó en el DCF). Sin ROE de la industria: una etapa, declarado. Devuelve `two_stage` (o None si no
    se activa) y actualiza los justificados y sus cocientes de `xm`. F10 · N2b: el ROE estable es el de la industria
    global sin la empresa (`roe_source` lo nombra)."""
    C = cfg("valuation.pb_two_stage")
    bv, roe, ke, g = (xm.get("book_value_cagr_3y"), xm.get("roe_reference"), xm.get("cost_of_equity"),
                      xm.get("terminal_growth"))
    _bvr = xm.get("book_value_cagr_3y_reason")
    if bv is None and is_anomalous_not_significant(_bvr):
        # F10 · crecimiento desde una base anómala: sin un crecimiento del valor en libros significativo no hay etapa
        # alta que medir; una sola etapa, declarado (antes, la tasa desde el año anómalo podía activar las dos).
        return {"two_stage": {"applied": False, "book_value_growth": None,
                              "reason": f"el crecimiento del valor en libros es {_bvr}: una sola etapa"}}
    if bv is None or bv <= C["bv_growth_threshold"] or roe is None or ke is None or g is None:
        return {}
    out: Dict[str, Any] = {"applied": False, "book_value_growth": bv, "years": C["years"],
                           "threshold": C["bv_growth_threshold"], "industry_roe": industry_roe,
                           "industry_roe_source": roe_source, "industry_roe_anchor": roe_anchor}
    if not industry_roe or industry_roe <= g:
        out["reason"] = ("el valor en libros crece un {:.0%} anual, pero sin ROE de la industria no hay etapa "
                         "estable a la que converger: una sola etapa").format(bv)
        return {"two_stage": out}
    if payout is not None:
        retention, ret_basis = max(0.0, 1 - payout), f"retención {max(0.0, 1 - payout):.0%}"
    elif dividend_yield == 0:
        retention, ret_basis = 1.0, "sin dividendo: retención 100 %"
    else:
        retention, ret_basis = 1.0, "sin reparto conocido: tope en el ROE"
    g1 = min(bv, roe * retention)
    pb2 = two_stage_multiple(roe, g1, C["years"], industry_roe, g, ke)
    if pb2 is None:
        out["reason"] = "el modelo de dos etapas no es aplicable con estos supuestos: una sola etapa"
        return {"two_stage": out}
    out.update(applied=True, g_high=g1, retention=retention, retention_basis=ret_basis,
               pb_single=xm.get("pb_justified"), pb_justified=pb2,
               text=(f"dos etapas: {C['years']} años con crecimiento del {g1:.1%} ({ret_basis}), después ROE de la "
                     f"industria ({industry_roe:.1%}"
                     + (f", {roe_source}" if roe_source else "") + f") y g {g:.1%}"))
    upd: Dict[str, Any] = {"two_stage": out, "pb_justified": pb2,
                           "pb_ratio": (xm["pb"] / pb2) if xm.get("pb") else None}
    rote = xm.get("rote")
    if rote is not None and rote > 0:
        pt2 = two_stage_multiple(rote, min(bv, rote * retention), C["years"], industry_roe, g, ke)
        if pt2 is not None:
            out["ptbv_single"] = xm.get("ptbv_justified")
            upd.update(ptbv_justified=pt2, ptbv_ratio=(xm["ptbv"] / pt2) if xm.get("ptbv") else None)
    imp = _two_stage_implied(xm.get("implied") or {}, ke, g, C["years"], industry_roe, bv, retention)
    if imp:
        upd["implied"] = imp
    return upd


def _two_stage_implied(imp: Dict[str, Any], ke: float, g: float, years: int, stable: float, bv: float,
                       retention: float) -> Optional[Dict[str, Any]]:
    """F11 · N1 (revisión de NU y NFLX): con el justificado en dos etapas, el retorno que descuenta el precio se despeja
    con el MISMO modelo: los `years` años de la etapa alta con su retorno de hoy y, después, el retorno estable que hace
    que el modelo dé el múltiplo de mercado. Forma cerrada (el segundo término de two_stage_multiple es lineal en él):

        R_T = g + (M − etapa alta) · (Ke − g) · ((1 + Ke) / (1 + g₁))ⁿ

    La banda compara ese retorno con el estable que supone el justificado (el de la industria), y la sensibilidad mueve
    el retorno de la etapa alta, de modo que a ±0 da el justificado. El de una etapa queda en `single` (contexto)."""
    own, mult = imp.get("own"), imp.get("multiple")
    if imp.get("state") != "ok" or own is None or own <= 0 or not mult or mult <= 0:
        return None
    C = cfg("valuation.bank_implied")
    g1 = min(bv, own * retention)
    probe = two_stage_multiple(own, g1, years, g + 1.0, g, ke)      # con R_T − g = 1
    if probe is None:
        return None
    tail = (1 + g1) ** years / ((ke - g) * (1 + ke) ** years)      # ∂(P/B) / ∂R_T
    first = probe - tail                                           # la etapa alta sola (R_T = g)
    out = dict(imp, model="dos_etapas", years=years, g_high=g1, stable=stable,
               single={"implied": imp.get("implied"), "gap": imp.get("gap"), "band": imp.get("band"),
                       "sensitivity": imp.get("sensitivity")})
    if mult <= first:
        # La etapa alta ya justifica el precio: el precio no exige nada después.
        out.update(implied=g, gap=stable - g, band="barata",
                   reason="la etapa alta ya justifica el precio: no exige retorno por encima de g después")
    else:
        rt = g + (mult - first) / tail
        gap = stable - rt
        out.update(implied=rt, gap=gap,
                   band=("barata" if gap > C["band_pp"] else "en_precio" if gap >= -C["band_pp"]
                         else "exigente" if gap >= -C["very_demanding_pp"] else "muy_exigente"))
    out["sensitivity"] = [{"delta": d, "return": own + d,
                           "multiple_justified": two_stage_multiple(own + d, min(bv, (own + d) * retention), years,
                                                                    stable, g, ke)}
                          for d in C["rote_sensitivity_deltas"]]
    return out


def at1_by_year(st: Dict[str, Any]) -> List[Optional[float]]:
    """AT1 dentro del patrimonio de cada ejercicio (fase 3, T4; lib/ordinary.py): en un emisor IFRS, Yahoo deja el
    "Common Stock Equity" igual al patrimonio y da el AT1 en "Other Equity Interest". Es AT1 solo si el emisor paga
    cupones a esos instrumentos (beneficio de los propietarios > beneficio del ordinario); si no, 0."""
    # F10 · B2: los propietarios de la fuente (la serie `net_income` ya es la del común)
    ni, nic = st.get("net_income_owners") or st.get("net_income") or [], st.get("net_income_common") or []
    eq, cse, oei = st.get("stockholders_equity") or [], st.get("common_stock_equity") or [], \
        st.get("other_equity_interest") or []
    tol = cfg("valuation.bank_implied.at1_relative_tolerance")
    out = []
    for i in range(len(eq)):
        n, c = (ni[i] if i < len(ni) else None), (nic[i] if i < len(nic) else None)
        e, ce, o = eq[i], (cse[i] if i < len(cse) else None), (oei[i] if i < len(oei) else None)
        pays = n is not None and c is not None and (n - c) > tol * abs(n)
        inside = e is not None and ce is not None and abs(e - ce) <= tol * abs(e)
        out.append(o if (pays and inside and _pos(o)) else 0.0)
    return out


def book_multiples(km: Dict[str, Any], ordinary: Optional[Dict[str, Any]], eq_fy: Optional[float],
                   tbv_fy: Optional[float], fy_end: Optional[str]) -> Dict[str, Any]:
    """F9 · R3 (una sola verdad por cifra): el P/B del modelo es el de la tabla de múltiplos (key_metrics.pb: precio
    entre el valor en libros del ordinario del balance del corte). NU: 5.33x con el patrimonio del FY2025 en la portada
    frente a 4.54x con el del 30-jun en la tabla. El P/TBV, con el tangible del mismo balance. Sin el balance del
    corte, el del último ejercicio, y se dice."""
    mcap, o = km.get("market_cap"), ordinary or {}
    pb_now, eq_now, tbv_now = _num(km.get("pb")), o.get("equity_common"), o.get("tangible_common")
    if pb_now is not None and pb_now > 0:
        pb, basis = pb_now, {"type": "corte", "date": o.get("period_end")}
    else:
        pb = (mcap / eq_fy) if (_pos(mcap) and _pos(eq_fy)) else None
        basis = {"type": "ejercicio", "date": fy_end} if pb is not None else None
    if pb is not None and basis["type"] == "corte" and _pos(eq_now) and _pos(tbv_now):
        ptbv, tbasis = pb * eq_now / tbv_now, {"type": "corte", "date": o.get("period_end")}
    else:
        ptbv = (mcap / tbv_fy) if (_pos(mcap) and _pos(tbv_fy)) else None
        tbasis = {"type": "ejercicio", "date": fy_end} if ptbv is not None else None
    return {"pb": pb, "ptbv": ptbv, "pb_basis": basis, "ptbv_basis": tbasis}


def _financial(st: Dict[str, Any], km: Dict[str, Any], beta: Optional[float],
               rf: Optional[float] = None, beta_preadjusted: bool = False,
               subtype: Optional[str] = None, ke: Optional[float] = None,
               ordinary: Optional[Dict[str, Any]] = None,
               history_fy: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    ni, eq, tbv = st.get("net_income") or [], st.get("stockholders_equity") or [], st.get("tangible_book_value") or []
    rev = st.get("revenue") or []
    mcap = km.get("market_cap")
    ni0, eq0, tbv0, rev0 = _first(ni), _first(eq), _first(tbv), _first(rev)
    roe_series = ratio_series(ni, eq)
    roe_fy = _first(roe_series)
    # Fase 3 (T4, §1.4 y §3): ROTE del accionista ordinario, ajustado por AT1 (beneficio del ordinario sobre el
    # tangible sin AT1). En EE. UU. Yahoo ya resta los preferentes; en un banco IFRS (BCS) el AT1 sigue dentro.
    nic = st.get("net_income_common") or []
    ni_ord = [(c if c is not None else n) for n, c in zip(ni, nic + [None] * (len(ni) - len(nic)))] if ni else []
    at1 = at1_by_year(st)
    tbv_ord = [(t - (at1[i] if i < len(at1) else 0.0)) if t is not None else None for i, t in enumerate(tbv)]
    rote_series = ratio_series(ni_ord, tbv_ord)
    rote = _first(rote_series)
    tbv_ord0 = _first(tbv_ord)
    ke, g = cost_of_equity(beta, rf, beta_preadjusted, ke), cfg("valuation.dcf.terminal_growth")   # β ajustada
    _bm = book_multiples(km, ordinary, eq0, tbv_ord0, _first(st.get("bs_ends") or []))
    pb, ptbv = _bm["pb"], _bm["ptbv"]
    # §8.8: aseguradora y conglomerado, ROE medio del ciclo de suscripción (los ejercicios disponibles), no el de un
    # año; banco, el ROTE del último ejercicio (§3) con la media como contexto.
    roe_vals = [x for x in roe_series if x is not None]
    roe_avg = mean(roe_vals) if roe_vals else None
    rote_vals = [x for x in rote_series if x is not None]
    rote_avg = mean(rote_vals) if rote_vals else None
    roe_ref = roe_avg if subtype in ("aseguradora", "conglomerado") else roe_fy
    j_pb, j_ptbv = justified_multiple(roe_ref, ke, g), justified_multiple(rote, ke, g)
    implied = _implied_reading(subtype, pb, ptbv, ke, g, roe_ref=roe_ref, roe_years=len(roe_vals), rote=rote,
                               rote_avg=rote_avg, rote_years=len(rote_vals), at1=_first(at1))

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

    # Fase 3 (T4, §1.4): crecimiento bancario con el margen de intereses y las comisiones. El "Total Revenue" de un
    # banco ya es el ingreso neto (margen de intereses + otros ingresos); el margen de intereses, aparte.
    nii = st.get("net_interest_income") or []
    nii_cagr, nii_why = strict_cagr(nii, 3)
    nii_share = (_first(nii) / rev0) if (_first(nii) is not None and _pos(rev0)) else None
    bv_series = tbv if (tbv and all(_pos(x) for x in tbv[:4])) else eq
    bv_growth, bv_why = strict_cagr(bv_series, 3)
    rev_yoy = _first(yoy_growths(rev))
    return {
        "cost_of_equity": ke, "terminal_growth": g,
        "beta_raw": None if (beta_preadjusted and beta is not None) else (
            beta if beta is not None else cfg("valuation.capm.default_beta")),
        "beta_adjusted": _blume(beta, beta_preadjusted),
        "roe_fy": roe_fy, "rote": rote, "pb": pb, "ptbv": ptbv,
        "pb_basis": _bm["pb_basis"], "ptbv_basis": _bm["ptbv_basis"],
        "roe_avg": roe_avg, "roe_reference": roe_ref, "rote_avg": rote_avg, "rote_years": len(rote_vals),
        "at1": _first(at1), "tangible_book_ordinary": tbv_ord0, "implied": implied,
        "pb_justified": j_pb, "ptbv_justified": j_ptbv,
        "pb_ratio": (pb / j_pb) if (pb is not None and j_pb) else None,
        "ptbv_ratio": (ptbv / j_ptbv) if (ptbv is not None and j_ptbv) else None,
        **_roe_stability(roe_series, _by_end(history_fy or {}, "net_income")),
        "efficiency_ratio": efficiency, "efficiency_reason": nie_why,
        "book_value_cagr_3y": bv_growth, "book_value_cagr_3y_reason": bv_why,
        "book_value_basis": "tangible" if bv_series is tbv else "contable",
        "revenue_growth_statements": rev_yoy,
        "net_interest_income_cagr_3y": nii_cagr, "net_interest_income_cagr_3y_reason": nii_why,
        "net_interest_income_share": nii_share,
        # F11 · T7: el ROE de cada ejercicio, el ancla de la persistencia de un subtipo sin margen neto (banco).
        "roe_by_year": [{"fy_end": str(e)[:10], "roe": r} for e, r in zip(st.get("bs_ends") or [], roe_series)
                        if e and r is not None],
    }


def _roe_stability(roe_series, ni_history: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    """σ del ROE (más reciente primero). F9 · R7 (revisión externa de NU): el paso de pérdidas a ganancias no es
    volatilidad del beneficio. Es un paso solo si la historia anual de EDGAR (`ni_history`, {cierre: beneficio neto})
    no tiene ningún ejercicio con beneficio antes de la última pérdida (NU: pérdidas en 2019–2022, beneficio desde 2023).
    Entonces la estabilidad se mide desde el paso a beneficios, y se dice; con menos de 3 ejercicios con beneficio no se
    evalúa (no significativa, no resta). Una pérdida entre ejercicios con beneficio es volatilidad y cuenta (BRK-B:
    beneficio en 2021, pérdida contable en 2022); sin la historia larga, la ventana corta no lo distingue y cuenta."""
    chron = [x for x in reversed(roe_series) if x is not None]
    whole = {"roe_std": stdev(chron) if len(chron) >= 3 else None, "roe_years": len(chron), "roe_std_basis": None,
             "roe_std_reason": None}
    long = [v for _, v in sorted((ni_history or {}).items())]
    last_long = max((i for i, v in enumerate(long) if v <= 0), default=None)
    last_loss = max((i for i, x in enumerate(chron) if x <= 0), default=None)
    if (last_loss is None or last_long is None or any(v > 0 for v in long[:last_long])
            or any(x > 0 for x in chron[:last_loss])):
        return whole
    run = chron[last_loss + 1:]
    if len(run) >= 3:
        return {"roe_std": stdev(run), "roe_years": len(run), "roe_std_basis": "desde el paso a beneficios",
                "roe_std_reason": None}
    return {"roe_std": None, "roe_years": len(run), "roe_std_basis": "desde el paso a beneficios",
            "roe_std_reason": (f"pasó de pérdidas a beneficios hace {len(run)} ejercicio{'s' if len(run) != 1 else ''}: "
                               "el cambio no es volatilidad del beneficio y la estabilidad necesita 3 con beneficio")}


def _implied_reading(subtype, pb, ptbv, ke, g, *, roe_ref, roe_years, rote, rote_avg, rote_years, at1):
    """ROTE (banco) o ROE (aseguradora, conglomerado) que descuenta el precio frente al que obtiene (F3_DISENO §3,
    §8.8): banda y sensibilidad (P/TBV o P/B justificado a ±2 pp)."""
    import bank_implied as bi
    C = cfg("valuation.bank_implied")
    bank = subtype == "banco"
    if bank:
        imp = bi.implied_rote(ptbv, ke, g)
        own, label, mult = rote, "ROTE", ptbv
    else:
        imp = bi.implied_roe(pb, ke, g)
        own, label, mult = roe_ref, "ROE", pb
    out = {"metric": label, "state": imp["state"], "reason": imp["reason"], "implied": imp["value"],
           "multiple": mult, "own": own, "own_avg": rote_avg if bank else roe_ref,
           "own_years": rote_years if bank else roe_years, "at1": at1 if bank else None,
           "band": None, "gap": None, "sensitivity": [], "subtype": subtype}
    if imp["state"] != bi.OK or own is None:
        return out
    gap = own - imp["value"]
    band = ("barata" if gap > C["band_pp"] else "en_precio" if gap >= -C["band_pp"]
            else "exigente" if gap >= -C["very_demanding_pp"] else "muy_exigente")
    out.update(gap=gap, band=band,
               sensitivity=[{"delta": d, "return": own + d, "multiple_justified": justified_multiple(own + d, ke, g)}
                            for d in C["rote_sensitivity_deltas"]])
    return out


def _per_share(values: List[Optional[float]], shares: List[Optional[float]]) -> List[Optional[float]]:
    return [(v / s) if (v is not None and _pos(s)) else None for v, s in zip(values or [], shares or [])]


def _reit(st: Dict[str, Any], km: Optional[Dict[str, Any]] = None,
          reit_ffo: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    # F8 · E3: FFO según Nareit, la misma definición que el TTM (lib/reit_ffo): beneficio + D&A − ventas de inmuebles +
    # deterioros de cada ejercicio, del estado de flujos que presentó el emisor; sin esos ajustes, el ejercicio queda sin
    # dato. Fase 3 (T1b): con el EBITDA = EBIT del emisor + D&A, "EBITDA − EBIT de Yahoo" ya no es la D&A; sin la fila
    # de D&A, esa diferencia como antes.
    import reit_ffo as _rf
    ni, ebitda, ebit = st.get("net_income") or [], st.get("ebitda") or [], st.get("ebit") or []
    # F13 · paso 7 (revisión de 110 empresas, patrón 10d): desde el beneficio de las operaciones continuadas, el del
    # perímetro vigente (CCI 2024: −5,07 B$ de discontinuadas, la fibra vendida, dejaban el FFO por acción en −6,95 $)
    disc = st.get("net_income_discontinued") or []
    ni = [(n - (disc[i] if i < len(disc) and disc[i] else 0.0)) if n is not None else None for i, n in enumerate(ni)]
    da = st.get("depreciation_amortization") or []
    if da and len([x for x in da if x is not None]) >= len([x for x in ni if x is not None]):
        base = [(n + abs(d)) if (n is not None and d is not None) else None for n, d in zip(ni, da)]
    else:
        base = [(n + (a - b)) if (n is not None and a is not None and b is not None) else None
                for n, a, b in zip(ni, ebitda, ebit)]
    ends = st.get("inc_ends") or []
    got = [_rf.fy_ffo(reit_ffo, ends[i] if i < len(ends) else None, b) for i, b in enumerate(base)]
    ffo = [v for v, _why in got]
    shares = st.get("ordinary_shares") or []
    ffo_ps = _per_share(ffo, shares)
    ffo_ps_cagr, ffo_ps_why = strict_cagr(ffo_ps, 3)
    if ffo_ps_cagr is None and (reit_ffo or {}).get("status") != "ok":
        ffo_ps_why = f"FFO según Nareit sin dato: {(reit_ffo or {}).get('reason') or 'sin los ajustes del emisor'}"
    elif ffo_ps_cagr is None and any(why for _v, why in got[:4]):
        ffo_ps_why = next(why for _v, why in got[:4] if why)
    fcf_ps_cagr, fcf_ps_why = fcf_cagr(_per_share(st.get("free_cash_flow") or [], shares))
    # Etapa 9a: rentabilidad sobre el FFO (TTM, la misma definición del P/FFO).
    km = km or {}
    ffo_ttm, eq, rev, ta = km.get("ffo"), km.get("total_equity"), km.get("revenue"), km.get("total_assets")
    return {
        "ffo_ttm": ffo_ttm,
        # Fase 7: la rentabilidad del FFO se mide sobre los activos (puntúa); sobre el patrimonio, solo informativa.
        "ffo_to_assets": (ffo_ttm / ta) if (ffo_ttm is not None and _pos(ta)) else None,
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


def yearly_financials(st: Optional[Dict[str, Any]], archetype: Optional[str] = None) -> List[Dict[str, Any]]:
    """Histórico anual (etapa 9b): los mismos estados anuales que alimentan los CAGR.

    Dato bruto, sin lecturas: ingresos, beneficio neto, FCF y márgenes por ejercicio
    (más antiguo primero); en GROWTH_PRE_PROFIT además FCF − SBC. Los ejercicios de la
    cuenta de resultados y del estado de flujos se alinean por año."""
    st = st or {}
    inc_y, cf_y = st.get("inc_years") or [], st.get("cf_years") or []
    def at(key, years, y):
        vals = st.get(key) or []
        i = years.index(y) if y in years else None
        return vals[i] if (i is not None and i < len(vals)) else None
    out = []
    for y in sorted(set(inc_y) | set(cf_y)):
        rev, ni, gp, oi = (at("revenue", inc_y, y), at("net_income", inc_y, y), at("gross_profit", inc_y, y),
                           at("operating_income", inc_y, y))
        fcf, sbc = at("free_cash_flow", cf_y, y), at("stock_based_compensation", cf_y, y)
        if not_applicable(archetype, "fcf"):     # FINANCIAL: el FCF de un banco no se lee
            fcf = None
        if all(v is None for v in (rev, ni, fcf)):
            continue
        m = lambda a: (a / rev) if (a is not None and _pos(rev)) else None
        row = {"year": int(y) if str(y).isdigit() else y, "revenue": rev, "net_income": ni, "free_cash_flow": fcf,
               "gross_margin": m(gp), "operating_margin": m(oi), "net_margin": m(ni), "fcf_margin": m(fcf)}
        if archetype == GROWTH_PRE_PROFIT:
            row["sbc"] = sbc
            row["fcf_minus_sbc"] = (fcf - sbc) if (fcf is not None and sbc is not None) else None
            row["fcf_minus_sbc_margin"] = m(row["fcf_minus_sbc"])
        out.append(row)
    return out


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
                       st: Optional[Dict[str, Any]] = None, sbc: Optional[Dict[str, Any]] = None,
                       revenue_cagr_3y_reason: Optional[str] = None,
                       revenue_cagr_3y_bound: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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
    # F10 (PM, 29-oct): con el crecimiento no significativo, su cota (desde una base baja, superior) + el margen es una
    # cota de la regla de 40; puntúa solo si ya decide el tramo (el peor), y lo declara.
    r40_bound = None
    if r40 is None and fcf_margin is not None and is_anomalous_not_significant(revenue_cagr_3y_reason) \
            and (revenue_cagr_3y_bound or {}).get("value") is not None:
        _b = {**revenue_cagr_3y_bound, "value": revenue_cagr_3y_bound["value"] + fcf_margin}
        if bound_decides(_b, cfg("thresholds.score.valoracion.rule_of_40_bounds")) is not None:
            r40, r40_bound = _b["value"], {**_b, "growth": revenue_cagr_3y_bound["value"]}
    ev_sales = km.get("ev_revenue")
    # key_metrics.cash = fila "Cash Cash Equivalents And Short Term Investments"
    # (caja + inversiones a corto plazo) del último balance.
    return {"ev_sales": ev_sales if _pos(ev_sales) else None, "fcf_margin": fcf_margin,
            "fcf_margin_basis": "FCF − SBC", "fcf_margin_reason": sbc.get("reason"),
            "fcf_margin_raw": (fcf / rev) if (fcf is not None and _pos(rev)) else None,
            "revenue_cagr_3y": revenue_cagr_3y, "rule_of_40": r40, "ebitda": km.get("ebitda"),
            # F10: con el crecimiento no significativo (año base anómalo), la regla de 40 tampoco lo es, con su motivo
            "rule_of_40_bound": r40_bound,
            "rule_of_40_reason": (revenue_cagr_3y_reason
                                  if r40 is None and is_anomalous_not_significant(revenue_cagr_3y_reason) else None),
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
    sbc = st.get("stock_based_compensation") or []
    series, series_sbc = [], []
    for i, (o, c, d) in enumerate(zip(ocf, capex, da)):
        if o is None or d is None:
            series.append(None)
            series_sbc.append(None)
            continue
        m = min(abs(d), abs(c)) if c is not None else abs(d)
        series.append(o - m)
        s = sbc[i] if i < len(sbc) else None
        series_sbc.append(o - m - s if s is not None else None)
    vals = [x for x in series if x is not None]
    # Fase 3 (T3, §8.4): FCF − SBC siempre que haya SBC, en los MISMOS ejercicios (la SBC es un coste real que el
    # flujo operativo devuelve como gasto sin caja). Sin SBC en alguno de ellos, sin dato (nunca mezclar).
    vals_sbc = [x for x in series_sbc if x is not None]
    complete = bool(vals) and len(vals_sbc) == len(vals)
    return {"value": mean(vals) if vals else None, "years": len(vals), "series": series,
            "value_minus_sbc": mean(vals_sbc) if complete else None,
            "reason": None if vals else "sin flujo operativo y D&A del mismo ejercicio"}


def investment_intensity(st: Dict[str, Any], years: Optional[int] = None) -> Dict[str, Any]:
    """F13 · paso 9 (revisión de 110 empresas, patrón 2): cuánto invierte frente a lo que repone. Capex ÷ D&A sumados en
    los últimos `years` ejercicios con los dos datos (la D&A aproxima el capex de mantenimiento, como en
    maintenance_fcf). {ratio, to_ocf, years, capex, da, ocf} o {ratio: None, reason}."""
    years = years or cfg("valuation.investment_intensity.years")
    capex, da = st.get("capital_expenditure") or [], st.get("depreciation_amortization") or []
    ocf = st.get("operating_cash_flow") or []
    rows = [(abs(c), abs(d), (ocf[i] if i < len(ocf) else None)) for i, (c, d) in enumerate(zip(capex, da))
            if c is not None and d is not None and d][:years]
    if len(rows) < years:
        return {"ratio": None, "to_ocf": None, "years": len(rows),
                "reason": f"capex y D&A de {len(rows)} ejercicios (hacen falta {years})"}
    c, d = sum(r[0] for r in rows), sum(r[1] for r in rows)
    o = sum(r[2] for r in rows) if all(r[2] is not None for r in rows) else None
    return {"ratio": c / d, "to_ocf": (c / o) if o and o > 0 else None, "years": len(rows), "capex": c, "da": d,
            "ocf": o, "reason": None}


def expansion(intensity: Dict[str, Any], ttm_capex_to_ocf: Optional[float]) -> bool:
    """F13 · paso 9: ¿invierte en expansión? capex ≥ min_capex_to_da × D&A y ≥ min_capex_to_ocf del flujo operativo (en
    los ejercicios medidos o en el TTM: META acelera su inversión en el último año, 78 % del flujo frente a ~50 % en
    tres). Sin medida, no."""
    C = cfg("valuation.investment_intensity")
    r, o = (intensity or {}).get("ratio"), (intensity or {}).get("to_ocf")
    if r is None or r < C["min_capex_to_da"]:
        return False
    return max(x for x in (o, ttm_capex_to_ocf, 0.0) if x is not None) >= C["min_capex_to_ocf"]


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
        "fcf_maintenance_minus_sbc": maint["value_minus_sbc"],
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


def growth_values(archetype: str, st_local: Dict[str, Any]) -> Dict[str, Any]:
    """Fase 3 (T1b): las métricas de crecimiento de la rama medidas con las filas anuales en la moneda de los estados
    (lib/growth_currency.local). Solo crecimientos: lo que mezcla las filas con importes del precio (EV/EBITDA,
    FCF normalizado) sigue en compute() con las filas convertidas."""
    if archetype == CYCLICAL:
        lo, hi = _V["cyclical_growth_bounds"]
        rev = st_local.get("revenue") or []
        eps = st_local.get("diluted_eps") or _per_share(st_local.get("net_income") or [],
                                                         st_local.get("ordinary_shares") or [])
        g_raw, e_raw = mean(yoy_growths(rev)), mean(yoy_growths(eps))
        return {"revenue_growth_normalized_raw": g_raw,
                "revenue_growth_normalized": None if g_raw is None else min(hi, max(lo, g_raw)),
                "eps_growth_normalized_raw": e_raw,
                "eps_growth_normalized": None if e_raw is None else min(hi, max(lo, e_raw))}
    if archetype == FINANCIAL:
        return {"revenue_growth_statements": _first(yoy_growths(st_local.get("revenue") or []))}
    return {}


def compute(archetype: str, statements_fy: Optional[Dict[str, Any]], key_metrics: Dict[str, Any], *,
            beta: Optional[float] = None, revenue_cagr_3y: Optional[float] = None,
            revenue_cagr_3y_reason: Optional[str] = None, revenue_cagr_3y_bound: Optional[Dict[str, Any]] = None,
            rf: Optional[float] = None, sbc: Optional[Dict[str, Any]] = None,
            beta_preadjusted: bool = False, subtype: Optional[str] = None,
            reit_ffo: Optional[Dict[str, Any]] = None, ke: Optional[float] = None,
            ordinary: Optional[Dict[str, Any]] = None,
            history_fy: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Métricas de la rama del arquetipo ({} si la rama no necesita ninguna). `reit_ffo`: los ajustes Nareit de cada
    ejercicio (lib/reit_ffo.resolve), para el FFO anual del REIT. `ke`: el Ke único del análisis. `history_fy`: la
    historia anual de EDGAR (F9 · R7: si el paso de pérdidas a ganancias lo es de verdad)."""
    st = statements_fy or {}
    if archetype == FINANCIAL:
        return _financial(st, key_metrics, beta, rf, beta_preadjusted, subtype=subtype, ke=ke, ordinary=ordinary,
                          history_fy=history_fy)
    if archetype == GROWTH_PRE_PROFIT:
        return _growth_pre_profit(key_metrics, revenue_cagr_3y, st, sbc, revenue_cagr_3y_reason,
                                  revenue_cagr_3y_bound)
    if archetype == REIT:
        return _reit(st, key_metrics, reit_ffo)
    if archetype == CYCLICAL:
        return _cyclical(st, key_metrics)
    if archetype == "UTILITY":
        return _utility(st, key_metrics, beta, rf, beta_preadjusted, ke=ke, ordinary=ordinary)
    return {}


def _utility(st: Dict[str, Any], km: Dict[str, Any], beta: Optional[float], rf: Optional[float],
             beta_preadjusted: bool, ke: Optional[float] = None,
             ordinary: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Utility regulada (fase 3, T7): su método intrínseco estándar es el P/B frente al ROE que el regulador le
    permite ganar sobre su base de activos. ROE implícito = P/B × (Ke − g) + g frente al ROE medio de los ejercicios
    (el regulado se revisa en ciclos tarifarios: la media, no un año)."""
    ni, eq = st.get("net_income") or [], st.get("stockholders_equity") or []
    roe_vals = [x for x in ratio_series(ni, eq) if x is not None]
    roe_avg = mean(roe_vals) if roe_vals else None
    _bm = book_multiples(km, ordinary, _first(eq), None, _first(st.get("bs_ends") or []))
    pb = _bm["pb"]
    ke, g = cost_of_equity(beta, rf, beta_preadjusted, ke), cfg("valuation.dcf.terminal_growth")
    j_pb = justified_multiple(roe_avg, ke, g)
    implied = _implied_reading("utility", pb, None, ke, g, roe_ref=roe_avg, roe_years=len(roe_vals), rote=None,
                               rote_avg=None, rote_years=0, at1=None)
    return {"cost_of_equity": ke, "terminal_growth": g, "pb": pb, "pb_basis": _bm["pb_basis"], "roe_avg": roe_avg,
            "pb_justified": j_pb,
            "pb_ratio": (pb / j_pb) if (pb is not None and j_pb) else None, "implied": implied}


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
