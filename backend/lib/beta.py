"""
Beta y rango de 52 semanas desde la serie de precios (fase 2b, T6; F2_PRECEDENCIA §5; D5: de la serie solo entran en
el motor la beta y el rango).

BETA (la que entra en el Ke del WACC y en el de FINANCIAL). F8 · E1 (auditoría externa del 26-oct-2026), una sola regla
visible:
  1. propia: 2 años semanales frente al S&P 500 (market_signals.beta), SOLO si pasa los tres filtros de
     `market.beta_choice` (R² ≥ min_r2, error estándar ≤ max_se y beta bruta dentro de own_range); ajustada por Blume
     en el coste de capital, como hasta ahora;
  2. si no los pasa (o no hay serie): la de ABAJO HACIA ARRIBA. Beta desapalancada de la industria de Damodaran
     (config/betas.toml [unlevered], corregida por caja), reapalancada con la D/E de mercado de la empresa y su tasa
     (`relever`, en el análisis, donde están la deuda, la capitalización y la t): βL = βU × [1 + (1 − t) × D/E]. Entra
     ya ajustada (sin Blume: no es la regresión de una empresa). Las financieras no se reapalancan (la deuda es su
     materia prima): la beta media de su industria ([industries]). Antes: la beta media de la industria sin
     reapalancar, y solo si R² < 0,10; una propia de −0,44 con R² 0,11 (AWK) entraba y dejaba el Ke por debajo del Kd;
  3. sin industria en la tabla: la de la fuente (Finnhub/Yahoo) con el aviso "beta de la fuente, sin verificar".
  Contraste: si |propia − fuente| > `discrepancy`, aviso "beta discrepante entre fuentes" (validate lo registra y la
  confianza lo cuenta).

RANGO DE 52 SEMANAS: máximo y mínimo diarios (sin ajustar por dividendos) de las sesiones del último año de la serie,
la de hoy incluida (la definición de Yahoo). Si la cotización queda fuera, la serie y el precio son de sesiones distintas: es un fallo de dato
y el rango queda sin dato con el motivo (no se ensancha con el precio: así era la protección 2, retirada).
"""
import re
from typing import Any, Dict, List, Optional

from market_signals import beta as _regression_beta   # D5: lo único de market_signals que entra en el motor
from settings import cfg

SOURCE_UNVERIFIED = "beta de la fuente, sin verificar"
DISCREPANT = "beta discrepante entre fuentes"


def _norm(s: Optional[str]) -> str:
    """Industria de Yahoo en la forma de las claves de config: la raya o el guion ENTRE ESPACIOS separa ("Banks—Regional",
    "Banks - Regional" -> "banks - regional"); el guion dentro de una palabra se queda ("Non-Alcoholic"). Antes de la
    fase 4/7 también se partía y "Beverages—Non-Alcoholic" (KO) no casaba con el mapa."""
    return re.sub(r"\s*[—–]\s*|\s+-\s+", " - ", str(s or "")).strip().lower()


def own_beta(frame, market: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Beta propia con los cierres ajustados del título y del índice (lib/price_history)."""
    mframe = (market or {}).get("frame")
    return _regression_beta(frame["adj_close"] if frame is not None else None,
                            mframe["adj_close"] if mframe is not None else None, (market or {}).get("symbol"))


def _lookup(table: str, sector: Optional[str], industry: Optional[str],
            region: str = "us") -> Optional[Dict[str, Any]]:
    """Fila de la industria de Damodaran que corresponde a la de Yahoo o, si no está en el mapa, la media ponderada por
    número de empresas de las industrias de su sector. `table`: "industries" ([empresas, beta]) o "unlevered"
    ([empresas, βU corregida por caja, D/E, t]). F9 · R2b: `region` «europe» o «emerging» lee la tabla de esa región
    (config/betas_regional.toml); «us», la de EE. UU. (betas.toml)."""
    B = cfg("betas")
    rows_of = B[table] if region == "us" else cfg("betas_regional")[region][table]
    ind = B["yahoo_industries"].get(_norm(industry))
    if ind and ind in rows_of:
        row = rows_of[ind]
        return {"value": float(row[1]), "basis": "industria", "damodaran": ind, "firms": int(row[0]), "row": list(row)}
    group = B["yahoo_sectors"].get(str(sector or ""))
    if not group:
        return None
    rows = [rows_of[g] for g in group if g in rows_of]
    n = sum(r[0] for r in rows)
    if not n:
        return None
    return {"value": sum(r[0] * r[1] for r in rows) / n, "basis": "sector", "damodaran": list(group), "firms": n,
            "row": None}


def _regional_source(region: str, column: str) -> Dict[str, str]:
    R = cfg("betas_regional")[region]
    return {"source": f"{R['source']} (columna {column})", "url": R["url"], "region": region}


def sector_beta(sector: Optional[str], industry: Optional[str], region: str = "us") -> Optional[Dict[str, Any]]:
    """Beta media (apalancada) de la industria de Damodaran (config/betas.toml [industries], o la de su región,
    F9 · R2b): la de las financieras."""
    r = _lookup("industries", sector, industry, region)
    if r is None:
        return None
    r.pop("row")
    B = cfg("betas")
    src = {"source": B["source"], "url": B["url"], "region": "us"} if region == "us" else _regional_source(region,
                                                                                                          "Beta")
    return {**r, **src}


def unlevered_beta(sector: Optional[str], industry: Optional[str], region: str = "us") -> Optional[Dict[str, Any]]:
    """βU corregida por caja de la industria de Damodaran (config/betas.toml [unlevered], o la de su región, F9 ·
    R2b)."""
    r = _lookup("unlevered", sector, industry, region)
    if r is None:
        return None
    row = r.pop("row")
    B = cfg("betas")
    src = ({"source": B["unlevered_source"], "url": B["url"], "region": "us"} if region == "us"
           else _regional_source(region, "Unlevered beta corrected for cash"))
    return {**r, "industry_de": row[2] if row else None, "industry_tax": row[3] if row else None, **src}


REGION_LABEL = {"us": "EE. UU.", "europe": "Europa", "emerging": "mercados emergentes"}


def regionalize(choice: Dict[str, Any], region: Dict[str, Any], sector: Optional[str],
                industry: Optional[str]) -> Dict[str, Any]:
    """F9 · R2b (decisión del PM del 27-oct): con la beta de abajo hacia arriba, la industria de la tabla de Damodaran
    de la región donde opera la empresa (`region` de country_risk.beta_region). Sin la industria en esa tabla, la de
    EE. UU., declarado. La propia y la de la fuente no cambian. Va antes de `relever`."""
    reg = (region or {}).get("region", "us")
    if choice.get("source") != "sector" or not choice.get("bottom_up") or reg == "us":
        return choice
    bu, lev = unlevered_beta(sector, industry, reg), sector_beta(sector, industry, reg)
    out = dict(choice)
    if bu is None or lev is None:
        out["region"] = {"region": "us", "reason": f"sin la industria en la tabla de {REGION_LABEL[reg]}: la de EE. UU."}
        return out
    out.update(value=lev["value"], sector=lev, bottom_up=bu, region={**region},
               reason=choice["reason"].replace("(Damodaran, enero de 2026)",
                                               f"(Damodaran, tabla de {REGION_LABEL[reg]}, enero de 2026: "
                                               f"{region['reason']})"))
    return out


def own_filters(own: Dict[str, Any]) -> List[str]:
    """Filtros de la beta propia que NO pasa (lista vacía: es utilizable). F8 · E1."""
    C = cfg("market.beta_choice")
    if own.get("status") != "ok":
        return [f"sin regresión ({own.get('reason') or own.get('status')})"]
    out = []
    raw, r2, se = own.get("raw"), own.get("r2"), own.get("se")
    lo, hi = C["own_range"]
    if r2 is None or r2 < C["min_r2"]:
        out.append(f"R² {r2:.2f} < {C['min_r2']:.2f}: la regresión no explica el título" if r2 is not None
                   else "sin R²")
    if se is None or se > C["max_se"]:
        out.append(f"error estándar {se:.2f} > {C['max_se']:.2f}" if se is not None else "sin error estándar")
    if raw is None or not lo <= raw <= hi:
        out.append(f"beta {raw:.2f} fuera de [{lo:g}; {hi:g}]" if raw is not None else "sin beta")
    return out


def choose(own: Dict[str, Any], source_beta: Optional[float], source_name: Optional[str],
           sector: Optional[str], industry: Optional[str]) -> Dict[str, Any]:
    """{value, adjusted (True = ya ajustada, sin Blume), source, reason, own, source_beta, discrepancy, sector,
    bottom_up}. Con la de abajo hacia arriba, `value` es provisional (la media apalancada de la industria) hasta que
    `relever` la reapalanca con la estructura de capital de la empresa."""
    C = cfg("market.beta_choice")
    out: Dict[str, Any] = {"value": None, "adjusted": False, "source": None, "reason": None,
                           "own": {k: own.get(k) for k in ("status", "raw", "adjusted", "r2", "se", "observations",
                                                           "first_week", "last_week", "reason")},
                           "source_beta": source_beta, "source_name": source_name, "discrepancy": None,
                           "rule": ("propia si pasa los filtros (R² ≥ {:.2f}, error estándar ≤ {:.2f}, beta entre "
                                    "{:g} y {:g}); si no, la de abajo hacia arriba de su industria (Damodaran)"
                                    ).format(C["min_r2"], C["max_se"], *C["own_range"])}
    fails = own_filters(own)
    out["own"]["fails"] = fails
    if not fails:
        out.update(value=own["raw"], source="propia",
                   reason=(f"2 años semanales frente al S&P 500 ({own['observations']} semanas, R² "
                           f"{own['r2']:.2f}, error estándar {own['se']:.2f}), ajustada por Blume"))
        if source_beta is not None and abs(own["raw"] - source_beta) > C["discrepancy"]:
            out["discrepancy"] = {"own": own["raw"], "source": source_beta, "source_name": source_name,
                                  "threshold": C["discrepancy"], "note": DISCREPANT}
        return out
    why = "; ".join(fails)
    bu, lev = unlevered_beta(sector, industry), sector_beta(sector, industry)
    if bu is not None and lev is not None:
        out.update(value=lev["value"], adjusted=True, source="sector", sector=lev, bottom_up=bu,
                   discarded=why if own.get("status") == "ok" else None,
                   reason=(f"beta propia descartada ({why}); de abajo hacia arriba: industria "
                           f"{bu['damodaran'] if bu['basis'] == 'industria' else 'sector ' + str(sector)} "
                           f"(Damodaran, enero de 2026)"))
        return out
    if source_beta is not None:
        out.update(value=source_beta, source="fuente",
                   reason=f"{SOURCE_UNVERIFIED} ({source_name or 'proveedor'}): beta propia descartada ({why}) y "
                          f"sin industria de Damodaran para {sector!r}/{industry!r}")
        return out
    out.update(source="sin_dato", reason=f"beta propia descartada ({why}), sin industria de Damodaran ni beta de la "
                                         "fuente")
    return out


def contrast(source: Optional[str], used: Optional[float], own: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """F11 · T5 (revisión de NU y NFLX): la beta sustituta (de su industria o de la fuente) frente a la propia que se
    descartó. Solo si la regresión propia explica algo (R² ≥ `contrast_min_r2`; con R² ≈ 0, KO o HSY, no hay nada que
    contrastar). Fuera del intervalo propia ± `contrast_k_se` errores estándar: {used, own, se, r2, low, high}; si no,
    None. No cambia la beta (la ponderación propia/industria es del modelo general); se declara y baja la confianza.
    NU: industria 0,60 frente a la propia 1,32 ± 2 · 0,28."""
    C = cfg("market.beta_choice")
    o = own or {}
    raw, se, r2 = o.get("raw"), o.get("se"), o.get("r2")
    if source == "propia" or used is None or raw is None or se is None or r2 is None or r2 < C["contrast_min_r2"]:
        return None
    lo, hi = raw - C["contrast_k_se"] * se, raw + C["contrast_k_se"] * se
    if lo <= used <= hi:
        return None
    return {"used": used, "own": raw, "se": se, "r2": r2, "low": lo, "high": hi}


def relever(choice: Dict[str, Any], debt: Optional[float], equity: Optional[float], tax: Optional[float],
            financial: bool) -> Dict[str, Any]:
    """F8 · E1: beta de abajo hacia arriba de la empresa, βL = βU × [1 + (1 − t) × D/E] con la D/E de mercado (deuda
    financiera / capitalización). Financiera: la media apalancada de su industria, sin reapalancar. Sin capitalización:
    la D/E media de la industria (declarado). Devuelve la elección con `value` y `reason` finales; las demás fuentes,
    tal cual."""
    if choice.get("source") != "sector" or not choice.get("bottom_up"):
        return choice
    out, bu = dict(choice), choice["bottom_up"]
    head = choice["reason"]
    if financial:
        lev = choice["sector"]
        out.update(value=lev["value"], relevered=None,
                   reason=(f"{head}: financiera, beta media de la industria ({lev['value']:.2f}), sin reapalancar (su "
                           "deuda es materia prima, no estructura de capital)"))
        return out
    t = tax if tax is not None else bu.get("industry_tax")
    if equity and equity > 0:
        de, de_basis = max(debt or 0.0, 0.0) / equity, "de mercado de la empresa"
    else:
        de, de_basis = bu.get("industry_de"), "media de la industria (sin capitalización de la empresa)"
    ind_de, k = bu.get("industry_de"), cfg("market.beta_choice.relever_max_de_ratio")
    if de is not None and ind_de and de > k * ind_de:
        lev = choice["sector"]
        out.update(value=lev["value"], relevered=None, not_comparable={"de": de, "industry_de": ind_de, "ratio": k},
                   reason=(f"{head}: D/E {de:.2f}, más de {k:g} veces la de su industria ({ind_de:.2f}); estructura de "
                           f"capital no comparable (p. ej., deuda de una financiera cautiva): beta media de la industria "
                           f"({lev['value']:.2f}), sin reapalancar"))
        return out
    if de is None or t is None:
        out.update(value=bu["value"], relevered=None,
                   reason=f"{head}: βU {bu['value']:.2f} sin reapalancar (sin D/E ni tasa)")
        return out
    val = bu["value"] * (1 + (1 - t) * de)
    out.update(value=val, relevered={"unlevered": bu["value"], "de": de, "de_basis": de_basis, "tax": t},
               reason=(f"{head}: βU {bu['value']:.2f} reapalancada con D/E {de_basis} {de:.2f} y t {t:.0%} → "
                       f"{val:.2f}"))
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
