"""
Stock Analyzer - Configuración Centralizada
============================================
Todas las constantes y parámetros configurables en un solo lugar.

Autor: Esteban
Versión: 2.5
"""

from dataclasses import dataclass
from typing import Dict

# =============================================================================
# ALTMAN Z-SCORE THRESHOLDS
# =============================================================================
# Fuente: Altman, E. I. (1968). "Financial Ratios, Discriminant Analysis 
# and the Prediction of Corporate Bankruptcy"

ALTMAN_Z_SAFE = 2.99          # Z > 2.99: Zona segura
ALTMAN_Z_GREY = 1.81          # 1.81 < Z < 2.99: Zona gris
# Z < 1.81: Zona de peligro

ALTMAN_Z_LABELS = {
    "SAFE": "Zona segura - Bajo riesgo de bancarrota",
    "GREY": "Zona gris - Riesgo moderado, monitorear",
    "DISTRESS": "Zona de peligro - Alto riesgo de bancarrota"
}

# =============================================================================
# PIOTROSKI F-SCORE THRESHOLDS
# =============================================================================
# Fuente: Piotroski, J. D. (2000). "Value Investing: The Use of Historical 
# Financial Statement Information to Separate Winners from Losers"

PIOTROSKI_STRONG = 7          # 7-9: Señal fuerte de compra
PIOTROSKI_NEUTRAL = 4         # 4-6: Neutral
PIOTROSKI_WEAK = 3            # 0-3: Señal de venta

PIOTROSKI_LABELS = {
    "STRONG": "Solidez financiera excepcional",
    "GOOD": "Buena salud financiera",
    "NEUTRAL": "Salud financiera neutral",
    "WEAK": "Señales de debilidad financiera"
}

# =============================================================================
# DCF MODEL PARAMETERS
# =============================================================================

# Tasas base (actualizables según condiciones de mercado)
DCF_RISK_FREE_RATE = 0.045        # 4.5% - US Treasury 10Y (actualizar periódicamente)
DCF_MARKET_RISK_PREMIUM = 0.055   # 5.5% - Prima de riesgo histórica
DCF_TERMINAL_GROWTH = 0.025       # 2.5% - Crecimiento perpetuo (~ inflación + PIB real)

# Límites de WACC
DCF_WACC_MIN = 0.06               # 6% mínimo razonable
DCF_WACC_MAX = 0.20               # 20% máximo razonable
DCF_WACC_DEFAULT = 0.10           # 10% default si no hay datos

# Límites de Growth
DCF_GROWTH_MAX = 0.50             # 50% cap máximo (ninguna empresa crece más indefinidamente)
DCF_GROWTH_DEFAULT = 0.08         # 8% default si no hay datos históricos

# Años de proyección
DCF_HIGH_GROWTH_YEARS = 5         # Años de alto crecimiento
DCF_TRANSITION_YEARS = 5          # Años de transición
DCF_TOTAL_YEARS = 10              # Total de años proyectados

# =============================================================================
# SCORING SYSTEM (100 PUNTOS)
# =============================================================================

SCORE_BASE = 50                   # Puntuación base inicial
SCORE_MAX = 100                   # Máximo posible
SCORE_MIN = 0                     # Mínimo posible

# Categorías y pesos
SCORE_CATEGORIES = {
    "solidez": {"peso": 20, "descripcion": "Solidez Financiera"},
    "rentabilidad": {"peso": 20, "descripcion": "Rentabilidad"},
    "valoracion": {"peso": 20, "descripcion": "Valoración"},
    "calidad": {"peso": 20, "descripcion": "Calidad de Ganancias"},
    "crecimiento": {"peso": 20, "descripcion": "Crecimiento"}
}

# Niveles de score
SCORE_LEVELS = {
    "EXCEPTIONAL": {"min": 80, "color": "#22c55e", "label": "Excepcional"},
    "GOOD": {"min": 65, "color": "#84cc16", "label": "Bueno"},
    "FAIR": {"min": 50, "color": "#eab308", "label": "Aceptable"},
    "WEAK": {"min": 35, "color": "#f97316", "label": "Débil"},
    "POOR": {"min": 0, "color": "#ef4444", "label": "Pobre"}
}

# =============================================================================
# GROWTH QUALITY THRESHOLDS
# =============================================================================

GROWTH_QUALITY_EXCELLENT = 80     # Score >= 80: Crecimiento de alta calidad
GROWTH_QUALITY_GOOD = 65          # Score >= 65: Buen crecimiento
GROWTH_QUALITY_FAIR = 50          # Score >= 50: Crecimiento aceptable
GROWTH_QUALITY_POOR = 35          # Score < 35: Crecimiento de baja calidad

# Thresholds para clasificar tipo de empresa
GROWTH_COMPANY_REVENUE_THRESHOLD = 0.15    # >15% revenue growth = growth company
GROWTH_COMPANY_EPS_THRESHOLD = 0.20        # >20% EPS growth = growth company
VALUE_COMPANY_PE_THRESHOLD = 15            # P/E < 15 = value company
VALUE_COMPANY_PB_THRESHOLD = 1.5           # P/B < 1.5 = value company

# =============================================================================
# RATIOS THRESHOLDS (GENERALES)
# =============================================================================

# Liquidez
CURRENT_RATIO_GOOD = 2.0          # >= 2.0: Buena liquidez
CURRENT_RATIO_MIN = 1.0           # >= 1.0: Liquidez mínima aceptable
QUICK_RATIO_GOOD = 1.0            # >= 1.0: Buena liquidez rápida

# Solvencia
DEBT_EQUITY_LOW = 0.5             # D/E < 0.5: Bajo apalancamiento
DEBT_EQUITY_HIGH = 2.0            # D/E > 2.0: Alto apalancamiento
INTEREST_COVERAGE_GOOD = 5.0      # >= 5x: Buena cobertura
INTEREST_COVERAGE_MIN = 2.0       # >= 2x: Cobertura mínima

# Rentabilidad
ROE_EXCELLENT = 0.20              # >= 20%: ROE excepcional
ROE_GOOD = 0.15                   # >= 15%: Buen ROE
ROE_MIN = 0.10                    # >= 10%: ROE mínimo aceptable
ROA_GOOD = 0.08                   # >= 8%: Buen ROA
ROIC_GOOD = 0.12                  # >= 12%: Buen ROIC (> WACC típico)

# Márgenes
GROSS_MARGIN_HIGH = 0.40          # >= 40%: Alto margen bruto
OPERATING_MARGIN_HIGH = 0.20      # >= 20%: Alto margen operativo
NET_MARGIN_HIGH = 0.15            # >= 15%: Alto margen neto

# Valoración
PE_LOW = 15                       # P/E < 15: Potencialmente barato
PE_HIGH = 25                      # P/E > 25: Potencialmente caro
PB_LOW = 1.5                      # P/B < 1.5: Potencialmente barato
PB_HIGH = 3.0                     # P/B > 3.0: Potencialmente caro
PEG_FAIR = 1.0                    # PEG = 1: Valoración justa
FCF_YIELD_HIGH = 0.08             # >= 8%: Alto FCF yield

# =============================================================================
# CACHE SETTINGS
# =============================================================================

CACHE_TTL_MINUTES = 10            # Tiempo de vida del caché (minutos)
CACHE_MAX_ENTRIES = 500           # Máximo de entradas en caché
CACHE_PROFILE_TTL = 30            # TTL para perfiles (cambian poco)

# =============================================================================
# API RATE LIMITS
# =============================================================================

YAHOO_FINANCE_DELAY = 0.5         # Segundos entre requests
MAX_PARALLEL_REQUESTS = 4         # Máximo de requests paralelos

# =============================================================================
# UI SETTINGS
# =============================================================================

# Colores del tema
UI_COLORS = {
    "primary": "#3b82f6",         # Azul principal
    "success": "#22c55e",         # Verde éxito
    "warning": "#eab308",         # Amarillo advertencia
    "danger": "#ef4444",          # Rojo peligro
    "info": "#06b6d4",            # Cyan info
    "neutral": "#71717a",         # Gris neutral
    "background": "#18181b",      # Fondo oscuro
    "card": "#27272a",            # Fondo de tarjetas
    "text": "#fafafa",            # Texto principal
    "text_muted": "#a1a1aa"       # Texto secundario
}

# Formato de números
NUMBER_FORMAT = {
    "currency_decimals": 2,
    "percentage_decimals": 1,
    "ratio_decimals": 2,
    "large_number_suffix": True   # 1.5B en lugar de 1,500,000,000
}

# =============================================================================
# SECTOR-SPECIFIC ADJUSTMENTS
# =============================================================================

SECTOR_ADJUSTMENTS = {
    "financials": {
        "ignore_debt_equity": True,
        "debt_equity_max": 15.0,
        "pe_weight": 0.5,
        "pb_relevant": True,
        "typical_roe": 0.12
    },
    "real_estate": {
        "ignore_pe": True,
        "use_ffo": True,
        "dividend_weight": 2.0,
        "debt_equity_max": 1.5
    },
    "utilities": {
        "debt_equity_max": 2.0,
        "dividend_weight": 1.5,
        "pe_max": 25,
        "growth_less_relevant": True
    },
    "technology": {
        "pe_tolerance": 1.5,
        "growth_weight": 1.5,
        "fcf_negative_tolerance": True
    },
    "healthcare": {
        "pe_tolerance": 1.3,
        "margin_weight": 1.3
    },
    "energy": {
        "ev_ebitda_weight": 1.5,
        "pe_weight": 0.7,
        "cyclical_adjustment": True
    }
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_score_level(score: float) -> dict:
    """Retorna el nivel correspondiente a un score."""
    for level_name, config in SCORE_LEVELS.items():
        if score >= config["min"]:
            return {"name": level_name, **config}
    return {"name": "POOR", **SCORE_LEVELS["POOR"]}


def get_altman_zone(z_score: float) -> str:
    """Retorna la zona de Altman Z-Score."""
    if z_score > ALTMAN_Z_SAFE:
        return "SAFE"
    elif z_score > ALTMAN_Z_GREY:
        return "GREY"
    return "DISTRESS"


def get_piotroski_level(f_score: int) -> str:
    """Retorna el nivel de Piotroski F-Score."""
    if f_score >= PIOTROSKI_STRONG:
        return "STRONG"
    elif f_score >= PIOTROSKI_NEUTRAL:
        return "NEUTRAL"
    return "WEAK"


# =============================================================================
# VERSION INFO
# =============================================================================

VERSION = "2.7"
VERSION_NAME = "Finanzer"
VERSION_DATE = "2025-12-21"
