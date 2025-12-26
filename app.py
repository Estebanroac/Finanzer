"""
Finanzer v3.1.2 - Clean Architecture
==================================
Aplicación web responsive para análisis fundamental de acciones.
Mobile-first design con soporte para dark/light theme.

Autor: Esteban
Versión: 3.1.2 - Bugfixes, limpieza de código, formatters centralizados
"""

import os
import sys

# Fix para deploys en Render/Heroku: asegurar que el directorio actual esté en PYTHONPATH
APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

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
import yfinance as yf

# Importar módulos del analizador
from financial_ratios import (
    calculate_all_ratios,
    aggregate_alerts,
    format_ratio,
    graham_number,
    dcf_multi_stage_dynamic,
    dcf_sensitivity_analysis,
    calculate_reit_metrics,
    is_reit_sector,
)
from data_fetcher import (
    FinancialDataService, 
    InvalidSymbolError, 
    APITimeoutError,
    DataFetchError
)
from sector_profiles import get_sector_profile
from stock_database import search_stocks, POPULAR_STOCKS

# Componentes UI refactorizados
from finanzer.components.tooltips import METRIC_TOOLTIPS, LABEL_TO_TOOLTIP, get_tooltip_text
from finanzer.components.cards import (
    create_metric_card, 
    create_metric_with_tooltip, 
    create_info_icon,
    create_score_summary_card,
    reset_tooltip_counter
)
from finanzer.components.tables import create_comparison_metric_row
from finanzer.components.sensitivity import build_sensitivity_section
from finanzer.components.charts import (
    get_score_color, 
    create_score_donut,
    create_price_chart,
    create_ytd_comparison_chart
)
from finanzer.components.pdf_generator import generate_simple_pdf

# Utilidades
from finanzer.utils.search import resolve_symbol, COMPANY_NAMES
from finanzer.utils.formatters import fmt, get_metric_color
from finanzer.analysis.alerts import get_alert_explanation
from finanzer.analysis.sectors import get_sector_metrics_config

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
    title="Finanzer"
)

server = app.server

# =============================================================================
# CONSTANTES
# =============================================================================

QUICK_PICKS = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "JPM", "V", "TSM"]

# =============================================================================
# LAYOUT PRINCIPAL
# =============================================================================

app.layout = dbc.Container([
    dcc.Store(id="analysis-data", storage_type="memory"),
    dcc.Store(id="current-symbol", data="", storage_type="memory"),
    dcc.Store(id="comparison-stocks", data=[], storage_type="session"),  # v2.9: Lista de acciones para comparar
    dcc.Store(id="theme-store", data="dark", storage_type="local"),  # Persiste en localStorage
    dcc.Store(id="search-history", data=[], storage_type="local"),  # v3.0: Historial de búsquedas
    dcc.Store(id="watchlist", data=[], storage_type="local"),  # v3.0.1: Watchlist/Favoritos
    dcc.Download(id="download-pdf"),
    
    # Loading indicator (NO fullscreen para no bloquear sugerencias)
    html.Div(id="loading-trigger", style={"display": "none"}),
    
    # Loading overlay mejorado
    html.Div(id="loading-overlay", children=[
        html.Div([
            html.Div(className="loading-spinner", style={
                "width": "48px",
                "height": "48px",
                "border": "4px solid rgba(16, 185, 129, 0.2)",
                "borderTopColor": "#10b981",
                "borderRadius": "50%",
                "animation": "spin 0.8s linear infinite",
                "margin": "0 auto 16px auto"
            }),
            html.P("Analizando...", style={
                "color": "#a1a1aa",
                "fontSize": "1rem",
                "marginBottom": "8px"
            }),
            html.P(id="loading-symbol", children="", style={
                "color": "#10b981",
                "fontSize": "1.2rem",
                "fontWeight": "600"
            })
        ], style={
            "textAlign": "center",
            "padding": "40px"
        })
    ], style={
        "display": "none",
        "position": "fixed",
        "top": "0",
        "left": "0",
        "right": "0",
        "bottom": "0",
        "backgroundColor": "rgba(24, 24, 27, 0.9)",
        "backdropFilter": "blur(4px)",
        "zIndex": "9999",
        "justifyContent": "center",
        "alignItems": "center"
    }),
    
    # =========================================================================
    # NAVBAR PERSISTENTE CON BÚSQUEDA
    # =========================================================================
    html.Div([
        dbc.Row([
            # Logo/Home
            dbc.Col([
                html.Div([
                    html.Span("📊", style={"fontSize": "1.5rem", "marginRight": "10px"}),
                    html.Span("Finanzer", style={
                        "fontSize": "1.3rem", "fontWeight": "700", "cursor": "pointer",
                        "background": "linear-gradient(135deg, #34d399 0%, #10b981 100%)",
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
                            "backgroundColor": "#10b981",
                            "border": "1px solid #10b981",
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
                "background": "linear-gradient(135deg, #10b981 0%, #059669 100%)",
                "borderRadius": "20px", "display": "flex",
                "alignItems": "center", "justifyContent": "center",
                "margin": "0 auto 25px auto",
                "boxShadow": "0 15px 50px rgba(16, 185, 129, 0.4)"
            }),
            
            # Título
            html.H1("Finanzer", style={
                "fontSize": "3rem", "fontWeight": "800",
                "background": "linear-gradient(135deg, #34d399 0%, #10b981 100%)",
                "WebkitBackgroundClip": "text", "WebkitTextFillColor": "transparent",
                "backgroundClip": "text", "marginBottom": "12px", "letterSpacing": "-0.02em"
            }),
            
            # Subtítulo
            html.P("Análisis fundamental de acciones para decisiones de inversión informadas",
                  className="home-subtitle"),
            
            # Quick Pills - usando html.Button para evitar override de Bootstrap
            html.Div([
                html.Button(ticker, id={"type": "quick-pick", "index": ticker},
                          n_clicks=0,
                          style={
                              "background": "rgba(16, 185, 129, 0.15)",
                              "border": "1px solid rgba(16, 185, 129, 0.4)",
                              "color": "#34d399", 
                              "borderRadius": "25px",
                              "padding": "10px 22px", 
                              "margin": "5px",
                              "fontWeight": "500", 
                              "fontSize": "0.9rem",
                              "cursor": "pointer",
                              "transition": "all 0.2s ease"
                          })
                for ticker in QUICK_PICKS
            ], style={"textAlign": "center", "marginBottom": "40px"}),
            
            # Búsquedas recientes (se llena dinámicamente)
            html.Div(id="recent-searches-container", children=[
                # Se actualiza via callback cuando hay historial
            ], style={"textAlign": "center", "marginBottom": "20px"}),
            
            # Watchlist/Favoritos (se llena dinámicamente)
            html.Div(id="watchlist-container", children=[
                # Se actualiza via callback cuando hay favoritos
            ], style={"textAlign": "center", "marginBottom": "30px"}),
            
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
        
        # Screener: Estrategias de Inversión
        html.Div([
            html.H5("🎯 Estrategias de Inversión", className="text-center mb-3", style={"color": "#a1a1aa"}),
            html.P("Acciones seleccionadas por estrategia", className="text-muted small text-center mb-4"),
            
            html.Div([
                # Value Investing
                html.Button([
                    html.Div("💎", style={"fontSize": "2rem", "marginBottom": "12px"}),
                    html.Div("Value", style={"fontWeight": "600", "fontSize": "1rem", "marginBottom": "4px"}),
                    html.Div("Bajo P/E", className="text-muted", style={"fontSize": "0.75rem"})
                ], id="strategy-value", n_clicks=0, style={
                    "background": "rgba(59, 130, 246, 0.1)",
                    "border": "1px solid rgba(59, 130, 246, 0.3)",
                    "borderRadius": "12px",
                    "padding": "20px",
                    "color": "#60a5fa",
                    "cursor": "pointer",
                    "transition": "all 0.2s ease",
                    "width": "140px",
                    "height": "140px",
                    "display": "flex",
                    "flexDirection": "column",
                    "alignItems": "center",
                    "justifyContent": "center"
                }),
                
                # Growth
                html.Button([
                    html.Div("🚀", style={"fontSize": "2rem", "marginBottom": "12px"}),
                    html.Div("Growth", style={"fontWeight": "600", "fontSize": "1rem", "marginBottom": "4px"}),
                    html.Div("Alto crecimiento", className="text-muted", style={"fontSize": "0.75rem"})
                ], id="strategy-growth", n_clicks=0, style={
                    "background": "rgba(16, 185, 129, 0.1)",
                    "border": "1px solid rgba(16, 185, 129, 0.3)",
                    "borderRadius": "12px",
                    "padding": "20px",
                    "color": "#34d399",
                    "cursor": "pointer",
                    "transition": "all 0.2s ease",
                    "width": "140px",
                    "height": "140px",
                    "display": "flex",
                    "flexDirection": "column",
                    "alignItems": "center",
                    "justifyContent": "center"
                }),
                
                # Dividends
                html.Button([
                    html.Div("💰", style={"fontSize": "2rem", "marginBottom": "12px"}),
                    html.Div("Dividendos", style={"fontWeight": "600", "fontSize": "1rem", "marginBottom": "4px"}),
                    html.Div("Income investing", className="text-muted", style={"fontSize": "0.75rem"})
                ], id="strategy-dividend", n_clicks=0, style={
                    "background": "rgba(245, 158, 11, 0.1)",
                    "border": "1px solid rgba(245, 158, 11, 0.3)",
                    "borderRadius": "12px",
                    "padding": "20px",
                    "color": "#F59E0B",
                    "cursor": "pointer",
                    "transition": "all 0.2s ease",
                    "width": "140px",
                    "height": "140px",
                    "display": "flex",
                    "flexDirection": "column",
                    "alignItems": "center",
                    "justifyContent": "center"
                }),
                
                # Blue Chips
                html.Button([
                    html.Div("🏛️", style={"fontSize": "2rem", "marginBottom": "12px"}),
                    html.Div("Blue Chips", style={"fontWeight": "600", "fontSize": "1rem", "marginBottom": "4px"}),
                    html.Div("Mega caps", className="text-muted", style={"fontSize": "0.75rem"})
                ], id="strategy-bluechip", n_clicks=0, style={
                    "background": "rgba(139, 92, 246, 0.1)",
                    "border": "1px solid rgba(139, 92, 246, 0.3)",
                    "borderRadius": "12px",
                    "padding": "20px",
                    "color": "#A78BFA",
                    "cursor": "pointer",
                    "transition": "all 0.2s ease",
                    "width": "140px",
                    "height": "140px",
                    "display": "flex",
                    "flexDirection": "column",
                    "alignItems": "center",
                    "justifyContent": "center"
                }),
                
            ], style={
                "display": "flex", 
                "justifyContent": "center", 
                "gap": "20px", 
                "flexWrap": "wrap"
            }),
            
            # Resultados del screener
            html.Div(id="screener-results", className="mt-4"),
            
        ], style={"maxWidth": "800px", "margin": "0 auto 40px auto", "padding": "0 20px"}),
        
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
        
        # Botones de descarga y favorito
        html.Div([
            html.Button([
                html.Span("📄", style={"marginRight": "8px"}),
                html.Span("Descargar PDF", className="btn-text-white")
            ], id="download-pdf-btn", n_clicks=0, className="download-btn"),
            
            # Botón favorito minimalista (solo icono)
            html.Button(
                id="toggle-watchlist-btn", 
                n_clicks=0,
                children=[html.Span(id="watchlist-icon", children="☆", style={"fontSize": "1.3rem"})],
                style={
                    "background": "transparent",
                    "border": "2px solid rgba(245, 158, 11, 0.4)",
                    "borderRadius": "50%",
                    "width": "48px",
                    "height": "48px",
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "center",
                    "cursor": "pointer",
                    "transition": "all 0.2s ease",
                    "color": "#F59E0B"
                },
                title="Añadir a Watchlist"
            ),
        ], className="text-center mb-4", style={"display": "flex", "justifyContent": "center", "alignItems": "center", "gap": "16px"}),
        
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
        "border": "1px solid rgba(16, 185, 129, 0.5)",
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
                    "color": "#10b981", "fontWeight": "700", "fontSize": "0.95rem",
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


# Callback para mostrar búsquedas recientes en el home
@callback(
    Output("recent-searches-container", "children"),
    Input("search-history", "data"),
)
def update_recent_searches(history):
    """Muestra las últimas búsquedas del usuario."""
    if not history or len(history) == 0:
        return None
    
    # Mostrar máximo 5 búsquedas recientes
    recent = history[:5]
    
    return html.Div([
        html.P("🕐 Búsquedas recientes", className="text-muted small mb-2"),
        html.Div([
            html.Button(
                f"{item['symbol']}",
                id={"type": "recent-search", "index": item['symbol']},
                n_clicks=0,
                style={
                    "background": "rgba(59, 130, 246, 0.1)",
                    "border": "1px solid rgba(59, 130, 246, 0.3)",
                    "color": "#60a5fa",
                    "borderRadius": "20px",
                    "padding": "6px 14px",
                    "margin": "3px",
                    "fontWeight": "500",
                    "fontSize": "0.8rem",
                    "cursor": "pointer",
                    "transition": "all 0.2s ease"
                }
            )
            for item in recent
        ], style={"display": "flex", "flexWrap": "wrap", "justifyContent": "center", "gap": "4px"})
    ])


# Callback para mostrar watchlist en el home
@callback(
    Output("watchlist-container", "children"),
    Input("watchlist", "data"),
)
def update_watchlist_display(watchlist):
    """Muestra los favoritos del usuario."""
    if not watchlist or len(watchlist) == 0:
        return None
    
    return html.Div([
        html.P("⭐ Mi Watchlist", className="text-muted small mb-2"),
        html.Div([
            html.Button(
                [
                    html.Span(f"{item['symbol']}", style={"marginRight": "6px"}),
                    html.Span(
                        f"({item.get('score', '?')}/100)" if item.get('score') else "",
                        style={"fontSize": "0.7rem", "opacity": "0.8"}
                    )
                ],
                id={"type": "watchlist-item", "index": item['symbol']},
                n_clicks=0,
                style={
                    "background": "rgba(245, 158, 11, 0.15)",
                    "border": "1px solid rgba(245, 158, 11, 0.4)",
                    "color": "#F59E0B",
                    "borderRadius": "20px",
                    "padding": "6px 14px",
                    "margin": "3px",
                    "fontWeight": "500",
                    "fontSize": "0.8rem",
                    "cursor": "pointer",
                    "transition": "all 0.2s ease",
                    "display": "inline-flex",
                    "alignItems": "center"
                }
            )
            for item in watchlist[:10]  # Máximo 10 en watchlist
        ], style={"display": "flex", "flexWrap": "wrap", "justifyContent": "center", "gap": "4px"})
    ])


# Callback para toggle de watchlist (añadir/quitar de favoritos)
@callback(
    Output("watchlist", "data", allow_duplicate=True),
    Output("watchlist-icon", "children", allow_duplicate=True),
    Output("toggle-watchlist-btn", "title", allow_duplicate=True),
    Output("toggle-watchlist-btn", "style", allow_duplicate=True),
    Input("toggle-watchlist-btn", "n_clicks"),
    State("analysis-data", "data"),
    State("watchlist", "data"),
    prevent_initial_call=True
)
def toggle_watchlist(n_clicks, analysis_data, current_watchlist):
    """Añade o quita la acción actual de la watchlist."""
    if not n_clicks or not analysis_data:
        return no_update, no_update, no_update, no_update
    
    symbol = analysis_data.get("symbol")
    if not symbol:
        return no_update, no_update, no_update, no_update
    
    watchlist = current_watchlist if current_watchlist else []
    
    # Estilos base
    style_inactive = {
        "background": "transparent",
        "border": "2px solid rgba(245, 158, 11, 0.4)",
        "borderRadius": "50%",
        "width": "48px",
        "height": "48px",
        "display": "flex",
        "alignItems": "center",
        "justifyContent": "center",
        "cursor": "pointer",
        "transition": "all 0.2s ease",
        "color": "#F59E0B"
    }
    
    style_active = {
        **style_inactive,
        "background": "rgba(245, 158, 11, 0.15)",
        "border": "2px solid #F59E0B",
    }
    
    # Verificar si ya está en watchlist
    existing = next((item for item in watchlist if item.get("symbol") == symbol), None)
    
    if existing:
        # Quitar de watchlist
        watchlist = [item for item in watchlist if item.get("symbol") != symbol]
        return watchlist, "☆", "Añadir a Watchlist", style_inactive
    else:
        # Añadir a watchlist
        score = analysis_data.get("alerts", {}).get("score_v2", {}).get("score")
        new_item = {
            "symbol": symbol,
            "name": analysis_data.get("company_name", symbol),
            "score": score,
            "added_at": datetime.now().isoformat()
        }
        watchlist.insert(0, new_item)
        watchlist = watchlist[:20]  # Máximo 20 items
        return watchlist, "★", "Quitar de Watchlist", style_active


# Callback para sincronizar estado del botón cuando cambia la acción analizada
@callback(
    Output("watchlist-icon", "children"),
    Output("toggle-watchlist-btn", "title"),
    Output("toggle-watchlist-btn", "style"),
    Input("analysis-data", "data"),
    State("watchlist", "data"),
)
def sync_watchlist_button(analysis_data, current_watchlist):
    """Sincroniza el estado del botón de favorito cuando cambia la acción."""
    # Estilos base
    style_inactive = {
        "background": "transparent",
        "border": "2px solid rgba(245, 158, 11, 0.4)",
        "borderRadius": "50%",
        "width": "48px",
        "height": "48px",
        "display": "flex",
        "alignItems": "center",
        "justifyContent": "center",
        "cursor": "pointer",
        "transition": "all 0.2s ease",
        "color": "#F59E0B"
    }
    
    style_active = {
        **style_inactive,
        "background": "rgba(245, 158, 11, 0.15)",
        "border": "2px solid #F59E0B",
    }
    
    if not analysis_data:
        return "☆", "Añadir a Watchlist", style_inactive
    
    symbol = analysis_data.get("symbol")
    if not symbol:
        return "☆", "Añadir a Watchlist", style_inactive
    
    watchlist = current_watchlist if current_watchlist else []
    
    # Verificar si la acción actual está en watchlist
    is_in_watchlist = any(item.get("symbol") == symbol for item in watchlist)
    
    if is_in_watchlist:
        return "★", "Quitar de Watchlist", style_active
    else:
        return "☆", "Añadir a Watchlist", style_inactive


# Estrategias predefinidas para el screener
INVESTMENT_STRATEGIES = {
    "value": {
        "name": "Value Investing",
        "description": "Empresas con valoración atractiva (bajo P/E)",
        "tickers": ["BRK-B", "JPM", "BAC", "WFC", "C", "CVX", "XOM", "VZ", "T", "IBM"],
        "color": "#60a5fa"
    },
    "growth": {
        "name": "Growth Stocks",
        "description": "Empresas con alto potencial de crecimiento",
        "tickers": ["NVDA", "TSLA", "AMD", "SHOP", "SQ", "SNOW", "PLTR", "NET", "DDOG", "CRWD"],
        "color": "#34d399"
    },
    "dividend": {
        "name": "Dividend Champions",
        "description": "Empresas con dividendos consistentes",
        "tickers": ["JNJ", "PG", "KO", "PEP", "MCD", "MMM", "O", "T", "VZ", "XOM"],
        "color": "#F59E0B"
    },
    "bluechip": {
        "name": "Blue Chips",
        "description": "Las empresas más grandes y estables",
        "tickers": ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "BRK-B", "JPM", "V", "UNH"],
        "color": "#A78BFA"
    }
}


# Callback para mostrar estrategias del screener
@callback(
    Output("screener-results", "children"),
    Input("strategy-value", "n_clicks"),
    Input("strategy-growth", "n_clicks"),
    Input("strategy-dividend", "n_clicks"),
    Input("strategy-bluechip", "n_clicks"),
    prevent_initial_call=True
)
def show_strategy_stocks(value_clicks, growth_clicks, dividend_clicks, bluechip_clicks):
    """Muestra las acciones de la estrategia seleccionada."""
    triggered_id = ctx.triggered_id
    
    if not triggered_id:
        return None
    
    # Mapear botón a estrategia
    strategy_map = {
        "strategy-value": "value",
        "strategy-growth": "growth",
        "strategy-dividend": "dividend",
        "strategy-bluechip": "bluechip"
    }
    
    strategy_key = strategy_map.get(triggered_id)
    if not strategy_key:
        return None
    
    strategy = INVESTMENT_STRATEGIES.get(strategy_key, {})
    tickers = strategy.get("tickers", [])
    color = strategy.get("color", "#10b981")
    name = strategy.get("name", "Estrategia")
    description = strategy.get("description", "")
    
    return html.Div([
        html.Div([
            html.H6(f"📋 {name}", style={"color": color, "marginBottom": "4px"}),
            html.P(description, className="text-muted small mb-3"),
        ], className="text-center"),
        
        html.Div([
            html.Button(
                ticker,
                id={"type": "screener-pick", "index": ticker},
                n_clicks=0,
                style={
                    "background": f"rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.15)",
                    "border": f"1px solid {color}40",
                    "color": color,
                    "borderRadius": "20px",
                    "padding": "8px 16px",
                    "margin": "4px",
                    "fontWeight": "500",
                    "cursor": "pointer",
                    "transition": "all 0.2s ease"
                }
            )
            for ticker in tickers
        ], style={"display": "flex", "flexWrap": "wrap", "justifyContent": "center", "gap": "4px"}),
        
        html.P("Click en cualquier ticker para analizarlo", className="text-muted small text-center mt-3")
    ], style={
        "background": "rgba(39, 39, 42, 0.5)",
        "borderRadius": "12px",
        "padding": "20px",
        "marginTop": "20px"
    })


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
    Output("search-history", "data"),  # v3.0: Guardar al historial
    Input("navbar-search-btn", "n_clicks"),
    Input("navbar-search-input", "n_submit"),
    Input("logo-home", "n_clicks"),
    Input({"type": "quick-pick", "index": ALL}, "n_clicks"),
    Input({"type": "suggestion-item", "index": ALL}, "n_clicks"),
    Input({"type": "recent-search", "index": ALL}, "n_clicks"),  # v3.0: Búsquedas recientes
    Input({"type": "watchlist-item", "index": ALL}, "n_clicks"),  # v3.0.1: Click en watchlist
    Input({"type": "screener-pick", "index": ALL}, "n_clicks"),  # v3.0.1: Click en screener
    State("navbar-search-input", "value"),
    State("analysis-data", "data"),
    State("search-history", "data"),  # v3.0: Leer historial actual
    prevent_initial_call=True
)
def handle_navigation(search_btn, search_submit, logo_clicks, quick_picks, suggestion_clicks, recent_clicks, watchlist_clicks, screener_clicks, search_value, stored_data, current_history):
    triggered_id = ctx.triggered_id
    triggered_prop = ctx.triggered[0]["prop_id"] if ctx.triggered else ""
    
    home_style = {"display": "block"}
    analysis_style = {"display": "none"}
    empty_outputs = [None] * 13
    
    # Historial actual (o lista vacía si es None)
    history = current_history if current_history else []
    
    # Estilo para ocultar sugerencias
    hide_suggestions = {
        "position": "absolute",
        "top": "100%",
        "left": "0",
        "right": "0",
        "marginTop": "4px",
        "background": "#1a1a1f",
        "border": "1px solid rgba(16, 185, 129, 0.4)",
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
            return home_style, analysis_style, *empty_outputs, "", None, None, None, "", hide_suggestions, no_update
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
    
    # CASO 5: Click en búsqueda reciente
    elif isinstance(triggered_id, dict) and triggered_id.get("type") == "recent-search":
        if triggered_value and triggered_value > 0:
            symbol = triggered_id.get("index")
        else:
            return no_update
    
    # CASO 6: Click en watchlist item
    elif isinstance(triggered_id, dict) and triggered_id.get("type") == "watchlist-item":
        if triggered_value and triggered_value > 0:
            symbol = triggered_id.get("index")
        else:
            return no_update
    
    # CASO 7: Click en screener pick
    elif isinstance(triggered_id, dict) and triggered_id.get("type") == "screener-pick":
        if triggered_value and triggered_value > 0:
            symbol = triggered_id.get("index")
        else:
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
            return home_style, analysis_style, *empty_outputs, "", error_msg, None, None, "", hide_suggestions, no_update
        
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
        
        # v2.9: Detectar si es REIT y calcular métricas específicas
        is_reit = is_reit_sector(profile.sector if profile else "")
        reit_metrics = None
        if is_reit and financials:
            try:
                reit_metrics = calculate_reit_metrics(
                    net_income=financials.net_income,
                    depreciation=financials.depreciation,
                    gains_on_sale=None,  # No disponible en yfinance
                    capex=financials.capex,
                    shares_outstanding=financials.shares_outstanding,
                    price=financials.price,
                    dividend_per_share=financials.dividend_per_share
                )
            except Exception as e:
                logger.warning(f"Error calculando métricas REIT: {e}")
                reit_metrics = None
        
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
                ], xs=12, md=6),
                dbc.Col([
                    html.Div([
                        html.Div([
                            html.H3(current_price, className="text-info mb-0", style={"fontWeight": "700"}),
                            html.Small("Precio actual", className="text-muted")
                        ]),
                        # v2.9: Botón agregar a comparación
                        html.Button([
                            html.Span("➕ ", style={"marginRight": "4px"}),
                            "Comparar"
                        ], id="btn-add-comparison", n_clicks=0,
                           className="btn btn-outline-success btn-sm mt-2",
                           style={"fontSize": "0.75rem", "padding": "4px 10px"})
                    ], className="text-md-end")
                ], xs=12, md=6, className="mt-2 mt-md-0")
            ])
        ], className="company-header-card")
        
        # Score Card - Rediseñado con mejor centrado
        score_card = html.Div([
            # Contenedor del donut con padding
            html.Div([
                dcc.Graph(
                    figure=create_score_donut(score), 
                    config={'displayModeBar': False}, 
                    style={"height": "160px", "marginTop": "5px"}
                )
            ], style={"display": "flex", "justifyContent": "center", "alignItems": "center"}),
            
            # Badges centrados con mejor espaciado
            html.Div([
                html.Span("🚀 Growth", className="badge me-2", style={
                    "backgroundColor": "rgba(16, 185, 129, 0.15)",
                    "color": "#34d399",
                    "border": "1px solid rgba(16, 185, 129, 0.3)",
                    "fontWeight": "500",
                    "padding": "5px 12px",
                    "fontSize": "0.75rem",
                    "borderRadius": "20px"
                }) if score_v2.get("is_growth_company") else None,
                html.Span(score_v2.get("level", ""), className="badge score-level-badge",
                    style={
                        "backgroundColor": score_v2.get('level_color', '#71717a'),
                        "color": "#ffffff",
                        "border": "none",
                        "fontWeight": "600",
                        "padding": "8px 20px",
                        "fontSize": "0.85rem",
                        "borderRadius": "25px",
                        "boxShadow": f"0 4px 12px {score_v2.get('level_color', '#71717a')}40"
                    })
                if score_v2.get("level") else None
            ], style={
                "display": "flex", 
                "justifyContent": "center", 
                "alignItems": "center",
                "gap": "8px",
                "marginTop": "10px",
                "marginBottom": "15px",
                "paddingBottom": "5px"
            })
        ], style={
            "display": "flex",
            "flexDirection": "column",
            "justifyContent": "center",
            "alignItems": "center",
            "minHeight": "220px",
            "padding": "10px"
        })
        
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
                dbc.Col([create_metric_card("P/E", format_ratio(ratios.get("pe"), "multiple"), "📊")], xs=6, md=3, className="mb-3"),
                dbc.Col([create_metric_card("Forward P/E", format_ratio(ratios.get("forward_pe"), "multiple"), "🔮")], xs=6, md=3, className="mb-3"),
                dbc.Col([create_metric_card("P/B", format_ratio(ratios.get("pb"), "multiple"), "📚")], xs=6, md=3, className="mb-3"),
                dbc.Col([create_metric_card("P/S", format_ratio(ratios.get("ps"), "multiple"), "💰")], xs=6, md=3, className="mb-3"),
            ]),
            dbc.Row([
                dbc.Col([create_metric_card("EV/EBITDA", format_ratio(ratios.get("ev_ebitda"), "multiple"), "🏢")], xs=6, md=3, className="mb-3"),
                dbc.Col([create_metric_card("P/FCF", format_ratio(ratios.get("p_fcf"), "multiple"), "💵")], xs=6, md=3, className="mb-3"),
                dbc.Col([create_metric_card("PEG Ratio", format_ratio(ratios.get("peg"), "decimal"), "📈")], xs=6, md=3, className="mb-3"),
                dbc.Col([create_metric_card("FCF Yield", format_ratio(ratios.get("fcf_yield"), "percent"), "💸")], xs=6, md=3, className="mb-3"),
            ]),
            
            # v2.9: Sección especial para REITs
            html.Div([
                html.Hr(className="my-4"),
                html.H6("🏠 Métricas REIT (FFO/AFFO)", className="mb-3"),
                html.P("Métricas específicas para Real Estate Investment Trusts", className="text-muted small mb-3"),
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.P("FFO/Share", className="text-muted small mb-1 text-center"),
                                html.H4(f"${reit_metrics['ffo_per_share']:.2f}" if reit_metrics.get('ffo_per_share') else "N/A", 
                                       className="mb-1 text-center text-info"),
                                html.P("Funds From Operations", className="small text-muted text-center", style={"fontSize": "0.7rem"})
                            ])
                        ], style={"backgroundColor": "#27272a", "border": "none"})
                    ], xs=6, md=3, className="mb-3"),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.P("P/FFO", className="text-muted small mb-1 text-center"),
                                html.H4(f"{reit_metrics['p_ffo']:.1f}x" if reit_metrics.get('p_ffo') else "N/A",
                                       className=f"mb-1 text-center {reit_metrics['p_ffo_interpretation'][1] if reit_metrics.get('p_ffo_interpretation') else ''}"),
                                html.P(reit_metrics['p_ffo_interpretation'][0] if reit_metrics.get('p_ffo_interpretation') else "Precio/FFO", 
                                      className="small text-muted text-center", style={"fontSize": "0.7rem"})
                            ])
                        ], style={"backgroundColor": "#27272a", "border": "none"})
                    ], xs=6, md=3, className="mb-3"),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.P("AFFO/Share", className="text-muted small mb-1 text-center"),
                                html.H4(f"${reit_metrics['affo_per_share']:.2f}" if reit_metrics.get('affo_per_share') else "N/A",
                                       className="mb-1 text-center text-info"),
                                html.P("Adjusted FFO", className="small text-muted text-center", style={"fontSize": "0.7rem"})
                            ])
                        ], style={"backgroundColor": "#27272a", "border": "none"})
                    ], xs=6, md=3, className="mb-3"),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.P("FFO Payout", className="text-muted small mb-1 text-center"),
                                html.H4(f"{reit_metrics['ffo_payout_ratio']:.0f}%" if reit_metrics.get('ffo_payout_ratio') else "N/A",
                                       className=f"mb-1 text-center {reit_metrics['payout_interpretation'][1] if reit_metrics.get('payout_interpretation') else ''}"),
                                html.P(reit_metrics['payout_interpretation'][0] if reit_metrics.get('payout_interpretation') else "Dividendo/FFO",
                                      className="small text-muted text-center", style={"fontSize": "0.7rem"})
                            ])
                        ], style={"backgroundColor": "#27272a", "border": "none"})
                    ], xs=6, md=3, className="mb-3"),
                ]),
                # Nota explicativa
                dbc.Alert([
                    html.Strong("💡 ¿Por qué FFO? "),
                    "Para REITs, el FFO es más relevante que el Net Income porque la depreciación inmobiliaria ",
                    "no refleja una pérdida real de valor. Un P/FFO < 15 generalmente indica buena valoración."
                ], color="info", className="mb-0 small", style={"backgroundColor": "rgba(16, 185, 129, 0.1)", "border": "1px solid rgba(16, 185, 129, 0.3)"})
            ]) if is_reit and reit_metrics and reit_metrics.get("is_valid") else None,
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
        except (KeyError, TypeError, ValueError, ConnectionError):
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
            
            # Tabla de métricas fundamentales con veredicto - REDISEÑADA
            html.Div([
                # Header con mejor explicación
                html.Div([
                    html.H6("📋 Comparación de Métricas Fundamentales", style={
                        "marginBottom": "8px", "fontWeight": "600", "fontSize": "1.1rem"
                    }),
                    html.P("¿Cómo se compara esta empresa vs su sector y el mercado general?", 
                           style={"color": "#9ca3af", "fontSize": "0.9rem", "marginBottom": "0"})
                ], style={"marginBottom": "20px"}),
                
                # Leyenda de columnas explicativa
                html.Div([
                    html.Div([
                        html.Div([
                            html.Span("📊", style={"fontSize": "1.2rem", "marginRight": "8px"}),
                            html.Div([
                                html.Strong(symbol, style={"color": "#10b981"}),
                                html.Div("Valor de la empresa", style={"fontSize": "0.75rem", "color": "#6b7280"})
                            ])
                        ], style={"display": "flex", "alignItems": "center"}),
                    ], style={"flex": "1", "padding": "10px"}),
                    
                    html.Div([
                        html.Div([
                            html.Span("🏢", style={"fontSize": "1.2rem", "marginRight": "8px"}),
                            html.Div([
                                html.Strong("Sector", style={"color": "#6b7280"}),
                                html.Div("Promedio del sector", style={"fontSize": "0.75rem", "color": "#6b7280"})
                            ])
                        ], style={"display": "flex", "alignItems": "center"}),
                    ], style={"flex": "1", "padding": "10px"}),
                    
                    html.Div([
                        html.Div([
                            html.Span("🌐", style={"fontSize": "1.2rem", "marginRight": "8px"}),
                            html.Div([
                                html.Strong("SPY", style={"color": "#6b7280"}),
                                html.Div("S&P 500 (mercado)", style={"fontSize": "0.75rem", "color": "#6b7280"})
                            ])
                        ], style={"display": "flex", "alignItems": "center"}),
                    ], style={"flex": "1", "padding": "10px"}),
                    
                    html.Div([
                        html.Div([
                            html.Span("✅", style={"fontSize": "1.2rem", "marginRight": "8px"}),
                            html.Div([
                                html.Strong("Veredicto", style={"color": "#6b7280"}),
                                html.Div("Evaluación comparativa", style={"fontSize": "0.75rem", "color": "#6b7280"})
                            ])
                        ], style={"display": "flex", "alignItems": "center"}),
                    ], style={"flex": "1", "padding": "10px"}),
                ], style={
                    "display": "flex", 
                    "gap": "10px", 
                    "background": "rgba(39, 39, 42, 0.5)", 
                    "borderRadius": "12px", 
                    "padding": "12px",
                    "marginBottom": "15px",
                    "flexWrap": "wrap"
                }),
                
                # Tabla con mejor diseño
                html.Div([
                    html.Table([
                        html.Thead([
                            html.Tr([
                                html.Th("Métrica", style={
                                    "textAlign": "left", "padding": "14px 16px", 
                                    "color": "#9ca3af", "fontWeight": "600", "fontSize": "0.85rem",
                                    "borderBottom": "1px solid #374151", "width": "25%"
                                }),
                                html.Th(symbol, style={
                                    "textAlign": "center", "padding": "14px 16px",
                                    "color": "#10b981", "fontWeight": "700", "fontSize": "0.9rem",
                                    "borderBottom": "1px solid #374151", "width": "18%"
                                }),
                                html.Th("Sector", style={
                                    "textAlign": "center", "padding": "14px 16px",
                                    "color": "#6b7280", "fontWeight": "500", "fontSize": "0.85rem",
                                    "borderBottom": "1px solid #374151", "width": "18%"
                                }),
                                html.Th("SPY", style={
                                    "textAlign": "center", "padding": "14px 16px",
                                    "color": "#6b7280", "fontWeight": "500", "fontSize": "0.85rem",
                                    "borderBottom": "1px solid #374151", "width": "18%"
                                }),
                                html.Th("Resultado", style={
                                    "textAlign": "center", "padding": "14px 16px",
                                    "color": "#9ca3af", "fontWeight": "600", "fontSize": "0.85rem",
                                    "borderBottom": "1px solid #374151", "width": "21%"
                                }),
                            ])
                        ]),
                        html.Tbody(comparison_rows)
                    ], style={
                        "width": "100%", 
                        "borderCollapse": "separate",
                        "borderSpacing": "0"
                    })
                ], style={
                    "background": "rgba(24, 24, 27, 0.5)",
                    "borderRadius": "12px",
                    "overflow": "hidden",
                    "border": "1px solid #374151"
                }),
                
                # Leyenda inferior
                html.Div([
                    html.Div([
                        html.Span("●", style={"color": "#22c55e", "marginRight": "6px", "fontSize": "1.2rem"}),
                        html.Span("Excelente", style={"fontWeight": "500", "marginRight": "6px"}),
                        html.Span("= Supera ambos benchmarks", style={"color": "#6b7280"})
                    ], style={"display": "flex", "alignItems": "center"}),
                    
                    html.Div([
                        html.Span("●", style={"color": "#eab308", "marginRight": "6px", "fontSize": "1.2rem"}),
                        html.Span("Aceptable", style={"fontWeight": "500", "marginRight": "6px"}),
                        html.Span("= Supera al menos uno", style={"color": "#6b7280"})
                    ], style={"display": "flex", "alignItems": "center"}),
                    
                    html.Div([
                        html.Span("●", style={"color": "#ef4444", "marginRight": "6px", "fontSize": "1.2rem"}),
                        html.Span("Débil", style={"fontWeight": "500", "marginRight": "6px"}),
                        html.Span("= Por debajo de ambos", style={"color": "#6b7280"})
                    ], style={"display": "flex", "alignItems": "center"}),
                ], style={
                    "display": "flex",
                    "justifyContent": "center",
                    "gap": "30px",
                    "marginTop": "20px",
                    "padding": "15px",
                    "background": "rgba(39, 39, 42, 0.3)",
                    "borderRadius": "10px",
                    "fontSize": "0.85rem",
                    "flexWrap": "wrap"
                })
            ], style={"marginTop": "25px"}),
            
            # v2.9: Sección de comparación multi-acción
            html.Div([
                html.Hr(className="my-4"),
                html.H6("🔀 Comparador Multi-Acción", className="mb-3"),
                html.P("Compara varias acciones lado a lado. Agrega acciones con el botón 'Comparar' en cada análisis.",
                      className="text-muted small mb-3"),
                html.Div(id="comparison-table-container", children=[
                    html.P("No hay acciones en la lista de comparación.", className="text-muted text-center"),
                    html.P("Usa el botón '➕ Comparar' en cada acción para agregarla.", className="text-muted small text-center")
                ])
            ], style={"backgroundColor": "rgba(24, 24, 27, 0.5)", "borderRadius": "12px", "padding": "20px", "marginTop": "20px"})
        ])
        
        # Tab Valor Intrínseco
        eps = ratios.get("eps")
        total_equity = financials.total_equity if financials else None
        shares = financials.shares_outstanding if financials else None
        bvps = total_equity / shares if total_equity and shares and shares > 0 else None
        graham = graham_number(eps, bvps) if eps and bvps else None
        
        fcf = ratios.get("fcf")
        
        # v2.3: DCF Multi-Stage con 3 etapas
        dcf_result = dcf_multi_stage_dynamic(
            fcf=fcf,
            shares_outstanding=shares,
            beta=financials.beta if financials else None,
            debt_to_equity=ratios.get("debt_to_equity"),
            interest_expense=financials.interest_expense if financials else None,
            total_debt=financials.total_debt if financials else None,
            revenue_growth_3y=contextual.get("revenue_cagr_3y") if contextual else None,
            fcf_growth_3y=contextual.get("fcf_cagr_3y") if contextual else None,
            eps_growth_3y=contextual.get("eps_cagr_3y") if contextual else None,
            margin_of_safety_pct=0.15  # 15% margen de seguridad
        )
        dcf_value = dcf_result.get("fair_value_per_share")
        dcf_value_mos = dcf_result.get("fair_value_with_mos")
        dcf_wacc = dcf_result.get("wacc_calculated")
        dcf_growth = dcf_result.get("growth_estimated")
        dcf_growth_source = dcf_result.get("growth_source", "")
        dcf_is_valid = dcf_result.get("is_valid", False)
        
        # Obtener desglose del modelo multi-stage
        model_result = dcf_result.get("model_result", {})
        value_composition = model_result.get("value_composition", {}) if model_result else {}
        stages = model_result.get("stages", {}) if model_result else {}
        sensitivity = dcf_result.get("sensitivity_analysis", {})
        
        # v2.9: DCF Sensitivity Analysis - Matriz de sensibilidad
        sensitivity_matrix = None
        try:
            # Solo calcular si tenemos TODOS los datos necesarios
            if (dcf_is_valid and 
                fcf is not None and fcf > 0 and 
                shares is not None and shares > 0 and 
                dcf_wacc is not None and dcf_wacc > 0 and 
                dcf_growth is not None):
                
                sensitivity_matrix = dcf_sensitivity_analysis(
                    fcf=fcf,
                    shares_outstanding=shares,
                    current_price=financials.price if financials else None,
                    base_growth_rate=max(0.01, min(dcf_growth, 0.30)),  # Limitar entre 1% y 30%
                    base_discount_rate=max(0.05, min(dcf_wacc, 0.20)),  # Limitar entre 5% y 20%
                    growth_rate_range=(-0.05, 0.05, 0.025),
                    discount_rate_range=(-0.02, 0.02, 0.01),
                )
        except Exception as e:
            logger.warning(f"Error calculando sensitivity matrix: {e}")
            sensitivity_matrix = None
        
        price = financials.price if financials else None
        
        # Calcular si está cara o barata
        dcf_vs_price = ((dcf_value - price) / price * 100) if dcf_value and price else None
        graham_vs_price = ((graham - price) / price * 100) if graham and price else None
        
        # Determinar veredicto general
        if dcf_value and graham and price:
            avg_intrinsic = (dcf_value + graham) / 2
            avg_vs_price = ((avg_intrinsic - price) / price * 100)
            if avg_vs_price > 20:
                verdict = ("🟢", "Potencialmente SUBVALORADA", "text-success", "Los modelos sugieren que cotiza por debajo de su valor estimado. Podría ser oportunidad de compra.")
            elif avg_vs_price > 0:
                verdict = ("🟡", "Precio RAZONABLE", "text-warning", "Cotiza cerca de su valor estimado. Ni cara ni barata según estos modelos.")
            elif avg_vs_price > -20:
                verdict = ("🟠", "Ligeramente SOBREVALORADA", "text-warning", "Cotiza algo por encima de su valor estimado. Considerar esperar mejor precio.")
            else:
                verdict = ("🔴", "Potencialmente SOBREVALORADA", "text-danger", "Los modelos sugieren que el precio actual está muy por encima del valor estimado.")
        elif dcf_value and price:
            dcf_diff = ((dcf_value - price) / price * 100)
            if dcf_diff > 15:
                verdict = ("🟢", "Potencialmente SUBVALORADA", "text-success", "El modelo DCF sugiere que cotiza por debajo de su valor.")
            elif dcf_diff > -15:
                verdict = ("🟡", "Precio RAZONABLE", "text-warning", "Cotiza cerca de su valor estimado por DCF.")
            else:
                verdict = ("🔴", "Potencialmente SOBREVALORADA", "text-danger", "El modelo DCF sugiere sobrevaloración.")
        else:
            verdict = ("⚪", "Datos insuficientes", "text-muted", "No hay suficiente información para calcular el valor intrínseco.")
        
        # IDs únicos para tooltips
        import random
        uid = random.randint(1000, 9999)
        
        tab_intrinsic = html.Div([
            html.H5("💰 ¿Cuánto vale realmente esta acción?", className="mb-1"),
            html.P("Estimamos el valor real usando modelos financieros y lo comparamos con el precio de mercado", 
                   className="text-muted small mb-3"),
            
            # Veredicto principal
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.Span(verdict[0], style={"fontSize": "2rem", "marginRight": "12px"}),
                        html.Div([
                            html.Span(verdict[1], className=f"h4 mb-0 {verdict[2]}"),
                            html.P(verdict[3], className="text-muted small mb-0 mt-1")
                        ])
                    ], className="d-flex align-items-start"),
                ])
            ], className="mb-4", style={"backgroundColor": "#1f1f23", "border": "1px solid #3f3f46"}),
            
            # Comparación de valores con tooltips
            html.H6("📊 Comparación de Valores", className="mb-3"),
            dbc.Row([
                # Precio actual
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.Div([
                                html.Span("Precio de Mercado", className="text-muted small"),
                                html.Span("i", id=f"tip-precio-{uid}", className="info-icon"),
                            ], className="mb-1 text-center d-flex align-items-center justify-content-center", style={"gap": "6px"}),
                            html.H3(f"${price:.2f}" if price else "N/A", className="mb-1 text-center"),
                            html.P("Lo que cuesta hoy", className="text-muted small mb-0 text-center",
                                  style={"fontSize": "0.75rem"})
                        ])
                    ], style={"backgroundColor": "#27272a", "border": "none"}),
                    dbc.Tooltip(
                        "El precio actual de la acción en el mercado. Es lo que pagarías si compras ahora.",
                        target=f"tip-precio-{uid}", placement="top"
                    )
                ], xs=12, md=4, className="mb-3"),
                
                # Graham
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.Div([
                                html.Span("Valor Graham", className="text-muted small"),
                                html.Span("i", id=f"tip-graham-{uid}", className="info-icon"),
                            ], className="mb-1 text-center d-flex align-items-center justify-content-center", style={"gap": "6px"}),
                            html.H3(f"${graham:.2f}" if graham else "N/A", 
                                   className=f"mb-1 text-center {'text-success' if graham and price and graham > price else 'text-danger' if graham else ''}"),
                            html.P([
                                f"{graham_vs_price:+.0f}% vs precio" if graham_vs_price else "Fórmula clásica"
                            ], className="small mb-0 text-center text-muted", style={"fontSize": "0.75rem"})
                        ])
                    ], style={"backgroundColor": "#27272a", "border": "none"}),
                    dbc.Tooltip(
                        get_tooltip_text("graham"),
                        target=f"tip-graham-{uid}", placement="top"
                    )
                ], xs=12, md=4, className="mb-3"),
                
                # DCF
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.Div([
                                html.Span("Valor DCF", className="text-muted small"),
                                html.Span("i", id=f"tip-dcf-{uid}", className="info-icon"),
                            ], className="mb-1 text-center d-flex align-items-center justify-content-center", style={"gap": "6px"}),
                            html.H3(f"${dcf_value:.2f}" if dcf_value else "N/A",
                                   className=f"mb-1 text-center {'text-success' if dcf_value and price and dcf_value > price else 'text-danger' if dcf_value else ''}"),
                            html.P([
                                f"{dcf_vs_price:+.0f}% vs precio" if dcf_vs_price else "Flujos futuros"
                            ], className="small mb-0 text-center text-muted", style={"fontSize": "0.75rem"})
                        ])
                    ], style={"backgroundColor": "#27272a", "border": "none"}),
                    dbc.Tooltip(
                        get_tooltip_text("dcf"),
                        target=f"tip-dcf-{uid}", placement="top"
                    )
                ], xs=12, md=4, className="mb-3"),
            ]),
            
            # Sección fija: Detalles del DCF
            html.Div([
                html.Hr(className="my-3"),
                html.Div([
                    html.Span("⚙️ ", style={"marginRight": "6px"}),
                    html.Span("Parámetros del modelo DCF", className="text-info fw-bold"),
                ], className="mb-3"),
                html.Div([
                    dbc.Row([
                        dbc.Col([
                            html.Div([
                                html.Span("WACC ", className="text-muted small"),
                                html.Span("i", id=f"tip-wacc-{uid}", className="info-icon", 
                                         style={"width": "14px", "height": "14px", "fontSize": "9px"}),
                            ], className="d-flex align-items-center justify-content-center", style={"gap": "4px"}),
                            html.Span(f"{dcf_wacc:.1%}" if dcf_wacc else "N/A", className="text-info"),
                            dbc.Tooltip(get_tooltip_text("wacc"), target=f"tip-wacc-{uid}", placement="top")
                        ], xs=6, md=3, className="text-center mb-2"),
                        dbc.Col([
                            html.Div([
                                html.Span("Growth Inicial ", className="text-muted small"),
                            ]),
                            html.Span(f"{dcf_growth:.1%}" if dcf_growth else "N/A", className="text-success"),
                        ], xs=6, md=3, className="text-center mb-2"),
                        dbc.Col([
                            html.Div([
                                html.Span("Margen Seguridad ", className="text-muted small"),
                                html.Span("i", id=f"tip-mos-{uid}", className="info-icon",
                                         style={"width": "14px", "height": "14px", "fontSize": "9px"}),
                            ], className="d-flex align-items-center justify-content-center", style={"gap": "4px"}),
                            html.Span(f"${dcf_value_mos:.2f}" if dcf_value_mos else "N/A", className="text-warning"),
                            dbc.Tooltip(get_tooltip_text("margin_of_safety"), target=f"tip-mos-{uid}", placement="top")
                        ], xs=6, md=3, className="text-center mb-2"),
                        dbc.Col([
                            html.Div([
                                html.Span("Fuente Growth ", className="text-muted small"),
                            ]),
                            html.Span(dcf_growth_source.replace("_", " ").title() if dcf_growth_source else "N/A", 
                                     className="text-muted", style={"fontSize": "0.85rem"}),
                        ], xs=6, md=3, className="text-center mb-2"),
                    ]),
                    
                    # Composición del valor por etapas
                    html.Div([
                        html.P("📈 Composición del valor por etapas:", className="text-muted small mt-3 mb-2"),
                        dbc.Row([
                            dbc.Col([
                                html.Div([
                                    html.Span(f"{value_composition.get('stage1_pct', 0):.0f}%", 
                                             className="h5 text-primary mb-0"),
                                    html.P("Años 1-5 (alto crecimiento)", className="small text-muted mb-0")
                                ], className="text-center")
                            ], xs=4),
                            dbc.Col([
                                html.Div([
                                    html.Span(f"{value_composition.get('stage2_pct', 0):.0f}%", 
                                             className="h5 text-info mb-0"),
                                    html.P("Años 6-10 (transición)", className="small text-muted mb-0")
                                ], className="text-center")
                            ], xs=4),
                            dbc.Col([
                                html.Div([
                                    html.Span(f"{value_composition.get('terminal_pct', 0):.0f}%", 
                                             className="h5 text-warning mb-0"),
                                    html.P("Perpetuidad (2.5%)", className="small text-muted mb-0")
                                ], className="text-center")
                            ], xs=4),
                        ])
                    ]) if value_composition else None,
                    
                ], className="p-3")
            ]) if dcf_is_valid else None,
            
            # Sección fija: Cómo interpretar
            html.Div([
                html.Div([
                    html.Span("📚 ", style={"marginRight": "6px"}),
                    html.Span("¿Cómo interpretar estos valores?", className="text-info fw-bold"),
                ], className="mb-3 mt-4"),
                html.Div([
                    html.Div([
                        html.Strong("🎯 Valor Graham", className="text-primary"),
                        html.P("Fórmula creada por Benjamin Graham, el padre del value investing. "
                               "Usa las ganancias actuales y el valor contable. Es conservadora y funciona "
                               "mejor para empresas estables con activos tangibles.", className="small mb-3"),
                    ]),
                    html.Div([
                        html.Strong("🎯 Valor DCF (Flujos Descontados)", className="text-success"),
                        html.P("Estima cuánto dinero generará la empresa en el futuro y lo trae a valor presente. "
                               "Usamos 3 etapas: crecimiento alto (5 años) → transición (5 años) → perpetuidad. "
                               "Es el método más usado en Wall Street.", className="small mb-3"),
                    ]),
                    html.Div([
                        html.Strong("⚠️ Importante", className="text-warning"),
                        html.P("Estos son MODELOS matemáticos, no predicciones exactas. Dependen de supuestos "
                               "sobre el futuro que pueden no cumplirse. Úsalos como UNA herramienta más, "
                               "nunca como única base para decidir.", className="small mb-0"),
                    ]),
                ], className="p-3")
            ]),
            
            # v2.9: Matriz de Sensibilidad DCF - REDISEÑADA
            build_sensitivity_section(sensitivity_matrix, price) if sensitivity_matrix and sensitivity_matrix.get("is_valid") else None,
            
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
                    for cat, reason in danger_alerts
                ]) if danger_alerts else None,
                
                html.H6("🟠 Advertencias", className="text-warning mt-3") if warning_alerts else None,
                html.Div([
                    html.Div([
                        html.Strong(f"{cat}: "), 
                        html.Span(reason),
                        html.Div(get_alert_explanation(cat, reason), className="text-muted small mt-1")
                    ], className="alert-box alert-warning-custom mb-2")
                    for cat, reason in warning_alerts
                ]) if warning_alerts else None,
                
                html.H6("🟢 Fortalezas", className="text-success mt-3") if success_alerts else None,
                html.Div([
                    html.Div([
                        html.Strong(f"{cat}: "), 
                        html.Span(reason),
                        html.Div(get_alert_explanation(cat, reason), className="text-muted small mt-1")
                    ], className="alert-box alert-success-custom mb-2")
                    for cat, reason in success_alerts
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
        
        # v3.0: Actualizar historial de búsquedas
        new_history = [h for h in history if h.get("symbol") != symbol]  # Eliminar duplicados
        new_history.insert(0, {"symbol": symbol, "name": company_name})  # Añadir al inicio
        new_history = new_history[:10]  # Mantener máximo 10
        
        return (
            {"display": "none"}, {"display": "block"},
            company_header, score_card, key_metrics, sector_notes,
            tab_valuation, tab_profitability, tab_health, tab_historical, tab_comparison, tab_intrinsic, tab_evaluation,
            footer, stored_data, symbol, None, None, stock_badge, "", hide_suggestions, new_history
        )
    
    except InvalidSymbolError as e:
        logger.warning(f"Símbolo inválido: {symbol} - {e}")
        error_msg = dbc.Alert(
            f"⚠️ Símbolo inválido: '{symbol}'. Verifica que el ticker sea correcto.",
            color="warning", dismissable=True
        )
        return home_style, analysis_style, *empty_outputs, "", error_msg, None, None, "", hide_suggestions, no_update
    
    except APITimeoutError as e:
        logger.error(f"Timeout obteniendo datos de {symbol}: {e}")
        error_msg = dbc.Alert(
            f"⏱️ Timeout al obtener datos de '{symbol}'. Los servidores están lentos, intenta de nuevo.",
            color="warning", dismissable=True
        )
        return home_style, analysis_style, *empty_outputs, "", error_msg, None, None, "", hide_suggestions, no_update
    
    except DataFetchError as e:
        logger.error(f"Error de datos para {symbol}: {e}")
        error_msg = dbc.Alert(
            f"❌ Error obteniendo datos de '{symbol}': {str(e)}",
            color="danger", dismissable=True
        )
        return home_style, analysis_style, *empty_outputs, "", error_msg, None, None, "", hide_suggestions, no_update
    
    except Exception as e:
        logger.error(f"Error inesperado analizando {symbol}: {type(e).__name__}: {e}", exc_info=True)
        error_msg = dbc.Alert(
            f"❌ Error inesperado al analizar '{symbol}'. Por favor intenta de nuevo.",
            color="danger", dismissable=True
        )
        return home_style, analysis_style, *empty_outputs, "", error_msg, None, None, "", hide_suggestions, no_update


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
        localStorage.setItem('finanzer-theme', newTheme);
        
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
        const savedTheme = localStorage.getItem('finanzer-theme');
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
        <style>
        /* ==============================================
           OVERRIDE BOOTSTRAP THEME COLORS - VERDE
           ============================================== */
        
        /* Botones de período - el activo es primary sin outline */
        .period-btn.btn-primary:not(.btn-outline-primary) {
            background-color: #10b981 !important;
            border-color: #10b981 !important;
            color: white !important;
        }
        
        /* Botones de período NO seleccionados - outline visible */
        .period-btn.btn-outline-secondary,
        .period-btn.btn-secondary.btn-outline-secondary {
            background-color: transparent !important;
            border: 2px solid #10b981 !important;
            color: #10b981 !important;
        }
        .period-btn.btn-outline-secondary:hover {
            background-color: rgba(16, 185, 129, 0.15) !important;
            border-color: #10b981 !important;
            color: #10b981 !important;
        }
        
        /* En modo claro, asegurar visibilidad */
        [data-theme="light"] .period-btn.btn-outline-secondary {
            border: 2px solid #059669 !important;
            color: #059669 !important;
        }
        
        /* Todos los botones primarios y secundarios -> verde */
        .btn-primary:not(.period-btn), .btn-secondary:not(.period-btn), 
        .btn-outline-primary:not(.period-btn), .btn-outline-secondary:not(.period-btn) {
            background-color: transparent !important;
            border-color: rgba(16, 185, 129, 0.4) !important;
            color: #34d399 !important;
        }
        .btn-primary:not(.period-btn):hover, .btn-secondary:not(.period-btn):hover, 
        .btn-outline-primary:not(.period-btn):hover, .btn-outline-secondary:not(.period-btn):hover {
            background-color: rgba(16, 185, 129, 0.2) !important;
            border-color: rgba(16, 185, 129, 0.6) !important;
            color: #34d399 !important;
        }
        .btn-primary:focus, .btn-secondary:focus {
            box-shadow: 0 0 0 0.2rem rgba(16, 185, 129, 0.25) !important;
        }
        
        /* Input de búsqueda - focus verde */
        #navbar-search-input:focus,
        #navbar-search-input:active,
        input[type="text"]:focus {
            border-color: #10b981 !important;
            box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.3) !important;
            outline: none !important;
        }
        
        /* Links primarios */
        a.text-primary, .text-primary {
            color: #10b981 !important;
        }
        
        /* Badge primario - Growth */
        .badge.bg-primary {
            background-color: rgba(16, 185, 129, 0.15) !important;
            color: #34d399 !important;
        }
        
        /* ==============================================
           FIN OVERRIDE BOOTSTRAP
           ============================================== */
        
        /* ==============================================
           MODO CLARO - CSS Específico
           ============================================== */
        [data-theme="light"] .period-btn.btn-outline-secondary {
            background-color: #e6f7f1 !important;
            border: 2px solid #10b981 !important;
            color: #047857 !important;
            font-weight: 600 !important;
        }
        [data-theme="light"] .period-btn.btn-primary:not(.btn-outline-primary) {
            background-color: #10b981 !important;
            border-color: #10b981 !important;
            color: white !important;
        }
        
        /* Quick picks en modo claro - usando clase parent */
        [data-theme="light"] button[id*="quick-pick"] {
            background: #e6f7f1 !important;
            border: 2px solid #10b981 !important;
            color: #047857 !important;
            font-weight: 600 !important;
        }
        
        /* ==============================================
           FIN MODO CLARO
           ============================================== */
        
        /* Botón de descarga PDF */
        .download-btn {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
            border: none !important;
            color: white !important;
            padding: 12px 28px !important;
            border-radius: 12px !important;
            font-weight: 600 !important;
            font-size: 1rem !important;
            cursor: pointer !important;
            transition: all 0.3s ease !important;
            box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3) !important;
        }
        .download-btn:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 8px 25px rgba(16, 185, 129, 0.4) !important;
        }
        
        /* Tooltips modernos y minimalistas */
        .tooltip {
            font-family: 'Inter', -apple-system, sans-serif !important;
        }
        .tooltip-inner {
            background: linear-gradient(145deg, #1a1a22 0%, #252530 100%) !important;
            border: 1px solid rgba(16, 185, 129, 0.25) !important;
            border-radius: 14px !important;
            padding: 18px 22px !important;
            max-width: 380px !important;
            text-align: left !important;
            font-size: 13px !important;
            line-height: 1.7 !important;
            box-shadow: 0 25px 50px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.03) !important;
            white-space: pre-line !important;
            color: #e4e4e7 !important;
        }
        .tooltip.show {
            opacity: 1 !important;
        }
        .bs-tooltip-top .tooltip-arrow::before,
        .bs-tooltip-auto[data-popper-placement^="top"] .tooltip-arrow::before {
            border-top-color: #252530 !important;
        }
        .bs-tooltip-bottom .tooltip-arrow::before,
        .bs-tooltip-auto[data-popper-placement^="bottom"] .tooltip-arrow::before {
            border-bottom-color: #252530 !important;
        }
        
        /* Info icon estilo */
        .info-icon {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 16px;
            height: 16px;
            border-radius: 50%;
            background: rgba(16, 185, 129, 0.12);
            color: #34d399;
            font-size: 10px;
            font-weight: 600;
            font-style: normal;
            cursor: help;
            margin-left: 6px;
            transition: all 0.2s ease;
            border: 1px solid rgba(16, 185, 129, 0.25);
            flex-shrink: 0;
        }
        .info-icon:hover {
            background: rgba(16, 185, 129, 0.25);
            transform: scale(1.1);
            border-color: rgba(16, 185, 129, 0.4);
        }
        
        /* Estilos específicos para modo claro */
        @media (prefers-color-scheme: light) {
            .metric-card {
                background-color: #f8fafc !important;
                border-color: #e2e8f0 !important;
            }
        }
        
        /* Logo Finanzer en verde */
        #logo-home span:last-child {
            background: linear-gradient(135deg, #34d399 0%, #10b981 100%) !important;
            -webkit-background-clip: text !important;
            -webkit-text-fill-color: transparent !important;
            background-clip: text !important;
        }
        
        /* Tabs activos con verde */
        .nav-tabs .nav-link.active {
            color: #059669 !important;
            border-bottom: 2px solid #10b981 !important;
        }
        .nav-tabs .nav-link:hover:not(.active) {
            color: #10b981 !important;
        }
        
        /* Links en verde */
        a {
            color: #10b981;
        }
        a:hover {
            color: #059669;
        }
        
        /* Tabla de comparación - hover en filas */
        table tr:hover td {
            background-color: rgba(16, 185, 129, 0.05) !important;
        }
        
        /* Score card styling */
        .score-card {
            background: linear-gradient(145deg, #1f1f23 0%, #18181b 100%);
            border-radius: 16px;
            border: 1px solid rgba(55, 65, 81, 0.5);
            padding: 0;
            overflow: hidden;
        }
        
        /* Badge del score con animación sutil */
        .score-level-badge {
            animation: fadeIn 0.5s ease-out;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        /* Quick picks hover - botones verdes */
        button[id*="quick-pick"]:hover {
            background: rgba(16, 185, 129, 0.3) !important;
            border-color: rgba(16, 185, 129, 0.6) !important;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.2);
        }
        
        /* Botón de búsqueda verde */
        #navbar-search-btn {
            background-color: #10b981 !important;
            border-color: #10b981 !important;
        }
        #navbar-search-btn:hover {
            background-color: #059669 !important;
            border-color: #059669 !important;
        }
        
        /* ==============================================
           TABLA DE SENSIBILIDAD - COLORES FIJOS (ULTRA-ESPECÍFICO)
           Estos estilos NUNCA deben cambiar con el tema
           ============================================== */
        
        /* Contenedor principal - NUNCA cambia */
        .sensitivity-container,
        div.sensitivity-container,
        [data-theme="light"] .sensitivity-container,
        [data-theme="dark"] .sensitivity-container {
            background-color: #18181b !important;
        }
        
        .sensitivity-table,
        .sensitivity-table tbody,
        .sensitivity-table thead,
        .sensitivity-table tr,
        .sensitivity-table td,
        .sensitivity-table th,
        table.sensitivity-table td,
        table.sensitivity-table th {
            background-color: transparent !important;
        }
        
        .sensitivity-table td,
        .sensitivity-table th {
            padding: 10px 6px !important;
            text-align: center !important;
            font-size: 0.9rem !important;
        }
        
        /* Headers - SIEMPRE oscuros */
        .sens-header,
        td.sens-header,
        th.sens-header,
        .sensitivity-table .sens-header,
        .sensitivity-table th.sens-header,
        [data-theme="light"] .sens-header,
        [data-theme="dark"] .sens-header {
            background-color: #18181b !important;
            color: #9ca3af !important;
            font-weight: 600 !important;
            border-bottom: 2px solid #3f3f46 !important;
        }
        
        .sens-header-base,
        td.sens-header-base,
        th.sens-header-base,
        .sensitivity-table .sens-header-base,
        .sensitivity-table th.sens-header-base,
        [data-theme="light"] .sens-header-base,
        [data-theme="dark"] .sens-header-base {
            background-color: #10b981 !important;
            color: white !important;
            font-weight: 700 !important;
            border-bottom: 2px solid #3f3f46 !important;
        }
        
        /* Row headers - SIEMPRE oscuros */
        .sens-row-header,
        td.sens-row-header,
        .sensitivity-table .sens-row-header,
        .sensitivity-table td.sens-row-header,
        [data-theme="light"] .sens-row-header,
        [data-theme="dark"] .sens-row-header {
            background-color: #18181b !important;
            color: #9ca3af !important;
            font-weight: 500 !important;
        }
        
        .sens-row-header-base,
        td.sens-row-header-base,
        .sensitivity-table .sens-row-header-base,
        .sensitivity-table td.sens-row-header-base,
        [data-theme="light"] .sens-row-header-base,
        [data-theme="dark"] .sens-row-header-base {
            background-color: #10b981 !important;
            color: white !important;
            font-weight: 700 !important;
        }
        
        /* Celdas de valoración - NUNCA CAMBIAN */
        .sens-very-undervalued,
        td.sens-very-undervalued,
        .sensitivity-table .sens-very-undervalued,
        .sensitivity-table td.sens-very-undervalued,
        [data-theme="light"] .sens-very-undervalued,
        [data-theme="dark"] .sens-very-undervalued {
            background-color: #166534 !important;
            color: white !important;
        }
        
        .sens-undervalued,
        td.sens-undervalued,
        .sensitivity-table .sens-undervalued,
        .sensitivity-table td.sens-undervalued,
        [data-theme="light"] .sens-undervalued,
        [data-theme="dark"] .sens-undervalued {
            background-color: #15803d !important;
            color: white !important;
        }
        
        .sens-fair,
        td.sens-fair,
        .sensitivity-table .sens-fair,
        .sensitivity-table td.sens-fair,
        [data-theme="light"] .sens-fair,
        [data-theme="dark"] .sens-fair {
            background-color: #854d0e !important;
            color: white !important;
        }
        
        .sens-overvalued,
        td.sens-overvalued,
        .sensitivity-table .sens-overvalued,
        .sensitivity-table td.sens-overvalued,
        [data-theme="light"] .sens-overvalued,
        [data-theme="dark"] .sens-overvalued {
            background-color: #b91c1c !important;
            color: white !important;
        }
        
        .sens-very-overvalued,
        td.sens-very-overvalued,
        .sensitivity-table .sens-very-overvalued,
        .sensitivity-table td.sens-very-overvalued,
        [data-theme="light"] .sens-very-overvalued,
        [data-theme="dark"] .sens-very-overvalued {
            background-color: #7f1d1d !important;
            color: white !important;
        }
        
        .sens-neutral,
        td.sens-neutral,
        .sensitivity-table .sens-neutral,
        .sensitivity-table td.sens-neutral,
        [data-theme="light"] .sens-neutral,
        [data-theme="dark"] .sens-neutral {
            background-color: #27272a !important;
            color: white !important;
        }
        
        /* Celda base */
        .sens-base-cell,
        td.sens-base-cell,
        .sensitivity-table .sens-base-cell,
        .sensitivity-table td.sens-base-cell {
            border: 3px solid #10b981 !important;
            border-radius: 6px !important;
            font-weight: 700 !important;
        }
        </style>
        <script>
        function applyThemeToInlineStyles(theme) {
            const isLight = theme === 'light';
            
            // PRIMERO: Limpiar TODOS los estilos inline de elementos de sensibilidad
            // para que las clases CSS tomen control
            document.querySelectorAll('.sensitivity-container, .sensitivity-table, .sensitivity-table td, .sensitivity-table th, [class*="sens-"]').forEach(el => {
                el.style.backgroundColor = '';
                el.style.color = '';
                el.style.borderColor = '';
            });
            
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
            const accentColors = ['#34d399', '#10b981', 'rgb(52, 211', 'rgb(16, 185'];
            
            // Cambiar colores de texto
            document.querySelectorAll('[style]').forEach(el => {
                // No modificar NADA dentro de la tabla o contenedor de sensibilidad
                if (el.closest('.sensitivity-table')) return;
                if (el.closest('.sensitivity-container')) return;
                if (el.hasAttribute('data-preserve')) return;
                
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
                
                // Texto accent (ahora verde)
                if (accentColors.some(col => style.includes(col))) {
                    el.style.color = isLight ? '#059669' : '#34d399';
                }
            });
            
            // Cambiar backgrounds
            document.querySelectorAll('[style*="background"]').forEach(el => {
                // No modificar NADA relacionado con sensibilidad
                if (el.closest('.sensitivity-table')) return;
                if (el.closest('.sensitivity-container')) return;
                if (el.className && typeof el.className === 'string' && el.className.includes('sensitivity')) return;
                if (el.className && typeof el.className === 'string' && el.className.includes('sens-')) return;
                if (el.hasAttribute('data-preserve')) return;
                
                const style = el.getAttribute('style') || '';
                
                // No cambiar botones con colores de acento (ahora verde)
                if (style.includes('#10b981') || style.includes('#34d399') || 
                    style.includes('#22c55e') || style.includes('#ef4444') ||
                    style.includes('#eab308') || style.includes('#3b82f6') ||
                    style.includes('linear-gradient')) {
                    return;
                }
                
                // No cambiar colores de valoración de sensibilidad
                if (style.includes('#166534') || style.includes('#15803d') ||
                    style.includes('#854d0e') || style.includes('#b91c1c') ||
                    style.includes('#7f1d1d')) {
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
                // No modificar NADA dentro de la tabla o contenedor de sensibilidad
                if (el.closest('.sensitivity-table')) return;
                if (el.closest('.sensitivity-container')) return;
                if (el.hasAttribute('data-preserve')) return;
                
                const style = el.getAttribute('style') || '';
                if (style.includes('#3f3f46') || style.includes('rgb(63, 63, 70)')) {
                    el.style.borderColor = c.border;
                }
            });
            
            // Metric cards en modo claro
            if (isLight) {
                document.querySelectorAll('.metric-card, [style*="rgba(39, 39, 42"]').forEach(el => {
                    el.style.backgroundColor = '#f8fafc';
                    el.style.borderColor = '#e2e8f0';
                });
                
                // Score card
                document.querySelectorAll('.score-card, [style*="#1f1f23"]').forEach(el => {
                    el.style.backgroundColor = '#f1f5f9';
                    el.style.borderColor = '#e2e8f0';
                });
                
                // Tabs
                document.querySelectorAll('.nav-tabs .nav-link').forEach(el => {
                    if (!el.classList.contains('active')) {
                        el.style.color = '#475569';
                    }
                });
                document.querySelectorAll('.nav-tabs .nav-link.active').forEach(el => {
                    el.style.color = '#059669';
                    el.style.borderBottomColor = '#10b981';
                });
                
                // Info icons en modo claro
                document.querySelectorAll('.info-icon').forEach(el => {
                    el.style.background = 'rgba(16, 185, 129, 0.1)';
                    el.style.color = '#059669';
                    el.style.borderColor = 'rgba(16, 185, 129, 0.3)';
                });
                
                // Quick picks en modo claro - buscar por estructura
                document.querySelectorAll('button').forEach(el => {
                    const id = el.getAttribute('id');
                    // Los quick picks tienen IDs que contienen "quick-pick"
                    if (id && id.includes('quick-pick')) {
                        el.style.background = '#e6f7f1';
                        el.style.border = '2px solid #10b981';
                        el.style.color = '#047857';
                        el.style.fontWeight = '600';
                    }
                });
                
                // Botones de período en modo claro
                document.querySelectorAll('.period-btn').forEach(el => {
                    if (el.classList.contains('btn-primary') && !el.classList.contains('btn-outline-primary')) {
                        // Botón activo - verde sólido
                        el.style.backgroundColor = '#10b981';
                        el.style.borderColor = '#10b981';
                        el.style.color = 'white';
                    } else {
                        // Botones inactivos - fondo claro con borde y texto verde oscuro
                        el.style.backgroundColor = '#e6f7f1';
                        el.style.border = '2px solid #10b981';
                        el.style.color = '#047857';
                        el.style.fontWeight = '600';
                    }
                });
                
                // Hero title y navbar title en modo claro
                document.querySelectorAll('#logo-home span:last-child').forEach(el => {
                    el.style.background = 'linear-gradient(135deg, #059669 0%, #047857 100%)';
                    el.style.webkitBackgroundClip = 'text';
                    el.style.webkitTextFillColor = 'transparent';
                });
            } else {
                // ============ MODO OSCURO ============
                
                // Quick picks en modo oscuro - restaurar colores originales
                document.querySelectorAll('button').forEach(el => {
                    const id = el.getAttribute('id');
                    if (id && id.includes('quick-pick')) {
                        el.style.background = 'rgba(16, 185, 129, 0.15)';
                        el.style.border = '1px solid rgba(16, 185, 129, 0.4)';
                        el.style.color = '#34d399';
                        el.style.fontWeight = '500';
                    }
                });
                
                // Botones de período en modo oscuro
                document.querySelectorAll('.period-btn').forEach(el => {
                    if (el.classList.contains('btn-primary') && !el.classList.contains('btn-outline-primary')) {
                        el.style.backgroundColor = '#10b981';
                        el.style.borderColor = '#10b981';
                        el.style.color = 'white';
                    } else {
                        el.style.backgroundColor = 'transparent';
                        el.style.border = '1px solid rgba(16, 185, 129, 0.4)';
                        el.style.color = '#34d399';
                        el.style.fontWeight = '500';
                    }
                });
                
                // Hero title en modo oscuro
                document.querySelectorAll('#logo-home span:last-child').forEach(el => {
                    el.style.background = 'linear-gradient(135deg, #34d399 0%, #10b981 100%)';
                    el.style.webkitBackgroundClip = 'text';
                    el.style.webkitTextFillColor = 'transparent';
                });
            }
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


# =============================================================================
# v2.9: COMPARADOR MULTI-ACCIÓN
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
        # Eliminar la más antigua
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
    
    # Crear tabla comparativa (usa fmt y get_metric_color de finanzer.utils.formatters)
    
    # Headers
    headers = ["Métrica"] + [s["symbol"] for s in comparison_list]
    
    # Filas de datos
    metrics_config = [
        ("Score", "score", "number"),
        ("P/E", "pe", "multiple"),
        ("ROE", "roe", "percent"),
        ("Deuda/Equity", "debt_equity", "multiple"),
        ("Margen Neto", "net_margin", "percent"),
        ("FCF Yield", "fcf_yield", "percent"),
        ("Div. Yield", "dividend_yield", "percent"),
    ]
    
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
            html.Tr([html.Th(h, style={"textAlign": "center", "padding": "10px", "borderBottom": "2px solid #3f3f46"}) for h in headers])
        ]),
        html.Tbody(rows, style={"textAlign": "center"})
    ], className="table table-dark", style={"width": "100%"})
    
    return html.Div([
        html.Div([
            html.H6(f"📊 Comparando {len(comparison_list)} acciones", className="mb-2"),
            html.Button("🗑️ Limpiar", id="btn-clear-comparison", n_clicks=0,
                       className="btn btn-outline-danger btn-sm", style={"fontSize": "0.75rem"})
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


if __name__ == "__main__":
    # Debug mode controlado por variable de entorno (default: False para producción)
    debug_mode = os.getenv("DEBUG", "false").lower() == "true"
    port = int(os.getenv("PORT", 8050))
    
    logger.info(f"Starting Finanzer - Debug: {debug_mode}, Port: {port}")
    app.run(debug=debug_mode, host="0.0.0.0", port=port)
