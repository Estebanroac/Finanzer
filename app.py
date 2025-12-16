"""
Stock Analyzer - Dash Edition v2.2
==================================
Aplicación web responsive para análisis fundamental de acciones.
Mobile-first design con soporte para dark/light theme.

Autor: Esteban
Versión: 2.2 - Sistema Adaptativo Growth/Value + Dark/Light Mode
"""

import os
import logging

# Configuración de logging (reemplaza prints de debug)
logging.basicConfig(
    level=logging.DEBUG if os.getenv("DEBUG", "false").lower() == "true" else logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

import dash
from dash import dcc, html, callback, Input, Output, State, no_update, ctx, ALL, MATCH
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from datetime import datetime
import base64
import io
import re
import traceback
import yfinance as yf

# Imports de reportlab (movidos al inicio para mejor performance)
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Spacer, Table, TableStyle

# Importar módulos del analizador
from financial_ratios import (
    calculate_all_ratios,
    aggregate_alerts,
    format_ratio,
    graham_number,
    dcf_fair_value,
    dcf_dynamic,
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
    """
    Resuelve y valida el símbolo de búsqueda.
    Validación PERMISIVA: sanitiza pero no rechaza símbolos potencialmente válidos.
    """
    if not query:
        return ""
    
    query_clean = query.strip()
    
    # Límite de longitud razonable (símbolos más largos son raros)
    if len(query_clean) > 15:
        query_clean = query_clean[:15]
    
    # Buscar en mapeo de nombres comunes
    query_lower = query_clean.lower()
    if query_lower in COMPANY_NAMES:
        return COMPANY_NAMES[query_lower]
    
    # Sanitización: solo permitir caracteres válidos para tickers
    # Incluye: letras, números, punto (BRK.A), guión (BRK-B), espacio (para búsqueda)
    sanitized = re.sub(r'[^A-Za-z0-9\.\-\s]', '', query_clean)
    
    return sanitized.upper().strip()


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


def create_price_chart(symbol: str, period: str = "1y"):
    """
    Crea gráfico de precio histórico moderno y minimalista.
    Retorna: (figura, pct_change, end_price) o (None, 0, 0) si hay error
    """
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period)
        
        if hist.empty or len(hist) < 2:
            return None, 0, 0
        
        start_price = float(hist['Close'].iloc[0])
        end_price = float(hist['Close'].iloc[-1])
        is_positive = end_price >= start_price
        pct_change = ((end_price - start_price) / start_price) * 100
        
        # Colores modernos
        if is_positive:
            line_color = '#10b981'  # Emerald
            fill_color = 'rgba(16, 185, 129, 0.12)'
        else:
            line_color = '#f43f5e'  # Rose
            fill_color = 'rgba(244, 63, 94, 0.12)'
        
        fig = go.Figure()
        
        # Línea principal con área
        fig.add_trace(go.Scatter(
            x=hist.index, y=hist['Close'],
            mode='lines',
            line=dict(color=line_color, width=2.5, shape='spline'),
            fill='tozeroy',
            fillcolor=fill_color,
            hovertemplate='%{x|%d %b %Y}<br><b>$%{y:.2f}</b><extra></extra>',
            name=''
        ))
        
        # Punto final destacado
        fig.add_trace(go.Scatter(
            x=[hist.index[-1]],
            y=[end_price],
            mode='markers',
            marker=dict(color=line_color, size=10, line=dict(color='#18181b', width=3)),
            hoverinfo='skip',
            showlegend=False
        ))
        
        # Formato de fecha según período
        if period in ['5d', '1wk']:
            date_format = '%d %b'
            nticks = 5
        elif period in ['1mo', '3mo']:
            date_format = '%d %b'
            nticks = 6
        elif period == '6mo':
            date_format = '%b'
            nticks = 6
        elif period == '1y':
            date_format = '%b %Y'
            nticks = 6
        else:  # 5y
            date_format = '%Y'
            nticks = 5
        
        fig.update_layout(
            height=280,
            margin=dict(l=10, r=70, t=10, b=35),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(
                showgrid=False,
                showticklabels=True,
                tickfont=dict(color='#71717a', size=10),
                zeroline=False,
                showline=False,
                tickformat=date_format,
                nticks=nticks,
                fixedrange=True
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='rgba(255, 255, 255, 0.04)',
                showticklabels=True,
                tickfont=dict(color='#71717a', size=10),
                tickprefix='$',
                zeroline=False,
                showline=False,
                side='right',
                fixedrange=True
            ),
            # Hover con fondo del color de la línea y texto blanco
            hovermode='x unified',
            hoverlabel=dict(
                bgcolor=line_color,
                bordercolor=line_color,
                font=dict(color='white', size=13)
            ),
            showlegend=False,
        )
        
        return fig, pct_change, end_price
    except Exception as e:
        logger.warning(f"Error creating price chart for {symbol}: {e}")
        return None, 0, 0


def create_ytd_comparison_chart(stock_ytd: float, market_ytd: float, sector_ytd: float, symbol: str) -> go.Figure:
    """Crea gráfico de barras comparativo YTD con porcentajes dentro de las barras."""
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
    
    # Determinar posición del texto basado en magnitud de valores
    text_positions = []
    for v in values:
        # Si el valor es muy pequeño, texto afuera; si no, adentro
        if abs(v) < 5:
            text_positions.append('outside')
        else:
            text_positions.append('inside')
    
    fig.add_trace(go.Bar(
        x=categories, y=values,
        marker=dict(
            color=colors,
            line=dict(width=0),
            opacity=0.9
        ),
        text=[f"{v:+.1f}%" for v in values],
        textposition=text_positions,
        textfont=dict(color='#ffffff', size=16, family='Inter, sans-serif'),
        insidetextanchor='middle',
        hovertemplate='%{x}<br>Rendimiento YTD: %{y:.2f}%<extra></extra>',
        width=0.55
    ))
    
    fig.add_hline(y=0, line_dash="solid", line_color="#52525b", line_width=2)
    
    fig.update_layout(
        height=320, margin=dict(l=20, r=20, t=40, b=30),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(
            showgrid=False, 
            tickfont=dict(color='#d4d4d8', size=14, family='Inter, sans-serif'),
            showline=False
        ),
        yaxis=dict(
            showgrid=True, gridcolor='rgba(255,255,255,0.06)',
            tickfont=dict(color='#71717a', size=11), 
            ticksuffix='%', zeroline=False,
            showline=False
        ),
        font={'family': 'Inter, sans-serif'}, 
        showlegend=False,
        bargap=0.35
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
        color = "#22c55e"
    elif score >= 10:
        color = "#eab308"
    else:
        color = "#ef4444"
    
    return html.Div([
        html.Div(f"{icon} {label}", className="score-summary-label"),
        html.Div(f"{score}/{max_score}", style={"color": color, "fontSize": "1.5rem", "fontWeight": "700"})
    ], className="score-summary-card")


def get_alert_explanation(category: str, reason: str) -> str:
    """Genera una explicación detallada para cada tipo de alerta."""
    category_lower = category.lower()
    reason_lower = reason.lower()
    
    # Explicaciones por categoría y tipo de alerta
    explanations = {
        # Valoración
        ("valoración", "p/e"): "El ratio P/E (Precio/Beneficio) compara el precio de la acción con sus ganancias por acción. Un P/E alto puede indicar sobrevaloración o expectativas de crecimiento.",
        ("valoración", "p/fcf"): "El ratio P/FCF (Precio/Flujo de Caja Libre) es más confiable que el P/E porque el flujo de caja es más difícil de manipular que las ganancias contables.",
        ("valoración", "ev/ebitda"): "EV/EBITDA compara el valor empresarial con las ganancias antes de intereses, impuestos y amortización. Útil para comparar empresas con diferentes estructuras de capital.",
        ("valoración", "peg"): "El PEG ajusta el P/E por el crecimiento esperado. Un PEG < 1 sugiere que la acción puede estar subvalorada para su tasa de crecimiento.",
        
        # Deuda
        ("deuda", "debt"): "El apalancamiento excesivo aumenta el riesgo financiero, especialmente en entornos de tasas de interés altas o recesiones económicas.",
        ("deuda", "interest"): "La cobertura de intereses mide la capacidad de la empresa para pagar sus gastos de interés. Un ratio bajo indica riesgo de incumplimiento.",
        ("deuda", "conservative"): "Un bajo nivel de deuda proporciona flexibilidad financiera y reduce el riesgo en ciclos económicos adversos.",
        
        # Rentabilidad
        ("rentabilidad", "roe"): "El ROE (Return on Equity) mide qué tan eficientemente la empresa genera beneficios con el capital de los accionistas. Un ROE consistentemente alto indica ventaja competitiva.",
        ("rentabilidad", "roa"): "El ROA (Return on Assets) indica qué tan eficientemente la empresa utiliza sus activos para generar beneficios.",
        ("rentabilidad", "margen"): "Los márgenes miden la rentabilidad en diferentes niveles del estado de resultados. Márgenes altos y estables indican poder de fijación de precios.",
        
        # Liquidez
        ("liquidez", "current"): "El Current Ratio mide la capacidad de pagar obligaciones de corto plazo. Un ratio < 1 puede indicar problemas de liquidez.",
        ("liquidez", "quick"): "El Quick Ratio excluye inventarios, dando una medida más estricta de liquidez inmediata.",
        
        # Flujo de Caja
        ("flujo", "fcf"): "El Flujo de Caja Libre es el dinero que queda después de operaciones e inversiones de capital. Es crucial para dividendos, recompras y reducción de deuda.",
        ("flujo", "negativo"): "Un FCF negativo persistente indica que la empresa está quemando efectivo y puede necesitar financiamiento externo.",
        ("flujo", "calidad"): "La relación FCF/Net Income indica la calidad de las ganancias. Un ratio bajo sugiere que las ganancias contables no se traducen en efectivo real.",
        
        # Crecimiento
        ("crecimiento", "revenue"): "El crecimiento de ingresos es fundamental para la creación de valor a largo plazo. Un crecimiento estancado puede indicar madurez del mercado o pérdida de competitividad.",
        ("crecimiento", "eps"): "El crecimiento del EPS (Beneficio por Acción) refleja no solo el crecimiento del negocio sino también la gestión del capital.",
        
        # Volatilidad
        ("volatilidad", "beta"): "Beta mide la volatilidad relativa al mercado. Beta > 1 significa más volátil que el mercado; Beta < 1 significa menos volátil.",
        ("volatilidad", "drawdown"): "El Maximum Drawdown mide la mayor caída desde un pico. Drawdowns grandes pueden indicar riesgo elevado.",
    }
    
    # Buscar explicación relevante
    for (cat_key, reason_key), explanation in explanations.items():
        if cat_key in category_lower and reason_key in reason_lower:
            return explanation
    
    # Explicaciones genéricas por categoría
    generic_explanations = {
        "valoración": "Las métricas de valoración comparan el precio de mercado con métricas fundamentales para determinar si una acción está cara o barata relativa a sus fundamentos.",
        "deuda": "Las métricas de deuda evalúan la estructura de capital y la capacidad de la empresa para cumplir con sus obligaciones financieras.",
        "rentabilidad": "Las métricas de rentabilidad miden la eficiencia de la empresa para convertir ingresos en beneficios.",
        "liquidez": "Las métricas de liquidez evalúan la capacidad de la empresa para cumplir con obligaciones de corto plazo.",
        "flujo": "Las métricas de flujo de caja evalúan la generación real de efectivo del negocio.",
        "crecimiento": "Las métricas de crecimiento evalúan la trayectoria de expansión del negocio.",
        "volatilidad": "Las métricas de volatilidad miden el riesgo de fluctuaciones en el precio de la acción.",
    }
    
    for cat_key, explanation in generic_explanations.items():
        if cat_key in category_lower:
            return explanation
    
    return "Esta métrica proporciona información relevante para evaluar la salud financiera y el potencial de inversión de la empresa."


def create_comparison_metric_row(metric_name: str, company_val, sector_val, market_val, fmt: str = "multiple", lower_better: bool = True):
    """Crea una fila de comparación de métricas con veredicto."""
    def format_val(v, fmt):
        if v is None:
            return "N/A"
        if fmt == "percent":
            return f"{v*100:.1f}%" if isinstance(v, float) and abs(v) < 2 else f"{v:.1f}%"
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
        html.Td(metric_name, className="comparison-td comparison-metric"),
        html.Td(format_val(company_val, fmt), className="comparison-td comparison-company"),
        html.Td(format_val(sector_val, fmt), className="comparison-td comparison-muted"),
        html.Td(format_val(market_val, fmt), className="comparison-td comparison-muted"),
        html.Td(verdict_text, className="comparison-td comparison-verdict", style={"color": verdict_color}),
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


def generate_simple_pdf(symbol: str, company_name: str, ratios: dict, alerts: dict, score: int) -> bytes:
    """PDF completo en UNA pagina - formato compacto."""
    # Imports de reportlab movidos al inicio del archivo para mejor performance
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.2*inch, bottomMargin=0.2*inch,
                           leftMargin=0.3*inch, rightMargin=0.3*inch)
    
    story = []
    pw = 7.9*inch
    
    def fmt(val, tipo="x"):
        if val is None: return "N/A"
        try:
            v = float(val)
            if tipo == "%":
                return f"{v*100:.1f}%" if abs(v) < 1 else f"{v:.1f}%"
            elif tipo == "$":
                if abs(v) >= 1e12: return f"${v/1e12:.1f}T"
                elif abs(v) >= 1e9: return f"${v/1e9:.1f}B"
                elif abs(v) >= 1e6: return f"${v/1e6:.0f}M"
                elif abs(v) >= 1000: return f"${v/1000:.0f}K"
                else: return f"${v:.2f}"
            elif tipo == "vol":
                if abs(v) >= 1e6: return f"{v/1e6:.1f}M"
                elif abs(v) >= 1000: return f"{v/1000:.0f}K"
                else: return f"{v:.0f}"
            else: return f"{v:.2f}"
        except: return "N/A"
    
    def sec(text, bg):
        t = Table([[text]], colWidths=[pw])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor(bg)),
            ('TEXTCOLOR', (0,0), (-1,-1), colors.white),
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 7),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('TOPPADDING', (0,0), (-1,-1), 1),
            ('BOTTOMPADDING', (0,0), (-1,-1), 1),
        ]))
        return t
    
    def tbl(headers, values, ncols):
        w = pw / ncols
        t = Table([headers, values], colWidths=[w]*ncols)
        t.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 5),
            ('FONTSIZE', (0,1), (-1,1), 7),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor('#d1d5db')),
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f3f4f6')),
            ('TOPPADDING', (0,0), (-1,-1), 1),
            ('BOTTOMPADDING', (0,0), (-1,-1), 1),
        ]))
        return t
    
    # HEADER
    h = Table([[f"{symbol} - {company_name}"]], colWidths=[pw])
    h.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#1e3a5f')),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 11),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(h)
    
    # SCORE + CATEGORIAS (combinados)
    sv2 = alerts.get("score_v2", {})
    ts = sv2.get("score", score)
    lv = sv2.get("level", "N/A")
    rec_full = alerts.get("recommendation", "N/A")
    # Acortar recomendación para que quepa
    rec_map = {
        "FAVORABLE - Considerar inversión": "FAVORABLE",
        "NEUTRAL - Requiere análisis adicional": "NEUTRAL",
        "PRECAUCIÓN - Riesgos identificados": "PRECAUCION",
        "EVITAR - Múltiples señales de alerta": "EVITAR"
    }
    rec = rec_map.get(rec_full, rec_full[:10] if len(rec_full) > 10 else rec_full)
    sig = alerts.get("signal", "N/A")
    gr = "Si" if sv2.get("is_growth_company", False) else "No"
    sbg = '#dcfce7' if ts >= 70 else '#fef9c3' if ts >= 50 else '#fee2e2'
    cs = sv2.get("category_scores", {})
    
    sc = Table([
        ["SCORE", "NIVEL", "RECOM", "SENAL", "GROWTH", "Valor", "Rent", "Solid", "Calid", "Crec"],
        [f"{ts}/100", lv, rec, sig, gr, 
         f"{cs.get('valoracion',0):.0f}/20", f"{cs.get('rentabilidad',0):.0f}/20",
         f"{cs.get('solidez',0):.0f}/20", f"{cs.get('calidad',0):.0f}/20", f"{cs.get('crecimiento',0):.0f}/20"]
    ], colWidths=[pw/10]*10)
    sc.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (4,0), colors.HexColor('#374151')),
        ('BACKGROUND', (5,0), (-1,0), colors.HexColor('#6366f1')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('BACKGROUND', (0,1), (4,1), colors.HexColor(sbg)),
        ('BACKGROUND', (5,1), (-1,1), colors.HexColor('#eef2ff')),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 5),
        ('FONTSIZE', (0,1), (-1,1), 7),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor('#9ca3af')),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(sc)
    story.append(Spacer(1, 2))
    
    # METRICAS CLAVE + VALORACION
    story.append(sec("METRICAS CLAVE | VALORACION", "#1f2937"))
    story.append(tbl(
        ["MktCap", "Precio", "Beta", "EV/EBITDA", "P/E", "FwdPE", "P/B", "P/S", "P/FCF", "PEG"],
        [fmt(ratios.get("market_cap"), "$"), fmt(ratios.get("price"), "$"), fmt(ratios.get("beta")),
         fmt(ratios.get("ev_ebitda")), fmt(ratios.get("pe")), fmt(ratios.get("forward_pe")),
         fmt(ratios.get("pb")), fmt(ratios.get("ps")), fmt(ratios.get("p_fcf")), fmt(ratios.get("peg"))], 10))
    story.append(Spacer(1, 1))
    
    # RENTABILIDAD
    story.append(sec("RENTABILIDAD", "#16a34a"))
    story.append(tbl(
        ["ROE", "ROA", "ROIC", "M.Bruto", "M.Oper", "M.Neto", "M.EBITDA", "EPS", "FCF Yld"],
        [fmt(ratios.get("roe"), "%"), fmt(ratios.get("roa"), "%"), fmt(ratios.get("roic"), "%"),
         fmt(ratios.get("gross_margin"), "%"), fmt(ratios.get("operating_margin"), "%"),
         fmt(ratios.get("net_margin"), "%"), fmt(ratios.get("ebitda_margin"), "%"),
         fmt(ratios.get("eps")), fmt(ratios.get("fcf_yield"), "%")], 9))
    story.append(tbl(
        ["Ingresos", "EBITDA", "Ing Neto", "FCF"],
        [fmt(ratios.get("revenue"), "$"), fmt(ratios.get("ebitda"), "$"),
         fmt(ratios.get("net_income"), "$"), fmt(ratios.get("fcf"), "$")], 4))
    story.append(Spacer(1, 1))
    
    # SOLIDEZ
    story.append(sec("SOLIDEZ FINANCIERA", "#7c3aed"))
    story.append(tbl(
        ["Current", "Quick", "CashR", "D/E", "D/Assets", "NetD/EBITDA", "CobInt", "FCF/D"],
        [fmt(ratios.get("current_ratio")), fmt(ratios.get("quick_ratio")), fmt(ratios.get("cash_ratio")),
         fmt(ratios.get("debt_to_equity")), fmt(ratios.get("debt_to_assets"), "%"),
         fmt(ratios.get("net_debt_to_ebitda")), fmt(ratios.get("interest_coverage")),
         fmt(ratios.get("fcf_to_debt"), "%")], 8))
    story.append(tbl(
        ["Work Cap", "Deuda Total", "Cash", "52W Hi", "52W Lo", "Vol Prom"],
        [fmt(ratios.get("working_capital"), "$"), fmt(ratios.get("total_debt"), "$"),
         fmt(ratios.get("cash_and_equivalents"), "$"), fmt(ratios.get("fifty_two_week_high"), "$"),
         fmt(ratios.get("fifty_two_week_low"), "$"), fmt(ratios.get("average_volume"), "vol")], 6))
    story.append(Spacer(1, 1))
    
    # VALOR INTRINSECO + INSTITUCIONALES
    story.append(sec("VALOR INTRINSECO | METRICAS INSTITUCIONALES", "#0d9488"))
    eps = ratios.get("eps")
    bvps = ratios.get("book_value_per_share")
    graham = (22.5 * eps * bvps) ** 0.5 if eps and bvps and eps > 0 and bvps > 0 else None
    fcf = ratios.get("fcf")
    shares = ratios.get("shares_outstanding")
    
    # v2.2: DCF Dinámico - usar WACC y growth específicos si están disponibles
    dcf_value = None
    wd = alerts.get('wacc')
    wacc_val = wd.get('wacc') if isinstance(wd, dict) else wd if isinstance(wd, (int, float)) else 0.10
    growth_val = ratios.get("revenue_cagr_3y", 0.05) or 0.05
    growth_val = min(max(growth_val, 0.02), 0.20)  # Limitar entre 2% y 20%
    if wacc_val and growth_val >= wacc_val:
        growth_val = wacc_val - 0.02  # Asegurar growth < wacc
    
    if fcf and shares and fcf > 0 and shares > 0 and wacc_val:
        dcf_sum = sum([fcf * ((1 + growth_val) ** i) / ((1 + wacc_val) ** i) for i in range(1, 11)])
        terminal = (fcf * ((1 + growth_val) ** 10) * 1.025) / (wacc_val - 0.025)
        dcf_value = (dcf_sum + terminal / ((1 + wacc_val) ** 10)) / shares
    
    price = ratios.get("price")
    gd = f"({((graham-price)/price*100):+.0f}%)" if graham and price and price > 0 else ""
    dd = f"({((dcf_value-price)/price*100):+.0f}%)" if dcf_value and price and price > 0 else ""
    
    zs = alerts.get('altman_z_score', {})
    fs = alerts.get('piotroski_f_score', {})
    jp = alerts.get('justified_pe')
    zv = zs.get('value') if isinstance(zs, dict) else None
    zl = zs.get('level', '') if isinstance(zs, dict) else ''
    zt = "Segura" if zl == 'SAFE' else "Gris" if zl == 'GREY' else "Riesgo" if zl else "N/A"
    fv = fs.get('value') if isinstance(fs, dict) else None
    wv = wd.get('wacc') if isinstance(wd, dict) else wd if isinstance(wd, (int, float)) else None
    jv = jp.get('justified_pe') if isinstance(jp, dict) else jp if isinstance(jp, (int, float)) else None
    
    story.append(tbl(
        ["Precio", "Graham", "DCF", "Z-Score", "Zona", "F-Score", "WACC", "JustPE"],
        [fmt(price, "$"), f"{fmt(graham,'$')}{gd}" if graham else "N/A",
         f"{fmt(dcf_value,'$')}{dd}" if dcf_value else "N/A",
         f"{zv:.2f}" if zv else "N/A", zt, f"{fv}/9" if fv is not None else "N/A",
         f"{wv*100:.1f}%" if wv else "N/A", f"{jv:.1f}x" if jv else "N/A"], 8))
    story.append(Spacer(1, 2))
    
    # SENALES
    story.append(sec("SENALES DETECTADAS", "#475569"))
    
    danger_list = list(alerts.get("danger", []))
    warning_list = list(alerts.get("warning", []))
    success_list = list(alerts.get("success", []))
    for key, label in [("valuation", "Val"), ("leverage", "Deu"), ("profitability", "Ren"),
                       ("liquidity", "Liq"), ("cash_flow", "FCF"), ("growth", "Cre"),
                       ("volatility", "Vol"), ("structural_deterioration", "Det")]:
        cat = alerts.get(key, {})
        if isinstance(cat, dict):
            for r in cat.get("overvalued_reasons", []):
                if (label, r) not in danger_list: danger_list.append((label, r))
            for r in cat.get("warning_reasons", []):
                if (label, r) not in warning_list: warning_list.append((label, r))
            for r in cat.get("undervalued_reasons", []):
                if (label, r) not in success_list: success_list.append((label, r))
            for r in cat.get("positive_reasons", []):
                if (label, r) not in success_list: success_list.append((label, r))
    
    rows = []
    for c, r in danger_list[:8]: rows.append(["RIESGO", f"{c}: {r}"])
    for c, r in warning_list[:5]: rows.append(["ADVERT", f"{c}: {r}"])
    for c, r in success_list[:5]: rows.append(["FORTALEZA", f"{c}: {r}"])
    if not rows: rows.append(["INFO", "Sin senales significativas"])
    
    sig_t = Table(rows, colWidths=[0.7*inch, 7.2*inch])
    ss = [('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'), ('FONTSIZE', (0,0), (-1,-1), 6),
          ('ALIGN', (0,0), (0,-1), 'CENTER'), ('ALIGN', (1,0), (1,-1), 'LEFT'),
          ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor('#e5e7eb')),
          ('TOPPADDING', (0,0), (-1,-1), 1), ('BOTTOMPADDING', (0,0), (-1,-1), 1),
          ('LEFTPADDING', (1,0), (1,-1), 3)]
    for i, row in enumerate(rows):
        if row[0] == "RIESGO":
            ss.extend([('BACKGROUND', (0,i), (0,i), colors.HexColor('#fee2e2')),
                       ('TEXTCOLOR', (0,i), (0,i), colors.HexColor('#dc2626'))])
        elif row[0] == "ADVERT":
            ss.extend([('BACKGROUND', (0,i), (0,i), colors.HexColor('#fef3c7')),
                       ('TEXTCOLOR', (0,i), (0,i), colors.HexColor('#d97706'))])
        elif row[0] == "FORTALEZA":
            ss.extend([('BACKGROUND', (0,i), (0,i), colors.HexColor('#dcfce7')),
                       ('TEXTCOLOR', (0,i), (0,i), colors.HexColor('#16a34a'))])
    sig_t.setStyle(TableStyle(ss))
    story.append(sig_t)
    story.append(Spacer(1, 3))
    
    # FOOTER
    ft = Table([[f"Stock Analyzer | {datetime.now().strftime('%d/%m/%Y %H:%M')} | No es asesoria financiera"]], colWidths=[pw])
    ft.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER'), ('FONTSIZE', (0,0), (-1,-1), 5), ('TEXTCOLOR', (0,0), (-1,-1), colors.gray)]))
    story.append(ft)
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

# =============================================================================
# LAYOUT PRINCIPAL
# =============================================================================

app.layout = dbc.Container([
    dcc.Store(id="analysis-data", storage_type="memory"),
    dcc.Store(id="current-symbol", data="", storage_type="memory"),
    dcc.Store(id="theme-store", data="dark", storage_type="local"),  # Persiste en localStorage
    dcc.Download(id="download-pdf"),
    
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
                  className="home-subtitle"),
            
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
                    html.H6("40+ Métricas", className="feature-title"),
                    html.P("Ratios financieros, valoración y solidez", className="feature-desc")
                ], style={"flex": "1", "textAlign": "center", "padding": "10px 15px", "minWidth": "150px"}),
                
                # Divider
                html.Div(className="feature-divider"),
                
                # Feature 2
                html.Div([
                    html.Div("📊", style={"fontSize": "1.8rem", "marginBottom": "10px"}),
                    html.H6("Score 0-100", className="feature-title"),
                    html.P("Evaluación con Z-Score y F-Score", className="feature-desc")
                ], style={"flex": "1", "textAlign": "center", "padding": "10px 15px", "minWidth": "150px"}),
                
                # Divider
                html.Div(className="feature-divider"),
                
                # Feature 3
                html.Div([
                    html.Div("⚖️", style={"fontSize": "1.8rem", "marginBottom": "10px"}),
                    html.H6("Comparativa", className="feature-title"),
                    html.P("Benchmark vs Sector y S&P 500", className="feature-desc")
                ], style={"flex": "1", "textAlign": "center", "padding": "10px 15px", "minWidth": "150px"}),
                
                # Divider
                html.Div(className="feature-divider"),
                
                # Feature 4
                html.Div([
                    html.Div("💰", style={"fontSize": "1.8rem", "marginBottom": "10px"}),
                    html.H6("Valor Intrínseco", className="feature-title"),
                    html.P("Métodos Graham y DCF", className="feature-desc")
                ], style={"flex": "1", "textAlign": "center", "padding": "10px 15px", "minWidth": "150px"}),
                
            ], className="features-container")
        ], style={"maxWidth": "900px", "margin": "0 auto 40px auto", "padding": "0 20px"}),
        
        # Disclaimer
        html.Div([
            html.P([
                html.Span("⚠️ "),
                "Esta herramienta es para fines educativos. No constituye asesoría financiera."
            ], className="disclaimer-text")
        ], style={"textAlign": "center", "paddingBottom": "40px"})
    ]),
    
    # =========================================================================
    # VISTA ANÁLISIS
    # =========================================================================
    html.Div(id="analysis-view", style={"display": "none"}, children=[
        html.Div(id="company-header"),
        
        # Botón de descarga PDF (fijo, no dinámico)
        html.Div([
            html.Button([
                html.Span("📄", style={"marginRight": "8px"}),
                html.Span("Descargar Análisis PDF", className="btn-text-white")
            ], id="download-pdf-btn", n_clicks=0, className="download-btn")
        ], className="text-center mb-4"),
        
        dbc.Row([
            dbc.Col([html.Div(id="score-card-container", className="score-card")], xs=12, md=4, lg=3, className="mb-3"),
            dbc.Col([html.Div(id="key-metrics-container")], xs=12, md=8, lg=9)
        ]),
        
        html.Div(id="sector-notes-container", className="mb-4"),
        html.Hr(),
        
        # Tabs con wrapper scrolleable para móvil
        html.Div([
            dbc.Tabs([
                dbc.Tab(html.Div(id="tab-valuation-content", className="tab-content-inner"), label="📊 Valoración", tab_id="tab-valuation"),
                dbc.Tab(html.Div(id="tab-profitability-content", className="tab-content-inner"), label="💰 Rentabilidad", tab_id="tab-profitability"),
                dbc.Tab(html.Div(id="tab-health-content", className="tab-content-inner"), label="🏦 Solidez", tab_id="tab-health"),
                dbc.Tab(html.Div(id="tab-historical-content", className="tab-content-inner"), label="📈 Histórico", tab_id="tab-historical"),
                dbc.Tab(html.Div(id="tab-comparison-content", className="tab-content-inner"), label="⚖️ Comparativa", tab_id="tab-comparison"),
                dbc.Tab(html.Div(id="tab-intrinsic-content", className="tab-content-inner"), label="🎯 Intrínseco", tab_id="tab-intrinsic"),
                dbc.Tab(html.Div(id="tab-evaluation-content", className="tab-content-inner"), label="📋 Evaluación", tab_id="tab-evaluation"),
            ], id="analysis-tabs", active_tab="tab-valuation", className="mb-3 tabs-scrollable"),
        ], className="tabs-wrapper"),
        
        html.Hr(),
        html.P(id="analysis-footer", className="text-center small text-muted")
    ]),
    
    # =========================================================================
    # THEME TOGGLE BUTTON
    # =========================================================================
    html.Button(
        id="theme-toggle",
        className="theme-toggle",
        children=[
            html.Span("☀️", id="icon-sun", style={"fontSize": "1.2rem"}),
            html.Span("🌙", id="icon-moon", style={"fontSize": "1.2rem", "display": "none"})
        ],
        title="Cambiar tema",
        n_clicks=0,
        style={
            "position": "fixed",
            "bottom": "20px",
            "right": "20px",
            "width": "50px",
            "height": "50px",
            "borderRadius": "50%",
            "border": "2px solid #3f3f46",
            "backgroundColor": "#18181b",
            "color": "#ffffff",
            "cursor": "pointer",
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "center",
            "fontSize": "1.3rem",
            "zIndex": "9999",
            "boxShadow": "0 4px 12px rgba(0, 0, 0, 0.4)",
            "transition": "all 0.2s ease"
        }
    ),
    
], fluid=True, className="fade-in", id="main-container")


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
            return home_style, analysis_style, *empty_outputs, "", None, None, None, "", hide_suggestions
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
            return home_style, analysis_style, *empty_outputs, "", error_msg, None, None, "", hide_suggestions
        
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
        
        # Company Header (sin botón PDF - está en el layout principal)
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
                ], xs=12, md=4, className="mt-2 mt-md-0")
            ])
        ], className="company-header-card")
        
        # Score Card
        score_card = html.Div([
            dcc.Graph(figure=create_score_donut(score), config={'displayModeBar': False}, style={"height": "180px"}),
            html.Div([
                html.Span("🚀 Growth", className="badge bg-primary me-2") if score_v2.get("is_growth_company") else None,
                html.Span(score_v2.get("level", ""), className="badge score-level-badge",
                    style={"backgroundColor": score_v2.get('level_color', '#71717a'),
                           "color": "#ffffff",
                           "border": "none",
                           "fontWeight": "600",
                           "padding": "8px 20px",
                           "fontSize": "0.85rem"})
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
            
            html.Hr(className="theme-hr"),
            
            # Fila 2: Márgenes
            html.H6("📊 Márgenes de Ganancia", className="mb-3 mt-3"),
            dbc.Row([
                dbc.Col([create_metric_card("Margen Bruto", format_ratio(ratios.get("gross_margin"), "percent"), "📦")], xs=6, md=3, className="mb-3"),
                dbc.Col([create_metric_card("Margen Operativo", format_ratio(ratios.get("operating_margin"), "percent"), "⚙️")], xs=6, md=3, className="mb-3"),
                dbc.Col([create_metric_card("Margen Neto", format_ratio(ratios.get("net_margin"), "percent"), "💎")], xs=6, md=3, className="mb-3"),
                dbc.Col([create_metric_card("Margen EBITDA", format_ratio(ratios.get("ebitda_margin"), "percent"), "📈")], xs=6, md=3, className="mb-3"),
            ], className="mb-3"),
            
            html.Hr(className="theme-hr"),
            
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
            
            html.Hr(className="theme-hr"),
            
            # Fila 2: Apalancamiento
            html.H6("⚖️ Apalancamiento (Largo Plazo)", className="mb-3 mt-3"),
            dbc.Row([
                dbc.Col([create_metric_card("Deuda/Equity", format_ratio(ratios.get("debt_to_equity"), "multiple"), "⚖️")], xs=6, md=3, className="mb-3"),
                dbc.Col([create_metric_card("Deuda/Activos", format_ratio(ratios.get("debt_to_assets"), "percent"), "📉")], xs=6, md=3, className="mb-3"),
                dbc.Col([create_metric_card("Deuda Neta/EBITDA", format_ratio(ratios.get("net_debt_to_ebitda"), "multiple"), "🔗")], xs=6, md=3, className="mb-3"),
                dbc.Col([create_metric_card("Deuda Total", format_ratio(ratios.get("total_debt"), "currency"), "💳")], xs=6, md=3, className="mb-3"),
            ], className="mb-3"),
            
            html.Hr(className="theme-hr"),
            
            # Fila 3: Cobertura y Flujo
            html.H6("🛡️ Cobertura y Flujo de Caja", className="mb-3 mt-3"),
            dbc.Row([
                dbc.Col([create_metric_card("Cobertura Int.", format_ratio(ratios.get("interest_coverage"), "multiple"), "🛡️")], xs=6, md=3, className="mb-3"),
                dbc.Col([create_metric_card("FCF", format_ratio(ratios.get("fcf"), "currency"), "💵")], xs=6, md=3, className="mb-3"),
                dbc.Col([create_metric_card("FCF/Deuda", format_ratio(ratios.get("fcf_to_debt"), "percent"), "📈")], xs=6, md=3, className="mb-3"),
                dbc.Col([create_metric_card("Cash & Eq.", format_ratio(ratios.get("cash_and_equivalents"), "currency"), "🏦")], xs=6, md=3, className="mb-3"),
            ])
        ])
        
        # Tab Histórico - obtener gráfico y datos de rendimiento
        price_chart, ytd_pct, ytd_end = create_price_chart(symbol, "1y")
        ytd_is_positive = ytd_pct >= 0
        
        # Obtener datos de 52 semanas
        try:
            ticker_info = yf.Ticker(symbol).info
            week_high = ticker_info.get("fiftyTwoWeekHigh")
            week_low = ticker_info.get("fiftyTwoWeekLow")
            avg_volume = ticker_info.get("averageVolume")
        except:
            week_high, week_low, avg_volume = None, None, None
        
        # Colores del rendimiento
        pct_color = '#10b981' if ytd_is_positive else '#f43f5e'
        
        tab_historical = html.Div([
            html.H5("Histórico de Precio", className="mb-2"),
            html.P("Evolución del precio de la acción", className="text-muted small mb-3"),
            
            # Header de rendimiento (SEPARADO de la gráfica)
            html.Div([
                html.Div([
                    html.Span(f"{ytd_pct:+.1f}%", style={
                        "fontSize": "2rem",
                        "fontWeight": "700",
                        "color": pct_color
                    }),
                    html.Span(" 1 año", style={
                        "fontSize": "0.9rem",
                        "color": "#71717a",
                        "marginLeft": "8px"
                    })
                ]),
                html.Div([
                    html.Span(f"${ytd_end:.2f}", style={
                        "fontSize": "1.1rem",
                        "color": "#a1a1aa"
                    }),
                    html.Span(" precio actual", style={
                        "fontSize": "0.8rem",
                        "color": "#52525b",
                        "marginLeft": "6px"
                    })
                ])
            ], style={
                "textAlign": "center",
                "padding": "15px 0",
                "marginBottom": "10px",
                "borderBottom": "1px solid rgba(255,255,255,0.05)"
            }, id="price-performance-header"),
            
            # Selector de periodo
            html.Div([
                dbc.ButtonGroup([
                    dbc.Button("1S", id="period-1wk", color="secondary", size="sm", outline=True, className="period-btn"),
                    dbc.Button("1M", id="period-1mo", color="secondary", size="sm", outline=True, className="period-btn"),
                    dbc.Button("3M", id="period-3mo", color="secondary", size="sm", outline=True, className="period-btn"),
                    dbc.Button("6M", id="period-6mo", color="secondary", size="sm", outline=True, className="period-btn"),
                    dbc.Button("1A", id="period-1y", color="primary", size="sm", className="period-btn"),
                    dbc.Button("5A", id="period-5y", color="secondary", size="sm", outline=True, className="period-btn"),
                ], className="mb-3")
            ], className="text-center mb-3"),
            
            # Gráfico principal (default 1Y)
            html.Div(id="price-chart-container", children=[
                dcc.Graph(figure=price_chart, config={'displayModeBar': False}, id="price-chart") if price_chart else 
                    html.Div([html.P("📈 No se pudieron cargar los datos", className="text-muted text-center py-5")])
            ]),
            
            # Gráficos adicionales para otros periodos (hidden, se cargan en callbacks)
            dcc.Store(id="chart-1wk", data=None),
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
            logger.warning(f"Error calculando YTD: {e}")
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
                        html.Div("EMPRESA", className="ytd-label"),
                        html.Div(f"{stock_ytd:+.1f}%", style={
                            "color": "#22c55e" if stock_ytd > 0 else "#ef4444",
                            "fontSize": "1.8rem", "fontWeight": "700", "marginTop": "8px"
                        })
                    ], className="ytd-card", style={"borderColor": "rgba(59, 130, 246, 0.5)"})
                ], xs=12, md=4, className="mb-3"),
                dbc.Col([
                    html.Div([
                        html.Div(f"📊 vs {sector_profile.sector_etf if sector_profile else 'Sector'}", style={"color": "#22c55e", "fontWeight": "600", "fontSize": "0.9rem"}),
                        html.Div("VS SECTOR", className="ytd-label"),
                        html.Div(f"{diff_vs_sector:+.1f}%", style={
                            "color": "#22c55e" if diff_vs_sector >= 0 else "#ef4444",
                            "fontSize": "1.8rem", "fontWeight": "700", "marginTop": "8px"
                        })
                    ], className="ytd-card", style={"borderColor": "rgba(34, 197, 94, 0.5)"})
                ], xs=12, md=4, className="mb-3"),
                dbc.Col([
                    html.Div([
                        html.Div("🌐 vs SPY", style={"color": "#eab308", "fontWeight": "600", "fontSize": "0.9rem"}),
                        html.Div("VS MERCADO", className="ytd-label"),
                        html.Div(f"{diff_vs_market:+.1f}%", style={
                            "color": "#22c55e" if diff_vs_market >= 0 else "#ef4444",
                            "fontSize": "1.8rem", "fontWeight": "700", "marginTop": "8px"
                        })
                    ], className="ytd-card", style={"borderColor": "rgba(234, 179, 8, 0.5)"})
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
                            html.Th("Métrica", className="comparison-th comparison-th-metric"),
                            html.Th(symbol, className="comparison-th comparison-th-company"),
                            html.Th("Sector", className="comparison-th comparison-th-muted"),
                            html.Th("SPY", className="comparison-th comparison-th-muted"),
                            html.Th("", className="comparison-th"),
                        ])
                    ]),
                    html.Tbody(comparison_rows)
                ], className="comparison-table")
            ], className="table-responsive-wrapper"),
            
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
        
        # v2.2: DCF Dinámico con WACC y growth específicos de la empresa
        dcf_result = dcf_dynamic(
            fcf=fcf,
            shares_outstanding=shares,
            beta=financials.beta if financials else None,
            debt_to_equity=ratios.get("debt_to_equity"),
            interest_expense=financials.interest_expense if financials else None,
            total_debt=financials.total_debt if financials else None,
            revenue_growth_3y=contextual.get("revenue_cagr_3y") if contextual else None,
            fcf_growth_3y=contextual.get("fcf_cagr_3y") if contextual else None
        )
        dcf_value = dcf_result.get("fair_value")
        dcf_wacc = dcf_result.get("wacc_used")
        dcf_growth = dcf_result.get("growth_used")
        
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
                        dbc.CardHeader("💵 Método DCF Dinámico"),
                        dbc.CardBody([
                            html.P([
                                "Flujos descontados · ",
                                html.Span(f"WACC {dcf_wacc:.1%}" if dcf_wacc else "", className="text-info"),
                                " · ",
                                html.Span(f"Growth {dcf_growth:.1%}" if dcf_growth else "", className="text-info")
                            ], className="text-muted small"),
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
            
            # MÉTRICAS INSTITUCIONALES
            html.H6("🏛️ Métricas Institucionales", className="mb-3"),
            dbc.Row([
                # Altman Z-Score
                dbc.Col([
                    html.Div([
                        html.Div("📊 Altman Z-Score", className="institutional-title"),
                        html.Div([
                            html.Span(f"{alerts.get('altman_z_score', {}).get('value', 0):.2f}" if alerts.get('altman_z_score', {}).get('value') else "N/A", 
                                     className="institutional-value",
                                     style={
                                         "color": "#22c55e" if alerts.get('altman_z_score', {}).get('level') == "SAFE" else 
                                                  "#eab308" if alerts.get('altman_z_score', {}).get('level') == "GREY" else "#ef4444"
                                     }),
                            html.Span(
                                " · Zona Segura" if alerts.get('altman_z_score', {}).get('level') == "SAFE" else
                                " · Zona Gris" if alerts.get('altman_z_score', {}).get('level') == "GREY" else
                                " · Zona de Riesgo",
                                className="institutional-label"
                            )
                        ]),
                        html.P(alerts.get('altman_z_score', {}).get('interpretation', ''), className="institutional-desc")
                    ], className="institutional-card")
                ], xs=12, md=6, className="mb-3"),
                
                # Piotroski F-Score
                dbc.Col([
                    html.Div([
                        html.Div("📈 Piotroski F-Score", className="institutional-title"),
                        html.Div([
                            html.Span(f"{alerts.get('piotroski_f_score', {}).get('value', 0)}/9" if alerts.get('piotroski_f_score', {}).get('value') is not None else "N/A", 
                                     className="institutional-value",
                                     style={
                                         "color": "#22c55e" if (alerts.get('piotroski_f_score', {}).get('value') or 0) >= 7 else 
                                                  "#eab308" if (alerts.get('piotroski_f_score', {}).get('value') or 0) >= 4 else "#ef4444"
                                     }),
                            html.Span(
                                " · Fuerte" if (alerts.get('piotroski_f_score', {}).get('value') or 0) >= 7 else
                                " · Neutral" if (alerts.get('piotroski_f_score', {}).get('value') or 0) >= 4 else
                                " · Débil",
                                className="institutional-label"
                            )
                        ]),
                        html.P(alerts.get('piotroski_f_score', {}).get('interpretation', ''), className="institutional-desc")
                    ], className="institutional-card")
                ], xs=12, md=6, className="mb-3"),
            ]),
            
            html.Hr(),
            
            # DESGLOSE DEL SCORE - Con detalles desplegables elegantes
            html.H6("📊 Desglose del Score (5 categorías × 20 pts)", className="mb-3"),
            html.Div([
                html.Div([
                    # Header clickeable con categoría y puntuación
                    html.Div([
                        html.Div([
                            html.Span(f"{cat.get('emoji', '📊')} {cat.get('category', 'N/A')}", 
                                     className="score-category-name"),
                        ], style={"flex": "1"}),
                        html.Span(f"{cat.get('score', 0)}/{cat.get('max_score', 20)}",
                            className="score-value",
                            style={
                                "color": "#22c55e" if cat.get('score', 0) >= 15 else 
                                         "#eab308" if cat.get('score', 0) >= 10 else "#ef4444"
                            }),
                        # Botón ver detalles
                        html.Span("ver detalles ›", 
                            id={"type": "score-detail-toggle", "index": i},
                            n_clicks=0,
                            className="score-detail-btn")
                    ], style={"display": "flex", "alignItems": "center", "marginBottom": "8px"}),
                    
                    # Barra de progreso
                    dbc.Progress(value=cat.get('score', 0), max=cat.get('max_score', 20), 
                                style={"height": "6px"}, className="score-progress-bar"),
                    
                    # Contenido desplegable con ajustes
                    dbc.Collapse(
                        html.Div([
                            html.Div([
                                html.Div([
                                    # Indicador +/-
                                    html.Span(
                                        f"+{adj.get('adjustment', 0)}" if adj.get('adjustment', 0) > 0 else str(adj.get('adjustment', 0)),
                                        style={
                                            "fontSize": "0.8rem", "fontWeight": "700", "minWidth": "32px",
                                            "color": "#22c55e" if adj.get('adjustment', 0) > 0 else "#ef4444",
                                        }
                                    ),
                                    # Métrica
                                    html.Span(adj.get('metric', ''), className="adjustment-metric"),
                                    # Razón
                                    html.Span(adj.get('reason', ''), className="adjustment-reason")
                                ], className="adjustment-row")
                            ]) for adj in cat.get('adjustments', [])
                        ] if cat.get('adjustments') else [
                            html.P("Sin ajustes registrados", className="no-adjustments-text")
                        ], style={"marginTop": "12px", "paddingLeft": "4px"}),
                        id={"type": "score-detail-collapse", "index": i},
                        is_open=False
                    )
                    
                ], className="score-category-box") for i, cat in enumerate(categories)
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
                        html.Div("🎯 TOTAL", className="score-summary-label"),
                        html.Div(f"{score}/100", style={"color": score_color, "fontSize": "1.8rem", "fontWeight": "700"})
                    ], className="score-summary-card score-total-card")
                ], xs=6, md=2, className="mb-3"),
            ], className="justify-content-center"),
            
            html.Hr(),
            
            # SEÑALES DETECTADAS
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
            
            # LISTA DE ALERTAS - Estilo simple con cajas
            html.Div([
                html.H6("🔴 Señales de Riesgo", className="text-danger") if danger_alerts else None,
                html.Div([
                    html.Div([
                        html.Strong(f"{cat}: "), 
                        html.Span(reason),
                        html.Div(get_alert_explanation(cat, reason), className="text-muted small mt-1")
                    ], className="alert-box alert-danger-custom mb-2")
                    for cat, reason in danger_alerts[:5]
                ]) if danger_alerts else None,
                
                html.H6("🟠 Advertencias", className="text-warning mt-3") if warning_alerts else None,
                html.Div([
                    html.Div([
                        html.Strong(f"{cat}: "), 
                        html.Span(reason),
                        html.Div(get_alert_explanation(cat, reason), className="text-muted small mt-1")
                    ], className="alert-box alert-warning-custom mb-2")
                    for cat, reason in warning_alerts[:5]
                ]) if warning_alerts else None,
                
                html.H6("🟢 Fortalezas", className="text-success mt-3") if success_alerts else None,
                html.Div([
                    html.Div([
                        html.Strong(f"{cat}: "), 
                        html.Span(reason),
                        html.Div(get_alert_explanation(cat, reason), className="text-muted small mt-1")
                    ], className="alert-box alert-success-custom mb-2")
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
        
        # ENRIQUECER ratios con datos adicionales para el PDF
        ratios["price"] = financials.price if financials else None
        ratios["revenue"] = financials.revenue if financials else None
        ratios["total_debt"] = financials.total_debt if financials else None
        ratios["shares_outstanding"] = financials.shares_outstanding if financials else None
        ratios["cash_and_equivalents"] = financials.cash if financials else None
        ratios["fifty_two_week_high"] = week_high
        ratios["fifty_two_week_low"] = week_low
        ratios["average_volume"] = avg_volume
        
        # Calcular working_capital si tenemos los datos
        if financials and financials.current_assets and financials.current_liabilities:
            ratios["working_capital"] = financials.current_assets - financials.current_liabilities
        
        # Calcular book_value_per_share si tenemos los datos
        if financials and financials.total_equity and financials.shares_outstanding:
            ratios["book_value_per_share"] = financials.total_equity / financials.shares_outstanding
        
        # Calcular fcf_to_debt si tenemos los datos
        if ratios.get("fcf") and financials and financials.total_debt and financials.total_debt > 0:
            ratios["fcf_to_debt"] = ratios["fcf"] / financials.total_debt
        
        # DEBUG: Verificar que score_v2 está en alerts antes de guardar
        logger.debug(f"[SAVE] Guardando datos para {symbol}")
        logger.debug(f"[SAVE] alerts tiene score_v2: {'score_v2' in alerts}")
        if 'score_v2' in alerts:
            sv2 = alerts['score_v2']
            logger.debug(f"[SAVE] score_v2.total_score: {sv2.get('total_score', 'NO EXISTE')}")
            logger.debug(f"[SAVE] score_v2.level: {sv2.get('level', 'NO EXISTE')}")
            logger.debug(f"[SAVE] score_v2.category_scores: {sv2.get('category_scores', 'NO EXISTE')}")
        
        stored_data = {"symbol": symbol, "company_name": company_name, "ratios": ratios, "alerts": alerts}
        
        return (
            {"display": "none"}, {"display": "block"},
            company_header, score_card, key_metrics, sector_notes,
            tab_valuation, tab_profitability, tab_health, tab_historical, tab_comparison, tab_intrinsic, tab_evaluation,
            footer, stored_data, symbol, None, None, stock_badge, "", hide_suggestions
        )
        
    except Exception as e:
        traceback.print_exc()
        error_msg = dbc.Alert(f"❌ Error al analizar '{symbol}': {str(e)}", color="danger", dismissable=True)
        return home_style, analysis_style, *empty_outputs, "", error_msg, None, None, "", hide_suggestions


# Callback para cambiar periodo del gráfico histórico
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
    if not symbol:
        return no_update, *["secondary"]*6, *[True]*6, no_update
    
    triggered_id = ctx.triggered_id
    
    period_map = {
        "period-1wk": "5d",
        "period-1mo": "1mo",
        "period-3mo": "3mo",
        "period-6mo": "6mo",
        "period-1y": "1y",
        "period-5y": "5y"
    }
    
    period_labels = {
        "period-1wk": "1 semana",
        "period-1mo": "1 mes",
        "period-3mo": "3 meses",
        "period-6mo": "6 meses",
        "period-1y": "1 año",
        "period-5y": "5 años"
    }
    
    period = period_map.get(triggered_id, "1y")
    period_label = period_labels.get(triggered_id, "1 año")
    
    # Crear gráfico y obtener datos de rendimiento en una sola llamada
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
        chart_component = dcc.Graph(figure=chart, config={'displayModeBar': False}, id="price-chart")
    else:
        chart_component = html.Div([html.P("📈 No se pudieron cargar los datos", className="text-muted text-center py-5")])
    
    # Colores de botones
    colors = ["secondary"] * 6
    outlines = [True] * 6
    
    button_order = ["period-1wk", "period-1mo", "period-3mo", "period-6mo", "period-1y", "period-5y"]
    if triggered_id in button_order:
        idx = button_order.index(triggered_id)
        colors[idx] = "primary"
        outlines[idx] = False
    
    return chart_component, *colors, *outlines, performance_header


# Callback para expandir/colapsar detalles del score
@callback(
    Output({"type": "score-detail-collapse", "index": MATCH}, "is_open"),
    Input({"type": "score-detail-toggle", "index": MATCH}, "n_clicks"),
    State({"type": "score-detail-collapse", "index": MATCH}, "is_open"),
    prevent_initial_call=True
)
def toggle_score_details(n_clicks, is_open):
    if n_clicks:
        return not is_open
    return is_open


# Callback para descargar PDF
@callback(
    Output("download-pdf", "data"),
    Input("download-pdf-btn", "n_clicks"),
    State("analysis-data", "data"),
    prevent_initial_call=True
)
def download_pdf(n_clicks, analysis_data):
    logger.debug(f"[PDF] Click #{n_clicks}, data exists: {analysis_data is not None}")
    
    if not n_clicks or n_clicks == 0:
        return no_update
    
    if not analysis_data:
        logger.warning("[PDF] No hay datos de análisis")
        return no_update
    
    try:
        symbol = analysis_data.get("symbol", "UNKNOWN")
        company_name = analysis_data.get("company_name", symbol)
        ratios = analysis_data.get("ratios", {})
        alerts = analysis_data.get("alerts", {})
        
        logger.debug(f"[PDF] Generando para {symbol}...")
        logger.debug(f"[PDF] alerts keys: {list(alerts.keys()) if alerts else 'VACIO'}")
        
        score_v2 = alerts.get("score_v2", {})
        logger.debug(f"[PDF] score_v2 existe: {bool(score_v2)}")
        logger.debug(f"[PDF] score_v2 keys: {list(score_v2.keys()) if score_v2 else 'VACIO'}")
        
        score = score_v2.get("score", 50)  # CORREGIDO: usar "score" no "total_score"
        logger.debug(f"[PDF] score final: {score}")
        logger.debug(f"[PDF] level: {score_v2.get('level', 'N/A')}")
        logger.debug(f"[PDF] category_scores: {score_v2.get('category_scores', {})}")
        
        # Generar PDF
        pdf_bytes = generate_simple_pdf(symbol, company_name, ratios, alerts, score)
        
        logger.info(f"[PDF] OK - {len(pdf_bytes)} bytes generados para {symbol}")
        
        # Guardar temporalmente y enviar
        import tempfile
        
        filename = f"analisis_{symbol}_{datetime.now().strftime('%Y%m%d')}.pdf"
        temp_path = os.path.join(tempfile.gettempdir(), filename)
        
        with open(temp_path, 'wb') as f:
            f.write(pdf_bytes)
        
        logger.debug(f"[PDF] Guardado en {temp_path}")
        
        return dcc.send_file(temp_path)
        
    except Exception as e:
        logger.error(f"[PDF] Error generando PDF: {e}", exc_info=True)
        return no_update


# =============================================================================
# THEME TOGGLE CALLBACKS
# =============================================================================

# Callback clientside para cambiar el tema (máxima performance)
app.clientside_callback(
    """
    function(n_clicks, currentTheme) {
        // Determinar nuevo tema
        let newTheme = currentTheme === 'light' ? 'dark' : 'light';
        
        // Si es el primer click y no hay tema guardado, empezar con dark
        if (n_clicks === 0) {
            newTheme = currentTheme || 'dark';
        }
        
        // Aplicar tema al documento
        document.documentElement.setAttribute('data-theme', newTheme);
        
        // Guardar en localStorage para persistencia
        localStorage.setItem('stock-analyzer-theme', newTheme);
        
        // Actualizar icono del botón y colores
        const btn = document.getElementById('theme-toggle');
        const sunIcon = document.getElementById('icon-sun');
        const moonIcon = document.getElementById('icon-moon');
        
        if (sunIcon && moonIcon) {
            if (newTheme === 'light') {
                sunIcon.style.display = 'none';
                moonIcon.style.display = 'block';
            } else {
                sunIcon.style.display = 'block';
                moonIcon.style.display = 'none';
            }
        }
        
        // Cambiar colores del botón según el tema
        if (btn) {
            if (newTheme === 'light') {
                btn.style.backgroundColor = '#ffffff';
                btn.style.borderColor = '#d4d4d8';
                btn.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.15)';
            } else {
                btn.style.backgroundColor = '#18181b';
                btn.style.borderColor = '#3f3f46';
                btn.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.4)';
            }
        }
        
        // NUEVO: Cambiar estilos inline de elementos con colores hardcoded
        applyThemeToInlineStyles(newTheme);
        
        return newTheme;
    }
    """,
    Output("theme-store", "data"),
    Input("theme-toggle", "n_clicks"),
    State("theme-store", "data"),
    prevent_initial_call=False
)

# Callback para inicializar tema al cargar la página
app.clientside_callback(
    """
    function(theme) {
        // Verificar si hay tema guardado en localStorage
        const savedTheme = localStorage.getItem('stock-analyzer-theme');
        const themeToApply = savedTheme || theme || 'dark';
        
        // Aplicar tema al documento
        document.documentElement.setAttribute('data-theme', themeToApply);
        
        // Actualizar icono del botón
        const btn = document.getElementById('theme-toggle');
        const sunIcon = document.getElementById('icon-sun');
        const moonIcon = document.getElementById('icon-moon');
        
        if (sunIcon && moonIcon) {
            if (themeToApply === 'light') {
                sunIcon.style.display = 'none';
                moonIcon.style.display = 'block';
            } else {
                sunIcon.style.display = 'block';
                moonIcon.style.display = 'none';
            }
        }
        
        // Cambiar colores del botón según el tema
        if (btn) {
            if (themeToApply === 'light') {
                btn.style.backgroundColor = '#ffffff';
                btn.style.borderColor = '#d4d4d8';
                btn.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.15)';
            } else {
                btn.style.backgroundColor = '#18181b';
                btn.style.borderColor = '#3f3f46';
                btn.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.4)';
            }
        }
        
        // NUEVO: Aplicar tema a estilos inline después de un pequeño delay
        setTimeout(() => applyThemeToInlineStyles(themeToApply), 100);
        
        // Observer para aplicar a nuevos elementos
        if (!window.themeObserver) {
            window.themeObserver = new MutationObserver(() => {
                const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
                applyThemeToInlineStyles(currentTheme);
            });
            window.themeObserver.observe(document.body, { childList: true, subtree: true });
        }
        
        return window.dash_clientside.no_update;
    }
    """,
    Output("theme-toggle", "title"),  # Dummy output
    Input("theme-store", "data"),
    prevent_initial_call=False
)

# Definir la función JavaScript global para cambiar estilos inline
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <script>
        function applyThemeToInlineStyles(theme) {
            const isLight = theme === 'light';
            
            // Colores para cada tema
            const colors = {
                light: {
                    textPrimary: '#1e293b',
                    textSecondary: '#475569',
                    textMuted: '#64748b',
                    bgPrimary: '#ffffff',
                    bgSecondary: '#f8fafc',
                    bgTertiary: '#f1f5f9',
                    border: '#e2e8f0'
                },
                dark: {
                    textPrimary: '#fafafa',
                    textSecondary: '#a1a1aa',
                    textMuted: '#71717a',
                    bgPrimary: '#09090b',
                    bgSecondary: '#18181b',
                    bgTertiary: '#27272a',
                    border: '#3f3f46'
                }
            };
            
            const c = isLight ? colors.light : colors.dark;
            
            // Lista de colores claros de texto (para dark mode) que deben cambiar en light mode
            const lightTextColors = ['#fff', '#ffffff', 'white', '#fafafa', '#d4d4d8', '#f4f4f5', 'rgb(255', 'rgb(250', 'rgb(212'];
            const mutedTextColors = ['#71717a', '#a1a1aa', '#52525b', 'rgb(113', 'rgb(161', 'rgb(82'];
            const accentColors = ['#a5b4fc', '#60a5fa', 'rgb(165', 'rgb(96'];
            
            // Cambiar colores de texto
            document.querySelectorAll('[style]').forEach(el => {
                const style = el.getAttribute('style') || '';
                if (!style.includes('color')) return;
                
                // No modificar botones
                if (el.closest('button') || el.closest('[class*="btn"]') || el.closest('.download-btn')) {
                    return;
                }
                
                // No modificar colores de estado (verde, rojo, amarillo)
                if (style.includes('#22c55e') || style.includes('#ef4444') || style.includes('#eab308') || 
                    style.includes('#10b981') || style.includes('#f43f5e') || style.includes('#3b82f6') ||
                    style.includes('rgb(34, 197') || style.includes('rgb(239, 68') || style.includes('rgb(234, 179')) {
                    return;
                }
                
                // Texto claro -> oscuro
                if (lightTextColors.some(c => style.includes(c))) {
                    el.style.color = c.textPrimary;
                }
                
                // Texto muted
                if (mutedTextColors.some(col => style.includes(col))) {
                    el.style.color = c.textMuted;
                }
                
                // Texto accent
                if (accentColors.some(col => style.includes(col))) {
                    el.style.color = isLight ? '#4f46e5' : '#a5b4fc';
                }
            });
            
            // Cambiar backgrounds
            document.querySelectorAll('[style*="background"]').forEach(el => {
                const style = el.getAttribute('style') || '';
                
                // No cambiar botones con colores de acento
                if (style.includes('#6366f1') || style.includes('#818cf8') || 
                    style.includes('#22c55e') || style.includes('#ef4444') ||
                    style.includes('#eab308') || style.includes('#3b82f6') ||
                    style.includes('linear-gradient')) {
                    return;
                }
                
                // Backgrounds oscuros
                if (style.includes('#09090b') || style.includes('rgb(9, 9, 11)')) {
                    el.style.backgroundColor = c.bgPrimary;
                }
                if (style.includes('#18181b') || style.includes('rgb(24, 24, 27)') || style.includes('#1f1f23')) {
                    el.style.backgroundColor = c.bgSecondary;
                }
                if (style.includes('#27272a') || style.includes('rgb(39, 39, 42)')) {
                    el.style.backgroundColor = c.bgTertiary;
                }
            });
            
            // Cambiar bordes
            document.querySelectorAll('[style*="border"]').forEach(el => {
                const style = el.getAttribute('style') || '';
                if (style.includes('#3f3f46') || style.includes('rgb(63, 63, 70)')) {
                    el.style.borderColor = c.border;
                }
            });
            
            // Asegurar que las tablas sean legibles
            document.querySelectorAll('table td, table th').forEach(el => {
                el.style.color = c.textPrimary;
                el.style.backgroundColor = c.bgSecondary;
                el.style.borderColor = c.border;
            });
            
            // Headers de tabla
            document.querySelectorAll('table thead th').forEach(el => {
                el.style.backgroundColor = c.bgTertiary;
            });
        }
        </script>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''


if __name__ == "__main__":
    # Debug mode controlado por variable de entorno (default: False para producción)
    debug_mode = os.getenv("DEBUG", "false").lower() == "true"
    port = int(os.getenv("PORT", 8050))
    
    logger.info(f"Starting Stock Analyzer - Debug: {debug_mode}, Port: {port}")
    app.run(debug=debug_mode, host="0.0.0.0", port=port)
