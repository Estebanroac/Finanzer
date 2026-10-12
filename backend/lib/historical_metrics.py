"""
Métricas contextuales a partir de series anuales (CAGR de ingresos y años con
FCF negativo).

Extraído en la etapa 4 de data_fetcher.get_complete_analysis_data, donde nunca
se ejecutaba: la tarea "historical" que lo alimentaba se había quitado del
camino crítico, así que `historical` era siempre None. Se conserva aislado
porque la etapa 6 lo necesitará. Desde la etapa 5, fcf_cagr alimenta el
componente "Crecimiento del FCF" del score (main.py).

Corrección respecto al original: el CAGR a 3 años tomaba como inicio el valor
MÁS ANTIGUO de la serie (revenues[-1]) aunque hubiera más de 4 ejercicios, lo
que con 5 años calculaba (r0/r4)^(1/3). Aquí el inicio es revenues[periods].
Como el original nunca corría, el cambio no afecta a ninguna salida.
"""
from typing import Any, Dict, List, Optional, Tuple


def cagr(end_val: Optional[float], start_val: Optional[float], periods: int) -> Optional[float]:
    """(final / inicial)^(1/n) − 1; None si algún valor no es positivo o n <= 0."""
    try:
        if end_val and start_val and end_val > 0 and start_val > 0 and periods > 0:
            return (end_val / start_val) ** (1 / periods) - 1
    except (TypeError, ValueError, ZeroDivisionError):
        pass
    return None


def series_cagr(values_newest_first: List[Optional[float]], years: int) -> Optional[float]:
    """CAGR de una serie anual ordenada de la más reciente a la más antigua
    (como la devuelve yfinance). Usa tantos periodos como haya, hasta `years`."""
    if not values_newest_first or len(values_newest_first) < 2:
        return None
    periods = min(years, len(values_newest_first) - 1)
    return cagr(values_newest_first[0], values_newest_first[periods], periods)


def contextual_from_history(historical: Dict[str, Any]) -> Dict[str, Any]:
    """Métricas contextuales con las mismas claves que usaba data_fetcher:
    revenue_cagr_3y (≥3 ejercicios), revenue_cagr_5y (≥5) y
    fcf_trend_negative_years."""
    out: Dict[str, Any] = {}
    revenues = (historical or {}).get("revenue") or []
    if len(revenues) >= 3:
        out["revenue_cagr_3y"] = series_cagr(revenues, 3)
        if len(revenues) >= 5:
            out["revenue_cagr_5y"] = series_cagr(revenues, 5)
    fcf_list = (historical or {}).get("fcf")
    if fcf_list:
        out["fcf_trend_negative_years"] = sum(1 for x in fcf_list if x and x < 0)
    return out


def fcf_cagr(values_newest_first: List[Optional[float]], years: int = 3) -> Tuple[Optional[float], Optional[str]]:
    """CAGR del FCF sobre `years` intervalos (years + 1 ejercicios anuales).

    Devuelve (cagr, None) o (None, motivo). El CAGR no está definido —y se
    devuelve "sin dato", nunca un número— si faltan ejercicios, si el FCF
    inicial es <= 0 o si el FCF cambia de signo dentro del periodo."""
    vals = list(values_newest_first or [])[:years + 1]
    if len(vals) < years + 1 or any(v is None for v in vals):
        return None, f"menos de {years + 1} ejercicios anuales de FCF"
    start, end = vals[years], vals[0]
    if start <= 0:
        return None, "FCF inicial <= 0: CAGR no definido"
    if any(v <= 0 for v in vals):
        return None, "el FCF cambia de signo en el periodo: CAGR no definido"
    return cagr(end, start, years), None


# ═══════════════════════════ etapa 6: series anuales ═══════════════════════════
# Todas reciben series de la más reciente a la más antigua (como _statements_fy)
# y tratan None como "sin dato": nunca lo convierten en cero.

def strict_cagr(values_newest_first: List[Optional[float]], years: int = 3) -> Tuple[Optional[float], Optional[str]]:
    """CAGR real sobre exactamente `years` intervalos (years + 1 ejercicios).
    (cagr, None) o (None, motivo); no usa menos periodos ni el proxy interanual."""
    vals = list(values_newest_first or [])[:years + 1]
    if len(vals) < years + 1 or vals[0] is None or vals[years] is None:
        return None, f"menos de {years + 1} ejercicios anuales"
    if vals[years] <= 0 or vals[0] <= 0:
        return None, "valor inicial o final <= 0: CAGR no definido"
    return cagr(vals[0], vals[years], years), None


def paired(a: List[Optional[float]], b: List[Optional[float]]) -> List[Tuple[float, float]]:
    """Pares (a_i, b_i) del mismo ejercicio con ambos datos presentes."""
    return [(x, y) for x, y in zip(a or [], b or []) if x is not None and y is not None]


def ratio_series(num: List[Optional[float]], den: List[Optional[float]]) -> List[Optional[float]]:
    """num/den por ejercicio; None si falta alguno o den <= 0."""
    out = []
    for x, y in zip(num or [], den or []):
        out.append(x / y if (x is not None and y is not None and y > 0) else None)
    return out


def yoy_growths(values_newest_first: List[Optional[float]]) -> List[Optional[float]]:
    """Crecimientos interanuales (más reciente primero); None si falta o base <= 0."""
    v = list(values_newest_first or [])
    out = []
    for i in range(len(v) - 1):
        a, b = v[i], v[i + 1]
        out.append((a / b - 1) if (a is not None and b is not None and b > 0) else None)
    return out


def present(values: List[Optional[float]]) -> List[float]:
    return [x for x in (values or []) if x is not None]


def mean(values: List[Optional[float]]) -> Optional[float]:
    v = present(values)
    return sum(v) / len(v) if v else None


def stdev(values: List[Optional[float]]) -> Optional[float]:
    """Desviación típica muestral; None con menos de 2 datos."""
    v = present(values)
    if len(v) < 2:
        return None
    m = sum(v) / len(v)
    return (sum((x - m) ** 2 for x in v) / (len(v) - 1)) ** 0.5


def detrended_std(values: List[Optional[float]]) -> Optional[float]:
    """Desviación de la serie alrededor de su tendencia lineal (MCO sobre el
    índice temporal). Separa la oscilación (ciclo) de una mejora o un deterioro
    sostenidos. None con menos de 3 datos consecutivos."""
    v = list(values or [])
    if len(v) < 3 or any(x is None for x in v):
        return None
    n = len(v)
    xs = list(range(n))
    mx, my = sum(xs) / n, sum(v) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, v)) / sxx
    resid = [y - (my + slope * (x - mx)) for x, y in zip(xs, v)]
    return (sum(r * r for r in resid) / (n - 2)) ** 0.5
