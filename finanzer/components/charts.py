"""
Finanzer - Componentes de gráficos.
Visualizaciones de datos financieros con Plotly.
"""

import logging
import yfinance as yf
import plotly.graph_objects as go

logger = logging.getLogger(__name__)


def get_score_color(score: int) -> tuple:
    """Retorna color y label según el score."""
    if score >= 70:
        return "#22c55e", "FAVORABLE"
    elif score >= 50:
        return "#eab308", "NEUTRAL"
    elif score >= 30:
        return "#f97316", "PRECAUCIÓN"
    else:
        return "#ef4444", "EVITAR"


def create_score_donut(score: int) -> go.Figure:
    """Crea gráfico donut moderno y minimalista para el score."""
    color, label = get_score_color(score)
    
    fig = go.Figure()
    
    # Track de fondo (gris oscuro sutil)
    fig.add_trace(go.Pie(
        values=[100],
        hole=0.78,
        marker=dict(colors=['#2d2d32']),
        showlegend=False,
        hoverinfo='none',
        textinfo='none'
    ))
    
    # Donut del score con gradiente visual
    remaining = 100 - score
    fig.add_trace(go.Pie(
        values=[score, remaining],
        hole=0.78,
        marker=dict(
            colors=[color, 'rgba(0,0,0,0)'], 
            line=dict(width=0)
        ),
        showlegend=False,
        hoverinfo='none',
        textinfo='none',
        rotation=90,
        direction='clockwise'
    ))
    
    # Score número
    fig.add_annotation(
        text=f"<b>{score}</b>", 
        x=0.5, y=0.52,
        font=dict(size=38, color=color, family='Inter, system-ui'),
        showarrow=False
    )
    
    # Label descriptivo
    fig.add_annotation(
        text=label.upper(), 
        x=0.5, y=0.30,
        font=dict(size=10, color='#6b7280', family='Inter, system-ui', weight=500),
        showarrow=False
    )
    
    fig.update_layout(
        height=160,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'family': 'Inter, system-ui, sans-serif'}
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
