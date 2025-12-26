"""
Tests for Basic Financial Ratios
================================
Cobertura de funciones de cálculo de ratios individuales.

Incluye:
- Helper functions (safe_div, safe_multiply, etc.)
- Profitability ratios (ROE, ROA, margins)
- Valuation ratios (P/E, P/B, P/S, EV/EBITDA)
- Liquidity ratios (current, quick, cash)
- Leverage ratios (D/E, interest coverage)
- Efficiency ratios (turnover ratios)
- Growth metrics (CAGR, YoY)
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from financial_ratios import (
    # Helper functions
    safe_div, safe_multiply, safe_subtract, safe_add,
    # Profitability
    roe, roa, roic, operating_margin, gross_margin, net_margin,
    ebitda, ebitda_margin,
    # Valuation
    earnings_per_share, price_earnings, forward_pe,
    book_value_per_share, price_book, sales_per_share, price_sales,
    free_cash_flow, free_cash_flow_per_share, price_free_cash_flow,
    market_cap, enterprise_value, ev_ebitda, ev_revenue, ev_fcf,
    peg_ratio, free_cash_flow_yield, dividend_yield, dividend_payout_ratio,
    earnings_yield,
    # Liquidity
    current_ratio, quick_ratio, cash_ratio, working_capital,
    # Leverage
    debt_to_equity, debt_to_assets, net_debt, net_debt_to_ebitda,
    interest_coverage, equity_multiplier,
    # Efficiency
    asset_turnover, inventory_turnover, receivables_turnover,
    days_sales_outstanding, days_inventory_outstanding,
    # Growth
    cagr, yoy_growth, volatility_coefficient,
    # DuPont
    dupont_roe, dupont_analysis,
)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

class TestSafeDiv:
    """Tests para safe_div."""
    
    def test_normal_division(self):
        assert safe_div(10, 2) == 5.0
        assert safe_div(100, 4) == 25.0
    
    def test_division_by_zero_returns_none(self):
        assert safe_div(10, 0) is None
        assert safe_div(100, 0.0) is None
    
    def test_none_numerator(self):
        assert safe_div(None, 5) is None
    
    def test_none_denominator(self):
        assert safe_div(10, None) is None
    
    def test_both_none(self):
        assert safe_div(None, None) is None
    
    def test_negative_values(self):
        assert safe_div(-10, 2) == -5.0
        assert safe_div(10, -2) == -5.0
        assert safe_div(-10, -2) == 5.0


class TestSafeMultiply:
    """Tests para safe_multiply."""
    
    def test_two_values(self):
        assert safe_multiply(5, 3) == 15.0
    
    def test_multiple_values(self):
        assert safe_multiply(2, 3, 4) == 24.0
    
    def test_with_none(self):
        assert safe_multiply(5, None) is None
        assert safe_multiply(None, 3) is None
    
    def test_single_value(self):
        result = safe_multiply(5)
        assert result == 5.0


class TestSafeSubtract:
    """Tests para safe_subtract."""
    
    def test_normal_subtraction(self):
        assert safe_subtract(10, 3) == 7.0
    
    def test_negative_result(self):
        assert safe_subtract(3, 10) == -7.0
    
    def test_with_none(self):
        assert safe_subtract(10, None) is None
        assert safe_subtract(None, 5) is None


class TestSafeAdd:
    """Tests para safe_add."""
    
    def test_two_values(self):
        assert safe_add(5, 3) == 8.0
    
    def test_multiple_values(self):
        assert safe_add(1, 2, 3, 4) == 10.0
    
    def test_with_none(self):
        assert safe_add(5, None) is None


# =============================================================================
# PROFITABILITY RATIOS
# =============================================================================

class TestROE:
    """Tests para Return on Equity."""
    
    def test_positive_roe(self):
        result = roe(1_000_000, 10_000_000)
        assert result == 0.1  # 10%
    
    def test_negative_net_income(self):
        result = roe(-500_000, 10_000_000)
        assert result == -0.05  # -5%
    
    def test_none_values(self):
        assert roe(None, 10_000_000) is None
        assert roe(1_000_000, None) is None
    
    def test_zero_equity(self):
        assert roe(1_000_000, 0) is None


class TestROA:
    """Tests para Return on Assets."""
    
    def test_positive_roa(self):
        result = roa(500_000, 5_000_000)
        assert result == 0.1  # 10%
    
    def test_none_values(self):
        assert roa(None, 5_000_000) is None


class TestROIC:
    """Tests para Return on Invested Capital."""
    
    def test_positive_roic(self):
        result = roic(800_000, 4_000_000)
        assert result == 0.2  # 20%
    
    def test_none_values(self):
        assert roic(None, 4_000_000) is None


class TestMargins:
    """Tests para márgenes."""
    
    def test_operating_margin(self):
        result = operating_margin(2_000_000, 10_000_000)
        assert result == 0.2  # 20%
    
    def test_gross_margin(self):
        result = gross_margin(4_000_000, 10_000_000)
        assert result == 0.4  # 40%
    
    def test_net_margin(self):
        result = net_margin(1_500_000, 10_000_000)
        assert result == 0.15  # 15%
    
    def test_ebitda_calculation(self):
        result = ebitda(1_000_000, 200_000, 100_000)
        assert result == 1_300_000
    
    def test_ebitda_margin(self):
        result = ebitda_margin(2_000_000, 10_000_000)
        assert result == 0.2  # 20%


# =============================================================================
# VALUATION RATIOS
# =============================================================================

class TestEPSAndPE:
    """Tests para EPS y P/E."""
    
    def test_eps_calculation(self):
        result = earnings_per_share(1_000_000_000, 100_000_000)
        assert result == 10.0
    
    def test_pe_calculation(self):
        result = price_earnings(150.0, 10.0)
        assert result == 15.0
    
    def test_forward_pe(self):
        result = forward_pe(100.0, 8.0)
        assert result == 12.5
    
    def test_pe_with_negative_eps(self):
        result = price_earnings(50.0, -5.0)
        assert result == -10.0  # P/E negativo


class TestBookValueRatios:
    """Tests para ratios de valor en libros."""
    
    def test_bvps(self):
        result = book_value_per_share(5_000_000_000, 100_000_000)
        assert result == 50.0
    
    def test_pb_ratio(self):
        result = price_book(75.0, 50.0)
        assert result == 1.5


class TestSalesRatios:
    """Tests para ratios de ventas."""
    
    def test_sales_per_share(self):
        result = sales_per_share(10_000_000_000, 500_000_000)
        assert result == 20.0
    
    def test_price_sales(self):
        result = price_sales(60.0, 20.0)
        assert result == 3.0


class TestFCFRatios:
    """Tests para ratios de Free Cash Flow."""
    
    def test_fcf_calculation(self):
        result = free_cash_flow(5_000_000_000, 1_000_000_000)
        assert result == 4_000_000_000
    
    def test_fcf_per_share(self):
        result = free_cash_flow_per_share(4_000_000_000, 400_000_000)
        assert result == 10.0
    
    def test_price_fcf(self):
        result = price_free_cash_flow(120.0, 10.0)
        assert result == 12.0
    
    def test_fcf_yield(self):
        result = free_cash_flow_yield(4_000_000_000, 40_000_000_000)
        assert result == 0.1  # 10%


class TestEnterpriseValue:
    """Tests para Enterprise Value."""
    
    def test_market_cap(self):
        result = market_cap(150.0, 1_000_000_000)
        assert result == 150_000_000_000
    
    def test_enterprise_value(self):
        result = enterprise_value(100_000_000_000, 20_000_000_000, 5_000_000_000)
        assert result == 115_000_000_000
    
    def test_ev_ebitda(self):
        result = ev_ebitda(100_000_000_000, 10_000_000_000)
        assert result == 10.0
    
    def test_ev_revenue(self):
        result = ev_revenue(100_000_000_000, 50_000_000_000)
        assert result == 2.0
    
    def test_ev_fcf(self):
        result = ev_fcf(100_000_000_000, 5_000_000_000)
        assert result == 20.0


class TestPEGAndYield:
    """Tests para PEG y yields."""
    
    def test_peg_ratio(self):
        result = peg_ratio(20.0, 20.0)  # P/E 20, growth 20%
        assert result == 1.0
    
    def test_peg_with_low_growth(self):
        result = peg_ratio(20.0, 5.0)  # P/E 20, growth 5%
        assert result == 4.0
    
    def test_peg_with_zero_growth(self):
        result = peg_ratio(20.0, 0.0)
        assert result is None
    
    def test_dividend_yield(self):
        result = dividend_yield(2.0, 50.0)
        assert result == 0.04  # 4%
    
    def test_dividend_payout_ratio(self):
        result = dividend_payout_ratio(500_000_000, 1_000_000_000)
        assert result == 0.5  # 50%
    
    def test_earnings_yield(self):
        result = earnings_yield(5.0, 100.0)
        assert result == 0.05  # 5%


# =============================================================================
# LIQUIDITY RATIOS
# =============================================================================

class TestLiquidityRatios:
    """Tests para ratios de liquidez."""
    
    def test_current_ratio(self):
        result = current_ratio(5_000_000, 2_500_000)
        assert result == 2.0
    
    def test_quick_ratio(self):
        result = quick_ratio(5_000_000, 1_000_000, 2_500_000)
        assert result == 1.6
    
    def test_cash_ratio(self):
        result = cash_ratio(1_000_000, 2_000_000)
        assert result == 0.5
    
    def test_working_capital(self):
        result = working_capital(5_000_000, 3_000_000)
        assert result == 2_000_000
    
    def test_negative_working_capital(self):
        result = working_capital(2_000_000, 5_000_000)
        assert result == -3_000_000


# =============================================================================
# LEVERAGE RATIOS
# =============================================================================

class TestLeverageRatios:
    """Tests para ratios de apalancamiento."""
    
    def test_debt_to_equity(self):
        result = debt_to_equity(5_000_000, 10_000_000)
        assert result == 0.5
    
    def test_debt_to_assets(self):
        result = debt_to_assets(3_000_000, 10_000_000)
        assert result == 0.3
    
    def test_net_debt(self):
        result = net_debt(5_000_000, 2_000_000)
        assert result == 3_000_000
    
    def test_net_debt_negative(self):
        """Net debt negativo = más efectivo que deuda."""
        result = net_debt(2_000_000, 5_000_000)
        assert result == -3_000_000
    
    def test_net_debt_to_ebitda(self):
        result = net_debt_to_ebitda(3_000_000, 1_500_000)
        assert result == 2.0
    
    def test_interest_coverage(self):
        result = interest_coverage(5_000_000, 500_000)
        assert result == 10.0
    
    def test_equity_multiplier(self):
        result = equity_multiplier(10_000_000, 4_000_000)
        assert result == 2.5


# =============================================================================
# EFFICIENCY RATIOS
# =============================================================================

class TestEfficiencyRatios:
    """Tests para ratios de eficiencia."""
    
    def test_asset_turnover(self):
        result = asset_turnover(10_000_000, 5_000_000)
        assert result == 2.0
    
    def test_inventory_turnover(self):
        result = inventory_turnover(6_000_000, 1_000_000)
        assert result == 6.0
    
    def test_receivables_turnover(self):
        result = receivables_turnover(12_000_000, 2_000_000)
        assert result == 6.0
    
    def test_days_sales_outstanding(self):
        result = days_sales_outstanding(2_000_000, 12_000_000)
        # DSO = (AR / Revenue) * 365
        expected = (2_000_000 / 12_000_000) * 365
        assert abs(result - expected) < 0.01
    
    def test_days_inventory_outstanding(self):
        result = days_inventory_outstanding(1_000_000, 6_000_000)
        # DIO = (Inventory / COGS) * 365
        expected = (1_000_000 / 6_000_000) * 365
        assert abs(result - expected) < 0.01


# =============================================================================
# GROWTH METRICS
# =============================================================================

class TestGrowthMetrics:
    """Tests para métricas de crecimiento."""
    
    def test_cagr_positive(self):
        """CAGR de $100 a $200 en 5 años."""
        result = cagr(100, 200, 5)
        # CAGR = (200/100)^(1/5) - 1 ≈ 14.87%
        assert result is not None
        assert abs(result - 0.1487) < 0.01
    
    def test_cagr_negative(self):
        """CAGR negativo cuando valor final < inicial."""
        result = cagr(200, 100, 5)
        assert result is not None
        assert result < 0
    
    def test_cagr_zero_years(self):
        result = cagr(100, 200, 0)
        assert result is None
    
    def test_cagr_negative_begin(self):
        result = cagr(-100, 200, 5)
        assert result is None
    
    def test_yoy_growth(self):
        result = yoy_growth(120, 100)
        assert result == 0.2  # 20%
    
    def test_yoy_growth_negative(self):
        result = yoy_growth(80, 100)
        assert result == -0.2  # -20%
    
    def test_volatility_coefficient(self):
        result = volatility_coefficient(10, 100)
        assert result == 0.1  # CV = 10%


# =============================================================================
# DUPONT ANALYSIS
# =============================================================================

class TestDuPontAnalysis:
    """Tests para análisis DuPont."""
    
    def test_dupont_roe_3factor(self):
        """DuPont 3-factor: ROE = Net Margin × Asset Turnover × Equity Multiplier."""
        result = dupont_roe(0.10, 1.5, 2.0)  # 10% margin, 1.5x turnover, 2x leverage
        assert abs(result - 0.30) < 0.001  # 30% ROE
    
    def test_dupont_analysis_full(self):
        """Test full DuPont decomposition."""
        result = dupont_analysis(
            net_income=1_000_000,
            revenue=10_000_000,
            total_assets=5_000_000,
            total_equity=2_500_000
        )
        
        assert result is not None
        # La función puede usar "roe" o "dupont_roe" como key
        assert "dupont_roe" in result or "roe" in result
        assert "net_margin" in result
        assert "asset_turnover" in result
        assert "equity_multiplier" in result
        
        # Verify: ROE = 1M/2.5M = 40%
        roe_value = result.get("dupont_roe") or result.get("roe") or result.get("calculated_roe")
        assert roe_value is not None
        assert abs(roe_value - 0.4) < 0.001
        
        # Net margin = 1M/10M = 10%
        assert abs(result["net_margin"] - 0.1) < 0.001
        
        # Asset turnover = 10M/5M = 2.0
        assert abs(result["asset_turnover"] - 2.0) < 0.001
        
        # Equity multiplier = 5M/2.5M = 2.0
        assert abs(result["equity_multiplier"] - 2.0) < 0.001
    
    def test_dupont_with_none(self):
        result = dupont_analysis(None, 10_000_000, 5_000_000, 2_500_000)
        assert result is None or result.get("roe") is None


# =============================================================================
# EDGE CASES FOR ALL RATIOS
# =============================================================================

class TestEdgeCasesAllRatios:
    """Tests de edge cases comunes para todos los ratios."""
    
    def test_all_ratios_handle_none(self):
        """Todos los ratios deben manejar None sin crash."""
        # Profitability
        assert roe(None, None) is None
        assert roa(None, None) is None
        assert operating_margin(None, None) is None
        
        # Valuation
        assert price_earnings(None, None) is None
        assert price_book(None, None) is None
        assert peg_ratio(None, None) is None
        
        # Liquidity
        assert current_ratio(None, None) is None
        assert quick_ratio(None, None, None) is None
        
        # Leverage
        assert debt_to_equity(None, None) is None
        assert interest_coverage(None, None) is None
        
        # Efficiency
        assert asset_turnover(None, None) is None
        
        # Growth
        assert cagr(None, None, None) is None
        assert yoy_growth(None, None) is None
    
    def test_all_ratios_handle_zero_denominator(self):
        """Todos los ratios deben manejar división por cero."""
        assert roe(1000, 0) is None
        assert roa(1000, 0) is None
        assert price_earnings(100, 0) is None
        assert current_ratio(1000, 0) is None
        assert debt_to_equity(1000, 0) is None
        assert interest_coverage(1000, 0) is None
        assert asset_turnover(1000, 0) is None
    
    def test_very_large_numbers(self):
        """Ratios deben manejar números muy grandes."""
        big = 1_000_000_000_000_000  # 1 quadrillion
        result = roe(big, big * 10)
        assert result == 0.1
        
        result = market_cap(1000, big)
        assert result == big * 1000
    
    def test_very_small_numbers(self):
        """Ratios deben manejar números muy pequeños."""
        small = 0.0001
        result = roe(small, small * 10)
        assert result == 0.1
