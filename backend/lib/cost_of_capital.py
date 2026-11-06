"""
Coste de capital (etapa 8; spec fallo 5, RECON C4).

Un solo WACC por análisis: el que usan el DCF, el grid y el spread ROIC−WACC, y
el que se muestra.

    WACC = E/(D+E)·Ke + D/(D+E)·Kd·(1 − t)

  E   capitalización bursátil (valor de mercado).
  D   deuda financiera total ("Total Debt" de Yahoo, que ya incluye las
      obligaciones por arrendamiento financiero cuando la empresa las informa:
      FCX 8.91 + 0.47 + 1.11 = 10.49B). Los arrendamientos operativos no
      aparecen en esa fila (NFLX, V) y no se añaden.
  Ke  CAPM: Rf + β ajustada (Blume: 0.67·β bruta + 0.33) × prima implícita de
      Damodaran (config, con fuente y fecha), con PISOS (F8 · E1): Ke ≥ Rf + 0,5 × ERP
      y, con deuda, Ke ≥ Kd + 1 pp (`equity_cost`). Un solo Ke por análisis: el del
      WACC, el del P/B justificado (FINANCIAL, UTILITY) y el del DCF del REIT.
      F9 · R1: más la prima de riesgo país ponderada por dónde opera la empresa
      (lib/country_risk.py), antes de los pisos.
  Kd  Rf + spread del rating sintético por cobertura de intereses (tabla de
      Damodaran, grandes y pequeñas por capitalización). Regla M: cobertura no
      significativa (EBIT < 0 con caja neta) -> tramo de caja neta; EBIT < 0 con
      deuda neta -> peor tramo. Ambos casos se marcan.
  t   tasa efectiva = provisión de impuestos / beneficio antes de impuestos,
      acotada; con BAI <= 0 o sin dato, el tipo legal. La misma t entra en el
      NOPAT del ROIC.
  Rf  F8 · E1: el del par Rf–ERP de config (Damodaran, la misma fecha que la
      prima: `capm_rates`). El ^TNX del día (caché de 24 h) queda como referencia
      y avisa si se aleja del par (hay que actualizarlo).

El WACC se acota a un ÚNICO rango (valuation.wacc.clamp_min/max). FINANCIAL no
usa WACC (se valora por P/B justificado con Ke); REIT tiene WACC (spread) pero
no DCF.
"""
import contextvars
import datetime as _dt
import time
from typing import Any, Dict, Optional

from settings import cfg

_RF_CACHE: Dict[str, Any] = {}
# F8 · E1: desplazamiento del Ke de la prueba de sensibilidad (lib/ke_sensitivity.py); 0 en el análisis normal.
KE_SHIFT: contextvars.ContextVar = contextvars.ContextVar("ke_shift", default=0.0)


def reset_cache() -> None:
    _RF_CACHE.clear()


def _fetch_risk_free() -> Optional[Dict[str, Any]]:
    """Último cierre de ^TNX (en %) -> {value (decimal), as_of}. None sin dato."""
    import yfinance as yf
    hist = yf.Ticker(cfg("valuation.capm.risk_free_ticker")).history(period="5d")
    if hist is None or getattr(hist, "empty", True) or "Close" not in hist:
        return None
    closes = [(idx, float(v)) for idx, v in zip(hist.index, hist["Close"].tolist()) if v == v]
    if not closes:
        return None
    idx, v = closes[-1]
    return {"value": v / 100, "as_of": str(getattr(idx, "date", lambda: idx)())}


def risk_free(now: Optional[float] = None) -> Dict[str, Any]:
    """Rf con su procedencia: {value, source, as_of, fallback, reason}."""
    C = cfg("valuation.capm")
    now = time.time() if now is None else now
    hit = _RF_CACHE.get("rf")
    if hit and now - hit["at"] < C["risk_free_cache_hours"] * 3600:
        return dict(hit["value"])
    try:
        got = _fetch_risk_free()
        why = None if got else "sin cotización"
    except Exception as e:  # red, bloqueo, formato: nunca rompe el análisis
        got, why = None, type(e).__name__
    lo, hi = C["risk_free_bounds"]
    if got and lo < got["value"] < hi:
        out = {"value": got["value"], "source": C["risk_free_ticker"], "as_of": got["as_of"],
               "fallback": False, "reason": None}
        _RF_CACHE["rf"] = {"value": out, "at": now}    # solo se cachea una lectura válida
        return dict(out)
    if got and why is None:
        why = f"lectura fuera de rango ({got['value']:.2%})"
    return {"value": C["risk_free_rate"], "source": "config", "as_of": None, "fallback": True,
            # V7 (M4): para el lector, qué falta y qué se usa (no el símbolo de Yahoo ni "config").
            "reason": (f"el rendimiento del bono del Tesoro de EE. UU. a 10 años no está disponible ({why}): se usa "
                       f"el valor de referencia del modelo, {C['risk_free_rate']:.2%}")}


def capm_rates(now: Optional[float] = None) -> Dict[str, Any]:
    """F8 · E1: Rf y ERP de la MISMA fecha (el par de config, Damodaran) para el Ke, el Kd y el WACC. El ^TNX del día
    (`risk_free`) va en `market` como referencia; si se aleja del par más de `pair_drift_warning`, `reason` lo dice.
    Antes: el Rf del día (4,99 % el 26-oct) con una ERP calculada con otro Rf (5,29 % el 1-oct)."""
    C = cfg("valuation.capm")
    live = risk_free(now)
    market = None if live.get("fallback") else {"value": live["value"], "source": live["source"],
                                                  "as_of": live.get("as_of")}
    out = {"value": C["risk_free_rate"], "erp": C["market_risk_premium"], "source": "par Rf–ERP de Damodaran",
           "as_of": C["pair_as_of"], "fallback": False, "reason": None, "market": market}
    if market is not None and abs(market["value"] - C["risk_free_rate"]) > C["pair_drift_warning"]:
        out["reason"] = (f"el bono a 10 años cotiza hoy al {market['value']:.2%}, a más de "
                         f"{C['pair_drift_warning'] * 100:.1f} pp del Rf del par ({C['risk_free_rate']:.2%} a "
                         f"{C['pair_as_of']}): el par Rf–ERP debe actualizarse")
    # F13 · paso 1: la revisión mensual del par (config/review.toml) se vigila en ejecución, no solo con la herramienta.
    import parameter_review
    out["review"] = parameter_review.parameter("market_risk_premium", _today())
    if out["review"]["status"] == "revisar":
        late = (f"la revisión mensual del par Rf–ERP de Damodaran ({C['pair_as_of']}) venció el "
                f"{out['review']['due']}: el coste del capital usa una prima que puede no ser la vigente")
        out["reason"] = f"{out['reason']}; {late}" if out["reason"] else late
    return out


def _today() -> _dt.date:
    """Hoy, para la revisión del par (el replay lo fija al día de la captura: los golden no dependen del día)."""
    return _dt.date.today()


def effective_tax_rate(pretax: Optional[float], tax: Optional[float], period: str = "") -> Dict[str, Any]:
    """t = provisión / BAI acotada; con BAI <= 0 o sin dato, el tipo legal."""
    T = cfg("valuation.tax")
    lo, hi = T["effective_bounds"]
    if pretax is None or tax is None or pretax <= 0:
        why = "beneficio antes de impuestos ≤ 0" if (pretax is not None and pretax <= 0) else \
            "sin beneficio antes de impuestos o provisión de impuestos"
        return {"rate": T["statutory_rate"], "source": "legal", "raw": None, "bounded": False, "period": period,
                "reason": f"{why}: tipo legal {T['statutory_rate']:.0%}"}
    raw = tax / pretax
    rate = min(hi, max(lo, raw))
    bounded = rate != raw
    return {"rate": rate, "source": "efectiva", "raw": raw, "bounded": bounded, "period": period,
            "reason": (f"tasa efectiva {raw:.1%} acotada a [{lo:.0%}, {hi:.0%}]" if bounded else None)}


def synthetic_rating(coverage: Optional[float], market_cap: Optional[float],
                     coverage_state: Optional[str] = None) -> Dict[str, Any]:
    """Rating sintético por cobertura de intereses (EBIT / intereses) y su spread."""
    R = cfg("valuation.synthetic_rating")
    large = market_cap is not None and market_cap >= R["large_cap_min"]
    bounds = R["large_coverage_bounds"] if large else R["small_coverage_bounds"]
    flag = None
    if coverage_state == "sin_carga":
        rating = R["ratings"][0]
        flag = "sin carga financiera neta (EBIT > 0 e ingresos financieros netos) -> mejor tramo"
    elif coverage_state == "no_significativo":
        rating = R["net_cash_rating"]
        flag = "regla M: EBIT < 0 con caja neta, cobertura no significativa -> tramo de caja neta"
    elif coverage_state == "negativa":
        rating = R["negative_rating"]
        flag = "regla M: EBIT < 0 con deuda neta -> peor tramo"
    elif coverage is None:
        rating = R["no_coverage_rating"]
        flag = "sin cobertura de intereses: tramo por defecto"
    else:
        i = next((k for k, b in enumerate(bounds) if coverage > b), len(bounds))
        rating = R["ratings"][i]
    return {"rating": rating, "spread": R["spreads"][R["ratings"].index(rating)],
            "table": "grandes" if large else "pequeñas", "coverage": coverage, "flag": flag}


def adjusted_beta(beta: Optional[float], preadjusted: bool = False) -> float:
    """Beta ajustada de Blume: blume_weight × β bruta + blume_prior (sin beta: la de mercado). Fase 2b (T6): una beta
    del sector (`preadjusted`) ya es una media de industria y entra tal cual (Blume corrige el error de estimación de
    una sola regresión)."""
    C = cfg("valuation.capm")
    if preadjusted and beta is not None:
        return beta
    raw = beta if beta is not None else C["default_beta"]
    return C["blume_weight"] * raw + C["blume_prior"]


def cost_of_equity(beta: Optional[float], rf: float, preadjusted: bool = False) -> float:
    """Ke = Rf + β ajustada (Blume) × prima implícita. `beta` es la beta BRUTA (o la del sector, `preadjusted`)."""
    return rf + adjusted_beta(beta, preadjusted) * cfg("valuation.capm.market_risk_premium")


def rating_coverage(*, coverage: Optional[float], state: Optional[str], ebit: Optional[float],
                    ebit_normalized: Optional[float], interest: Optional[float], reit: bool,
                    ebitda: Optional[float], operating_cash_flow: Optional[float], depreciation: Optional[float],
                    market_cap: Optional[float], state_fn, equity_income: Optional[float] = None) -> Dict[str, Any]:
    """F13 · paso 2 (revisión de 110 empresas, patrón 3): la cobertura de intereses con la que se busca el rating
    sintético (Kd y, por el piso Ke ≥ Kd + 1 pp, el Ke). Antes era siempre el EBIT contable del TTM: un deterioro sin
    salida de caja daba rating D y llevaba el WACC al tope (KHC, APD, MOS: 20 %; WELL, REIT: CC y 18,5 %).

    Por orden: (1) REIT: EBITDA / intereses (la depreciación inmobiliaria no es un coste de caja); (2) el EBIT
    normalizado (sin los cargos que la normalización ya quita del operativo: deterioros, reestructuración, I+D
    adquirida), si es mayor que el contable; (3) si aun así sale un rating de impago con la caja operativa positiva, el
    rating es incoherente y se usa la cobertura de caja: (flujo operativo + intereses − D&A) / intereses, en la escala
    del EBIT. La nota y las alertas siguen con la cobertura contable: esto es solo el coste de la deuda.

    `state_fn(coverage, ebit)`: el estado de la cobertura (financial_ratios.interest_coverage_state con la deuda neta y
    el resultado financiero neto del análisis). -> {coverage, state, basis, reason, reported}"""
    R = cfg("valuation.synthetic_rating")
    out = {"coverage": coverage, "state": state, "basis": "EBIT", "reason": None,
           "reported": {"coverage": coverage, "state": state}}
    ie = abs(interest) if interest else None
    if not ie:
        return out
    if reit and ebitda is not None:
        out.update(coverage=ebitda / ie, state=state_fn(ebitda / ie, ebitda), basis="EBITDA",
                   reason="REIT: cobertura con el EBITDA (la depreciación inmobiliaria no es un coste de caja)")
    elif ebit_normalized is not None and ebit is not None and ebit_normalized > ebit:
        out.update(coverage=ebit_normalized / ie, state=state_fn(ebit_normalized / ie, ebit_normalized),
                   basis="EBIT normalizado",
                   reason="cobertura con el EBIT normalizado (sin los cargos que la normalización quita del operativo)")
    # F13 (decisión del usuario: SRE y Oncor): el resultado de las participadas operativas (método de participación,
    # positivo) se suma al EBIT de la cobertura: la parte proporcional de su negocio también paga la deuda de la matriz.
    if equity_income and equity_income > 0 and out["basis"] != "EBITDA":
        base = (ebit_normalized if out["basis"] == "EBIT normalizado" else ebit)
        # solo si pesa: por debajo de `coverage_equity_min_share` del EBIT no cambia la lectura
        if base is not None and base > 0 and equity_income >= R["coverage_equity_min_share"] * base:
            cov = (base + equity_income) / ie
            out.update(coverage=cov, state=state_fn(cov, base + equity_income), basis=out["basis"] + " + participadas",
                       equity_income=equity_income,
                       reason=((out["reason"] + "; ") if out["reason"] else "")
                       + f"con el resultado de las participadas operativas ({equity_income / 1e9:.2f}B)")
    low = set(R["incoherent_ratings"])
    if synthetic_rating(out["coverage"], market_cap, out["state"])["rating"] in low \
            and operating_cash_flow and operating_cash_flow > 0 and depreciation is not None:
        cash = operating_cash_flow + ie - abs(depreciation)
        cov = cash / ie
        if synthetic_rating(cov, market_cap, state_fn(cov, cash))["rating"] not in low:
            out.update(coverage=cov, state=state_fn(cov, cash), basis="caja operativa",
                       reason=(f"rating de impago con la caja operativa positiva: incoherente; cobertura de caja "
                               f"(flujo operativo + intereses − D&A) / intereses = {cov:.2f}"))
    return out


def cost_of_debt(rf: float, market_cap: Optional[float], total_debt: Optional[float],
                 interest_coverage: Optional[float], coverage_state: Optional[str]) -> Optional[Dict[str, Any]]:
    """Kd = Rf + spread del rating sintético; None sin deuda (o sin capitalización para la tabla)."""
    if not market_cap or market_cap <= 0 or not (total_debt is not None and total_debt > 0):
        return None
    rt = synthetic_rating(interest_coverage, market_cap, coverage_state)
    return {"value": rf + rt["spread"], "rating": rt}


def equity_cost(beta: Optional[float], rf: float, kd: Optional[float] = None,
                preadjusted: bool = False, crp: float = 0.0) -> Dict[str, Any]:
    """F8 · E1: Ke = máx(CAPM + CRP, Rf + ke_floor_erp_multiple × ERP, Kd + ke_floor_over_kd). El accionista es
    residual: su coste no queda por debajo del de la deuda ni de medio mercado (Damodaran; la auditoría del 26-oct: AWK
    Ke 5,14 % < Kd 5,88 %). `floor` dice qué piso manda, si alguno. En la prueba de sensibilidad se suma KE_SHIFT.
    F9 · R1: `crp` es la prima de riesgo país ya ponderada y con su λ (lib/country_risk.py); los pisos van después,
    sobre el Ke con la prima. `capm` sigue siendo el CAPM sin ella."""
    C = cfg("valuation.capm")
    capm = cost_of_equity(beta, rf, preadjusted)
    base = capm + crp
    floors = [("Rf + {:g} × ERP".format(C["ke_floor_erp_multiple"]), rf + C["ke_floor_erp_multiple"] *
               C["market_risk_premium"])]
    if kd is not None:
        floors.append(("Kd + {:g} pp".format(C["ke_floor_over_kd"] * 100), kd + C["ke_floor_over_kd"]))
    name, top = max(floors, key=lambda f: f[1])
    value = max(base, top)
    shift = KE_SHIFT.get()
    return {"value": value + shift, "capm": capm, "crp": crp or None, "shift": shift or None,
            "floor": {"rule": name, "value": top, "capm": capm, "crp": crp or None} if top > base else None,
            "floors": {n: v for n, v in floors}}


def wacc(*, beta: Optional[float], rf: Dict[str, Any], market_cap: Optional[float],
         total_debt: Optional[float], interest_coverage: Optional[float],
         coverage_state: Optional[str], tax: Dict[str, Any], beta_preadjusted: bool = False,
         ke: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """WACC ponderado con todos sus componentes (lo mostrado es lo usado: `value`). `ke`: el de `equity_cost` del
    análisis (uno solo); sin él, se calcula aquí con los mismos pisos."""
    C, W = cfg("valuation.capm"), cfg("valuation.wacc")
    b = beta if beta is not None else C["default_beta"]
    pre = beta_preadjusted and beta is not None
    kd_info = cost_of_debt(rf["value"], market_cap, total_debt, interest_coverage, coverage_state)
    if ke is None:
        ke = equity_cost(b, rf["value"], kd_info and kd_info["value"], pre)
    out: Dict[str, Any] = {
        "value": None, "raw": None, "clamped": False, "bounds": [W["clamp_min"], W["clamp_max"]],
        "ke": ke["value"], "ke_capm": ke["capm"], "ke_crp": ke.get("crp"), "ke_floor": ke["floor"],
        "ke_shift": ke.get("shift"),
        "beta": adjusted_beta(b, pre), "beta_raw": None if pre else b,
        "beta_method": "beta de abajo hacia arriba (sin Blume)" if pre else "Blume",
        "beta_default": beta is None, "rf": rf["value"], "rf_source": rf["source"],
        "rf_fallback": rf["fallback"], "rf_reason": rf.get("reason"), "rf_as_of": rf.get("as_of"),
        "rf_market": rf.get("market"), "mrp": C["market_risk_premium"], "kd": None, "kd_after_tax": None, "rating": None,
        "tax_rate": tax["rate"], "tax_source": tax["source"], "tax_reason": tax.get("reason"),
        "equity": market_cap, "debt": total_debt, "weights": None, "reason": None,
    }
    if not market_cap or market_cap <= 0:
        out["reason"] = "sin capitalización bursátil: no hay pesos de mercado"
        return out
    d = total_debt if (total_debt is not None and total_debt > 0) else 0.0
    we, wd = market_cap / (market_cap + d), d / (market_cap + d)
    raw = we * ke["value"]
    if kd_info is not None:
        kd = kd_info["value"]
        out.update(rating=kd_info["rating"], kd=kd, kd_after_tax=kd * (1 - tax["rate"]))
        raw += wd * out["kd_after_tax"]
    value = min(W["clamp_max"], max(W["clamp_min"], raw))
    out.update(value=value, raw=raw, clamped=value != raw, weights={"equity": we, "debt": wd})
    return out
