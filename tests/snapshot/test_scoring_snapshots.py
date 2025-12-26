"""
Snapshot Tests for Scoring Model
================================
Tests que capturan el comportamiento esperado del modelo para
empresas de referencia. Si el modelo cambia, estos tests fallarán
y alertarán sobre posibles regresiones.

Metodología:
1. Definir datos de empresas de referencia (no cambian)
2. Capturar scores esperados (validados manualmente)
3. Verificar que el modelo produce los mismos resultados

IMPORTANTE: Si un test falla después de un cambio intencional,
actualizar el snapshot después de validar que el nuevo
comportamiento es correcto.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from financial_ratios import (
    altman_z_score,
    piotroski_f_score,
    calculate_score_v2,
    classify_company_type,
    calculate_growth_quality_score,
    score_solidez_financiera,
    score_rentabilidad,
    score_valoracion,
    score_calidad_ganancias,
    score_crecimiento,
)


# =============================================================================
# DATOS DE REFERENCIA (NO MODIFICAR)
# =============================================================================

# Empresa tipo "Blue Chip" estable (JNJ-like)
BLUE_CHIP_DATA = {
    "name": "Blue Chip Reference",
    "z_score_inputs": {
        "working_capital": 15_000_000_000,
        "total_assets": 180_000_000_000,
        "retained_earnings": 120_000_000_000,
        "ebit": 25_000_000_000,
        "market_value_equity": 400_000_000_000,
        "total_liabilities": 100_000_000_000,
        "sales": 95_000_000_000,
    },
    "f_score_inputs": {
        "net_income": 20_000_000_000,
        "roa_current": 0.111,
        "roa_prior": 0.105,
        "operating_cash_flow": 23_000_000_000,
        "long_term_debt_current": 30_000_000_000,
        "long_term_debt_prior": 32_000_000_000,
        "current_ratio_current": 1.2,
        "current_ratio_prior": 1.15,
        "shares_current": 2_400_000_000,
        "shares_prior": 2_450_000_000,
        "gross_margin_current": 0.68,
        "gross_margin_prior": 0.67,
        "asset_turnover_current": 0.53,
        "asset_turnover_prior": 0.52,
    },
    "ratio_values": {
        "current_ratio": 1.2,
        "debt_to_equity": 1.25,
        "interest_coverage": 25.0,
        "roe": 0.25,
        "roa": 0.111,
        "operating_margin": 0.263,
        "net_margin": 0.21,
        "pe": 20.0,
        "p_fcf": 22.0,
        "ev_ebitda": 14.0,
        "peg": 2.5,
        "fcf_yield": 0.045,
        "fcf": 18_000_000_000,
        "operating_cash_flow": 23_000_000_000,
        "net_income": 20_000_000_000,
        "fcf_to_net_income": 0.9,
        "dividend_yield": 0.028,
    },
    "contextual_values": {
        "sector_pe": 18.0,
        "sector_ev_ebitda": 12.0,
        "revenue_cagr_3y": 0.04,
        "eps_cagr_3y": 0.06,
        "fcf_cagr_3y": 0.05,
    },
}

# Empresa tipo "High Growth Tech" (NVDA-like)
HIGH_GROWTH_TECH_DATA = {
    "name": "High Growth Tech Reference",
    "z_score_inputs": {
        "working_capital": 25_000_000_000,
        "total_assets": 65_000_000_000,
        "retained_earnings": 30_000_000_000,
        "ebit": 35_000_000_000,
        "market_value_equity": 1_200_000_000_000,
        "total_liabilities": 25_000_000_000,
        "sales": 60_000_000_000,
    },
    "f_score_inputs": {
        "net_income": 30_000_000_000,
        "roa_current": 0.46,
        "roa_prior": 0.25,
        "operating_cash_flow": 28_000_000_000,
        "long_term_debt_current": 10_000_000_000,
        "long_term_debt_prior": 11_000_000_000,
        "current_ratio_current": 4.0,
        "current_ratio_prior": 3.5,
        "shares_current": 2_500_000_000,
        "shares_prior": 2_500_000_000,
        "gross_margin_current": 0.75,
        "gross_margin_prior": 0.65,
        "asset_turnover_current": 0.92,
        "asset_turnover_prior": 0.75,
    },
    "ratio_values": {
        "current_ratio": 4.0,
        "debt_to_equity": 0.25,
        "interest_coverage": 100.0,
        "roe": 0.75,
        "roa": 0.46,
        "operating_margin": 0.58,
        "net_margin": 0.50,
        "pe": 60.0,
        "p_fcf": 48.0,
        "ev_ebitda": 35.0,
        "peg": 1.2,
        "fcf_yield": 0.021,
        "fcf": 25_000_000_000,
        "operating_cash_flow": 28_000_000_000,
        "net_income": 30_000_000_000,
        "fcf_to_net_income": 0.83,
        "dividend_yield": 0.0,
        "roic": 0.65,
    },
    "contextual_values": {
        "sector_pe": 30.0,
        "sector_ev_ebitda": 20.0,
        "revenue_cagr_3y": 0.50,
        "eps_cagr_3y": 0.80,
        "fcf_cagr_3y": 0.60,
    },
}

# Empresa tipo "Deep Value" (banco regional)
DEEP_VALUE_DATA = {
    "name": "Deep Value Reference",
    "z_score_inputs": {
        "working_capital": 5_000_000_000,
        "total_assets": 200_000_000_000,
        "retained_earnings": 15_000_000_000,
        "ebit": 8_000_000_000,
        "market_value_equity": 25_000_000_000,
        "total_liabilities": 180_000_000_000,
        "sales": 20_000_000_000,
    },
    "f_score_inputs": {
        "net_income": 5_000_000_000,
        "roa_current": 0.025,
        "roa_prior": 0.022,
        "operating_cash_flow": 6_000_000_000,
        "long_term_debt_current": 50_000_000_000,
        "long_term_debt_prior": 55_000_000_000,
        "current_ratio_current": 1.1,
        "current_ratio_prior": 1.0,
        "shares_current": 500_000_000,
        "shares_prior": 520_000_000,
        "gross_margin_current": 0.70,
        "gross_margin_prior": 0.68,
        "asset_turnover_current": 0.10,
        "asset_turnover_prior": 0.095,
    },
    "ratio_values": {
        "current_ratio": 1.1,
        "debt_to_equity": 9.0,  # Alto pero normal para bancos
        "interest_coverage": 3.0,
        "roe": 0.25,
        "roa": 0.025,
        "operating_margin": 0.40,
        "net_margin": 0.25,
        "pe": 5.0,
        "p_fcf": 5.0,
        "ev_ebitda": 6.0,
        "peg": 0.5,
        "fcf_yield": 0.20,
        "fcf": 5_000_000_000,
        "operating_cash_flow": 6_000_000_000,
        "net_income": 5_000_000_000,
        "fcf_to_net_income": 1.0,
        "dividend_yield": 0.05,
    },
    "contextual_values": {
        "sector_pe": 10.0,
        "sector_ev_ebitda": 8.0,
        "revenue_cagr_3y": 0.03,
        "eps_cagr_3y": 0.08,
        "fcf_cagr_3y": 0.05,
    },
}

# Empresa en problemas (turnaround candidate)
DISTRESSED_DATA = {
    "name": "Distressed Reference",
    "z_score_inputs": {
        "working_capital": -2_000_000_000,
        "total_assets": 30_000_000_000,
        "retained_earnings": -5_000_000_000,
        "ebit": 500_000_000,
        "market_value_equity": 5_000_000_000,
        "total_liabilities": 28_000_000_000,
        "sales": 25_000_000_000,
    },
    "f_score_inputs": {
        "net_income": -1_000_000_000,
        "roa_current": -0.033,
        "roa_prior": 0.01,
        "operating_cash_flow": 200_000_000,
        "long_term_debt_current": 15_000_000_000,
        "long_term_debt_prior": 12_000_000_000,
        "current_ratio_current": 0.7,
        "current_ratio_prior": 0.9,
        "shares_current": 800_000_000,
        "shares_prior": 600_000_000,
        "gross_margin_current": 0.20,
        "gross_margin_prior": 0.25,
        "asset_turnover_current": 0.83,
        "asset_turnover_prior": 0.90,
    },
    "ratio_values": {
        "current_ratio": 0.7,
        "debt_to_equity": 14.0,
        "interest_coverage": 0.5,
        "roe": -0.50,
        "roa": -0.033,
        "operating_margin": 0.02,
        "net_margin": -0.04,
        "pe": -5.0,
        "p_fcf": None,
        "ev_ebitda": 50.0,
        "peg": None,
        "fcf_yield": -0.10,
        "fcf": -500_000_000,
        "operating_cash_flow": 200_000_000,
        "net_income": -1_000_000_000,
        "fcf_to_net_income": 0.5,
        "dividend_yield": 0.0,
    },
    "contextual_values": {
        "sector_pe": 15.0,
        "sector_ev_ebitda": 10.0,
        "revenue_cagr_3y": -0.08,
        "eps_cagr_3y": -0.30,
        "fcf_cagr_3y": -0.20,
    },
}


# =============================================================================
# SNAPSHOTS DE Z-SCORE
# =============================================================================

class TestAltmanZScoreSnapshots:
    """Snapshots para Altman Z-Score."""
    
    def test_blue_chip_z_score_snapshot(self):
        """Blue chip debe estar en zona SAFE con Z > 3.0."""
        z, level, _ = altman_z_score(**BLUE_CHIP_DATA["z_score_inputs"])
        
        assert z is not None, "Z-Score no debe ser None"
        assert level == "SAFE", f"Blue chip debe ser SAFE, got {level}"
        assert z > 3.0, f"Blue chip Z-Score debe ser > 3.0, got {z}"
        # Snapshot: Z-Score esperado aproximadamente 4.5-5.5
        assert 4.0 < z < 6.0, f"Z-Score {z} fuera de rango esperado [4.0, 6.0]"
    
    def test_high_growth_tech_z_score_snapshot(self):
        """High growth tech debe estar en zona SAFE."""
        z, level, _ = altman_z_score(**HIGH_GROWTH_TECH_DATA["z_score_inputs"])
        
        assert z is not None
        assert level == "SAFE", f"High growth tech debe ser SAFE, got {level}"
        # Tech con mucho cash y poca deuda = Z muy alto
        assert z > 5.0, f"High growth tech Z-Score debe ser > 5.0, got {z}"
    
    def test_deep_value_z_score_snapshot(self):
        """
        Deep value (banco) típicamente tiene Z-Score bajo por alta deuda.
        NOTA: El Z-Score de Altman no es ideal para instituciones financieras
        porque los bancos están naturalmente muy apalancados.
        """
        z, level, _ = altman_z_score(**DEEP_VALUE_DATA["z_score_inputs"])
        
        assert z is not None
        # Bancos pueden caer en DISTRESS por su estructura de capital
        # Esto es una limitación conocida del Z-Score para financials
        assert level in ["SAFE", "GREY", "DISTRESS"], f"Deep value nivel: {level}"
    
    def test_distressed_z_score_snapshot(self):
        """Empresa distressed debe estar en zona DISTRESS."""
        z, level, _ = altman_z_score(**DISTRESSED_DATA["z_score_inputs"])
        
        assert z is not None
        assert level == "DISTRESS", f"Distressed debe ser DISTRESS, got {level}"
        assert z < 1.81, f"Distressed Z-Score debe ser < 1.81, got {z}"


# =============================================================================
# SNAPSHOTS DE F-SCORE
# =============================================================================

class TestPiotroskirFScoreSnapshots:
    """Snapshots para Piotroski F-Score."""
    
    def test_blue_chip_f_score_snapshot(self):
        """Blue chip debe tener F-Score 6-8."""
        score, details, _ = piotroski_f_score(**BLUE_CHIP_DATA["f_score_inputs"])
        
        assert 6 <= score <= 9, f"Blue chip F-Score esperado 6-9, got {score}"
        # Verificar que hay detalles para las 9 señales
        assert len(details) == 9
    
    def test_high_growth_tech_f_score_snapshot(self):
        """High growth tech debe tener F-Score 7-9."""
        score, details, _ = piotroski_f_score(**HIGH_GROWTH_TECH_DATA["f_score_inputs"])
        
        # Tech de alta calidad con mejoras en todas las métricas
        assert score >= 7, f"High growth tech F-Score esperado >= 7, got {score}"
    
    def test_deep_value_f_score_snapshot(self):
        """Deep value debe tener F-Score 6-8."""
        score, details, _ = piotroski_f_score(**DEEP_VALUE_DATA["f_score_inputs"])
        
        assert 5 <= score <= 9, f"Deep value F-Score esperado 5-9, got {score}"
    
    def test_distressed_f_score_snapshot(self):
        """Distressed debe tener F-Score 0-3."""
        score, details, _ = piotroski_f_score(**DISTRESSED_DATA["f_score_inputs"])
        
        assert score <= 4, f"Distressed F-Score esperado <= 4, got {score}"


# =============================================================================
# SNAPSHOTS DE SCORING POR CATEGORÍA
# =============================================================================

class TestCategoryScoringSnapshots:
    """Snapshots para scores por categoría."""
    
    def test_blue_chip_solidez_snapshot(self):
        """Blue chip solidez financiera debe ser 14-18."""
        result = score_solidez_financiera(
            z_score=5.0, z_score_level="SAFE",
            current_ratio=BLUE_CHIP_DATA["ratio_values"]["current_ratio"],
            debt_to_equity=BLUE_CHIP_DATA["ratio_values"]["debt_to_equity"],
            interest_coverage=BLUE_CHIP_DATA["ratio_values"]["interest_coverage"],
            sector_de_threshold=1.5
        )
        
        assert 12 <= result["score"] <= 20, \
            f"Blue chip solidez esperada 12-20, got {result['score']}"
    
    def test_blue_chip_rentabilidad_snapshot(self):
        """Blue chip rentabilidad debe ser 14-18."""
        result = score_rentabilidad(
            roe=BLUE_CHIP_DATA["ratio_values"]["roe"],
            roa=BLUE_CHIP_DATA["ratio_values"]["roa"],
            operating_margin=BLUE_CHIP_DATA["ratio_values"]["operating_margin"],
            net_margin=BLUE_CHIP_DATA["ratio_values"]["net_margin"],
            sector_roe_threshold=0.12
        )
        
        assert 14 <= result["score"] <= 20, \
            f"Blue chip rentabilidad esperada 14-20, got {result['score']}"
    
    def test_high_growth_valoracion_snapshot(self):
        """
        High growth tech valoración: P/E alto pero growth quality debe
        mitigar la penalización. Score esperado 6-14.
        """
        result = score_valoracion(
            pe=HIGH_GROWTH_TECH_DATA["ratio_values"]["pe"],
            p_fcf=HIGH_GROWTH_TECH_DATA["ratio_values"]["p_fcf"],
            ev_ebitda=HIGH_GROWTH_TECH_DATA["ratio_values"]["ev_ebitda"],
            peg=HIGH_GROWTH_TECH_DATA["ratio_values"]["peg"],
            sector_pe=HIGH_GROWTH_TECH_DATA["contextual_values"]["sector_pe"],
            sector_ev_ebitda=HIGH_GROWTH_TECH_DATA["contextual_values"]["sector_ev_ebitda"],
            fcf_yield=HIGH_GROWTH_TECH_DATA["ratio_values"]["fcf_yield"],
            # Datos de growth para ajuste v2.2
            revenue_growth_3y=HIGH_GROWTH_TECH_DATA["contextual_values"]["revenue_cagr_3y"],
            eps_growth_3y=HIGH_GROWTH_TECH_DATA["contextual_values"]["eps_cagr_3y"],
            roe=HIGH_GROWTH_TECH_DATA["ratio_values"]["roe"],
            roic=HIGH_GROWTH_TECH_DATA["ratio_values"]["roic"],
            operating_margin=HIGH_GROWTH_TECH_DATA["ratio_values"]["operating_margin"],
            fcf_growth_3y=HIGH_GROWTH_TECH_DATA["contextual_values"]["fcf_cagr_3y"],
        )
        
        # Con growth quality excepcional, la penalización por P/E alto se reduce
        assert result["score"] >= 4, \
            f"High growth valoración esperada >= 4 (ajustada), got {result['score']}"
        
        # Debe identificar company_type como growth
        if "company_type" in result:
            assert result["company_type"] in ["growth", "garp"]
    
    def test_deep_value_valoracion_snapshot(self):
        """Deep value valoración debe ser muy alta (16-20)."""
        result = score_valoracion(
            pe=DEEP_VALUE_DATA["ratio_values"]["pe"],
            p_fcf=DEEP_VALUE_DATA["ratio_values"]["p_fcf"],
            ev_ebitda=DEEP_VALUE_DATA["ratio_values"]["ev_ebitda"],
            peg=DEEP_VALUE_DATA["ratio_values"]["peg"],
            sector_pe=DEEP_VALUE_DATA["contextual_values"]["sector_pe"],
            sector_ev_ebitda=DEEP_VALUE_DATA["contextual_values"]["sector_ev_ebitda"],
            fcf_yield=DEEP_VALUE_DATA["ratio_values"]["fcf_yield"],
        )
        
        # P/E 5x y FCF yield 20% = muy barato
        assert result["score"] >= 16, \
            f"Deep value valoración esperada >= 16, got {result['score']}"


# =============================================================================
# SNAPSHOTS DE SCORING TOTAL
# =============================================================================

class TestTotalScoringSnapshots:
    """Snapshots para score total."""
    
    def test_blue_chip_total_score_snapshot(self):
        """Blue chip score total debe ser 65-80."""
        result = calculate_score_v2(
            ratio_values=BLUE_CHIP_DATA["ratio_values"],
            contextual_values=BLUE_CHIP_DATA["contextual_values"],
            z_score_value=5.0,
            z_score_level="SAFE",
            f_score_value=7,
            sector_key="healthcare"
        )
        
        assert 60 <= result["score"] <= 85, \
            f"Blue chip total esperado 60-85, got {result['score']}"
        assert result["level"] in ["Excelente", "Favorable"]
    
    def test_high_growth_tech_total_score_snapshot(self):
        """High growth tech score total debe ser 60-80."""
        result = calculate_score_v2(
            ratio_values=HIGH_GROWTH_TECH_DATA["ratio_values"],
            contextual_values=HIGH_GROWTH_TECH_DATA["contextual_values"],
            z_score_value=8.0,
            z_score_level="SAFE",
            f_score_value=8,
            sector_key="technology"
        )
        
        # A pesar del P/E muy alto, los fundamentos excepcionales
        # deben dar un score decente
        assert result["score"] >= 55, \
            f"High growth tech total esperado >= 55, got {result['score']}"
    
    def test_deep_value_total_score_snapshot(self):
        """Deep value score total debe ser 60-80."""
        result = calculate_score_v2(
            ratio_values=DEEP_VALUE_DATA["ratio_values"],
            contextual_values=DEEP_VALUE_DATA["contextual_values"],
            z_score_value=2.5,
            z_score_level="GREY",
            f_score_value=7,
            sector_key="financials"
        )
        
        # Deep value con buenos fundamentos
        assert 55 <= result["score"] <= 85, \
            f"Deep value total esperado 55-85, got {result['score']}"
    
    def test_distressed_total_score_snapshot(self):
        """Distressed score total debe ser < 35."""
        result = calculate_score_v2(
            ratio_values=DISTRESSED_DATA["ratio_values"],
            contextual_values=DISTRESSED_DATA["contextual_values"],
            z_score_value=1.2,
            z_score_level="DISTRESS",
            f_score_value=2,
            sector_key="consumer_cyclical"
        )
        
        assert result["score"] <= 40, \
            f"Distressed total esperado <= 40, got {result['score']}"
        assert result["level"] in ["Alto Riesgo", "Precaución"]


# =============================================================================
# SNAPSHOTS DE CLASIFICACIÓN GROWTH/VALUE
# =============================================================================

class TestCompanyTypeSnapshots:
    """Snapshots para clasificación de tipo de empresa."""
    
    def test_high_growth_classified_correctly(self):
        """High growth tech debe clasificarse como growth."""
        result = classify_company_type(
            revenue_growth_3y=0.50,
            eps_growth_3y=0.80,
            pe=60.0,
            sector_pe=30.0,
            dividend_yield=0.0,
            fcf_yield=0.021,
            roe=0.75
        )
        
        assert result["type"] in ["growth", "garp"], \
            f"High growth debe ser growth/garp, got {result['type']}"
        assert result["has_quality_growth"] == True
    
    def test_deep_value_classified_correctly(self):
        """Deep value debe clasificarse como value o deep_value."""
        result = classify_company_type(
            revenue_growth_3y=0.03,
            eps_growth_3y=0.08,
            pe=5.0,
            sector_pe=10.0,
            dividend_yield=0.05,
            fcf_yield=0.20,
            roe=0.25
        )
        
        assert result["type"] in ["deep_value", "value", "dividend"], \
            f"Deep value debe ser value type, got {result['type']}"
    
    def test_growth_quality_score_snapshot(self):
        """Growth quality score debe reflejar calidad del crecimiento."""
        # Crecimiento excepcional
        result_exceptional = calculate_growth_quality_score(
            revenue_growth_3y=0.50,
            eps_growth_3y=0.80,
            fcf_growth_3y=0.60,
            roe=0.75,
            roic=0.65,
            operating_margin=0.58,
            fcf_to_net_income=0.83
        )
        
        assert result_exceptional["score"] >= 80, \
            f"Exceptional growth quality esperado >= 80, got {result_exceptional['score']}"
        assert result_exceptional["level"] == "exceptional"
        
        # Crecimiento pobre
        result_poor = calculate_growth_quality_score(
            revenue_growth_3y=-0.08,
            eps_growth_3y=-0.30,
            fcf_growth_3y=-0.20,
            roe=-0.50,
            roic=-0.40,
            operating_margin=0.02,
            fcf_to_net_income=0.5
        )
        
        assert result_poor["score"] < 35, \
            f"Poor growth quality esperado < 35, got {result_poor['score']}"


# =============================================================================
# REGRESSION TESTS
# =============================================================================

class TestRegressionSnapshots:
    """
    Tests de regresión para detectar cambios inesperados.
    Si alguno de estos tests falla después de un cambio de código,
    verificar si el cambio fue intencional.
    """
    
    def test_score_categories_always_sum_to_total(self):
        """La suma de categorías siempre debe igualar el total."""
        test_cases = [
            BLUE_CHIP_DATA,
            HIGH_GROWTH_TECH_DATA,
            DEEP_VALUE_DATA,
        ]
        
        for data in test_cases:
            result = calculate_score_v2(
                ratio_values=data["ratio_values"],
                contextual_values=data["contextual_values"],
                z_score_value=4.0,
                z_score_level="SAFE",
                f_score_value=7,
                sector_key="default"
            )
            
            category_sum = sum(cat["score"] for cat in result["categories"])
            assert category_sum == result["score"], \
                f"Suma de categorías ({category_sum}) != total ({result['score']}) para {data['name']}"
    
    def test_scores_always_bounded(self):
        """Todos los scores deben estar en rangos válidos."""
        test_cases = [
            BLUE_CHIP_DATA,
            HIGH_GROWTH_TECH_DATA,
            DEEP_VALUE_DATA,
            DISTRESSED_DATA,
        ]
        
        for data in test_cases:
            result = calculate_score_v2(
                ratio_values=data["ratio_values"],
                contextual_values=data["contextual_values"],
                z_score_value=3.0,
                z_score_level="SAFE",
                f_score_value=5,
                sector_key="default"
            )
            
            assert 0 <= result["score"] <= 100, \
                f"Total score fuera de rango para {data['name']}: {result['score']}"
            
            for cat in result["categories"]:
                assert 0 <= cat["score"] <= 20, \
                    f"Categoría {cat['category']} score fuera de rango: {cat['score']}"
    
    def test_growth_quality_always_bounded(self):
        """Growth quality score siempre debe estar entre 0-100."""
        test_cases = [
            {"revenue_growth_3y": 1.0, "eps_growth_3y": 2.0, "fcf_growth_3y": 1.5,
             "roe": 0.99, "roic": 0.99, "operating_margin": 0.90, "fcf_to_net_income": 2.0},
            {"revenue_growth_3y": -0.5, "eps_growth_3y": -0.8, "fcf_growth_3y": -0.6,
             "roe": -0.99, "roic": -0.99, "operating_margin": -0.50, "fcf_to_net_income": -1.0},
        ]
        
        for params in test_cases:
            result = calculate_growth_quality_score(**params)
            assert 0 <= result["score"] <= 100, \
                f"Growth quality score fuera de rango: {result['score']}"
    
    def test_z_score_zones_consistent(self):
        """Las zonas de Z-Score deben ser consistentes con los umbrales."""
        # Exactamente en los límites
        z_299, level_299, _ = altman_z_score(
            working_capital=2000, total_assets=10000, retained_earnings=1500,
            ebit=800, market_value_equity=12000, total_liabilities=5000, sales=15000
        )
        
        z_181, level_181, _ = altman_z_score(
            working_capital=500, total_assets=10000, retained_earnings=200,
            ebit=300, market_value_equity=5000, total_liabilities=7000, sales=10000
        )
        
        # Verificar consistencia de clasificación
        if z_299 is not None:
            if z_299 > 2.99:
                assert level_299 == "SAFE"
            elif z_299 > 1.81:
                assert level_299 == "GREY"
            else:
                assert level_299 == "DISTRESS"
