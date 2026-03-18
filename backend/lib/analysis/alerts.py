"""
Finanzer - Sistema de alertas y explicaciones.
Proporciona contexto educativo para cada tipo de alerta financiera.
"""

from typing import Dict


# Explicaciones detalladas por tipo de alerta
ALERT_EXPLANATIONS: Dict[tuple, str] = {
    # Valoración
    ("valoración", "p/e"): "El ratio P/E (Precio/Beneficio) compara el precio de la acción con sus ganancias por acción. Un P/E alto puede indicar sobrevaloración o expectativas de crecimiento.",
    ("valoración", "p/fcf"): "El ratio P/FCF (Precio/Flujo de Caja Libre) es más confiable que el P/E porque el flujo de caja es más difícil de manipular que las ganancias contables.",
    ("valoración", "ev/ebitda"): "EV/EBITDA compara el valor empresarial con las ganancias antes de intereses, impuestos y amortización. Útil para comparar empresas con diferentes estructuras de capital.",
    ("valoración", "peg"): "El PEG ajusta el P/E por el crecimiento esperado. Un PEG < 1 sugiere que la acción puede estar subvalorada para su tasa de crecimiento.",
    
    # Deuda
    ("deuda", "debt"): "El apalancamiento excesivo aumenta el riesgo financiero, especialmente en entornos de tasas de interés altas o recesiones económicas.",
    ("deuda", "interest"): "La cobertura de intereses mide la capacidad de la empresa para pagar sus gastos de interés. Un ratio bajo indica riesgo de incumplimiento.",
    ("deuda", "conservative"): "Un bajo nivel de deuda proporciona flexibilidad financiera y reduce el riesgo en ciclos económicos adversos.",
    
    # Rentabilidad
    ("rentabilidad", "roe"): "El ROE (Return on Equity) mide qué tan eficientemente la empresa genera beneficios con el capital de los accionistas. Un ROE consistentemente alto indica ventaja competitiva.",
    ("rentabilidad", "roa"): "El ROA (Return on Assets) indica qué tan eficientemente la empresa utiliza sus activos para generar beneficios.",
    ("rentabilidad", "margen"): "Los márgenes miden la rentabilidad en diferentes niveles del estado de resultados. Márgenes altos y estables indican poder de fijación de precios.",
    
    # Liquidez
    ("liquidez", "current"): "El Current Ratio mide la capacidad de pagar obligaciones de corto plazo. Un ratio < 1 puede indicar problemas de liquidez.",
    ("liquidez", "quick"): "El Quick Ratio excluye inventarios, dando una medida más estricta de liquidez inmediata.",
    
    # Flujo de Caja
    ("flujo", "fcf"): "El Flujo de Caja Libre es el dinero que queda después de operaciones e inversiones de capital. Es crucial para dividendos, recompras y reducción de deuda.",
    ("flujo", "negativo"): "Un FCF negativo persistente indica que la empresa está quemando efectivo y puede necesitar financiamiento externo.",
    ("flujo", "calidad"): "La relación FCF/Net Income indica la calidad de las ganancias. Un ratio bajo sugiere que las ganancias contables no se traducen en efectivo real.",
    
    # Crecimiento
    ("crecimiento", "revenue"): "El crecimiento de ingresos es fundamental para la creación de valor a largo plazo. Un crecimiento estancado puede indicar madurez del mercado o pérdida de competitividad.",
    ("crecimiento", "eps"): "El crecimiento del EPS (Beneficio por Acción) refleja no solo el crecimiento del negocio sino también la gestión del capital.",
    
    # Volatilidad
    ("volatilidad", "beta"): "Beta mide la volatilidad relativa al mercado. Beta > 1 significa más volátil que el mercado; Beta < 1 significa menos volátil.",
    ("volatilidad", "drawdown"): "El Maximum Drawdown mide la mayor caída desde un pico. Drawdowns grandes pueden indicar riesgo elevado.",
}

# Explicaciones genéricas por categoría
GENERIC_EXPLANATIONS: Dict[str, str] = {
    "valoración": "Las métricas de valoración comparan el precio de mercado con métricas fundamentales para determinar si una acción está cara o barata relativa a sus fundamentos.",
    "deuda": "Las métricas de deuda evalúan la estructura de capital y la capacidad de la empresa para cumplir con sus obligaciones financieras.",
    "rentabilidad": "Las métricas de rentabilidad miden la eficiencia de la empresa para convertir ingresos en beneficios.",
    "liquidez": "Las métricas de liquidez evalúan la capacidad de la empresa para cumplir con obligaciones de corto plazo.",
    "flujo": "Las métricas de flujo de caja evalúan la generación real de efectivo del negocio.",
    "crecimiento": "Las métricas de crecimiento evalúan la trayectoria de expansión del negocio.",
    "volatilidad": "Las métricas de volatilidad miden el riesgo de fluctuaciones en el precio de la acción.",
}


def get_alert_explanation(category: str, reason: str) -> str:
    """
    Genera una explicación detallada para cada tipo de alerta.
    
    Args:
        category: Categoría de la alerta (valoración, deuda, etc.)
        reason: Razón específica de la alerta
    
    Returns:
        Explicación educativa de la alerta
    """
    category_lower = category.lower()
    reason_lower = reason.lower()
    
    # Buscar explicación específica
    for (cat_key, reason_key), explanation in ALERT_EXPLANATIONS.items():
        if cat_key in category_lower and reason_key in reason_lower:
            return explanation
    
    # Buscar explicación genérica por categoría
    for cat_key, explanation in GENERIC_EXPLANATIONS.items():
        if cat_key in category_lower:
            return explanation
    
    # Fallback
    return "Esta métrica proporciona información relevante para evaluar la salud financiera y el potencial de inversión de la empresa."
