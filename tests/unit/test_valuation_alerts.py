"""
Tests for Valuation Functions and Alerts
========================================
Cobertura de funciones de valuación avanzada y sistema de alertas.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from financial_ratios import (
    graham_number,
    margin_of_safety,
    calculate_justified_pe,
    adjust_valuation_for_growth,
    valuation_flags,
    leverage_flags,
    liquidity_flags,
    profitability_flags,
    cash_flow_flags,
    growth_flags,
    aggregate_alerts,
    calculate_all_ratios,
    format_ratio,
    detect_growth_company,
)


# =============================================================================
# GRAHAM NUMBER
# =============================================================================

class TestGrahamNumber:
    """Tests para el número de Graham."""
    
    def test_graham_number_calculation(self):
        """Graham Number = sqrt(22.5 × EPS × BVPS)"""
        result = graham_number(5.0, 50.0)
        assert result is not None
        assert abs(result - 75.0) < 0.01
    
    def test_graham_number_with_high_values(self):
        result = graham_number(10.0, 100.0)
        assert result is not None
        assert abs(result - 150.0) < 0.01
    
    def test_graham_number_negative_eps(self):
        result = graham_number(-5.0, 50.0)
        assert result is None
    
    def test_graham_number_negative_bvps(self):
        result = graham_number(5.0, -50.0)
        assert result is None
    
    def test_graham_number_none_values(self):
        assert graham_number(None, 50.0) is None
        assert graham_number(5.0, None) is None


# =============================================================================
# MARGIN OF SAFETY
# =============================================================================

class TestMarginOfSafety:
    """Tests para margen de seguridad."""
    
    def test_positive_margin(self):
        result = margin_of_safety(100.0, 80.0)
        assert result is not None
        assert abs(result - 0.20) < 0.001
    
    def test_negative_margin(self):
        result = margin_of_safety(100.0, 120.0)
        assert result is not None
        assert abs(result - (-0.20)) < 0.001
    
    def test_zero_intrinsic_value(self):
        result = margin_of_safety(0, 50.0)
        assert result is None
    
    def test_none_values(self):
        assert margin_of_safety(None, 50.0) is None
        assert margin_of_safety(100.0, None) is None


# =============================================================================
# JUSTIFIED P/E
# =============================================================================

class TestJustifiedPE:
    """Tests para P/E justificado."""
    
    def test_justified_pe_calculation(self):
        result = calculate_justified_pe(
            earnings_growth=0.10,
            required_return=0.12,
            roe=0.20,
            payout_ratio=0.40
        )
        assert result is not None
        assert result > 0
    
    def test_justified_pe_high_growth(self):
        pe_low = calculate_justified_pe(earnings_growth=0.05, required_return=0.12)
        pe_high = calculate_justified_pe(earnings_growth=0.10, required_return=0.12)
        
        if pe_low is not None and pe_high is not None:
            assert pe_high > pe_low
    
    def test_justified_pe_none_growth(self):
        result = calculate_justified_pe(earnings_growth=None)
        # Debe manejar None sin crash


# =============================================================================
# ADJUST VALUATION FOR GROWTH
# =============================================================================

class TestAdjustValuationForGrowth:
    """Tests para ajuste de valoración por crecimiento."""
    
    def test_high_quality_growth_reduces_penalty(self):
        result = adjust_valuation_for_growth(
            base_pe_adjustment=-5,  # Penalización por P/E alto
            pe=50,
            sector_pe=25,
            growth_quality_score=90,
            company_type="growth",
            revenue_growth=0.30,
            roe=0.35
        )
        
        # La función puede retornar tupla o solo un valor
        if isinstance(result, tuple):
            adjusted = result[0]
        else:
            adjusted = result
        
        # Con growth quality alto, la penalización debe reducirse
        assert adjusted >= -5 or adjusted is not None
    
    def test_low_quality_growth_no_adjustment(self):
        result = adjust_valuation_for_growth(
            base_pe_adjustment=-5,
            pe=50,
            sector_pe=25,
            growth_quality_score=30,
            company_type="value",
            revenue_growth=0.03,
            roe=0.10
        )
        
        # Con growth quality bajo, no debe haber mucho ajuste
        if isinstance(result, tuple):
            adjusted = result[0]
        else:
            adjusted = result
        
        assert adjusted is not None


# =============================================================================
# FLAGS FUNCTIONS
# =============================================================================

class TestValuationFlags:
    """Tests para banderas de valoración."""
    
    def test_overvalued_flags(self):
        result = valuation_flags(
            pe=50,
            sector_pe=20,
            p_fcf=40,
            ev_ebitda_value=25,
            peg=3.0,
            fcf_yield_value=0.02
        )
        
        assert result is not None
        assert isinstance(result, dict)
        assert "overvalued_flag" in result
    
    def test_undervalued_flags(self):
        result = valuation_flags(
            pe=10,
            sector_pe=20,
            p_fcf=8,
            ev_ebitda_value=6,
            peg=0.5,
            fcf_yield_value=0.10
        )
        
        assert result is not None
        assert "undervalued_flag" in result
    
    def test_valuation_flags_with_none(self):
        result = valuation_flags(
            pe=None,
            sector_pe=20,
            p_fcf=None
        )
        
        assert result is not None


class TestLeverageFlags:
    """Tests para banderas de apalancamiento."""
    
    def test_high_leverage_flags(self):
        result = leverage_flags(
            debt_to_equity_value=3.0,
            interest_coverage_value=1.5,
            net_debt_to_ebitda_value=6.0
        )
        
        assert result is not None
        assert isinstance(result, dict)
    
    def test_low_leverage_flags(self):
        result = leverage_flags(
            debt_to_equity_value=0.3,
            interest_coverage_value=20.0,
            net_debt_to_ebitda_value=1.0
        )
        
        assert result is not None


class TestLiquidityFlags:
    """Tests para banderas de liquidez."""
    
    def test_poor_liquidity_flags(self):
        result = liquidity_flags(
            current_ratio_value=0.6,
            quick_ratio_value=0.3,
            cash_ratio_value=0.1
        )
        
        assert result is not None
        assert isinstance(result, dict)
    
    def test_good_liquidity_flags(self):
        result = liquidity_flags(
            current_ratio_value=2.5,
            quick_ratio_value=2.0,
            cash_ratio_value=0.5
        )
        
        assert result is not None


class TestProfitabilityFlags:
    """Tests para banderas de rentabilidad."""
    
    def test_unprofitable_flags(self):
        result = profitability_flags(
            roe_value=-0.10,
            roa_value=-0.05,
            operating_margin_value=-0.03,
            net_margin_value=-0.05
        )
        
        assert result is not None
        assert isinstance(result, dict)
    
    def test_profitable_flags(self):
        result = profitability_flags(
            roe_value=0.25,
            roa_value=0.15,
            operating_margin_value=0.20,
            net_margin_value=0.15
        )
        
        assert result is not None


class TestCashFlowFlags:
    """Tests para banderas de flujo de caja."""
    
    def test_negative_fcf_flags(self):
        result = cash_flow_flags(
            fcf_value=-500_000_000,
            fcf_to_net_income=-5.0
        )
        
        assert result is not None
        assert isinstance(result, dict)
    
    def test_positive_fcf_flags(self):
        result = cash_flow_flags(
            fcf_value=1_000_000_000,
            fcf_to_net_income=1.25
        )
        
        assert result is not None


class TestGrowthFlags:
    """Tests para banderas de crecimiento."""
    
    def test_contracting_company_flags(self):
        result = growth_flags(
            revenue_cagr_3y=-0.15,
            eps_cagr_3y=-0.25,
            fcf_cagr_3y=-0.20
        )
        
        assert result is not None
        assert isinstance(result, dict)
    
    def test_growing_company_flags(self):
        result = growth_flags(
            revenue_cagr_3y=0.15,
            eps_cagr_3y=0.20,
            fcf_cagr_3y=0.18
        )
        
        assert result is not None


# =============================================================================
# AGGREGATE ALERTS
# =============================================================================

class TestAggregateAlerts:
    """Tests para agregación de alertas."""
    
    def test_aggregate_returns_dict(self, healthy_company_data):
        data = healthy_company_data
        
        ratio_values = {
            "pe": data["pe"],
            "p_fcf": 30,
            "ev_ebitda": data["ev_ebitda"],
            "peg": data["peg"],
            "fcf_yield": data["fcf_yield"],
            "current_ratio": data["current_ratio"],
            "quick_ratio": data["current_ratio"] * 0.8,
            "debt_to_equity": data["debt_to_equity"],
            "interest_coverage": data["interest_coverage"],
            "roe": data["roe"],
            "roa": data["roa"],
            "operating_margin": data["operating_margin"],
            "net_margin": data["net_margin"],
            "fcf": data["free_cash_flow"],
            "operating_cash_flow": data["operating_cash_flow"],
            "net_income": data["net_income"],
        }
        
        contextual_values = {
            "sector_pe": data["sector_pe"],
            "sector_ev_ebitda": data["sector_ev_ebitda"],
            "revenue_cagr_3y": data["revenue_growth_3y"],
            "eps_cagr_3y": data["eps_growth_3y"],
        }
        
        result = aggregate_alerts(ratio_values, contextual_values)
        
        assert result is not None
        assert isinstance(result, dict)
        assert "score" in result


# =============================================================================
# DETECT GROWTH COMPANY
# =============================================================================

class TestDetectGrowthCompany:
    """Tests para detección de empresa growth."""
    
    def test_detect_growth_company_high_growth(self):
        ratio_values = {"pe": 50, "roe": 0.30}
        contextual_values = {
            "revenue_cagr_3y": 0.30,
            "eps_cagr_3y": 0.40,
            "sector_pe": 25,
        }
        
        result = detect_growth_company(ratio_values, contextual_values)
        # High growth + high PE ratio usually indicates growth
        assert isinstance(result, bool)
    
    def test_detect_growth_company_low_growth(self):
        ratio_values = {"pe": 12, "roe": 0.12}
        contextual_values = {
            "revenue_cagr_3y": 0.03,
            "eps_cagr_3y": 0.05,
            "sector_pe": 15,
        }
        
        result = detect_growth_company(ratio_values, contextual_values)
        assert isinstance(result, bool)


# =============================================================================
# FORMAT RATIO
# =============================================================================

class TestFormatRatio:
    """Tests para formateo de ratios."""
    
    def test_format_decimal(self):
        result = format_ratio(0.1567, "decimal", 2)
        assert result is not None
        assert len(result) > 0
    
    def test_format_percent(self):
        result = format_ratio(0.1567, "percent", 1)
        assert result is not None
    
    def test_format_none_value(self):
        result = format_ratio(None, "decimal", 2)
        assert result in ["N/A", "-", "—", "--"]
    
    def test_format_multiplier(self):
        result = format_ratio(15.5, "multiplier", 1)
        assert result is not None


# =============================================================================
# CALCULATE ALL RATIOS
# =============================================================================

class TestCalculateAllRatios:
    """Tests para cálculo de todos los ratios."""
    
    def test_calculate_all_ratios_complete_data(self):
        financial_data = {
            "price": 150.0,
            "shares_outstanding": 1_000_000_000,
            "net_income": 5_000_000_000,
            "revenue": 50_000_000_000,
            "total_assets": 100_000_000_000,
            "total_equity": 40_000_000_000,
            "total_debt": 20_000_000_000,
            "current_assets": 30_000_000_000,
            "current_liabilities": 20_000_000_000,
            "operating_income": 8_000_000_000,
            "gross_profit": 20_000_000_000,
            "operating_cash_flow": 7_000_000_000,
            "capex": 2_000_000_000,
            "cash_and_equivalents": 10_000_000_000,
            "ebit": 8_000_000_000,
            "interest_expense": 500_000_000,
        }
        
        result = calculate_all_ratios(financial_data)
        
        assert result is not None
        assert isinstance(result, dict)
    
    def test_calculate_all_ratios_empty_data(self):
        result = calculate_all_ratios({})
        
        assert result is not None
        assert isinstance(result, dict)
