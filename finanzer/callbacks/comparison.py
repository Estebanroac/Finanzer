"""
Finanzer - Callbacks del comparador multi-acción.
Permite comparar hasta 5 acciones side-by-side.
"""

from dash import callback, html, no_update, Input, Output, State
from finanzer.utils.formatters import fmt, get_metric_color


# =============================================================================
# CALLBACKS
# =============================================================================

@callback(
    Output("comparison-stocks", "data"),
    Output("btn-add-comparison", "children"),
    Input("btn-add-comparison", "n_clicks"),
    State("analysis-data", "data"),
    State("comparison-stocks", "data"),
    prevent_initial_call=True
)
def add_to_comparison(n_clicks, analysis_data, comparison_list):
    """Agrega la acción actual a la lista de comparación."""
    if not n_clicks or not analysis_data:
        return no_update, no_update
    
    if comparison_list is None:
        comparison_list = []
    
    symbol = analysis_data.get("symbol", "")
    company_name = analysis_data.get("company_name", symbol)
    ratios = analysis_data.get("ratios", {})
    alerts = analysis_data.get("alerts", {})
    score_v2 = alerts.get("score_v2", {})
    
    # Verificar si ya está en la lista
    existing_symbols = [s.get("symbol") for s in comparison_list]
    if symbol in existing_symbols:
        return comparison_list, [html.Span("✓ "), "Ya agregado"]
    
    # Limitar a 5 acciones máximo
    if len(comparison_list) >= 5:
        comparison_list = comparison_list[1:]
    
    # Agregar nueva acción con métricas clave
    new_stock = {
        "symbol": symbol,
        "name": company_name,
        "score": score_v2.get("total_score", 0),
        "pe": ratios.get("pe"),
        "roe": ratios.get("roe"),
        "debt_equity": ratios.get("debt_to_equity"),
        "net_margin": ratios.get("net_margin"),
        "fcf_yield": ratios.get("fcf_yield"),
        "dividend_yield": ratios.get("dividend_yield"),
        "revenue_growth": ratios.get("revenue_growth"),
    }
    
    comparison_list.append(new_stock)
    
    return comparison_list, [html.Span("✓ "), f"Agregado ({len(comparison_list)})"]


@callback(
    Output("comparison-table-container", "children"),
    Input("comparison-stocks", "data"),
    prevent_initial_call=True
)
def update_comparison_table(comparison_list):
    """Actualiza la tabla de comparación."""
    if not comparison_list or len(comparison_list) == 0:
        return html.Div([
            html.P("No hay acciones en la lista de comparación.", className="text-muted text-center"),
            html.P("Usa el botón 'Comparar' en cada acción para agregarla.", className="text-muted small text-center")
        ])
    
    # Headers
    headers = ["Métrica"] + [s["symbol"] for s in comparison_list]
    
    # Configuración de métricas
    metrics_config = [
        ("Score", "score", "number"),
        ("P/E", "pe", "multiple"),
        ("ROE", "roe", "percent"),
        ("Deuda/Equity", "debt_equity", "multiple"),
        ("Margen Neto", "net_margin", "percent"),
        ("FCF Yield", "fcf_yield", "percent"),
        ("Div. Yield", "dividend_yield", "percent"),
    ]
    
    # Filas de datos
    rows = []
    for metric_name, metric_key, fmt_type in metrics_config:
        row = [html.Td(metric_name, style={"fontWeight": "600", "color": "#a1a1aa"})]
        for stock in comparison_list:
            val = stock.get(metric_key)
            color_class = get_metric_color(val, metric_key)
            row.append(html.Td(fmt(val, fmt_type), className=color_class))
        rows.append(html.Tr(row))
    
    table = html.Table([
        html.Thead([
            html.Tr([
                html.Th(h, style={
                    "textAlign": "center", 
                    "padding": "10px", 
                    "borderBottom": "2px solid #3f3f46"
                }) for h in headers
            ])
        ]),
        html.Tbody(rows, style={"textAlign": "center"})
    ], className="table table-dark", style={"width": "100%"})
    
    return html.Div([
        html.Div([
            html.H6(f"📊 Comparando {len(comparison_list)} acciones", className="mb-2"),
            html.Button(
                "🗑️ Limpiar", 
                id="btn-clear-comparison", 
                n_clicks=0,
                className="btn btn-outline-danger btn-sm", 
                style={"fontSize": "0.75rem"}
            )
        ], className="d-flex justify-content-between align-items-center mb-3"),
        table,
        html.P([
            html.Span("💡 Tip: ", className="text-info"),
            "Verde = bueno, Amarillo = regular, Rojo = atención. Máximo 5 acciones."
        ], className="small text-muted mt-2")
    ])


@callback(
    Output("comparison-stocks", "data", allow_duplicate=True),
    Output("comparison-table-container", "children", allow_duplicate=True),
    Input("btn-clear-comparison", "n_clicks"),
    prevent_initial_call=True
)
def clear_comparison(n_clicks):
    """Limpia la lista de comparación."""
    if n_clicks:
        return [], html.Div([
            html.P("Lista de comparación limpiada.", className="text-muted text-center"),
            html.P("Usa el botón 'Comparar' en cada acción para agregarla.", className="text-muted small text-center")
        ])
    return no_update, no_update
