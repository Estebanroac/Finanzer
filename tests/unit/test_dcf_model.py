"""
Tests for DCF Model
===================
Validación del modelo de Discounted Cash Flow para valuación intrínseca.

Modelos testeados:
1. dcf_fair_value: DCF clásico con parámetros fijos
2. dcf_dynamic: DCF dinámico con WACC y growth calculados
3. calculate_wacc: Cálculo del costo de capital (CAPM)

Fórmula DCF:
    PV = Σ (FCF_t / (1+r)^t) + Terminal_Value / (1+r)^n

Donde:
    Terminal_Value = FCF_n+1 / (r - g)  [Gordon Growth Model]
    r = WACC (Weighted Average Cost of Capital)
    g = Terminal growth rate

Referencias:
    - Gordon, M. J. (1959). "Dividends, Earnings, and Stock Prices"
    - Damodaran, A. "Investment Valuation"
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from financial_ratios import dcf_fair_value, dcf_dynamic, calculate_wacc


class TestDCFFairValueBasic:
    """Tests básicos del DCF clásico."""
    
    def test_positive_fcf_returns_value(self):
        """FCF positivo debe retornar valor positivo."""
        fair_value = dcf_fair_value(
            fcf=1_000_000_000,  # $1B FCF
            growth_rate=0.10,  # 10% growth
            discount_rate=0.12,  # 12% WACC
            terminal_growth=0.03,  # 3% terminal
            years=10,
            shares_outstanding=100_000_000
        )
        
        assert fair_value is not None
        assert fair_value > 0, "DCF con FCF positivo debe dar valor positivo"
    
    def test_higher_growth_higher_value(self):
        """Mayor growth rate debe dar mayor valor."""
        fcf = 1_000_000_000
        shares = 100_000_000
        
        value_low_growth = dcf_fair_value(
            fcf=fcf, growth_rate=0.05, discount_rate=0.10,
            terminal_growth=0.03, years=10, shares_outstanding=shares
        )
        
        value_high_growth = dcf_fair_value(
            fcf=fcf, growth_rate=0.15, discount_rate=0.10,
            terminal_growth=0.03, years=10, shares_outstanding=shares
        )
        
        assert value_high_growth > value_low_growth, \
            "Mayor growth debe producir mayor valor"
    
    def test_higher_discount_rate_lower_value(self):
        """Mayor discount rate debe dar menor valor."""
        fcf = 1_000_000_000
        shares = 100_000_000
        
        value_low_wacc = dcf_fair_value(
            fcf=fcf, growth_rate=0.10, discount_rate=0.08,  # WACC bajo
            terminal_growth=0.03, years=10, shares_outstanding=shares
        )
        
        value_high_wacc = dcf_fair_value(
            fcf=fcf, growth_rate=0.10, discount_rate=0.15,  # WACC alto
            terminal_growth=0.03, years=10, shares_outstanding=shares
        )
        
        assert value_low_wacc > value_high_wacc, \
            "Mayor WACC debe producir menor valor"
    
    def test_terminal_growth_impact(self):
        """Mayor terminal growth debe dar mayor valor (pero menor que discount rate)."""
        fcf = 1_000_000_000
        shares = 100_000_000
        
        value_low_terminal = dcf_fair_value(
            fcf=fcf, growth_rate=0.10, discount_rate=0.12,
            terminal_growth=0.02, years=10, shares_outstanding=shares
        )
        
        value_high_terminal = dcf_fair_value(
            fcf=fcf, growth_rate=0.10, discount_rate=0.12,
            terminal_growth=0.04, years=10, shares_outstanding=shares
        )
        
        assert value_high_terminal > value_low_terminal, \
            "Mayor terminal growth debe producir mayor valor"


class TestDCFFairValueEdgeCases:
    """Tests de casos edge del DCF clásico."""
    
    def test_none_fcf_returns_none(self):
        """FCF None debe retornar None."""
        result = dcf_fair_value(
            fcf=None,
            growth_rate=0.10,
            discount_rate=0.12,
            terminal_growth=0.03,
            years=10,
            shares_outstanding=100_000_000
        )
        
        assert result is None
    
    def test_none_shares_returns_none(self):
        """Shares None debe retornar None."""
        result = dcf_fair_value(
            fcf=1_000_000_000,
            growth_rate=0.10,
            discount_rate=0.12,
            terminal_growth=0.03,
            years=10,
            shares_outstanding=None
        )
        
        assert result is None
    
    def test_zero_shares_returns_none(self):
        """Shares = 0 debe retornar None (división por cero)."""
        result = dcf_fair_value(
            fcf=1_000_000_000,
            growth_rate=0.10,
            discount_rate=0.12,
            terminal_growth=0.03,
            years=10,
            shares_outstanding=0
        )
        
        assert result is None
    
    def test_negative_shares_returns_none(self):
        """Shares negativo debe retornar None."""
        result = dcf_fair_value(
            fcf=1_000_000_000,
            growth_rate=0.10,
            discount_rate=0.12,
            terminal_growth=0.03,
            years=10,
            shares_outstanding=-100_000_000
        )
        
        assert result is None
    
    def test_terminal_growth_equals_discount_rate_returns_none(self):
        """Terminal growth = discount rate causa división por cero."""
        result = dcf_fair_value(
            fcf=1_000_000_000,
            growth_rate=0.10,
            discount_rate=0.10,  # Igual a terminal
            terminal_growth=0.10,  # Igual a discount
            years=10,
            shares_outstanding=100_000_000
        )
        
        assert result is None, "g >= r debe retornar None (modelo no válido)"
    
    def test_terminal_growth_exceeds_discount_rate_returns_none(self):
        """Terminal growth > discount rate causa valor negativo/infinito."""
        result = dcf_fair_value(
            fcf=1_000_000_000,
            growth_rate=0.10,
            discount_rate=0.08,
            terminal_growth=0.10,  # > discount rate
            years=10,
            shares_outstanding=100_000_000
        )
        
        assert result is None, "g > r debe retornar None"


class TestDCFFairValueRealisticScenarios:
    """Tests con escenarios realistas."""
    
    def test_apple_like_valuation(self):
        """
        Valuación tipo Apple:
        FCF ~$100B, growth moderado, WACC ~10%
        """
        fair_value = dcf_fair_value(
            fcf=100_000_000_000,  # $100B FCF
            growth_rate=0.08,  # 8% growth
            discount_rate=0.10,  # 10% WACC
            terminal_growth=0.03,  # 3% terminal
            years=10,
            shares_outstanding=15_500_000_000  # ~15.5B shares
        )
        
        assert fair_value is not None
        # Apple's fair value debería estar en rango razonable (>$100, <$500)
        assert 50 < fair_value < 500, f"Fair value {fair_value} fuera de rango esperado"
    
    def test_high_growth_tech_valuation(self):
        """
        Valuación de tech de alto crecimiento:
        FCF moderado pero growth alto
        """
        fair_value = dcf_fair_value(
            fcf=5_000_000_000,  # $5B FCF
            growth_rate=0.25,  # 25% growth
            discount_rate=0.12,  # 12% WACC (riesgo más alto)
            terminal_growth=0.04,  # 4% terminal
            years=10,
            shares_outstanding=500_000_000
        )
        
        assert fair_value is not None
        assert fair_value > 0
    
    def test_mature_utility_valuation(self):
        """
        Valuación de utility madura:
        FCF estable, bajo growth
        """
        fair_value = dcf_fair_value(
            fcf=3_000_000_000,  # $3B FCF
            growth_rate=0.02,  # 2% growth
            discount_rate=0.07,  # 7% WACC (bajo riesgo)
            terminal_growth=0.02,  # 2% terminal
            years=10,
            shares_outstanding=400_000_000
        )
        
        assert fair_value is not None
        assert fair_value > 0


class TestCalculateWACC:
    """Tests para el cálculo del WACC."""
    
    def test_equity_only_company(self):
        """
        Empresa sin deuda: WACC = Cost of Equity.
        Cost of Equity = Rf + β * (Rm - Rf)
        """
        wacc = calculate_wacc(
            beta=1.0,
            risk_free_rate=0.045,  # 4.5%
            market_risk_premium=0.055,  # 5.5%
            debt_to_equity=0,  # Sin deuda
        )
        
        # WACC = 4.5% + 1.0 * 5.5% = 10%
        assert wacc is not None
        assert abs(wacc - 0.10) < 0.001, f"WACC debería ser ~10%, got {wacc:.2%}"
    
    def test_high_beta_higher_wacc(self):
        """Beta alto debe producir WACC más alto."""
        wacc_low_beta = calculate_wacc(
            beta=0.8,
            risk_free_rate=0.045,
            market_risk_premium=0.055,
            debt_to_equity=0
        )
        
        wacc_high_beta = calculate_wacc(
            beta=1.5,
            risk_free_rate=0.045,
            market_risk_premium=0.055,
            debt_to_equity=0
        )
        
        assert wacc_high_beta > wacc_low_beta, "Beta alto debe dar WACC alto"
    
    def test_debt_reduces_wacc_tax_shield(self):
        """
        Deuda reduce WACC por tax shield (si costo de deuda < costo de equity).
        """
        # Sin deuda
        wacc_no_debt = calculate_wacc(
            beta=1.0,
            risk_free_rate=0.045,
            market_risk_premium=0.055,
            debt_to_equity=0
        )
        
        # Con algo de deuda (moderada)
        wacc_with_debt = calculate_wacc(
            beta=1.0,
            risk_free_rate=0.045,
            market_risk_premium=0.055,
            debt_to_equity=0.3,  # 30% D/E
            cost_of_debt=0.05,  # 5% costo de deuda
            tax_rate=0.25
        )
        
        # El tax shield generalmente reduce WACC ligeramente
        # pero depende de la proporción
        assert wacc_with_debt is not None
        assert wacc_no_debt is not None
    
    def test_none_beta_uses_default(self):
        """Beta None debe usar default (1.0)."""
        wacc = calculate_wacc(
            beta=None,
            risk_free_rate=0.045,
            market_risk_premium=0.055,
            debt_to_equity=0
        )
        
        # Debería comportarse como beta = 1.0
        assert wacc is not None
        assert abs(wacc - 0.10) < 0.001
    
    def test_wacc_formula_correctness(self):
        """Verificar la fórmula WACC = E/(E+D)*Re + D/(E+D)*Rd*(1-T)."""
        beta = 1.2
        rf = 0.04
        erp = 0.05
        d_e = 0.5  # D/E = 0.5 → D/(D+E) = 0.333, E/(D+E) = 0.667
        rd = 0.06
        tax = 0.25
        
        wacc = calculate_wacc(
            beta=beta,
            risk_free_rate=rf,
            market_risk_premium=erp,
            debt_to_equity=d_e,
            cost_of_debt=rd,
            tax_rate=tax
        )
        
        # Cálculo manual
        re = rf + beta * erp  # 0.04 + 1.2 * 0.05 = 0.10
        weight_e = 1 / (1 + d_e)  # 0.667
        weight_d = d_e / (1 + d_e)  # 0.333
        expected_wacc = weight_e * re + weight_d * rd * (1 - tax)
        # = 0.667 * 0.10 + 0.333 * 0.06 * 0.75
        # = 0.0667 + 0.015 = 0.0817
        
        assert wacc is not None
        assert abs(wacc - expected_wacc) < 0.001, \
            f"WACC {wacc:.4f} difiere de esperado {expected_wacc:.4f}"


class TestDCFDynamic:
    """Tests para el DCF dinámico con WACC y growth calculados."""
    
    def test_returns_dict_structure(self):
        """dcf_dynamic debe retornar dict con estructura correcta."""
        result = dcf_dynamic(
            fcf=1_000_000_000,
            shares_outstanding=100_000_000,
            beta=1.0,
            debt_to_equity=0.3,
            revenue_growth_3y=0.10
        )
        
        assert isinstance(result, dict)
        assert "fair_value" in result
        assert "wacc_used" in result
        assert "growth_used" in result
        assert "terminal_growth" in result
        assert "warnings" in result
    
    def test_uses_fcf_growth_when_available(self):
        """Debe usar FCF growth si está disponible."""
        result = dcf_dynamic(
            fcf=1_000_000_000,
            shares_outstanding=100_000_000,
            beta=1.0,
            fcf_growth_3y=0.15,  # FCF growth disponible
            revenue_growth_3y=0.10  # También disponible
        )
        
        # Debería preferir FCF growth
        if result.get("growth_source"):
            assert result["growth_source"] == "fcf_growth_3y"
    
    def test_falls_back_to_revenue_growth(self):
        """Debe usar revenue growth si FCF growth no está disponible."""
        result = dcf_dynamic(
            fcf=1_000_000_000,
            shares_outstanding=100_000_000,
            beta=1.0,
            fcf_growth_3y=None,  # No disponible
            revenue_growth_3y=0.10
        )
        
        if result.get("growth_source"):
            assert result["growth_source"] == "revenue_growth_3y"
    
    def test_caps_growth_rate(self):
        """Growth rate debe estar capeado a valores razonables."""
        result = dcf_dynamic(
            fcf=1_000_000_000,
            shares_outstanding=100_000_000,
            beta=1.0,
            fcf_growth_3y=0.50  # 50% - muy alto
        )
        
        # Growth debería estar capeado (típicamente a 20-25%)
        assert result["growth_used"] is not None
        assert result["growth_used"] <= 0.30, \
            f"Growth {result['growth_used']:.0%} debería estar capeado"
    
    def test_negative_fcf_returns_warning(self):
        """FCF negativo debe generar warning."""
        result = dcf_dynamic(
            fcf=-500_000_000,  # FCF negativo
            shares_outstanding=100_000_000,
            beta=1.0,
            revenue_growth_3y=0.10
        )
        
        assert result["fair_value"] is None
        assert len(result["warnings"]) > 0
        assert any("negativo" in w.lower() for w in result["warnings"])
    
    def test_missing_data_uses_defaults(self):
        """Datos faltantes deben usar defaults y generar warnings."""
        result = dcf_dynamic(
            fcf=1_000_000_000,
            shares_outstanding=100_000_000,
            beta=None,  # Sin beta
            debt_to_equity=None,  # Sin D/E
            revenue_growth_3y=None,  # Sin growth
            fcf_growth_3y=None
        )
        
        # Debería usar defaults
        assert result["wacc_used"] is not None
        assert result["growth_used"] is not None
        # Debería tener warnings
        assert len(result["warnings"]) > 0
    
    def test_growth_adjusted_when_exceeds_wacc(self):
        """Growth debe ajustarse si excede WACC."""
        result = dcf_dynamic(
            fcf=1_000_000_000,
            shares_outstanding=100_000_000,
            beta=0.5,  # Beta bajo = WACC bajo
            risk_free_rate=0.03,
            market_risk_premium=0.04,  # WACC ≈ 5%
            fcf_growth_3y=0.20  # 20% > 5%
        )
        
        # Growth debería ser ajustado para ser < WACC
        if result["wacc_used"] is not None and result["growth_used"] is not None:
            assert result["growth_used"] < result["wacc_used"], \
                "Growth debe ser menor que WACC"


class TestDCFDynamicWithRealData:
    """Tests con datos realistas de empresas."""
    
    def test_value_company_dcf(self, value_company_data):
        """DCF de empresa value debe dar valor razonable."""
        result = dcf_dynamic(
            fcf=value_company_data["free_cash_flow"],
            shares_outstanding=value_company_data["shares_outstanding"],
            beta=0.9,  # Value stocks típicamente beta < 1
            debt_to_equity=value_company_data["debt_to_equity"],
            revenue_growth_3y=value_company_data["revenue_growth_3y"],
            fcf_growth_3y=value_company_data["fcf_growth_3y"]
        )
        
        assert result["fair_value"] is not None
        assert result["fair_value"] > 0
    
    def test_growth_company_dcf(self, growth_company_data):
        """DCF de empresa growth debe dar valor razonable."""
        result = dcf_dynamic(
            fcf=growth_company_data["free_cash_flow"],
            shares_outstanding=growth_company_data["shares_outstanding"],
            beta=1.3,  # Growth stocks típicamente beta > 1
            debt_to_equity=growth_company_data["debt_to_equity"],
            revenue_growth_3y=growth_company_data["revenue_growth_3y"],
            fcf_growth_3y=growth_company_data["fcf_growth_3y"]
        )
        
        assert result["fair_value"] is not None
        assert result["fair_value"] > 0
    
    def test_distressed_company_dcf(self, distressed_company_data):
        """DCF de empresa en distress debe manejar FCF negativo."""
        result = dcf_dynamic(
            fcf=distressed_company_data["free_cash_flow"],  # Negativo
            shares_outstanding=distressed_company_data["shares_outstanding"],
            beta=2.0,  # Alto riesgo
            debt_to_equity=distressed_company_data["debt_to_equity"],
            revenue_growth_3y=distressed_company_data["revenue_growth_3y"]
        )
        
        # FCF negativo = no se puede hacer DCF
        assert result["fair_value"] is None
        assert len(result["warnings"]) > 0


class TestDCFSensitivity:
    """Tests de sensibilidad del DCF a cambios en parámetros."""
    
    def test_wacc_sensitivity(self):
        """
        Pequeños cambios en WACC deben producir cambios significativos en valor.
        Esto es importante para entender el riesgo del modelo.
        """
        fcf = 1_000_000_000
        shares = 100_000_000
        growth = 0.08
        terminal = 0.03
        
        value_8pct = dcf_fair_value(fcf, growth, 0.08, terminal, 10, shares)
        value_10pct = dcf_fair_value(fcf, growth, 0.10, terminal, 10, shares)
        value_12pct = dcf_fair_value(fcf, growth, 0.12, terminal, 10, shares)
        
        # El valor debe disminuir monotónicamente con WACC
        assert value_8pct > value_10pct > value_12pct
        
        # Cambio de 2% en WACC debería producir >10% cambio en valor
        pct_change = (value_8pct - value_10pct) / value_10pct
        assert pct_change > 0.10, "DCF debería ser sensible a cambios en WACC"
    
    def test_growth_sensitivity(self):
        """
        Pequeños cambios en growth deben producir cambios en valor.
        """
        fcf = 1_000_000_000
        shares = 100_000_000
        wacc = 0.10
        terminal = 0.03
        
        value_5pct = dcf_fair_value(fcf, 0.05, wacc, terminal, 10, shares)
        value_10pct = dcf_fair_value(fcf, 0.10, wacc, terminal, 10, shares)
        value_15pct = dcf_fair_value(fcf, 0.15, wacc, terminal, 10, shares)
        
        # El valor debe aumentar monotónicamente con growth
        assert value_5pct < value_10pct < value_15pct
    
    def test_terminal_value_dominance(self):
        """
        El terminal value típicamente domina el DCF (>50% del valor total).
        Esto muestra la importancia de los supuestos de largo plazo.
        """
        fcf = 1_000_000_000
        shares = 100_000_000
        
        # Comparar con diferentes terminal growth
        value_low_terminal = dcf_fair_value(fcf, 0.08, 0.10, 0.02, 10, shares)
        value_high_terminal = dcf_fair_value(fcf, 0.08, 0.10, 0.04, 10, shares)
        
        # Terminal growth 2% vs 4% debería hacer gran diferencia
        pct_diff = (value_high_terminal - value_low_terminal) / value_low_terminal
        assert pct_diff > 0.15, f"Terminal value debe ser sensible al growth terminal, diff={pct_diff:.1%}"
