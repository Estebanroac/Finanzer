"""
F8 · E4 (auditoría externa del 26-oct-2026, VZ): el FCF de una telecom excluye las compras de licencias de espectro,
que van en actividades de inversión y no en el capex. Son una inversión recurrente del negocio, pero muy irregular (VZ:
47,6 mil millones de USD en 2021 por la banda C y 0,45 en 2025), así que se resta su media del ciclo de subastas:

    FCF ajustado = FCF − media de las compras de espectro de los `years` últimos ejercicios

Ventana (decisión del PM del 27-oct, desviación razonada de la auditoría, que pedía 5 años): 10 ejercicios, el ciclo
completo de subastas (AWS-3 2015, mmWave 2019-20, banda C 2021, 3,45 GHz 2022). Con 5, una sola subasta (la banda C)
dominaba la media y sobrestimaba el gasto recurrente. Si EDGAR trae menos de 10 ejercicios con el dato, se promedian
los que haya con un mínimo de `min_years`; por debajo, «sin dato» declarado. No se suponen ceros ni se estima.
Parámetros en config/valuation.toml [telecom_spectrum].
"""
from typing import Any, Dict, List, Optional

from settings import cfg


def adjustment(history_fy: Optional[Dict[str, Any]], industry: Optional[str]) -> Optional[Dict[str, Any]]:
    """None si la empresa no es una telecom; si lo es, {status: "ok", average, years, values, concept} o
    {status: "sin_dato", reason}."""
    C = cfg("valuation.telecom_spectrum")
    if industry not in C["industries"]:
        return None
    n, need = C["years"], C["min_years"]
    hist = history_fy or {}
    fy_ends: List[str] = [v["fy_end"] for v in (hist.get("revenue") or {}).get("values") or []][:n]
    spec = {v["fy_end"]: v for v in (hist.get("spectrum_purchases") or {}).get("values") or []}
    have = [e for e in fy_ends if e in spec]
    if len(have) < need:
        return {"status": "sin_dato",
                "reason": (f"EDGAR trae las compras de espectro de {len(have)} de los {len(fy_ends)} últimos ejercicios "
                           f"y hacen falta al menos {need}: sin la media no se ajusta el FCF")}
    vals = [spec[e]["value"] for e in have]
    return {"status": "ok", "average": sum(vals) / len(vals), "years": [e[:4] for e in have], "values": vals,
            "window": n, "concept": spec[have[0]]["concept"]}
