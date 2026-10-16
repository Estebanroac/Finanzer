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
      Damodaran (config, con fuente y fecha).
  Kd  Rf + spread del rating sintético por cobertura de intereses (tabla de
      Damodaran, grandes y pequeñas por capitalización). Regla M: cobertura no
      significativa (EBIT < 0 con caja neta) -> tramo de caja neta; EBIT < 0 con
      deuda neta -> peor tramo. Ambos casos se marcan.
  t   tasa efectiva = provisión de impuestos / beneficio antes de impuestos,
      acotada; con BAI <= 0 o sin dato, el tipo legal. La misma t entra en el
      NOPAT del ROIC.
  Rf  rendimiento del Tesoro a 10 años (^TNX) con caché de 24 h; si no hay
      lectura válida, el valor de config, marcado.

El WACC se acota a un ÚNICO rango (valuation.wacc.clamp_min/max). FINANCIAL no
usa WACC (se valora por P/B justificado con Ke); REIT tiene WACC (spread) pero
no DCF.
"""
import datetime as _dt
import time
from typing import Any, Dict, Optional

from settings import cfg

_RF_CACHE: Dict[str, Any] = {}


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
            "reason": f"{C['risk_free_ticker']} no disponible ({why}): valor de config"}


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


def wacc(*, beta: Optional[float], rf: Dict[str, Any], market_cap: Optional[float],
         total_debt: Optional[float], interest_coverage: Optional[float],
         coverage_state: Optional[str], tax: Dict[str, Any], beta_preadjusted: bool = False) -> Dict[str, Any]:
    """WACC ponderado con todos sus componentes (lo mostrado es lo usado: `value`)."""
    C, W = cfg("valuation.capm"), cfg("valuation.wacc")
    b = beta if beta is not None else C["default_beta"]
    pre = beta_preadjusted and beta is not None
    ke = cost_of_equity(b, rf["value"], pre)
    out: Dict[str, Any] = {
        "value": None, "raw": None, "clamped": False, "bounds": [W["clamp_min"], W["clamp_max"]],
        "ke": ke, "beta": adjusted_beta(b, pre), "beta_raw": None if pre else b,
        "beta_method": "beta del sector (sin Blume)" if pre else "Blume",
        "beta_default": beta is None, "rf": rf["value"], "rf_source": rf["source"],
        "rf_fallback": rf["fallback"], "rf_reason": rf.get("reason"), "rf_as_of": rf.get("as_of"),
        "mrp": C["market_risk_premium"], "kd": None, "kd_after_tax": None, "rating": None,
        "tax_rate": tax["rate"], "tax_source": tax["source"], "tax_reason": tax.get("reason"),
        "equity": market_cap, "debt": total_debt, "weights": None, "reason": None,
    }
    if not market_cap or market_cap <= 0:
        out["reason"] = "sin capitalización bursátil: no hay pesos de mercado"
        return out
    d = total_debt if (total_debt is not None and total_debt > 0) else 0.0
    we, wd = market_cap / (market_cap + d), d / (market_cap + d)
    raw = we * ke
    if d > 0:
        rt = synthetic_rating(interest_coverage, market_cap, coverage_state)
        kd = rf["value"] + rt["spread"]
        out.update(rating=rt, kd=kd, kd_after_tax=kd * (1 - tax["rate"]))
        raw += wd * out["kd_after_tax"]
    value = min(W["clamp_max"], max(W["clamp_min"], raw))
    out.update(value=value, raw=raw, clamped=value != raw, weights={"equity": we, "debt": wd})
    return out
