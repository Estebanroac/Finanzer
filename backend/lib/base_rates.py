"""
Tasas base del crecimiento de las ventas (fase 3, T3; F3_DISENO §8.1): la referencia principal del DCF inverso.

"¿Qué proporción de empresas comparables sostuvo ese crecimiento 10 años?" Fuente: Mauboussin y Callahan (2021),
Exhibit 3 (config/base_rates.toml): mediana, media y desviación típica del CAGR de ventas por tramo de tamaño (ventas
del año inicial en dólares de 2020) y por industria (las cinco de Fama y French).

Decisiones (declaradas, F3_T3 en la bitácora):
  · **Distribución:** los autores advierten que no es normal (cola a la derecha). Se ajusta una LOGNORMAL a
    1 + CAGR con la mediana y la desviación típica de la celda: ln(1 + g) ~ N(ln(1 + mediana), s), con s tal que la
    desviación típica de 1 + g sea la publicada. Respeta la asimetría y no da probabilidades a crecimientos < −100%.
  · **Celda:** la de su tramo e industria; con menos de `min_count` observaciones a ese horizonte, la fila "All" del
    tramo (en las más grandes, el tamaño pesa más que la industria: 100+ Healthcare tiene 7 observaciones a 10 años).
  · **Tamaño:** las ventas en dólares de hoy se llevan a dólares de 2020 con el IPC (config `size.deflator_to_2020`).
  · **Industria:** del sector de Yahoo a Fama y French 5 (config `industry_map`); sin sector, "All".
"""
import math
from typing import Any, Dict, Optional

from settings import cfg


def industry_for(sector: Optional[str]) -> str:
    return cfg("base_rates.industry_map").get((sector or "").strip().lower(), "All")


def size_bin(revenue_usd: Optional[float]) -> Optional[str]:
    """Tramo de tamaño por las ventas (USD de hoy, deflactadas a 2020)."""
    if revenue_usd is None or revenue_usd <= 0:
        return None
    rev2020 = revenue_usd * cfg("base_rates.size.deflator_to_2020") / 1e9
    bins = sorted(cfg("base_rates.bins").items(), key=lambda kv: kv[1])
    out = None
    for name, lo in bins:
        if rev2020 >= lo:
            out = name
    return out


def _lognormal_sigma(median: float, std: float) -> Optional[float]:
    """s de ln(1 + g) ~ N(ln(1 + mediana), s) con desviación típica de 1 + g igual a `std`:
    Var(X) = (e^{s²} − 1) e^{s²} m², con m = 1 + mediana; x = e^{s²} resuelve x² − x − (std/m)² = 0."""
    m = 1.0 + median
    if m <= 0 or std is None or std <= 0:
        return None
    k = (std / m) ** 2
    x = (1.0 + math.sqrt(1.0 + 4.0 * k)) / 2.0
    return math.sqrt(math.log(x))


def _norm_sf(z: float) -> float:
    return 0.5 * math.erfc(z / math.sqrt(2.0))


def share_sustaining(g: Optional[float], revenue_usd: Optional[float], sector: Optional[str],
                     horizon_years: int = 10) -> Dict[str, Any]:
    """Proporción de comparables (tramo × industria) cuyo CAGR de ventas a `horizon_years` fue ≥ g."""
    out = {"share": None, "bin": None, "industry": industry_for(sector), "cell": None, "median": None, "std": None,
           "count": None, "horizon_years": horizon_years, "reason": None, "revenue_usd": revenue_usd}
    if g is None:
        return dict(out, reason="sin crecimiento exigido")
    b = size_bin(revenue_usd)
    if b is None:
        return dict(out, reason="sin ventas en USD para el tramo de tamaño (sin tipo de cambio)")
    T = cfg("base_rates.table")
    try:
        h = cfg("base_rates.horizons_years").index(horizon_years)
    except ValueError:
        return dict(out, bin=b, reason=f"horizonte de {horizon_years} años sin tasa base")
    ind = out["industry"]
    row = T[b].get(ind)
    if row is None or row["count"][h] < cfg("base_rates.min_count"):
        ind = "All"
        row = T[b]["All"]
    s = _lognormal_sigma(row["median"][h], row["std"][h])
    out.update(bin=b, cell=f"{b} · {ind}", median=row["median"][h], std=row["std"][h], count=row["count"][h])
    if s is None or 1.0 + g <= 0:
        return dict(out, share=1.0 if 1.0 + g <= 0 else None,
                    reason=None if 1.0 + g <= 0 else "celda sin dispersión")
    z = (math.log(1.0 + g) - math.log(1.0 + row["median"][h])) / s
    out["share"] = _norm_sf(z)
    return out
