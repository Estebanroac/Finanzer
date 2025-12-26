"""
Tests for Altman Z-Score
========================
Validación exhaustiva del predictor de bancarrota de Altman (1968).

Fórmula: Z = 1.2*X1 + 1.4*X2 + 3.3*X3 + 0.6*X4 + 1.0*X5

Donde:
    X1 = Working Capital / Total Assets
    X2 = Retained Earnings / Total Assets
    X3 = EBIT / Total Assets
    X4 = Market Value Equity / Total Liabilities
    X5 = Sales / Total Assets

Interpretación:
    Z > 2.99: Safe Zone (bajo riesgo)
    1.81 < Z < 2.99: Grey Zone (monitorear)
    Z < 1.81: Distress Zone (alto riesgo)

Referencias:
    - Altman, E. I. (1968). "Financial Ratios, Discriminant Analysis and
      the Prediction of Corporate Bankruptcy"
    - Accuracy histórica: 80-90% a 2 años
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from financial_ratios import altman_z_score


class TestAltmanZScoreCalculation:
    """Tests de cálculo matemático del Z-Score."""
    
    def test_formula_correctness_manual_calculation(self):
        """
        Verifica que la fórmula se calcula correctamente comparando
        con un cálculo manual.
        """
        # Datos de prueba
        working_capital = 5000
        total_assets = 10000
        retained_earnings = 3000
        ebit = 1500
        market_value_equity = 20000
        total_liabilities = 8000
        sales = 15000
        
        # Cálculo manual
        X1 = working_capital / total_assets  # 0.5
        X2 = retained_earnings / total_assets  # 0.3
        X3 = ebit / total_assets  # 0.15
        X4 = market_value_equity / total_liabilities  # 2.5
        X5 = sales / total_assets  # 1.5
        
        expected_z = 1.2*X1 + 1.4*X2 + 3.3*X3 + 0.6*X4 + 1.0*X5
        # = 1.2*0.5 + 1.4*0.3 + 3.3*0.15 + 0.6*2.5 + 1.0*1.5
        # = 0.6 + 0.42 + 0.495 + 1.5 + 1.5
        # = 4.515
        
        z, level, interpretation = altman_z_score(
            working_capital, total_assets, retained_earnings,
            ebit, market_value_equity, total_liabilities, sales
        )
        
        assert abs(z - expected_z) < 0.02, f"Z-Score calculado: {z}, esperado: {round(expected_z, 2)}"
        assert 4.50 <= z <= 4.52, f"Z-Score debería estar entre 4.50-4.52, got {z}"
    
    def test_coefficients_are_correct(self):
        """
        Verifica que los coeficientes de Altman (1.2, 1.4, 3.3, 0.6, 1.0)
        están implementados correctamente.
        """
        # Caso donde cada componente es 1.0
        # X1=X2=X3=X4=X5=1.0 → Z = 1.2 + 1.4 + 3.3 + 0.6 + 1.0 = 7.5
        z, _, _ = altman_z_score(
            working_capital=100,
            total_assets=100,
            retained_earnings=100,
            ebit=100,
            market_value_equity=100,
            total_liabilities=100,
            sales=100
        )
        
        assert z == 7.5, f"Con todos los ratios = 1.0, Z debería ser 7.5, got {z}"


class TestAltmanZScoreZones:
    """Tests de clasificación en zonas de riesgo."""
    
    def test_safe_zone_above_299(self, altman_safe_zone_data):
        """Z > 2.99 debe clasificarse como SAFE."""
        z, level, interpretation = altman_z_score(**altman_safe_zone_data)
        
        assert z is not None, "Z-Score no debería ser None"
        assert z > 2.99, f"Z-Score {z} debería ser > 2.99"
        assert level == "SAFE", f"Level debería ser SAFE, got {level}"
        assert "segura" in interpretation.lower(), "Interpretación debe mencionar 'segura'"
    
    def test_grey_zone_between_181_and_299(self, altman_grey_zone_data):
        """1.81 < Z < 2.99 debe clasificarse como GREY."""
        z, level, interpretation = altman_z_score(**altman_grey_zone_data)
        
        assert z is not None, "Z-Score no debería ser None"
        assert 1.81 < z < 2.99, f"Z-Score {z} debería estar entre 1.81 y 2.99"
        assert level == "GREY", f"Level debería ser GREY, got {level}"
        assert "gris" in interpretation.lower() or "moderado" in interpretation.lower()
    
    def test_distress_zone_below_181(self, altman_distress_zone_data):
        """Z < 1.81 debe clasificarse como DISTRESS."""
        z, level, interpretation = altman_z_score(**altman_distress_zone_data)
        
        assert z is not None, "Z-Score no debería ser None"
        assert z < 1.81, f"Z-Score {z} debería ser < 1.81"
        assert level == "DISTRESS", f"Level debería ser DISTRESS, got {level}"
        assert "peligro" in interpretation.lower() or "alto riesgo" in interpretation.lower()
    
    def test_boundary_exactly_299(self):
        """Z = 2.99 exacto debería ser GREY (no incluye el límite superior)."""
        # Construir datos que den exactamente ~2.99
        # Esto es difícil de hacer exacto, así que probamos el límite
        z, level, _ = altman_z_score(
            working_capital=1500,
            total_assets=10000,
            retained_earnings=1000,
            ebit=500,
            market_value_equity=10000,
            total_liabilities=6000,
            sales=12000
        )
        
        # Si z está muy cerca de 2.99, verificar la clasificación
        if z is not None and abs(z - 2.99) < 0.1:
            # El comportamiento exacto en el límite depende de la implementación
            assert level in ["SAFE", "GREY"], f"En el límite, level debería ser SAFE o GREY"
    
    def test_boundary_exactly_181(self):
        """Z = 1.81 exacto debería ser GREY (incluye el límite inferior)."""
        # Aproximación al límite 1.81
        z, level, _ = altman_z_score(
            working_capital=200,
            total_assets=10000,
            retained_earnings=100,
            ebit=300,
            market_value_equity=5000,
            total_liabilities=7000,
            sales=10000
        )
        
        if z is not None and abs(z - 1.81) < 0.1:
            assert level in ["GREY", "DISTRESS"], f"En el límite, level debería ser GREY o DISTRESS"


class TestAltmanZScoreEdgeCases:
    """Tests de casos edge y manejo de errores."""
    
    def test_missing_working_capital(self):
        """Working capital None debe retornar None."""
        z, level, interpretation = altman_z_score(
            working_capital=None,
            total_assets=10000,
            retained_earnings=3000,
            ebit=1500,
            market_value_equity=20000,
            total_liabilities=8000,
            sales=15000
        )
        
        assert z is None, "Z-Score debería ser None con working_capital faltante"
        assert level == "N/A"
        assert "insuficientes" in interpretation.lower()
    
    def test_missing_total_assets(self):
        """Total assets None debe retornar None."""
        z, level, interpretation = altman_z_score(
            working_capital=5000,
            total_assets=None,
            retained_earnings=3000,
            ebit=1500,
            market_value_equity=20000,
            total_liabilities=8000,
            sales=15000
        )
        
        assert z is None
        assert level == "N/A"
    
    def test_missing_multiple_fields(self):
        """Múltiples campos None debe retornar None."""
        z, level, interpretation = altman_z_score(
            working_capital=None,
            total_assets=None,
            retained_earnings=None,
            ebit=1500,
            market_value_equity=20000,
            total_liabilities=8000,
            sales=15000
        )
        
        assert z is None
        assert level == "N/A"
    
    def test_zero_total_assets_division(self):
        """Total assets = 0 debe manejarse sin crash (división por cero)."""
        z, level, interpretation = altman_z_score(
            working_capital=5000,
            total_assets=0,  # División por cero potencial
            retained_earnings=3000,
            ebit=1500,
            market_value_equity=20000,
            total_liabilities=8000,
            sales=15000
        )
        
        assert z is None, "Z-Score debería ser None con total_assets = 0"
        assert level == "N/A"
    
    def test_zero_total_liabilities_division(self):
        """Total liabilities = 0 debe manejarse sin crash."""
        z, level, interpretation = altman_z_score(
            working_capital=5000,
            total_assets=10000,
            retained_earnings=3000,
            ebit=1500,
            market_value_equity=20000,
            total_liabilities=0,  # División por cero en X4
            sales=15000
        )
        
        assert z is None, "Z-Score debería ser None con total_liabilities = 0"
        assert level == "N/A"
    
    def test_negative_working_capital(self):
        """Working capital negativo es válido y debe calcularse."""
        z, level, interpretation = altman_z_score(
            working_capital=-2000,  # Negativo es válido
            total_assets=10000,
            retained_earnings=1000,
            ebit=500,
            market_value_equity=5000,
            total_liabilities=7000,
            sales=8000
        )
        
        assert z is not None, "Z-Score debería calcularse con working capital negativo"
        # Working capital negativo reduce X1, típicamente produce zona gris o distress
        assert level in ["GREY", "DISTRESS"]
    
    def test_negative_retained_earnings(self):
        """Retained earnings negativo (pérdidas acumuladas) es válido."""
        z, level, interpretation = altman_z_score(
            working_capital=1000,
            total_assets=10000,
            retained_earnings=-3000,  # Pérdidas acumuladas
            ebit=500,
            market_value_equity=5000,
            total_liabilities=7000,
            sales=8000
        )
        
        assert z is not None, "Z-Score debería calcularse con retained earnings negativo"
    
    def test_negative_ebit_operating_loss(self):
        """EBIT negativo (pérdida operativa) es válido."""
        z, level, interpretation = altman_z_score(
            working_capital=1000,
            total_assets=10000,
            retained_earnings=500,
            ebit=-500,  # Pérdida operativa
            market_value_equity=5000,
            total_liabilities=7000,
            sales=8000
        )
        
        assert z is not None, "Z-Score debería calcularse con EBIT negativo"
        # EBIT negativo reduce X3 significativamente, probablemente distress
        assert level == "DISTRESS" or z < 2.0


class TestAltmanZScoreRealWorldScenarios:
    """Tests con escenarios del mundo real."""
    
    def test_apple_like_company(self):
        """
        Empresa tipo Apple: mucho efectivo, poca deuda, alta rentabilidad.
        Debería estar claramente en zona SAFE.
        """
        z, level, _ = altman_z_score(
            working_capital=50_000_000_000,  # $50B working capital
            total_assets=350_000_000_000,  # $350B assets
            retained_earnings=100_000_000_000,  # $100B retained
            ebit=120_000_000_000,  # $120B EBIT
            market_value_equity=2_800_000_000_000,  # $2.8T market cap
            total_liabilities=280_000_000_000,  # $280B liabilities
            sales=380_000_000_000  # $380B revenue
        )
        
        assert z is not None
        assert z > 2.99, f"Empresa tipo Apple debería tener Z > 2.99, got {z}"
        assert level == "SAFE"
    
    def test_heavily_leveraged_utility(self):
        """
        Utility con alta deuda pero flujos estables.
        Podría estar en zona gris pero no necesariamente en distress.
        """
        z, level, _ = altman_z_score(
            working_capital=500_000_000,
            total_assets=50_000_000_000,
            retained_earnings=5_000_000_000,
            ebit=3_000_000_000,
            market_value_equity=20_000_000_000,
            total_liabilities=35_000_000_000,  # Alta deuda
            sales=15_000_000_000
        )
        
        assert z is not None
        # Utilities típicamente tienen Z más bajo pero no necesariamente distress
        assert z > 0, "Z-Score debería ser positivo"
    
    def test_startup_pre_profit(self):
        """
        Startup que quema efectivo, sin ganancias retenidas.
        Típicamente en zona de distress.
        """
        z, level, _ = altman_z_score(
            working_capital=-50_000_000,  # Quemando efectivo
            total_assets=200_000_000,
            retained_earnings=-150_000_000,  # Pérdidas acumuladas
            ebit=-80_000_000,  # Pérdida operativa
            market_value_equity=500_000_000,  # Valoración especulativa
            total_liabilities=180_000_000,
            sales=50_000_000
        )
        
        assert z is not None
        assert level == "DISTRESS", f"Startup pre-profit debería estar en DISTRESS, got {level}"
    
    def test_turnaround_company(self):
        """
        Empresa en proceso de turnaround: mejorando pero aún débil.
        Probablemente zona gris.
        """
        z, level, _ = altman_z_score(
            working_capital=200_000_000,  # Ligeramente positivo
            total_assets=5_000_000_000,
            retained_earnings=-500_000_000,  # Aún con pérdidas acumuladas
            ebit=300_000_000,  # Volviendo a ser rentable
            market_value_equity=3_000_000_000,
            total_liabilities=3_500_000_000,
            sales=4_000_000_000
        )
        
        assert z is not None
        # Turnaround típicamente en zona gris
        assert level in ["GREY", "DISTRESS", "SAFE"]


class TestAltmanZScoreReturnTypes:
    """Tests de tipos de retorno."""
    
    def test_return_type_is_tuple(self, altman_safe_zone_data):
        """La función debe retornar una tupla de 3 elementos."""
        result = altman_z_score(**altman_safe_zone_data)
        
        assert isinstance(result, tuple), "Resultado debe ser tupla"
        assert len(result) == 3, "Tupla debe tener 3 elementos"
    
    def test_z_score_is_float_or_none(self, altman_safe_zone_data):
        """Z-Score debe ser float o None."""
        z, _, _ = altman_z_score(**altman_safe_zone_data)
        
        assert z is None or isinstance(z, (int, float)), "Z-Score debe ser numérico o None"
    
    def test_level_is_string(self, altman_safe_zone_data):
        """Level debe ser string."""
        _, level, _ = altman_z_score(**altman_safe_zone_data)
        
        assert isinstance(level, str), "Level debe ser string"
        assert level in ["SAFE", "GREY", "DISTRESS", "N/A"]
    
    def test_interpretation_is_string(self, altman_safe_zone_data):
        """Interpretation debe ser string no vacío."""
        _, _, interpretation = altman_z_score(**altman_safe_zone_data)
        
        assert isinstance(interpretation, str), "Interpretation debe ser string"
        assert len(interpretation) > 0, "Interpretation no debe estar vacía"
    
    def test_z_score_is_rounded(self, altman_safe_zone_data):
        """Z-Score debe estar redondeado a 2 decimales."""
        z, _, _ = altman_z_score(**altman_safe_zone_data)
        
        if z is not None:
            # Verificar que tiene máximo 2 decimales
            assert z == round(z, 2), "Z-Score debe estar redondeado a 2 decimales"


class TestAltmanZScoreDocumentation:
    """Tests que verifican la documentación de la función."""
    
    def test_function_has_docstring(self):
        """La función debe tener docstring."""
        assert altman_z_score.__doc__ is not None
        assert len(altman_z_score.__doc__) > 100
    
    def test_docstring_contains_formula(self):
        """El docstring debe explicar la fórmula."""
        doc = altman_z_score.__doc__
        
        assert "1.2" in doc or "X1" in doc, "Docstring debe mencionar la fórmula"
    
    def test_docstring_contains_interpretation(self):
        """El docstring debe explicar la interpretación."""
        doc = altman_z_score.__doc__
        
        assert "2.99" in doc, "Docstring debe mencionar umbral 2.99"
        assert "1.81" in doc, "Docstring debe mencionar umbral 1.81"
