"""P8b: la variación de un valor en un periodo de la portada, en un solo sitio. La usan las listas del cintillo
(lib/trending.py) y la variación de las mini-gráficas (lib/sparklines.py): el % de cada tarjeta es exactamente el que
ordena su lista.

    cambio = cierre_ajustado(última sesión) / cierre_ajustado(hace N sesiones) − 1

con N de `market.trending.period_sessions` (1D = 1, la sesión anterior; 1S = 5; 1M = 21; 6M = 126) y el cierre
ajustado por splits y dividendos («Adj Close» de Yahoo), para que un split o un dividendo no falseen la rentabilidad.
Las sesiones se cuentan en el calendario común del universo (las fechas con cotización de cualquier valor), así que
todas las tarjetas de un periodo comparten la fecha de partida; un valor sin cotización en esa fecha o antes (salida
a bolsa reciente) queda sin variación.
"""
from bisect import bisect_right
from typing import List, Optional, Sequence

from settings import cfg


def periods() -> List[str]:
    return list(cfg("market.trending.periods"))


def sessions(period: str) -> int:
    return int(cfg("market.trending.period_sessions")[period])


def reference_date(calendar: Sequence[str], period: str) -> Optional[str]:
    """La sesión de partida del periodo: N sesiones antes de la última del calendario (None si no hay tantas)."""
    n = sessions(period)
    return calendar[-1 - n] if len(calendar) > n else None


def change(dates: Sequence[str], adj: Sequence[float], calendar: Sequence[str], period: str) -> Optional[float]:
    """Variación del periodo de un valor con cotizaciones `adj` (cierre ajustado) en las fechas `dates` (ISO,
    ascendentes). None si no cotiza en la última sesión del calendario o no tiene precio en la de partida."""
    ref = reference_date(calendar, period)
    if not ref or not dates or dates[-1] != calendar[-1]:
        return None
    i = bisect_right(list(dates), ref) - 1
    if i < 0 or not adj[i] or adj[i] <= 0 or adj[-1] != adj[-1]:
        return None
    return adj[-1] / adj[i] - 1
