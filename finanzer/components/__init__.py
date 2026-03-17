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
    if name in ('create_metric_card', 'create_metric_with_tooltip', 
                'create_score_summary_card', 'create_info_icon', 'reset_tooltip_counter'):
        from .cards import (
            create_metric_card, create_metric_with_tooltip,
            create_score_summary_card, create_info_icon, reset_tooltip_counter
        )
        return locals()[name]
    
    if name in ('get_score_color', 'create_score_donut', 
                'create_price_chart', 'create_ytd_comparison_chart'):
        from .charts import (
            get_score_color, create_score_donut,
            create_price_chart, create_ytd_comparison_chart
        )
        return locals()[name]
    
    if name in ('create_comparison_metric_row', 'create_comparison_table_header'):
        from .tables import create_comparison_metric_row, create_comparison_table_header
        return locals()[name]
    
    if name in ('build_sensitivity_section', 'get_sensitivity_cell_class'):
        from .sensitivity import build_sensitivity_section, get_sensitivity_cell_class
        return locals()[name]
    
    if name == 'generate_simple_pdf':
        from .pdf_generator import generate_simple_pdf
        return generate_simple_pdf
    
    raise AttributeError(f"module 'finanzer.components' has no attribute '{name}'")
