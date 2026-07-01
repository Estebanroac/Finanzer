"""
Finanzer - Stock Analyzer v3.0.0
Aplicación web para análisis fundamental de acciones.

Estructura modular:
- analysis/: Lógica financiera (ratios, scoring, alerts, sectors)
- components/: UI (cards, charts, tables, tooltips, sensitivity, pdf)
- callbacks/: Callbacks de Dash (search, chart, comparison)
- utils/: Utilidades (search, formatters)
- assets/: CSS customizado
"""

__version__ = "3.0.0"
__author__ = "Esteban"

__all__ = ['analysis', 'components', 'callbacks', 'utils']
