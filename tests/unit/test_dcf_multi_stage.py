"""
Tests for DCF Multi-Stage Model
===============================
Validación del modelo DCF de 3 etapas implementado en v2.3.

El modelo Multi-Stage es más realista porque:
1. Reconoce que el alto crecimiento no es sostenible indefinidamente
2. Modela la transición gradual hacia el crecimiento terminal
3. Proporciona análisis de sensibilidad automático
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from financial_ratios import dcf_multi_stage, dcf_multi_stage_dynamic, calculate_wacc


# =============================================================================
# TESTS BÁSICOS DE DCF MULTI-STAGE
# =============================================================================

class TestDCFMultiStageBasic:
    """Tests básicos de la función dcf_multi_stage."""
    
    def test_returns_dict_structure(self):
        """Debe retornar un diccionario con la estructura correcta."""
        result = dcf_multi_stage(
            fcf=1_000_000_000,
            shares_outstanding=100_000_000,
            high_growth_rate=0.15,
            discount_rate=0.10
        )
        
        assert isinstance(result, dict)
        assert "fair_value_per_share" in result
        assert "enterprise_value" in result
        assert "stages" in result
        assert "is_valid" in result
        assert "value_composition" in result
    
    def test_positive_fcf_returns_valid(self):
        """Con FCF positivo, debe retornar un resultado válido."""
        result = dcf_multi_stage(
            fcf=1_000_000_000,
            shares_outstanding=100_000_000,
            high_growth_rate=0.15,
            discount_rate=0.10
        )
        
        assert result["is_valid"] == True
        assert result["fair_value_per_share"] > 0
        assert result["enterprise_value"] > 0
    
    def test_negative_fcf_returns_invalid(self):
        """Con FCF negativo, debe retornar resultado inválido."""
        result = dcf_multi_stage(
            fcf=-500_000_000,
            shares_outstanding=100_000_000,
            high_growth_rate=0.15,
            discount_rate=0.10
        )
        
        assert result["is_valid"] == False
        assert result["fair_value_per_share"] is None
        assert len(result["warnings"]) > 0
    
    def test_none_inputs_handled(self):
        """Debe manejar inputs None sin crash."""
        result = dcf_multi_stage(
            fcf=None,
            shares_outstanding=100_000_000,
            high_growth_rate=0.15,
            discount_rate=0.10
        )
        
        assert result["is_valid"] == False
        
        result = dcf_multi_stage(
            fcf=1_000_000_000,
            shares_outstanding=None,
            high_growth_rate=0.15,
            discount_rate=0.10
        )
        
        assert result["is_valid"] == False
    
    def test_zero_shares_handled(self):
        """Debe manejar shares = 0 sin crash."""
        result = dcf_multi_stage(
            fcf=1_000_000_000,
            shares_outstanding=0,
            high_growth_rate=0.15,
            discount_rate=0.10
        )
        
        assert result["is_valid"] == False


# =============================================================================
# TESTS DE LÓGICA DE CRECIMIENTO
# =============================================================================

class TestDCFMultiStageGrowthLogic:
    """Tests de la lógica de crecimiento por etapas."""
    
    def test_higher_growth_higher_value(self):
        """Mayor growth rate debe dar mayor valor."""
        result_low = dcf_multi_stage(
            fcf=1_000_000_000,
            shares_outstanding=100_000_000,
            high_growth_rate=0.10,
            discount_rate=0.10
        )
        
        result_high = dcf_multi_stage(
            fcf=1_000_000_000,
            shares_outstanding=100_000_000,
            high_growth_rate=0.25,
            discount_rate=0.10
        )
        
        assert result_high["fair_value_per_share"] > result_low["fair_value_per_share"]
    
    def test_higher_discount_lower_value(self):
        """Mayor discount rate debe dar menor valor."""
        result_low = dcf_multi_stage(
            fcf=1_000_000_000,
            shares_outstanding=100_000_000,
            high_growth_rate=0.15,
            discount_rate=0.08
        )
        
        result_high = dcf_multi_stage(
            fcf=1_000_000_000,
            shares_outstanding=100_000_000,
            high_growth_rate=0.15,
            discount_rate=0.12
        )
        
        assert result_low["fair_value_per_share"] > result_high["fair_value_per_share"]
    
    def test_growth_rates_decay_stage1(self):
        """Las tasas de crecimiento deben decaer en etapa 1."""
        result = dcf_multi_stage(
            fcf=1_000_000_000,
            shares_outstanding=100_000_000,
            high_growth_rate=0.30,
            high_growth_years=5,
            discount_rate=0.10,
            decay_type="linear"
        )
        
        rates = result["stages"]["high_growth"]["rates"]
        
        # Verificar que hay decay (cada tasa <= la anterior)
        for i in range(1, len(rates)):
            assert rates[i] <= rates[i-1], f"Rate {i} ({rates[i]}) > rate {i-1} ({rates[i-1]})"
    
    def test_growth_rates_converge_to_terminal(self):
        """Las tasas deben converger al terminal growth."""
        terminal = 0.025
        
        result = dcf_multi_stage(
            fcf=1_000_000_000,
            shares_outstanding=100_000_000,
            high_growth_rate=0.30,
            terminal_growth=terminal,
            discount_rate=0.10
        )
        
        transition_rates = result["stages"]["transition"]["rates"]
        
        # La última tasa de transición debe estar cerca del terminal
        if transition_rates:
            assert abs(transition_rates[-1] - terminal) < 0.01
    
    def test_growth_capped_at_50_percent(self):
        """El growth rate debe estar capped en 50%."""
        result = dcf_multi_stage(
            fcf=1_000_000_000,
            shares_outstanding=100_000_000,
            high_growth_rate=0.80,  # 80% - irreal
            discount_rate=0.10
        )
        
        # Debe haber un warning sobre el cap
        assert any("capped" in w.lower() for w in result["warnings"])
        
        # Las tasas no deben exceder 50%
        rates = result["stages"]["high_growth"]["rates"]
        assert all(r <= 0.50 for r in rates)


# =============================================================================
# TESTS DE TIPOS DE DECAY
# =============================================================================

class TestDCFMultiStageDecayTypes:
    """Tests para los diferentes tipos de decay."""
    
    def test_linear_decay(self):
        """Decay lineal debe ser constante."""
        result = dcf_multi_stage(
            fcf=1_000_000_000,
            shares_outstanding=100_000_000,
            high_growth_rate=0.30,
            high_growth_years=5,
            discount_rate=0.10,
            decay_type="linear"
        )
        
        rates = result["stages"]["high_growth"]["rates"]
        if len(rates) >= 3:
            # Diferencia entre tasas consecutivas debe ser similar
            diff1 = rates[0] - rates[1]
            diff2 = rates[1] - rates[2]
            assert abs(diff1 - diff2) < 0.01
    
    def test_exponential_decay(self):
        """Decay exponencial debe ser más rápido al inicio."""
        result = dcf_multi_stage(
            fcf=1_000_000_000,
            shares_outstanding=100_000_000,
            high_growth_rate=0.30,
            high_growth_years=5,
            discount_rate=0.10,
            decay_type="exponential"
        )
        
        rates = result["stages"]["high_growth"]["rates"]
        if len(rates) >= 3:
            # Primera caída debe ser mayor que la última
            first_drop = rates[0] - rates[1]
            last_drop = rates[-2] - rates[-1]
            assert first_drop >= last_drop
    
    def test_step_decay(self):
        """Decay step debe mantener tasa constante en etapa 1."""
        result = dcf_multi_stage(
            fcf=1_000_000_000,
            shares_outstanding=100_000_000,
            high_growth_rate=0.20,
            high_growth_years=5,
            discount_rate=0.10,
            decay_type="step"
        )
        
        rates = result["stages"]["high_growth"]["rates"]
        # En step, todas las tasas de etapa 1 deben ser iguales
        assert all(r == rates[0] for r in rates)


# =============================================================================
# TESTS DE VALOR TERMINAL
# =============================================================================

class TestDCFMultiStageTerminalValue:
    """Tests relacionados con el valor terminal."""
    
    def test_terminal_value_calculated(self):
        """El valor terminal debe calcularse correctamente."""
        result = dcf_multi_stage(
            fcf=1_000_000_000,
            shares_outstanding=100_000_000,
            high_growth_rate=0.15,
            discount_rate=0.10,
            terminal_growth=0.025
        )
        
        assert result["stages"]["terminal"]["terminal_value"] is not None
        assert result["stages"]["terminal"]["terminal_value"] > 0
        assert result["stages"]["terminal"]["pv"] > 0
    
    def test_terminal_dominance_warning(self):
        """Debe advertir si el terminal value domina demasiado."""
        # Con growth bajo, terminal value domina
        result = dcf_multi_stage(
            fcf=1_000_000_000,
            shares_outstanding=100_000_000,
            high_growth_rate=0.03,  # Muy bajo
            discount_rate=0.10,
            terminal_growth=0.025
        )
        
        terminal_pct = result["value_composition"]["terminal_pct"]
        if terminal_pct > 75:
            assert any("terminal" in w.lower() for w in result["warnings"])
    
    def test_discount_equals_terminal_invalid(self):
        """Discount rate = terminal growth debe ser inválido."""
        result = dcf_multi_stage(
            fcf=1_000_000_000,
            shares_outstanding=100_000_000,
            high_growth_rate=0.15,
            discount_rate=0.03,
            terminal_growth=0.03  # Igual al discount rate
        )
        
        assert result["is_valid"] == False


# =============================================================================
# TESTS DE COMPOSICIÓN DE VALOR
# =============================================================================

class TestDCFMultiStageComposition:
    """Tests de la composición del valor por etapas."""
    
    def test_value_composition_sums_to_100(self):
        """La composición debe sumar aproximadamente 100%."""
        result = dcf_multi_stage(
            fcf=1_000_000_000,
            shares_outstanding=100_000_000,
            high_growth_rate=0.15,
            discount_rate=0.10
        )
        
        total = (
            result["value_composition"]["stage1_pct"] +
            result["value_composition"]["stage2_pct"] +
            result["value_composition"]["terminal_pct"]
        )
        
        assert abs(total - 100) < 0.5
    
    def test_high_growth_gives_more_stage1_absolute_value(self):
        """Mayor growth debe dar más valor ABSOLUTO en etapa 1."""
        result_low = dcf_multi_stage(
            fcf=1_000_000_000,
            shares_outstanding=100_000_000,
            high_growth_rate=0.05,
            discount_rate=0.10
        )
        
        result_high = dcf_multi_stage(
            fcf=1_000_000_000,
            shares_outstanding=100_000_000,
            high_growth_rate=0.30,
            discount_rate=0.10
        )
        
        # El valor absoluto de stage 1 debe ser mayor con high growth
        assert result_high["stages"]["high_growth"]["pv"] > result_low["stages"]["high_growth"]["pv"]


# =============================================================================
# TESTS DE MARGEN DE SEGURIDAD
# =============================================================================

class TestDCFMultiStageMOS:
    """Tests del margen de seguridad incorporado."""
    
    def test_margin_of_safety_reduces_value(self):
        """El margen de seguridad debe reducir el valor."""
        result_no_mos = dcf_multi_stage(
            fcf=1_000_000_000,
            shares_outstanding=100_000_000,
            high_growth_rate=0.15,
            discount_rate=0.10,
            margin_of_safety_pct=0.0
        )
        
        result_with_mos = dcf_multi_stage(
            fcf=1_000_000_000,
            shares_outstanding=100_000_000,
            high_growth_rate=0.15,
            discount_rate=0.10,
            margin_of_safety_pct=0.20  # 20% MoS
        )
        
        assert result_with_mos["fair_value_with_mos"] < result_no_mos["fair_value_per_share"]
        # Debe ser exactamente 80% del original
        expected = result_no_mos["fair_value_per_share"] * 0.80
        assert abs(result_with_mos["fair_value_with_mos"] - expected) < 0.01


# =============================================================================
# TESTS DE DCF MULTI-STAGE DINÁMICO
# =============================================================================

class TestDCFMultiStageDynamic:
    """Tests para la versión dinámica que calcula WACC y growth."""
    
    def test_dynamic_returns_valid_structure(self):
        """Debe retornar la estructura correcta."""
        result = dcf_multi_stage_dynamic(
            fcf=1_000_000_000,
            shares_outstanding=100_000_000,
            beta=1.2,
            revenue_growth_3y=0.15
        )
        
        assert "fair_value_per_share" in result
        assert "wacc_calculated" in result
        assert "growth_estimated" in result
        assert "growth_source" in result
        assert "sensitivity_analysis" in result
    
    def test_dynamic_calculates_wacc(self):
        """Debe calcular WACC basado en beta."""
        result = dcf_multi_stage_dynamic(
            fcf=1_000_000_000,
            shares_outstanding=100_000_000,
            beta=1.5,  # Alta beta
            debt_to_equity=0.5
        )
        
        assert result["wacc_calculated"] is not None
        assert 0.06 <= result["wacc_calculated"] <= 0.20
    
    def test_dynamic_uses_fcf_growth_priority(self):
        """Debe priorizar FCF growth sobre revenue growth."""
        result = dcf_multi_stage_dynamic(
            fcf=1_000_000_000,
            shares_outstanding=100_000_000,
            fcf_growth_3y=0.20,
            revenue_growth_3y=0.10
        )
        
        assert result["growth_source"] == "fcf_growth_3y"
        assert result["growth_estimated"] == 0.20
    
    def test_dynamic_falls_back_to_revenue(self):
        """Sin FCF growth, debe usar revenue growth."""
        result = dcf_multi_stage_dynamic(
            fcf=1_000_000_000,
            shares_outstanding=100_000_000,
            fcf_growth_3y=None,
            revenue_growth_3y=0.12
        )
        
        assert result["growth_source"] == "revenue_growth_3y"
    
    def test_dynamic_sensitivity_analysis(self):
        """Debe incluir análisis de sensibilidad."""
        result = dcf_multi_stage_dynamic(
            fcf=1_000_000_000,
            shares_outstanding=100_000_000,
            beta=1.0,
            revenue_growth_3y=0.15
        )
        
        if result["is_valid"]:
            assert result["sensitivity_analysis"] is not None
            assert "wacc_sensitivity" in result["sensitivity_analysis"]
            assert "growth_sensitivity" in result["sensitivity_analysis"]
    
    def test_dynamic_handles_negative_fcf(self):
        """Debe manejar FCF negativo correctamente."""
        result = dcf_multi_stage_dynamic(
            fcf=-500_000_000,
            shares_outstanding=100_000_000,
            beta=1.0
        )
        
        assert result["is_valid"] == False
        assert any("negativo" in w.lower() for w in result["warnings"])


# =============================================================================
# TESTS DE ESCENARIOS REALES
# =============================================================================

class TestDCFMultiStageRealScenarios:
    """Tests con escenarios realistas de empresas."""
    
    def test_high_growth_tech_company(self):
        """
        Escenario: Empresa tech de alto crecimiento (tipo NVDA)
        - FCF: $30B
        - Shares: 2.5B
        - Growth: 40%
        - Beta: 1.7
        """
        result = dcf_multi_stage_dynamic(
            fcf=30_000_000_000,
            shares_outstanding=2_500_000_000,
            beta=1.7,
            fcf_growth_3y=0.40,
            revenue_growth_3y=0.35
        )
        
        assert result["is_valid"] == True
        # El fair value debe ser razonable (no infinito ni negativo)
        assert 10 < result["fair_value_per_share"] < 1000
        # Growth debe estar capped
        assert result["growth_estimated"] <= 0.35
    
    def test_mature_stable_company(self):
        """
        Escenario: Empresa madura estable (tipo JNJ)
        - FCF: $20B
        - Shares: 2.5B
        - Growth: 5%
        - Beta: 0.7
        """
        result = dcf_multi_stage_dynamic(
            fcf=20_000_000_000,
            shares_outstanding=2_500_000_000,
            beta=0.7,
            fcf_growth_3y=0.05,
            revenue_growth_3y=0.03
        )
        
        assert result["is_valid"] == True
        # Terminal value debería dominar para empresa madura
        if result["model_result"]["value_composition"]["terminal_pct"] > 60:
            pass  # Esperado para empresas maduras
    
    def test_value_stock(self):
        """
        Escenario: Value stock con bajo crecimiento pero alto FCF yield
        - FCF: $10B
        - Shares: 500M
        - Growth: 3%
        - Beta: 0.9
        """
        result = dcf_multi_stage_dynamic(
            fcf=10_000_000_000,
            shares_outstanding=500_000_000,
            beta=0.9,
            fcf_growth_3y=0.03
        )
        
        assert result["is_valid"] == True
        # Fair value per share = EV / shares debería ser alto
        assert result["fair_value_per_share"] > 100


# =============================================================================
# TESTS DE CONSISTENCIA
# =============================================================================

class TestDCFMultiStageConsistency:
    """Tests de consistencia del modelo."""
    
    def test_deterministic_results(self):
        """El modelo debe ser determinístico."""
        params = {
            "fcf": 1_000_000_000,
            "shares_outstanding": 100_000_000,
            "high_growth_rate": 0.15,
            "discount_rate": 0.10
        }
        
        result1 = dcf_multi_stage(**params)
        result2 = dcf_multi_stage(**params)
        
        assert result1["fair_value_per_share"] == result2["fair_value_per_share"]
    
    def test_pv_sum_equals_enterprise_value(self):
        """La suma de PVs debe igualar el enterprise value."""
        result = dcf_multi_stage(
            fcf=1_000_000_000,
            shares_outstanding=100_000_000,
            high_growth_rate=0.15,
            discount_rate=0.10
        )
        
        pv_sum = (
            result["stages"]["high_growth"]["pv"] +
            result["stages"]["transition"]["pv"] +
            result["stages"]["terminal"]["pv"]
        )
        
        # Pueden diferir por redondeo
        assert abs(pv_sum - result["enterprise_value"]) < 1
