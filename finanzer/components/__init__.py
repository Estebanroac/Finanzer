"""
Finanzer - Componentes de UI.
Módulos reutilizables para la interfaz de usuario.

Nota: cards.py y charts.py requieren dash/plotly instalados.
Para usar sin estas dependencias, importar módulos individuales:
    from finanzer.components.tooltips import METRIC_TOOLTIPS
"""

# Tooltips siempre disponible (sin dependencias externas)
from .tooltips import METRIC_TOOLTIPS, LABEL_TO_TOOLTIP, get_tooltip_text

# Los demás módulos requieren dash/plotly - importar bajo demanda
__all__ = [
    # Tooltips (siempre disponible)
    'METRIC_TOOLTIPS',
    'LABEL_TO_TOOLTIP', 
    'get_tooltip_text',
    # Cards (requiere dash)
    'create_metric_card',
    'create_metric_with_tooltip',
    'create_score_summary_card',
    'create_info_icon',
    'reset_tooltip_counter',
    # Charts (requiere plotly)
    'get_score_color',
    'create_score_donut',
    'create_price_chart',
    'create_ytd_comparison_chart',
    # Tables (requiere dash)
    'create_comparison_metric_row',
    'create_comparison_table_header',
    # Sensitivity (requiere dash)
    'build_sensitivity_section',
    'get_sensitivity_cell_class',
    # PDF (requiere reportlab)
    'generate_simple_pdf',
]


def __getattr__(name):
    """Lazy loading de módulos con dependencias."""
    import importlib as _il

    _MODULE_MAP = {
        'create_metric_card': '.cards',
        'create_metric_with_tooltip': '.cards',
        'create_score_summary_card': '.cards',
        'create_info_icon': '.cards',
        'reset_tooltip_counter': '.cards',
        'get_score_color': '.charts',
        'create_score_donut': '.charts',
        'create_price_chart': '.charts',
        'create_ytd_comparison_chart': '.charts',
        'create_comparison_metric_row': '.tables',
        'create_comparison_table_header': '.tables',
        'build_sensitivity_section': '.sensitivity',
        'get_sensitivity_cell_class': '.sensitivity',
        'generate_simple_pdf': '.pdf_generator',
    }

    if name in _MODULE_MAP:
        module = _il.import_module(_MODULE_MAP[name], __package__)
        attr = getattr(module, name)
        globals()[name] = attr  # Cache para futuras llamadas
        return attr

    raise AttributeError(f"module 'finanzer.components' has no attribute '{name}'")
