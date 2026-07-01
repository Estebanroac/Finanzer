"""
Finanzer - Componentes de análisis de sensibilidad DCF.
Visualización de matriz de escenarios para valoración.
"""

from dash import html
from typing import Optional, Dict, Any, List


def get_sensitivity_cell_class(fair_value: Optional[float], price: Optional[float]) -> str:
    """
    Determina la clase CSS según la diferencia entre valor justo y precio.
    
    Args:
        fair_value: Valor justo calculado
        price: Precio actual de mercado
    
    Returns:
        Clase CSS para colorear la celda
    """
    if fair_value is None or price is None or price <= 0:
        return "sens-neutral"
    
    try:
        diff_pct = ((fair_value / price) - 1) * 100
        
        if diff_pct > 30:
            return "sens-very-undervalued"
        elif diff_pct > 10:
            return "sens-undervalued"
        elif diff_pct > -10:
            return "sens-fair"
        elif diff_pct > -30:
            return "sens-overvalued"
        else:
            return "sens-very-overvalued"
    except (TypeError, ValueError, ZeroDivisionError):
        return "sens-neutral"


def build_sensitivity_section(
    sensitivity_data: Dict[str, Any], 
    current_price: float
) -> Optional[html.Div]:
    """
    Construye la sección de análisis de sensibilidad DCF con diseño limpio.
    
    Args:
        sensitivity_data: Dict con matriz, growth_rates, discount_rates, statistics
        current_price: Precio actual de la acción
    
    Returns:
        html.Div con la sección completa o None si datos inválidos
    """
    # Validación exhaustiva de datos de entrada
    if not sensitivity_data:
        return None
    if not sensitivity_data.get("is_valid"):
        return None
    
    matrix = sensitivity_data.get("matrix", [])
    growth_rates = sensitivity_data.get("growth_rates", [])
    discount_rates = sensitivity_data.get("discount_rates", [])
    base_case = sensitivity_data.get("base_case", {})
    stats = sensitivity_data.get("statistics", {})
    
    # Validar que tenemos datos mínimos
    if not matrix or not growth_rates or not discount_rates:
        return None
    if len(matrix) == 0 or len(growth_rates) == 0 or len(discount_rates) == 0:
        return None
    
    base_gr = base_case.get("growth_rate", 0.10)
    base_dr = base_case.get("discount_rate", 0.10)
    base_value = base_case.get("fair_value")
    interpretation = sensitivity_data.get("interpretation", "")
    
    # Validar precio y base_value
    price_valid = current_price is not None and current_price > 0
    base_valid = base_value is not None and base_value > 0
    
    # Construir filas de la tabla
    header_cells = [html.Th("Crec. ↓ / WACC →", className="sens-header")]
    
    for dr in discount_rates:
        is_base = abs(dr - base_dr) < 0.001
        header_cells.append(html.Th(
            f"{dr:.1%}", 
            className="sens-header-base" if is_base else "sens-header"
        ))
    
    body_rows = []
    for i, gr in enumerate(growth_rates):
        if i >= len(matrix):
            continue
            
        is_base_row = abs(gr - base_gr) < 0.001
        
        row_cells = [html.Td(
            f"{gr:.1%}", 
            className="sens-row-header-base" if is_base_row else "sens-row-header"
        )]
        
        for j, val in enumerate(matrix[i]):
            if j >= len(discount_rates):
                continue
                
            is_base_col = abs(discount_rates[j] - base_dr) < 0.001
            is_base_cell = is_base_row and is_base_col
            
            cell_class = get_sensitivity_cell_class(val, current_price) if price_valid else "sens-neutral"
            if is_base_cell:
                cell_class += " sens-base-cell"
            
            cell_text = f"${val:.0f}" if val is not None else "N/A"
            row_cells.append(html.Td(cell_text, className=cell_class))
        
        body_rows.append(html.Tr(row_cells))
    
    # Contar escenarios
    all_values = [v for row in matrix for v in row if v is not None]
    undervalued_pct = 0
    if price_valid and len(all_values) > 0:
        undervalued = sum(1 for v in all_values if v > current_price)
        undervalued_pct = (undervalued / len(all_values)) * 100
    
    # Formatear valores para mostrar
    price_str = f"${current_price:.2f}" if price_valid else "N/A"
    base_str = f"${base_value:.2f}" if base_valid else "N/A"
    
    min_val = stats.get("min_value")
    max_val = stats.get("max_value")
    range_str = ""
    if min_val is not None and max_val is not None:
        range_str = f"${min_val:.0f} - ${max_val:.0f}"
    
    return html.Div([
        html.Hr(className="my-4"),
        # Título fijo (sin Details)
        html.Div([
            html.Span("📊 ", style={"marginRight": "6px"}),
            html.Span("Análisis de Sensibilidad", className="text-info fw-bold"),
            html.Span(" — ¿Y si cambian los supuestos?", className="text-muted small ms-2"),
        ], className="mb-3", style={"fontSize": "1.05rem"}),
        
        html.Div([
            # Explicación clara
            html.Div([
                html.P([
                    "Esta tabla muestra el ", html.Strong("valor justo estimado"),
                    " de la acción según diferentes escenarios. ",
                    "Cada celda es un 'qué pasaría si...' combinando distintas tasas de crecimiento y descuento."
                ], className="mb-2", style={"color": "#d1d5db", "fontSize": "0.9rem"}),
                
                # Referencia del precio actual
                html.Div([
                    html.Span("📌 Precio actual: ", style={"color": "#9ca3af"}),
                    html.Strong(price_str, style={"color": "#3b82f6", "fontSize": "1.1rem"}),
                    html.Span(" — ", style={"color": "#6b7280"}),
                    html.Span("Caso base: ", style={"color": "#9ca3af"}),
                    html.Strong(base_str, style={"color": "#10b981", "fontSize": "1.1rem"}),
                    html.Span(f" (Growth {base_gr:.1%}, WACC {base_dr:.1%})", style={"color": "#6b7280", "fontSize": "0.85rem"}),
                ], className="mb-3 p-2", style={
                    "backgroundColor": "rgba(59, 130, 246, 0.1)",
                    "borderRadius": "8px",
                    "border": "1px solid rgba(59, 130, 246, 0.3)"
                }),
            ], className="mb-3"),
            
            # Tabla
            html.Div([
                html.Table([
                    html.Thead([html.Tr(header_cells)]),
                    html.Tbody(body_rows)
                ], className="sensitivity-table", style={
                    "width": "100%", 
                    "borderCollapse": "separate", 
                    "borderSpacing": "3px",
                    "borderRadius": "8px"
                })
            ], style={"overflowX": "auto", "marginBottom": "15px"}),
            
            # Leyenda visual mejorada
            html.Div([
                html.Div([
                    html.Span("Leyenda: ", style={"color": "#9ca3af", "fontWeight": "500", "marginRight": "12px"}),
                    html.Span("🟢", style={"marginRight": "4px"}),
                    html.Span("Subvalorada ", style={"color": "#22c55e", "marginRight": "12px", "fontSize": "0.85rem"}),
                    html.Span("🟡", style={"marginRight": "4px"}),
                    html.Span("Precio justo ", style={"color": "#eab308", "marginRight": "12px", "fontSize": "0.85rem"}),
                    html.Span("🔴", style={"marginRight": "4px"}),
                    html.Span("Sobrevalorada", style={"color": "#ef4444", "fontSize": "0.85rem"}),
                ], className="d-flex flex-wrap align-items-center mb-2"),
                
                # Interpretación
                html.Div([
                    html.Strong("📈 Veredicto: ", style={"color": "#9ca3af"}),
                    html.Span(interpretation if interpretation else "Sin datos suficientes", style={
                        "color": "#22c55e" if undervalued_pct >= 60 else "#eab308" if undervalued_pct >= 40 else "#ef4444"
                    }),
                ]),
                
                html.P([
                    f"Rango de valores: {range_str}" if range_str else "Rango no disponible"
                ], className="small text-muted mb-0 mt-1"),
                
            ], style={
                "backgroundColor": "rgba(39, 39, 42, 0.5)",
                "padding": "12px 15px",
                "borderRadius": "8px",
                "marginTop": "10px"
            }),
            
            # Nota explicativa
            html.P([
                html.Span("💡 ", style={"marginRight": "4px"}),
                "Si el valor justo (celda) es ", html.Strong("mayor"), " que el precio actual → ",
                html.Span("subvalorada", className="text-success"), ". ",
                "Si es ", html.Strong("menor"), " → ",
                html.Span("sobrevalorada", className="text-danger"), "."
            ], className="small text-muted mt-3 mb-0", style={"fontStyle": "italic"})
            
        ], className="p-3 sensitivity-container")
    ])
