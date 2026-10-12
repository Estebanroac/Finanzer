"""
Constantes de modelo que leen financial_ratios.py y main.py.

Etapa 4: se borraron las constantes sin uso (Piotroski, niveles de score,
umbrales de ratios, caché, rate limits, UI, versión): ningún módulo las
importaba y varias contradecían a los valores que de verdad se ejecutan.
"""

# Altman Z-Score original (Altman, 1968): Z > 2.99 segura; 1.81–2.99 gris.
ALTMAN_Z_SAFE = 2.99
ALTMAN_Z_GREY = 1.81

# DCF / CAPM
DCF_RISK_FREE_RATE = 0.045        # 4.5% - US Treasury 10Y
DCF_MARKET_RISK_PREMIUM = 0.055   # 5.5% - Prima de riesgo histórica
DCF_TERMINAL_GROWTH = 0.025       # 2.5% - Crecimiento perpetuo
DCF_WACC_DEFAULT = 0.10           # descuento por defecto de dcf_multi_stage
DCF_HIGH_GROWTH_YEARS = 5         # Años de alto crecimiento
DCF_TRANSITION_YEARS = 5          # Años de transición
