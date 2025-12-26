"""
Finanzer - Utilidades generales.
"""

from .search import (
    resolve_symbol,
    is_valid_ticker,
    normalize_ticker,
    COMPANY_NAMES,
)

from .formatters import (
    fmt,
    get_metric_color,
)

__all__ = [
    'resolve_symbol',
    'is_valid_ticker',
    'normalize_ticker',
    'COMPANY_NAMES',
    'fmt',
    'get_metric_color',
]
