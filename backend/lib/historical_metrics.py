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
    inicial es <= 0 o si el FCF cambia de signo dentro del periodo. Con año
    base anómalo (etapa 7) usa la regresión log-lineal (growth_rate)."""
    r = growth_rate(values_newest_first, years, what="FCF")
    return r["value"], r["reason"]


# ═══════════════════════════ etapa 6: series anuales ═══════════════════════════
# Todas reciben series de la más reciente a la más antigua (como _statements_fy)
# y tratan None como "sin dato": nunca lo convierten en cero.

def strict_cagr(values_newest_first: List[Optional[float]], years: int = 3) -> Tuple[Optional[float], Optional[str]]:
    """CAGR real sobre exactamente `years` intervalos (years + 1 ejercicios).
    (cagr, None) o (None, motivo); no usa menos periodos ni el proxy interanual.
    Con año base anómalo (etapa 7) usa la regresión log-lineal (growth_rate)."""
    r = growth_rate(values_newest_first, years, strict_ends_only=True)
    return r["value"], r["reason"]


def loglinear_growth(values_newest_first: List[Optional[float]]) -> Tuple[Optional[float], Optional[str], int]:
    """Crecimiento anual por regresión log-lineal (MCO de ln(valor) sobre el año)
    con todos los ejercicios disponibles. Solo series positivas: con algún valor
    <= 0, sin dato con motivo. (crecimiento, motivo, ejercicios usados)."""
    pts = [(i, v) for i, v in enumerate(reversed(list(values_newest_first or []))) if v is not None]
    if len(pts) < 3:
        return None, "menos de 3 ejercicios para la regresión log-lineal", len(pts)
    if any(v <= 0 for _, v in pts):
        return None, "serie con valores <= 0: la regresión log-lineal no está definida", len(pts)
    import math
    xs, ys = [p[0] for p in pts], [math.log(p[1]) for p in pts]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    return math.exp(slope) - 1, None, len(pts)


# Etapa 9a (regla general): un valor negativo en TODOS los ejercicios de la ventana impide
# calcular una tasa, pero no es "sin dato": es una señal y puntúa en el peor tramo.
SUSTAINED_NEGATIVE = "negativo en todos los ejercicios de la ventana"


def is_sustained_negative(reason: Optional[str]) -> bool:
    return bool(reason) and reason.startswith(SUSTAINED_NEGATIVE)


def growth_rate(values_newest_first: List[Optional[float]], years: int = 3, *, what: str = "valor",
                strict_ends_only: bool = False) -> Dict[str, Any]:
    """Crecimiento anual de una serie (etapa 7): CAGR de punta a punta, salvo con
    AÑO BASE ANÓMALO —el valor inicial es menor que anomalous_base_ratio × la
    mediana de los demás años de la ventana—, en cuyo caso usa la regresión
    log-lineal sobre todos los años disponibles y se marca "base anómala".

    {value, reason, method: "cagr"|"log_lineal", anomalous_base, years_used}.
    strict_ends_only: solo exige positivos el inicio y el final (CAGR de ingresos
    y similares); si no, cualquier valor <= 0 en la ventana deja el CAGR sin dato
    (FCF: cambio de signo)."""
    from settings import cfg
    vals = list(values_newest_first or [])[:years + 1]
    out = {"value": None, "reason": None, "method": "cagr", "anomalous_base": False, "years_used": years + 1}
    if len(vals) < years + 1 or vals[0] is None or vals[years] is None or \
            (not strict_ends_only and any(v is None for v in vals)):
        out["reason"] = (f"menos de {years + 1} ejercicios anuales" + (f" de {what}" if what != "valor" else ""))
        return out
    start, end = vals[years], vals[0]
    if all(v is not None and v < 0 for v in vals):
        from numfmt import amount
        out["reason"] = (f"{SUSTAINED_NEGATIVE} ({what} de {amount(vals[years])} a {amount(vals[0])}): la tasa no se "
                         "calcula, pero es una señal, no un dato ausente")
        out["sustained_negative"] = True
        return out
    if start <= 0:
        out["reason"] = (f"{what} inicial <= 0: CAGR no definido" if not strict_ends_only
                         else "valor inicial o final <= 0: CAGR no definido")
        return out
    if strict_ends_only and end <= 0:
        out["reason"] = "valor inicial o final <= 0: CAGR no definido"
        return out
    if not strict_ends_only and any(v <= 0 for v in vals):
        out["reason"] = f"el {what} cambia de signo en el periodo: CAGR no definido"
        return out
    others = sorted(v for v in vals[:years] if v is not None)
    med = others[len(others) // 2] if len(others) % 2 else (others[len(others) // 2 - 1] + others[len(others) // 2]) / 2
    ratio = cfg("thresholds.growth.anomalous_base_ratio")
    if start < ratio * med:
        g, why, n = loglinear_growth(values_newest_first)
        out.update(method="log_lineal", anomalous_base=True, years_used=n, value=g,
                   reason=(f"base anómala ({start / med:.0%} de la mediana del resto); " + why) if why else None)
        out["note"] = (f"base anómala: el año inicial es el {start / med:.0%} de la mediana de los demás "
                       f"(< {ratio:.0%}); crecimiento por regresión log-lineal sobre {n} ejercicios")
        return out
    out["value"] = cagr(end, start, years)
    return out


def per_share(values: List[Optional[float]], shares: List[Optional[float]]) -> List[Optional[float]]:
    """valor / acciones del mismo ejercicio; None si falta alguno o acciones <= 0."""
    return [(v / s) if (v is not None and s is not None and s > 0) else None
            for v, s in zip(values or [], shares or [])]


def per_share_basis(shares_newest_first: List[Optional[float]], years: int = 3) -> Dict[str, Any]:
    """¿El crecimiento debe evaluarse por acción? (etapa 7). Sí si las acciones en
    circulación (balance anual, base ajustada por splits) crecen más que
    per_share_min_shares_cagr anual compuesto en la ventana."""
    from settings import cfg
    thr = cfg("thresholds.growth.per_share_min_shares_cagr")
    vals = list(shares_newest_first or [])[:years + 1]
    s_cagr = cagr(vals[0], vals[years], years) if (len(vals) == years + 1 and None not in (vals[0], vals[years])) \
        else None
    if s_cagr is None:
        return {"basis": "agregado", "shares_cagr_3y": None, "threshold": thr,
                "reason": f"sin {years + 1} ejercicios de acciones en circulación: se mide el agregado"}
    if s_cagr > thr:
        return {"basis": "por_accion", "shares_cagr_3y": s_cagr, "threshold": thr,
                "reason": f"las acciones crecen {s_cagr:+.1%} anual en la ventana (> {thr:.0%}): la emisión "
                          "inflaría el crecimiento agregado"}
    return {"basis": "agregado", "shares_cagr_3y": s_cagr, "threshold": thr,
            "reason": f"las acciones varían {s_cagr:+.1%} anual (<= {thr:.0%}): el agregado no está inflado por emisión"}


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
