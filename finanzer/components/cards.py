"""
Finanzer - Componentes de tarjetas de métricas.
Cards para mostrar KPIs, scores y métricas financieras.
"""

from dash import html
import dash_bootstrap_components as dbc

from .tooltips import METRIC_TOOLTIPS, LABEL_TO_TOOLTIP, get_tooltip_text


# Contador global para IDs únicos de tooltips
_tooltip_counter = [0]


def create_info_icon(tooltip_id: str, tooltip_key: str):
    """Crea un ícono de información con tooltip moderno y accesible."""
    return html.Span([
        html.Span("i", 
                  id=tooltip_id, 
                  className="info-icon",
                  role="button",
                  tabIndex=0,
                  **{"aria-label": f"Información sobre {tooltip_key}"}
        ),
        dbc.Tooltip(
            get_tooltip_text(tooltip_key),
            target=tooltip_id,
            placement="top",
        )
    ])


def create_metric_with_tooltip(label: str, value: str, tooltip_key: str, uid: int, value_class: str = "", sublabel: str = ""):
    """Crea una métrica con tooltip informativo integrado."""
    tooltip_id = f"tip-{tooltip_key}-{uid}"
    
    return dbc.Card([
        dbc.CardBody([
            html.Div([
                html.Span(label, className="text-muted small"),
                create_info_icon(tooltip_id, tooltip_key) if tooltip_key in METRIC_TOOLTIPS else None,
            ], className="mb-1 text-center"),
            html.H4(value, className=f"mb-1 text-center {value_class}"),
            html.P(sublabel, className="text-muted small mb-0 text-center", 
                  style={"fontSize": "0.7rem"}) if sublabel else None
        ])
    ], style={"backgroundColor": "#27272a", "border": "none"}, className="h-100")


def create_metric_card(label: str, value: str, icon: str = "📊", tooltip_key: str = None):
    """Crea una tarjeta de métrica centrada con tooltip opcional."""
    # Auto-detectar tooltip key si no se proporciona
    if tooltip_key is None:
        tooltip_key = LABEL_TO_TOOLTIP.get(label)
    
    # Generar ID único
    _tooltip_counter[0] += 1
    tip_id = f"mc-tip-{_tooltip_counter[0]}"
    
    # Contenido del label con o sin tooltip
    if tooltip_key and tooltip_key in METRIC_TOOLTIPS:
        label_content = html.Div([
            html.Span(f"{icon} {label}", className="metric-label"),
            html.Span("i", id=tip_id, className="info-icon", style={"marginLeft": "6px"}),
            dbc.Tooltip(get_tooltip_text(tooltip_key), target=tip_id, placement="top")
        ], style={"display": "inline-flex", "alignItems": "center", "justifyContent": "center"})
    else:
        label_content = html.Div(f"{icon} {label}", className="metric-label")
    
    return html.Div([
        label_content,
        html.Div(value if value else "N/A", className="metric-value")
    ], className="metric-card", style={"textAlign": "center"})


def create_score_summary_card(label: str, score: int, max_score: int = 20, icon: str = "📊"):
    """Crea tarjeta de resumen de score por categoría."""
    pct = score / max_score if max_score > 0 else 0
    if pct >= 0.75:
        color = "#22c55e"
    elif pct >= 0.50:
        color = "#eab308"
    else:
        color = "#ef4444"
    
    return html.Div([
        html.Div(f"{icon} {label}", className="score-summary-label"),
        html.Div(f"{score}/{max_score}", style={"color": color, "fontSize": "1.5rem", "fontWeight": "700"})
    ], className="score-summary-card")


def reset_tooltip_counter():
    """Reinicia el contador de tooltips (útil para testing)."""
    _tooltip_counter[0] = 0
