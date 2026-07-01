"""
Finanzer - Callback del gráfico de precios.
Maneja los cambios de período del gráfico histórico.
"""

from dash import callback, html, dcc, ctx, no_update, Input, Output, State

# Import del creador de gráficos
try:
    from finanzer.components.charts import create_price_chart
except ImportError:
    # Fallback - importar directamente si finanzer no está en path
    try:
        from components.charts import create_price_chart
    except ImportError:
        create_price_chart = None


# Mapeo de botones a períodos
PERIOD_MAP = {
    "period-1wk": "5d",
    "period-1mo": "1mo",
    "period-3mo": "3mo",
    "period-6mo": "6mo",
    "period-1y": "1y",
    "period-5y": "5y"
}

PERIOD_LABELS = {
    "period-1wk": "1 semana",
    "period-1mo": "1 mes",
    "period-3mo": "3 meses",
    "period-6mo": "6 meses",
    "period-1y": "1 año",
    "period-5y": "5 años"
}

BUTTON_ORDER = ["period-1wk", "period-1mo", "period-3mo", "period-6mo", "period-1y", "period-5y"]


@callback(
    Output("price-chart-container", "children"),
    Output("period-1wk", "color"),
    Output("period-1mo", "color"),
    Output("period-3mo", "color"),
    Output("period-6mo", "color"),
    Output("period-1y", "color"),
    Output("period-5y", "color"),
    Output("period-1wk", "outline"),
    Output("period-1mo", "outline"),
    Output("period-3mo", "outline"),
    Output("period-6mo", "outline"),
    Output("period-1y", "outline"),
    Output("period-5y", "outline"),
    Output("price-performance-header", "children"),
    Input("period-1wk", "n_clicks"),
    Input("period-1mo", "n_clicks"),
    Input("period-3mo", "n_clicks"),
    Input("period-6mo", "n_clicks"),
    Input("period-1y", "n_clicks"),
    Input("period-5y", "n_clicks"),
    State("current-symbol", "data"),
    prevent_initial_call=True
)
def update_price_chart_period(n1w, n1, n3, n6, n12, n60, symbol):
    """Actualiza el gráfico de precio cuando cambia el período."""
    if not symbol or create_price_chart is None:
        return no_update, *["secondary"]*6, *[True]*6, no_update
    
    triggered_id = ctx.triggered_id
    
    period = PERIOD_MAP.get(triggered_id, "1y")
    period_label = PERIOD_LABELS.get(triggered_id, "1 año")
    
    # Crear gráfico y obtener datos de rendimiento
    chart, pct_change, end_price = create_price_chart(symbol, period)
    is_positive = pct_change >= 0
    pct_color = '#10b981' if is_positive else '#f43f5e'
    
    # Header de rendimiento actualizado
    performance_header = [
        html.Div([
            html.Span(f"{pct_change:+.1f}%", style={
                "fontSize": "2rem",
                "fontWeight": "700",
                "color": pct_color
            }),
            html.Span(f" {period_label}", style={
                "fontSize": "0.9rem",
                "color": "#71717a",
                "marginLeft": "8px"
            })
        ]),
        html.Div([
            html.Span(f"${end_price:.2f}", style={
                "fontSize": "1.1rem",
                "color": "#a1a1aa"
            }),
            html.Span(" precio actual", style={
                "fontSize": "0.8rem",
                "color": "#52525b",
                "marginLeft": "6px"
            })
        ])
    ]
    
    if chart:
        chart_component = dcc.Graph(
            figure=chart, 
            config={'displayModeBar': False}, 
            id="price-chart"
        )
    else:
        chart_component = html.Div([
            html.P("📈 No se pudieron cargar los datos", 
                   className="text-muted text-center py-5")
        ])
    
    # Actualizar colores de botones
    colors = ["secondary"] * 6
    outlines = [True] * 6
    
    if triggered_id in BUTTON_ORDER:
        idx = BUTTON_ORDER.index(triggered_id)
        colors[idx] = "primary"
        outlines[idx] = False
    
    return chart_component, *colors, *outlines, performance_header
