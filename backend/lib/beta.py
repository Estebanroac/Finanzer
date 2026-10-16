"""
Beta y rango de 52 semanas desde la serie de precios (fase 2b, T6; F2_PRECEDENCIA §5; D5: de la serie solo entran en
el motor la beta y el rango).

BETA (la que entra en el Ke del WACC y en el de FINANCIAL):
  1. propia: 2 años semanales frente al S&P 500 (market_signals.beta, el método de la referencia de la 2a), con el
     cierre ajustado de lib/price_history; ajustada por Blume en el coste de capital, como hasta ahora;
  2. si R² < `market.beta_choice.min_r2` o hay menos de 52 semanas: la del SECTOR (config/betas.toml, Damodaran),
     que entra ya ajustada (sin Blume: es una media de industria, no una regresión de una empresa). Evita las betas
     casi nulas o negativas de utilities, REIT y energía (DUK −0.12, XOM −0.02);
  3. sin serie (la descarga falla): la de la fuente (Finnhub/Yahoo) con el aviso "beta de la fuente, sin verificar".
  Contraste: si |propia − fuente| > `discrepancy`, aviso "beta discrepante entre fuentes" (validate lo registra y la
  confianza lo cuenta).

RANGO DE 52 SEMANAS: máximo y mínimo diarios (sin ajustar por dividendos) de las sesiones del último año de la serie,
la de hoy incluida (la definición de Yahoo). Si la cotización queda fuera, la serie y el precio son de sesiones distintas: es un fallo de dato
y el rango queda sin dato con el motivo (no se ensancha con el precio: así era la protección 2, retirada).
"""
import re
from typing import Any, Dict, Optional

from market_signals import beta as _regression_beta   # D5: lo único de market_signals que entra en el motor
from settings import cfg

SOURCE_UNVERIFIED = "beta de la fuente, sin verificar"
DISCREPANT = "beta discrepante entre fuentes"


def _norm(s: Optional[str]) -> str:
    return re.sub(r"\s*[—–-]\s*", " - ", str(s or "")).strip().lower()


def own_beta(frame, market: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Beta propia con los cierres ajustados del título y del índice (lib/price_history)."""
    mframe = (market or {}).get("frame")
    return _regression_beta(frame["adj_close"] if frame is not None else None,
                            mframe["adj_close"] if mframe is not None else None, (market or {}).get("symbol"))


def sector_beta(sector: Optional[str], industry: Optional[str]) -> Optional[Dict[str, Any]]:
    """Beta del sector (config/betas.toml): la de la industria de Damodaran que corresponde a la de Yahoo o, si no
    está en la tabla, la media ponderada por número de empresas de las industrias de su sector."""
    B = cfg("betas")
    ind = B["yahoo_industries"].get(_norm(industry))
    if ind:
        firms, b = B["industries"][ind]
        return {"value": float(b), "basis": "industria", "damodaran": ind, "firms": int(firms),
                "source": B["source"], "url": B["url"]}
    group = B["yahoo_sectors"].get(str(sector or ""))
    if not group:
        return None
    rows = [B["industries"][g] for g in group]
    n = sum(r[0] for r in rows)
    return {"value": sum(r[0] * r[1] for r in rows) / n, "basis": "sector", "damodaran": list(group), "firms": n,
            "source": B["source"], "url": B["url"]}


def choose(own: Dict[str, Any], source_beta: Optional[float], source_name: Optional[str],
           sector: Optional[str], industry: Optional[str]) -> Dict[str, Any]:
    """{value, adjusted (True = ya ajustada, sin Blume), source, reason, own, source_beta, discrepancy, sector}."""
    C = cfg("market.beta_choice")
    out: Dict[str, Any] = {"value": None, "adjusted": False, "source": None, "reason": None,
                           "own": {k: own.get(k) for k in ("status", "raw", "adjusted", "r2", "observations",
                                                           "first_week", "last_week", "reason")},
                           "source_beta": source_beta, "source_name": source_name, "discrepancy": None}
    st = own.get("status")
    reliable = st == "ok" and (own.get("r2") or 0.0) >= C["min_r2"]
    if reliable:
        out.update(value=own["raw"], source="propia",
                   reason=(f"2 años semanales frente al S&P 500 ({own['observations']} semanas, R² "
                           f"{own['r2']:.2f}), ajustada por Blume"))
        if source_beta is not None and abs(own["raw"] - source_beta) > C["discrepancy"]:
            out["discrepancy"] = {"own": own["raw"], "source": source_beta, "source_name": source_name,
                                  "threshold": C["discrepancy"], "note": DISCREPANT}
        return out
    if st in ("ok", "historia_insuficiente"):
        sb = sector_beta(sector, industry)
        why = (f"R² {own['r2']:.2f} < {C['min_r2']:g}: la regresión no explica el título" if st == "ok"
               else f"historia insuficiente ({own.get('reason')})")
        if sb is not None:
            out.update(value=sb["value"], adjusted=True, source="sector", sector=sb,
                       reason=(f"beta propia no fiable ({why}); beta del sector "
                               f"({sb['damodaran'] if sb['basis'] == 'industria' else 'sector ' + str(sector)}, "
                               f"{sb['source']}), sin Blume"))
            return out
        out["reason"] = f"beta propia no fiable ({why}) y sin beta del sector para {sector!r}/{industry!r}"
    if source_beta is not None:
        out.update(value=source_beta, source="fuente",
                   reason=f"{SOURCE_UNVERIFIED} ({source_name or 'proveedor'}): sin serie de precios para la propia "
                          f"({own.get('reason') or st})")
        return out
    out.update(source="sin_dato", reason=f"sin beta propia ({own.get('reason') or st}) ni de la fuente")
    return out


def range_52w(frame, price: Optional[float]) -> Dict[str, Any]:
    """Máximo y mínimo diarios de las sesiones de los últimos `range52_window_days` días (la de hoy incluida; el mismo
    día de hace un año, no), con su fecha."""
    import pandas as pd
    days = cfg("market.beta_choice.range52_window_days")
    if frame is None or len(frame) == 0:
        return {"status": "sin_dato", "reason": "sin serie de precios", "high": None, "low": None}
    last = frame.index[-1]
    if frame.index[0] > last - pd.Timedelta(days=days):
        return {"status": "sin_dato", "reason": f"la serie empieza el {frame.index[0].date()}: no cubre 52 semanas",
                "high": None, "low": None}
    w = frame[frame.index > last - pd.Timedelta(days=days)]
    hi_col = w["high"].where(w["high"].notna(), w["close"])
    lo_col = w["low"].where(w["low"].notna(), w["close"])
    hi, lo = float(hi_col.max()), float(lo_col.min())
    out = {"status": "ok", "reason": None, "high": hi, "low": lo, "high_date": str(hi_col.idxmax().date()),
           "low_date": str(lo_col.idxmin().date()), "first_session": str(w.index[0].date()),
           "last_session": str(w.index[-1].date()), "sessions": len(w)}
    if price is not None and not (lo <= price <= hi):
        out.update(status="sin_dato", high=None, low=None,
                   reason=(f"la cotización {price:.2f} queda fuera del rango de la serie [{lo:.2f}, {hi:.2f}] a "
                           f"{out['last_session']}: precio y serie de sesiones distintas"))
    return out
