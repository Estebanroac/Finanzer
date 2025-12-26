"""
Pytest Configuration and Shared Fixtures
=========================================
Fixtures reutilizables para toda la suite de tests.

Contiene:
- Datos de empresas de ejemplo (value, growth, distressed)
- Configuraciones de sector
- Mocks para Yahoo Finance
- Helpers para assertions
"""

import pytest
import sys
import os

# Agregar el directorio padre al path para imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# =============================================================================
# FIXTURES: DATOS DE EMPRESAS DE EJEMPLO
# =============================================================================

@pytest.fixture
def healthy_company_data():
    """
    Datos de una empresa saludable típica (tipo JNJ, PG).
    Z-Score: SAFE, F-Score: 7-8, Score total esperado: 70-85
    """
    return {
        # Datos básicos
        "symbol": "HEALTHY",
        "name": "Healthy Corp",
        "sector": "Consumer Defensive",
        "price": 150.0,
        "shares_outstanding": 1_000_000_000,
        
        # Balance Sheet
        "working_capital": 5_000_000_000,
        "total_assets": 50_000_000_000,
        "retained_earnings": 20_000_000_000,
        "total_liabilities": 15_000_000_000,
        "long_term_debt": 8_000_000_000,
        "long_term_debt_prior": 9_000_000_000,  # Bajó
        "market_cap": 150_000_000_000,
        
        # Income Statement
        "revenue": 40_000_000_000,
        "ebit": 8_000_000_000,
        "net_income": 6_000_000_000,
        "interest_expense": 400_000_000,
        "gross_profit": 16_000_000_000,
        "gross_profit_prior": 15_000_000_000,
        
        # Cash Flow
        "operating_cash_flow": 7_000_000_000,
        "free_cash_flow": 5_000_000_000,
        "capex": 2_000_000_000,
        
        # Ratios calculados
        "pe": 25.0,
        "pb": 2.5,
        "ps": 3.75,
        "roe": 0.17,  # 17%
        "roa": 0.12,  # 12%
        "roa_prior": 0.11,
        "current_ratio": 1.8,
        "current_ratio_prior": 1.7,
        "debt_to_equity": 0.45,
        "interest_coverage": 20.0,
        "gross_margin": 0.40,
        "gross_margin_prior": 0.38,
        "operating_margin": 0.20,
        "net_margin": 0.15,
        "fcf_yield": 0.033,  # 3.3%
        "dividend_yield": 0.025,
        "peg": 1.5,
        "ev_ebitda": 12.0,
        
        # Growth
        "revenue_growth_3y": 0.08,  # 8%
        "eps_growth_3y": 0.10,  # 10%
        "fcf_growth_3y": 0.07,  # 7%
        
        # Shares (sin dilución)
        "shares_current": 1_000_000_000,
        "shares_prior": 1_000_000_000,
        
        # Asset Turnover
        "asset_turnover_current": 0.80,
        "asset_turnover_prior": 0.78,
        
        # Sector context
        "sector_pe": 22.0,
        "sector_ev_ebitda": 11.0,
    }


@pytest.fixture
def growth_company_data():
    """
    Datos de una empresa growth de alta calidad (tipo NVDA, AMZN).
    P/E alto pero justificado por crecimiento excepcional.
    Z-Score: SAFE, F-Score: 6-7, Score total esperado: 65-80
    """
    return {
        "symbol": "GROWTH",
        "name": "Growth Tech Inc",
        "sector": "Technology",
        "price": 500.0,
        "shares_outstanding": 500_000_000,
        
        # Balance Sheet
        "working_capital": 8_000_000_000,
        "total_assets": 40_000_000_000,
        "retained_earnings": 15_000_000_000,
        "total_liabilities": 10_000_000_000,
        "long_term_debt": 3_000_000_000,
        "long_term_debt_prior": 3_500_000_000,
        "market_cap": 250_000_000_000,
        
        # Income Statement
        "revenue": 30_000_000_000,
        "ebit": 9_000_000_000,
        "net_income": 7_000_000_000,
        "interest_expense": 150_000_000,
        "gross_profit": 18_000_000_000,
        "gross_profit_prior": 14_000_000_000,
        
        # Cash Flow
        "operating_cash_flow": 10_000_000_000,
        "free_cash_flow": 8_000_000_000,
        "capex": 2_000_000_000,
        
        # Ratios - P/E alto pero justificado
        "pe": 55.0,  # Alto
        "pb": 8.0,
        "ps": 8.3,
        "roe": 0.35,  # 35% - Excepcional
        "roa": 0.175,
        "roa_prior": 0.15,
        "current_ratio": 2.5,
        "current_ratio_prior": 2.3,
        "debt_to_equity": 0.12,  # Muy bajo
        "interest_coverage": 60.0,
        "gross_margin": 0.60,  # 60%
        "gross_margin_prior": 0.55,
        "operating_margin": 0.30,
        "net_margin": 0.233,
        "fcf_yield": 0.032,
        "dividend_yield": 0.0,  # No paga dividendos
        "peg": 1.1,  # Bueno para growth
        "ev_ebitda": 22.0,
        
        # Growth - Excepcional
        "revenue_growth_3y": 0.35,  # 35%
        "eps_growth_3y": 0.50,  # 50%
        "fcf_growth_3y": 0.40,  # 40%
        
        # Sin dilución
        "shares_current": 500_000_000,
        "shares_prior": 500_000_000,
        
        "asset_turnover_current": 0.75,
        "asset_turnover_prior": 0.70,
        
        # Sector context
        "sector_pe": 28.0,
        "sector_ev_ebitda": 18.0,
        
        # ROIC para growth quality
        "roic": 0.30,
    }


@pytest.fixture
def distressed_company_data():
    """
    Datos de una empresa en problemas financieros.
    Z-Score: DISTRESS, F-Score: 2-3, Score total esperado: 20-35
    """
    return {
        "symbol": "DISTRESS",
        "name": "Troubled Corp",
        "sector": "Consumer Cyclical",
        "price": 5.0,
        "shares_outstanding": 200_000_000,
        
        # Balance Sheet - Débil
        "working_capital": -500_000_000,  # Negativo!
        "total_assets": 10_000_000_000,
        "retained_earnings": -2_000_000_000,  # Pérdidas acumuladas
        "total_liabilities": 9_000_000_000,
        "long_term_debt": 6_000_000_000,
        "long_term_debt_prior": 5_000_000_000,  # Subió
        "market_cap": 1_000_000_000,
        
        # Income Statement - Pérdidas
        "revenue": 8_000_000_000,
        "ebit": -200_000_000,  # Pérdida operativa
        "net_income": -500_000_000,  # Pérdida neta
        "interest_expense": 400_000_000,
        "gross_profit": 1_500_000_000,
        "gross_profit_prior": 2_000_000_000,  # Empeoró
        
        # Cash Flow - Quemando caja
        "operating_cash_flow": -100_000_000,
        "free_cash_flow": -300_000_000,
        "capex": 200_000_000,
        
        # Ratios - Malos
        "pe": -2.0,  # Negativo (pérdidas)
        "pb": 0.5,
        "ps": 0.125,
        "roe": -0.50,  # -50%
        "roa": -0.05,
        "roa_prior": 0.02,  # Empeoró
        "current_ratio": 0.7,  # < 1 es malo
        "current_ratio_prior": 0.9,  # Empeoró
        "debt_to_equity": 9.0,  # Muy alto
        "interest_coverage": -0.5,  # No cubre intereses
        "gross_margin": 0.19,
        "gross_margin_prior": 0.25,  # Empeoró
        "operating_margin": -0.025,
        "net_margin": -0.0625,
        "fcf_yield": -0.30,
        "dividend_yield": 0.0,
        "peg": None,  # N/A con earnings negativos
        "ev_ebitda": None,
        
        # Growth - Negativo
        "revenue_growth_3y": -0.10,  # Contracción
        "eps_growth_3y": -0.50,
        "fcf_growth_3y": -0.40,
        
        # Dilución
        "shares_current": 200_000_000,
        "shares_prior": 150_000_000,  # Dilución!
        
        "asset_turnover_current": 0.80,
        "asset_turnover_prior": 0.90,  # Empeoró
        
        "sector_pe": 15.0,
        "sector_ev_ebitda": 10.0,
    }


@pytest.fixture
def value_company_data():
    """
    Datos de una empresa value clásica (tipo BRK, bancos sólidos).
    P/E bajo, dividendos, crecimiento moderado.
    """
    return {
        "symbol": "VALUE",
        "name": "Value Industries",
        "sector": "Financials",
        "price": 80.0,
        "shares_outstanding": 800_000_000,
        
        # Balance sólido
        "working_capital": 10_000_000_000,
        "total_assets": 100_000_000_000,
        "retained_earnings": 30_000_000_000,
        "total_liabilities": 60_000_000_000,
        "long_term_debt": 20_000_000_000,
        "long_term_debt_prior": 22_000_000_000,
        "market_cap": 64_000_000_000,
        
        # Income sólido
        "revenue": 25_000_000_000,
        "ebit": 8_000_000_000,
        "net_income": 6_000_000_000,
        "interest_expense": 1_000_000_000,
        "gross_profit": 15_000_000_000,
        "gross_profit_prior": 14_500_000_000,
        
        # Cash Flow fuerte
        "operating_cash_flow": 7_500_000_000,
        "free_cash_flow": 6_000_000_000,
        "capex": 1_500_000_000,
        
        # Ratios value
        "pe": 10.7,  # Bajo
        "pb": 1.6,
        "ps": 2.56,
        "roe": 0.15,
        "roa": 0.06,
        "roa_prior": 0.055,
        "current_ratio": 1.5,
        "current_ratio_prior": 1.4,
        "debt_to_equity": 1.5,  # Normal para financials
        "interest_coverage": 8.0,
        "gross_margin": 0.60,
        "gross_margin_prior": 0.58,
        "operating_margin": 0.32,
        "net_margin": 0.24,
        "fcf_yield": 0.094,  # 9.4% - Excelente
        "dividend_yield": 0.04,  # 4%
        "peg": 0.9,
        "ev_ebitda": 8.0,
        
        # Growth moderado
        "revenue_growth_3y": 0.05,
        "eps_growth_3y": 0.08,
        "fcf_growth_3y": 0.06,
        
        "shares_current": 800_000_000,
        "shares_prior": 820_000_000,  # Recompra
        
        "asset_turnover_current": 0.25,
        "asset_turnover_prior": 0.24,
        
        "sector_pe": 12.0,
        "sector_ev_ebitda": 9.0,
    }


@pytest.fixture
def garp_company_data():
    """
    Datos de una empresa GARP (Growth at Reasonable Price).
    Crecimiento sólido con valoración razonable.
    """
    return {
        "symbol": "GARP",
        "name": "GARP Corp",
        "sector": "Technology",
        "price": 200.0,
        "shares_outstanding": 300_000_000,
        
        "working_capital": 4_000_000_000,
        "total_assets": 25_000_000_000,
        "retained_earnings": 10_000_000_000,
        "total_liabilities": 8_000_000_000,
        "long_term_debt": 3_000_000_000,
        "long_term_debt_prior": 3_200_000_000,
        "market_cap": 60_000_000_000,
        
        "revenue": 15_000_000_000,
        "ebit": 4_000_000_000,
        "net_income": 3_000_000_000,
        "interest_expense": 150_000_000,
        "gross_profit": 9_000_000_000,
        "gross_profit_prior": 7_500_000_000,
        
        "operating_cash_flow": 4_000_000_000,
        "free_cash_flow": 3_200_000_000,
        "capex": 800_000_000,
        
        # Valoración razonable para su crecimiento
        "pe": 20.0,
        "pb": 3.5,
        "ps": 4.0,
        "roe": 0.24,  # 24% - Muy bueno
        "roa": 0.12,
        "roa_prior": 0.10,
        "current_ratio": 2.0,
        "current_ratio_prior": 1.9,
        "debt_to_equity": 0.47,
        "interest_coverage": 26.7,
        "gross_margin": 0.60,
        "gross_margin_prior": 0.55,
        "operating_margin": 0.267,
        "net_margin": 0.20,
        "fcf_yield": 0.053,  # 5.3%
        "dividend_yield": 0.01,
        "peg": 1.0,  # Perfecto
        "ev_ebitda": 14.0,
        
        # Growth sólido
        "revenue_growth_3y": 0.20,  # 20%
        "eps_growth_3y": 0.25,  # 25%
        "fcf_growth_3y": 0.22,
        
        "shares_current": 300_000_000,
        "shares_prior": 300_000_000,
        
        "asset_turnover_current": 0.60,
        "asset_turnover_prior": 0.55,
        
        "sector_pe": 28.0,
        "sector_ev_ebitda": 18.0,
        
        "roic": 0.22,
    }


# =============================================================================
# FIXTURES: DATOS PARA ALTMAN Z-SCORE
# =============================================================================

@pytest.fixture
def altman_safe_zone_data():
    """Datos que producen Z-Score > 2.99 (zona segura)."""
    return {
        "working_capital": 5_000_000_000,
        "total_assets": 10_000_000_000,
        "retained_earnings": 3_000_000_000,
        "ebit": 1_500_000_000,
        "market_value_equity": 20_000_000_000,
        "total_liabilities": 4_000_000_000,
        "sales": 15_000_000_000,
    }


@pytest.fixture
def altman_grey_zone_data():
    """Datos que producen 1.81 < Z-Score < 2.99 (zona gris)."""
    return {
        "working_capital": 1_000_000_000,
        "total_assets": 10_000_000_000,
        "retained_earnings": 500_000_000,
        "ebit": 600_000_000,
        "market_value_equity": 8_000_000_000,
        "total_liabilities": 6_000_000_000,
        "sales": 12_000_000_000,
    }


@pytest.fixture
def altman_distress_zone_data():
    """Datos que producen Z-Score < 1.81 (zona de peligro)."""
    return {
        "working_capital": -500_000_000,
        "total_assets": 10_000_000_000,
        "retained_earnings": -1_000_000_000,
        "ebit": 200_000_000,
        "market_value_equity": 2_000_000_000,
        "total_liabilities": 9_000_000_000,
        "sales": 8_000_000_000,
    }


# =============================================================================
# FIXTURES: CONFIGURACIÓN DE SECTORES
# =============================================================================

@pytest.fixture
def technology_sector_context():
    """Contexto típico del sector tecnología."""
    return {
        "sector_key": "technology",
        "sector_pe": 28.0,
        "sector_ev_ebitda": 18.0,
        "typical_gross_margin": 0.55,
        "typical_operating_margin": 0.20,
        "typical_roe": 0.20,
        "typical_debt_to_equity": 0.40,
    }


@pytest.fixture
def financials_sector_context():
    """Contexto típico del sector financiero."""
    return {
        "sector_key": "financials",
        "sector_pe": 12.0,
        "sector_ev_ebitda": 9.0,
        "typical_roe": 0.12,
        "typical_debt_to_equity": 8.0,  # Alto es normal
    }


@pytest.fixture
def consumer_defensive_sector_context():
    """Contexto típico del sector consumer defensive."""
    return {
        "sector_key": "consumer_defensive",
        "sector_pe": 22.0,
        "sector_ev_ebitda": 14.0,
        "typical_gross_margin": 0.35,
        "typical_operating_margin": 0.15,
        "typical_roe": 0.20,
        "typical_dividend_yield": 0.025,
    }


# =============================================================================
# HELPERS PARA ASSERTIONS
# =============================================================================

def assert_score_in_range(score: int, min_score: int, max_score: int, context: str = ""):
    """Helper para validar que un score está en rango esperado."""
    assert min_score <= score <= max_score, \
        f"Score {score} fuera de rango [{min_score}, {max_score}]. {context}"


def assert_z_score_zone(z_score: float, expected_zone: str):
    """Helper para validar zona de Altman Z-Score."""
    if expected_zone == "SAFE":
        assert z_score > 2.99, f"Z-Score {z_score} debería ser > 2.99 para SAFE"
    elif expected_zone == "GREY":
        assert 1.81 < z_score <= 2.99, f"Z-Score {z_score} debería ser 1.81-2.99 para GREY"
    elif expected_zone == "DISTRESS":
        assert z_score <= 1.81, f"Z-Score {z_score} debería ser <= 1.81 para DISTRESS"


def assert_f_score_level(f_score: int, expected_level: str):
    """Helper para validar nivel de Piotroski F-Score."""
    levels = {
        "exceptional": (8, 9),
        "good": (6, 7),
        "neutral": (4, 5),
        "weak": (2, 3),
        "critical": (0, 1),
    }
    min_s, max_s = levels[expected_level]
    assert min_s <= f_score <= max_s, \
        f"F-Score {f_score} debería ser {min_s}-{max_s} para {expected_level}"


# =============================================================================
# PYTEST MARKERS
# =============================================================================

def pytest_configure(config):
    """Configurar markers personalizados."""
    config.addinivalue_line(
        "markers", "slow: marca tests que son lentos (requieren API calls)"
    )
    config.addinivalue_line(
        "markers", "integration: marca tests de integración"
    )
    config.addinivalue_line(
        "markers", "snapshot: marca tests de snapshot"
    )
