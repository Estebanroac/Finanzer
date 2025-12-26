"""
Finanzer - Componentes de tablas.
Tablas y filas para comparación de métricas.
"""

from dash import html
from typing import Optional, Union


def create_comparison_metric_row(
    metric_name: str, 
    company_val: Optional[float], 
    sector_val: Optional[float], 
    market_val: Optional[float], 
    fmt: str = "multiple", 
    lower_better: bool = True
) -> html.Tr:
    """
    Crea una fila de comparación de métricas con veredicto.
    
    Args:
        metric_name: Nombre de la métrica a mostrar
        company_val: Valor de la empresa
        sector_val: Valor benchmark del sector
        market_val: Valor benchmark del mercado
        fmt: Formato de visualización ("multiple", "percent", "decimal")
        lower_better: Si True, valores menores son mejores
    
    Returns:
        html.Tr con la fila de comparación
    """
    def format_val(v: Optional[float], fmt: str) -> str:
        if v is None:
            return "N/A"
        if fmt == "percent":
            return f"{v*100:.1f}%" if isinstance(v, float) and abs(v) < 2 else f"{v:.1f}%"
        elif fmt == "multiple":
            return f"{v:.2f}x"
        else:
            return f"{v:.2f}"
    
    def get_verdict(
        company_val: Optional[float], 
        sector_val: Optional[float], 
        market_val: Optional[float], 
        lower_is_better: bool
    ) -> tuple:
        """Calcula veredicto basado en comparación con sector Y mercado."""
        if company_val is None:
            return "Sin datos", "#6b7280", "⚪"
        if lower_is_better is None:
            return "N/A", "#6b7280", "⚪"
        
        better_than_sector = False
        better_than_market = False
        
        if sector_val is not None:
            if lower_is_better:
                better_than_sector = company_val < sector_val * 1.15
            else:
                better_than_sector = company_val > sector_val * 0.85
        
        if market_val is not None:
            if lower_is_better:
                better_than_market = company_val < market_val * 1.15
            else:
                better_than_market = company_val > market_val * 0.85
        
        if better_than_sector and better_than_market:
            return "Excelente", "#22c55e", "●"
        elif better_than_sector or better_than_market:
            return "Aceptable", "#eab308", "●"
        else:
            return "Débil", "#ef4444", "●"
    
    verdict_text, verdict_color, verdict_icon = get_verdict(
        company_val, sector_val, market_val, lower_better
    )
    
    # Estilo base de celda
    cell_style = {
        "padding": "14px 16px",
        "borderBottom": "1px solid rgba(55, 65, 81, 0.5)",
        "fontSize": "0.9rem"
    }
    
    return html.Tr([
        html.Td(metric_name, style={
            **cell_style, 
            "textAlign": "left", 
            "fontWeight": "500", 
            "color": "#e5e7eb"
        }),
        html.Td(format_val(company_val, fmt), style={
            **cell_style, 
            "textAlign": "center", 
            "fontWeight": "700", 
            "color": "#ffffff",
            "fontSize": "0.95rem"
        }),
        html.Td(format_val(sector_val, fmt), style={
            **cell_style, 
            "textAlign": "center", 
            "color": "#9ca3af"
        }),
        html.Td(format_val(market_val, fmt), style={
            **cell_style, 
            "textAlign": "center", 
            "color": "#9ca3af"
        }),
        html.Td([
            html.Span(verdict_icon, style={
                "color": verdict_color, 
                "marginRight": "8px", 
                "fontSize": "1rem"
            }),
            html.Span(verdict_text, style={"fontWeight": "500"})
        ], style={
            **cell_style, 
            "textAlign": "center", 
            "color": verdict_color
        }),
    ], style={"transition": "background 0.2s"})


def create_comparison_table_header() -> html.Thead:
    """Crea el encabezado de la tabla de comparación."""
    header_style = {
        "padding": "14px 16px",
        "textAlign": "center",
        "fontWeight": "600",
        "fontSize": "0.85rem",
        "color": "#9ca3af",
        "borderBottom": "2px solid rgba(55, 65, 81, 0.8)",
        "textTransform": "uppercase",
        "letterSpacing": "0.05em"
    }
    
    return html.Thead([
        html.Tr([
            html.Th("Métrica", style={**header_style, "textAlign": "left"}),
            html.Th("Empresa", style={**header_style, "color": "#ffffff"}),
            html.Th("Sector", style=header_style),
            html.Th("Mercado", style=header_style),
            html.Th("Veredicto", style=header_style),
        ])
    ])
