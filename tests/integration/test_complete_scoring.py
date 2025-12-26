"""
Integration Tests: Complete Scoring Flow
========================================
Tests que verifican el flujo completo de análisis desde datos
hasta score final, asegurando que todos los componentes trabajan
juntos correctamente.

Estos tests usan datos mock para evitar llamadas a APIs externas
en el flujo de CI/CD.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from financial_ratios import (
    altman_z_score,
    piotroski_f_score,
    calculate_score_v2,
    calculate_all_ratios,
    graham_number,
    dcf_dynamic,
)


class TestCompleteAnalysisFlow:
    """Tests del flujo completo de análisis."""
    
    def test_full_analysis_healthy_company(self, healthy_company_data):
        """
        Test del flujo completo para una empresa saludable:
        1. Calcular Z-Score
        2. Calcular F-Score
        3. Calcular Score total
        4. Verificar consistencia
        """
        data = healthy_company_data
        
        # 1. Z-Score
        z_score, z_level, z_interp = altman_z_score(
            working_capital=data["working_capital"],
            total_assets=data["total_assets"],
            retained_earnings=data["retained_earnings"],
            ebit=data["ebit"],
            market_value_equity=data["market_cap"],
            total_liabilities=data["total_liabilities"],
            sales=data["revenue"]
        )
        
        assert z_score is not None
        assert z_score > 2.0, "Empresa saludable debe tener Z-Score > 2.0"
        
        # 2. F-Score
        f_score, f_details, f_interp = piotroski_f_score(
            net_income=data["net_income"],
            roa_current=data["roa"],
            roa_prior=data["roa_prior"],
            operating_cash_flow=data["operating_cash_flow"],
            long_term_debt_current=data["long_term_debt"],
            long_term_debt_prior=data["long_term_debt_prior"],
            current_ratio_current=data["current_ratio"],
            current_ratio_prior=data["current_ratio_prior"],
            shares_current=data["shares_current"],
            shares_prior=data["shares_prior"],
            gross_margin_current=data["gross_margin"],
            gross_margin_prior=data["gross_margin_prior"],
            asset_turnover_current=data["asset_turnover_current"],
            asset_turnover_prior=data["asset_turnover_prior"]
        )
        
        assert f_score >= 5, "Empresa saludable debe tener F-Score >= 5"
        
        # 3. Score total
        ratio_values = {
            "current_ratio": data["current_ratio"],
            "debt_to_equity": data["debt_to_equity"],
            "interest_coverage": data["interest_coverage"],
            "roe": data["roe"],
            "roa": data["roa"],
            "operating_margin": data["operating_margin"],
            "net_margin": data["net_margin"],
            "pe": data["pe"],
            "p_fcf": data["price"] * data["shares_outstanding"] / data["free_cash_flow"],
            "ev_ebitda": data["ev_ebitda"],
            "peg": data["peg"],
            "fcf_yield": data["fcf_yield"],
            "fcf": data["free_cash_flow"],
            "operating_cash_flow": data["operating_cash_flow"],
            "net_income": data["net_income"],
            "fcf_to_net_income": data["free_cash_flow"] / data["net_income"],
        }
        
        contextual_values = {
            "sector_pe": data["sector_pe"],
            "sector_ev_ebitda": data["sector_ev_ebitda"],
            "revenue_cagr_3y": data["revenue_growth_3y"],
            "eps_cagr_3y": data["eps_growth_3y"],
            "fcf_cagr_3y": data["fcf_growth_3y"],
        }
        
        result = calculate_score_v2(
            ratio_values=ratio_values,
            contextual_values=contextual_values,
            z_score_value=z_score,
            z_score_level=z_level,
            f_score_value=f_score,
            sector_key="consumer_defensive"
        )
        
        # 4. Verificaciones de consistencia
        assert result["score"] >= 60, \
            f"Empresa saludable debe tener score >= 60, got {result['score']}"
        
        # Verificar que todas las categorías tienen score
        assert len(result["categories"]) == 5
        for cat in result["categories"]:
            assert 0 <= cat["score"] <= 20
        
        # Verificar que el nivel es apropiado
        assert result["level"] in ["Excelente", "Favorable", "Neutral"]
    
    def test_full_analysis_distressed_company(self, distressed_company_data):
        """Test del flujo completo para empresa en distress."""
        data = distressed_company_data
        
        # 1. Z-Score (debe indicar distress)
        z_score, z_level, _ = altman_z_score(
            working_capital=data["working_capital"],
            total_assets=data["total_assets"],
            retained_earnings=data["retained_earnings"],
            ebit=data["ebit"],
            market_value_equity=data["market_cap"],
            total_liabilities=data["total_liabilities"],
            sales=data["revenue"]
        )
        
        assert z_level == "DISTRESS", "Empresa en problemas debe tener Z-Score DISTRESS"
        
        # 2. F-Score (debe ser bajo)
        f_score, _, _ = piotroski_f_score(
            net_income=data["net_income"],
            roa_current=data["roa"],
            roa_prior=data["roa_prior"],
            operating_cash_flow=data["operating_cash_flow"],
            long_term_debt_current=data["long_term_debt"],
            long_term_debt_prior=data["long_term_debt_prior"],
            current_ratio_current=data["current_ratio"],
            current_ratio_prior=data["current_ratio_prior"],
            shares_current=data["shares_current"],
            shares_prior=data["shares_prior"],
            gross_margin_current=data["gross_margin"],
            gross_margin_prior=data["gross_margin_prior"],
            asset_turnover_current=data["asset_turnover_current"],
            asset_turnover_prior=data["asset_turnover_prior"]
        )
        
        assert f_score <= 3, "Empresa en distress debe tener F-Score <= 3"
        
        # 3. Score total (debe ser bajo)
        ratio_values = {
            "current_ratio": data["current_ratio"],
            "debt_to_equity": data["debt_to_equity"],
            "interest_coverage": data["interest_coverage"],
            "roe": data["roe"],
            "roa": data["roa"],
            "operating_margin": data["operating_margin"],
            "net_margin": data["net_margin"],
            "pe": data["pe"],
            "p_fcf": None,  # FCF negativo
            "ev_ebitda": None,
            "peg": None,
            "fcf_yield": data["fcf_yield"],
            "fcf": data["free_cash_flow"],
            "operating_cash_flow": data["operating_cash_flow"],
            "net_income": data["net_income"],
            "fcf_to_net_income": 0.6,
        }
        
        contextual_values = {
            "sector_pe": data["sector_pe"],
            "sector_ev_ebitda": data["sector_ev_ebitda"],
            "revenue_cagr_3y": data["revenue_growth_3y"],
            "eps_cagr_3y": data["eps_growth_3y"],
            "fcf_cagr_3y": data["fcf_growth_3y"],
        }
        
        result = calculate_score_v2(
            ratio_values=ratio_values,
            contextual_values=contextual_values,
            z_score_value=z_score,
            z_score_level=z_level,
            f_score_value=f_score,
            sector_key="consumer_cyclical"
        )
        
        assert result["score"] <= 40, \
            f"Empresa en distress debe tener score <= 40, got {result['score']}"
        assert result["level"] in ["Precaución", "Alto Riesgo"]


class TestGrowthValueIntegration:
    """Tests de integración del sistema Growth/Value."""
    
    def test_growth_company_not_penalized_unfairly(self, growth_company_data):
        """
        Empresa growth de alta calidad no debe ser penalizada
        excesivamente por P/E alto.
        """
        data = growth_company_data
        
        ratio_values = {
            "current_ratio": data["current_ratio"],
            "debt_to_equity": data["debt_to_equity"],
            "interest_coverage": data["interest_coverage"],
            "roe": data["roe"],
            "roa": data["roa"],
            "operating_margin": data["operating_margin"],
            "net_margin": data["net_margin"],
            "pe": data["pe"],  # 55x - Alto
            "p_fcf": data["market_cap"] / data["free_cash_flow"],
            "ev_ebitda": data["ev_ebitda"],
            "peg": data["peg"],
            "fcf_yield": data["fcf_yield"],
            "fcf": data["free_cash_flow"],
            "operating_cash_flow": data["operating_cash_flow"],
            "net_income": data["net_income"],
            "fcf_to_net_income": data["free_cash_flow"] / data["net_income"],
            "roic": data.get("roic"),
        }
        
        contextual_values = {
            "sector_pe": data["sector_pe"],  # 28x
            "sector_ev_ebitda": data["sector_ev_ebitda"],
            "revenue_cagr_3y": data["revenue_growth_3y"],  # 35%
            "eps_cagr_3y": data["eps_growth_3y"],  # 50%
            "fcf_cagr_3y": data["fcf_growth_3y"],
        }
        
        result = calculate_score_v2(
            ratio_values=ratio_values,
            contextual_values=contextual_values,
            z_score_value=4.5,
            z_score_level="SAFE",
            f_score_value=7,
            sector_key="technology"
        )
        
        # A pesar del P/E alto (55x vs 28x sector), el score no debe ser terrible
        # porque la calidad del crecimiento lo justifica
        assert result["score"] >= 55, \
            f"Growth de calidad no debe ser penalizado excesivamente: {result['score']}"
        
        # Verificar que se detectó como growth o garp
        if "company_type" in result:
            assert result["company_type"] in ["growth", "garp", "blend"]
    
    def test_value_company_recognized(self, value_company_data):
        """Empresa value debe tener buen score en valoración."""
        data = value_company_data
        
        ratio_values = {
            "current_ratio": data["current_ratio"],
            "debt_to_equity": data["debt_to_equity"],
            "interest_coverage": data["interest_coverage"],
            "roe": data["roe"],
            "roa": data["roa"],
            "operating_margin": data["operating_margin"],
            "net_margin": data["net_margin"],
            "pe": data["pe"],  # 10.7x - Bajo
            "p_fcf": data["market_cap"] / data["free_cash_flow"],
            "ev_ebitda": data["ev_ebitda"],  # 8x - Bajo
            "peg": data["peg"],  # 0.9 - Atractivo
            "fcf_yield": data["fcf_yield"],  # 9.4% - Excelente
            "fcf": data["free_cash_flow"],
            "operating_cash_flow": data["operating_cash_flow"],
            "net_income": data["net_income"],
            "fcf_to_net_income": data["free_cash_flow"] / data["net_income"],
            "dividend_yield": data["dividend_yield"],
        }
        
        contextual_values = {
            "sector_pe": data["sector_pe"],
            "sector_ev_ebitda": data["sector_ev_ebitda"],
            "revenue_cagr_3y": data["revenue_growth_3y"],
            "eps_cagr_3y": data["eps_growth_3y"],
            "fcf_cagr_3y": data["fcf_growth_3y"],
        }
        
        result = calculate_score_v2(
            ratio_values=ratio_values,
            contextual_values=contextual_values,
            z_score_value=3.2,
            z_score_level="SAFE",
            f_score_value=7,
            sector_key="financials"
        )
        
        # Valoración debe ser alta (P/E bajo, FCF yield alto)
        valoracion_score = result["category_scores"]["valoracion"]
        assert valoracion_score >= 14, \
            f"Empresa value debe tener alta puntuación en valoración: {valoracion_score}"


class TestValuationIntegration:
    """Tests de integración para modelos de valuación."""
    
    def test_graham_number_consistency(self, healthy_company_data):
        """Graham Number debe ser consistente con datos."""
        data = healthy_company_data
        
        eps = data["net_income"] / data["shares_outstanding"]
        bvps = (data["total_assets"] - data["total_liabilities"]) / data["shares_outstanding"]
        
        graham = graham_number(eps, bvps)
        
        if graham is not None:
            # Graham Number debe ser positivo y razonable
            assert graham > 0
            # No debería ser absurdamente diferente del precio
            assert 0.2 * data["price"] < graham < 5 * data["price"]
    
    def test_dcf_consistency(self, healthy_company_data):
        """DCF debe producir valores consistentes."""
        data = healthy_company_data
        
        result = dcf_dynamic(
            fcf=data["free_cash_flow"],
            shares_outstanding=data["shares_outstanding"],
            beta=1.0,
            debt_to_equity=data["debt_to_equity"],
            revenue_growth_3y=data["revenue_growth_3y"],
            fcf_growth_3y=data["fcf_growth_3y"]
        )
        
        if result["fair_value"] is not None:
            # Fair value debe ser positivo
            assert result["fair_value"] > 0
            # WACC debe estar en rango razonable
            assert 0.05 <= result["wacc_used"] <= 0.20
            # Growth debe estar en rango razonable
            assert 0.0 <= result["growth_used"] <= 0.30


class TestScoreConsistency:
    """Tests de consistencia del sistema de scoring."""
    
    def test_score_is_deterministic(self, healthy_company_data):
        """El mismo input debe producir el mismo score."""
        data = healthy_company_data
        
        ratio_values = {
            "current_ratio": data["current_ratio"],
            "debt_to_equity": data["debt_to_equity"],
            "interest_coverage": data["interest_coverage"],
            "roe": data["roe"],
            "roa": data["roa"],
            "operating_margin": data["operating_margin"],
            "net_margin": data["net_margin"],
            "pe": data["pe"],
            "p_fcf": 30.0,
            "ev_ebitda": data["ev_ebitda"],
            "peg": data["peg"],
            "fcf_yield": data["fcf_yield"],
            "fcf": data["free_cash_flow"],
            "operating_cash_flow": data["operating_cash_flow"],
            "net_income": data["net_income"],
            "fcf_to_net_income": 1.0,
        }
        
        contextual_values = {
            "sector_pe": data["sector_pe"],
            "sector_ev_ebitda": data["sector_ev_ebitda"],
            "revenue_cagr_3y": data["revenue_growth_3y"],
            "eps_cagr_3y": data["eps_growth_3y"],
            "fcf_cagr_3y": data["fcf_growth_3y"],
        }
        
        # Calcular dos veces
        result1 = calculate_score_v2(
            ratio_values=ratio_values,
            contextual_values=contextual_values,
            z_score_value=4.0,
            z_score_level="SAFE",
            f_score_value=7,
            sector_key="consumer_defensive"
        )
        
        result2 = calculate_score_v2(
            ratio_values=ratio_values,
            contextual_values=contextual_values,
            z_score_value=4.0,
            z_score_level="SAFE",
            f_score_value=7,
            sector_key="consumer_defensive"
        )
        
        assert result1["score"] == result2["score"], \
            "El scoring debe ser determinístico"
    
    def test_score_bounded(self, healthy_company_data):
        """El score siempre debe estar entre 0 y 100."""
        # Probar con diferentes tipos de empresas
        test_fixtures = [
            "healthy_company_data",
        ]
        
        data = healthy_company_data
        
        ratio_values = {
            "current_ratio": data["current_ratio"],
            "debt_to_equity": data["debt_to_equity"],
            "interest_coverage": data["interest_coverage"],
            "roe": data["roe"],
            "roa": data["roa"],
            "operating_margin": data["operating_margin"],
            "net_margin": data["net_margin"],
            "pe": data["pe"],
            "p_fcf": 30.0,
            "ev_ebitda": data["ev_ebitda"],
            "peg": data["peg"],
            "fcf_yield": data["fcf_yield"],
            "fcf": data["free_cash_flow"],
            "operating_cash_flow": data["operating_cash_flow"],
            "net_income": data["net_income"],
            "fcf_to_net_income": 1.0,
        }
        
        contextual_values = {
            "sector_pe": data["sector_pe"],
            "sector_ev_ebitda": data["sector_ev_ebitda"],
            "revenue_cagr_3y": data["revenue_growth_3y"],
            "eps_cagr_3y": data["eps_growth_3y"],
            "fcf_cagr_3y": data["fcf_growth_3y"],
        }
        
        result = calculate_score_v2(
            ratio_values=ratio_values,
            contextual_values=contextual_values,
            z_score_value=4.0,
            z_score_level="SAFE",
            f_score_value=7,
            sector_key="consumer_defensive"
        )
        
        assert 0 <= result["score"] <= 100, \
            f"Score debe estar entre 0-100, got {result['score']}"
        
        # Cada categoría también debe estar bounded
        for cat in result["categories"]:
            assert 0 <= cat["score"] <= 20, \
                f"Categoría {cat['category']} score {cat['score']} fuera de rango"
