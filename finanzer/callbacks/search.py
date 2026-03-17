"""
Finanzer - Callbacks de búsqueda de acciones.
Maneja las sugerencias de autocompletado.
"""

from dash import callback, html, Input, Output

# Import de la base de datos de stocks
try:
    from stock_database import search_stocks
except ImportError:
    # Fallback si no está disponible
    def search_stocks(query, limit=6):
        return []


# Estilos base del dropdown de sugerencias
DROPDOWN_BASE_STYLE = {
    "position": "absolute",
    "top": "100%",
    "left": "0",
    "right": "0",
    "marginTop": "4px",
    "background": "#1f1f23",
    "border": "1px solid rgba(16, 185, 129, 0.5)",
    "borderRadius": "10px",
    "boxShadow": "0 8px 32px rgba(0, 0, 0, 0.7)",
    "zIndex": "9999",
    "maxHeight": "300px",
    "overflowY": "auto"
}


@callback(
    Output("navbar-search-suggestions", "children"),
    Output("navbar-search-suggestions", "style"),
    Input("navbar-search-input", "value"),
    prevent_initial_call=True
)
def update_search_suggestions(search_value):
    """Muestra sugerencias mientras el usuario escribe."""
    
    hidden_style = {**DROPDOWN_BASE_STYLE, "display": "none"}
    visible_style = {**DROPDOWN_BASE_STYLE, "display": "block"}
    
    # Si no hay valor o es muy corto, ocultar
    if not search_value or len(str(search_value).strip()) < 1:
        return [], hidden_style
    
    query = str(search_value).strip()
    
    # Buscar sugerencias
    suggestions = search_stocks(query, limit=6)
    
    if not suggestions:
        return [
            html.Div([
                html.P(f"No hay sugerencias para '{query}'", style={
                    "color": "#a1a1aa", "margin": "0 0 4px 0", "fontSize": "0.85rem"
                }),
                html.P("💡 Presiona Enter para buscar cualquier ticker", style={
                    "color": "#10b981", "margin": "0", "fontSize": "0.8rem", "fontWeight": "500"
                })
            ], style={"padding": "12px 16px", "textAlign": "center"})
        ], visible_style
    
    # Crear items de sugerencias clickeables
    suggestion_items = []
    for i, (ticker, name, _) in enumerate(suggestions):
        is_last = i == len(suggestions) - 1
        suggestion_items.append(
            html.Div([
                html.Span(ticker, style={
                    "color": "#10b981", 
                    "fontWeight": "700", 
                    "fontSize": "0.95rem",
                    "marginRight": "12px", 
                    "minWidth": "60px", 
                    "display": "inline-block"
                }),
                html.Span(
                    name[:35] + ("..." if len(name) > 35 else ""), 
                    style={"color": "#d4d4d8", "fontSize": "0.85rem"}
                )
            ], 
            id={"type": "suggestion-item", "index": ticker}, 
            n_clicks=0,
            style={
                "padding": "12px 16px",
                "cursor": "pointer",
                "borderBottom": "none" if is_last else "1px solid rgba(63, 63, 70, 0.5)",
                "transition": "all 0.15s ease",
                "backgroundColor": "transparent"
            }, 
            className="suggestion-hover")
        )
    
    return suggestion_items, visible_style
