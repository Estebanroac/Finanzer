"""
Finanzer - Módulo de análisis financiero.
Contiene utilidades de formateo, alertas y configuración sectorial.

Nota: Los ratios y scoring principales están en financial_ratios.py (raíz del proyecto).
"""

from .utils import (
    safe_div,
    safe_multiply,
    safe_subtract,
    safe_add,
    safe_percentage,
    clamp,
    format_large_number,
    format_ratio
)

from .alerts import (
    get_alert_explanation,
    ALERT_EXPLANATIONS,
    GENERIC_EXPLANATIONS,
)

from .sectors import (
    get_sector_metrics_config,
    MARKET_BENCHMARKS,
)

__all__ = [
    # Utils
    'safe_div', 'safe_multiply', 'safe_subtract', 'safe_add',
    'safe_percentage', 'clamp', 'format_large_number', 'format_ratio',
    # Alerts
    'get_alert_explanation', 'ALERT_EXPLANATIONS', 'GENERIC_EXPLANATIONS',
    # Sectors
    'get_sector_metrics_config', 'MARKET_BENCHMARKS',
]
