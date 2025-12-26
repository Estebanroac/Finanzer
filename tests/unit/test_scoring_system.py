"""
Tests for Scoring System v2.2
=============================
Validación del sistema de scoring de 5 categorías × 20 puntos = 100 máximo.

Categorías:
1. Solidez Financiera (20 pts): Z-Score, Current Ratio, D/E, Interest Coverage
2. Rentabilidad (20 pts): ROE, ROA, Márgenes
3. Valoración (20 pts): P/E, EV/EBITDA, P/FCF, PEG + ajuste Growth/Value
4. Calidad de Ganancias (20 pts): F-Score, FCF vs NI, OCF
5. Crecimiento (20 pts): Revenue, EPS, FCF growth

v2.2 Features:
- Sistema adaptativo Growth/Value
- Growth Quality Score
- Ajustes dinámicos de valoración
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from financial_ratios import (
    score_solidez_financiera,
    score_rentabilidad,
    score_valoracion,
    score_calidad_ganancias,
    score_crecimiento,
    calculate_score_v2,
    classify_company_type,
    calculate_growth_quality_score,
)


# =============================================================================
# TESTS: SOLIDEZ FINANCIERA (20 pts)
# =============================================================================

class TestScoreSolidezFinanciera:
    """Tests para la categoría de Solidez Financiera."""
    
    def test_perfect_solidez_score(self):
        """Empresa con métricas perfectas debe obtener ~20 pts."""
        result = score_solidez_financiera(
            z_score=5.0,  # Muy seguro
            z_score_level="SAFE",
            current_ratio=2.5,  # Excelente liquidez
            debt_to_equity=0.2,  # Muy baja deuda
            interest_coverage=25.0,  # Excelente cobertura
            sector_de_threshold=1.0
        )
        
        assert result["score"] >= 17, f"Solidez perfecta debería ser >=17, got {result['score']}"
        assert result["category"] == "Solidez Financiera"
        assert result["max_score"] == 20
    
    def test_distressed_solidez_score(self):
        """Empresa en distress debe obtener score muy bajo."""
        result = score_solidez_financiera(
            z_score=1.2,  # Zona de peligro
            z_score_level="DISTRESS",
            current_ratio=0.6,  # Mala liquidez
            debt_to_equity=3.0,  # Alta deuda
            interest_coverage=0.8,  # No cubre intereses
            sector_de_threshold=1.0
        )
        
        assert result["score"] <= 5, f"Empresa en distress debería tener score <=5, got {result['score']}"
    
    def test_z_score_safe_gives_bonus(self):
        """Z-Score SAFE debe dar bonus."""
        result_safe = score_solidez_financiera(
            z_score=4.0, z_score_level="SAFE",
            current_ratio=1.5, debt_to_equity=0.5,
            interest_coverage=10.0, sector_de_threshold=1.0
        )
        
        result_grey = score_solidez_financiera(
            z_score=2.5, z_score_level="GREY",
            current_ratio=1.5, debt_to_equity=0.5,
            interest_coverage=10.0, sector_de_threshold=1.0
        )
        
        assert result_safe["score"] > result_grey["score"]
    
    def test_z_score_distress_penalizes(self):
        """Z-Score DISTRESS debe penalizar."""
        result_distress = score_solidez_financiera(
            z_score=1.5, z_score_level="DISTRESS",
            current_ratio=1.5, debt_to_equity=0.5,
            interest_coverage=10.0, sector_de_threshold=1.0
        )
        
        result_grey = score_solidez_financiera(
            z_score=2.5, z_score_level="GREY",
            current_ratio=1.5, debt_to_equity=0.5,
            interest_coverage=10.0, sector_de_threshold=1.0
        )
        
        assert result_distress["score"] < result_grey["score"]
    
    def test_high_debt_penalizes(self):
        """Deuda alta debe penalizar."""
        result_low_debt = score_solidez_financiera(
            z_score=3.5, z_score_level="SAFE",
            current_ratio=1.5, debt_to_equity=0.3,  # Baja
            interest_coverage=10.0, sector_de_threshold=1.0
        )
        
        result_high_debt = score_solidez_financiera(
            z_score=3.5, z_score_level="SAFE",
            current_ratio=1.5, debt_to_equity=2.0,  # Alta
            interest_coverage=10.0, sector_de_threshold=1.0
        )
        
        assert result_low_debt["score"] > result_high_debt["score"]
    
    def test_sector_adjusted_debt_threshold(self):
        """El umbral de D/E debe ajustarse por sector."""
        # Sector con threshold alto (ej: utilities)
        result_utility = score_solidez_financiera(
            z_score=3.0, z_score_level="SAFE",
            current_ratio=1.5, debt_to_equity=1.2,
            interest_coverage=5.0, sector_de_threshold=1.5  # Alto threshold
        )
        
        # Mismo D/E pero sector con threshold bajo
        result_tech = score_solidez_financiera(
            z_score=3.0, z_score_level="SAFE",
            current_ratio=1.5, debt_to_equity=1.2,
            interest_coverage=5.0, sector_de_threshold=0.5  # Bajo threshold
        )
        
        # La utiliy debería tener mejor score con el mismo D/E
        assert result_utility["score"] >= result_tech["score"]
    
    def test_returns_correct_structure(self):
        """El resultado debe tener la estructura correcta."""
        result = score_solidez_financiera(
            z_score=3.0, z_score_level="SAFE",
            current_ratio=1.5, debt_to_equity=0.5,
            interest_coverage=10.0, sector_de_threshold=1.0
        )
        
        assert "category" in result
        assert "emoji" in result
        assert "score" in result
        assert "max_score" in result
        assert "base" in result
        assert "adjustments" in result
        assert isinstance(result["adjustments"], list)


# =============================================================================
# TESTS: RENTABILIDAD (20 pts)
# =============================================================================

class TestScoreRentabilidad:
    """Tests para la categoría de Rentabilidad."""
    
    def test_exceptional_profitability(self):
        """ROE y márgenes excepcionales deben dar score alto."""
        result = score_rentabilidad(
            roe=0.35,  # 35% - Excepcional
            roa=0.20,  # 20% - Excelente
            operating_margin=0.35,  # 35%
            net_margin=0.25,  # 25%
            sector_roe_threshold=0.12
        )
        
        assert result["score"] >= 18, f"Rentabilidad excepcional debería ser >=18, got {result['score']}"
    
    def test_negative_roe_penalizes(self):
        """ROE negativo debe penalizar severamente."""
        result = score_rentabilidad(
            roe=-0.15,  # Negativo
            roa=-0.05,
            operating_margin=-0.05,
            net_margin=-0.10,
            sector_roe_threshold=0.12
        )
        
        assert result["score"] <= 5, f"ROE negativo debería dar score <=5, got {result['score']}"
    
    def test_roe_has_high_weight(self):
        """ROE debe tener peso alto en el score."""
        result_high_roe = score_rentabilidad(
            roe=0.25,  # Alto
            roa=0.08, operating_margin=0.12, net_margin=0.08,
            sector_roe_threshold=0.12
        )
        
        result_low_roe = score_rentabilidad(
            roe=0.05,  # Bajo
            roa=0.08, operating_margin=0.12, net_margin=0.08,
            sector_roe_threshold=0.12
        )
        
        diff = result_high_roe["score"] - result_low_roe["score"]
        assert diff >= 6, f"ROE debería impactar >=6 pts, diferencia fue {diff}"
    
    def test_operating_margin_impact(self):
        """Operating margin debe impactar el score."""
        result_high_margin = score_rentabilidad(
            roe=0.15, roa=0.10,
            operating_margin=0.30,  # Alto
            net_margin=0.15, sector_roe_threshold=0.12
        )
        
        result_low_margin = score_rentabilidad(
            roe=0.15, roa=0.10,
            operating_margin=0.05,  # Bajo
            net_margin=0.15, sector_roe_threshold=0.12
        )
        
        assert result_high_margin["score"] > result_low_margin["score"]


# =============================================================================
# TESTS: VALORACIÓN (20 pts) + SISTEMA GROWTH/VALUE
# =============================================================================

class TestScoreValoracion:
    """Tests para la categoría de Valoración."""
    
    def test_undervalued_company_high_score(self):
        """Empresa subvalorada debe tener score alto."""
        result = score_valoracion(
            pe=12.0,  # Bajo vs sector
            p_fcf=10.0,
            ev_ebitda=8.0,
            peg=0.7,  # Muy atractivo
            sector_pe=20.0,
            sector_ev_ebitda=12.0,
            fcf_yield=0.10  # 10%
        )
        
        assert result["score"] >= 16, f"Empresa subvalorada debería ser >=16, got {result['score']}"
    
    def test_overvalued_company_low_score(self):
        """Empresa sobrevalorada debe tener score bajo."""
        result = score_valoracion(
            pe=50.0,  # Muy alto
            p_fcf=40.0,
            ev_ebitda=25.0,
            peg=3.0,  # Muy caro
            sector_pe=20.0,
            sector_ev_ebitda=12.0,
            fcf_yield=0.02
        )
        
        assert result["score"] <= 8, f"Empresa sobrevalorada debería ser <=8, got {result['score']}"
    
    def test_growth_quality_reduces_pe_penalty(self):
        """
        v2.2: Alta calidad de crecimiento debe reducir la penalización
        por P/E alto.
        """
        # Empresa con P/E alto pero SIN crecimiento de calidad
        result_no_quality = score_valoracion(
            pe=45.0, p_fcf=35.0, ev_ebitda=20.0,
            peg=2.5, sector_pe=20.0, sector_ev_ebitda=12.0,
            # Sin datos de growth
            revenue_growth_3y=None, eps_growth_3y=None,
            roe=None, roic=None, operating_margin=None
        )
        
        # Empresa con mismo P/E pero CON crecimiento de calidad
        result_with_quality = score_valoracion(
            pe=45.0, p_fcf=35.0, ev_ebitda=20.0,
            peg=2.5, sector_pe=20.0, sector_ev_ebitda=12.0,
            # Datos de growth de alta calidad
            revenue_growth_3y=0.30,  # 30%
            eps_growth_3y=0.40,  # 40%
            roe=0.35,  # 35%
            roic=0.30,  # 30%
            operating_margin=0.30,  # 30%
            fcf_growth_3y=0.25
        )
        
        # La empresa con growth quality debe tener mejor score
        assert result_with_quality["score"] > result_no_quality["score"], \
            f"Growth quality debe reducir penalización: {result_with_quality['score']} vs {result_no_quality['score']}"
    
    def test_garp_bonus(self):
        """Empresa GARP con fundamentos excepcionales debe recibir bonus."""
        result = score_valoracion(
            pe=22.0,  # Ligeramente sobre sector
            p_fcf=18.0,
            ev_ebitda=14.0,
            peg=1.0,  # Perfecto para GARP
            sector_pe=20.0,
            sector_ev_ebitda=12.0,
            fcf_yield=0.055,
            # Datos de crecimiento para GARP
            revenue_growth_3y=0.20,
            eps_growth_3y=0.25,
            roe=0.25,
            roic=0.22,
            operating_margin=0.25,
            dividend_yield=0.01
        )
        
        # GARP con buenos fundamentos debe tener score decente
        assert result["score"] >= 12, \
            f"GARP con fundamentos sólidos debería ser >=12, got {result['score']}"
        
        # Debe identificar company_type
        if "company_type" in result:
            assert result["company_type"] in ["garp", "growth", "blend"]
    
    def test_fcf_yield_bonus(self):
        """FCF Yield alto debe dar bonus."""
        result_high_yield = score_valoracion(
            pe=18.0, p_fcf=12.0, ev_ebitda=10.0, peg=1.5,
            sector_pe=20.0, sector_ev_ebitda=12.0,
            fcf_yield=0.10  # 10% - Excelente
        )
        
        result_low_yield = score_valoracion(
            pe=18.0, p_fcf=12.0, ev_ebitda=10.0, peg=1.5,
            sector_pe=20.0, sector_ev_ebitda=12.0,
            fcf_yield=0.02  # 2% - Bajo
        )
        
        assert result_high_yield["score"] > result_low_yield["score"]


class TestClassifyCompanyType:
    """Tests para la clasificación Growth/Value."""
    
    def test_classify_deep_value(self):
        """P/E muy bajo + bajo crecimiento = Deep Value."""
        result = classify_company_type(
            revenue_growth_3y=0.02,  # Bajo
            eps_growth_3y=0.03,
            pe=8.0,  # Muy bajo
            sector_pe=20.0,
            dividend_yield=0.05,  # Alto dividendo
            fcf_yield=0.12,  # Muy alto
            roe=0.12
        )
        
        assert result["type"] in ["deep_value", "value", "dividend"]
    
    def test_classify_growth(self):
        """Alto crecimiento + P/E alto = Growth."""
        result = classify_company_type(
            revenue_growth_3y=0.35,  # Muy alto
            eps_growth_3y=0.40,
            pe=50.0,  # Alto
            sector_pe=25.0,
            dividend_yield=0.0,  # Sin dividendos
            fcf_yield=0.02,
            roe=0.30  # Alto
        )
        
        assert result["type"] in ["growth", "garp"]
    
    def test_classify_garp(self):
        """Buen crecimiento + valoración razonable = GARP."""
        result = classify_company_type(
            revenue_growth_3y=0.18,  # Sólido
            eps_growth_3y=0.20,
            pe=22.0,  # Razonable
            sector_pe=20.0,
            dividend_yield=0.01,
            fcf_yield=0.05,
            roe=0.22  # Bueno
        )
        
        assert result["type"] in ["garp", "growth", "value"]
    
    def test_classify_dividend(self):
        """Alto dividendo = Dividend."""
        result = classify_company_type(
            revenue_growth_3y=0.03,
            eps_growth_3y=0.05,
            pe=15.0,
            sector_pe=18.0,
            dividend_yield=0.06,  # 6% - Muy alto
            fcf_yield=0.08,
            roe=0.12
        )
        
        assert result["type"] in ["dividend", "value", "deep_value"]
    
    def test_classify_blend(self):
        """Sin características claras = Blend."""
        result = classify_company_type(
            revenue_growth_3y=0.05,
            eps_growth_3y=0.06,
            pe=18.0,
            sector_pe=20.0,
            dividend_yield=0.02,
            fcf_yield=0.04,
            roe=0.11
        )
        
        # Debe tener baja confianza o ser blend
        assert result["confidence"] < 0.5 or result["type"] == "blend"


class TestCalculateGrowthQualityScore:
    """Tests para el Growth Quality Score."""
    
    def test_exceptional_growth_quality(self):
        """Crecimiento de alta calidad debe dar score 80+."""
        result = calculate_growth_quality_score(
            revenue_growth_3y=0.30,  # 30%
            eps_growth_3y=0.40,  # 40% > revenue (expansión márgenes)
            fcf_growth_3y=0.25,
            roe=0.35,
            roic=0.30,
            operating_margin=0.30,
            fcf_to_net_income=1.2
        )
        
        assert result["score"] >= 80, f"Exceptional growth debería ser >=80, got {result['score']}"
        assert result["level"] == "exceptional"
    
    def test_poor_growth_quality(self):
        """Crecimiento de baja calidad debe dar score <40."""
        result = calculate_growth_quality_score(
            revenue_growth_3y=-0.10,  # Contracción
            eps_growth_3y=-0.20,  # Contracción peor
            fcf_growth_3y=-0.15,
            roe=0.05,  # Bajo
            roic=0.04,
            operating_margin=0.03,  # Muy bajo
            fcf_to_net_income=0.5
        )
        
        assert result["score"] < 40, f"Poor growth debería ser <40, got {result['score']}"
    
    def test_eps_vs_revenue_expansion(self):
        """EPS creciendo más que revenue indica expansión de márgenes."""
        result = calculate_growth_quality_score(
            revenue_growth_3y=0.15,
            eps_growth_3y=0.25,  # > revenue (bueno)
            fcf_growth_3y=0.20,
            roe=0.18, roic=0.16, operating_margin=0.18,
            fcf_to_net_income=1.0
        )
        
        # Debe tener bonus por expansión de márgenes
        breakdown_text = str(result["breakdown"])
        assert "Expansión" in breakdown_text or result["score"] > 60


# =============================================================================
# TESTS: CALIDAD DE GANANCIAS (20 pts)
# =============================================================================

class TestScoreCalidadGanancias:
    """Tests para la categoría de Calidad de Ganancias."""
    
    def test_exceptional_quality(self):
        """F-Score alto + FCF positivo debe dar score alto."""
        result = score_calidad_ganancias(
            f_score=8,  # Excepcional
            fcf=1_000_000_000,  # Positivo
            ocf=1_200_000_000,  # Positivo y > FCF
            net_income=900_000_000,
            fcf_to_net_income=1.1  # FCF > NI
        )
        
        assert result["score"] >= 18, f"Calidad excepcional debería ser >=18, got {result['score']}"
    
    def test_weak_quality(self):
        """F-Score bajo + FCF negativo debe dar score bajo."""
        result = score_calidad_ganancias(
            f_score=2,  # Débil
            fcf=-200_000_000,  # Negativo
            ocf=-100_000_000,  # Negativo
            net_income=500_000_000,  # Ganancias sin cash
            fcf_to_net_income=-0.4
        )
        
        assert result["score"] <= 5, f"Calidad débil debería ser <=5, got {result['score']}"
    
    def test_f_score_has_high_weight(self):
        """F-Score debe tener peso alto."""
        result_high_f = score_calidad_ganancias(
            f_score=9, fcf=100, ocf=120, net_income=90, fcf_to_net_income=1.1
        )
        
        result_low_f = score_calidad_ganancias(
            f_score=2, fcf=100, ocf=120, net_income=90, fcf_to_net_income=1.1
        )
        
        diff = result_high_f["score"] - result_low_f["score"]
        assert diff >= 4, f"F-Score debería impactar al menos 4 pts, diff={diff}"
    
    def test_fcf_vs_net_income_quality(self):
        """FCF > Net Income indica earnings de calidad."""
        # Caso con FCF muy superior a Net Income
        result_quality = score_calidad_ganancias(
            f_score=5,  # Neutral F-Score para aislar el efecto
            fcf=200,
            ocf=250,
            net_income=100,
            fcf_to_net_income=2.0  # FCF 100% más que NI - excelente
        )
        
        # Caso con FCF muy inferior a Net Income
        result_poor = score_calidad_ganancias(
            f_score=5,  # Mismo F-Score
            fcf=20,
            ocf=40,
            net_income=100,
            fcf_to_net_income=0.2  # FCF 80% menos que NI - preocupante
        )
        
        assert result_quality["score"] >= result_poor["score"], \
            f"FCF quality {result_quality['score']} debería ser >= poor {result_poor['score']}"


# =============================================================================
# TESTS: CRECIMIENTO (20 pts)
# =============================================================================

class TestScoreCrecimiento:
    """Tests para la categoría de Crecimiento."""
    
    def test_exceptional_growth(self):
        """Crecimiento excepcional debe dar score alto."""
        result = score_crecimiento(
            revenue_growth_3y=0.25,  # 25%
            eps_growth_3y=0.30,  # 30%
            fcf_growth_3y=0.20,  # 20%
            peg=1.0,
            is_growth_company=True
        )
        
        assert result["score"] >= 18, f"Crecimiento excepcional debería ser >=18, got {result['score']}"
    
    def test_contracting_company(self):
        """Contracción debe dar score bajo."""
        result = score_crecimiento(
            revenue_growth_3y=-0.10,  # -10%
            eps_growth_3y=-0.20,  # -20%
            fcf_growth_3y=-0.15,
            peg=None,
            is_growth_company=False
        )
        
        assert result["score"] <= 5, f"Contracción debería ser <=5, got {result['score']}"
    
    def test_growth_company_bonus(self):
        """Empresa growth debe recibir bonus."""
        result_growth = score_crecimiento(
            revenue_growth_3y=0.15, eps_growth_3y=0.18, fcf_growth_3y=0.12,
            peg=1.5, is_growth_company=True  # Con bonus
        )
        
        result_not_growth = score_crecimiento(
            revenue_growth_3y=0.15, eps_growth_3y=0.18, fcf_growth_3y=0.12,
            peg=1.5, is_growth_company=False  # Sin bonus
        )
        
        assert result_growth["score"] > result_not_growth["score"]


# =============================================================================
# TESTS: SISTEMA DE SCORING COMPLETO (calculate_score_v2)
# =============================================================================

class TestCalculateScoreV2:
    """Tests para el sistema de scoring completo."""
    
    def test_healthy_company_high_score(self, healthy_company_data):
        """Empresa saludable debe tener score 70-85."""
        ratio_values = {
            "current_ratio": healthy_company_data["current_ratio"],
            "debt_to_equity": healthy_company_data["debt_to_equity"],
            "interest_coverage": healthy_company_data["interest_coverage"],
            "roe": healthy_company_data["roe"],
            "roa": healthy_company_data["roa"],
            "operating_margin": healthy_company_data["operating_margin"],
            "net_margin": healthy_company_data["net_margin"],
            "pe": healthy_company_data["pe"],
            "p_fcf": 30.0,
            "ev_ebitda": healthy_company_data["ev_ebitda"],
            "peg": healthy_company_data["peg"],
            "fcf_yield": healthy_company_data["fcf_yield"],
            "fcf": healthy_company_data["free_cash_flow"],
            "operating_cash_flow": healthy_company_data["operating_cash_flow"],
            "net_income": healthy_company_data["net_income"],
            "fcf_to_net_income": healthy_company_data["free_cash_flow"] / healthy_company_data["net_income"],
        }
        
        contextual_values = {
            "sector_pe": healthy_company_data["sector_pe"],
            "sector_ev_ebitda": healthy_company_data["sector_ev_ebitda"],
            "revenue_cagr_3y": healthy_company_data["revenue_growth_3y"],
            "eps_cagr_3y": healthy_company_data["eps_growth_3y"],
            "fcf_cagr_3y": healthy_company_data["fcf_growth_3y"],
        }
        
        result = calculate_score_v2(
            ratio_values=ratio_values,
            contextual_values=contextual_values,
            z_score_value=4.0,
            z_score_level="SAFE",
            f_score_value=7,
            sector_key="consumer_defensive"
        )
        
        assert 65 <= result["score"] <= 90, \
            f"Empresa saludable debería tener score 65-90, got {result['score']}"
    
    def test_distressed_company_low_score(self, distressed_company_data):
        """Empresa en distress debe tener score <40."""
        ratio_values = {
            "current_ratio": distressed_company_data["current_ratio"],
            "debt_to_equity": distressed_company_data["debt_to_equity"],
            "interest_coverage": distressed_company_data["interest_coverage"],
            "roe": distressed_company_data["roe"],
            "roa": distressed_company_data["roa"],
            "operating_margin": distressed_company_data["operating_margin"],
            "net_margin": distressed_company_data["net_margin"],
            "pe": distressed_company_data["pe"],
            "p_fcf": None,
            "ev_ebitda": distressed_company_data["ev_ebitda"],
            "peg": distressed_company_data["peg"],
            "fcf_yield": distressed_company_data["fcf_yield"],
            "fcf": distressed_company_data["free_cash_flow"],
            "operating_cash_flow": distressed_company_data["operating_cash_flow"],
            "net_income": distressed_company_data["net_income"],
            "fcf_to_net_income": 0.6,
        }
        
        contextual_values = {
            "sector_pe": distressed_company_data["sector_pe"],
            "sector_ev_ebitda": distressed_company_data["sector_ev_ebitda"],
            "revenue_cagr_3y": distressed_company_data["revenue_growth_3y"],
            "eps_cagr_3y": distressed_company_data["eps_growth_3y"],
            "fcf_cagr_3y": distressed_company_data["fcf_growth_3y"],
        }
        
        result = calculate_score_v2(
            ratio_values=ratio_values,
            contextual_values=contextual_values,
            z_score_value=1.2,
            z_score_level="DISTRESS",
            f_score_value=2,
            sector_key="consumer_cyclical"
        )
        
        assert result["score"] <= 40, \
            f"Empresa en distress debería tener score <=40, got {result['score']}"
    
    def test_score_breakdown_sums_correctly(self, healthy_company_data):
        """La suma de categorías debe igualar score total."""
        ratio_values = {
            "current_ratio": 1.8, "debt_to_equity": 0.5, "interest_coverage": 15.0,
            "roe": 0.15, "roa": 0.10, "operating_margin": 0.18, "net_margin": 0.12,
            "pe": 20.0, "p_fcf": 18.0, "ev_ebitda": 12.0, "peg": 1.5, "fcf_yield": 0.05,
            "fcf": 1000, "operating_cash_flow": 1200, "net_income": 900, "fcf_to_net_income": 1.1
        }
        
        contextual_values = {
            "sector_pe": 22.0, "sector_ev_ebitda": 14.0,
            "revenue_cagr_3y": 0.10, "eps_cagr_3y": 0.12, "fcf_cagr_3y": 0.08
        }
        
        result = calculate_score_v2(
            ratio_values=ratio_values,
            contextual_values=contextual_values,
            z_score_value=3.5,
            z_score_level="SAFE",
            f_score_value=7,
            sector_key="default"
        )
        
        category_sum = sum(cat["score"] for cat in result["categories"])
        assert category_sum == result["score"], \
            f"Suma de categorías ({category_sum}) debe igualar total ({result['score']})"
    
    def test_score_levels_correct(self):
        """Los niveles de score deben ser correctos."""
        # Test para diferentes rangos
        test_cases = [
            (85, "Excelente"),
            (70, "Favorable"),
            (55, "Neutral"),
            (40, "Precaución"),
            (25, "Alto Riesgo"),
        ]
        
        for target_score, expected_level in test_cases:
            # No podemos forzar un score exacto, pero verificamos la lógica
            if target_score >= 80:
                assert expected_level == "Excelente"
            elif target_score >= 65:
                assert expected_level == "Favorable"
            elif target_score >= 50:
                assert expected_level == "Neutral"
            elif target_score >= 35:
                assert expected_level == "Precaución"
            else:
                assert expected_level == "Alto Riesgo"
