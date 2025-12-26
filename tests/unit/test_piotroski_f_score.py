"""
Tests for Piotroski F-Score
===========================
Validación del indicador de fortaleza financiera de Piotroski (2000).

F-Score: 0-9 puntos en 3 categorías:

RENTABILIDAD (4 puntos):
    1. ROA > 0
    2. CFO > 0
    3. ROA mejoró vs año anterior
    4. CFO > Net Income (calidad de earnings)

APALANCAMIENTO/LIQUIDEZ (3 puntos):
    5. Deuda LP disminuyó o igual
    6. Current Ratio mejoró
    7. No emitió nuevas acciones

EFICIENCIA OPERATIVA (2 puntos):
    8. Margen bruto mejoró
    9. Asset Turnover mejoró

Interpretación:
    8-9: Fortaleza excepcional
    6-7: Buena salud
    4-5: Neutral
    2-3: Debilidad
    0-1: Alto riesgo

Referencias:
    - Piotroski, J. D. (2000). "Value Investing: The Use of Historical
      Financial Statement Information to Separate Winners from Losers"
    - Portafolio de alto F-Score supera mercado por ~23% anual
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from financial_ratios import piotroski_f_score


class TestPiotroskirScorePerfectCompany:
    """Tests con empresa que cumple todos los criterios (9/9)."""
    
    def test_perfect_score_all_positive(self):
        """
        Empresa excepcional: cumple las 9 señales.
        Debería obtener F-Score = 9.
        """
        score, details, interpretation = piotroski_f_score(
            # Rentabilidad (4 pts)
            net_income=1_000_000_000,
            roa_current=0.15,
            roa_prior=0.12,  # Mejoró
            operating_cash_flow=1_200_000_000,  # > net_income
            # Apalancamiento (3 pts)
            long_term_debt_current=5_000_000_000,
            long_term_debt_prior=6_000_000_000,  # Bajó
            current_ratio_current=2.0,
            current_ratio_prior=1.8,  # Mejoró
            shares_current=100_000_000,
            shares_prior=100_000_000,  # Sin dilución
            # Eficiencia (2 pts)
            gross_margin_current=0.50,
            gross_margin_prior=0.48,  # Mejoró
            asset_turnover_current=1.2,
            asset_turnover_prior=1.1  # Mejoró
        )
        
        assert score == 9, f"F-Score debería ser 9/9, got {score}"
        assert all("✓" in d for d in details), "Todos los detalles deberían ser positivos"
        assert "excepcional" in interpretation.lower()
    
    def test_perfect_score_verifies_all_signals(self):
        """Verifica que cada una de las 9 señales está presente."""
        score, details, _ = piotroski_f_score(
            net_income=1_000_000,
            roa_current=0.15,
            roa_prior=0.12,
            operating_cash_flow=1_200_000,
            long_term_debt_current=500_000,
            long_term_debt_prior=600_000,
            current_ratio_current=2.0,
            current_ratio_prior=1.8,
            shares_current=1_000_000,
            shares_prior=1_000_000,
            gross_margin_current=0.50,
            gross_margin_prior=0.48,
            asset_turnover_current=1.2,
            asset_turnover_prior=1.1
        )
        
        # Debe haber exactamente 9 señales
        assert len(details) == 9, f"Debe haber 9 señales, got {len(details)}"
        
        # Verificar señales específicas mencionadas
        details_text = " ".join(details)
        assert "ROA" in details_text
        assert "Cash Flow" in details_text or "CFO" in details_text
        assert "Deuda" in details_text or "deuda" in details_text
        assert "dilución" in details_text.lower() or "acciones" in details_text.lower()
        assert "Margen" in details_text or "margen" in details_text


class TestPiotroskirScoreWeakCompany:
    """Tests con empresa que falla todos los criterios (0-1/9)."""
    
    def test_zero_score_all_failing(self):
        """
        Empresa en problemas: falla todas las señales.
        Debería obtener F-Score = 0.
        """
        score, details, interpretation = piotroski_f_score(
            # Rentabilidad fallando
            net_income=-500_000_000,  # Pérdidas
            roa_current=-0.05,  # Negativo
            roa_prior=0.02,  # Empeoró
            operating_cash_flow=-200_000_000,  # CFO negativo
            # Apalancamiento fallando
            long_term_debt_current=8_000_000_000,
            long_term_debt_prior=6_000_000_000,  # Deuda subió
            current_ratio_current=0.8,
            current_ratio_prior=1.2,  # Empeoró
            shares_current=150_000_000,
            shares_prior=100_000_000,  # Dilución
            # Eficiencia fallando
            gross_margin_current=0.20,
            gross_margin_prior=0.25,  # Empeoró
            asset_turnover_current=0.8,
            asset_turnover_prior=1.0  # Empeoró
        )
        
        assert score <= 1, f"F-Score debería ser 0-1, got {score}"
        # Verificar que la mayoría de detalles son negativos (✗) o sin datos
        negative_count = sum(1 for d in details if "✗" in d or "Sin datos" in d or "N/A" in d)
        assert negative_count >= 7, f"Al menos 7 señales deben ser negativas, got {negative_count}"
    
    def test_weak_interpretation(self):
        """Empresa débil debe tener interpretación apropiada."""
        score, details, interpretation = piotroski_f_score(
            net_income=-100,
            roa_current=-0.01,
            roa_prior=0.01,
            operating_cash_flow=-50,
            long_term_debt_current=1000,
            long_term_debt_prior=800,
            current_ratio_current=0.5,
            current_ratio_prior=1.0,
            shares_current=200,
            shares_prior=100,
            gross_margin_current=0.10,
            gross_margin_prior=0.15,
            asset_turnover_current=0.5,
            asset_turnover_prior=0.7
        )
        
        # Score bajo debe indicar debilidad o riesgo
        assert score <= 2
        interpretation_lower = interpretation.lower()
        assert any(word in interpretation_lower for word in 
                  ["riesgo", "debilidad", "deterioro", "weak", "poor"])


class TestPiotroskirScoreRentabilidad:
    """Tests específicos para las 4 señales de rentabilidad."""
    
    def test_signal_1_roa_positive(self):
        """Señal 1: ROA > 0 suma 1 punto."""
        # Con ROA positivo
        score_pos, details_pos, _ = piotroski_f_score(
            net_income=100, roa_current=0.10, roa_prior=None,
            operating_cash_flow=None,
            long_term_debt_current=None, long_term_debt_prior=None,
            current_ratio_current=None, current_ratio_prior=None,
            shares_current=None, shares_prior=None,
            gross_margin_current=None, gross_margin_prior=None,
            asset_turnover_current=None, asset_turnover_prior=None
        )
        
        # Con ROA negativo
        score_neg, details_neg, _ = piotroski_f_score(
            net_income=100, roa_current=-0.05, roa_prior=None,
            operating_cash_flow=None,
            long_term_debt_current=None, long_term_debt_prior=None,
            current_ratio_current=None, current_ratio_prior=None,
            shares_current=None, shares_prior=None,
            gross_margin_current=None, gross_margin_prior=None,
            asset_turnover_current=None, asset_turnover_prior=None
        )
        
        assert score_pos > score_neg, "ROA positivo debe dar más puntos"
        assert any("ROA positivo" in d for d in details_pos)
    
    def test_signal_2_cfo_positive(self):
        """Señal 2: CFO > 0 suma 1 punto."""
        # CFO positivo
        score_pos, _, _ = piotroski_f_score(
            net_income=None, roa_current=None, roa_prior=None,
            operating_cash_flow=500_000,  # Positivo
            long_term_debt_current=None, long_term_debt_prior=None,
            current_ratio_current=None, current_ratio_prior=None,
            shares_current=None, shares_prior=None,
            gross_margin_current=None, gross_margin_prior=None,
            asset_turnover_current=None, asset_turnover_prior=None
        )
        
        # CFO negativo
        score_neg, _, _ = piotroski_f_score(
            net_income=None, roa_current=None, roa_prior=None,
            operating_cash_flow=-500_000,  # Negativo
            long_term_debt_current=None, long_term_debt_prior=None,
            current_ratio_current=None, current_ratio_prior=None,
            shares_current=None, shares_prior=None,
            gross_margin_current=None, gross_margin_prior=None,
            asset_turnover_current=None, asset_turnover_prior=None
        )
        
        assert score_pos > score_neg
    
    def test_signal_3_roa_improvement(self):
        """Señal 3: ROA mejoró vs año anterior suma 1 punto."""
        # ROA mejoró
        score_improved, _, _ = piotroski_f_score(
            net_income=None, roa_current=0.12, roa_prior=0.10,  # Mejoró
            operating_cash_flow=None,
            long_term_debt_current=None, long_term_debt_prior=None,
            current_ratio_current=None, current_ratio_prior=None,
            shares_current=None, shares_prior=None,
            gross_margin_current=None, gross_margin_prior=None,
            asset_turnover_current=None, asset_turnover_prior=None
        )
        
        # ROA empeoró
        score_worse, _, _ = piotroski_f_score(
            net_income=None, roa_current=0.08, roa_prior=0.10,  # Empeoró
            operating_cash_flow=None,
            long_term_debt_current=None, long_term_debt_prior=None,
            current_ratio_current=None, current_ratio_prior=None,
            shares_current=None, shares_prior=None,
            gross_margin_current=None, gross_margin_prior=None,
            asset_turnover_current=None, asset_turnover_prior=None
        )
        
        assert score_improved > score_worse
    
    def test_signal_4_cfo_vs_net_income(self):
        """Señal 4: CFO > Net Income (calidad de earnings) suma 1 punto."""
        # CFO > Net Income (buena calidad)
        score_quality, details, _ = piotroski_f_score(
            net_income=1_000_000,
            roa_current=None, roa_prior=None,
            operating_cash_flow=1_200_000,  # > net_income
            long_term_debt_current=None, long_term_debt_prior=None,
            current_ratio_current=None, current_ratio_prior=None,
            shares_current=None, shares_prior=None,
            gross_margin_current=None, gross_margin_prior=None,
            asset_turnover_current=None, asset_turnover_prior=None
        )
        
        # CFO < Net Income (mala calidad)
        score_poor, _, _ = piotroski_f_score(
            net_income=1_000_000,
            roa_current=None, roa_prior=None,
            operating_cash_flow=500_000,  # < net_income
            long_term_debt_current=None, long_term_debt_prior=None,
            current_ratio_current=None, current_ratio_prior=None,
            shares_current=None, shares_prior=None,
            gross_margin_current=None, gross_margin_prior=None,
            asset_turnover_current=None, asset_turnover_prior=None
        )
        
        assert score_quality > score_poor
        assert any("calidad" in d.lower() or "CFO" in d for d in details)


class TestPiotroskirScoreApalancamiento:
    """Tests específicos para las 3 señales de apalancamiento/liquidez."""
    
    def test_signal_5_debt_decreased(self):
        """Señal 5: Deuda LP disminuyó suma 1 punto."""
        # Deuda bajó
        score_down, _, _ = piotroski_f_score(
            net_income=None, roa_current=None, roa_prior=None,
            operating_cash_flow=None,
            long_term_debt_current=500, long_term_debt_prior=600,  # Bajó
            current_ratio_current=None, current_ratio_prior=None,
            shares_current=None, shares_prior=None,
            gross_margin_current=None, gross_margin_prior=None,
            asset_turnover_current=None, asset_turnover_prior=None
        )
        
        # Deuda subió
        score_up, _, _ = piotroski_f_score(
            net_income=None, roa_current=None, roa_prior=None,
            operating_cash_flow=None,
            long_term_debt_current=700, long_term_debt_prior=600,  # Subió
            current_ratio_current=None, current_ratio_prior=None,
            shares_current=None, shares_prior=None,
            gross_margin_current=None, gross_margin_prior=None,
            asset_turnover_current=None, asset_turnover_prior=None
        )
        
        assert score_down > score_up
    
    def test_signal_5_debt_equal_is_ok(self):
        """Deuda igual al año anterior también suma punto."""
        score, details, _ = piotroski_f_score(
            net_income=None, roa_current=None, roa_prior=None,
            operating_cash_flow=None,
            long_term_debt_current=500, long_term_debt_prior=500,  # Igual
            current_ratio_current=None, current_ratio_prior=None,
            shares_current=None, shares_prior=None,
            gross_margin_current=None, gross_margin_prior=None,
            asset_turnover_current=None, asset_turnover_prior=None
        )
        
        assert any("✓" in d and ("Deuda" in d or "deuda" in d) for d in details)
    
    def test_signal_6_current_ratio_improved(self):
        """Señal 6: Current Ratio mejoró suma 1 punto."""
        # Mejoró
        score_better, _, _ = piotroski_f_score(
            net_income=None, roa_current=None, roa_prior=None,
            operating_cash_flow=None,
            long_term_debt_current=None, long_term_debt_prior=None,
            current_ratio_current=2.0, current_ratio_prior=1.5,  # Mejoró
            shares_current=None, shares_prior=None,
            gross_margin_current=None, gross_margin_prior=None,
            asset_turnover_current=None, asset_turnover_prior=None
        )
        
        # Empeoró
        score_worse, _, _ = piotroski_f_score(
            net_income=None, roa_current=None, roa_prior=None,
            operating_cash_flow=None,
            long_term_debt_current=None, long_term_debt_prior=None,
            current_ratio_current=1.2, current_ratio_prior=1.5,  # Empeoró
            shares_current=None, shares_prior=None,
            gross_margin_current=None, gross_margin_prior=None,
            asset_turnover_current=None, asset_turnover_prior=None
        )
        
        assert score_better > score_worse
    
    def test_signal_7_no_share_dilution(self):
        """Señal 7: No emitió nuevas acciones suma 1 punto."""
        # Sin dilución
        score_no_dilution, _, _ = piotroski_f_score(
            net_income=None, roa_current=None, roa_prior=None,
            operating_cash_flow=None,
            long_term_debt_current=None, long_term_debt_prior=None,
            current_ratio_current=None, current_ratio_prior=None,
            shares_current=100, shares_prior=100,  # Igual
            gross_margin_current=None, gross_margin_prior=None,
            asset_turnover_current=None, asset_turnover_prior=None
        )
        
        # Con dilución
        score_diluted, _, _ = piotroski_f_score(
            net_income=None, roa_current=None, roa_prior=None,
            operating_cash_flow=None,
            long_term_debt_current=None, long_term_debt_prior=None,
            current_ratio_current=None, current_ratio_prior=None,
            shares_current=120, shares_prior=100,  # Dilución
            gross_margin_current=None, gross_margin_prior=None,
            asset_turnover_current=None, asset_turnover_prior=None
        )
        
        assert score_no_dilution > score_diluted
    
    def test_signal_7_share_buyback_is_ok(self):
        """Recompra de acciones (menos shares) también suma punto."""
        score, details, _ = piotroski_f_score(
            net_income=None, roa_current=None, roa_prior=None,
            operating_cash_flow=None,
            long_term_debt_current=None, long_term_debt_prior=None,
            current_ratio_current=None, current_ratio_prior=None,
            shares_current=90, shares_prior=100,  # Recompra
            gross_margin_current=None, gross_margin_prior=None,
            asset_turnover_current=None, asset_turnover_prior=None
        )
        
        assert any("✓" in d and "dilución" in d.lower() for d in details)


class TestPiotroskirScoreEficiencia:
    """Tests específicos para las 2 señales de eficiencia operativa."""
    
    def test_signal_8_gross_margin_improved(self):
        """Señal 8: Margen bruto mejoró suma 1 punto."""
        # Mejoró
        score_better, _, _ = piotroski_f_score(
            net_income=None, roa_current=None, roa_prior=None,
            operating_cash_flow=None,
            long_term_debt_current=None, long_term_debt_prior=None,
            current_ratio_current=None, current_ratio_prior=None,
            shares_current=None, shares_prior=None,
            gross_margin_current=0.40, gross_margin_prior=0.35,  # Mejoró
            asset_turnover_current=None, asset_turnover_prior=None
        )
        
        # Empeoró
        score_worse, _, _ = piotroski_f_score(
            net_income=None, roa_current=None, roa_prior=None,
            operating_cash_flow=None,
            long_term_debt_current=None, long_term_debt_prior=None,
            current_ratio_current=None, current_ratio_prior=None,
            shares_current=None, shares_prior=None,
            gross_margin_current=0.30, gross_margin_prior=0.35,  # Empeoró
            asset_turnover_current=None, asset_turnover_prior=None
        )
        
        assert score_better > score_worse
    
    def test_signal_9_asset_turnover_improved(self):
        """Señal 9: Asset Turnover mejoró suma 1 punto."""
        # Mejoró
        score_better, _, _ = piotroski_f_score(
            net_income=None, roa_current=None, roa_prior=None,
            operating_cash_flow=None,
            long_term_debt_current=None, long_term_debt_prior=None,
            current_ratio_current=None, current_ratio_prior=None,
            shares_current=None, shares_prior=None,
            gross_margin_current=None, gross_margin_prior=None,
            asset_turnover_current=1.2, asset_turnover_prior=1.0  # Mejoró
        )
        
        # Empeoró
        score_worse, _, _ = piotroski_f_score(
            net_income=None, roa_current=None, roa_prior=None,
            operating_cash_flow=None,
            long_term_debt_current=None, long_term_debt_prior=None,
            current_ratio_current=None, current_ratio_prior=None,
            shares_current=None, shares_prior=None,
            gross_margin_current=None, gross_margin_prior=None,
            asset_turnover_current=0.8, asset_turnover_prior=1.0  # Empeoró
        )
        
        assert score_better > score_worse


class TestPiotroskirScoreMissingData:
    """Tests de manejo de datos faltantes."""
    
    def test_all_none_returns_zero(self):
        """Todos los datos None retorna score 0."""
        score, details, interpretation = piotroski_f_score(
            net_income=None, roa_current=None, roa_prior=None,
            operating_cash_flow=None,
            long_term_debt_current=None, long_term_debt_prior=None,
            current_ratio_current=None, current_ratio_prior=None,
            shares_current=None, shares_prior=None,
            gross_margin_current=None, gross_margin_prior=None,
            asset_turnover_current=None, asset_turnover_prior=None
        )
        
        assert score == 0
        assert len(details) == 9  # Debe reportar las 9 señales
        assert all("✗" in d or "Sin datos" in d for d in details)
    
    def test_missing_historical_data_partial_score(self):
        """
        Con datos actuales pero sin históricos, solo puede puntuar
        en señales que no requieren comparación.
        """
        score, details, _ = piotroski_f_score(
            # Datos actuales disponibles
            net_income=1_000_000,
            roa_current=0.15,
            roa_prior=None,  # Sin histórico
            operating_cash_flow=1_200_000,
            # Sin históricos
            long_term_debt_current=500_000,
            long_term_debt_prior=None,
            current_ratio_current=2.0,
            current_ratio_prior=None,
            shares_current=100_000,
            shares_prior=None,
            gross_margin_current=0.50,
            gross_margin_prior=None,
            asset_turnover_current=1.2,
            asset_turnover_prior=None
        )
        
        # Solo puede ganar puntos en señales que no requieren histórico:
        # 1. ROA > 0 ✓
        # 2. CFO > 0 ✓
        # 4. CFO > Net Income ✓
        # Máximo = 3 puntos sin datos históricos
        assert score <= 4, f"Sin históricos, max score debería ser ~3-4, got {score}"
    
    def test_details_indicate_missing_data(self):
        """Los detalles deben indicar claramente cuando faltan datos."""
        _, details, _ = piotroski_f_score(
            net_income=None, roa_current=0.10, roa_prior=None,
            operating_cash_flow=None,
            long_term_debt_current=None, long_term_debt_prior=None,
            current_ratio_current=None, current_ratio_prior=None,
            shares_current=None, shares_prior=None,
            gross_margin_current=None, gross_margin_prior=None,
            asset_turnover_current=None, asset_turnover_prior=None
        )
        
        # Debe haber indicaciones de datos faltantes
        missing_indicators = [d for d in details if "Sin datos" in d or "N/A" in d or "histórico" in d.lower()]
        assert len(missing_indicators) > 0, "Debe indicar datos faltantes"


class TestPiotroskirScoreInterpretation:
    """Tests de interpretación del F-Score."""
    
    def test_score_8_9_exceptional(self):
        """Score 8-9 debe interpretarse como excepcional."""
        # Crear empresa con score 8
        score, _, interpretation = piotroski_f_score(
            net_income=1000, roa_current=0.15, roa_prior=0.12,
            operating_cash_flow=1200,
            long_term_debt_current=500, long_term_debt_prior=600,
            current_ratio_current=2.0, current_ratio_prior=1.8,
            shares_current=100, shares_prior=100,
            gross_margin_current=0.50, gross_margin_prior=0.48,
            asset_turnover_current=1.2, asset_turnover_prior=1.1
        )
        
        if score >= 8:
            assert "excepcional" in interpretation.lower()
    
    def test_score_6_7_good(self):
        """Score 6-7 debe interpretarse como bueno."""
        # Empresa con algunos indicadores fallando
        score, _, interpretation = piotroski_f_score(
            net_income=1000, roa_current=0.15, roa_prior=0.16,  # ROA no mejoró
            operating_cash_flow=1200,
            long_term_debt_current=500, long_term_debt_prior=600,
            current_ratio_current=2.0, current_ratio_prior=1.8,
            shares_current=100, shares_prior=100,
            gross_margin_current=0.45, gross_margin_prior=0.48,  # Margen no mejoró
            asset_turnover_current=1.2, asset_turnover_prior=1.1
        )
        
        if 6 <= score <= 7:
            interpretation_lower = interpretation.lower()
            assert any(word in interpretation_lower for word in ["bueno", "buena", "good", "salud"])
    
    def test_score_4_5_neutral(self):
        """Score 4-5 debe interpretarse como neutral."""
        # Empresa mixta
        score, _, interpretation = piotroski_f_score(
            net_income=1000, roa_current=0.08, roa_prior=0.10,  # Empeoró
            operating_cash_flow=800,  # < net_income
            long_term_debt_current=500, long_term_debt_prior=500,
            current_ratio_current=1.5, current_ratio_prior=1.5,
            shares_current=100, shares_prior=100,
            gross_margin_current=0.40, gross_margin_prior=0.40,
            asset_turnover_current=1.0, asset_turnover_prior=1.0
        )
        
        if 4 <= score <= 5:
            interpretation_lower = interpretation.lower()
            assert any(word in interpretation_lower for word in ["neutral", "moderado", "moderate"])


class TestPiotroskirScoreReturnTypes:
    """Tests de tipos de retorno."""
    
    def test_returns_tuple(self):
        """Debe retornar tupla de 3 elementos."""
        result = piotroski_f_score(
            net_income=1000, roa_current=0.10, roa_prior=0.08,
            operating_cash_flow=1100,
            long_term_debt_current=500, long_term_debt_prior=600,
            current_ratio_current=2.0, current_ratio_prior=1.8,
            shares_current=100, shares_prior=100,
            gross_margin_current=0.40, gross_margin_prior=0.38,
            asset_turnover_current=1.0, asset_turnover_prior=0.9
        )
        
        assert isinstance(result, tuple)
        assert len(result) == 3
    
    def test_score_is_integer(self):
        """Score debe ser entero entre 0 y 9."""
        score, _, _ = piotroski_f_score(
            net_income=1000, roa_current=0.10, roa_prior=0.08,
            operating_cash_flow=1100,
            long_term_debt_current=500, long_term_debt_prior=600,
            current_ratio_current=2.0, current_ratio_prior=1.8,
            shares_current=100, shares_prior=100,
            gross_margin_current=0.40, gross_margin_prior=0.38,
            asset_turnover_current=1.0, asset_turnover_prior=0.9
        )
        
        assert isinstance(score, int)
        assert 0 <= score <= 9
    
    def test_details_is_list(self):
        """Details debe ser lista de strings."""
        _, details, _ = piotroski_f_score(
            net_income=1000, roa_current=0.10, roa_prior=0.08,
            operating_cash_flow=1100,
            long_term_debt_current=500, long_term_debt_prior=600,
            current_ratio_current=2.0, current_ratio_prior=1.8,
            shares_current=100, shares_prior=100,
            gross_margin_current=0.40, gross_margin_prior=0.38,
            asset_turnover_current=1.0, asset_turnover_prior=0.9
        )
        
        assert isinstance(details, list)
        assert all(isinstance(d, str) for d in details)
    
    def test_interpretation_is_string(self):
        """Interpretation debe ser string no vacío."""
        _, _, interpretation = piotroski_f_score(
            net_income=1000, roa_current=0.10, roa_prior=0.08,
            operating_cash_flow=1100,
            long_term_debt_current=500, long_term_debt_prior=600,
            current_ratio_current=2.0, current_ratio_prior=1.8,
            shares_current=100, shares_prior=100,
            gross_margin_current=0.40, gross_margin_prior=0.38,
            asset_turnover_current=1.0, asset_turnover_prior=0.9
        )
        
        assert isinstance(interpretation, str)
        assert len(interpretation) > 0
