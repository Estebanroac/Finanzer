"""
Finanzer - Tooltips y explicaciones de métricas financieras.
Contiene las definiciones de todos los indicadores con rangos y contexto.
"""

# =============================================================================
# TOOLTIPS - Explicaciones de todos los indicadores
# =============================================================================

METRIC_TOOLTIPS = {
    # === VALORACIÓN ===
    "pe": {
        "nombre": "P/E (Precio/Beneficio)",
        "que_es": "Cuántos dólares pagas por cada dólar de ganancia anual.",
        "rangos": "• <15: Posiblemente barata\n• 15-25: Valoración típica\n• >25: Cara o alto crecimiento",
        "contexto": "Compara siempre con empresas del mismo sector."
    },
    "forward_pe": {
        "nombre": "Forward P/E (P/E Proyectado)",
        "que_es": "P/E basado en las ganancias esperadas del próximo año fiscal.",
        "rangos": "• <12: Muy barato\n• 12-20: Normal\n• >25: Expectativas altas",
        "contexto": "Más útil que P/E trailing para empresas en crecimiento."
    },
    "pb": {
        "nombre": "P/B (Precio/Valor en Libros)",
        "que_es": "Cuánto pagas en relación al valor contable de los activos.",
        "rangos": "• <1: Por debajo de valor contable\n• 1-3: Rango normal\n• >3: Prima alta sobre activos",
        "contexto": "Más útil para bancos y empresas con activos tangibles."
    },
    "ps": {
        "nombre": "P/S (Precio/Ventas)",
        "que_es": "Cuánto pagas por cada dólar de ventas.",
        "rangos": "• <1: Muy barato\n• 1-5: Normal\n• >10: Muy caro",
        "contexto": "Útil para empresas sin ganancias pero con ingresos."
    },
    "p_fcf": {
        "nombre": "P/FCF (Precio/Flujo de Caja)",
        "que_es": "Cuánto pagas por cada dólar de efectivo real generado.",
        "rangos": "• <15: Atractivo\n• 15-25: Normal\n• >25: Caro",
        "contexto": "Más confiable que P/E porque el efectivo es difícil de manipular."
    },
    "ev_ebitda": {
        "nombre": "EV/EBITDA",
        "que_es": "Valor empresarial vs ganancias operativas.",
        "rangos": "• <8: Barato\n• 8-12: Normal\n• >12: Caro",
        "contexto": "Mejor para comparar empresas con diferente deuda."
    },
    "peg": {
        "nombre": "PEG Ratio",
        "que_es": "P/E ajustado por crecimiento esperado.",
        "rangos": "• <1: Subvalorada para su growth ✓\n• =1: Valor justo\n• >1.5: Cara para su growth",
        "contexto": "PEG de 1 significa P/E justificado por crecimiento."
    },
    "fcf_yield": {
        "nombre": "FCF Yield",
        "que_es": "Rendimiento del flujo de caja como % del precio.",
        "rangos": "• >8%: Muy atractivo\n• 5-8%: Bueno\n• <3%: Bajo",
        "contexto": "Como el dividendo potencial. Mayor = mejor."
    },
    
    # === RENTABILIDAD ===
    "roe": {
        "nombre": "ROE (Retorno sobre Patrimonio)",
        "que_es": "Ganancia generada por cada dólar de los accionistas.",
        "rangos": "• >20%: Excelente ✓\n• 15-20%: Muy bueno\n• 10-15%: Aceptable\n• <10%: Bajo",
        "contexto": "Buffett busca ROE consistente >15%."
    },
    "roa": {
        "nombre": "ROA (Retorno sobre Activos)",
        "que_es": "Eficiencia usando activos para generar ganancias.",
        "rangos": "• >10%: Excelente\n• 5-10%: Bueno\n• <5%: Normal/Bajo",
        "contexto": "Varía por sector. Bancos ~1%, Tech más alto."
    },
    "roic": {
        "nombre": "ROIC (Retorno sobre Capital Invertido)",
        "que_es": "Rendimiento del capital total invertido.",
        "rangos": "• >15%: Excelente, crea valor ✓\n• 10-15%: Bueno\n• <WACC: Destruye valor ✗",
        "contexto": "Si ROIC > WACC, la empresa crea valor."
    },
    "margen_bruto": {
        "nombre": "Margen Bruto",
        "que_es": "% de ingresos después de costos de producción.",
        "rangos": "• >60%: Excelente (software)\n• 40-60%: Bueno\n• 20-40%: Normal\n• <20%: Bajo",
        "contexto": "Márgenes altos = ventaja competitiva."
    },
    "margen_operativo": {
        "nombre": "Margen Operativo",
        "que_es": "% de ingresos después de gastos operativos.",
        "rangos": "• >25%: Excelente\n• 15-25%: Muy bueno\n• 10-15%: Bueno\n• <10%: Bajo",
        "contexto": "Muestra eficiencia operativa."
    },
    "margen_neto": {
        "nombre": "Margen Neto",
        "que_es": "% de ventas que se convierte en ganancia final.",
        "rangos": "• >20%: Excelente\n• 10-20%: Muy bueno\n• 5-10%: Normal\n• <5%: Bajo",
        "contexto": "La línea final después de todo."
    },
    "margen_ebitda": {
        "nombre": "Margen EBITDA",
        "que_es": "% de ingresos como EBITDA (ganancia operativa + depreciación).",
        "rangos": "• >30%: Excelente\n• 20-30%: Bueno\n• 10-20%: Normal\n• <10%: Bajo",
        "contexto": "Útil para comparar empresas con diferentes políticas de depreciación."
    },
    
    # === SOLIDEZ FINANCIERA ===
    "current_ratio": {
        "nombre": "Current Ratio (Liquidez)",
        "que_es": "Capacidad de pagar deudas corto plazo con activos corrientes.",
        "rangos": "• >2: Muy sólido ✓\n• 1.5-2: Saludable\n• 1-1.5: Aceptable\n• <1: Riesgo ⚠️",
        "contexto": "<1 significa que no puede cubrir deudas próximas."
    },
    "quick_ratio": {
        "nombre": "Quick Ratio (Prueba Ácida)",
        "que_es": "Liquidez sin contar inventario (más conservador).",
        "rangos": "• >1.5: Excelente\n• 1-1.5: Bueno ✓\n• 0.5-1: Aceptable\n• <0.5: Riesgo ⚠️",
        "contexto": "Más estricto que current ratio."
    },
    "cash_ratio": {
        "nombre": "Cash Ratio",
        "que_es": "Solo efectivo vs deudas de corto plazo (el más conservador).",
        "rangos": "• >1: Puede pagar todo en efectivo\n• 0.5-1: Buena posición\n• 0.2-0.5: Normal\n• <0.2: Bajo",
        "contexto": "Muy conservador. Pocas empresas tienen >1."
    },
    "working_capital": {
        "nombre": "Working Capital (Capital de Trabajo)",
        "que_es": "Activos corrientes menos pasivos corrientes.",
        "rangos": "• Positivo: Puede operar día a día ✓\n• Negativo: Riesgo de liquidez ⚠️",
        "contexto": "Dinero disponible para operaciones diarias."
    },
    "debt_to_equity": {
        "nombre": "Deuda/Patrimonio (D/E)",
        "que_es": "Cuánta deuda por cada dólar de patrimonio.",
        "rangos": "• <0.5: Conservador ✓\n• 0.5-1: Normal\n• 1-2: Apalancado\n• >2: Muy apalancado ⚠️",
        "contexto": "Varía por sector. Bancos tienen D/E alto."
    },
    "debt_to_assets": {
        "nombre": "Deuda/Activos",
        "que_es": "Porcentaje de activos financiados con deuda.",
        "rangos": "• <30%: Conservador ✓\n• 30-50%: Normal\n• 50-70%: Alto\n• >70%: Muy alto ⚠️",
        "contexto": "Menor es generalmente mejor."
    },
    "net_debt_ebitda": {
        "nombre": "Deuda Neta/EBITDA",
        "que_es": "Años para pagar toda la deuda con ganancias operativas.",
        "rangos": "• <1: Casi sin deuda ✓\n• 1-2: Conservador\n• 2-3: Normal\n• >4: Alto riesgo ⚠️",
        "contexto": "Negativo = más efectivo que deuda."
    },
    "interest_coverage": {
        "nombre": "Cobertura de Intereses",
        "que_es": "Veces que puede pagar intereses con beneficio operativo.",
        "rangos": "• >10: Excelente ✓\n• 5-10: Bueno\n• 2-5: Aceptable\n• <2: Riesgo ⚠️",
        "contexto": "<1.5 es señal de alerta seria."
    },
    "total_debt": {
        "nombre": "Deuda Total",
        "que_es": "Suma de toda la deuda de corto y largo plazo.",
        "rangos": "Depende del tamaño de la empresa.",
        "contexto": "Comparar con equity y EBITDA para contexto."
    },
    "fcf": {
        "nombre": "Free Cash Flow (FCF)",
        "que_es": "Efectivo disponible después de operaciones e inversiones.",
        "rangos": "• Positivo: Genera efectivo ✓\n• Negativo: Quema efectivo",
        "contexto": "El dinero real que queda. Clave para dividendos y recompras."
    },
    "fcf_to_debt": {
        "nombre": "FCF/Deuda",
        "que_es": "Qué proporción de la deuda podría pagar con FCF anual.",
        "rangos": "• >25%: Excelente\n• 15-25%: Bueno\n• 5-15%: Normal\n• <5%: Bajo",
        "contexto": "Mayor = más capacidad de pago."
    },
    "cash_equivalents": {
        "nombre": "Cash & Equivalents",
        "que_es": "Efectivo disponible inmediatamente.",
        "rangos": "Depende del tamaño y sector.",
        "contexto": "Colchón para emergencias y oportunidades."
    },
    
    # === CRECIMIENTO ===
    "revenue_growth": {
        "nombre": "Crecimiento de Ingresos",
        "que_es": "Tasa anual de crecimiento de ventas.",
        "rangos": "• >20%: Alto crecimiento\n• 10-20%: Buen crecimiento\n• 5-10%: Moderado\n• <0%: Contracción ⚠️",
        "contexto": "Motor del valor a largo plazo."
    },
    "eps_growth": {
        "nombre": "Crecimiento de EPS",
        "que_es": "Crecimiento de ganancias por acción.",
        "rangos": "• >25%: Excelente\n• 15-25%: Muy bueno\n• 5-15%: Bueno\n• <0%: Decreciendo ⚠️",
        "contexto": "Más importante que crecimiento de ingresos."
    },
    "fcf_growth": {
        "nombre": "Crecimiento de FCF",
        "que_es": "Crecimiento del flujo de caja libre.",
        "rangos": "• >20%: Excelente\n• 10-20%: Bueno\n• 0-10%: Estable\n• <0%: Decreciendo",
        "contexto": "Crecimiento de efectivo real."
    },
    
    # === MODELOS DE VALORACIÓN ===
    "graham": {
        "nombre": "Número de Graham",
        "que_es": "Precio máximo que deberías pagar según Benjamin Graham, el padre del value investing. Usa una fórmula conservadora: √(22.5 × EPS × Book Value). Si el precio actual está por debajo de este número, la acción podría estar barata.",
        "rangos": "• Precio < Graham: Potencialmente subvalorada ✓\n• Precio ≈ Graham: Precio justo\n• Precio > Graham: Potencialmente sobrevalorada",
        "contexto": "Mejor para empresas estables con ganancias consistentes. No funciona bien con empresas tech de alto crecimiento o empresas con pérdidas."
    },
    "dcf": {
        "nombre": "DCF (Flujos Descontados)",
        "que_es": "Calcula cuánto vale la empresa hoy basándose en todo el dinero que generará en el futuro. Es como preguntar: '¿Cuánto pagaría hoy por todos los flujos de efectivo que esta empresa producirá en los próximos 10+ años?'. Se descuentan al presente usando el WACC.",
        "rangos": "• Precio < DCF: Oportunidad de compra ✓\n• Precio ≈ DCF (±15%): Valoración justa\n• Precio > DCF: Posiblemente cara",
        "contexto": "Modelo usado por analistas de Wall Street. Muy sensible a los supuestos de crecimiento y tasa de descuento. Pequeños cambios pueden alterar mucho el resultado."
    },
    "wacc": {
        "nombre": "WACC (Costo Promedio del Capital)",
        "que_es": "Es el retorno mínimo que la empresa necesita generar para satisfacer a sus inversores (accionistas) y acreedores (bancos). Combina el costo de la deuda y el costo del equity. Se usa como tasa de descuento en el modelo DCF.",
        "rangos": "• 5-7%: Empresa muy estable, bajo riesgo\n• 7-9%: Riesgo moderado (típico)\n• 9-12%: Riesgo elevado\n• >12%: Alto riesgo o mercado emergente",
        "contexto": "Un WACC alto significa que los flujos futuros valen menos hoy (mayor descuento). Empresas con mucha deuda o alta volatilidad tienen WACC más alto."
    },
    "margin_of_safety": {
        "nombre": "Margen de Seguridad",
        "que_es": "Es el 'colchón' entre el precio actual y el valor intrínseco calculado. Si una acción vale $100 según el DCF y cotiza a $70, tienes 30% de margen de seguridad. Este margen te protege si tus cálculos están equivocados.",
        "rangos": "• >30%: Excelente protección ✓\n• 15-30%: Buen margen\n• 0-15%: Margen pequeño\n• <0%: Sin margen (precio > valor)",
        "contexto": "Benjamin Graham recomendaba mínimo 30%. Warren Buffett busca márgenes amplios. A mayor incertidumbre sobre la empresa, mayor margen deberías exigir."
    },
    
    # === SCORES INSTITUCIONALES ===
    "altman_z": {
        "nombre": "Altman Z-Score",
        "que_es": "Fórmula creada por el profesor Edward Altman en 1968 para predecir si una empresa quebrará en los próximos 2 años. Combina 5 ratios financieros: liquidez, rentabilidad acumulada, rentabilidad operativa, valor de mercado vs deuda, y rotación de activos.",
        "rangos": "• >2.99: Zona Segura - Probabilidad de quiebra muy baja ✓\n• 1.81-2.99: Zona Gris - Precaución, monitorear ⚠️\n• <1.81: Zona de Peligro - Riesgo alto de problemas financieros 🚨",
        "contexto": "Ha demostrado 80-90% de precisión prediciendo quiebras. Funciona mejor con empresas manufactureras. Para bancos y empresas de servicios hay versiones modificadas."
    },
    "piotroski_f": {
        "nombre": "Piotroski F-Score",
        "que_es": "Sistema de puntuación creado por el profesor Joseph Piotroski. Evalúa 9 criterios de salud financiera: rentabilidad (4 puntos), apalancamiento/liquidez (3 puntos), y eficiencia operativa (2 puntos). Cada criterio cumplido suma 1 punto.",
        "rangos": "• 8-9: Fortaleza excepcional - Empresa muy sólida ✓✓\n• 6-7: Buena salud financiera ✓\n• 4-5: Salud neutral - Mixta\n• 0-3: Señales de debilidad ⚠️",
        "contexto": "Estudios muestran que acciones con F-Score alto (8-9) superan al mercado. Es especialmente útil para filtrar empresas 'value' y evitar trampas de valor."
    },
    
    # === DIVIDENDOS ===
    "dividend_yield": {
        "nombre": "Dividend Yield",
        "que_es": "% anual recibido en dividendos sobre el precio.",
        "rangos": "• >5%: Alto (verificar sostenibilidad)\n• 3-5%: Bueno\n• 1-3%: Moderado\n• <1%: Bajo",
        "contexto": "Yield muy alto puede indicar problemas."
    },
    "payout_ratio": {
        "nombre": "Payout Ratio",
        "que_es": "% de ganancias repartido como dividendo.",
        "rangos": "• <40%: Conservador ✓\n• 40-60%: Equilibrado\n• 60-80%: Alto\n• >80%: Insostenible ⚠️",
        "contexto": ">100% = paga más de lo que gana."
    },
    
    # === OTROS ===
    "beta": {
        "nombre": "Beta",
        "que_es": "Volatilidad vs el mercado (S&P 500).",
        "rangos": "• <0.8: Defensivo\n• 0.8-1.2: Similar al mercado\n• 1.2-1.5: Más volátil\n• >1.5: Muy volátil ⚠️",
        "contexto": "Beta 1.5 = si mercado sube 10%, acción sube ~15%."
    },
    "market_cap": {
        "nombre": "Market Cap",
        "que_es": "Valor total de la empresa según el mercado.",
        "rangos": "• >$200B: Mega cap\n• $10-200B: Large cap\n• $2-10B: Mid cap\n• <$2B: Small cap",
        "contexto": "Más grande = más estable, menos crecimiento."
    },
    "52w_high": {
        "nombre": "52 Week High",
        "que_es": "Precio más alto del último año.",
        "rangos": "Referencia para evaluar posición actual.",
        "contexto": "Cerca del high = momentum positivo o sobrevalorada."
    },
    "52w_low": {
        "nombre": "52 Week Low", 
        "que_es": "Precio más bajo del último año.",
        "rangos": "Referencia para evaluar posición actual.",
        "contexto": "Cerca del low = oportunidad o problemas."
    },
    "volume": {
        "nombre": "Volumen Promedio",
        "que_es": "Cantidad de acciones negociadas diariamente.",
        "rangos": "Mayor volumen = mayor liquidez.",
        "contexto": "Importante para entrar/salir de posiciones."
    },
    "ebitda": {
        "nombre": "EBITDA",
        "que_es": "Ganancias antes de intereses, impuestos, depreciación y amortización.",
        "rangos": "Positivo = operativamente rentable.",
        "contexto": "Proxy de flujo de caja operativo."
    },
    "eps": {
        "nombre": "EPS (Ganancias por Acción)",
        "que_es": "Beneficio neto dividido entre acciones.",
        "rangos": "Positivo = rentable. Mayor = mejor.",
        "contexto": "Base para calcular P/E."
    },
    "net_income": {
        "nombre": "Net Income (Ingreso Neto)",
        "que_es": "Ganancia final después de todos los gastos.",
        "rangos": "Positivo = rentable.",
        "contexto": "La línea final del estado de resultados."
    },
    
    # === REITs ===
    "ffo": {
        "nombre": "FFO (Funds From Operations)",
        "que_es": "Métrica principal para REITs. Ingreso neto + depreciación - ganancias por venta.",
        "formula": "Net Income + Depreciation - Gains on Property Sale",
        "rangos": "• Positivo: Operaciones saludables\n• Creciendo: REIT en expansión\n• Negativo: Problemas operativos",
        "contexto": "Más relevante que Net Income para REITs porque la depreciación inmobiliaria no refleja pérdida real de valor."
    },
    "p_ffo": {
        "nombre": "P/FFO (Precio/FFO)",
        "que_es": "Equivalente al P/E pero para REITs. Cuánto pagas por cada dólar de FFO.",
        "formula": "Precio ÷ FFO por Acción",
        "rangos": "• <12: Potencialmente barato\n• 12-18: Rango normal\n• >18: Caro o alta calidad",
        "contexto": "Para REITs, P/FFO es más relevante que P/E tradicional."
    },
    "ffo_payout": {
        "nombre": "FFO Payout Ratio",
        "que_es": "Porcentaje del FFO pagado como dividendo.",
        "formula": "Dividendos ÷ FFO × 100",
        "rangos": "• <80%: Sostenible con margen\n• 80-95%: Normal para REITs\n• >95%: Riesgo de recorte",
        "contexto": "REITs deben distribuir 90%+ de ingresos por ley. Un payout muy alto sobre FFO es riesgoso."
    },
}


# =============================================================================
# MAPEO DE LABELS A TOOLTIPS
# =============================================================================

LABEL_TO_TOOLTIP = {
    # Valoración (todas las variantes)
    "P/E": "pe", "P/E Ratio": "pe", "Forward P/E": "forward_pe", "Fwd P/E": "forward_pe",
    "P/B": "pb", "P/B Ratio": "pb", "P/Book": "pb",
    "P/S": "ps", "P/S Ratio": "ps",
    "P/FCF": "p_fcf", "P/FCF Ratio": "p_fcf",
    "EV/EBITDA": "ev_ebitda", 
    "PEG": "peg", "PEG Ratio": "peg",
    "FCF Yield": "fcf_yield", "Earnings Yield": "fcf_yield",
    
    # Rentabilidad
    "ROE": "roe", "ROA": "roa", "ROIC": "roic", "ROE 5Y Avg": "roe",
    "Margen Bruto": "margen_bruto", "Margen Operativo": "margen_operativo", 
    "Margen Neto": "margen_neto", "Margen EBITDA": "margen_ebitda",
    "EBITDA": "ebitda", "Ingreso Neto": "net_income", "EPS": "eps",
    
    # Liquidez
    "Current Ratio": "current_ratio", "Quick Ratio": "quick_ratio", 
    "Cash Ratio": "cash_ratio", "Working Capital": "working_capital",
    
    # Apalancamiento  
    "D/E": "debt_to_equity", "Deuda/Equity": "debt_to_equity", "Debt/Equity": "debt_to_equity",
    "Deuda/Activos": "debt_to_assets", "Debt/Assets": "debt_to_assets",
    "Deuda Neta/EBITDA": "net_debt_ebitda", "Deuda Total": "total_debt",
    "Net Debt/EBITDA": "net_debt_ebitda",
    
    # Cobertura
    "Cobertura Int.": "interest_coverage", "Interest Coverage": "interest_coverage",
    "FCF": "fcf", "FCF/Deuda": "fcf_to_debt", "Cash & Eq.": "cash_equivalents",
    
    # Crecimiento
    "Crec. Ingresos": "revenue_growth", "Crec. EPS": "eps_growth", "Crec. FCF": "fcf_growth",
    "Revenue Growth": "revenue_growth", "EPS Growth": "eps_growth", "FCF Growth": "fcf_growth",
    "Crec. Ingresos 3Y": "revenue_growth", "Crec. EPS 3Y": "eps_growth",
    
    # Scores institucionales
    "Altman Z-Score": "altman_z", "Z-Score": "altman_z",
    "Piotroski F": "piotroski_f", "F-Score": "piotroski_f",
    
    # Dividendos
    "Dividend Yield": "dividend_yield", "Payout Ratio": "payout_ratio",
    "Div. Yield": "dividend_yield",
    
    # REITs
    "FFO": "ffo", "P/FFO": "p_ffo", "FFO Payout": "ffo_payout",
    "FFO/Share": "ffo", "AFFO": "ffo",
    
    # Otros
    "Beta": "beta", "Market Cap": "market_cap", "Cap. Mercado": "market_cap",
    "52W High": "52w_high", "52W Low": "52w_low", "Vol. Promedio": "volume",
}


def get_tooltip_text(metric_key: str) -> str:
    """Genera el texto del tooltip con formato legible."""
    if metric_key not in METRIC_TOOLTIPS:
        return "Información no disponible"
    
    t = METRIC_TOOLTIPS[metric_key]
    
    text = f"""📌 {t['nombre']}

{t['que_es']}

📊 Rangos:
{t['rangos']}

💡 {t['contexto']}"""
    
    return text
