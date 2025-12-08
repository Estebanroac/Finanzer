"""
Stock Analyzer - Dash Edition v2.0
==================================
Aplicación web responsive para análisis fundamental de acciones.
Mobile-first design con dark theme premium.

Autor: Esteban
Versión: 2.0 - Comparativa completa y Score Summary
"""

import dash
from dash import dcc, html, callback, Input, Output, State, no_update, ctx, ALL
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from datetime import datetime

# Importar módulos del analizador
from financial_ratios import (
    calculate_all_ratios,
    aggregate_alerts,
    format_ratio,
    graham_number,
    dcf_fair_value,
)
from data_fetcher import FinancialDataService
from sector_profiles import get_sector_profile
from stock_database import search_stocks, POPULAR_STOCKS

# =============================================================================
# INICIALIZACIÓN DE LA APP
# =============================================================================

app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.DARKLY,
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
    ],
    suppress_callback_exceptions=True,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1, maximum-scale=1"},
        {"name": "theme-color", "content": "#09090b"}
    ],
    title="Stock Analyzer"
)

server = app.server

# =============================================================================
# CONSTANTES
# =============================================================================

QUICK_PICKS = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "JPM", "V", "TSM"]

COMPANY_NAMES = {
    "apple": "AAPL", "microsoft": "MSFT", "google": "GOOGL", "alphabet": "GOOGL",
    "amazon": "AMZN", "tesla": "TSLA", "nvidia": "NVDA", "meta": "META",
    "facebook": "META", "netflix": "NFLX", "disney": "DIS", "visa": "V",
    "mastercard": "MA", "jpmorgan": "JPM", "berkshire": "BRK-B", "taiwan semiconductor": "TSM",
}

# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

def resolve_symbol(query: str) -> str:
    if not query:
        return ""
    query_clean = query.lower().strip()
    return COMPANY_NAMES.get(query_clean, query.upper().strip())


def get_score_color(score: int) -> tuple:
    if score >= 70:
        return "#22c55e", "FAVORABLE"
    elif score >= 50:
        return "#eab308", "NEUTRAL"
    elif score >= 30:
        return "#f97316", "PRECAUCIÓN"
    else:
        return "#ef4444", "EVITAR"


def create_score_donut(score: int) -> go.Figure:
    """Crea gráfico donut moderno para el score."""
    color, label = get_score_color(score)
    
    fig = go.Figure()
    
    # Donut de fondo
    fig.add_trace(go.Pie(
        values=[100],
        hole=0.75,
        marker=dict(colors=['#27272a']),
        showlegend=False,
        hoverinfo='none',
        textinfo='none'
    ))
    
    # Donut del score
    remaining = 100 - score
    fig.add_trace(go.Pie(
        values=[score, remaining],
        hole=0.75,
        marker=dict(colors=[color, 'rgba(0,0,0,0)'], line=dict(width=0)),
        showlegend=False,
        hoverinfo='none',
        textinfo='none',
        rotation=90,
        direction='clockwise'
    ))
    
    fig.add_annotation(text=f"<b>{score}</b>", x=0.5, y=0.55,
        font=dict(size=42, color=color, family='Inter'), showarrow=False)
    fig.add_annotation(text=label, x=0.5, y=0.35,
        font=dict(size=12, color='#71717a', family='Inter'), showarrow=False)
    
    fig.update_layout(
        height=180, margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font={'family': 'Inter, sans-serif'}
    )
    return fig


def create_price_chart(symbol: str, period: str = "1y") -> go.Figure:
    """Crea gráfico de precio histórico."""
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period)
        
        if hist.empty:
            return None
        
        start_price = hist['Close'].iloc[0]
        end_price = hist['Close'].iloc[-1]
        is_positive = end_price >= start_price
        pct_change = ((end_price - start_price) / start_price) * 100
        line_color = '#22c55e' if is_positive else '#ef4444'
        fill_color = 'rgba(34, 197, 94, 0.15)' if is_positive else 'rgba(239, 68, 68, 0.15)'
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=hist.index, y=hist['Close'],
            mode='lines',
            line=dict(color=line_color, width=2.5),
            fill='tozeroy', fillcolor=fill_color,
            hovertemplate='%{x|%d %b %Y}<br>$%{y:.2f}<extra></extra>'
        ))
        
        # Añadir anotación de rendimiento
        fig.add_annotation(
            x=hist.index[-1], y=end_price,
            text=f"{pct_change:+.1f}%",
            showarrow=False,
            font=dict(size=14, color=line_color, family='Inter'),
            xanchor='left', xshift=10
        )
        
        fig.update_layout(
            height=320, margin=dict(l=10, r=60, t=20, b=10),
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showgrid=False, showticklabels=True, tickfont=dict(color='#71717a', size=10), zeroline=False),
            yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', showticklabels=True,
                      tickfont=dict(color='#71717a', size=10), tickprefix='$', zeroline=False),
            hovermode='x unified', font={'family': 'Inter, sans-serif'}
        )
        return fig
    except:
        return None


def create_ytd_comparison_chart(stock_ytd: float, market_ytd: float, sector_ytd: float, symbol: str) -> go.Figure:
    """Crea gráfico de barras comparativo YTD mejorado."""
    categories = [symbol, 'S&P 500', 'Sector ETF']
    values = [stock_ytd, market_ytd, sector_ytd]
    
    # Colores según valor positivo/negativo
    colors = []
    for v in values:
        if v > 0:
            colors.append('#22c55e')
        elif v < 0:
            colors.append('#ef4444')
        else:
            colors.append('#71717a')
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=categories, y=values,
        marker=dict(
            color=colors,
            line=dict(width=0),
            opacity=0.85
        ),
        text=[f"{v:+.1f}%" for v in values],
        textposition='outside',
        textfont=dict(color='#e4e4e7', size=14, family='Inter', weight=600),
        hovertemplate='%{x}<br>Rendimiento YTD: %{y:.2f}%<extra></extra>',
        width=0.5
    ))
    
    fig.add_hline(y=0, line_dash="solid", line_color="#3f3f46", line_width=2)
    
    fig.update_layout(
        height=300, margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(
            showgrid=False, 
            tickfont=dict(color='#a1a1aa', size=13, family='Inter'),
            showline=False
        ),
        yaxis=dict(
            showgrid=True, gridcolor='rgba(255,255,255,0.08)',
            tickfont=dict(color='#71717a', size=11), 
            ticksuffix='%', zeroline=False,
            showline=False
        ),
        font={'family': 'Inter, sans-serif'}, 
        showlegend=False,
        bargap=0.4
    )
    return fig


def create_metric_card(label: str, value: str, icon: str = "📊"):
    """Crea una tarjeta de métrica centrada."""
    return html.Div([
        html.Div(f"{icon} {label}", className="metric-label"),
        html.Div(value if value else "N/A", className="metric-value")
    ], className="metric-card", style={"textAlign": "center"})


def create_score_summary_card(label: str, score: int, max_score: int = 20, icon: str = "📊"):
    """Crea tarjeta de resumen de score por categoría."""
    if score >= 15:
        color, bg = "#22c55e", "rgba(34, 197, 94, 0.15)"
    elif score >= 10:
        color, bg = "#eab308", "rgba(234, 179, 8, 0.15)"
    else:
        color, bg = "#ef4444", "rgba(239, 68, 68, 0.15)"
    
    return html.Div([
        html.Div(f"{icon} {label}", style={"color": "#71717a", "fontSize": "0.75rem", "marginBottom": "8px"}),
        html.Div(f"{score}/{max_score}", style={"color": color, "fontSize": "1.5rem", "fontWeight": "700"})
    ], style={
        "background": bg, "border": f"1px solid {color}33", "borderRadius": "12px",
        "padding": "16px", "textAlign": "center"
    })


def create_comparison_metric_row(metric_name: str, company_val, sector_val, market_val, fmt: str = "multiple", lower_better: bool = True):
    """Crea una fila de comparación de métricas con veredicto."""
    def format_val(v, fmt):
        if v is None:
            return "N/A"
        if fmt == "percent":
            return f"{v*100:.1f}%" if isinstance(v, float) and v < 1 else f"{v:.1f}%"
        elif fmt == "multiple":
            return f"{v:.2f}x"
        else:
            return f"{v:.2f}"
    
    def get_verdict(company_val, sector_val, market_val, lower_is_better):
        """Calcula veredicto basado en comparación con sector Y mercado."""
        if company_val is None:
            return "⚪ Sin datos", "#71717a"
        if lower_is_better is None:
            return "⚪ N/A", "#71717a"
        
        # Comparar con ambos benchmarks
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
            return "🟢 Excelente", "#22c55e"
        elif better_than_sector or better_than_market:
            return "🟡 Aceptable", "#eab308"
        else:
            return "🔴 Débil", "#ef4444"
    
    verdict_text, verdict_color = get_verdict(company_val, sector_val, market_val, lower_better)
    
    return html.Tr([
        html.Td(metric_name, style={"padding": "12px 16px", "borderBottom": "1px solid #27272a", "fontWeight": "500"}),
        html.Td(format_val(company_val, fmt), style={"padding": "12px", "borderBottom": "1px solid #27272a", "textAlign": "center", "color": "#3b82f6", "fontWeight": "600"}),
        html.Td(format_val(sector_val, fmt), style={"padding": "12px", "borderBottom": "1px solid #27272a", "textAlign": "center", "color": "#a1a1aa"}),
        html.Td(format_val(market_val, fmt), style={"padding": "12px", "borderBottom": "1px solid #27272a", "textAlign": "center", "color": "#a1a1aa"}),
        html.Td(verdict_text, style={"padding": "12px 16px", "borderBottom": "1px solid #27272a", "textAlign": "center", "color": verdict_color, "fontWeight": "600"}),
    ])


def get_sector_metrics_config(sector: str) -> list:
    """Retorna configuración de métricas según sector.
    
    IMPORTANTE: Los valores sector_val deben coincidir con los umbrales
    en SECTOR_THRESHOLDS de financial_ratios.py para consistencia.
    """
    sector_lower = sector.lower() if sector else ""
    
    if any(x in sector_lower for x in ["financial", "bank", "insurance"]):
        return [
            {"key": "pb", "name": "P/Book ⭐", "lower_better": True, "sector_val": 1.3, "market_val": 4.0, "fmt": "multiple"},
            {"key": "pe", "name": "P/E Ratio", "lower_better": True, "sector_val": 14.0, "market_val": 28.9, "fmt": "multiple"},
            {"key": "roe", "name": "ROE ⭐", "lower_better": False, "sector_val": 0.12, "market_val": 0.15, "fmt": "percent"},
            {"key": "net_margin", "name": "Margen Neto", "lower_better": False, "sector_val": 0.20, "market_val": 0.10, "fmt": "percent"},
            {"key": "dividend_yield", "name": "Dividend Yield", "lower_better": False, "sector_val": 0.025, "market_val": 0.015, "fmt": "percent"},
        ]
    elif any(x in sector_lower for x in ["tech", "software", "semiconductor", "information"]):
        return [
            {"key": "pe", "name": "P/E Ratio", "lower_better": True, "sector_val": 28.0, "market_val": 28.9, "fmt": "multiple"},
            {"key": "revenue_growth", "name": "Crec. Ingresos ⭐", "lower_better": False, "sector_val": 0.15, "market_val": 0.08, "fmt": "percent"},
            {"key": "gross_margin", "name": "Margen Bruto ⭐", "lower_better": False, "sector_val": 0.50, "market_val": 0.35, "fmt": "percent"},
            {"key": "operating_margin", "name": "Margen Operativo", "lower_better": False, "sector_val": 0.15, "market_val": 0.12, "fmt": "percent"},
            {"key": "roe", "name": "ROE", "lower_better": False, "sector_val": 0.22, "market_val": 0.15, "fmt": "percent"},
            {"key": "debt_to_equity", "name": "Deuda/Equity", "lower_better": True, "sector_val": 0.50, "market_val": 0.80, "fmt": "multiple"},
        ]
    elif any(x in sector_lower for x in ["health", "biotech", "pharma"]):
        return [
            {"key": "pe", "name": "P/E Ratio", "lower_better": True, "sector_val": 22.0, "market_val": 28.9, "fmt": "multiple"},
            {"key": "gross_margin", "name": "Margen Bruto ⭐", "lower_better": False, "sector_val": 0.55, "market_val": 0.35, "fmt": "percent"},
            {"key": "operating_margin", "name": "Margen Operativo", "lower_better": False, "sector_val": 0.12, "market_val": 0.12, "fmt": "percent"},
            {"key": "roe", "name": "ROE", "lower_better": False, "sector_val": 0.18, "market_val": 0.15, "fmt": "percent"},
            {"key": "debt_to_equity", "name": "Deuda/Equity", "lower_better": True, "sector_val": 0.60, "market_val": 0.80, "fmt": "multiple"},
        ]
    elif any(x in sector_lower for x in ["consumer cyclical", "consumer discretionary", "retail"]):
        return [
            {"key": "pe", "name": "P/E Ratio", "lower_better": True, "sector_val": 22.0, "market_val": 28.9, "fmt": "multiple"},
            {"key": "revenue_growth", "name": "Crec. Ingresos ⭐", "lower_better": False, "sector_val": 0.10, "market_val": 0.08, "fmt": "percent"},
            {"key": "operating_margin", "name": "Margen Operativo", "lower_better": False, "sector_val": 0.06, "market_val": 0.12, "fmt": "percent"},
            {"key": "roe", "name": "ROE", "lower_better": False, "sector_val": 0.18, "market_val": 0.15, "fmt": "percent"},
            {"key": "current_ratio", "name": "Current Ratio", "lower_better": False, "sector_val": 1.2, "market_val": 1.5, "fmt": "multiple"},
        ]
    elif any(x in sector_lower for x in ["energy", "oil", "gas"]):
        # Energy: sector cíclico, capital intensivo - métricas específicas
        return [
            {"key": "ev_ebitda", "name": "EV/EBITDA ⭐", "lower_better": True, "sector_val": 6.0, "market_val": 12.0, "fmt": "multiple"},
            {"key": "fcf_yield", "name": "FCF Yield ⭐", "lower_better": False, "sector_val": 0.08, "market_val": 0.04, "fmt": "percent"},
            {"key": "roe", "name": "ROE", "lower_better": False, "sector_val": 0.12, "market_val": 0.15, "fmt": "percent"},
            {"key": "operating_margin", "name": "Margen Operativo", "lower_better": False, "sector_val": 0.08, "market_val": 0.12, "fmt": "percent"},
            {"key": "debt_to_equity", "name": "Deuda/Equity", "lower_better": True, "sector_val": 0.50, "market_val": 0.80, "fmt": "multiple"},
            {"key": "dividend_yield", "name": "Dividend Yield", "lower_better": False, "sector_val": 0.04, "market_val": 0.015, "fmt": "percent"},
        ]
    elif any(x in sector_lower for x in ["utility", "utilities"]):
        return [
            {"key": "pe", "name": "P/E Ratio", "lower_better": True, "sector_val": 18.0, "market_val": 28.9, "fmt": "multiple"},
            {"key": "dividend_yield", "name": "Dividend Yield ⭐", "lower_better": False, "sector_val": 0.035, "market_val": 0.015, "fmt": "percent"},
            {"key": "roe", "name": "ROE", "lower_better": False, "sector_val": 0.10, "market_val": 0.15, "fmt": "percent"},
            {"key": "operating_margin", "name": "Margen Operativo", "lower_better": False, "sector_val": 0.12, "market_val": 0.12, "fmt": "percent"},
            {"key": "debt_to_equity", "name": "Deuda/Equity", "lower_better": True, "sector_val": 1.50, "market_val": 0.80, "fmt": "multiple"},
        ]
    elif any(x in sector_lower for x in ["consumer defensive", "consumer staples"]):
        return [
            {"key": "pe", "name": "P/E Ratio", "lower_better": True, "sector_val": 22.0, "market_val": 28.9, "fmt": "multiple"},
            {"key": "dividend_yield", "name": "Dividend Yield ⭐", "lower_better": False, "sector_val": 0.025, "market_val": 0.015, "fmt": "percent"},
            {"key": "roe", "name": "ROE", "lower_better": False, "sector_val": 0.20, "market_val": 0.15, "fmt": "percent"},
            {"key": "operating_margin", "name": "Margen Operativo", "lower_better": False, "sector_val": 0.10, "market_val": 0.12, "fmt": "percent"},
            {"key": "gross_margin", "name": "Margen Bruto", "lower_better": False, "sector_val": 0.35, "market_val": 0.35, "fmt": "percent"},
        ]
    elif any(x in sector_lower for x in ["industrial", "aerospace", "defense"]):
        return [
            {"key": "pe", "name": "P/E Ratio", "lower_better": True, "sector_val": 20.0, "market_val": 28.9, "fmt": "multiple"},
            {"key": "roe", "name": "ROE", "lower_better": False, "sector_val": 0.15, "market_val": 0.15, "fmt": "percent"},
            {"key": "operating_margin", "name": "Margen Operativo", "lower_better": False, "sector_val": 0.08, "market_val": 0.12, "fmt": "percent"},
            {"key": "debt_to_equity", "name": "Deuda/Equity", "lower_better": True, "sector_val": 0.80, "market_val": 0.80, "fmt": "multiple"},
            {"key": "current_ratio", "name": "Current Ratio", "lower_better": False, "sector_val": 1.3, "market_val": 1.5, "fmt": "multiple"},
        ]
    elif any(x in sector_lower for x in ["real estate", "reit"]):
        return [
            {"key": "dividend_yield", "name": "Dividend Yield ⭐", "lower_better": False, "sector_val": 0.04, "market_val": 0.015, "fmt": "percent"},
            {"key": "pb", "name": "P/Book", "lower_better": True, "sector_val": 2.0, "market_val": 4.0, "fmt": "multiple"},
            {"key": "roe", "name": "ROE", "lower_better": False, "sector_val": 0.08, "market_val": 0.15, "fmt": "percent"},
            {"key": "operating_margin", "name": "Margen Operativo", "lower_better": False, "sector_val": 0.25, "market_val": 0.12, "fmt": "percent"},
            {"key": "debt_to_equity", "name": "Deuda/Equity", "lower_better": True, "sector_val": 2.00, "market_val": 0.80, "fmt": "multiple"},
        ]
    elif any(x in sector_lower for x in ["communication", "media", "telecom"]):
        return [
            {"key": "pe", "name": "P/E Ratio", "lower_better": True, "sector_val": 18.0, "market_val": 28.9, "fmt": "multiple"},
            {"key": "roe", "name": "ROE", "lower_better": False, "sector_val": 0.15, "market_val": 0.15, "fmt": "percent"},
            {"key": "operating_margin", "name": "Margen Operativo", "lower_better": False, "sector_val": 0.15, "market_val": 0.12, "fmt": "percent"},
            {"key": "debt_to_equity", "name": "Deuda/Equity", "lower_better": True, "sector_val": 1.00, "market_val": 0.80, "fmt": "multiple"},
            {"key": "dividend_yield", "name": "Dividend Yield", "lower_better": False, "sector_val": 0.02, "market_val": 0.015, "fmt": "percent"},
        ]
    elif any(x in sector_lower for x in ["material", "mining", "chemical"]):
        return [
            {"key": "pe", "name": "P/E Ratio", "lower_better": True, "sector_val": 15.0, "market_val": 28.9, "fmt": "multiple"},
            {"key": "ev_ebitda", "name": "EV/EBITDA ⭐", "lower_better": True, "sector_val": 8.0, "market_val": 12.0, "fmt": "multiple"},
            {"key": "roe", "name": "ROE", "lower_better": False, "sector_val": 0.12, "market_val": 0.15, "fmt": "percent"},
            {"key": "operating_margin", "name": "Margen Operativo", "lower_better": False, "sector_val": 0.10, "market_val": 0.12, "fmt": "percent"},
            {"key": "debt_to_equity", "name": "Deuda/Equity", "lower_better": True, "sector_val": 0.60, "market_val": 0.80, "fmt": "multiple"},
        ]
    else:
        return [
            {"key": "pe", "name": "P/E Ratio", "lower_better": True, "sector_val": 20.0, "market_val": 28.9, "fmt": "multiple"},
            {"key": "roe", "name": "ROE", "lower_better": False, "sector_val": 0.15, "market_val": 0.15, "fmt": "percent"},
            {"key": "net_margin", "name": "Margen Neto", "lower_better": False, "sector_val": 0.10, "market_val": 0.10, "fmt": "percent"},
            {"key": "operating_margin", "name": "Margen Operativo", "lower_better": False, "sector_val": 0.12, "market_val": 0.12, "fmt": "percent"},
            {"key": "debt_to_equity", "name": "Deuda/Equity", "lower_better": True, "sector_val": 0.80, "market_val": 0.80, "fmt": "multiple"},
            {"key": "current_ratio", "name": "Current Ratio", "lower_better": False, "sector_val": 1.5, "market_val": 1.5, "fmt": "multiple"},
        ]


# =============================================================================
# LAYOUT PRINCIPAL
# =============================================================================

app.layout = dbc.Container([
    dcc.Store(id="analysis-data", storage_type="memory"),
    dcc.Store(id="current-symbol", data="", storage_type="memory"),
    
    # Loading indicator (NO fullscreen para no bloquear sugerencias)
    html.Div(id="loading-trigger", style={"display": "none"}),
    
    # =========================================================================
    # NAVBAR PERSISTENTE CON BÚSQUEDA
    # =========================================================================
    html.Div([
        dbc.Row([
            # Logo/Home
            dbc.Col([
                html.Div([
                    html.Span("📊", style={"fontSize": "1.5rem", "marginRight": "10px"}),
                    html.Span("Stock Analyzer", style={
                        "fontSize": "1.3rem", "fontWeight": "700", "cursor": "pointer",
                        "background": "linear-gradient(135deg, #60a5fa 0%, #a78bfa 100%)",
                        "WebkitBackgroundClip": "text", "WebkitTextFillColor": "transparent"
                    })
                ], id="logo-home", style={"display": "flex", "alignItems": "center", "cursor": "pointer"})
            ], xs=12, md=3, className="mb-2 mb-md-0"),
            
            # Barra de búsqueda con contenedor relativo para el dropdown
            dbc.Col([
                html.Div([
                    # Contenedor del input y botón
                    html.Div([
                        dcc.Input(
                            id="navbar-search-input", 
                            type="text",
                            placeholder="Buscar: AAPL, Microsoft, Tesla...",
                            debounce=False,  # Actualiza con cada tecla
                            value="",
                            n_submit=0,
                            style={
                                "width": "calc(100% - 50px)",
                                "borderRadius": "10px 0 0 10px", 
                                "backgroundColor": "#18181b", 
                                "border": "1px solid #3f3f46", 
                                "borderRight": "none",
                                "color": "#fff",
                                "padding": "10px 14px",
                                "fontSize": "0.9rem",
                                "outline": "none",
                                "display": "inline-block",
                                "verticalAlign": "middle"
                            }
                        ),
                        html.Button("🔍", id="navbar-search-btn", n_clicks=0, style={
                            "width": "50px",
                            "borderRadius": "0 10px 10px 0", 
                            "padding": "10px 0",
                            "backgroundColor": "#6366f1",
                            "border": "1px solid #6366f1",
                            "color": "#fff",
                            "cursor": "pointer",
                            "fontSize": "1rem",
                            "display": "inline-block",
                            "verticalAlign": "middle"
                        })
                    ], style={"display": "flex", "alignItems": "center"}),
                    
                    # Dropdown de sugerencias
                    html.Div(id="navbar-search-suggestions", style={"display": "none"})
                    
                ], style={"position": "relative"})
            ], xs=12, md=6),
            
            # Símbolo actual (solo visible en análisis)
            dbc.Col([
                html.Div(id="current-stock-badge", style={"textAlign": "right"})
            ], xs=12, md=3, className="d-none d-md-block")
        ], className="align-items-center")
    ], id="navbar-container", style={
        "padding": "15px 20px",
        "marginTop": "10px",
        "marginBottom": "10px",
        "background": "rgba(9, 9, 11, 0.98)",
        "borderBottom": "1px solid rgba(63, 63, 70, 0.5)",
        "position": "relative",
        "zIndex": "100"
    }),
    
    # =========================================================================
    # VISTA HOME
    # =========================================================================
    html.Div(id="home-view", children=[
        # Hero Section - Centrada
        html.Div([
            # Logo
            html.Div([
                html.Span("📊", style={"fontSize": "2.5rem"})
            ], style={
                "width": "80px", "height": "80px",
                "background": "linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%)",
                "borderRadius": "20px", "display": "flex",
                "alignItems": "center", "justifyContent": "center",
                "margin": "0 auto 25px auto",
                "boxShadow": "0 15px 50px rgba(99, 102, 241, 0.4)"
            }),
            
            # Título
            html.H1("Stock Analyzer", style={
                "fontSize": "3rem", "fontWeight": "800",
                "background": "linear-gradient(135deg, #60a5fa 0%, #a78bfa 100%)",
                "WebkitBackgroundClip": "text", "WebkitTextFillColor": "transparent",
                "backgroundClip": "text", "marginBottom": "12px", "letterSpacing": "-0.02em"
            }),
            
            # Subtítulo
            html.P("Análisis fundamental de acciones para decisiones de inversión informadas",
                  style={"color": "#a1a1aa", "fontSize": "1.1rem", "marginBottom": "30px"}),
            
            # Quick Pills
            html.Div([
                dbc.Button(ticker, id={"type": "quick-pick", "index": ticker},
                          style={
                              "background": "rgba(99, 102, 241, 0.15)",
                              "border": "1px solid rgba(99, 102, 241, 0.4)",
                              "color": "#a5b4fc", "borderRadius": "25px",
                              "padding": "8px 20px", "margin": "5px",
                              "fontWeight": "500", "fontSize": "0.9rem"
                          })
                for ticker in QUICK_PICKS
            ], style={"textAlign": "center", "marginBottom": "40px"}),
            
        ], style={
            "textAlign": "center", "padding": "60px 20px",
            "maxWidth": "700px", "margin": "0 auto"
        }),
        
        html.Div(id="error-message"),
        
        # Features Row
        html.Div([
            html.Div([
                # Feature 1
                html.Div([
                    html.Div("🎯", style={"fontSize": "1.8rem", "marginBottom": "10px"}),
                    html.H6("40+ Métricas", style={"color": "#fff", "marginBottom": "5px", "fontWeight": "600"}),
                    html.P("Ratios financieros, valoración y solidez", 
                          style={"color": "#71717a", "fontSize": "0.8rem", "margin": "0"})
                ], style={"flex": "1", "textAlign": "center", "padding": "10px 15px", "minWidth": "150px"}),
                
                # Divider
                html.Div(style={"width": "1px", "background": "#3f3f46", "margin": "10px 0"}),
                
                # Feature 2
                html.Div([
                    html.Div("📊", style={"fontSize": "1.8rem", "marginBottom": "10px"}),
                    html.H6("Score 0-100", style={"color": "#fff", "marginBottom": "5px", "fontWeight": "600"}),
                    html.P("Evaluación con Z-Score y F-Score", 
                          style={"color": "#71717a", "fontSize": "0.8rem", "margin": "0"})
                ], style={"flex": "1", "textAlign": "center", "padding": "10px 15px", "minWidth": "150px"}),
                
                # Divider
                html.Div(style={"width": "1px", "background": "#3f3f46", "margin": "10px 0"}),
                
                # Feature 3
                html.Div([
                    html.Div("⚖️", style={"fontSize": "1.8rem", "marginBottom": "10px"}),
                    html.H6("Comparativa", style={"color": "#fff", "marginBottom": "5px", "fontWeight": "600"}),
                    html.P("Benchmark vs Sector y S&P 500", 
                          style={"color": "#71717a", "fontSize": "0.8rem", "margin": "0"})
                ], style={"flex": "1", "textAlign": "center", "padding": "10px 15px", "minWidth": "150px"}),
                
                # Divider
                html.Div(style={"width": "1px", "background": "#3f3f46", "margin": "10px 0"}),
                
                # Feature 4
                html.Div([
                    html.Div("💰", style={"fontSize": "1.8rem", "marginBottom": "10px"}),
                    html.H6("Valor Intrínseco", style={"color": "#fff", "marginBottom": "5px", "fontWeight": "600"}),
                    html.P("Métodos Graham y DCF", 
                          style={"color": "#71717a", "fontSize": "0.8rem", "margin": "0"})
                ], style={"flex": "1", "textAlign": "center", "padding": "10px 15px", "minWidth": "150px"}),
                
            ], style={
                "display": "flex", "justifyContent": "center", "alignItems": "stretch",
                "background": "rgba(24, 24, 27, 0.8)", "border": "1px solid rgba(63, 63, 70, 0.5)",
                "borderRadius": "16px", "padding": "20px", "flexWrap": "wrap"
            })
        ], style={"maxWidth": "900px", "margin": "0 auto 40px auto", "padding": "0 20px"}),
        
        # Disclaimer
        html.Div([
            html.P([
                html.Span("⚠️ "),
                "Esta herramienta es para fines educativos. No constituye asesoría financiera."
            ], style={
                "color": "#a1a1aa", "fontSize": "0.85rem", "margin": "0",
                "padding": "12px 24px", "background": "rgba(234, 179, 8, 0.1)",
                "border": "1px solid rgba(234, 179, 8, 0.25)", "borderRadius": "10px",
                "display": "inline-block"
            })
        ], style={"textAlign": "center", "paddingBottom": "40px"})
    ]),
    
    # =========================================================================
    # VISTA ANÁLISIS
    # =========================================================================
    html.Div(id="analysis-view", style={"display": "none"}, children=[
        html.Div(id="company-header"),
        
        dbc.Row([
            dbc.Col([html.Div(id="score-card-container", className="score-card")], xs=12, md=4, lg=3, className="mb-3"),
            dbc.Col([html.Div(id="key-metrics-container")], xs=12, md=8, lg=9)
        ]),
        
        html.Div(id="sector-notes-container", className="mb-4"),
        html.Hr(),
        
        dbc.Tabs([
            dbc.Tab(html.Div(id="tab-valuation-content"), label="📊 Valoración", tab_id="tab-valuation"),
            dbc.Tab(html.Div(id="tab-profitability-content"), label="💰 Rentabilidad", tab_id="tab-profitability"),
            dbc.Tab(html.Div(id="tab-health-content"), label="🏦 Solidez", tab_id="tab-health"),
            dbc.Tab(html.Div(id="tab-historical-content"), label="📈 Histórico", tab_id="tab-historical"),
            dbc.Tab(html.Div(id="tab-comparison-content"), label="⚖️ Comparativa", tab_id="tab-comparison"),
            dbc.Tab(html.Div(id="tab-intrinsic-content"), label="🎯 Valor Intrínseco", tab_id="tab-intrinsic"),
            dbc.Tab(html.Div(id="tab-evaluation-content"), label="📋 Evaluación", tab_id="tab-evaluation"),
        ], id="analysis-tabs", active_tab="tab-valuation", className="mb-3"),
        
        html.Hr(),
        html.P(id="analysis-footer", className="text-center small text-muted")
    ]),
    
], fluid=True, className="fade-in")


# =============================================================================
# CALLBACKS
# =============================================================================

# Callback para sugerencias de búsqueda (se activa con cada tecla)
@callback(
    Output("navbar-search-suggestions", "children"),
    Output("navbar-search-suggestions", "style"),
    Input("navbar-search-input", "value"),
    prevent_initial_call=True
)
def update_search_suggestions(search_value):
    """Muestra sugerencias mientras el usuario escribe."""
    
    # Estilos base del dropdown
    dropdown_base = {
        "position": "absolute",
        "top": "100%",
        "left": "0",
        "right": "0",
        "marginTop": "4px",
        "background": "#1f1f23",
        "border": "1px solid rgba(99, 102, 241, 0.5)",
        "borderRadius": "10px",
        "boxShadow": "0 8px 32px rgba(0, 0, 0, 0.7)",
        "zIndex": "9999",
        "maxHeight": "300px",
        "overflowY": "auto"
    }
    
    hidden_style = {**dropdown_base, "display": "none"}
    visible_style = {**dropdown_base, "display": "block"}
    
    # Si no hay valor o es muy corto, ocultar
    if not search_value or len(str(search_value).strip()) < 1:
        return [], hidden_style
    
    query = str(search_value).strip()
    
    # Buscar sugerencias
    suggestions = search_stocks(query, limit=6)
    
    if not suggestions:
        return [html.P("No se encontraron resultados", style={
            "color": "#71717a", "padding": "12px 16px", "margin": "0", "textAlign": "center", "fontSize": "0.9rem"
        })], visible_style
    
    # Crear items de sugerencias clickeables
    suggestion_items = []
    for i, (ticker, name, _) in enumerate(suggestions):
        is_last = i == len(suggestions) - 1
        suggestion_items.append(
            html.Div([
                html.Span(ticker, style={
                    "color": "#60a5fa", "fontWeight": "700", "fontSize": "0.95rem",
                    "marginRight": "12px", "minWidth": "60px", "display": "inline-block"
                }),
                html.Span(name[:35] + ("..." if len(name) > 35 else ""), style={
                    "color": "#d4d4d8", "fontSize": "0.85rem"
                })
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


# Callback principal de navegación (SOLO se activa con click o Enter)
@callback(
    Output("home-view", "style"),
    Output("analysis-view", "style"),
    Output("company-header", "children"),
    Output("score-card-container", "children"),
    Output("key-metrics-container", "children"),
    Output("sector-notes-container", "children"),
    Output("tab-valuation-content", "children"),
    Output("tab-profitability-content", "children"),
    Output("tab-health-content", "children"),
    Output("tab-historical-content", "children"),
    Output("tab-comparison-content", "children"),
    Output("tab-intrinsic-content", "children"),
    Output("tab-evaluation-content", "children"),
    Output("analysis-footer", "children"),
    Output("analysis-data", "data"),
    Output("current-symbol", "data"),
    Output("error-message", "children"),
    Output("loading-trigger", "children"),
    Output("current-stock-badge", "children"),
    Output("navbar-search-input", "value"),
    Output("navbar-search-suggestions", "style", allow_duplicate=True),
    Input("navbar-search-btn", "n_clicks"),
    Input("navbar-search-input", "n_submit"),
    Input("logo-home", "n_clicks"),
    Input({"type": "quick-pick", "index": ALL}, "n_clicks"),
    Input({"type": "suggestion-item", "index": ALL}, "n_clicks"),
    State("navbar-search-input", "value"),
    State("analysis-data", "data"),
    prevent_initial_call=True
)
def handle_navigation(search_btn, search_submit, logo_clicks, quick_picks, suggestion_clicks, search_value, stored_data):
    triggered_id = ctx.triggered_id
    triggered_prop = ctx.triggered[0]["prop_id"] if ctx.triggered else ""
    
    home_style = {"display": "block"}
    analysis_style = {"display": "none"}
    empty_outputs = [None] * 13
    
    # Estilo para ocultar sugerencias
    hide_suggestions = {
        "position": "absolute",
        "top": "100%",
        "left": "0",
        "right": "0",
        "marginTop": "4px",
        "background": "#1a1a1f",
        "border": "1px solid rgba(99, 102, 241, 0.4)",
        "borderRadius": "10px",
        "boxShadow": "0 8px 32px rgba(0, 0, 0, 0.6)",
        "zIndex": "9999",
        "maxHeight": "280px",
        "overflowY": "auto",
        "display": "none"
    }
    
    # Si no hay triggered_id o es None, no hacer nada
    if not triggered_id:
        return no_update
    
    # Verificar el valor del trigger (debe ser > 0 para ser un click real)
    triggered_value = ctx.triggered[0]["value"] if ctx.triggered else None
    
    # Regresar al home
    if triggered_id == "logo-home":
        if logo_clicks and logo_clicks > 0:
            return home_style, analysis_style, *empty_outputs, None, "", None, None, None, "", hide_suggestions
        return no_update
    
    symbol = None
    
    # CASO 1: Click en botón de búsqueda
    if triggered_id == "navbar-search-btn":
        if search_btn and search_btn > 0 and search_value:
            symbol = resolve_symbol(search_value.strip())
        else:
            return no_update
    
    # CASO 2: Enter en el input (n_submit incrementa)
    elif triggered_id == "navbar-search-input":
        # n_submit solo se dispara con Enter, y value cambia con cada tecla
        # Si triggered_value es un entero > 0, fue Enter
        if isinstance(triggered_value, int) and triggered_value > 0 and search_value:
            symbol = resolve_symbol(search_value.strip())
        else:
            # Fue un cambio de valor (escribiendo), ignorar
            return no_update
    
    # CASO 3: Quick pick
    elif isinstance(triggered_id, dict) and triggered_id.get("type") == "quick-pick":
        if triggered_value and triggered_value > 0:
            symbol = triggered_id.get("index")
        else:
            return no_update
    
    # CASO 4: Click en sugerencia
    elif isinstance(triggered_id, dict) and triggered_id.get("type") == "suggestion-item":
        # triggered_value es el n_clicks del elemento clickeado
        if triggered_value and triggered_value > 0:
            symbol = triggered_id.get("index")
        else:
            # n_clicks = 0 significa que el elemento se acaba de crear, no un click real
            return no_update
    
    # Si no hay símbolo válido, no hacer nada
    if not symbol:
        return no_update
    
    try:
        service = FinancialDataService()
        data = service.get_complete_analysis_data(symbol)
        
        if not data.get("financials"):
            error_msg = dbc.Alert(f"❌ No se encontraron datos para '{symbol}'. Verifica el símbolo.",
                                 color="danger", dismissable=True)
            return home_style, analysis_style, *empty_outputs, None, "", error_msg, None, None, "", hide_suggestions
        
        profile = data.get("profile")
        financials = data.get("financials")
        contextual = data.get("contextual", {})
        
        fin_dict = service.financials_to_dict(financials)
        ratios = calculate_all_ratios(fin_dict)
        
        # Mapeo completo de sectores (Yahoo Finance -> SECTOR_THRESHOLDS keys)
        sector_map = {
            "Technology": "technology",
            "Financial Services": "financials",
            "Healthcare": "healthcare",
            "Utilities": "utilities",
            "Consumer Cyclical": "consumer_discretionary",
            "Consumer Defensive": "consumer_staples",
            "Energy": "energy",
            "Real Estate": "real_estate",
            "Industrials": "industrials",
            "Basic Materials": "materials",
            "Communication Services": "communication_services",
        }
        sector_key = sector_map.get(profile.sector if profile else "", "default")
        contextual["pe_5y_avg"] = ratios.get("pe")
        alerts = aggregate_alerts(ratios, contextual, sector_key)
        sector_profile = get_sector_profile(profile.sector if profile else None)
        
        company_name = profile.name if profile else symbol
        company_sector = profile.sector if profile else "N/A"
        company_industry = profile.industry if profile else "N/A"
        current_price = f"${financials.price:.2f}" if financials and financials.price else "N/A"
        
        score = alerts.get("score", 0)
        score_color, score_label = get_score_color(score)
        score_v2 = alerts.get("score_v2", {})
        
        # Badge del stock actual para navbar
        stock_badge = html.Div([
            html.Span(symbol, style={"color": "#3b82f6", "fontWeight": "700", "fontSize": "1.1rem"}),
            html.Span(f" · {current_price}", className="text-muted")
        ])
        
        # Company Header
        company_header = html.Div([
            dbc.Row([
                dbc.Col([
                    html.H2(company_name, className="mb-1", style={"fontWeight": "700"}),
                    html.P([
                        html.Span("📁 ", className="text-muted"),
                        html.Span(company_sector, className="text-secondary"),
                        html.Span(" · ", className="text-muted"),
                        html.Span("🏭 ", className="text-muted"),
                        html.Span(company_industry, className="text-secondary"),
                    ], className="mb-0 small")
                ], xs=12, md=8),
                dbc.Col([
                    html.Div([
                        html.H3(current_price, className="text-info mb-0", style={"fontWeight": "700"}),
                        html.Small("Precio actual", className="text-muted")
                    ], className="text-md-end")
                ], xs=12, md=4)
            ])
        ], className="company-header-card")
        
        # Score Card
        score_card = html.Div([
            dcc.Graph(figure=create_score_donut(score), config={'displayModeBar': False}, style={"height": "180px"}),
            html.Div([
                html.Span("🚀 Growth", className="badge bg-primary me-2") if score_v2.get("is_growth_company") else None,
                html.Span(score_v2.get("level", ""), className="badge",
                    style={"backgroundColor": f"{score_v2.get('level_color', '#71717a')}22",
                           "color": score_v2.get('level_color', '#71717a'),
                           "border": f"1px solid {score_v2.get('level_color', '#71717a')}"})
                if score_v2.get("level") else None
            ], className="text-center mt-2")
        ])
        
        # Key Metrics
        key_metrics = html.Div([
            html.H5("📊 Métricas Clave", className="mb-3"),
            dbc.Row([
                dbc.Col([create_metric_card("Market Cap", format_ratio(ratios.get("market_cap"), "currency"), "🌐")], xs=6, md=3, className="mb-2"),
                dbc.Col([create_metric_card("P/E", format_ratio(ratios.get("pe"), "multiple"), "📊")], xs=6, md=3, className="mb-2"),
                dbc.Col([create_metric_card("ROE", format_ratio(ratios.get("roe"), "percent"), "🎯")], xs=6, md=3, className="mb-2"),
                dbc.Col([create_metric_card("D/E", format_ratio(ratios.get("debt_to_equity"), "multiple"), "⚖️")], xs=6, md=3, className="mb-2"),
            ]),
            dbc.Row([
                dbc.Col([create_metric_card("Margen Neto", format_ratio(ratios.get("net_margin"), "percent"), "💎")], xs=6, md=3, className="mb-2"),
                dbc.Col([create_metric_card("FCF Yield", format_ratio(ratios.get("fcf_yield"), "percent"), "💸")], xs=6, md=3, className="mb-2"),
                dbc.Col([create_metric_card("EV/EBITDA", format_ratio(ratios.get("ev_ebitda"), "multiple"), "🏢")], xs=6, md=3, className="mb-2"),
                dbc.Col([create_metric_card("Beta", f"{financials.beta:.2f}" if financials and financials.beta else "N/A", "📉")], xs=6, md=3, className="mb-2"),
            ])
        ])
        
        # Sector Notes
        sector_notes = html.Details([
            html.Summary(f"📋 Notas para sector {sector_profile.display_name}", className="text-muted"),
            html.Div([
                html.P([html.Span("ETF de referencia: ", className="text-muted"),
                       html.Span(sector_profile.sector_etf, className="text-info")], className="mb-2 small"),
                html.Ul([html.Li(note, className="small") for note in sector_profile.sector_notes])
            ], className="mt-2")
        ]) if sector_profile.sector_notes else None
        
        # Tab Valoración
        tab_valuation = html.Div([
            html.H5("Métricas de Valoración", className="mb-2"),
            html.P("¿Está cara o barata la acción? · Datos TTM", className="text-muted small mb-3"),
            dbc.Row([
                dbc.Col([create_metric_card("P/E Ratio", format_ratio(ratios.get("pe"), "multiple"), "📊")], xs=6, md=3, className="mb-3"),
                dbc.Col([create_metric_card("Forward P/E", format_ratio(ratios.get("forward_pe"), "multiple"), "🔮")], xs=6, md=3, className="mb-3"),
                dbc.Col([create_metric_card("P/B Ratio", format_ratio(ratios.get("pb"), "multiple"), "📚")], xs=6, md=3, className="mb-3"),
                dbc.Col([create_metric_card("P/S Ratio", format_ratio(ratios.get("ps"), "multiple"), "💰")], xs=6, md=3, className="mb-3"),
            ]),
            dbc.Row([
                dbc.Col([create_metric_card("EV/EBITDA", format_ratio(ratios.get("ev_ebitda"), "multiple"), "🏢")], xs=6, md=3, className="mb-3"),
                dbc.Col([create_metric_card("P/FCF", format_ratio(ratios.get("p_fcf"), "multiple"), "💵")], xs=6, md=3, className="mb-3"),
                dbc.Col([create_metric_card("PEG Ratio", format_ratio(ratios.get("peg"), "decimal"), "📈")], xs=6, md=3, className="mb-3"),
                dbc.Col([create_metric_card("FCF Yield", format_ratio(ratios.get("fcf_yield"), "percent"), "💸")], xs=6, md=3, className="mb-3"),
            ])
        ])
        
        # Tab Rentabilidad
        tab_profitability = html.Div([
            html.H5("Métricas de Rentabilidad", className="mb-2"),
            html.P("¿Qué tan eficiente es generando ganancias?", className="text-muted small mb-4"),
            
            # Fila 1: Retornos
            html.H6("🎯 Retornos sobre Capital", className="mb-3"),
            dbc.Row([
                dbc.Col([create_metric_card("ROE", format_ratio(ratios.get("roe"), "percent"), "🎯")], xs=6, md=3, className="mb-3"),
                dbc.Col([create_metric_card("ROA", format_ratio(ratios.get("roa"), "percent"), "🏭")], xs=6, md=3, className="mb-3"),
                dbc.Col([create_metric_card("ROIC", format_ratio(ratios.get("roic"), "percent"), "💎")], xs=6, md=3, className="mb-3"),
                dbc.Col([create_metric_card("ROE 5Y Avg", format_ratio(ratios.get("roe_5y_avg"), "percent"), "📊")], xs=6, md=3, className="mb-3"),
            ], className="mb-3"),
            
            html.Hr(style={"borderColor": "#27272a"}),
            
            # Fila 2: Márgenes
            html.H6("📊 Márgenes de Ganancia", className="mb-3 mt-3"),
            dbc.Row([
                dbc.Col([create_metric_card("Margen Bruto", format_ratio(ratios.get("gross_margin"), "percent"), "📦")], xs=6, md=3, className="mb-3"),
                dbc.Col([create_metric_card("Margen Operativo", format_ratio(ratios.get("operating_margin"), "percent"), "⚙️")], xs=6, md=3, className="mb-3"),
                dbc.Col([create_metric_card("Margen Neto", format_ratio(ratios.get("net_margin"), "percent"), "💎")], xs=6, md=3, className="mb-3"),
                dbc.Col([create_metric_card("Margen EBITDA", format_ratio(ratios.get("ebitda_margin"), "percent"), "📈")], xs=6, md=3, className="mb-3"),
            ], className="mb-3"),
            
            html.Hr(style={"borderColor": "#27272a"}),
            
            # Fila 3: Resultado
            html.H6("💰 Resultados Absolutos", className="mb-3 mt-3"),
            dbc.Row([
                dbc.Col([create_metric_card("EBITDA", format_ratio(ratios.get("ebitda"), "currency"), "📊")], xs=6, md=4, className="mb-3"),
                dbc.Col([create_metric_card("Ingreso Neto", format_ratio(ratios.get("net_income"), "currency"), "💵")], xs=6, md=4, className="mb-3"),
                dbc.Col([create_metric_card("EPS", format_ratio(ratios.get("eps"), "decimal"), "📈")], xs=6, md=4, className="mb-3"),
            ])
        ])
        
        # Tab Solidez
        tab_health = html.Div([
            html.H5("Solidez Financiera", className="mb-2"),
            html.P("¿Puede pagar sus deudas y mantener operaciones?", className="text-muted small mb-4"),
            
            # Fila 1: Liquidez
            html.H6("💧 Liquidez (Corto Plazo)", className="mb-3"),
            dbc.Row([
                dbc.Col([create_metric_card("Current Ratio", format_ratio(ratios.get("current_ratio"), "multiple"), "💧")], xs=6, md=3, className="mb-3"),
                dbc.Col([create_metric_card("Quick Ratio", format_ratio(ratios.get("quick_ratio"), "multiple"), "⚡")], xs=6, md=3, className="mb-3"),
                dbc.Col([create_metric_card("Cash Ratio", format_ratio(ratios.get("cash_ratio"), "multiple"), "💵")], xs=6, md=3, className="mb-3"),
                dbc.Col([create_metric_card("Working Capital", format_ratio(ratios.get("working_capital"), "currency"), "📊")], xs=6, md=3, className="mb-3"),
            ], className="mb-3"),
            
            html.Hr(style={"borderColor": "#27272a"}),
            
            # Fila 2: Apalancamiento
            html.H6("⚖️ Apalancamiento (Largo Plazo)", className="mb-3 mt-3"),
            dbc.Row([
                dbc.Col([create_metric_card("Deuda/Equity", format_ratio(ratios.get("debt_to_equity"), "multiple"), "⚖️")], xs=6, md=3, className="mb-3"),
                dbc.Col([create_metric_card("Deuda/Activos", format_ratio(ratios.get("debt_to_assets"), "percent"), "📉")], xs=6, md=3, className="mb-3"),
                dbc.Col([create_metric_card("Deuda Neta/EBITDA", format_ratio(ratios.get("net_debt_to_ebitda"), "multiple"), "🔗")], xs=6, md=3, className="mb-3"),
                dbc.Col([create_metric_card("Deuda Total", format_ratio(ratios.get("total_debt"), "currency"), "💳")], xs=6, md=3, className="mb-3"),
            ], className="mb-3"),
            
            html.Hr(style={"borderColor": "#27272a"}),
            
            # Fila 3: Cobertura y Flujo
            html.H6("🛡️ Cobertura y Flujo de Caja", className="mb-3 mt-3"),
            dbc.Row([
                dbc.Col([create_metric_card("Cobertura Int.", format_ratio(ratios.get("interest_coverage"), "multiple"), "🛡️")], xs=6, md=3, className="mb-3"),
                dbc.Col([create_metric_card("FCF", format_ratio(ratios.get("fcf"), "currency"), "💵")], xs=6, md=3, className="mb-3"),
                dbc.Col([create_metric_card("FCF/Deuda", format_ratio(ratios.get("fcf_to_debt"), "percent"), "📈")], xs=6, md=3, className="mb-3"),
                dbc.Col([create_metric_card("Cash & Eq.", format_ratio(ratios.get("cash_and_equivalents"), "currency"), "🏦")], xs=6, md=3, className="mb-3"),
            ])
        ])
        
        # Tab Histórico
        price_chart = create_price_chart(symbol, "1y")
        
        # Obtener datos de 52 semanas
        try:
            import yfinance as yf
            ticker_info = yf.Ticker(symbol).info
            week_high = ticker_info.get("fiftyTwoWeekHigh")
            week_low = ticker_info.get("fiftyTwoWeekLow")
            avg_volume = ticker_info.get("averageVolume")
        except:
            week_high, week_low, avg_volume = None, None, None
        
        tab_historical = html.Div([
            html.H5("Histórico de Precio", className="mb-2"),
            html.P("Evolución del precio de la acción", className="text-muted small mb-3"),
            
            # Selector de periodo
            html.Div([
                dbc.ButtonGroup([
                    dbc.Button("1M", id="period-1mo", color="secondary", size="sm", outline=True, className="period-btn"),
                    dbc.Button("3M", id="period-3mo", color="secondary", size="sm", outline=True, className="period-btn"),
                    dbc.Button("6M", id="period-6mo", color="secondary", size="sm", outline=True, className="period-btn"),
                    dbc.Button("1Y", id="period-1y", color="primary", size="sm", className="period-btn"),
                    dbc.Button("5Y", id="period-5y", color="secondary", size="sm", outline=True, className="period-btn"),
                ], className="mb-3")
            ], className="text-center mb-3"),
            
            # Gráfico principal (default 1Y)
            html.Div(id="price-chart-container", children=[
                dcc.Graph(figure=price_chart, config={'displayModeBar': False}, id="price-chart") if price_chart else 
                    html.Div([html.P("📈 No se pudieron cargar los datos", className="text-muted text-center py-5")])
            ]),
            
            # Gráficos adicionales para otros periodos (hidden, se cargan en callbacks)
            dcc.Store(id="chart-1mo", data=None),
            dcc.Store(id="chart-3mo", data=None),
            dcc.Store(id="chart-6mo", data=None),
            dcc.Store(id="chart-5y", data=None),
            
            html.Hr(),
            
            # Métricas de rendimiento
            html.H6("📊 Rendimiento 52 Semanas", className="mb-3"),
            dbc.Row([
                dbc.Col([create_metric_card("52W High", f"${week_high:.2f}" if week_high else "N/A", "📈")], xs=6, md=3, className="mb-3"),
                dbc.Col([create_metric_card("52W Low", f"${week_low:.2f}" if week_low else "N/A", "📉")], xs=6, md=3, className="mb-3"),
                dbc.Col([create_metric_card("Beta", f"{financials.beta:.2f}" if financials and financials.beta else "N/A", "📊")], xs=6, md=3, className="mb-3"),
                dbc.Col([create_metric_card("Vol. Promedio", f"{avg_volume/1e6:.1f}M" if avg_volume else "N/A", "📶")], xs=6, md=3, className="mb-3"),
            ]),
            
            # Posición actual
            html.Hr(),
            html.H6("📍 Posición Actual", className="mb-3"),
            html.Div([
                html.P([
                    f"Precio actual ${financials.price:.2f}" if financials and financials.price else "N/A",
                    html.Span(" · ", className="text-muted"),
                    f"{((financials.price - week_low) / (week_high - week_low) * 100):.0f}% del rango 52W" if week_high and week_low and financials and financials.price else ""
                ], className="text-muted mb-2") if week_high and week_low else None,
                dbc.Progress(
                    value=((financials.price - week_low) / (week_high - week_low) * 100) if week_high and week_low and financials and financials.price and (week_high - week_low) > 0 else 50,
                    style={"height": "10px"}, className="mb-2"
                ) if week_high and week_low else None
            ])
        ])
        
        # Tab Comparativa - COMPLETA
        try:
            import yfinance as yf
            from datetime import datetime
            
            current_year = datetime.now().year
            ytd_start = f"{current_year}-01-01"
            
            # YTD de la empresa
            ticker_hist = yf.Ticker(symbol).history(start=ytd_start)
            stock_ytd = ((ticker_hist['Close'].iloc[-1] / ticker_hist['Close'].iloc[0]) - 1) * 100 if not ticker_hist.empty else 0
            
            # YTD del mercado (SPY)
            spy_hist = yf.Ticker("SPY").history(start=ytd_start)
            market_ytd = ((spy_hist['Close'].iloc[-1] / spy_hist['Close'].iloc[0]) - 1) * 100 if not spy_hist.empty else 0
            
            # YTD del sector
            sector_etf = sector_profile.sector_etf if sector_profile else "XLK"
            sector_hist = yf.Ticker(sector_etf).history(start=ytd_start)
            sector_ytd = ((sector_hist['Close'].iloc[-1] / sector_hist['Close'].iloc[0]) - 1) * 100 if not sector_hist.empty else 0
            
        except Exception as e:
            print(f"Error YTD: {e}")
            stock_ytd, market_ytd, sector_ytd = 0, 0, 0
        
        diff_vs_market = stock_ytd - market_ytd
        diff_vs_sector = stock_ytd - sector_ytd
        
        # Mensaje de análisis
        if diff_vs_market > 10:
            perf_msg = f"🚀 {symbol} está superando al mercado por {diff_vs_market:.1f} puntos"
            perf_color = "#22c55e"
        elif diff_vs_market > 0:
            perf_msg = f"✅ {symbol} está ligeramente por encima del mercado (+{diff_vs_market:.1f}%)"
            perf_color = "#4ade80"
        elif diff_vs_market > -10:
            perf_msg = f"⚠️ {symbol} está ligeramente por debajo del mercado ({diff_vs_market:.1f}%)"
            perf_color = "#eab308"
        else:
            perf_msg = f"🔴 {symbol} está rezagado vs el mercado por {abs(diff_vs_market):.1f} puntos"
            perf_color = "#ef4444"
        
        # Tabla de métricas comparativas
        metrics_config = get_sector_metrics_config(company_sector)
        comparison_rows = []
        for m in metrics_config:
            company_val = ratios.get(m["key"])
            comparison_rows.append(
                create_comparison_metric_row(m["name"], company_val, m["sector_val"], m["market_val"], m["fmt"], m["lower_better"])
            )
        
        tab_comparison = html.Div([
            html.H5("🔄 Comparativa de Mercado", className="mb-2"),
            html.P("Comparación vs Sector y S&P 500", className="text-muted small mb-3"),
            
            html.Div([
                html.P([
                    html.Strong("¿Qué compara esta sección? "),
                    f"Comparamos {symbol} contra: ",
                    html.Span(f"{sector_profile.sector_etf if sector_profile else 'ETF'}", className="text-success"),
                    " (Sector) y ",
                    html.Span("SPY", className="text-warning"),
                    " (Mercado)"
                ], className="small")
            ], className="alert-info-custom alert-box mb-4"),
            
            # YTD Cards
            html.H6("📊 Rendimiento YTD (Year-to-Date)", className="mb-3"),
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.Div(f"📌 {symbol}", style={"color": "#3b82f6", "fontWeight": "600", "fontSize": "0.9rem"}),
                        html.Div("EMPRESA", style={"color": "#71717a", "fontSize": "0.7rem", "marginTop": "4px"}),
                        html.Div(f"{stock_ytd:+.1f}%", style={
                            "color": "#22c55e" if stock_ytd > 0 else "#ef4444",
                            "fontSize": "1.8rem", "fontWeight": "700", "marginTop": "8px"
                        })
                    ], style={"textAlign": "center", "padding": "20px", "background": "linear-gradient(145deg, #18181b, #1f1f23)",
                             "border": "1px solid rgba(59, 130, 246, 0.5)", "borderRadius": "12px"})
                ], xs=12, md=4, className="mb-3"),
                dbc.Col([
                    html.Div([
                        html.Div(f"📊 vs {sector_profile.sector_etf if sector_profile else 'Sector'}", style={"color": "#22c55e", "fontWeight": "600", "fontSize": "0.9rem"}),
                        html.Div("VS SECTOR", style={"color": "#71717a", "fontSize": "0.7rem", "marginTop": "4px"}),
                        html.Div(f"{diff_vs_sector:+.1f}%", style={
                            "color": "#22c55e" if diff_vs_sector >= 0 else "#ef4444",
                            "fontSize": "1.8rem", "fontWeight": "700", "marginTop": "8px"
                        })
                    ], style={"textAlign": "center", "padding": "20px", "background": "linear-gradient(145deg, #18181b, #1f1f23)",
                             "border": "1px solid rgba(34, 197, 94, 0.5)", "borderRadius": "12px"})
                ], xs=12, md=4, className="mb-3"),
                dbc.Col([
                    html.Div([
                        html.Div("🌐 vs SPY", style={"color": "#eab308", "fontWeight": "600", "fontSize": "0.9rem"}),
                        html.Div("VS MERCADO", style={"color": "#71717a", "fontSize": "0.7rem", "marginTop": "4px"}),
                        html.Div(f"{diff_vs_market:+.1f}%", style={
                            "color": "#22c55e" if diff_vs_market >= 0 else "#ef4444",
                            "fontSize": "1.8rem", "fontWeight": "700", "marginTop": "8px"
                        })
                    ], style={"textAlign": "center", "padding": "20px", "background": "linear-gradient(145deg, #18181b, #1f1f23)",
                             "border": "1px solid rgba(234, 179, 8, 0.5)", "borderRadius": "12px"})
                ], xs=12, md=4, className="mb-3"),
            ]),
            
            html.Div([html.P(perf_msg, style={"color": perf_color, "margin": "0"})],
                    style={"background": "rgba(39, 39, 42, 0.5)", "borderRadius": "8px", "padding": "12px", "textAlign": "center", "marginBottom": "20px"}),
            
            # Gráfico YTD
            dcc.Graph(figure=create_ytd_comparison_chart(stock_ytd, market_ytd, sector_ytd, symbol), config={'displayModeBar': False}),
            
            html.Hr(),
            
            # Tabla de métricas fundamentales con veredicto
            html.H6("📋 Comparación de Métricas Fundamentales", className="mb-3"),
            html.P("Comparación detallada con benchmarks del sector y mercado", className="text-muted small mb-3"),
            
            html.Div([
                html.Table([
                    html.Thead([
                        html.Tr([
                            html.Th("Métrica", style={"padding": "14px 16px", "borderBottom": "2px solid #3f3f46", "textAlign": "left", "color": "#a1a1aa", "fontSize": "0.85rem"}),
                            html.Th(symbol, style={"padding": "14px 12px", "borderBottom": "2px solid #3f3f46", "textAlign": "center", "color": "#3b82f6", "fontWeight": "700"}),
                            html.Th(f"Sector ({sector_profile.sector_etf if sector_profile else 'ETF'})", style={"padding": "14px 12px", "borderBottom": "2px solid #3f3f46", "textAlign": "center", "color": "#a1a1aa", "fontSize": "0.85rem"}),
                            html.Th("Mercado (SPY)", style={"padding": "14px 12px", "borderBottom": "2px solid #3f3f46", "textAlign": "center", "color": "#a1a1aa", "fontSize": "0.85rem"}),
                            html.Th("Veredicto", style={"padding": "14px 16px", "borderBottom": "2px solid #3f3f46", "textAlign": "center", "color": "#a1a1aa", "fontSize": "0.85rem"}),
                        ])
                    ]),
                    html.Tbody(comparison_rows)
                ], style={"width": "100%", "borderCollapse": "collapse", "background": "#18181b", "borderRadius": "12px"})
            ], style={"overflowX": "auto"}),
            
            html.Div([
                html.P([
                    html.Span("🟢 Excelente", style={"color": "#22c55e"}), " = Supera sector y mercado · ",
                    html.Span("🟡 Aceptable", style={"color": "#eab308"}), " = Supera uno de los benchmarks · ",
                    html.Span("🔴 Débil", style={"color": "#ef4444"}), " = Por debajo de ambos"
                ], className="small text-muted text-center mt-3")
            ])
        ])
        
        # Tab Valor Intrínseco
        eps = ratios.get("eps")
        total_equity = financials.total_equity if financials else None
        shares = financials.shares_outstanding if financials else None
        bvps = total_equity / shares if total_equity and shares and shares > 0 else None
        graham = graham_number(eps, bvps) if eps and bvps else None
        
        fcf = ratios.get("fcf")
        dcf_value = None
        if fcf and fcf > 0 and shares:
            dcf_value = dcf_fair_value(fcf, 0.08, 0.10, 0.025, 10, shares)
        
        price = financials.price if financials else None
        
        tab_intrinsic = html.Div([
            html.H5("Valoración Intrínseca", className="mb-2"),
            html.P("Estimación del valor real de la acción", className="text-muted small mb-3"),
            html.Div([
                html.P([html.Strong("⚠️ Nota: "), "Estos métodos son estimaciones basadas en supuestos. Úsalos como referencia."],
                      className="alert-info-custom alert-box small")
            ]),
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("📐 Método Graham"),
                        dbc.CardBody([
                            html.P("Valor intrínseco según Benjamin Graham", className="text-muted small"),
                            html.H3(f"${graham:.2f}" if graham else "N/A",
                                   className="text-success" if graham and price and graham > price else "text-danger" if graham else "text-muted"),
                            html.P([f"{((graham - price) / price * 100):+.0f}% vs precio actual" if graham and price else "Datos insuficientes"],
                                  className="small text-muted"),
                        ])
                    ], className="h-100")
                ], xs=12, md=6, className="mb-3"),
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("💵 Método DCF"),
                        dbc.CardBody([
                            html.P("Valor presente de flujos de caja (10 años)", className="text-muted small"),
                            html.H3(f"${dcf_value:.2f}" if dcf_value else "N/A",
                                   className="text-success" if dcf_value and price and dcf_value > price else "text-danger" if dcf_value else "text-muted"),
                            html.P([f"{((dcf_value - price) / price * 100):+.0f}% vs precio actual" if dcf_value and price else "Requiere FCF positivo"],
                                  className="small text-muted"),
                        ])
                    ], className="h-100")
                ], xs=12, md=6, className="mb-3"),
            ]),
            html.Hr(),
            html.H6("📊 Resumen de Valoración"),
            dbc.Row([
                dbc.Col([create_metric_card("Precio Mercado", f"${price:.2f}" if price else "N/A", "💰")], xs=4),
                dbc.Col([create_metric_card("Valor Graham", f"${graham:.2f}" if graham else "N/A", "📐")], xs=4),
                dbc.Col([create_metric_card("Valor DCF", f"${dcf_value:.2f}" if dcf_value else "N/A", "💵")], xs=4),
            ])
        ])
        
        # Tab Evaluación con RESUMEN DE PUNTUACIÓN
        categories = score_v2.get("categories", [])
        cat_scores = score_v2.get("category_scores", {})
        
        solidez = cat_scores.get("solidez", 0)
        rentabilidad = cat_scores.get("rentabilidad", 0)
        valoracion = cat_scores.get("valoracion", 0)
        calidad = cat_scores.get("calidad", 0)
        crecimiento = cat_scores.get("crecimiento", 0)
        
        # Alertas - Recolección completa de todas las fuentes
        danger_alerts, warning_alerts, success_alerts = [], [], []
        
        # Valoración
        val = alerts.get("valuation", {})
        for reason in val.get("overvalued_reasons", []):
            danger_alerts.append(("Valoración", reason))
        for reason in val.get("undervalued_reasons", []):
            success_alerts.append(("Valoración", reason))
        
        # Deuda/Apalancamiento
        lev = alerts.get("leverage", {})
        for reason in lev.get("warning_reasons", []):
            danger_alerts.append(("Deuda", reason))
        for reason in lev.get("positive_reasons", []):
            success_alerts.append(("Deuda", reason))
        
        # Rentabilidad
        prof = alerts.get("profitability", {})
        for reason in prof.get("warning_reasons", []):
            warning_alerts.append(("Rentabilidad", reason))
        for reason in prof.get("positive_reasons", []):
            success_alerts.append(("Rentabilidad", reason))
        
        # Liquidez
        liq = alerts.get("liquidity", {})
        for reason in liq.get("warning_reasons", []):
            warning_alerts.append(("Liquidez", reason))
        for reason in liq.get("positive_reasons", []):
            success_alerts.append(("Liquidez", reason))
        
        # Flujo de Caja
        cf = alerts.get("cash_flow", {})
        for reason in cf.get("warning_reasons", []):
            danger_alerts.append(("Flujo de Caja", reason))
        for reason in cf.get("positive_reasons", []):
            success_alerts.append(("Flujo de Caja", reason))
        
        # Crecimiento
        growth = alerts.get("growth", {})
        for reason in growth.get("warning_reasons", []):
            warning_alerts.append(("Crecimiento", reason))
        for reason in growth.get("positive_reasons", []):
            success_alerts.append(("Crecimiento", reason))
        
        # Volatilidad
        vol = alerts.get("volatility", {})
        for reason in vol.get("warning_reasons", []):
            warning_alerts.append(("Volatilidad", reason))
        for reason in vol.get("positive_reasons", []):
            success_alerts.append(("Volatilidad", reason))
        
        # Extraer alertas de score_v2 categories (detalles de ajustes)
        for cat in categories:
            adjustments = cat.get("adjustments", [])
            for adj in adjustments:
                if adj.get("adjustment", 0) < -2:  # Penalizaciones fuertes
                    danger_alerts.append((cat.get("category", ""), f"{adj.get('metric', '')}: {adj.get('reason', '')}"))
                elif adj.get("adjustment", 0) < 0:  # Penalizaciones leves
                    warning_alerts.append((cat.get("category", ""), f"{adj.get('metric', '')}: {adj.get('reason', '')}"))
                elif adj.get("adjustment", 0) > 2:  # Bonificaciones fuertes
                    success_alerts.append((cat.get("category", ""), f"{adj.get('metric', '')}: {adj.get('reason', '')}"))
        
        # Eliminar duplicados manteniendo orden
        def unique_alerts(alerts_list):
            seen = set()
            result = []
            for cat, reason in alerts_list:
                key = (cat, reason[:50])  # Usar primeros 50 chars para comparar
                if key not in seen:
                    seen.add(key)
                    result.append((cat, reason))
            return result
        
        danger_alerts = unique_alerts(danger_alerts)
        warning_alerts = unique_alerts(warning_alerts)
        success_alerts = unique_alerts(success_alerts)
        
        tab_evaluation = html.Div([
            html.H5("Evaluación Completa", className="mb-2"),
            html.P("Desglose del score y análisis detallado", className="text-muted small mb-3"),
            
            # Desglose por categorías
            html.H6("📊 Desglose del Score (5 categorías × 20 pts)", className="mb-3"),
            html.Div([
                html.Div([
                    dbc.Row([
                        dbc.Col([html.Span(f"{cat.get('emoji', '📊')} {cat.get('category', 'N/A')}", className="fw-bold")], xs=8),
                        dbc.Col([html.Span(f"{cat.get('score', 0)}/{cat.get('max_score', 20)}",
                            className="text-success fw-bold" if cat.get('score', 0) >= 15 else 
                                     "text-warning fw-bold" if cat.get('score', 0) >= 10 else "text-danger fw-bold")
                        ], xs=4, className="text-end")
                    ]),
                    dbc.Progress(value=cat.get('score', 0), max=cat.get('max_score', 20), className="mb-3", style={"height": "8px"})
                ], className="mb-2") for cat in categories
            ]) if categories else html.P("Sin datos de scoring", className="text-muted"),
            
            html.Hr(),
            
            # RESUMEN DE PUNTUACIÓN
            html.H6("📋 Resumen de Puntuación", className="mb-3"),
            dbc.Row([
                dbc.Col([create_score_summary_card("Solidez", solidez, 20, "🏛️")], xs=6, md=2, className="mb-3"),
                dbc.Col([create_score_summary_card("Rentabilidad", rentabilidad, 20, "💰")], xs=6, md=2, className="mb-3"),
                dbc.Col([create_score_summary_card("Valoración", valoracion, 20, "💵")], xs=6, md=2, className="mb-3"),
                dbc.Col([create_score_summary_card("Calidad", calidad, 20, "✅")], xs=6, md=2, className="mb-3"),
                dbc.Col([create_score_summary_card("Crecimiento", crecimiento, 20, "📈")], xs=6, md=2, className="mb-3"),
                dbc.Col([
                    html.Div([
                        html.Div("🎯 TOTAL", style={"color": "#71717a", "fontSize": "0.75rem", "marginBottom": "8px"}),
                        html.Div(f"{score}/100", style={
                            "color": score_color, "fontSize": "1.8rem", "fontWeight": "700"
                        })
                    ], style={
                        "background": f"{score_color}22", "border": f"1px solid {score_color}55",
                        "borderRadius": "12px", "padding": "16px", "textAlign": "center"
                    })
                ], xs=6, md=2, className="mb-3"),
            ], className="justify-content-center"),
            
            html.Hr(),
            
            # Señales
            html.H6("📋 Señales Detectadas", className="mb-3"),
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.H4(len(danger_alerts), className="text-danger mb-0"),
                        html.Small("Riesgos", className="text-muted")
                    ], className="text-center p-3", style={"background": "rgba(239, 68, 68, 0.1)", "borderRadius": "8px"})
                ], xs=4),
                dbc.Col([
                    html.Div([
                        html.H4(len(warning_alerts), className="text-warning mb-0"),
                        html.Small("Advertencias", className="text-muted")
                    ], className="text-center p-3", style={"background": "rgba(234, 179, 8, 0.1)", "borderRadius": "8px"})
                ], xs=4),
                dbc.Col([
                    html.Div([
                        html.H4(len(success_alerts), className="text-success mb-0"),
                        html.Small("Fortalezas", className="text-muted")
                    ], className="text-center p-3", style={"background": "rgba(34, 197, 94, 0.1)", "borderRadius": "8px"})
                ], xs=4),
            ], className="mb-4"),
            
            # Lista de alertas
            html.Div([
                html.H6("🔴 Señales de Riesgo", className="text-danger") if danger_alerts else None,
                html.Div([
                    html.Div([html.Strong(f"{cat}: "), html.Span(reason)],
                            className="alert-box alert-danger-custom mb-2")
                    for cat, reason in danger_alerts[:5]
                ]) if danger_alerts else None,
                
                html.H6("🟠 Advertencias", className="text-warning mt-3") if warning_alerts else None,
                html.Div([
                    html.Div([html.Strong(f"{cat}: "), html.Span(reason)],
                            className="alert-box alert-warning-custom mb-2")
                    for cat, reason in warning_alerts[:5]
                ]) if warning_alerts else None,
                
                html.H6("🟢 Fortalezas", className="text-success mt-3") if success_alerts else None,
                html.Div([
                    html.Div([html.Strong(f"{cat}: "), html.Span(reason)],
                            className="alert-box alert-success-custom mb-2")
                    for cat, reason in success_alerts[:5]
                ]) if success_alerts else None,
            ])
        ])
        
        # Footer
        footer = [
            f"📅 Análisis generado: {datetime.now().strftime('%Y-%m-%d %H:%M')} · ",
            html.Span("Datos: Yahoo Finance · ", className="text-muted"),
            html.Span("Esto no es asesoría financiera.", className="text-warning")
        ]
        
        stored_data = {"symbol": symbol, "company_name": company_name, "ratios": ratios, "alerts": alerts}
        
        return (
            {"display": "none"}, {"display": "block"},
            company_header, score_card, key_metrics, sector_notes,
            tab_valuation, tab_profitability, tab_health, tab_historical, tab_comparison, tab_intrinsic, tab_evaluation,
            footer, stored_data, symbol, None, None, stock_badge, "", hide_suggestions
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        error_msg = dbc.Alert(f"❌ Error al analizar '{symbol}': {str(e)}", color="danger", dismissable=True)
        return home_style, analysis_style, *empty_outputs, None, "", error_msg, None, None, "", hide_suggestions


# Callback para cambiar periodo del gráfico histórico
@callback(
    Output("price-chart-container", "children"),
    Output("period-1mo", "color"),
    Output("period-3mo", "color"),
    Output("period-6mo", "color"),
    Output("period-1y", "color"),
    Output("period-5y", "color"),
    Output("period-1mo", "outline"),
    Output("period-3mo", "outline"),
    Output("period-6mo", "outline"),
    Output("period-1y", "outline"),
    Output("period-5y", "outline"),
    Input("period-1mo", "n_clicks"),
    Input("period-3mo", "n_clicks"),
    Input("period-6mo", "n_clicks"),
    Input("period-1y", "n_clicks"),
    Input("period-5y", "n_clicks"),
    State("current-symbol", "data"),
    prevent_initial_call=True
)
def update_price_chart_period(n1, n3, n6, n12, n60, symbol):
    if not symbol:
        return no_update, *["secondary"]*5, *[True]*5
    
    triggered_id = ctx.triggered_id
    
    period_map = {
        "period-1mo": "1mo",
        "period-3mo": "3mo",
        "period-6mo": "6mo",
        "period-1y": "1y",
        "period-5y": "5y"
    }
    
    period = period_map.get(triggered_id, "1y")
    
    # Crear nuevo gráfico
    chart = create_price_chart(symbol, period)
    
    if chart:
        chart_component = dcc.Graph(figure=chart, config={'displayModeBar': False}, id="price-chart")
    else:
        chart_component = html.Div([html.P("📈 No se pudieron cargar los datos", className="text-muted text-center py-5")])
    
    # Colores de botones (el activo es primary, los demás secondary outline)
    colors = ["secondary"] * 5
    outlines = [True] * 5
    
    button_order = ["period-1mo", "period-3mo", "period-6mo", "period-1y", "period-5y"]
    if triggered_id in button_order:
        idx = button_order.index(triggered_id)
        colors[idx] = "primary"
        outlines[idx] = False
    
    return chart_component, *colors, *outlines


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)
