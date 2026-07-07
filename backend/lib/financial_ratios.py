"""
Financial Ratios Calculator Module
==================================
Módulo completo para cálculo de ratios financieros y sistema de alertas
para análisis fundamental de acciones.

Autor: Esteban
Versión: 3.1 - Configuración Centralizada
"""

from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass
from enum import Enum

# Importar configuración centralizada
try:
    from config import (
        ALTMAN_Z_SAFE, ALTMAN_Z_GREY,
        DCF_RISK_FREE_RATE, DCF_MARKET_RISK_PREMIUM, DCF_TERMINAL_GROWTH,
        DCF_WACC_DEFAULT,
        DCF_GROWTH_MAX, DCF_GROWTH_DEFAULT,
        DCF_HIGH_GROWTH_YEARS, DCF_TRANSITION_YEARS,
    )
    CONFIG_AVAILABLE = True
except ImportError:
    # Fallback si config.py no está disponible
    CONFIG_AVAILABLE = False
    ALTMAN_Z_SAFE = 2.99
    ALTMAN_Z_GREY = 1.81
    DCF_RISK_FREE_RATE = 0.045
    DCF_MARKET_RISK_PREMIUM = 0.055
    DCF_TERMINAL_GROWTH = 0.025
    DCF_WACC_DEFAULT = 0.10
    DCF_GROWTH_MAX = 0.50
    DCF_GROWTH_DEFAULT = 0.08
    DCF_HIGH_GROWTH_YEARS = 5
    DCF_TRANSITION_YEARS = 5


# =========================
# CONFIGURACIÓN Y TIPOS
# =========================

class SignalType(Enum):
    """Tipos de señal para alertas."""
    POSITIVE = "Positivo"
    NEUTRAL = "Neutral"
    WARNING = "Advertencia"
    DANGER = "Peligro"


# =============================================================================
# NUEVAS MÉTRICAS INSTITUCIONALES
# =============================================================================

# Sectores considerados como "Financieros" (modelo adaptativo)
FINANCIAL_SECTORS = {
    "financials",           # Financial Services
    "financial services",
    "banks",
    "insurance",
    "asset management",
    "capital markets",
    "diversified financial",
    "regional banks",
    "investment banking",
    "credit services",
}

# Benchmarks específicos para sector financiero
# CALIBRADOS según estándares reales del sector bancario (Q1 2024)
# Fuente: Promedios de grandes bancos, requisitos Basilea III/IV
FINANCIAL_BENCHMARKS = {
    # ROA Bancario (promedio sector: 0.3-0.5%)
    "roa_excellent": 0.005,    # >0.5% es excelente para banco
    "roa_good": 0.003,         # >0.3% es bueno
    "roa_acceptable": 0.002,   # >0.2% es aceptable
    
    # ROE Bancario (objetivo típico: 8-12%)
    "roe_excellent": 0.12,     # >12% es excelente
    "roe_good": 0.08,          # >8% es bueno
    "roe_acceptable": 0.06,    # >6% es aceptable
    
    # Price to Book (valoración bancaria)
    "pb_cheap": 0.8,           # P/B < 0.8 es barato
    "pb_fair": 1.2,            # P/B 0.8-1.2 es justo
    "pb_expensive": 2.0,       # P/B > 2.0 es caro
    
    # Debt/Equity para BANCOS (muy diferente a industriales)
    # Los bancos operan normalmente con D/E de 8-15x
    "de_very_conservative": 5.0,   # <5x muy conservador (excelente)
    "de_conservative": 10.0,       # 5-10x conservador (bueno)
    "de_normal": 15.0,             # 10-15x normal/típico
    # >15x = elevado
    
    # Capitalización
    "equity_to_assets_solid": 0.06,  # >6% es sólido para banco
    "equity_to_assets_good": 0.04,   # >4% es aceptable
    
    # Dividendos
    "dividend_yield_good": 0.025,    # >2.5% es buen dividendo
    "payout_sustainable": 0.60,      # <60% payout es sostenible
}


def is_financial_sector(sector: str) -> bool:
    """
    Detecta si un sector es financiero (bancos, seguros, asset management).
    
    Args:
        sector: Nombre del sector (puede venir de Yahoo Finance o del mapeo interno)
        
    Returns:
        True si es sector financiero
    """
    if not sector:
        return False
    sector_lower = sector.lower().strip()
    
    # Verificar coincidencia directa
    if sector_lower in FINANCIAL_SECTORS:
        return True
    
    # Verificar si contiene palabras clave
    financial_keywords = ["bank", "financ", "insurance", "asset manage", "capital market"]
    return any(kw in sector_lower for kw in financial_keywords)

def altman_z_score(
    working_capital: Optional[float],
    total_assets: Optional[float],
    retained_earnings: Optional[float],
    ebit: Optional[float],
    market_value_equity: Optional[float],
    total_liabilities: Optional[float],
    sales: Optional[float],
    sector: str = "",
    book_value_equity: Optional[float] = None,
) -> Tuple[Optional[float], str, str, dict]:
    """
    Altman Z-Score adaptativo — selecciona automáticamente el modelo correcto
    según el tipo de empresa:

    1) Z-Score ORIGINAL (1968) — empresas manufactureras públicas
       Z = 1.2×X1 + 1.4×X2 + 3.3×X3 + 0.6×X4 + 1.0×X5
       Safe > 2.99 | Grey 1.81–2.99 | Distress < 1.81

    2) Z''-Score (1995) — servicios, tech, non-manufacturing
       Elimina X5 (asset turnover) porque sesga a empresas asset-light.
       Z'' = 6.56×X1 + 3.26×X2 + 6.72×X3 + 1.05×X4
       Safe > 2.60 | Grey 1.10–2.60 | Distress < 1.10

    3) Z'-Score (1983) — empresas privadas (usa book value en vez de market cap)
       Z' = 0.717×X1 + 0.847×X2 + 3.107×X3 + 0.420×X4' + 0.998×X5
       donde X4' = Book Value Equity / Total Liabilities
       Safe > 2.90 | Grey 1.23–2.90 | Distress < 1.23

    Returns:
        Tuple[z_score, risk_level, interpretation, details_dict]
    """
    # ── Financial sector exclusion ──
    # El Altman Z-Score no fue diseñado para instituciones financieras.
    # Los bancos y aseguradoras tienen estructuras de deuda masivas por naturaleza
    # (depósitos = pasivos), lo que genera Z-Scores artificialmente bajos.
    if is_financial_sector(sector or ""):
        return (
            None,
            "N/A",
            "El modelo Altman Z-Score no es aplicable a instituciones financieras. "
            "Los bancos, aseguradoras y empresas de servicios financieros tienen "
            "estructuras de balance fundamentalmente diferentes (depósitos = pasivos), "
            "lo que invalida las métricas del modelo.",
            {
                "model": "No Aplicable",
                "reason": "financial_sector",
                "sector": sector or "",
                "warnings": [
                    "El Altman Z-Score fue diseñado para empresas industriales y comerciales",
                    "Para evaluar instituciones financieras, se recomienda usar métricas como "
                    "CET1 Ratio, Tier 1 Capital, ROA bancario y Texas Ratio",
                ],
            },
        )

    # ── Determine which model to use based on sector ──
    _sector = (sector or "").lower().strip()
    _NON_MFG_SECTORS = {
        "technology", "tech", "communication services",
        "healthcare", "consumer cyclical", "consumer defensive",
        "real estate", "utilities", "software", "internet",
        "media", "telecom", "services", "retail", "fintech",
    }
    is_non_manufacturing = any(s in _sector for s in _NON_MFG_SECTORS) or _sector == ""
    use_private = (market_value_equity is None or market_value_equity == 0) and book_value_equity is not None

    # ── Validate minimum required inputs ──
    if total_assets is None or total_assets == 0:
        return None, "N/A", "Datos insuficientes para calcular Z-Score", {}
    if ebit is None:
        return None, "N/A", "Datos insuficientes: falta EBIT / Operating Income", {}
    if total_liabilities is None or total_liabilities == 0:
        return None, "N/A", "Datos insuficientes: faltan pasivos totales", {}

    # WC and RE can legitimately be None — treat as 0 only with flag
    wc = working_capital if working_capital is not None else 0
    re = retained_earnings if retained_earnings is not None else 0

    try:
        X1 = wc / total_assets
        X2 = re / total_assets
        X3 = ebit / total_assets

        details = {"X1_wc_ta": round(X1, 4), "X2_re_ta": round(X2, 4), "X3_ebit_ta": round(X3, 4)}

        if use_private:
            # ── Z'-Score (private companies) ──
            X4p = book_value_equity / total_liabilities
            X5 = (sales / total_assets) if sales else 0
            z = 0.717*X1 + 0.847*X2 + 3.107*X3 + 0.420*X4p + 0.998*X5
            model_name = "Z'-Score (Empresas Privadas)"
            safe_threshold, grey_threshold = 2.90, 1.23
            details.update({"X4_bv_tl": round(X4p, 4), "X5_rev_ta": round(X5, 4)})

        elif is_non_manufacturing:
            # ── Z''-Score (services / tech / non-manufacturing) ──
            X4 = market_value_equity / total_liabilities
            z = 6.56*X1 + 3.26*X2 + 6.72*X3 + 1.05*X4
            model_name = "Z''-Score (No Manufactura)"
            safe_threshold, grey_threshold = 2.60, 1.10
            details.update({"X4_mcap_tl": round(X4, 4)})

        else:
            # ── Z-Score Original (manufacturing) ──
            X4 = market_value_equity / total_liabilities
            X5 = (sales / total_assets) if sales else 0
            z = 1.2*X1 + 1.4*X2 + 3.3*X3 + 0.6*X4 + 1.0*X5
            model_name = "Z-Score Original (Manufactura)"
            safe_threshold, grey_threshold = ALTMAN_Z_SAFE, ALTMAN_Z_GREY
            details.update({"X4_mcap_tl": round(X4, 4), "X5_rev_ta": round(X5, 4)})

        details["model"] = model_name
        details["safe_threshold"] = safe_threshold
        details["grey_threshold"] = grey_threshold

        # ── Classify zone ──
        if z > safe_threshold:
            risk_level = "SAFE"
            interpretation = f"{model_name}: Zona segura — bajo riesgo de bancarrota"
        elif z > grey_threshold:
            risk_level = "GREY"
            interpretation = f"{model_name}: Zona gris — riesgo moderado, monitorear"
        else:
            risk_level = "DISTRESS"
            interpretation = f"{model_name}: Zona de peligro — alto riesgo de bancarrota"

        # Add data quality warnings
        warnings = []
        if working_capital is None:
            warnings.append("Working Capital estimado (datos parciales)")
        if retained_earnings is None:
            warnings.append("Retained Earnings no disponible, asumido 0")
        if warnings:
            details["warnings"] = warnings

        return round(z, 2), risk_level, interpretation, details

    except (ZeroDivisionError, TypeError, ValueError):
        return None, "N/A", "Error en cálculo del Z-Score", {}
    except Exception:
        return None, "N/A", "Error inesperado en cálculo", {}


def financial_health_score(
    roa: Optional[float],
    roe: Optional[float],
    total_equity: Optional[float],
    total_assets: Optional[float],
    book_value: Optional[float],
    book_value_prior: Optional[float] = None,
    dividend_yield: Optional[float] = None,
    payout_ratio: Optional[float] = None,
    debt_to_equity: Optional[float] = None  # Nuevo: D/E para bancos
) -> Tuple[Optional[int], str, str, List[Dict[str, Any]]]:
    """
    Financial Health Score - Indicador de solidez para sector financiero (0-10).
    
    Reemplaza al Altman Z-Score para bancos, seguros y empresas financieras,
    ya que el Z-Score no es aplicable a su modelo de negocio.
    
    CALIBRADO según estándares reales del sector bancario (2024):
    - ROA promedio grandes bancos: 0.3-0.5%
    - ROE objetivo típico: 8-12%
    - D/E normal para bancos: 8-15x
    
    Componentes:
        ROA (0-3 pts): >0.5% excelente, >0.3% bueno, >0.2% aceptable
        ROE (0-3 pts): >12% excelente, >8% bueno, >6% aceptable
        D/E Bancario (0-2 pts): <5x muy conservador, 5-10x conservador
        Book Value Growth (0-1 pts): Creciendo YoY
        Dividend (0-1 pts): Paga dividendo sostenible
    
    IMPORTANTE: Cuando faltan datos, se asigna puntuación NEUTRAL proporcional,
    NO se penaliza. "No penalizar por examen no tomado."
    
    Returns:
        Tuple[score, risk_level, interpretation, details]
    """
    score = 0
    max_possible = 0  # Track máximo posible según datos disponibles
    details = []
    b = FINANCIAL_BENCHMARKS
    
    # 1. ROA (0-3 puntos) - Crítico para bancos
    if roa is not None:
        max_possible += 3
        roa_pct = roa if roa < 1 else roa / 100  # Normalizar si viene como porcentaje
        if roa_pct >= b["roa_excellent"]:
            pts = 3
            detail = f"ROA excelente ({roa_pct*100:.2f}% ≥ 0.5%)"
            severity = "excellent"
        elif roa_pct >= b["roa_good"]:
            pts = 2
            detail = f"ROA bueno ({roa_pct*100:.2f}% ≥ 0.3%)"
            severity = "good"
        elif roa_pct >= b["roa_acceptable"]:
            pts = 1
            detail = f"ROA aceptable ({roa_pct*100:.2f}% ≥ 0.2%)"
            severity = "ok"
        else:
            pts = 0
            detail = f"ROA bajo ({roa_pct*100:.2f}% < 0.2%)"
            severity = "weak"
        score += pts
        details.append({"metric": "ROA Bancario", "points": pts, "max": 3, "detail": detail, "severity": severity})
    
    # 2. ROE (0-3 puntos)
    if roe is not None:
        max_possible += 3
        roe_pct = roe if roe < 1 else roe / 100
        if roe_pct >= b["roe_excellent"]:
            pts = 3
            detail = f"ROE excelente ({roe_pct*100:.1f}% ≥ 12%)"
            severity = "excellent"
        elif roe_pct >= b["roe_good"]:
            pts = 2
            detail = f"ROE bueno ({roe_pct*100:.1f}% ≥ 8%)"
            severity = "good"
        elif roe_pct >= b["roe_acceptable"]:
            pts = 1
            detail = f"ROE aceptable ({roe_pct*100:.1f}% ≥ 6%)"
            severity = "ok"
        else:
            pts = 0
            detail = f"ROE bajo ({roe_pct*100:.1f}% < 6%)"
            severity = "weak"
        score += pts
        details.append({"metric": "ROE", "points": pts, "max": 3, "detail": detail, "severity": severity})
    
    # 3. D/E Bancario (0-2 puntos) - NUEVO: Interpretación correcta para bancos
    # Los bancos operan normalmente con D/E de 8-15x, así que 2.6x es MUY conservador
    if debt_to_equity is not None:
        max_possible += 2
        if debt_to_equity < b["de_very_conservative"]:
            pts = 2
            detail = f"D/E muy conservador ({debt_to_equity:.1f}x < 5x) - Excelente para banco"
            severity = "excellent"
        elif debt_to_equity < b["de_conservative"]:
            pts = 2
            detail = f"D/E conservador ({debt_to_equity:.1f}x < 10x) - Sólido"
            severity = "good"
        elif debt_to_equity < b["de_normal"]:
            pts = 1
            detail = f"D/E normal ({debt_to_equity:.1f}x) - Típico bancario"
            severity = "ok"
        else:
            pts = 0
            detail = f"D/E elevado ({debt_to_equity:.1f}x > 15x)"
            severity = "moderate"
        score += pts
        details.append({"metric": "D/E Bancario", "points": pts, "max": 2, "detail": detail, "severity": severity})
    elif total_equity is not None and total_assets is not None and total_assets > 0:
        # Fallback: usar Equity/Assets si no hay D/E
        max_possible += 2
        equity_ratio = total_equity / total_assets
        if equity_ratio >= b["equity_to_assets_solid"]:
            pts = 2
            detail = f"Capitalización sólida ({equity_ratio*100:.1f}% ≥ 6%)"
            severity = "excellent"
        elif equity_ratio >= b["equity_to_assets_good"]:
            pts = 1
            detail = f"Capitalización aceptable ({equity_ratio*100:.1f}%)"
            severity = "ok"
        else:
            pts = 0
            detail = f"Capitalización baja ({equity_ratio*100:.1f}%)"
            severity = "weak"
        score += pts
        details.append({"metric": "Equity/Assets", "points": pts, "max": 2, "detail": detail, "severity": severity})
    
    # 4. Book Value Growth (0-1 punto)
    if book_value is not None and book_value_prior is not None and book_value_prior > 0:
        max_possible += 1
        bv_growth = (book_value - book_value_prior) / book_value_prior
        if bv_growth > 0:
            pts = 1
            detail = f"Book Value creciendo ({bv_growth*100:.1f}% YoY)"
            severity = "excellent"
        else:
            pts = 0
            detail = f"Book Value decreciendo ({bv_growth*100:.1f}% YoY)"
            severity = "weak"
        score += pts
        details.append({"metric": "Book Value Growth", "points": pts, "max": 1, "detail": detail, "severity": severity})
    
    # 5. Dividend (0-1 punto) - Bancos suelen pagar dividendos
    if dividend_yield is not None and dividend_yield > 0:
        max_possible += 1
        # Un payout negativo (dividendos pagados con ganancias negativas, año en
        # pérdidas) NO es sostenible: antes `payout < 0.60` lo daba por sostenible.
        _sustainable = 0 <= payout_ratio < b.get("payout_sustainable", 0.60) if payout_ratio is not None else True
        if _sustainable:
            pts = 1
            detail = f"Dividendo sostenible ({dividend_yield*100:.2f}%)"
            severity = "excellent"
        elif payout_ratio is not None and payout_ratio < 0:
            pts = 0
            detail = f"Dividendo insostenible (pagado con pérdidas)"
            severity = "weak"
        else:
            pts = 0
            detail = f"Payout ratio alto ({payout_ratio*100:.0f}% > 60%)"
            severity = "moderate"
        score += pts
        details.append({"metric": "Dividendo", "points": pts, "max": 1, "detail": detail, "severity": severity})
    
    # =====================================================
    # MANEJO DE DATOS FALTANTES: Escalar a 10 puntos
    # Si solo tenemos algunos datos, escalar proporcionalmente
    # NO penalizar por datos que no tenemos
    # =====================================================
    if max_possible > 0:
        # Escalar score a base 10
        scaled_score = round((score / max_possible) * 10)
    else:
        # Sin datos: puntuación neutral (5/10)
        scaled_score = 5
        details.append({
            "metric": "Datos Limitados", 
            "points": 5, 
            "max": 10, 
            "detail": "Análisis limitado - métricas bancarias regulatorias no disponibles",
            "severity": "neutral"
        })
    
    # Determinar nivel de riesgo e interpretación
    if scaled_score >= 8:
        risk_level = "STRONG"
        interpretation = "Excelente - Institución financiera muy sólida"
    elif scaled_score >= 6:
        risk_level = "GOOD"
        interpretation = "Buena salud financiera"
    elif scaled_score >= 4:
        risk_level = "NEUTRAL"
        interpretation = "Neutral - Dentro de parámetros normales"
    else:
        risk_level = "WEAK"
        interpretation = "Por debajo del promedio sectorial"
    
    # Agregar nota si el análisis es limitado
    if max_possible < 6:
        interpretation += " (análisis limitado por datos disponibles)"
    
    return scaled_score, risk_level, interpretation, details


def piotroski_f_score(
    # Rentabilidad (4 puntos)
    net_income: Optional[float],
    roa_current: Optional[float],
    roa_prior: Optional[float],
    operating_cash_flow: Optional[float],
    # Apalancamiento/Liquidez (3 puntos)
    long_term_debt_current: Optional[float],
    long_term_debt_prior: Optional[float],
    current_ratio_current: Optional[float],
    current_ratio_prior: Optional[float],
    shares_current: Optional[float],
    shares_prior: Optional[float],
    # Eficiencia Operativa (2 puntos)
    gross_margin_current: Optional[float],
    gross_margin_prior: Optional[float],
    asset_turnover_current: Optional[float],
    asset_turnover_prior: Optional[float],
    total_assets: Optional[float] = None
) -> Tuple[int, List[str], str]:
    """
    Piotroski F-Score - Indicador de fortaleza financiera (0-9).
    
    Desarrollado por Joseph Piotroski (Stanford, 2000).
    
    Mide 9 señales binarias en 3 categorías:
    
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
        8-9: Fortaleza financiera excepcional
        6-7: Buena salud financiera
        4-5: Neutral
        2-3: Debilidad financiera
        0-1: Alto riesgo de problemas financieros
    
    Returns:
        Tuple[score, details, interpretation]
    """
    score = 0
    details = []
    
    # === RENTABILIDAD (4 puntos) ===
    
    # 1. ROA positivo
    if roa_current is not None and roa_current > 0:
        score += 1
        details.append("✓ ROA positivo")
    else:
        details.append("✗ ROA negativo o N/A")
    
    # 2. CFO positivo
    if operating_cash_flow is not None and operating_cash_flow > 0:
        score += 1
        details.append("✓ Cash Flow Operativo positivo")
    else:
        details.append("✗ CFO negativo o N/A")
    
    # 3. ROA mejoró
    if roa_current is not None and roa_prior is not None:
        if roa_current > roa_prior:
            score += 1
            details.append("✓ ROA mejoró vs año anterior")
        else:
            details.append("✗ ROA no mejoró")
    else:
        details.append("✗ Sin datos ROA histórico")
    
    # 4. Calidad de earnings (CFO > Net Income)
    if operating_cash_flow is not None and net_income is not None:
        if operating_cash_flow > net_income:
            score += 1
            details.append("✓ CFO > Net Income (earnings de calidad)")
        else:
            details.append("✗ CFO < Net Income (alerta calidad)")
    else:
        details.append("✗ Sin datos para calidad de earnings")
    
    # === APALANCAMIENTO/LIQUIDEZ (3 puntos) ===
    
    # 5. Deuda LP disminuyó
    if long_term_debt_current is not None and long_term_debt_prior is not None:
        if long_term_debt_current <= long_term_debt_prior:
            score += 1
            details.append("✓ Deuda LP estable o disminuyó")
        else:
            details.append("✗ Deuda LP aumentó")
    else:
        details.append("✗ Sin datos de deuda LP histórica")
    
    # 6. Current Ratio mejoró
    if current_ratio_current is not None and current_ratio_prior is not None:
        if current_ratio_current > current_ratio_prior:
            score += 1
            details.append("✓ Liquidez (Current Ratio) mejoró")
        else:
            details.append("✗ Liquidez no mejoró")
    else:
        details.append("✗ Sin datos de liquidez histórica")
    
    # 7. No emitió nuevas acciones (dilución)
    if shares_current is not None and shares_prior is not None:
        if shares_current <= shares_prior:
            score += 1
            details.append("✓ Sin dilución de acciones")
        else:
            details.append("✗ Emisión de nuevas acciones (dilución)")
    else:
        details.append("✗ Sin datos de acciones históricas")
    
    # === EFICIENCIA OPERATIVA (2 puntos) ===
    
    # 8. Margen bruto mejoró
    if gross_margin_current is not None and gross_margin_prior is not None:
        if gross_margin_current > gross_margin_prior:
            score += 1
            details.append("✓ Margen bruto mejoró")
        else:
            details.append("✗ Margen bruto no mejoró")
    else:
        details.append("✗ Sin datos de margen bruto histórico")
    
    # 9. Asset Turnover mejoró
    if asset_turnover_current is not None and asset_turnover_prior is not None:
        if asset_turnover_current > asset_turnover_prior:
            score += 1
            details.append("✓ Eficiencia de activos mejoró")
        else:
            details.append("✗ Eficiencia de activos no mejoró")
    else:
        details.append("✗ Sin datos de asset turnover histórico")
    
    # Signals that couldn't be evaluated because prior-year data is missing
    # (e.g. recent IPOs). A low score caused by absent history is a data
    # limitation, not financial weakness — don't call it "debilidad".
    no_data = sum(1 for d in details if "Sin datos" in d)

    # Interpretación
    if no_data >= 4:
        interpretation = f"Datos históricos limitados ({no_data}/9 señales sin evaluar) - F-Score no concluyente"
    elif score >= 8:
        interpretation = "Excelente - Fortaleza financiera excepcional"
    elif score >= 6:
        interpretation = "Bueno - Salud financiera sólida"
    elif score >= 4:
        interpretation = "Neutral - Monitorear indicadores"
    elif score >= 2:
        interpretation = "Débil - Señales de debilidad financiera"
    else:
        interpretation = "Crítico - Alto riesgo de problemas"

    return score, details, interpretation


def calculate_wacc(
    beta: Optional[float],
    risk_free_rate: float = DCF_RISK_FREE_RATE,
    market_risk_premium: float = DCF_MARKET_RISK_PREMIUM,
    cost_of_debt: Optional[float] = None,
    tax_rate: float = 0.25,
    debt_to_equity: Optional[float] = None,
    interest_expense: Optional[float] = None,
    total_debt: Optional[float] = None
) -> Optional[float]:
    """
    Calcula el WACC (Weighted Average Cost of Capital) específico de la empresa.
    
    WACC = E/(E+D) * Re + D/(E+D) * Rd * (1-T)
    
    Donde:
        Re = Cost of Equity = Rf + β * (Rm - Rf)  [CAPM]
        Rd = Cost of Debt
        T = Tax Rate
        E/(E+D) = Weight of Equity
        D/(E+D) = Weight of Debt
    
    Args:
        beta: Beta de la acción
        risk_free_rate: Tasa libre de riesgo (Treasury 10Y)
        market_risk_premium: Prima de riesgo del mercado
        cost_of_debt: Costo de deuda (si no se provee, se estima)
        tax_rate: Tasa impositiva
        debt_to_equity: Ratio deuda/equity
        interest_expense: Gasto por intereses (para estimar costo de deuda)
        total_debt: Deuda total (para estimar costo de deuda)
    
    Returns:
        WACC como decimal (ej: 0.10 = 10%)
    """
    if beta is None:
        beta = 1.0  # Asumir mercado si no hay beta
    
    # Cost of Equity usando CAPM
    cost_of_equity = risk_free_rate + beta * market_risk_premium
    
    # Si no hay deuda significativa, WACC ≈ Cost of Equity
    if debt_to_equity is None or debt_to_equity < 0.01:
        return cost_of_equity
    
    # Estimar Cost of Debt si no se provee
    if cost_of_debt is None:
        if interest_expense is not None and total_debt is not None and total_debt > 0:
            cost_of_debt = interest_expense / total_debt
        else:
            # Estimación basada en rating implícito
            if debt_to_equity < 0.3:
                cost_of_debt = risk_free_rate + 0.01  # Investment grade
            elif debt_to_equity < 0.6:
                cost_of_debt = risk_free_rate + 0.02  # BBB
            elif debt_to_equity < 1.0:
                cost_of_debt = risk_free_rate + 0.03  # BB
            else:
                cost_of_debt = risk_free_rate + 0.05  # High yield
    
    # Calcular pesos
    equity_weight = 1 / (1 + debt_to_equity)
    debt_weight = debt_to_equity / (1 + debt_to_equity)
    
    # WACC
    wacc = (equity_weight * cost_of_equity + 
            debt_weight * cost_of_debt * (1 - tax_rate))
    
    return round(wacc, 4)


def calculate_justified_pe(
    earnings_growth: Optional[float],
    required_return: float = 0.10,
    roe: Optional[float] = None,
    payout_ratio: float = 0.30
) -> Optional[float]:
    """
    Calcula el P/E justificado basado en fundamentos (Gordon Growth Model adaptado).
    
    P/E justificado = Payout * (1 + g) / (r - g)
    
    O simplificado para growth: P/E ≈ (1 + g) / (r - g)
    
    Ajustes:
        - ROE > 20%: +20% premium (calidad)
        - ROE > 30%: +35% premium (excepcional)
    
    Args:
        earnings_growth: Crecimiento esperado de EPS
        required_return: Retorno requerido (WACC o costo de equity)
        roe: Return on Equity para ajuste de calidad
        payout_ratio: Ratio de dividendos
    
    Returns:
        P/E justificado
    """
    if earnings_growth is None:
        return None
    
    # Limitar growth para evitar división por cero o negativos
    g = min(earnings_growth, required_return - 0.01)
    g = max(g, -0.05)  # No menos de -5%
    
    if required_return <= g:
        # Growth muy alto - usar múltiplo de PEG
        return 25 * (1 + earnings_growth)  # Base P/E 25 ajustado por growth
    
    try:
        # Gordon Growth Model simplificado
        justified_pe = (1 + g) / (required_return - g)
        
        # Ajuste por calidad (ROE)
        if roe is not None:
            if roe > 0.30:
                justified_pe *= 1.35  # Premium excepcional
            elif roe > 0.20:
                justified_pe *= 1.20  # Premium calidad
            elif roe < 0.08:
                justified_pe *= 0.85  # Descuento baja calidad
        
        # Limitar a rangos razonables
        justified_pe = max(5, min(80, justified_pe))
        
        return round(justified_pe, 1)
        
    except (ZeroDivisionError, TypeError, ValueError):
        return None
    except Exception:
        return None


# =============================================================================
# NUEVAS FUNCIONES v2.2 - Sistema Adaptativo Growth/Value
# =============================================================================

def classify_company_type(
    revenue_growth_3y: Optional[float],
    eps_growth_3y: Optional[float],
    pe: Optional[float],
    sector_pe: Optional[float],
    dividend_yield: Optional[float],
    fcf_yield: Optional[float],
    roe: Optional[float]
) -> Dict[str, Any]:
    """
    Clasifica una empresa en categorías de inversión.
    
    Tipos:
        - "deep_value": P/E muy bajo, fundamentos sólidos
        - "value": P/E bajo, crecimiento moderado
        - "garp": Growth at Reasonable Price (crecimiento + valoración razonable)
        - "growth": Alto crecimiento, múltiplos elevados justificados
        - "speculative_growth": Alto crecimiento pero fundamentos débiles
        - "dividend": Foco en dividendos
        - "blend": No encaja claramente en ninguna categoría
    
    Returns:
        Dict con tipo, confianza, y razones
    """
    scores = {
        "deep_value": 0,
        "value": 0,
        "garp": 0,
        "growth": 0,
        "speculative_growth": 0,
        "dividend": 0
    }
    reasons = []
    
    # Evaluar métricas de crecimiento
    has_strong_growth = False
    has_quality_growth = False
    
    if revenue_growth_3y is not None:
        if revenue_growth_3y >= 0.25:
            scores["growth"] += 3
            scores["garp"] += 2
            has_strong_growth = True
            reasons.append(f"Revenue growth {revenue_growth_3y:.0%}")
        elif revenue_growth_3y >= 0.15:
            scores["growth"] += 2
            scores["garp"] += 2
            has_strong_growth = True
        elif revenue_growth_3y >= 0.05:
            scores["garp"] += 1
            scores["value"] += 1
        elif revenue_growth_3y < 0:
            scores["value"] += 1
            scores["deep_value"] += 1
    
    if eps_growth_3y is not None:
        if eps_growth_3y >= 0.20:
            scores["growth"] += 2
            scores["garp"] += 2
            has_quality_growth = True
        elif eps_growth_3y >= 0.10:
            scores["garp"] += 1
    
    # Evaluar valoración
    if pe is not None and pe > 0:
        pe_threshold = sector_pe if sector_pe and sector_pe > 0 else 20
        pe_ratio_to_sector = pe / pe_threshold
        
        if pe_ratio_to_sector <= 0.6:
            scores["deep_value"] += 3
            reasons.append(f"P/E muy bajo vs sector")
        elif pe_ratio_to_sector <= 0.85:
            scores["value"] += 2
            scores["deep_value"] += 1
        elif pe_ratio_to_sector <= 1.15:
            scores["garp"] += 2
            scores["value"] += 1
        elif pe_ratio_to_sector <= 1.5:
            scores["growth"] += 1
            scores["garp"] += 1
        else:
            scores["growth"] += 2
            scores["speculative_growth"] += 1
            reasons.append(f"P/E elevado ({pe:.0f}x)")
    
    # Evaluar calidad (ROE)
    if roe is not None:
        if roe >= 0.25:
            scores["growth"] += 1
            scores["garp"] += 2
            has_quality_growth = True
            reasons.append(f"ROE excepcional {roe:.0%}")
        elif roe >= 0.15:
            scores["garp"] += 1
            scores["value"] += 1
        elif roe < 0.08:
            scores["speculative_growth"] += 2
            scores["growth"] -= 1
    
    # Evaluar dividendos
    if dividend_yield is not None:
        if dividend_yield >= 0.04:
            scores["dividend"] += 3
            scores["value"] += 1
            reasons.append(f"Alto dividendo {dividend_yield:.1%}")
        elif dividend_yield >= 0.02:
            scores["dividend"] += 1
            scores["value"] += 1
    
    # FCF Yield (indicador de value)
    if fcf_yield is not None:
        if fcf_yield >= 0.08:
            scores["deep_value"] += 2
            scores["value"] += 1
        elif fcf_yield >= 0.05:
            scores["value"] += 1
            scores["garp"] += 1
    
    # Determinar tipo ganador
    best_type = max(scores, key=scores.get)
    best_score = scores[best_type]
    
    # Si hay crecimiento fuerte + calidad, es GARP o Growth legítimo
    if has_strong_growth and has_quality_growth:
        if scores["garp"] >= scores["growth"] - 1:
            best_type = "garp"
        else:
            best_type = "growth"
        # Reducir speculative si hay calidad
        scores["speculative_growth"] = max(0, scores["speculative_growth"] - 2)
    
    # Calcular confianza
    total_score = sum(scores.values())
    confidence = best_score / max(total_score, 1)
    
    # Si la confianza es baja, es blend
    if confidence < 0.25 or best_score < 3:
        best_type = "blend"
        confidence = 0.5
    
    return {
        "type": best_type,
        "confidence": round(confidence, 2),
        "scores": scores,
        "reasons": reasons,
        "has_quality_growth": has_quality_growth
    }


def calculate_growth_quality_score(
    revenue_growth_3y: Optional[float],
    eps_growth_3y: Optional[float],
    fcf_growth_3y: Optional[float],
    roe: Optional[float],
    roic: Optional[float],
    operating_margin: Optional[float],
    fcf_to_net_income: Optional[float]
) -> Dict[str, Any]:
    """
    Calcula un score de calidad del crecimiento (0-100).
    
    Un crecimiento de calidad tiene:
    - Crecimiento de revenue sostenido
    - EPS creciendo igual o más que revenue (expansión de márgenes)
    - FCF positivo y creciente
    - ROE/ROIC altos
    - Buenos márgenes operativos
    
    Returns:
        Dict con score, nivel, y breakdown
    """
    score = 50  # Base neutral
    breakdown = []
    
    # 1. Crecimiento de Revenue (hasta ±15 pts)
    if revenue_growth_3y is not None:
        if revenue_growth_3y >= 0.25:
            score += 15
            breakdown.append(("Revenue Growth", "+15", "Excepcional"))
        elif revenue_growth_3y >= 0.15:
            score += 10
            breakdown.append(("Revenue Growth", "+10", "Fuerte"))
        elif revenue_growth_3y >= 0.08:
            score += 5
            breakdown.append(("Revenue Growth", "+5", "Sólido"))
        elif revenue_growth_3y >= 0:
            score += 0
            breakdown.append(("Revenue Growth", "0", "Estable"))
        else:
            score -= 10
            breakdown.append(("Revenue Growth", "-10", "Contracción"))
    
    # 2. EPS vs Revenue growth (hasta ±10 pts)
    if eps_growth_3y is not None and revenue_growth_3y is not None:
        if eps_growth_3y > revenue_growth_3y * 1.2:
            score += 10
            breakdown.append(("EPS vs Revenue", "+10", "Expansión de márgenes"))
        elif eps_growth_3y >= revenue_growth_3y:
            score += 5
            breakdown.append(("EPS vs Revenue", "+5", "Márgenes estables"))
        elif eps_growth_3y >= revenue_growth_3y * 0.5:
            score -= 5
            breakdown.append(("EPS vs Revenue", "-5", "Compresión leve"))
        else:
            score -= 10
            breakdown.append(("EPS vs Revenue", "-10", "Compresión severa"))
    
    # 3. FCF Growth (hasta ±10 pts)
    if fcf_growth_3y is not None:
        if fcf_growth_3y >= 0.15:
            score += 10
            breakdown.append(("FCF Growth", "+10", "Excelente"))
        elif fcf_growth_3y >= 0.05:
            score += 5
            breakdown.append(("FCF Growth", "+5", "Positivo"))
        elif fcf_growth_3y >= 0:
            score += 0
            breakdown.append(("FCF Growth", "0", "Estable"))
        else:
            score -= 10
            breakdown.append(("FCF Growth", "-10", "Negativo"))
    
    # 4. ROE/ROIC - Calidad del capital (hasta ±10 pts)
    best_return = max(filter(None, [roe, roic]), default=None)
    if best_return is not None:
        if best_return >= 0.25:
            score += 10
            breakdown.append(("Return on Capital", "+10", "Excepcional"))
        elif best_return >= 0.15:
            score += 5
            breakdown.append(("Return on Capital", "+5", "Bueno"))
        elif best_return >= 0.08:
            score += 0
            breakdown.append(("Return on Capital", "0", "Aceptable"))
        else:
            score -= 10
            breakdown.append(("Return on Capital", "-10", "Bajo"))
    
    # 5. Margen operativo (hasta ±5 pts)
    if operating_margin is not None:
        if operating_margin >= 0.25:
            score += 5
            breakdown.append(("Op. Margin", "+5", "Muy alto"))
        elif operating_margin >= 0.15:
            score += 3
            breakdown.append(("Op. Margin", "+3", "Saludable"))
        elif operating_margin < 0.05:
            score -= 5
            breakdown.append(("Op. Margin", "-5", "Bajo"))
    
    # Normalizar a 0-100
    score = max(0, min(100, score))
    
    # Determinar nivel
    if score >= 80:
        level = "exceptional"
        label = "Crecimiento Excepcional"
    elif score >= 65:
        level = "high_quality"
        label = "Alta Calidad"
    elif score >= 50:
        level = "moderate"
        label = "Calidad Moderada"
    elif score >= 35:
        level = "low_quality"
        label = "Baja Calidad"
    else:
        level = "poor"
        label = "Crecimiento Pobre"
    
    return {
        "score": score,
        "level": level,
        "label": label,
        "breakdown": breakdown
    }


def adjust_valuation_for_growth(
    base_pe_adjustment: int,
    pe: float,
    sector_pe: float,
    growth_quality_score: int,
    company_type: str,
    revenue_growth: Optional[float],
    roe: Optional[float]
) -> tuple:
    """
    Ajusta la penalización de P/E basado en la calidad del crecimiento.

    v2.4: Ajustes MÁS GENEROSOS para growth de calidad.
    El mercado paga múltiplos altos por empresas que crecen rápido con
    buenos fundamentos. Penalizar -5 a NVDA por P/E alto no tiene sentido
    si crece >50% con ROE >100%.

    Returns:
        (adjusted_value, reason, severity)
    """
    # Si el ajuste base es positivo (P/E bajo), no modificar
    if base_pe_adjustment >= 0:
        return base_pe_adjustment, None, None

    pe_premium = pe / sector_pe if sector_pe > 0 else pe / 20

    # Calcular ajuste basado en calidad
    adjustment_modifier = 0
    reason_parts = []

    # v2.4: Growth quality alta JUSTIFICA premium de forma más agresiva
    if growth_quality_score >= 85:
        adjustment_modifier += 5  # Antes: 3 → ahora puede neutralizar -5
        reason_parts.append("calidad excepcional")
    elif growth_quality_score >= 75:
        adjustment_modifier += 4
        reason_parts.append("calidad muy alta")
    elif growth_quality_score >= 65:
        adjustment_modifier += 3
        reason_parts.append("alta calidad")
    elif growth_quality_score >= 50:
        adjustment_modifier += 2
        reason_parts.append("calidad moderada")

    # Tipo de empresa — growth legítimo merece más alivio
    if company_type in ["garp", "growth"] and growth_quality_score >= 60:
        adjustment_modifier += 2
        reason_parts.append("growth legítimo" if company_type == "growth" else "GARP")
    elif company_type == "speculative_growth":
        adjustment_modifier -= 1
        reason_parts.append("especulativo")

    # ROE excepcional justifica premium (ventaja competitiva duradera)
    if roe is not None and roe >= 0.30:
        adjustment_modifier += 2
        reason_parts.append(f"ROE {roe:.0%}")
    elif roe is not None and roe >= 0.20:
        adjustment_modifier += 1
        reason_parts.append(f"ROE {roe:.0%}")

    # Aplicar modificador
    new_adjustment = base_pe_adjustment + adjustment_modifier

    # v2.4: Permitir que growth de calidad excepcional llegue a bonus moderado (+2 max)
    if growth_quality_score >= 80 and company_type in ["growth", "garp"]:
        new_adjustment = min(new_adjustment, 2)  # Puede convertir en bonus leve
    elif growth_quality_score >= 65:
        new_adjustment = min(new_adjustment, 1)  # Puede llegar a +1
    else:
        new_adjustment = min(new_adjustment, 0)  # No convertir en bonus

    # Determinar severidad
    if new_adjustment >= 0:
        severity = "ok"
    elif new_adjustment >= -1:
        severity = "moderate"
    else:
        severity = "severe"

    # Construir razón
    if adjustment_modifier > 0 and reason_parts:
        if new_adjustment >= 0:
            reason = f"Premium justificado por {', '.join(reason_parts[:2])}"
        else:
            reason = f"Premium parcialmente justificado ({', '.join(reason_parts[:2])})"
    elif adjustment_modifier < 0:
        reason = f"Premium no justificado"
    else:
        reason = None

    return new_adjustment, reason, severity


# =============================================================================
# CONFIGURACIÓN ORIGINAL (preservada)
# =============================================================================

@dataclass
class ThresholdConfig:
    """Configuración de umbrales ajustables por sector."""
    # Valoración
    pe_overvalued_mult: float = 1.3
    pe_undervalued_mult: float = 0.7
    pe_historical_overvalued_mult: float = 1.4
    pe_historical_undervalued_mult: float = 0.6
    p_fcf_high: float = 25.0
    p_fcf_low: float = 10.0
    ev_ebitda_overvalued_mult: float = 1.3
    ev_ebitda_undervalued_mult: float = 0.7
    fcf_yield_low: float = 0.03  # 3%
    fcf_yield_high: float = 0.08  # 8%
    peg_overvalued: float = 2.0
    peg_undervalued: float = 1.0
    
    # Apalancamiento
    net_debt_ebitda_high: float = 4.0
    net_debt_ebitda_low: float = 2.0
    debt_equity_high: float = 1.0
    interest_coverage_low: float = 3.0
    
    # Liquidez
    current_ratio_low: float = 1.0
    current_ratio_high: float = 2.0
    quick_ratio_low: float = 0.7
    
    # Rentabilidad
    roe_high: float = 0.20  # 20%
    roe_low: float = 0.08  # 8%
    roa_high: float = 0.12  # 12% — banda superior sectorial (bancos ~1.2%, tech ~15%)
    roa_low: float = 0.03  # 3%
    operating_margin_low: float = 0.05  # 5%
    net_margin_low: float = 0.03  # 3%
    
    # Volatilidad
    beta_high: float = 1.5
    beta_low: float = 0.8


# Configuraciones predefinidas por sector
SECTOR_THRESHOLDS = {
    "technology": ThresholdConfig(
        pe_overvalued_mult=1.4,
        p_fcf_high=35.0,
        roe_high=0.22,  # Tech tiene ROE alto típico
        roe_low=0.10,
        roa_high=0.15,
        # 0.80 (antes 0.50): con 0.50 la banda severa (-5, penalización máxima)
        # arrancaba en D/E>0.80x, castigando a mega-caps con patrimonio encogido
        # por recompras (AAPL ~1.0x, cobertura 40x) igual que a un sobre-apalancado.
        debt_equity_high=0.80,
        operating_margin_low=0.15,
        net_margin_low=0.10,
    ),
    "utilities": ThresholdConfig(
        pe_overvalued_mult=1.2,
        p_fcf_high=18.0,
        debt_equity_high=1.5,
        roe_high=0.10,  # Utilities tienen ROE bajo típico
        roe_low=0.05,
        roa_high=0.035,  # capital intensivo: ROA 3.5%+ ya es excelente
        roa_low=0.015,
        operating_margin_low=0.12,
        net_margin_low=0.08,
    ),
    "financials": ThresholdConfig(
        pe_overvalued_mult=1.25,
        roe_high=0.12,  # Bancos: ROE más bajo es normal
        roe_low=0.06,
        roa_high=0.012,  # ROA bancario excelente ≈ 1.2%+
        roa_low=0.008,   # Promedio real de bancos US ≈ 1.0-1.3%; mínimo aceptable 0.8%
        debt_equity_high=10.0,  # Los ratios de deuda no aplican igual
        operating_margin_low=0.20,
        net_margin_low=0.15,
    ),
    "healthcare": ThresholdConfig(
        pe_overvalued_mult=1.35,
        p_fcf_high=30.0,
        roe_high=0.18,
        roe_low=0.08,
        operating_margin_low=0.12,
        net_margin_low=0.08,
    ),
    "consumer_cyclical": ThresholdConfig(
        pe_overvalued_mult=1.3,
        current_ratio_low=1.2,
        roe_high=0.18,
        roe_low=0.08,
        operating_margin_low=0.06,
        net_margin_low=0.04,
    ),
    "consumer_defensive": ThresholdConfig(
        pe_overvalued_mult=1.25,
        roe_high=0.20,
        roe_low=0.10,
        debt_equity_high=1.2,
        operating_margin_low=0.10,
        net_margin_low=0.06,
    ),
    "energy": ThresholdConfig(
        pe_overvalued_mult=1.2,
        p_fcf_high=12.0,
        roe_high=0.12,  # Energy: ROE más bajo es normal (capital intensivo)
        roe_low=0.05,
        roa_high=0.06,
        debt_equity_high=0.50,
        operating_margin_low=0.08,
        net_margin_low=0.05,
        fcf_yield_high=0.10,
        fcf_yield_low=0.05,
    ),
    "real_estate": ThresholdConfig(
        pe_overvalued_mult=1.3,
        debt_equity_high=2.0,  # REITs usan más deuda
        roe_high=0.08,
        roe_low=0.03,
        roa_high=0.03,
        roa_low=0.01,
        operating_margin_low=0.25,
        net_margin_low=0.15,
    ),
    "industrials": ThresholdConfig(
        pe_overvalued_mult=1.3,
        roe_high=0.15,
        roe_low=0.08,
        debt_equity_high=0.80,
        operating_margin_low=0.08,
        net_margin_low=0.05,
    ),
    "materials": ThresholdConfig(
        pe_overvalued_mult=1.25,
        roe_high=0.12,
        roe_low=0.05,
        roa_high=0.06,
        debt_equity_high=0.60,
        operating_margin_low=0.10,
        net_margin_low=0.06,
    ),
    "communication": ThresholdConfig(
        pe_overvalued_mult=1.35,
        roe_high=0.15,
        roe_low=0.08,
        debt_equity_high=1.0,
        operating_margin_low=0.15,
        net_margin_low=0.10,
    ),
    "default": ThresholdConfig(),
}


def safe_div(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    """Divide numerator by denominator, returning None if denominator is zero or None."""
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def safe_multiply(*args: Optional[float]) -> Optional[float]:
    """Multiplica valores, retornando None si alguno es None."""
    if any(arg is None for arg in args):
        return None
    result = 1.0
    for arg in args:
        result *= arg
    return result


def safe_subtract(a: Optional[float], b: Optional[float]) -> Optional[float]:
    """Resta b de a, retornando None si alguno es None."""
    if a is None or b is None:
        return None
    return a - b


# =========================
# RATIOS DE RENTABILIDAD
# =========================

def roe(net_income: Optional[float], average_equity: Optional[float]) -> Optional[float]:
    """Return on Equity (ROE) = Net Income / Average Equity."""
    return safe_div(net_income, average_equity)


def roa(net_income: Optional[float], average_assets: Optional[float]) -> Optional[float]:
    """Return on Assets (ROA) = Net Income / Average Total Assets."""
    return safe_div(net_income, average_assets)


def roic(nopat: Optional[float], invested_capital: Optional[float]) -> Optional[float]:
    """Return on Invested Capital (ROIC) = NOPAT / Invested Capital.
    NOPAT = Net Operating Profit After Taxes = EBIT * (1 - Tax Rate)
    Invested Capital = Total Debt + Total Equity - Cash
    """
    return safe_div(nopat, invested_capital)


def operating_margin(operating_income: Optional[float], revenue: Optional[float]) -> Optional[float]:
    """Operating Margin = Operating Income (EBIT) / Revenue."""
    return safe_div(operating_income, revenue)


def gross_margin(gross_profit: Optional[float], revenue: Optional[float]) -> Optional[float]:
    """Gross Margin = Gross Profit / Revenue."""
    return safe_div(gross_profit, revenue)


def net_margin(net_income: Optional[float], revenue: Optional[float]) -> Optional[float]:
    """Net Margin = Net Income / Revenue."""
    return safe_div(net_income, revenue)


def ebitda(operating_income: Optional[float], depreciation: Optional[float], 
           amortization: Optional[float] = 0) -> Optional[float]:
    """EBITDA = Operating Income + Depreciation + Amortization."""
    if operating_income is None or depreciation is None:
        return None
    amort = amortization if amortization is not None else 0
    return operating_income + depreciation + amort


def ebitda_margin(ebitda_value: Optional[float], revenue: Optional[float]) -> Optional[float]:
    """EBITDA Margin = EBITDA / Revenue."""
    return safe_div(ebitda_value, revenue)


# =========================
# RATIOS DE VALORACIÓN
# =========================

def earnings_per_share(net_income: Optional[float], shares_outstanding: Optional[float]) -> Optional[float]:
    """EPS = Net Income / Shares Outstanding."""
    return safe_div(net_income, shares_outstanding)


def price_earnings(price_per_share: Optional[float], eps: Optional[float]) -> Optional[float]:
    """P/E Ratio = Price per Share / Earnings per Share."""
    return safe_div(price_per_share, eps)


def forward_pe(price_per_share: Optional[float], forward_eps: Optional[float]) -> Optional[float]:
    """Forward P/E = Price per Share / Forward EPS Estimate."""
    return safe_div(price_per_share, forward_eps)


def book_value_per_share(total_equity: Optional[float], shares_outstanding: Optional[float]) -> Optional[float]:
    """Book Value per Share = Total Equity / Shares Outstanding."""
    return safe_div(total_equity, shares_outstanding)


def price_book(price_per_share: Optional[float], book_value_ps: Optional[float]) -> Optional[float]:
    """P/B Ratio = Price per Share / Book Value per Share."""
    return safe_div(price_per_share, book_value_ps)


def sales_per_share(revenue: Optional[float], shares_outstanding: Optional[float]) -> Optional[float]:
    """Sales per Share = Revenue / Shares Outstanding."""
    return safe_div(revenue, shares_outstanding)


def price_sales(price_per_share: Optional[float], sales_ps: Optional[float]) -> Optional[float]:
    """P/S Ratio = Price per Share / Sales per Share."""
    return safe_div(price_per_share, sales_ps)


def free_cash_flow(operating_cash_flow: Optional[float], capex: Optional[float]) -> Optional[float]:
    """Free Cash Flow = Operating Cash Flow - Capital Expenditures (CapEx)."""
    return safe_subtract(operating_cash_flow, capex)


def free_cash_flow_per_share(fcf: Optional[float], shares_outstanding: Optional[float]) -> Optional[float]:
    """FCF per Share = Free Cash Flow / Shares Outstanding."""
    return safe_div(fcf, shares_outstanding)


def price_free_cash_flow(price_per_share: Optional[float], fcf_per_share: Optional[float]) -> Optional[float]:
    """P/FCF Ratio = Price per Share / FCF per Share."""
    return safe_div(price_per_share, fcf_per_share)


def market_cap(price_per_share: Optional[float], shares_outstanding: Optional[float]) -> Optional[float]:
    """Market Capitalization = Price per Share * Shares Outstanding."""
    return safe_multiply(price_per_share, shares_outstanding)


def enterprise_value(market_capitalization: Optional[float],
                     total_debt: Optional[float],
                     cash_and_equivalents: Optional[float]) -> Optional[float]:
    """Enterprise Value (EV) = Market Cap + Total Debt - Cash and Equivalents."""
    if market_capitalization is None or total_debt is None or cash_and_equivalents is None:
        return None
    return market_capitalization + total_debt - cash_and_equivalents


def ev_ebitda(ev: Optional[float], ebitda_value: Optional[float]) -> Optional[float]:
    """EV/EBITDA = Enterprise Value / EBITDA."""
    return safe_div(ev, ebitda_value)


def ev_revenue(ev: Optional[float], revenue: Optional[float]) -> Optional[float]:
    """EV/Revenue = Enterprise Value / Revenue."""
    return safe_div(ev, revenue)


def ev_fcf(ev: Optional[float], fcf: Optional[float]) -> Optional[float]:
    """EV/FCF = Enterprise Value / Free Cash Flow."""
    return safe_div(ev, fcf)


def peg_ratio(pe: Optional[float], earnings_growth_rate_pct: Optional[float]) -> Optional[float]:
    """PEG Ratio = P/E / Earnings Growth Rate (%).
    earnings_growth_rate_pct must be expressed as a percentage (e.g., 15 for 15%).
    """
    if pe is None or earnings_growth_rate_pct is None or earnings_growth_rate_pct <= 0:
        return None
    return safe_div(pe, earnings_growth_rate_pct)


def free_cash_flow_yield(fcf: Optional[float], market_capitalization: Optional[float]) -> Optional[float]:
    """FCF Yield = Free Cash Flow / Market Capitalization."""
    return safe_div(fcf, market_capitalization)


def dividend_yield(dividend_per_share: Optional[float], price_per_share: Optional[float]) -> Optional[float]:
    """Dividend Yield = Annual Dividend per Share / Price per Share."""
    return safe_div(dividend_per_share, price_per_share)


def dividend_payout_ratio(dividends: Optional[float], net_income: Optional[float]) -> Optional[float]:
    """Dividend Payout Ratio = Total Dividends / Net Income."""
    return safe_div(dividends, net_income)


# =========================
# MÉTRICAS PARA REITs
# =========================

def funds_from_operations(
    net_income: Optional[float],
    depreciation: Optional[float],
    gains_on_sale: Optional[float] = 0
) -> Optional[float]:
    """
    FFO (Funds From Operations) - Métrica principal para REITs.
    
    FFO = Net Income + Depreciation & Amortization - Gains on Sale of Property
    
    Es más relevante que Net Income para REITs porque:
    - La depreciación inmobiliaria no refleja la pérdida real de valor
    - Los inmuebles tienden a apreciarse, no depreciarse
    
    Args:
        net_income: Ingreso neto
        depreciation: Depreciación y amortización
        gains_on_sale: Ganancias por venta de propiedades (se resta)
    
    Returns:
        FFO o None si datos insuficientes
    """
    if net_income is None or depreciation is None:
        return None
    
    gains = gains_on_sale or 0
    return net_income + depreciation - gains



def ffo_payout_ratio(dividends: Optional[float], ffo: Optional[float]) -> Optional[float]:
    """
    FFO Payout Ratio - Porcentaje de FFO pagado como dividendo.
    
    Para REITs, debe ser < 100% para ser sostenible.
    REITs deben distribuir 90%+ de ingresos por ley, pero basado en FFO es más relevante.
    
    Args:
        dividends: Dividendos totales pagados
        ffo: Funds From Operations
    
    Returns:
        Ratio o None
    """
    return safe_div(dividends, ffo)


def price_to_ffo(price: Optional[float], ffo_per_share: Optional[float]) -> Optional[float]:
    """
    P/FFO - Equivalente al P/E pero para REITs.
    
    Rangos típicos:
    - < 12: Potencialmente barato
    - 12-18: Rango normal
    - > 18: Caro o alta calidad
    
    Args:
        price: Precio por acción
        ffo_per_share: FFO por acción
    
    Returns:
        P/FFO ratio o None
    """
    return safe_div(price, ffo_per_share)


def earnings_yield(eps: Optional[float], price_per_share: Optional[float]) -> Optional[float]:
    """Earnings Yield = EPS / Price per Share (inverso del P/E)."""
    return safe_div(eps, price_per_share)


# =========================
# RATIOS DE LIQUIDEZ
# =========================

def current_ratio(current_assets: Optional[float], current_liabilities: Optional[float]) -> Optional[float]:
    """Current Ratio = Current Assets / Current Liabilities."""
    return safe_div(current_assets, current_liabilities)


def quick_ratio(current_assets: Optional[float], inventories: Optional[float], 
                current_liabilities: Optional[float]) -> Optional[float]:
    """Quick Ratio = (Current Assets - Inventories) / Current Liabilities."""
    if current_assets is None or inventories is None:
        return None
    return safe_div(current_assets - inventories, current_liabilities)


def cash_ratio(cash_and_equivalents: Optional[float], current_liabilities: Optional[float]) -> Optional[float]:
    """Cash Ratio = Cash and Equivalents / Current Liabilities."""
    return safe_div(cash_and_equivalents, current_liabilities)


def working_capital(current_assets: Optional[float], current_liabilities: Optional[float]) -> Optional[float]:
    """Working Capital = Current Assets - Current Liabilities."""
    return safe_subtract(current_assets, current_liabilities)


# =========================
# RATIOS DE SOLVENCIA / ENDEUDAMIENTO
# =========================

def debt_to_equity(total_debt: Optional[float], total_equity: Optional[float]) -> Optional[float]:
    """Debt/Equity = Total Debt / Total Equity."""
    return safe_div(total_debt, total_equity)


def debt_to_assets(total_debt: Optional[float], total_assets: Optional[float]) -> Optional[float]:
    """Debt/Assets = Total Debt / Total Assets."""
    return safe_div(total_debt, total_assets)


def net_debt(total_debt: Optional[float], cash_and_equivalents: Optional[float]) -> Optional[float]:
    """Net Debt = Total Debt - Cash and Equivalents."""
    return safe_subtract(total_debt, cash_and_equivalents)


def net_debt_to_ebitda(net_debt_value: Optional[float], ebitda_value: Optional[float]) -> Optional[float]:
    """Net Debt/EBITDA = Net Debt / EBITDA."""
    return safe_div(net_debt_value, ebitda_value)


def interest_coverage(ebit: Optional[float], interest_expense: Optional[float]) -> Optional[float]:
    """Interest Coverage = EBIT / Interest Expense."""
    return safe_div(ebit, interest_expense)


# =========================
# RATIOS DE EFICIENCIA
# =========================

def asset_turnover(revenue: Optional[float], average_total_assets: Optional[float]) -> Optional[float]:
    """Asset Turnover = Revenue / Average Total Assets."""
    return safe_div(revenue, average_total_assets)


def inventory_turnover(cost_of_goods_sold: Optional[float], average_inventory: Optional[float]) -> Optional[float]:
    """Inventory Turnover = Cost of Goods Sold / Average Inventory."""
    return safe_div(cost_of_goods_sold, average_inventory)




# =========================
# SISTEMA DE SEVERIDAD DE ALERTAS v1.0
# =========================

def classify_valuation_alert_severity(
    pe_ratio: Optional[float],
    p_fcf: Optional[float],
    ev_ebitda: Optional[float],
    sector_pe: Optional[float] = None,
    sector_ev_ebitda: Optional[float] = None,
    thresholds: 'ThresholdConfig' = None
) -> Dict[str, Any]:
    """
    Clasifica alertas de valoración con severidad proporcional.
    
    Returns:
        Dict con alertas clasificadas por severidad y penalización total sugerida
    """
    if thresholds is None:
        thresholds = ThresholdConfig()
    
    alerts = {
        "minor": [],      # Penalización: -2 cada una
        "moderate": [],   # Penalización: -4 cada una
        "severe": [],     # Penalización: -6 cada una
        "total_penalty": 0,
        "details": []
    }
    
    # P/E Ratio - Solo evaluar si tenemos referencia sectorial
    if pe_ratio is not None and pe_ratio > 0:
        # Usar sector_pe como base si existe, si no usar umbral genérico de 25x
        if sector_pe and sector_pe > 0:
            pe_threshold = sector_pe * thresholds.pe_overvalued_mult
        else:
            pe_threshold = 25.0  # Umbral genérico si no hay dato sectorial
        
        if pe_ratio > pe_threshold:
            deviation = (pe_ratio - pe_threshold) / pe_threshold
            if deviation <= 0.15:
                alerts["minor"].append(f"P/E ({pe_ratio:.1f}x) ligeramente elevado")
                alerts["total_penalty"] += 2
            elif deviation <= 0.40:
                alerts["moderate"].append(f"P/E ({pe_ratio:.1f}x) significativamente alto")
                alerts["total_penalty"] += 4
            else:
                alerts["severe"].append(f"P/E ({pe_ratio:.1f}x) extremadamente alto")
                alerts["total_penalty"] += 6
            
            alerts["details"].append({
                "metric": "P/E",
                "value": pe_ratio,
                "threshold": pe_threshold,
                "deviation_pct": deviation * 100,
                "severity": "minor" if deviation <= 0.15 else ("moderate" if deviation <= 0.40 else "severe")
            })
    
    # P/FCF
    if p_fcf is not None and p_fcf > thresholds.p_fcf_high:
        deviation = (p_fcf - thresholds.p_fcf_high) / thresholds.p_fcf_high
        if deviation <= 0.20:
            alerts["minor"].append(f"P/FCF ({p_fcf:.1f}x) ligeramente alto")
            alerts["total_penalty"] += 2
        elif deviation <= 0.50:
            alerts["moderate"].append(f"P/FCF ({p_fcf:.1f}x) alto")
            alerts["total_penalty"] += 4
        else:
            alerts["severe"].append(f"P/FCF ({p_fcf:.1f}x) muy alto")
            alerts["total_penalty"] += 6
        
        alerts["details"].append({
            "metric": "P/FCF",
            "value": p_fcf,
            "threshold": thresholds.p_fcf_high,
            "deviation_pct": deviation * 100,
            "severity": "minor" if deviation <= 0.20 else ("moderate" if deviation <= 0.50 else "severe")
        })
    
    # EV/EBITDA
    if ev_ebitda is not None and sector_ev_ebitda is not None:
        ev_threshold = sector_ev_ebitda * 1.3  # 30% sobre sector
        if ev_ebitda > ev_threshold:
            deviation = (ev_ebitda - ev_threshold) / ev_threshold
            if deviation <= 0.15:
                alerts["minor"].append(f"EV/EBITDA ({ev_ebitda:.1f}x) algo elevado vs sector")
                alerts["total_penalty"] += 2
            elif deviation <= 0.35:
                alerts["moderate"].append(f"EV/EBITDA ({ev_ebitda:.1f}x) significativamente > sector")
                alerts["total_penalty"] += 4
            else:
                alerts["severe"].append(f"EV/EBITDA ({ev_ebitda:.1f}x) muy > sector")
                alerts["total_penalty"] += 6
            
            alerts["details"].append({
                "metric": "EV/EBITDA",
                "value": ev_ebitda,
                "threshold": ev_threshold,
                "sector_value": sector_ev_ebitda,
                "deviation_pct": deviation * 100,
                "severity": "minor" if deviation <= 0.15 else ("moderate" if deviation <= 0.35 else "severe")
            })
    
    return alerts


def classify_all_alerts_severity(
    ratio_values: Dict[str, Optional[float]],
    contextual_values: Dict[str, Optional[float]],
    thresholds: 'ThresholdConfig',
    val_flags: Dict,
    lev_flags: Dict,
    liq_flags: Dict,
    prof_flags: Dict,
    cf_flags: Dict
) -> Dict[str, Any]:
    """
    Clasifica TODAS las alertas del modelo por severidad.
    
    Returns:
        Dict con conteo por severidad, penalización total, y CAP recomendado
    """
    result = {
        "risks": {
            "minor": [],
            "moderate": [],
            "severe": []
        },
        "risk_count": 0,
        "total_risk_penalty": 0,
        "score_cap": 100,  # CAP máximo permitido
        "severity_breakdown": {}
    }
    
    # --- Alertas de VALORACIÓN ---
    pe = ratio_values.get("pe")
    p_fcf = ratio_values.get("p_fcf")
    ev_ebitda = ratio_values.get("ev_ebitda")
    sector_pe = contextual_values.get("sector_pe")
    sector_ev_ebitda = contextual_values.get("sector_ev_ebitda")
    
    val_severity = classify_valuation_alert_severity(
        pe, p_fcf, ev_ebitda, sector_pe, sector_ev_ebitda, thresholds
    )
    
    result["risks"]["minor"].extend(val_severity["minor"])
    result["risks"]["moderate"].extend(val_severity["moderate"])
    result["risks"]["severe"].extend(val_severity["severe"])
    result["total_risk_penalty"] += val_severity["total_penalty"]
    result["severity_breakdown"]["valuation"] = val_severity
    
    # --- Alertas de APALANCAMIENTO ---
    if lev_flags.get("overleveraged_flag"):
        de_ratio = ratio_values.get("debt_to_equity", 0)
        de_threshold = thresholds.debt_equity_high
        
        if de_ratio and de_ratio > de_threshold:
            deviation = (de_ratio - de_threshold) / de_threshold if de_threshold > 0 else 1.0
            if deviation <= 0.25:
                result["risks"]["minor"].append(f"D/E ({de_ratio:.2f}x) algo elevado")
                result["total_risk_penalty"] += 2
            elif deviation <= 0.60:
                result["risks"]["moderate"].append(f"D/E ({de_ratio:.2f}x) significativamente alto")
                result["total_risk_penalty"] += 4
            else:
                result["risks"]["severe"].append(f"D/E ({de_ratio:.2f}x) crítico")
                result["total_risk_penalty"] += 6
    
    # --- Alertas de LIQUIDEZ ---
    if liq_flags.get("weak_liquidity_flag"):
        current = ratio_values.get("current_ratio", 0)
        if current < 0.8:
            result["risks"]["severe"].append(f"Liquidez crítica (Current Ratio: {current:.2f})")
            result["total_risk_penalty"] += 6
        elif current < 1.0:
            result["risks"]["moderate"].append(f"Liquidez débil (Current Ratio: {current:.2f})")
            result["total_risk_penalty"] += 4
        else:
            result["risks"]["minor"].append(f"Liquidez ajustada (Current Ratio: {current:.2f})")
            result["total_risk_penalty"] += 2
    
    # --- Alertas de RENTABILIDAD ---
    if prof_flags.get("weak_profitability_flag"):
        roe_val = ratio_values.get("roe")
        net_margin_val = ratio_values.get("net_margin")
        
        if roe_val is not None and roe_val < 0:
            result["risks"]["severe"].append(f"ROE negativo ({roe_val*100:.1f}%)")
            result["total_risk_penalty"] += 6
        elif roe_val is not None and roe_val < 0.05:
            result["risks"]["moderate"].append(f"ROE muy bajo ({roe_val*100:.1f}%)")
            result["total_risk_penalty"] += 4
        elif net_margin_val is not None and net_margin_val < 0:
            result["risks"]["severe"].append("Margen neto negativo")
            result["total_risk_penalty"] += 6
    
    # --- Alertas de CASH FLOW ---
    if cf_flags.get("problematic_cash_flow_flag"):
        fcf = ratio_values.get("fcf")
        ocf = contextual_values.get("operating_cash_flow")
        
        if ocf is not None and ocf < 0:
            result["risks"]["severe"].append("Cash Flow Operativo negativo")
            result["total_risk_penalty"] += 6
        elif fcf is not None and fcf < 0:
            result["risks"]["moderate"].append("Free Cash Flow negativo")
            result["total_risk_penalty"] += 4
    
    # Contar riesgos totales
    result["risk_count"] = (
        len(result["risks"]["minor"]) + 
        len(result["risks"]["moderate"]) + 
        len(result["risks"]["severe"])
    )
    
    # Determinar CAP dinámico basado en severidad
    severe_count = len(result["risks"]["severe"])
    moderate_count = len(result["risks"]["moderate"])
    minor_count = len(result["risks"]["minor"])
    
    if severe_count >= 2:
        result["score_cap"] = 70  # Múltiples riesgos severos
    elif severe_count >= 1:
        result["score_cap"] = 80  # Al menos un riesgo severo
    elif moderate_count >= 3:
        result["score_cap"] = 80  # Varios riesgos moderados
    elif moderate_count >= 1 or minor_count >= 2:
        result["score_cap"] = 90  # Riesgos moderados o varios menores
    # else: mantiene 100
    
    return result

def graham_number(eps: Optional[float], book_value_ps: Optional[float]) -> Optional[float]:
    """Graham Number = sqrt(22.5 × EPS × Book Value per Share).
    Precio máximo a pagar según Benjamin Graham.
    """
    if eps is None or book_value_ps is None:
        return None
    if eps <= 0 or book_value_ps <= 0:
        return None
    return (22.5 * eps * book_value_ps) ** 0.5


def dcf_multi_stage(
    fcf: Optional[float],
    shares_outstanding: Optional[float],
    high_growth_rate: float = 0.15,
    high_growth_years: int = DCF_HIGH_GROWTH_YEARS,
    transition_years: int = DCF_TRANSITION_YEARS,
    terminal_growth: float = DCF_TERMINAL_GROWTH,
    discount_rate: float = DCF_WACC_DEFAULT,
    decay_type: str = "linear",
    margin_of_safety_pct: float = 0.0,
    net_debt: Optional[float] = 0.0,
) -> Dict[str, Any]:
    """
    DCF Multi-Stage (3 etapas) - Modelo más realista.
    
    Etapas:
    - Etapa 1 (High Growth): Años 1-5, crecimiento alto con decay gradual
    - Etapa 2 (Transition): Años 6-10, convergencia hacia terminal growth
    - Etapa 3 (Terminal): Año 10+, perpetuidad con Gordon Growth Model
    """
    result = {
        "fair_value_per_share": None,
        "fair_value_with_mos": None,
        "enterprise_value": None,
        "equity_value": None,
        "net_debt": net_debt,
        "method": "multi_stage_dcf",
        "stages": {
            "high_growth": {"pv": None, "years": high_growth_years, "rates": []},
            "transition": {"pv": None, "years": transition_years, "rates": []},
            "terminal": {"pv": None, "terminal_value": None}
        },
        "inputs": {
            "fcf": fcf,
            "high_growth_rate": high_growth_rate,
            "terminal_growth": terminal_growth,
            "discount_rate": discount_rate,
            "decay_type": decay_type,
            "total_years": high_growth_years + transition_years
        },
        "warnings": [],
        "is_valid": False
    }
    
    # Validaciones
    if fcf is None or shares_outstanding is None:
        result["warnings"].append("FCF o shares no disponibles")
        return result
    
    if shares_outstanding <= 0:
        result["warnings"].append("Shares outstanding debe ser positivo")
        return result
    
    if fcf <= 0:
        result["warnings"].append("FCF negativo - considerar usar EV/EBITDA")
        return result
    
    if discount_rate <= terminal_growth:
        result["warnings"].append(f"Discount rate debe ser > terminal growth")
        return result
    
    if high_growth_rate < terminal_growth:
        high_growth_rate = terminal_growth
    
    MAX_GROWTH = 0.50
    if high_growth_rate > MAX_GROWTH:
        result["warnings"].append(f"Growth capped de {high_growth_rate:.1%} a {MAX_GROWTH:.1%}")
        high_growth_rate = MAX_GROWTH
    
    # ETAPA 1: Alto Crecimiento
    pv_stage1 = 0.0
    projected_fcf = fcf
    stage1_rates = []
    
    if decay_type == "linear" and high_growth_years > 1:
        yearly_decay = (high_growth_rate - terminal_growth) / (high_growth_years + transition_years)
    else:
        yearly_decay = 0
    
    decay_factor = 0.85 if decay_type == "exponential" else 1.0
    
    for year in range(1, high_growth_years + 1):
        if decay_type == "linear":
            year_growth = high_growth_rate - (yearly_decay * (year - 1))
        elif decay_type == "exponential":
            year_growth = terminal_growth + (high_growth_rate - terminal_growth) * (decay_factor ** (year - 1))
        else:
            year_growth = high_growth_rate
        
        year_growth = max(year_growth, terminal_growth)
        stage1_rates.append(year_growth)
        projected_fcf *= (1 + year_growth)
        pv_stage1 += projected_fcf / ((1 + discount_rate) ** year)
    
    result["stages"]["high_growth"]["pv"] = round(pv_stage1, 2)
    result["stages"]["high_growth"]["rates"] = [round(r, 4) for r in stage1_rates]
    
    # ETAPA 2: Transición
    pv_stage2 = 0.0
    stage2_rates = []
    end_stage1_growth = stage1_rates[-1] if stage1_rates else high_growth_rate
    
    if transition_years > 0:
        transition_decay = (end_stage1_growth - terminal_growth) / transition_years
    else:
        transition_decay = 0
    
    for i, year in enumerate(range(high_growth_years + 1, high_growth_years + transition_years + 1)):
        year_growth = end_stage1_growth - (transition_decay * (i + 1))
        year_growth = max(year_growth, terminal_growth)
        stage2_rates.append(year_growth)
        projected_fcf *= (1 + year_growth)
        pv_stage2 += projected_fcf / ((1 + discount_rate) ** year)
    
    result["stages"]["transition"]["pv"] = round(pv_stage2, 2)
    result["stages"]["transition"]["rates"] = [round(r, 4) for r in stage2_rates]
    
    # ETAPA 3: Valor Terminal
    total_projection_years = high_growth_years + transition_years
    terminal_fcf = projected_fcf * (1 + terminal_growth)
    terminal_value = terminal_fcf / (discount_rate - terminal_growth)
    pv_terminal = terminal_value / ((1 + discount_rate) ** total_projection_years)
    
    result["stages"]["terminal"]["terminal_value"] = round(terminal_value, 2)
    result["stages"]["terminal"]["pv"] = round(pv_terminal, 2)
    
    # CÁLCULO FINAL
    # Puente Enterprise Value -> Equity Value: descontar el FCF de la firma (FCFF)
    # al WACC produce el valor de la EMPRESA (enterprise value). El precio por
    # acción corresponde al EQUITY, así que hay que restar la deuda neta
    # (deuda total - caja) antes de dividir entre las acciones. Sin este puente
    # las empresas apalancadas quedan sistemáticamente sobrevaloradas (y las de
    # caja neta, subvaloradas).
    enterprise_value = pv_stage1 + pv_stage2 + pv_terminal
    equity_value = enterprise_value - (net_debt or 0.0)
    if equity_value <= 0:
        result["warnings"].append(
            "Equity value <= 0 tras restar la deuda neta (empresa muy apalancada)"
        )
    fair_value_per_share = equity_value / shares_outstanding

    if margin_of_safety_pct > 0:
        fair_value_with_mos = fair_value_per_share * (1 - margin_of_safety_pct)
    else:
        fair_value_with_mos = fair_value_per_share

    result["enterprise_value"] = round(enterprise_value, 2)
    result["equity_value"] = round(equity_value, 2)
    result["net_debt"] = round(net_debt or 0.0, 2)
    result["fair_value_per_share"] = round(fair_value_per_share, 2)
    result["fair_value_with_mos"] = round(fair_value_with_mos, 2)
    result["is_valid"] = True
    
    total_pv = pv_stage1 + pv_stage2 + pv_terminal
    result["value_composition"] = {
        "stage1_pct": round(pv_stage1 / total_pv * 100, 1),
        "stage2_pct": round(pv_stage2 / total_pv * 100, 1),
        "terminal_pct": round(pv_terminal / total_pv * 100, 1)
    }
    
    if result["value_composition"]["terminal_pct"] > 75:
        result["warnings"].append(
            f"Terminal value representa {result['value_composition']['terminal_pct']:.0f}% del valor"
        )
    
    return result


def dcf_multi_stage_dynamic(
    fcf: Optional[float],
    shares_outstanding: Optional[float],
    beta: Optional[float] = None,
    debt_to_equity: Optional[float] = None,
    interest_expense: Optional[float] = None,
    total_debt: Optional[float] = None,
    cash: Optional[float] = None,
    revenue_growth_3y: Optional[float] = None,
    eps_growth_3y: Optional[float] = None,
    fcf_growth_3y: Optional[float] = None,
    risk_free_rate: float = DCF_RISK_FREE_RATE,
    market_risk_premium: float = DCF_MARKET_RISK_PREMIUM,
    terminal_growth: float = DCF_TERMINAL_GROWTH,
    high_growth_years: int = DCF_HIGH_GROWTH_YEARS,
    transition_years: int = DCF_TRANSITION_YEARS,
    margin_of_safety_pct: float = 0.0,
) -> Dict[str, Any]:
    """
    DCF Multi-Stage Dinámico - Combina modelo de 3 etapas con 
    WACC y growth calculados dinámicamente.
    """
    result = {
        "fair_value_per_share": None,
        "fair_value_with_mos": None,
        "wacc_calculated": None,
        "growth_estimated": None,
        "growth_source": None,
        "method": "multi_stage_dcf_dynamic",
        "model_result": None,
        "net_debt": None,
        "warnings": [],
        "is_valid": False,
        "sensitivity_analysis": None
    }
    
    if fcf is None or shares_outstanding is None or shares_outstanding <= 0:
        result["warnings"].append("FCF o shares no disponibles")
        return result
    
    if fcf <= 0:
        result["warnings"].append("FCF negativo - DCF no aplicable")
        return result
    
    # CALCULAR WACC
    wacc = calculate_wacc(
        beta=beta,
        risk_free_rate=risk_free_rate,
        market_risk_premium=market_risk_premium,
        debt_to_equity=debt_to_equity,
        interest_expense=interest_expense,
        total_debt=total_debt
    )
    
    if wacc is None:
        wacc = 0.10
        result["warnings"].append("WACC estimado en 10%")
    
    wacc = max(0.06, min(wacc, 0.20))
    result["wacc_calculated"] = wacc

    # Deuda neta para el puente Enterprise Value -> Equity Value en dcf_multi_stage.
    # Solo se calcula si hay algún dato de deuda o caja; si no, queda None y el
    # DCF se comporta como antes (sin puente) para no inventar una deuda de 0.
    net_debt = None
    if total_debt is not None or cash is not None:
        net_debt = (total_debt or 0.0) - (cash or 0.0)
    result["net_debt"] = net_debt

    # ESTIMAR GROWTH
    growth_rate = None
    growth_source = None
    
    growth_candidates = [
        (fcf_growth_3y, "fcf_growth_3y", 0.35),
        (eps_growth_3y, "eps_growth_3y", 0.40),
        (revenue_growth_3y, "revenue_growth_3y", 0.30),
    ]
    
    for growth_val, source, cap in growth_candidates:
        if growth_val is not None and growth_val > -0.20:
            growth_rate = min(growth_val, cap)
            growth_rate = max(growth_rate, terminal_growth)
            growth_source = source
            break
    
    if growth_rate is None:
        growth_rate = 0.08
        growth_source = "default_estimate"
        result["warnings"].append("Growth estimado en 8%")
    
    result["growth_estimated"] = growth_rate
    result["growth_source"] = growth_source
    
    # EJECUTAR DCF MULTI-STAGE
    if growth_rate > 0.25:
        decay_type = "exponential"
    elif growth_rate > 0.15:
        decay_type = "linear"
    else:
        decay_type = "step"
    
    model_result = dcf_multi_stage(
        fcf=fcf,
        shares_outstanding=shares_outstanding,
        high_growth_rate=growth_rate,
        high_growth_years=high_growth_years,
        transition_years=transition_years,
        terminal_growth=terminal_growth,
        discount_rate=wacc,
        decay_type=decay_type,
        margin_of_safety_pct=margin_of_safety_pct,
        net_debt=net_debt
    )
    
    result["model_result"] = model_result
    result["warnings"].extend(model_result.get("warnings", []))
    
    if model_result["is_valid"]:
        result["fair_value_per_share"] = model_result["fair_value_per_share"]
        result["fair_value_with_mos"] = model_result["fair_value_with_mos"]
        result["is_valid"] = True
        
        # ANÁLISIS DE SENSIBILIDAD
        sensitivity = {"wacc_sensitivity": {}, "growth_sensitivity": {}}
        
        for wacc_delta in [-0.02, -0.01, 0.01, 0.02]:
            test_wacc = wacc + wacc_delta
            if test_wacc > terminal_growth + 0.01:
                test_result = dcf_multi_stage(
                    fcf=fcf, shares_outstanding=shares_outstanding,
                    high_growth_rate=growth_rate, discount_rate=test_wacc,
                    terminal_growth=terminal_growth, decay_type=decay_type,
                    net_debt=net_debt
                )
                if test_result["is_valid"]:
                    sensitivity["wacc_sensitivity"][f"{wacc_delta:+.0%}"] = test_result["fair_value_per_share"]
        
        for growth_delta in [-0.05, -0.025, 0.025, 0.05]:
            test_growth = max(growth_rate + growth_delta, terminal_growth)
            test_result = dcf_multi_stage(
                fcf=fcf, shares_outstanding=shares_outstanding,
                high_growth_rate=test_growth, discount_rate=wacc,
                terminal_growth=terminal_growth, decay_type=decay_type,
                net_debt=net_debt
            )
            if test_result["is_valid"]:
                sensitivity["growth_sensitivity"][f"{growth_delta:+.1%}"] = test_result["fair_value_per_share"]
        
        result["sensitivity_analysis"] = sensitivity
    
    return result


def margin_of_safety(intrinsic_value: Optional[float], current_price: Optional[float]) -> Optional[float]:
    """Margin of Safety = (Intrinsic Value - Current Price) / Intrinsic Value.
    Positivo indica subvaloración, negativo indica sobrevaloración.
    """
    if intrinsic_value is None or current_price is None or intrinsic_value == 0:
        return None
    return (intrinsic_value - current_price) / intrinsic_value


# =========================
# REGLAS DE CRITICIDAD / ALERTAS
# =========================

def valuation_flags(
    pe: Optional[float] = None,
    sector_pe: Optional[float] = None,
    pe_5y_avg: Optional[float] = None,
    p_fcf: Optional[float] = None,
    ev_ebitda_value: Optional[float] = None,
    sector_ev_ebitda: Optional[float] = None,
    fcf_yield_value: Optional[float] = None,
    peg: Optional[float] = None,
    pb: Optional[float] = None,
    thresholds: ThresholdConfig = None,
) -> Dict[str, Any]:
    """Reglas para sobrevaloración / infravaloración con umbrales configurables."""
    t = thresholds or ThresholdConfig()
    
    overvalued_reasons = []
    undervalued_reasons = []

    # P/E análisis
    if pe is not None:
        # P/E negativo indica pérdidas
        if pe < 0:
            overvalued_reasons.append(f"P/E negativo ({pe:.1f}) - empresa con pérdidas")
        else:
            # P/E extremadamente alto (>50) es señal de sobrevaloración independiente del sector
            if pe > 50:
                overvalued_reasons.append(f"P/E muy alto ({pe:.1f}) > 50")
            elif pe > 35:
                overvalued_reasons.append(f"P/E elevado ({pe:.1f}) > 35")
            
            # Comparación con sector
            if sector_pe is not None and sector_pe > 0:
                if pe > t.pe_overvalued_mult * sector_pe:
                    overvalued_reasons.append(f"P/E ({pe:.1f}) > {t.pe_overvalued_mult}x sector ({sector_pe:.1f})")
                if pe < t.pe_undervalued_mult * sector_pe:
                    undervalued_reasons.append(f"P/E ({pe:.1f}) < {t.pe_undervalued_mult}x sector ({sector_pe:.1f})")
            
            # Comparación histórica
            if pe_5y_avg is not None and pe_5y_avg > 0:
                if pe > t.pe_historical_overvalued_mult * pe_5y_avg:
                    overvalued_reasons.append(f"P/E ({pe:.1f}) > {t.pe_historical_overvalued_mult}x promedio 5 años ({pe_5y_avg:.1f})")
                if pe < t.pe_historical_undervalued_mult * pe_5y_avg:
                    undervalued_reasons.append(f"P/E ({pe:.1f}) < {t.pe_historical_undervalued_mult}x promedio 5 años ({pe_5y_avg:.1f})")

    # P/FCF - importante para validar calidad de ganancias
    if p_fcf is not None:
        if p_fcf < 0:
            overvalued_reasons.append("P/FCF negativo - FCF negativo es señal de alerta")
        elif p_fcf > 50:
            overvalued_reasons.append(f"P/FCF muy alto ({p_fcf:.1f}) > 50")
        elif p_fcf > t.p_fcf_high:
            overvalued_reasons.append(f"P/FCF ({p_fcf:.1f}) > {t.p_fcf_high}")
        elif p_fcf < t.p_fcf_low and p_fcf > 0:
            undervalued_reasons.append(f"P/FCF ({p_fcf:.1f}) < {t.p_fcf_low}")

    # EV/EBITDA vs sector
    if ev_ebitda_value is not None:
        if ev_ebitda_value > 25:
            overvalued_reasons.append(f"EV/EBITDA muy alto ({ev_ebitda_value:.1f}) > 25")
        elif sector_ev_ebitda is not None and sector_ev_ebitda > 0:
            if ev_ebitda_value > t.ev_ebitda_overvalued_mult * sector_ev_ebitda:
                overvalued_reasons.append(f"EV/EBITDA ({ev_ebitda_value:.1f}) > {t.ev_ebitda_overvalued_mult}x sector ({sector_ev_ebitda:.1f})")
            if ev_ebitda_value < t.ev_ebitda_undervalued_mult * sector_ev_ebitda:
                undervalued_reasons.append(f"EV/EBITDA ({ev_ebitda_value:.1f}) < {t.ev_ebitda_undervalued_mult}x sector ({sector_ev_ebitda:.1f})")

    # FCF Yield
    if fcf_yield_value is not None:
        if fcf_yield_value < 0:
            overvalued_reasons.append("FCF Yield negativo - empresa quema efectivo")
        elif fcf_yield_value < t.fcf_yield_low:
            overvalued_reasons.append(f"FCF Yield ({fcf_yield_value:.1%}) < {t.fcf_yield_low:.0%}")
        elif fcf_yield_value > t.fcf_yield_high:
            undervalued_reasons.append(f"FCF Yield ({fcf_yield_value:.1%}) > {t.fcf_yield_high:.0%}")

    # PEG Ratio
    if peg is not None and peg > 0:
        if peg > t.peg_overvalued:
            overvalued_reasons.append(f"PEG ({peg:.2f}) > {t.peg_overvalued}")
        if peg < t.peg_undervalued:
            undervalued_reasons.append(f"PEG ({peg:.2f}) < {t.peg_undervalued}")

    # P/B muy alto puede indicar sobrevaloración
    if pb is not None and pb > 10:
        overvalued_reasons.append(f"P/B muy alto ({pb:.1f}) > 10")

    has_overvalued = len(overvalued_reasons) > 0
    has_undervalued = len(undervalued_reasons) > 0

    return {
        "overvalued_flag": has_overvalued and not has_undervalued,
        "undervalued_flag": has_undervalued and not has_overvalued,
        "mixed_signals_flag": has_overvalued and has_undervalued,
        "overvalued_reasons": overvalued_reasons,
        "undervalued_reasons": undervalued_reasons,
    }


def leverage_flags(
    debt_to_equity_value: Optional[float] = None,
    net_debt_to_ebitda_value: Optional[float] = None,
    interest_coverage_value: Optional[float] = None,
    debt_to_assets_value: Optional[float] = None,
    thresholds: ThresholdConfig = None,
) -> Dict[str, Any]:
    """Reglas para identificar sobreapalancamiento y solidez financiera."""
    t = thresholds or ThresholdConfig()
    
    warning_reasons = []
    positive_reasons = []

    if net_debt_to_ebitda_value is not None:
        if net_debt_to_ebitda_value > t.net_debt_ebitda_high:
            warning_reasons.append(f"Deuda Neta/EBITDA ({net_debt_to_ebitda_value:.1f}) > {t.net_debt_ebitda_high}")
        elif net_debt_to_ebitda_value < t.net_debt_ebitda_low:
            positive_reasons.append(f"Deuda Neta/EBITDA ({net_debt_to_ebitda_value:.1f}) < {t.net_debt_ebitda_low}")
        # Deuda neta negativa = más cash que deuda
        if net_debt_to_ebitda_value < 0:
            positive_reasons.append("Posición de caja neta (más efectivo que deuda)")

    if debt_to_equity_value is not None and debt_to_equity_value > t.debt_equity_high:
        warning_reasons.append(f"Deuda/Equity ({debt_to_equity_value:.2f}) > {t.debt_equity_high}")

    if interest_coverage_value is not None:
        if interest_coverage_value < t.interest_coverage_low:
            warning_reasons.append(f"Cobertura de intereses ({interest_coverage_value:.1f}x) < {t.interest_coverage_low}x")
        elif interest_coverage_value > 10:
            positive_reasons.append(f"Excelente cobertura de intereses ({interest_coverage_value:.1f}x)")

    if debt_to_assets_value is not None and debt_to_assets_value > 0.6:
        warning_reasons.append(f"Deuda/Activos ({debt_to_assets_value:.1%}) > 60%")

    return {
        "overleveraged_flag": len(warning_reasons) > 0,
        "conservative_leverage_flag": len(positive_reasons) > 0 and len(warning_reasons) == 0,
        "warning_reasons": warning_reasons,
        "positive_reasons": positive_reasons,
    }


def liquidity_flags(
    current_ratio_value: Optional[float] = None,
    quick_ratio_value: Optional[float] = None,
    cash_ratio_value: Optional[float] = None,
    thresholds: ThresholdConfig = None,
) -> Dict[str, Any]:
    """Reglas para identificar problemas de liquidez de corto plazo."""
    t = thresholds or ThresholdConfig()
    
    warning_reasons = []
    positive_reasons = []

    if current_ratio_value is not None:
        if current_ratio_value < t.current_ratio_low:
            warning_reasons.append(f"Current Ratio ({current_ratio_value:.2f}) < {t.current_ratio_low}")
        elif current_ratio_value > t.current_ratio_high:
            positive_reasons.append(f"Current Ratio ({current_ratio_value:.2f}) > {t.current_ratio_high}")

    if quick_ratio_value is not None:
        if quick_ratio_value < t.quick_ratio_low:
            warning_reasons.append(f"Quick Ratio ({quick_ratio_value:.2f}) < {t.quick_ratio_low}")
        elif quick_ratio_value > 1.5:
            positive_reasons.append(f"Quick Ratio ({quick_ratio_value:.2f}) > 1.5")

    if cash_ratio_value is not None and cash_ratio_value > 0.5:
        positive_reasons.append(f"Cash Ratio ({cash_ratio_value:.2f}) indica alta liquidez inmediata")

    return {
        "weak_liquidity_flag": len(warning_reasons) > 0,
        "strong_liquidity_flag": len(positive_reasons) > 0 and len(warning_reasons) == 0,
        "warning_reasons": warning_reasons,
        "positive_reasons": positive_reasons,
    }


def profitability_flags(
    roe_value: Optional[float] = None,
    roa_value: Optional[float] = None,
    operating_margin_value: Optional[float] = None,
    net_margin_value: Optional[float] = None,
    gross_margin_value: Optional[float] = None,
    thresholds: ThresholdConfig = None,
) -> Dict[str, Any]:
    """Reglas para evaluar fortaleza de rentabilidad.
    
    Usa umbrales sectoriales para evaluar si la rentabilidad es buena o mala
    RELATIVAMENTE al sector, no con umbrales absolutos.
    """
    t = thresholds or ThresholdConfig()
    
    warning_reasons = []
    positive_reasons = []

    # ROE: usa umbrales sectoriales
    if roe_value is not None:
        if roe_value >= t.roe_high:
            positive_reasons.append(f"ROE ({roe_value:.1%}) supera umbral sectorial ({t.roe_high:.0%})")
        elif roe_value < t.roe_low:
            warning_reasons.append(f"ROE ({roe_value:.1%}) por debajo del mínimo ({t.roe_low:.0%})")
        # Zona neutral: entre roe_low y roe_high - no genera ni positivo ni negativo

    # ROA: usa umbral sectorial (para financieras es ~0.3%, para industriales ~3%)
    if roa_value is not None:
        if roa_value < t.roa_low:
            # Formato adaptativo: si el umbral es muy bajo (bancos), mostrar decimales
            if t.roa_low < 0.01:
                warning_reasons.append(f"ROA ({roa_value:.2%}) < {t.roa_low:.1%}")
            else:
                warning_reasons.append(f"ROA ({roa_value:.1%}) < {t.roa_low:.0%}")
        else:
            # Umbral positivo también adaptativo
            roa_good = t.roa_low * 2  # 2x el mínimo es bueno
            if roa_value >= roa_good:
                if t.roa_low < 0.01:
                    positive_reasons.append(f"ROA sólido para el sector ({roa_value:.2%})")
                else:
                    positive_reasons.append(f"ROA sólido ({roa_value:.1%})")

    # Operating Margin: usa umbral sectorial (1.5x el mínimo = muy bueno)
    if operating_margin_value is not None:
        op_margin_good = t.operating_margin_low * 1.5
        if operating_margin_value < t.operating_margin_low:
            warning_reasons.append(f"Margen Op. ({operating_margin_value:.1%}) < {t.operating_margin_low:.0%}")
        elif operating_margin_value >= op_margin_good:
            positive_reasons.append(f"Margen Op. ({operating_margin_value:.1%}) sólido para el sector")

    # Net Margin: usa umbral sectorial (1.5x el mínimo = muy bueno)
    if net_margin_value is not None:
        net_margin_good = t.net_margin_low * 1.5
        if net_margin_value < t.net_margin_low:
            warning_reasons.append(f"Margen Neto ({net_margin_value:.1%}) < {t.net_margin_low:.0%}")
        elif net_margin_value >= net_margin_good:
            positive_reasons.append(f"Margen Neto ({net_margin_value:.1%}) sólido para el sector")

    # Gross Margin: > 35% es generalmente saludable, > 50% es excelente
    if gross_margin_value is not None:
        if gross_margin_value > 0.50:
            positive_reasons.append(f"Margen Bruto ({gross_margin_value:.1%}) indica fuerte ventaja competitiva")
        elif gross_margin_value > 0.35:
            positive_reasons.append(f"Margen Bruto ({gross_margin_value:.1%}) saludable")

    return {
        "high_profitability_flag": len(positive_reasons) >= 2 and len(warning_reasons) == 0,
        "weak_profitability_flag": len(warning_reasons) >= 2,
        "warning_reasons": warning_reasons,
        "positive_reasons": positive_reasons,
    }


def cash_flow_flags(
    fcf_value: Optional[float] = None,
    fcf_trend_negative_years: Optional[int] = None,
    fcf_to_net_income: Optional[float] = None,
) -> Dict[str, Any]:
    """Reglas para evaluar la calidad del flujo de caja."""
    warning_reasons = []
    positive_reasons = []

    if fcf_value is not None:
        if fcf_value < 0:
            warning_reasons.append("FCF negativo - la empresa quema efectivo")
        elif fcf_value > 0:
            positive_reasons.append("FCF positivo")

    if fcf_trend_negative_years is not None and fcf_trend_negative_years >= 2:
        warning_reasons.append(f"FCF negativo por {fcf_trend_negative_years} años consecutivos")

    # Calidad de ganancias: FCF debería ser similar o mayor al Net Income
    if fcf_to_net_income is not None:
        if fcf_to_net_income < 0.5:
            warning_reasons.append("FCF/Net Income < 50% - posible problema de calidad de ganancias")
        elif fcf_to_net_income > 0.8:
            positive_reasons.append("FCF/Net Income > 80% - alta calidad de ganancias")

    return {
        "problematic_cash_flow_flag": len(warning_reasons) > 0,
        "strong_cash_flow_flag": len(positive_reasons) > 0 and len(warning_reasons) == 0,
        "warning_reasons": warning_reasons,
        "positive_reasons": positive_reasons,
    }


def growth_flags(
    revenue_cagr_3y: Optional[float] = None,
    revenue_cagr_5y: Optional[float] = None,
    eps_cagr_3y: Optional[float] = None,
    fcf_cagr_3y: Optional[float] = None,
) -> Dict[str, Any]:
    """Reglas para evaluar el crecimiento."""
    warning_reasons = []
    positive_reasons = []

    if revenue_cagr_3y is not None:
        if revenue_cagr_3y < 0:
            warning_reasons.append(f"Ingresos decreciendo ({revenue_cagr_3y:.1%} CAGR 3Y)")
        elif revenue_cagr_3y > 0.10:
            positive_reasons.append(f"Fuerte crecimiento de ingresos ({revenue_cagr_3y:.1%} CAGR 3Y)")

    if revenue_cagr_5y is not None and revenue_cagr_5y < -0.02:
        warning_reasons.append(f"Tendencia negativa de ingresos a largo plazo ({revenue_cagr_5y:.1%} CAGR 5Y)")

    if eps_cagr_3y is not None:
        if eps_cagr_3y < 0:
            warning_reasons.append(f"EPS decreciendo ({eps_cagr_3y:.1%} CAGR 3Y)")
        elif eps_cagr_3y > 0.15:
            positive_reasons.append(f"Fuerte crecimiento de EPS ({eps_cagr_3y:.1%} CAGR 3Y)")

    return {
        "strong_growth_flag": len(positive_reasons) >= 2 and len(warning_reasons) == 0,
        "weak_growth_flag": len(warning_reasons) >= 2,
        "warning_reasons": warning_reasons,
        "positive_reasons": positive_reasons,
    }


def structural_deterioration_flag(
    revenue_cagr_5y: Optional[float] = None,
    operating_margin_change_3y: Optional[float] = None,
    fcf_trend_negative_years: Optional[int] = None,
) -> Tuple[bool, List[str]]:
    """Alerta de deterioro estructural.
    True si hay múltiples señales de deterioro simultáneas.
    """
    reasons = []
    
    if revenue_cagr_5y is not None and revenue_cagr_5y < 0:
        reasons.append(f"Ingresos decrecientes (CAGR 5Y: {revenue_cagr_5y:.1%})")
    
    if operating_margin_change_3y is not None and operating_margin_change_3y < -0.03:
        reasons.append(f"Márgenes operativos en caída ({operating_margin_change_3y:.1%} en 3 años)")
    
    if fcf_trend_negative_years is not None and fcf_trend_negative_years >= 2:
        reasons.append(f"FCF negativo por {fcf_trend_negative_years} años")

    # Deterioro estructural si hay al menos 2 de 3 señales
    is_deteriorating = len(reasons) >= 2

    return is_deteriorating, reasons


def volatility_risk_flags(
    beta: Optional[float] = None,
    price_std_52w: Optional[float] = None,
    max_drawdown_1y: Optional[float] = None,
    thresholds: ThresholdConfig = None,
) -> Dict[str, Any]:
    """Reglas para evaluar riesgo y volatilidad."""
    t = thresholds or ThresholdConfig()
    
    warning_reasons = []
    positive_reasons = []

    if beta is not None:
        if beta > t.beta_high:
            warning_reasons.append(f"Beta alto ({beta:.2f}) - más volátil que el mercado")
        elif beta < t.beta_low:
            positive_reasons.append(f"Beta bajo ({beta:.2f}) - menos volátil que el mercado")

    if max_drawdown_1y is not None and max_drawdown_1y < -0.30:
        warning_reasons.append(f"Drawdown significativo en el último año ({max_drawdown_1y:.1%})")

    return {
        "high_volatility_flag": len(warning_reasons) > 0,
        "low_volatility_flag": len(positive_reasons) > 0 and len(warning_reasons) == 0,
        "warning_reasons": warning_reasons,
        "positive_reasons": positive_reasons,
    }


# =========================
# AGREGADOR DE ALERTAS
# =========================

def detect_growth_company(ratio_values: Dict, contextual_values: Dict) -> bool:
    """Detecta si es una empresa de alto crecimiento que reinvierte."""
    revenue_growth = contextual_values.get("revenue_cagr_3y")
    fcf = ratio_values.get("fcf")
    gross_margin = ratio_values.get("gross_margin")
    
    # Es growth si: crece >15% anual, tiene margen bruto alto (>40%), aunque FCF sea negativo
    if revenue_growth and revenue_growth > 0.15 and gross_margin and gross_margin > 0.40:
        return True
    return False


def get_sector_specific_adjustments(sector: str) -> Dict[str, Any]:
    """Ajustes por sector para el motor de alertas (aggregate_alerts).

    Solo contiene claves que el consumidor realmente lee (ignore_pe,
    ignore_debt_equity, pe_weight, margin_weight, growth_weight,
    dividend_weight, fcf_negative_tolerance, fcf_less_relevant,
    growth_less_relevant). La auditoría sectorial 2026-07 eliminó 7 claves
    inertes (pe_tolerance, pe_max, ev_ebitda_weight, debt_equity_max,
    pb_relevant, typical_roe, cyclical_adjustment) que ningún código leía.
    """
    adjustments = {
        # Financieros: Deuda alta es normal, P/E pesa menos
        "financials": {
            "ignore_debt_equity": True,  # No penalizar D/E alto
            "pe_weight": 0.5,  # Reducir peso del P/E
        },
        # REITs: P/E no relevante, dividendos son clave
        "real_estate": {
            "ignore_pe": True,  # No usar P/E
            "dividend_weight": 2.0,  # Doble peso a dividendos
            "fcf_less_relevant": True,  # FFO es mejor que FCF
        },
        # Utilities: dividendos importantes, crecimiento menos relevante
        "utilities": {
            "dividend_weight": 1.5,
            "growth_less_relevant": True,
        },
        # Tecnología: Crecimiento más importante
        "technology": {
            "growth_weight": 1.5,  # Más peso al crecimiento
            "fcf_negative_tolerance": True,  # Si crece, FCF neg es ok
        },
        # Healthcare/Biotech: márgenes importantes
        "healthcare": {
            "margin_weight": 1.3,
        },
        # Energía: cíclico, P/E pesa menos
        "energy": {
            "pe_weight": 0.7,
        },
        # Default
        "default": {}
    }
    
    # Mapear sectores de Yahoo Finance a nuestras categorías
    sector_lower = sector.lower().replace("_", " ") if sector else ""
    
    if any(x in sector_lower for x in ["financial", "bank", "insurance", "capital market"]):
        return adjustments["financials"]
    elif any(x in sector_lower for x in ["real estate", "reit", "realestate"]):
        return adjustments["real_estate"]
    elif any(x in sector_lower for x in ["utilit", "electric", "gas util", "water"]):
        return adjustments["utilities"]
    elif any(x in sector_lower for x in ["tech", "software", "semiconductor", "information"]):
        return adjustments["technology"]
    elif any(x in sector_lower for x in ["health", "biotech", "pharma", "medical"]):
        return adjustments["healthcare"]
    elif any(x in sector_lower for x in ["energy", "oil", "gas", "petroleum"]):
        return adjustments["energy"]
    
    return adjustments["default"]


def aggregate_alerts(ratio_values: Dict[str, Optional[float]],
                     contextual_values: Dict[str, Optional[float]],
                     sector: str = "default",
                     real_sector: str = "",
                     precomputed_f_score: Optional[int] = None) -> Dict[str, Any]:
    """Genera un reporte completo de alertas a partir de ratios calculados.
    
    VERSIÓN 3.1 - MODELO ADAPTATIVO con:
    - Altman Z-Score para riesgo de bancarrota (empresas no financieras)
    - Financial Health Score para sector financiero (bancos, seguros, etc.)
    - Piotroski F-Score para fortaleza financiera
    - PEG override para empresas growth
    - Scoring simétrico (+20/-20)
    - P/E justificado dinámico
    
    Args:
        ratio_values: Dict con ratios calculados (pe, p_fcf, roe, etc.)
        contextual_values: Dict con valores de contexto (sector_pe, pe_5y_avg, etc.)
        sector: Sector mapeado para umbrales (ej: "financials", "technology")
        real_sector: Sector real de Yahoo Finance (ej: "Financial Services")
    
    Returns:
        Dict con alertas categorizadas, score general y recomendación
    """
    thresholds = SECTOR_THRESHOLDS.get(sector, SECTOR_THRESHOLDS["default"])
    sector_adjustments = get_sector_specific_adjustments(sector)
    is_growth_company = detect_growth_company(ratio_values, contextual_values)
    
    # v3.1: Detectar si es sector financiero
    is_financial = is_financial_sector(real_sector) or is_financial_sector(sector)
    
    # =========================================
    # NUEVAS MÉTRICAS INSTITUCIONALES
    # =========================================
    
    # Altman Z-Score (riesgo de bancarrota) - Solo para NO financieras
    if not is_financial:
        z_score_value, z_score_level, z_score_interpretation, _ = altman_z_score(
            working_capital=contextual_values.get("working_capital"),
            total_assets=contextual_values.get("total_assets"),
            retained_earnings=contextual_values.get("retained_earnings"),
            ebit=contextual_values.get("ebit"),
            market_value_equity=contextual_values.get("market_cap"),
            total_liabilities=contextual_values.get("total_liabilities"),
            sales=contextual_values.get("revenue"),
            sector=real_sector,
        )
    else:
        z_score_value, z_score_level, z_score_interpretation = None, "N/A", "No aplica a sector financiero"
    
    # Piotroski F-Score (fortaleza financiera)
    f_score_value, f_score_details, f_score_interpretation = piotroski_f_score(
        net_income=contextual_values.get("net_income"),
        roa_current=ratio_values.get("roa"),
        roa_prior=contextual_values.get("roa_prior"),
        operating_cash_flow=contextual_values.get("operating_cash_flow"),
        long_term_debt_current=contextual_values.get("long_term_debt"),
        long_term_debt_prior=contextual_values.get("long_term_debt_prior"),
        current_ratio_current=ratio_values.get("current_ratio"),
        current_ratio_prior=contextual_values.get("current_ratio_prior"),
        shares_current=contextual_values.get("shares_outstanding"),
        shares_prior=contextual_values.get("shares_prior"),
        gross_margin_current=ratio_values.get("gross_margin"),
        gross_margin_prior=contextual_values.get("gross_margin_prior"),
        asset_turnover_current=ratio_values.get("asset_turnover"),
        asset_turnover_prior=contextual_values.get("asset_turnover_prior"),
        total_assets=contextual_values.get("total_assets")
    )

    # Preferir el F-Score autoritativo (calculado con datos de año fiscal puro,
    # sin mezcla TTM). El cálculo interno de arriba carece de datos prior cuando
    # se llama con fin_dict, lo que penalizaría el score de toda empresa.
    if precomputed_f_score is not None:
        f_score_value = precomputed_f_score

    # WACC dinámico
    wacc = calculate_wacc(
        beta=ratio_values.get("beta"),
        debt_to_equity=ratio_values.get("debt_to_equity"),
        interest_expense=contextual_values.get("interest_expense"),
        total_debt=contextual_values.get("total_debt")
    )
    
    # P/E Justificado (para override de penalización)
    earnings_growth = contextual_values.get("eps_cagr_3y") or contextual_values.get("revenue_cagr_3y")
    justified_pe = calculate_justified_pe(
        earnings_growth=earnings_growth,
        required_return=wacc or 0.10,
        roe=ratio_values.get("roe")
    )
    
    # Calcular todas las flags tradicionales
    val_flags = valuation_flags(
        pe=ratio_values.get("pe"),
        sector_pe=contextual_values.get("sector_pe"),
        pe_5y_avg=contextual_values.get("pe_5y_avg"),
        p_fcf=ratio_values.get("p_fcf"),
        ev_ebitda_value=ratio_values.get("ev_ebitda"),
        sector_ev_ebitda=contextual_values.get("sector_ev_ebitda"),
        fcf_yield_value=ratio_values.get("fcf_yield"),
        peg=ratio_values.get("peg"),
        pb=ratio_values.get("pb"),
        thresholds=thresholds,
    )

    lev_flags = leverage_flags(
        debt_to_equity_value=ratio_values.get("debt_to_equity"),
        net_debt_to_ebitda_value=ratio_values.get("net_debt_to_ebitda"),
        interest_coverage_value=ratio_values.get("interest_coverage"),
        debt_to_assets_value=ratio_values.get("debt_to_assets"),
        thresholds=thresholds,
    )

    liq_flags = liquidity_flags(
        current_ratio_value=ratio_values.get("current_ratio"),
        quick_ratio_value=ratio_values.get("quick_ratio"),
        cash_ratio_value=ratio_values.get("cash_ratio"),
        thresholds=thresholds,
    )

    prof_flags = profitability_flags(
        roe_value=ratio_values.get("roe"),
        roa_value=ratio_values.get("roa"),
        operating_margin_value=ratio_values.get("operating_margin"),
        net_margin_value=ratio_values.get("net_margin"),
        gross_margin_value=ratio_values.get("gross_margin"),
        thresholds=thresholds,
    )

    cf_flags = cash_flow_flags(
        fcf_value=ratio_values.get("fcf"),
        fcf_trend_negative_years=contextual_values.get("fcf_trend_negative_years"),
        fcf_to_net_income=ratio_values.get("fcf_to_net_income"),
    )

    growth_fl = growth_flags(
        revenue_cagr_3y=contextual_values.get("revenue_cagr_3y"),
        revenue_cagr_5y=contextual_values.get("revenue_cagr_5y"),
        eps_cagr_3y=contextual_values.get("eps_cagr_3y"),
        fcf_cagr_3y=contextual_values.get("fcf_cagr_3y"),
    )

    det_flag, det_reasons = structural_deterioration_flag(
        revenue_cagr_5y=contextual_values.get("revenue_cagr_5y"),
        operating_margin_change_3y=contextual_values.get("operating_margin_change_3y"),
        fcf_trend_negative_years=contextual_values.get("fcf_trend_negative_years"),
    )

    vol_flags = volatility_risk_flags(
        beta=ratio_values.get("beta"),
        max_drawdown_1y=contextual_values.get("max_drawdown_1y"),
        thresholds=thresholds,
    )

    # =========================================
    # SCORING V3.0 - INSTITUTIONAL GRADE
    # =========================================
    score = 50  # Base neutral
    score_breakdown = {}
    
    # --- ALTMAN Z-SCORE (CRÍTICO: -30 a +5) ---
    z_score_adjustment = 0
    if z_score_level == "DISTRESS":
        z_score_adjustment = -30  # CRÍTICO: Alto riesgo de bancarrota
    elif z_score_level == "GREY":
        z_score_adjustment = -10  # Zona gris - monitorear
    elif z_score_level == "SAFE":
        z_score_adjustment = 5    # Bonus por solidez
    
    score += z_score_adjustment
    score_breakdown["z_score"] = z_score_adjustment
    
    # --- PIOTROSKI F-SCORE (+12 a -15) ---
    f_score_adjustment = 0
    if f_score_value >= 8:
        f_score_adjustment = 12   # Fortaleza excepcional
    elif f_score_value >= 6:
        f_score_adjustment = 6    # Buena salud
    elif f_score_value >= 4:
        f_score_adjustment = 0    # Neutral
    elif f_score_value >= 2:
        f_score_adjustment = -8   # Debilidad
    else:
        f_score_adjustment = -15  # Crítico
    
    score += f_score_adjustment
    score_breakdown["f_score"] = f_score_adjustment

    # --- VALORACIÓN SIMÉTRICA (+20/-20) con PEG Override ---
    num_overvalued = len(val_flags.get("overvalued_reasons", []))
    num_undervalued = len(val_flags.get("undervalued_reasons", []))
    pe_current = ratio_values.get("pe")
    peg_current = ratio_values.get("peg")
    
    # Ajuste sectorial para P/E
    pe_weight = sector_adjustments.get("pe_weight", 1.0)
    
    # Si es sector que ignora P/E (REITs), filtrar
    if sector_adjustments.get("ignore_pe"):
        filtered_overvalued = [r for r in val_flags.get("overvalued_reasons", []) if "P/E" not in r]
        num_overvalued = len(filtered_overvalued)
    
    valuation_score = 0
    peg_override_applied = False
    
    if val_flags["undervalued_flag"]:
        # SIMÉTRICO: Mismo potencial de bonus que penalización
        valuation_score = min(20, num_undervalued * 6)
    elif val_flags["overvalued_flag"]:
        base_penalty = min(20, num_overvalued * 6)
        
        # PEG OVERRIDE: Si PEG < 1.5, el growth justifica la valoración
        if peg_current is not None and peg_current < 1.5 and peg_current > 0:
            if peg_current < 1.0:
                base_penalty = 0  # PEG < 1 = subvaluado para su crecimiento
                valuation_score = 8  # Bonus en lugar de penalización
            else:
                base_penalty = int(base_penalty * 0.3)  # Reducción 70%
            peg_override_applied = True
        
        # P/E JUSTIFICADO Override
        elif justified_pe is not None and pe_current is not None:
            if pe_current <= justified_pe * 1.3:  # Dentro de 30% del justificado
                base_penalty = int(base_penalty * 0.4)  # Reducción 60%
                peg_override_applied = True
        
        valuation_score = -int(base_penalty * pe_weight)
        
    elif val_flags["mixed_signals_flag"]:
        valuation_score = 0  # Neutral en lugar de -3
    
    score += valuation_score
    score_breakdown["valuation"] = valuation_score
    
    # --- APALANCAMIENTO (+10 a -12) ---
    leverage_score = 0
    
    if sector_adjustments.get("ignore_debt_equity"):
        if lev_flags["conservative_leverage_flag"]:
            leverage_score = 8
    else:
        if lev_flags["conservative_leverage_flag"]:
            leverage_score = 10
        elif lev_flags["overleveraged_flag"]:
            num_warnings = len(lev_flags.get("warning_reasons", []))
            leverage_score = -min(12, num_warnings * 4)
    
    score += leverage_score
    score_breakdown["leverage"] = leverage_score

    # --- LIQUIDEZ (+5 a -7) ---
    liquidity_score = 0
    if liq_flags["strong_liquidity_flag"]:
        liquidity_score = 5
    elif liq_flags["weak_liquidity_flag"]:
        liquidity_score = -7
    
    score += liquidity_score
    score_breakdown["liquidity"] = liquidity_score

    # --- RENTABILIDAD (+15 a -10) - AUMENTADO ---
    profitability_score = 0
    margin_weight = sector_adjustments.get("margin_weight", 1.0)
    
    if prof_flags["high_profitability_flag"]:
        profitability_score = int(15 * margin_weight)  # Aumentado de 12 a 15
    elif prof_flags["weak_profitability_flag"]:
        profitability_score = -10
    
    score += profitability_score
    score_breakdown["profitability"] = profitability_score

    # --- CASH FLOW (+10 a -10) ---
    cash_flow_score = 0
    
    if cf_flags["strong_cash_flow_flag"]:
        cash_flow_score = 10
    elif cf_flags["problematic_cash_flow_flag"]:
        if is_growth_company and sector_adjustments.get("fcf_negative_tolerance"):
            cash_flow_score = -3  # Reducido para growth
        elif sector_adjustments.get("fcf_less_relevant"):
            cash_flow_score = -2  # REITs
        else:
            cash_flow_score = -10
    
    score += cash_flow_score
    score_breakdown["cash_flow"] = cash_flow_score

    # --- CRECIMIENTO (+15 a -8) - AUMENTADO de +10 ---
    growth_score = 0
    growth_weight = sector_adjustments.get("growth_weight", 1.0)
    
    if growth_fl["strong_growth_flag"]:
        base_growth_score = 15  # Aumentado de 10 a 15
        growth_score = int(base_growth_score * growth_weight)
        
        # COMPOUNDER BONUS: Growth + Alta rentabilidad
        if prof_flags["high_profitability_flag"]:
            growth_score += 5  # Bonus adicional
            
    elif growth_fl["weak_growth_flag"]:
        if not sector_adjustments.get("growth_less_relevant"):
            growth_score = -8
        else:
            growth_score = -3  # Utilities
    
    score += growth_score
    score_breakdown["growth"] = growth_score

    # --- DETERIORO ESTRUCTURAL (-12 puntos) ---
    deterioration_score = 0
    if det_flag:
        if is_growth_company:
            deterioration_score = -5  # Reducido para growth
        else:
            deterioration_score = -12  # Reducido de -15
    
    score += deterioration_score
    score_breakdown["deterioration"] = deterioration_score

    # --- VOLATILIDAD (+5 a -5) ---
    volatility_score = 0
    if vol_flags["low_volatility_flag"]:
        volatility_score = 5
    elif vol_flags["high_volatility_flag"]:
        volatility_score = -5
    
    score += volatility_score
    score_breakdown["volatility"] = volatility_score

    # --- DIVIDENDOS (Bonus para sectores relevantes) ---
    dividend_score = 0
    div_yield = ratio_values.get("dividend_yield")
    payout = ratio_values.get("payout_ratio")
    if div_yield and div_yield > 0:
        div_weight = sector_adjustments.get("dividend_weight", 1.0)
        if div_yield > 0.04:
            dividend_score = int(5 * div_weight)
        elif div_yield > 0.025:
            dividend_score = int(3 * div_weight)
        # An unsustainable payout (>100% of earnings) makes the yield a red flag,
        # not a strength — a dividend cut is likely. REITs are exempt: they
        # distribute most of their FFO, so a net-income-based payout >100% is
        # normal for them. For everyone else, cancel the bonus and penalize.
        is_reit = ("real_estate" in (sector or "")
                   or "real estate" in (real_sector or "").lower()
                   or "reit" in (real_sector or "").lower())
        # payout > 1.0: paga más de lo que gana. payout < 0: paga dividendos con
        # ganancias NEGATIVAS (año en pérdidas). Como dividends_paid es positivo y
        # net_income negativo, ese payout sale NEGATIVO, no >100%, así que el
        # guard `> 1.0` lo dejaba escapar Y aún recibía el bonus +5/+3. Ambos casos
        # son insostenibles (recorte de dividendo probable) -> penalizar.
        unsustainable = payout is not None and (payout > 1.0 or payout < 0)
        if unsustainable and not is_reit:
            dividend_score = -3

    score += dividend_score
    score_breakdown["dividends"] = dividend_score

    # =========================================
    # SISTEMA DE SEVERIDAD Y CAP DINÁMICO v1.0
    # =========================================
    # Clasifica alertas por severidad y aplica CAP proporcional
    
    severity_analysis = classify_all_alerts_severity(
        ratio_values=ratio_values,
        contextual_values=contextual_values,
        thresholds=thresholds,
        val_flags=val_flags,
        lev_flags=lev_flags,
        liq_flags=liq_flags,
        prof_flags=prof_flags,
        cf_flags=cf_flags
    )
    
    score_breakdown["severity_analysis"] = severity_analysis
    
    # Aplicar penalización adicional basada en severidad
    # (Esto es adicional a las penalizaciones ya aplicadas por flags)
    # Solo aplicamos la mitad para no doble-penalizar
    severity_penalty = severity_analysis["total_risk_penalty"] // 2
    score -= severity_penalty
    score_breakdown["severity_penalty"] = -severity_penalty
    
    # Aplicar CAP dinámico
    score_cap = severity_analysis["score_cap"]
    score_before_cap = score
    
    # Limitar score entre 0 y el CAP
    score = max(0, min(score_cap, score))
    
    # Registrar si el CAP se aplicó
    cap_applied = score_before_cap > score_cap
    score_breakdown["score_cap"] = score_cap
    score_breakdown["cap_applied"] = cap_applied
    if cap_applied:
        score_breakdown["score_before_cap"] = score_before_cap

    # Determinar recomendación
    if score >= 70:
        recommendation = "FAVORABLE - Considerar inversión"
        signal = SignalType.POSITIVE
    elif score >= 50:
        recommendation = "NEUTRAL - Requiere análisis adicional"
        signal = SignalType.NEUTRAL
    elif score >= 30:
        recommendation = "PRECAUCIÓN - Riesgos identificados"
        signal = SignalType.WARNING
    else:
        recommendation = "EVITAR - Múltiples señales de alerta"
        signal = SignalType.DANGER

    # =========================================
    # SCORING V2.0 - NUEVO SISTEMA TRANSPARENTE
    # =========================================
    score_v2_result = calculate_score_v2(
        ratio_values=ratio_values,
        contextual_values=contextual_values,
        z_score_value=z_score_value,
        z_score_level=z_score_level,
        f_score_value=f_score_value,
        sector_key=sector,
        real_sector=real_sector  # v3.1: Pasar sector real para modelo adaptativo
    )

    return {
        "score": score_v2_result["score"],  # Usar score v2 como principal
        "score_v1": score,  # Mantener v1 como referencia
        "recommendation": recommendation,
        "signal": signal.value,
        "is_growth_company": is_growth_company,
        "peg_override_applied": peg_override_applied,
        "sector_adjustments_applied": list(sector_adjustments.keys()) if sector_adjustments else [],
        "score_breakdown": score_breakdown,
        # Sistema de severidad v1.0 (legacy)
        "severity_analysis": severity_analysis,
        "score_cap": score_cap,
        "cap_applied": cap_applied,
        # NUEVO: Score v2.0
        "score_v2": score_v2_result,
        # Nuevas métricas institucionales
        "altman_z_score": {
            "value": z_score_value,
            "level": z_score_level,
            "interpretation": z_score_interpretation
        },
        "piotroski_f_score": {
            "value": f_score_value,
            "details": f_score_details,
            "interpretation": f_score_interpretation
        },
        "wacc": wacc,
        "justified_pe": justified_pe,
        # v3.1: Información de modelo adaptativo
        "is_financial_sector": is_financial,
        "financial_health": score_v2_result.get("financial_health"),  # Solo para financieras
        # Flags tradicionales
        "valuation": val_flags,
        "leverage": lev_flags,
        "liquidity": liq_flags,
        "profitability": prof_flags,
        "cash_flow": cf_flags,
        "growth": growth_fl,
        "structural_deterioration": {"flag": det_flag, "reasons": det_reasons},
        "volatility": vol_flags,
    }


# =========================
# FUNCIONES DE UTILIDAD
# =========================

def calculate_all_ratios(financial_data: Dict) -> Dict[str, Optional[float]]:
    """Calcula todos los ratios a partir de datos financieros crudos.
    
    Args:
        financial_data: Dict con datos financieros de la empresa
            Esperados: revenue, net_income, total_assets, total_equity,
                      total_debt, cash, current_assets, current_liabilities,
                      inventories, operating_income, depreciation, capex,
                      operating_cash_flow, shares_outstanding, price,
                      interest_expense, cogs, etc.
    
    Returns:
        Dict con todos los ratios calculados
    """
    d = financial_data
    
    # Calcular valores intermedios
    ebitda_val = ebitda(d.get("operating_income"), d.get("depreciation"), d.get("amortization"))
    if ebitda_val is None:
        # Yahoo no siempre desglosa depreciación/amortización (entonces el EBITDA
        # calculado sale None), pero sí suele proveer el EBITDA directo. Usarlo como
        # fallback para que ev_ebitda, ebitda_margin y net_debt_to_ebitda no queden
        # None cuando el dato existe.
        ebitda_val = d.get("ebitda")
    fcf_val = free_cash_flow(d.get("operating_cash_flow"), d.get("capex"))
    mkt_cap = market_cap(d.get("price"), d.get("shares_outstanding"))
    ev_val = enterprise_value(mkt_cap, d.get("total_debt"), d.get("cash"))
    net_debt_val = net_debt(d.get("total_debt"), d.get("cash"))
    # EPS para P/E: preferir el EPS TTM diluido REPORTADO (el estándar de mercado;
    # Yahoo lo da como trailingEps y Finnhub lo rellena/corrige en degradación).
    # Calcular net_income/acciones solo como respaldo — en degradación ese
    # net_income es el del año fiscal (no TTM) e infla el P/E ~8%.
    _rep_eps = d.get("eps")
    if isinstance(_rep_eps, (int, float)) and _rep_eps == _rep_eps and _rep_eps != 0:
        eps_val = float(_rep_eps)
    else:
        eps_val = earnings_per_share(d.get("net_income"), d.get("shares_outstanding"))
    bvps = book_value_per_share(d.get("total_equity"), d.get("shares_outstanding"))
    fcf_ps = free_cash_flow_per_share(fcf_val, d.get("shares_outstanding"))

    # COGS para inventory_turnover: Yahoo no siempre expone "Cost Of Revenue" y el
    # dataclass no lo trae, así que se deriva de datos que sí están
    # (Revenue - Gross Profit). Sin esto inventory_turnover era SIEMPRE None y la
    # eficiencia de inventario (peso alto en retail) nunca puntuaba.
    cogs_val = d.get("cogs")
    if cogs_val is None and d.get("revenue") is not None and d.get("gross_profit") is not None:
        cogs_val = d.get("revenue") - d.get("gross_profit")

    # Calcular NOPAT e Invested Capital para ROIC
    tax_rate = d.get("tax_rate", 0.25)  # Default 25% si no se proporciona
    operating_inc = d.get("operating_income")
    # 'is not None' (no truthiness): un operating_income exactamente 0 (break-even
    # operativo) es un dato válido -> NOPAT=0, no None.
    nopat_val = operating_inc * (1 - tax_rate) if operating_inc is not None else None
    invested_cap = None
    if d.get("total_debt") is not None and d.get("total_equity") is not None and d.get("cash") is not None:
        invested_cap = d.get("total_debt") + d.get("total_equity") - d.get("cash")
        # Capital invertido <= 0 (empresa con caja neta o equity negativo por
        # recompras) no tiene sentido económico como denominador y produciría un
        # ROIC negativo espurio; se trata como no informativo (misma convención
        # que el D/E negativo en el scoring).
        if invested_cap <= 0:
            invested_cap = None

    # FFO para REITs. Yahoo no suele desglosar la depreciación, lo que dejaba
    # el FFO en None para casi todo REIT; se deriva D&A = EBITDA - EBIT cuando
    # falta (ambos ya disponibles con el fallback de EBITDA).
    _dep = d.get("depreciation")
    if _dep is None and ebitda_val is not None and operating_inc is not None:
        _dep = ebitda_val - operating_inc
    ffo_val = funds_from_operations(d.get("net_income"), _dep, d.get("gains_on_sale"))
    ffo_ps = safe_div(ffo_val, d.get("shares_outstanding")) if ffo_val else None

    # PEG: peg_ratio() espera el crecimiento de ganancias en PORCENTAJE (15 = 15%),
    # pero earnings_growth_rate llega como decimal (0.15). Sin escalar *100 el PEG
    # sale ~100x inflado (un PEG justo de 1.67 se mostraría como 167).
    _earnings_growth_pct = (
        d.get("earnings_growth_rate") * 100
        if d.get("earnings_growth_rate") is not None else None
    )

    return {
        # Rentabilidad
        "roe": roe(d.get("net_income"), d.get("total_equity")),
        "roa": roa(d.get("net_income"), d.get("total_assets")),
        "roic": roic(nopat_val, invested_cap),
        "gross_margin": gross_margin(d.get("gross_profit"), d.get("revenue")),
        "operating_margin": operating_margin(d.get("operating_income"), d.get("revenue")),
        "net_margin": net_margin(d.get("net_income"), d.get("revenue")),
        "ebitda": ebitda_val,
        "ebitda_margin": ebitda_margin(ebitda_val, d.get("revenue")),
        
        # Valoración
        "eps": eps_val,
        "pe": price_earnings(d.get("price"), eps_val),
        "forward_pe": forward_pe(d.get("price"), d.get("forward_eps")),
        "pb": price_book(d.get("price"), bvps),
        "ps": price_sales(d.get("price"), sales_per_share(d.get("revenue"), d.get("shares_outstanding"))),
        "p_fcf": price_free_cash_flow(d.get("price"), fcf_ps),
        "market_cap": mkt_cap,
        "enterprise_value": ev_val,
        "ev_ebitda": ev_ebitda(ev_val, ebitda_val),
        "ev_revenue": ev_revenue(ev_val, d.get("revenue")),
        "ev_fcf": ev_fcf(ev_val, fcf_val),
        "peg": peg_ratio(price_earnings(d.get("price"), eps_val), _earnings_growth_pct),
        "fcf_yield": free_cash_flow_yield(fcf_val, mkt_cap),
        "dividend_yield": dividend_yield(d.get("dividend_per_share"), d.get("price")),
        "payout_ratio": dividend_payout_ratio(d.get("dividends_paid"), d.get("net_income")),
        "earnings_yield": earnings_yield(eps_val, d.get("price")),
        
        # Liquidez
        "current_ratio": current_ratio(d.get("current_assets"), d.get("current_liabilities")),
        "quick_ratio": quick_ratio(d.get("current_assets"), d.get("inventories"), d.get("current_liabilities")),
        "cash_ratio": cash_ratio(d.get("cash"), d.get("current_liabilities")),
        
        # Solvencia
        "debt_to_equity": debt_to_equity(d.get("total_debt"), d.get("total_equity")),
        "debt_to_assets": debt_to_assets(d.get("total_debt"), d.get("total_assets")),
        "net_debt": net_debt_val,
        "net_debt_to_ebitda": net_debt_to_ebitda(net_debt_val, ebitda_val),
        "interest_coverage": interest_coverage(d.get("operating_income"), d.get("interest_expense")),
        
        # Eficiencia
        "asset_turnover": asset_turnover(d.get("revenue"), d.get("total_assets")),
        "inventory_turnover": inventory_turnover(cogs_val, d.get("inventories")),
        
        # Cash Flow
        "fcf": fcf_val,
        "fcf_to_net_income": safe_div(fcf_val, d.get("net_income")),
        "operating_cash_flow": d.get("operating_cash_flow"),
        "net_income": d.get("net_income"),
        
        # REITs (FFO)
        "ffo": ffo_val,
        "ffo_per_share": ffo_ps,
        "p_ffo": price_to_ffo(d.get("price"), ffo_ps),
        "ffo_payout": ffo_payout_ratio(d.get("dividends_paid"), ffo_val),
        
        # Valoración intrínseca
        "graham_number": graham_number(eps_val, bvps),
        
        # Volatilidad
        "beta": d.get("beta"),
    }


def score_solidez_financiera(
    z_score: Optional[float],
    z_score_level: str,
    current_ratio: Optional[float],
    debt_to_equity: Optional[float],
    interest_coverage: Optional[float],
    sector_de_threshold: float = 1.0
) -> Dict[str, Any]:
    """
    Categoría 1: Solidez Financiera (20 pts máximo)
    Base: 10 pts, ajusta según métricas
    """
    base_score = 10
    adjustments = []
    
    # Z-Score (peso alto: hasta ±6 pts)
    if z_score is not None:
        if z_score_level == "SAFE":
            adj = 6
            adjustments.append({"metric": "Altman Z-Score", "value": f"{z_score:.2f}", "adjustment": adj, "reason": "Zona segura - Muy baja probabilidad de quiebra", "severity": "excellent"})
        elif z_score_level == "GREY":
            adj = -2
            adjustments.append({"metric": "Altman Z-Score", "value": f"{z_score:.2f}", "adjustment": adj, "reason": "Zona gris - Requiere monitoreo cercano", "severity": "moderate"})
        elif z_score_level == "DISTRESS":
            adj = -6
            adjustments.append({"metric": "Altman Z-Score", "value": f"{z_score:.2f}", "adjustment": adj, "reason": "Zona peligro - Riesgo significativo de problemas", "severity": "severe"})
        else:
            adj = 0
        base_score += adj
    
    # Current Ratio (hasta ±4 pts)
    if current_ratio is not None:
        if current_ratio >= 2.0:
            adj = 4
            sev = "excellent"
            reason = f"Liquidez excelente - Cubre 2x sus deudas corto plazo"
        elif current_ratio >= 1.5:
            adj = 2
            sev = "good"
            reason = f"Liquidez sólida - Buena capacidad de pago ({current_ratio:.2f}x)"
        elif current_ratio >= 1.0:
            adj = 0
            sev = "ok"
            reason = f"Liquidez justa - Cubre sus obligaciones ({current_ratio:.2f}x)"
        elif current_ratio >= 0.8:
            adj = -2
            sev = "moderate"
            reason = f"Liquidez ajustada - Poco margen de maniobra ({current_ratio:.2f}x)"
        else:
            adj = -4
            sev = "severe"
            reason = f"Riesgo de liquidez - Podría tener problemas de pago ({current_ratio:.2f}x)"
        
        base_score += adj
        adjustments.append({"metric": "Current Ratio", "value": f"{current_ratio:.2f}x", "adjustment": adj, "reason": reason, "severity": sev})
    
    # Debt/Equity (hasta ±5 pts) - proporcional al sector
    if debt_to_equity is not None:
        threshold = sector_de_threshold
        if debt_to_equity < 0:
            # Negative book equity (buybacks) makes D/E negative and useless as a
            # leverage gauge — a very negative value is NOT "low debt". Treat it
            # neutral; interest coverage and the leverage flags (which use
            # equity-independent ratios) assess the real leverage.
            adj = 0
            sev = "ok"
            reason = f"D/E no informativo (patrimonio negativo, {debt_to_equity:.1f}x) — evaluar por cobertura de intereses"
        elif debt_to_equity <= threshold * 0.5:
            adj = 5
            sev = "excellent"
            reason = f"Deuda muy baja - Estructura financiera conservadora"
        elif debt_to_equity <= threshold:
            adj = 2
            sev = "good"
            reason = f"Deuda controlada - Dentro del rango saludable ({debt_to_equity:.2f}x)"
        elif debt_to_equity <= threshold * 1.3:
            adj = 0
            sev = "ok"
            reason = f"Deuda aceptable - Cerca del límite sectorial ({debt_to_equity:.2f}x)"
        elif debt_to_equity <= threshold * 1.6:
            adj = -2
            sev = "moderate"
            reason = f"Deuda elevada - Por encima del sector ({debt_to_equity:.2f}x vs {threshold:.1f}x)"
        elif interest_coverage is not None and interest_coverage >= 10:
            # Mitigación: D/E alto pero el beneficio operativo cubre los
            # intereses con mucha holgura — típico de mega-caps con patrimonio
            # encogido por recompras, no de empresas sobre-apalancadas. Sin esta
            # gradación, un D/E de 1.0x con cobertura 40x recibía la misma
            # penalización máxima que uno de 8x al borde del impago.
            adj = -2
            sev = "moderate"
            reason = (f"Deuda alta ({debt_to_equity:.2f}x) pero fácilmente servible "
                      f"(cobertura {interest_coverage:.0f}x) — riesgo acotado")
        else:
            adj = -5
            sev = "severe"
            reason = f"Deuda muy alta - Riesgo financiero elevado ({debt_to_equity:.2f}x)"
        
        base_score += adj
        adjustments.append({"metric": "Deuda/Equity", "value": f"{debt_to_equity:.2f}x", "adjustment": adj, "reason": reason, "severity": sev})
    
    # Interest Coverage (hasta ±3 pts)
    if interest_coverage is not None:
        if interest_coverage >= 10:
            adj = 3
            sev = "excellent"
            reason = "Cobertura excelente"
        elif interest_coverage >= 5:
            adj = 1
            sev = "good"
            reason = "Cobertura sólida"
        elif interest_coverage >= 3:
            adj = 0
            sev = "ok"
            reason = "Cobertura aceptable"
        elif interest_coverage >= 1.5:
            adj = -2
            sev = "moderate"
            reason = "Cobertura ajustada"
        else:
            adj = -3
            sev = "severe"
            reason = "Riesgo de cobertura"
        
        base_score += adj
        adjustments.append({"metric": "Cobertura Intereses", "value": f"{interest_coverage:.1f}x", "adjustment": adj, "reason": reason, "severity": sev})
    
    final_score = max(0, min(20, base_score))
    
    return {
        "category": "Solidez Financiera",
        "emoji": "🏛️",
        "score": final_score,
        "max_score": 20,
        "base": 10,
        "adjustments": adjustments,
        "total_adjustment": final_score - 10
    }


def score_solidez_financiera_financial(
    financial_health: Optional[int],
    financial_health_level: str,
    financial_health_details: List[Dict[str, Any]],
    roe: Optional[float],
    roa: Optional[float],
    price_to_book: Optional[float],
    debt_to_equity: Optional[float] = None  # Nuevo: D/E para interpretar correctamente
) -> Dict[str, Any]:
    """
    Categoría 1 ADAPTADA: Solidez Financiera para Sector Financiero (20 pts máximo)
    
    Reemplaza la evaluación tradicional (Z-Score, Current Ratio, D/E) por métricas
    relevantes para bancos, seguros y empresas financieras.
    
    PRINCIPIO CLAVE: No penalizar agresivamente cuando faltan datos.
    "No reprobar a un estudiante en un examen que nunca tomó."
    
    NOTA CONSERVADORA: Sin acceso a métricas regulatorias (CET1, Tier 1, NPL),
    el máximo es 18/20, no 20/20. Los 2 puntos restantes requieren datos 
    regulatorios que Yahoo Finance no proporciona.
    
    Componentes:
        - Financial Health Score (0-10) → mapeo proporcional
        - D/E Bancario contextualizado → bonus si es conservador
        - P/B → ajuste por valoración
    """
    adjustments = []
    b = FINANCIAL_BENCHMARKS
    has_regulatory_data = False  # Yahoo Finance no tiene CET1, Tier 1, etc.
    
    # =====================================================
    # ESTRATEGIA CONSERVADORA:
    # Sin métricas regulatorias, máximo = 18/20
    # Los 2 puntos restantes requieren CET1, Tier 1, NPL, etc.
    # =====================================================
    MAX_WITHOUT_REGULATORY = 18
    
    if financial_health is not None:
        # Mapeo lineal: FHS 0-10 → Solidez 4-18 (conservador)
        # Fórmula: solidez = 4 + (financial_health * 1.4)
        base_score = 4 + (financial_health * 1.4)
        
        if financial_health_level == "STRONG":
            sev = "excellent"
            reason = f"Solidez bancaria excelente ({financial_health}/10)"
        elif financial_health_level == "GOOD":
            sev = "good"
            reason = f"Buena salud financiera ({financial_health}/10)"
        elif financial_health_level == "NEUTRAL":
            sev = "ok"
            reason = f"Salud financiera neutral ({financial_health}/10)"
        else:  # WEAK
            sev = "moderate"  # NO severe - no penalizar excesivamente
            reason = f"Por debajo del promedio ({financial_health}/10)"
        
        adjustments.append({
            "metric": "Solidez Bancaria", 
            "value": f"{financial_health}/10", 
            "adjustment": round(base_score - 10),  # Relativo a base 10
            "reason": reason, 
            "severity": sev,
            "details": financial_health_details
        })
    else:
        # Sin datos: puntuación NEUTRAL (10/20), no penalizar
        base_score = 10
        adjustments.append({
            "metric": "Datos Limitados",
            "value": "N/A",
            "adjustment": 0,
            "reason": "Métricas bancarias regulatorias no disponibles - score neutral asignado",
            "severity": "neutral"
        })
    
    # =====================================================
    # BONUS: D/E Bancario muy conservador (hasta +3 pts)
    # Los bancos operan normalmente con D/E 8-15x
    # Un D/E de 2.6x es EXCEPCIONALMENTE conservador
    # =====================================================
    if debt_to_equity is not None:
        if debt_to_equity < b["de_very_conservative"]:  # <5x
            bonus = 3
            sev = "excellent"
            reason = f"D/E muy conservador ({debt_to_equity:.1f}x < 5x) - Excepcional para banco"
        elif debt_to_equity < b["de_conservative"]:  # 5-10x
            bonus = 2
            sev = "good"
            reason = f"D/E conservador ({debt_to_equity:.1f}x) - Sólido para banco"
        elif debt_to_equity < b["de_normal"]:  # 10-15x
            bonus = 0
            sev = "ok"
            reason = f"D/E normal ({debt_to_equity:.1f}x) - Típico bancario"
        else:  # >15x
            bonus = -2
            sev = "moderate"
            reason = f"D/E elevado ({debt_to_equity:.1f}x > 15x)"
        
        base_score += bonus
        adjustments.append({
            "metric": "D/E Bancario",
            "value": f"{debt_to_equity:.1f}x",
            "adjustment": bonus,
            "reason": reason,
            "severity": sev
        })
    
    # =====================================================
    # P/B: Ajuste por valoración (hasta ±2 pts)
    # =====================================================
    if price_to_book is not None:
        if price_to_book < b["pb_cheap"]:  # <0.8x
            adj = 2
            sev = "excellent"
            reason = f"P/B atractivo ({price_to_book:.2f}x) - Bajo valor en libros"
        elif price_to_book <= b["pb_fair"]:  # 0.8-1.2x
            adj = 1
            sev = "good"
            reason = f"P/B justo ({price_to_book:.2f}x)"
        elif price_to_book <= b["pb_expensive"]:  # 1.2-2.0x
            adj = 0
            sev = "ok"
            reason = f"P/B elevado ({price_to_book:.2f}x)"
        else:  # >2.0x
            adj = -1
            sev = "moderate"
            reason = f"P/B muy alto ({price_to_book:.2f}x > 2x)"
        
        base_score += adj
        adjustments.append({
            "metric": "Price/Book",
            "value": f"{price_to_book:.2f}x",
            "adjustment": adj,
            "reason": reason,
            "severity": sev
        })
    
    # Aplicar cap conservador: sin métricas regulatorias, máximo 18/20
    if not has_regulatory_data:
        final_score = max(0, min(MAX_WITHOUT_REGULATORY, round(base_score)))
        methodology_note = "Evaluación adaptada para sector bancario (máx 18/20 sin datos regulatorios CET1/Tier1)"
    else:
        final_score = max(0, min(20, round(base_score)))
        methodology_note = "Evaluación completa con métricas regulatorias"
    
    return {
        "category": "Solidez Financiera",
        "emoji": "🏦",
        "score": final_score,
        "max_score": 20,
        "base": 10,
        "adjustments": adjustments,
        "total_adjustment": final_score - 10,
        "is_financial_sector": True,
        "methodology_note": methodology_note
    }


def score_rentabilidad(
    roe: Optional[float],
    roa: Optional[float],
    operating_margin: Optional[float],
    net_margin: Optional[float],
    sector_roe_threshold: float = 0.12,
    sector_roa_threshold: float = 0.03,
    roic: Optional[float] = None,
    wacc: Optional[float] = None,
    sector_roe_high: float = 0.20,
    sector_roa_high: float = 0.12
) -> Dict[str, Any]:
    """
    Categoría 2: Rentabilidad (20 pts máximo)
    Base: 10 pts

    Las bandas SUPERIORES también son sectoriales (roe_high/roa_high de
    ThresholdConfig): antes estaban hardcodeadas (ROE 25%/15%, ROA 15%/8%),
    inalcanzables estructuralmente para bancos, utilities o REITs — un banco
    excelente (ROE 16%, ROA 1.3%) quedaba capado a +2/0 por muy por encima
    de su sector que estuviera.
    """
    base_score = 10
    adjustments = []

    # ROE (peso alto: hasta ±6 pts) — bandas relativas al roe_high sectorial
    if roe is not None:
        if roe < 0 and roa is not None and roa > 0.03:
            # Negative book equity (e.g. from heavy buybacks: HD, MCD, SBUX,
            # ABBV) makes ROE negative even for very profitable companies — a
            # balance-sheet artifact, not value destruction. Don't apply the
            # harsh penalty; ROA and margins carry the real profitability signal.
            adj = 0
            sev = "ok"
            reason = f"ROE negativo por patrimonio negativo (recompras) — no penalizado; ROA {roa:.1%} sólido"
        elif roe >= sector_roe_high * 1.25:
            adj = 6
            sev = "excellent"
            reason = f"Excepcional para su sector ({roe:.1%} vs {sector_roe_high:.0%} rango alto sectorial)"
        elif roe >= sector_roe_high:
            adj = 4
            sev = "good"
            reason = f"Muy bueno ({roe:.1%}) - En el rango alto de su sector"
        elif roe >= sector_roe_threshold:
            adj = 2
            sev = "ok"
            reason = f"Bueno ({roe:.1%}) - Competitivo en su sector"
        elif roe >= 0.05:
            adj = -2
            sev = "moderate"
            reason = f"Bajo ({roe:.1%}) - Por debajo de lo esperado"
        elif roe >= 0:
            adj = -4
            sev = "moderate"
            reason = f"Muy bajo ({roe:.1%}) - Poco eficiente con el capital"
        else:
            adj = -6
            sev = "severe"
            reason = f"Negativo ({roe:.1%}) - Destruye valor para accionistas"
        
        base_score += adj
        adjustments.append({"metric": "ROE", "value": f"{roe:.1%}", "adjustment": adj, "reason": reason, "severity": sev})
    
    # ROA (hasta ±4 pts) — bandas relativas al roa_high sectorial
    if roa is not None:
        if roa >= sector_roa_high * 1.25:
            adj = 4
            sev = "excellent"
            reason = f"Excelente para su sector ({roa:.1%})"
        elif roa >= sector_roa_high:
            adj = 2
            sev = "good"
            reason = f"Bueno ({roa:.1%}) - Rango alto de su sector"
        elif roa >= sector_roa_threshold:
            adj = 0
            sev = "ok"
            reason = f"Aceptable ({roa:.1%}) - Normal para su sector"
        elif roa >= 0:
            adj = -2
            sev = "moderate"
            reason = f"Bajo ({roa:.1%}) - Activos poco productivos"
        else:
            adj = -4
            sev = "severe"
            reason = f"Negativo ({roa:.1%}) - Perdiendo dinero con sus activos"
        
        base_score += adj
        adjustments.append({"metric": "ROA", "value": f"{roa:.1%}", "adjustment": adj, "reason": reason, "severity": sev})
    
    # Operating Margin (hasta ±5 pts)
    if operating_margin is not None:
        if operating_margin >= 0.30:
            adj = 5
            sev = "excellent"
            reason = f"Excepcional ({operating_margin:.1%}) - Alto poder de fijación de precios"
        elif operating_margin >= 0.20:
            adj = 3
            sev = "good"
            reason = f"Muy bueno ({operating_margin:.1%}) - Operaciones eficientes"
        elif operating_margin >= 0.10:
            adj = 1
            sev = "ok"
            reason = f"Bueno ({operating_margin:.1%}) - Márgenes saludables"
        elif operating_margin >= 0.05:
            adj = -1
            sev = "moderate"
            reason = f"Ajustado ({operating_margin:.1%}) - Márgenes bajo presión"
        elif operating_margin >= 0:
            adj = -3
            sev = "moderate"
            reason = f"Bajo ({operating_margin:.1%}) - Costos erosionan ganancias"
        else:
            adj = -5
            sev = "severe"
            reason = f"Negativo ({operating_margin:.1%}) - Operaciones no rentables"
        
        base_score += adj
        adjustments.append({"metric": "Margen Operativo", "value": f"{operating_margin:.1%}", "adjustment": adj, "reason": reason, "severity": sev})
    
    # Net Margin (hasta ±3 pts)
    if net_margin is not None:
        if net_margin >= 0.20:
            adj = 3
            sev = "excellent"
            reason = f"Excelente ({net_margin:.1%}) - Alta rentabilidad final"
        elif net_margin >= 0.10:
            adj = 2
            sev = "good"
            reason = f"Bueno ({net_margin:.1%}) - Ganancias sólidas"
        elif net_margin >= 0.05:
            adj = 0
            sev = "ok"
            reason = f"Aceptable ({net_margin:.1%}) - Márgenes estándar"
        elif net_margin >= 0:
            adj = -2
            sev = "moderate"
            reason = f"Bajo ({net_margin:.1%}) - Poca ganancia por venta"
        else:
            adj = -3
            sev = "severe"
            reason = f"Negativo ({net_margin:.1%})"
        
        base_score += adj
        adjustments.append({"metric": "Margen Neto", "value": f"{net_margin:.1%}", "adjustment": adj, "reason": reason, "severity": sev})

    # ROIC - WACC spread (hasta ±3): ¿la empresa genera retornos por encima de su
    # costo de capital? Es el filtro de CREACIÓN DE VALOR económico que faltaba: el
    # ROE/ROA se miden contra umbrales absolutos, así una empresa con ROE alto puede
    # DESTRUIR valor si su WACC es mayor. Señal moderada para complementar (no
    # duplicar) el ROE. No aplica a financieras (se pasa wacc=None para ellas).
    if roic is not None and wacc is not None:
        spread = roic - wacc
        if spread >= 0.10:
            adj = 3; sev = "excellent"
            reason = f"Crea mucho valor (ROIC {roic:.1%} vs WACC {wacc:.1%}, spread +{spread:.1%})"
        elif spread >= 0.03:
            adj = 2; sev = "good"
            reason = f"Crea valor (ROIC {roic:.1%} > WACC {wacc:.1%}, spread +{spread:.1%})"
        elif spread >= 0:
            adj = 1; sev = "ok"
            reason = f"Retorno por encima del costo de capital (spread +{spread:.1%})"
        elif spread >= -0.03:
            adj = -1; sev = "moderate"
            reason = f"Retorno apenas por debajo del costo de capital (spread {spread:.1%})"
        else:
            adj = -3; sev = "severe"
            reason = f"Destruye valor (ROIC {roic:.1%} < WACC {wacc:.1%}, spread {spread:.1%})"
        base_score += adj
        adjustments.append({"metric": "ROIC vs WACC", "value": f"{spread:+.1%}", "adjustment": adj, "reason": reason, "severity": sev})

    final_score = max(0, min(20, base_score))

    return {
        "category": "Rentabilidad",
        "emoji": "💰",
        "score": final_score,
        "max_score": 20,
        "base": 10,
        "adjustments": adjustments,
        "total_adjustment": final_score - 10
    }


def score_valoracion(
    pe: Optional[float],
    p_fcf: Optional[float],
    ev_ebitda: Optional[float],
    peg: Optional[float],
    sector_pe: Optional[float] = None,
    sector_ev_ebitda: Optional[float] = None,
    fcf_yield: Optional[float] = None,
    # Parámetros v2.2+ para ajuste growth/value
    revenue_growth_3y: Optional[float] = None,
    eps_growth_3y: Optional[float] = None,
    roe: Optional[float] = None,
    roic: Optional[float] = None,
    operating_margin: Optional[float] = None,
    fcf_growth_3y: Optional[float] = None,
    dividend_yield: Optional[float] = None,
    # v2.4: Forward P/E para growth
    forward_pe: Optional[float] = None,
    earnings_yield: Optional[float] = None,
    # v3.3: REITs se valoran por P/FFO, no por P/E ni P/FCF
    is_reit: bool = False,
    p_ffo: Optional[float] = None
) -> Dict[str, Any]:
    """
    Categoría 3: Valoración (20 pts máximo)
    Base: 10 pts

    v2.4: MODELO ADAPTATIVO MEJORADO

    Problemas resueltos vs v2.2:
    - Las penalizaciones ya no se apilan sin control (-13 posible → max -8 para growth)
    - Forward P/E importa para growth stocks (si Forward << Trailing = crecimiento)
    - Earnings Yield como nueva métrica positiva
    - PEG bueno atenúa penalizaciones de otros múltiplos
    - Bandas más amplias para empresas growth de calidad

    Filosofía: Una empresa cara que crece rápido con buenos fundamentos
    NO es lo mismo que una empresa cara que no crece.
    """
    base_score = 10
    adjustments = []

    # Calcular calidad del crecimiento y tipo de empresa
    growth_quality = calculate_growth_quality_score(
        revenue_growth_3y=revenue_growth_3y,
        eps_growth_3y=eps_growth_3y,
        fcf_growth_3y=fcf_growth_3y,
        roe=roe,
        roic=roic,
        operating_margin=operating_margin,
        fcf_to_net_income=None
    )

    company_profile = classify_company_type(
        revenue_growth_3y=revenue_growth_3y,
        eps_growth_3y=eps_growth_3y,
        pe=pe,
        sector_pe=sector_pe,
        dividend_yield=dividend_yield,
        fcf_yield=fcf_yield,
        roe=roe
    )

    growth_quality_score = growth_quality["score"]
    company_type = company_profile["type"]
    # Sin NINGÚN dato de crecimiento, growth_quality devuelve su base neutral
    # (50) — no debe bastar para activar tolerancias/rescates de valoración:
    # la ausencia de datos no es evidencia de calidad.
    has_growth_data = any(x is not None for x in (revenue_growth_3y, eps_growth_3y, fcf_growth_3y))
    is_quality_growth = (has_growth_data and company_type in ["growth", "garp"] and growth_quality_score >= 60)

    # v2.4: Track negative adjustments to cap them for growth
    total_negative = 0

    # ─── REIT: P/FFO en lugar de P/E y P/FCF (hasta ±4 pts) ────
    # El beneficio neto de un REIT está deprimido por la depreciación de
    # inmuebles (no-cash) y su FCF por el capex de cartera: P/E y P/FCF son
    # métricas engañosas para el sector. El estándar es P/FFO.
    if is_reit:
        if p_ffo is not None and p_ffo > 0:
            if p_ffo <= 12:
                adj = 4; sev = "excellent"
                reason = f"Barato por FFO ({p_ffo:.1f}x)"
            elif p_ffo <= 16:
                adj = 2; sev = "good"
                reason = f"Atractivo por FFO ({p_ffo:.1f}x)"
            elif p_ffo <= 20:
                adj = 0; sev = "ok"
                reason = f"En línea ({p_ffo:.1f}x FFO)"
            elif p_ffo <= 25:
                adj = -2; sev = "moderate"
                reason = f"Caro por FFO ({p_ffo:.1f}x)"
            else:
                adj = -4; sev = "severe"
                reason = f"Muy caro por FFO ({p_ffo:.1f}x)"
            if adj < 0:
                total_negative += adj
            base_score += adj
            adjustments.append({"metric": "P/FFO (REIT)", "value": f"{p_ffo:.1f}x", "adjustment": adj, "reason": reason, "severity": sev})
        else:
            adjustments.append({"metric": "P/FFO (REIT)", "value": "N/D", "adjustment": 0,
                                "reason": "P/E y P/FCF omitidos (engañosos para REITs); FFO no disponible",
                                "severity": "ok"})

    # ─── P/E vs Sector (hasta ±5 pts) — omitido para REITs ─────
    if not is_reit and pe is not None and pe > 0:
        pe_threshold = sector_pe if sector_pe and sector_pe > 0 else 20

        # v2.4: Bandas más amplias para growth
        if is_quality_growth:
            # Growth stocks: tolerar hasta 1.5x sector como "en línea"
            if pe <= pe_threshold * 0.7:
                adj = 5; sev = "excellent"
                reason = f"Barato ({pe:.1f}x vs {pe_threshold:.1f}x sector)"
            elif pe <= pe_threshold * 1.0:
                adj = 3; sev = "good"
                reason = f"Atractivo para growth ({pe:.1f}x)"
            elif pe <= pe_threshold * 1.5:
                adj = 0; sev = "ok"
                reason = f"Razonable para growth ({pe:.1f}x vs {pe_threshold:.1f}x)"
            elif pe <= pe_threshold * 2.0:
                adj = -2; sev = "moderate"
                reason = f"Premium elevado ({pe:.1f}x vs {pe_threshold:.1f}x)"
            else:
                adj = -3; sev = "severe"  # v2.4: max -3 en vez de -5
                reason = f"Muy caro ({pe:.1f}x vs {pe_threshold:.1f}x)"
        else:
            if pe <= pe_threshold * 0.7:
                adj = 5; sev = "excellent"
                reason = f"Muy barato ({pe:.1f}x vs {pe_threshold:.1f}x sector)"
            elif pe <= pe_threshold * 0.9:
                adj = 3; sev = "good"
                reason = f"Atractivo ({pe:.1f}x)"
            elif pe <= pe_threshold * 1.1:
                adj = 0; sev = "ok"
                reason = f"En línea ({pe:.1f}x vs {pe_threshold:.1f}x)"
            elif pe <= pe_threshold * 1.3:
                adj = -2; sev = "moderate"
                reason = f"Premium ({pe:.1f}x vs {pe_threshold:.1f}x)"
            else:
                adj = -4; sev = "severe"
                reason = f"Muy caro ({pe:.1f}x vs {pe_threshold:.1f}x)"

        # v2.4: Ajustar penalización con growth quality (ahora más agresivo)
        if adj < 0 and has_growth_data and growth_quality_score >= 50:
            original_adj = adj
            adjusted_adj, adj_reason, adj_sev = adjust_valuation_for_growth(
                base_pe_adjustment=adj,
                pe=pe,
                sector_pe=pe_threshold,
                growth_quality_score=growth_quality_score,
                company_type=company_type,
                revenue_growth=revenue_growth_3y,
                roe=roe
            )
            if adjusted_adj != original_adj:
                adj = adjusted_adj
                sev = adj_sev if adj_sev else sev
                quality_label = growth_quality["label"]
                if adj >= 0:
                    reason = f"Premium justificado ({pe:.1f}x) - {quality_label}"
                else:
                    reason = f"Premium ajustado ({pe:.1f}x) - {quality_label}"

        if adj < 0:
            total_negative += adj
        base_score += adj
        adjustments.append({"metric": "P/E vs Sector", "value": f"{pe:.1f}x", "adjustment": adj, "reason": reason, "severity": sev})

    # ─── Forward P/E Bonus (NUEVO v2.4) ────────────────
    if forward_pe is not None and forward_pe > 0 and pe is not None and pe > 0:
        pe_compression = (pe - forward_pe) / pe  # % de "mejora" esperada
        if pe_compression >= 0.25:  # Forward P/E 25%+ menor que trailing
            adj = 3; sev = "excellent"
            reason = f"Fuerte compresión P/E ({pe:.0f}x → {forward_pe:.0f}x forward)"
            base_score += adj
            adjustments.append({"metric": "Forward P/E", "value": f"{forward_pe:.1f}x", "adjustment": adj, "reason": reason, "severity": sev})
        elif pe_compression >= 0.12:
            adj = 2; sev = "good"
            reason = f"P/E mejorando ({pe:.0f}x → {forward_pe:.0f}x forward)"
            base_score += adj
            adjustments.append({"metric": "Forward P/E", "value": f"{forward_pe:.1f}x", "adjustment": adj, "reason": reason, "severity": sev})
        elif pe_compression >= 0.05:
            adj = 1; sev = "good"
            reason = f"P/E estable a mejor ({pe:.0f}x → {forward_pe:.0f}x)"
            base_score += adj
            adjustments.append({"metric": "Forward P/E", "value": f"{forward_pe:.1f}x", "adjustment": adj, "reason": reason, "severity": sev})

    # ─── P/FCF (hasta ±4 pts) — omitido para REITs (capex de cartera) ──
    if not is_reit and p_fcf is not None and p_fcf > 0:
        # v2.4: Bandas más amplias para growth
        if is_quality_growth:
            if p_fcf <= 15:
                adj = 4; sev = "excellent"
                reason = f"Excelente para growth ({p_fcf:.1f}x)"
            elif p_fcf <= 25:
                adj = 2; sev = "good"
                reason = f"Bueno para growth ({p_fcf:.1f}x)"
            elif p_fcf <= 40:
                adj = 0; sev = "ok"
                reason = f"Aceptable para growth ({p_fcf:.1f}x)"
            elif p_fcf <= 60:
                adj = -1; sev = "moderate"
                reason = f"Elevado ({p_fcf:.1f}x) - growth premium"
            else:
                adj = -2; sev = "moderate"
                reason = f"Muy alto ({p_fcf:.1f}x)"
        else:
            if p_fcf <= 12:
                adj = 4; sev = "excellent"
                reason = f"Muy atractivo ({p_fcf:.1f}x)"
            elif p_fcf <= 18:
                adj = 2; sev = "good"
                reason = f"Bueno ({p_fcf:.1f}x)"
            elif p_fcf <= 25:
                adj = 0; sev = "ok"
                reason = f"Aceptable ({p_fcf:.1f}x)"
            elif p_fcf <= 35:
                adj = -2; sev = "moderate"
                reason = f"Elevado ({p_fcf:.1f}x)"
            else:
                adj = -4; sev = "severe"
                reason = f"Muy alto ({p_fcf:.1f}x)"

        if adj < 0:
            total_negative += adj
        base_score += adj
        adjustments.append({"metric": "P/FCF", "value": f"{p_fcf:.1f}x", "adjustment": adj, "reason": reason, "severity": sev})

    # ─── EV/EBITDA vs Sector (hasta ±4 pts) ────────────
    if ev_ebitda is not None and ev_ebitda > 0:
        ev_threshold = sector_ev_ebitda if sector_ev_ebitda and sector_ev_ebitda > 0 else 12

        if is_quality_growth:
            if ev_ebitda <= ev_threshold * 0.7:
                adj = 4; sev = "excellent"
                reason = f"Muy barato ({ev_ebitda:.1f}x vs {ev_threshold:.1f}x)"
            elif ev_ebitda <= ev_threshold * 1.2:
                adj = 2; sev = "good"
                reason = f"Atractivo para growth ({ev_ebitda:.1f}x)"
            elif ev_ebitda <= ev_threshold * 1.8:
                adj = 0; sev = "ok"
                reason = f"Razonable para growth ({ev_ebitda:.1f}x)"
            elif ev_ebitda <= ev_threshold * 2.5:
                adj = -1; sev = "moderate"
                reason = f"Premium ({ev_ebitda:.1f}x vs {ev_threshold:.1f}x)"
            else:
                adj = -2; sev = "severe"
                reason = f"Muy caro ({ev_ebitda:.1f}x vs {ev_threshold:.1f}x)"
        else:
            if ev_ebitda <= ev_threshold * 0.7:
                adj = 4; sev = "excellent"
                reason = f"Muy barato ({ev_ebitda:.1f}x vs {ev_threshold:.1f}x)"
            elif ev_ebitda <= ev_threshold:
                adj = 2; sev = "good"
                reason = f"Atractivo ({ev_ebitda:.1f}x)"
            elif ev_ebitda <= ev_threshold * 1.2:
                adj = 0; sev = "ok"
                reason = f"En línea ({ev_ebitda:.1f}x)"
            elif ev_ebitda <= ev_threshold * 1.5:
                adj = -2; sev = "moderate"
                reason = f"Premium ({ev_ebitda:.1f}x vs {ev_threshold:.1f}x)"
            else:
                adj = -4; sev = "severe"
                reason = f"Muy caro ({ev_ebitda:.1f}x vs {ev_threshold:.1f}x)"

        if adj < 0:
            total_negative += adj
        base_score += adj
        adjustments.append({"metric": "EV/EBITDA vs Sector", "value": f"{ev_ebitda:.1f}x", "adjustment": adj, "reason": reason, "severity": sev})

    # ─── PEG Ratio (hasta ±4 pts) ─────────────────────
    if peg is not None and peg > 0:
        if peg <= 0.8:
            adj = 4; sev = "excellent"
            reason = f"Muy atractivo ({peg:.2f})"
        elif peg <= 1.2:
            adj = 2; sev = "good"
            reason = f"Bueno ({peg:.2f})"
        elif peg <= 1.8:
            adj = 0; sev = "ok"
            reason = f"Razonable ({peg:.2f})"
        elif peg <= 2.5:
            adj = -2; sev = "moderate"
            reason = f"Caro para su crecimiento ({peg:.2f})"
        else:
            adj = -3; sev = "severe"  # v2.4: max -3 en vez de -4
            reason = f"Muy caro ({peg:.2f})"

        if adj < 0:
            total_negative += adj
        base_score += adj
        adjustments.append({"metric": "PEG Ratio", "value": f"{peg:.2f}", "adjustment": adj, "reason": reason, "severity": sev})

    # ─── De-dup de valoración (Fase B) ─────────────────
    # Se eliminaron los bonos separados de "FCF Yield" (+3) y "Earnings Yield"
    # (+2): fcf_yield = 1/p_fcf y earnings_yield = 1/pe, así que premiaban el
    # MISMO hecho ("barato por FCF" / "barato por ganancias") que las bandas de
    # P/FCF (±4) y P/E ya puntúan arriba -> doble conteo que inflaba valoración
    # a las value stocks. Las bandas de P/FCF y P/E quedan como señal primaria.
    # (fcf_yield/earnings_yield siguen usándose para alertas y ajuste de growth,
    # no para un bonus redundante de valoración.)

    # ─── GARP / Growth Quality Bonus ───────────────────
    if company_type == "garp" and growth_quality_score >= 70:
        adj = 3; sev = "excellent"  # v2.4: subió de +2 a +3
        reason = f"GARP: Growth + Fundamentos sólidos (Quality: {growth_quality_score})"
        base_score += adj
        adjustments.append({"metric": "Perfil GARP", "value": f"Score {growth_quality_score}", "adjustment": adj, "reason": reason, "severity": sev})
    elif company_type == "growth" and growth_quality_score >= 75:
        adj = 2; sev = "excellent"
        reason = f"Growth de alta calidad (Quality: {growth_quality_score})"
        base_score += adj
        adjustments.append({"metric": "Growth Quality", "value": f"Score {growth_quality_score}", "adjustment": adj, "reason": reason, "severity": sev})

    # ─── v2.4: CAP DE PENALIZACIONES para growth ──────
    # Para growth stocks de calidad, no permitir que las penalizaciones
    # destruyan completamente la categoría.
    # Max penalización neta: -4 para quality growth, -6 para moderate growth
    if is_quality_growth and total_negative < -4:
        rescue_pts = min(-total_negative - 4, 4)  # Max rescue: 4 pts
        base_score += rescue_pts
        adjustments.append({
            "metric": "Ajuste Growth",
            "value": f"Quality {growth_quality_score}",
            "adjustment": rescue_pts,
            "reason": f"Límite de penalización para growth de calidad ({company_type})",
            "severity": "good"
        })
    elif growth_quality_score >= 50 and company_type not in ["speculative_growth"] and total_negative < -6:
        rescue_pts = min(-total_negative - 6, 3)
        base_score += rescue_pts
        adjustments.append({
            "metric": "Ajuste Crecimiento",
            "value": f"Quality {growth_quality_score}",
            "adjustment": rescue_pts,
            "reason": f"Límite de penalización por calidad moderada",
            "severity": "good"
        })

    final_score = max(0, min(20, base_score))

    return {
        "category": "Valoración",
        "emoji": "💵",
        "score": final_score,
        "max_score": 20,
        "base": 10,
        "adjustments": adjustments,
        "total_adjustment": final_score - 10,
        "company_type": company_type,
        "growth_quality_score": growth_quality_score,
        "growth_quality_label": growth_quality["label"]
    }


def score_calidad_ganancias(
    f_score: Optional[int],
    fcf: Optional[float],
    ocf: Optional[float],
    net_income: Optional[float],
    fcf_to_net_income: Optional[float],
    earnings_consistency: Optional[float] = None
) -> Dict[str, Any]:
    """
    Categoría 4: Calidad de Ganancias (20 pts máximo)
    Base: 10 pts
    """
    base_score = 10
    adjustments = []
    
    # Piotroski F-Score (peso alto: hasta ±7 pts)
    if f_score is not None:
        if f_score >= 8:
            adj = 7
            sev = "excellent"
            reason = f"Fortaleza excepcional ({f_score}/9)"
        elif f_score >= 6:
            adj = 4
            sev = "good"
            reason = f"Buena salud ({f_score}/9)"
        elif f_score >= 4:
            adj = 0
            sev = "ok"
            reason = f"Neutral ({f_score}/9)"
        elif f_score >= 2:
            adj = -4
            sev = "moderate"
            reason = f"Debilidad ({f_score}/9)"
        else:
            adj = -7
            sev = "severe"
            reason = f"Señales de deterioro ({f_score}/9)"
        
        base_score += adj
        adjustments.append({"metric": "Piotroski F-Score", "value": f"{f_score}/9", "adjustment": adj, "reason": reason, "severity": sev})
    
    # Operating Cash Flow (hasta ±4 pts)
    if ocf is not None:
        if ocf > 0:
            adj = 3
            sev = "good"
            reason = "Genera efectivo operativo"
        else:
            adj = -4
            sev = "severe"
            reason = "Quema efectivo operativo"
        
        base_score += adj
        adjustments.append({"metric": "Cash Flow Operativo", "value": "Positivo" if ocf > 0 else "Negativo", "adjustment": adj, "reason": reason, "severity": sev})
    
    # FCF (hasta ±4 pts)
    if fcf is not None:
        if fcf > 0:
            adj = 3
            sev = "good"
            reason = "FCF positivo"
        else:
            adj = -4
            sev = "severe"
            reason = "FCF negativo"
        
        base_score += adj
        adjustments.append({"metric": "Free Cash Flow", "value": "Positivo" if fcf > 0 else "Negativo", "adjustment": adj, "reason": reason, "severity": sev})
    
    # Calidad FCF vs Net Income (hasta ±3 pts)
    if fcf_to_net_income is not None and net_income is not None and net_income > 0:
        if fcf_to_net_income >= 1.0:
            adj = 3
            sev = "excellent"
            reason = f"FCF > Net Income ({fcf_to_net_income:.1%})"
        elif fcf_to_net_income >= 0.7:
            adj = 1
            sev = "good"
            reason = f"FCF sólido vs ganancias ({fcf_to_net_income:.1%})"
        elif fcf_to_net_income >= 0.3:
            adj = 0
            sev = "ok"
            reason = f"FCF aceptable ({fcf_to_net_income:.1%})"
        else:
            adj = -2
            sev = "moderate"
            reason = f"Ganancias sin respaldo de cash ({fcf_to_net_income:.1%})"
        
        base_score += adj
        adjustments.append({"metric": "FCF / Net Income", "value": f"{fcf_to_net_income:.0%}", "adjustment": adj, "reason": reason, "severity": sev})
    
    final_score = max(0, min(20, base_score))
    
    return {
        "category": "Calidad de Ganancias",
        "emoji": "✅",
        "score": final_score,
        "max_score": 20,
        "base": 10,
        "adjustments": adjustments,
        "total_adjustment": final_score - 10
    }


def score_crecimiento(
    revenue_growth_3y: Optional[float],
    eps_growth_3y: Optional[float],
    fcf_growth_3y: Optional[float],
    is_growth_company: bool = False
) -> Dict[str, Any]:
    """
    Categoría 5: Crecimiento (20 pts máximo)
    Base: 10 pts
    """
    base_score = 10
    adjustments = []
    
    # Revenue Growth 3Y (hasta ±5 pts)
    if revenue_growth_3y is not None:
        if revenue_growth_3y >= 0.20:
            adj = 5
            sev = "excellent"
            reason = f"Crecimiento excepcional ({revenue_growth_3y:.1%})"
        elif revenue_growth_3y >= 0.10:
            adj = 3
            sev = "good"
            reason = f"Crecimiento sólido ({revenue_growth_3y:.1%})"
        elif revenue_growth_3y >= 0.03:
            adj = 1
            sev = "ok"
            reason = f"Crecimiento moderado ({revenue_growth_3y:.1%})"
        elif revenue_growth_3y >= 0:
            adj = -1
            sev = "moderate"
            reason = f"Crecimiento plano ({revenue_growth_3y:.1%})"
        else:
            adj = -4
            sev = "severe"
            reason = f"Contracción ({revenue_growth_3y:.1%})"
        
        base_score += adj
        adjustments.append({"metric": "Crecimiento Ingresos 3Y", "value": f"{revenue_growth_3y:.1%}", "adjustment": adj, "reason": reason, "severity": sev})
    
    # EPS Growth 3Y (hasta ±5 pts)
    if eps_growth_3y is not None:
        if eps_growth_3y >= 0.25:
            adj = 5
            sev = "excellent"
            reason = f"EPS excepcional ({eps_growth_3y:.1%})"
        elif eps_growth_3y >= 0.12:
            adj = 3
            sev = "good"
            reason = f"EPS sólido ({eps_growth_3y:.1%})"
        elif eps_growth_3y >= 0.05:
            adj = 1
            sev = "ok"
            reason = f"EPS moderado ({eps_growth_3y:.1%})"
        elif eps_growth_3y >= 0:
            adj = -1
            sev = "moderate"
            reason = f"EPS plano ({eps_growth_3y:.1%})"
        else:
            adj = -4
            sev = "severe"
            reason = f"EPS en declive ({eps_growth_3y:.1%})"
        
        base_score += adj
        adjustments.append({"metric": "Crecimiento EPS 3Y", "value": f"{eps_growth_3y:.1%}", "adjustment": adj, "reason": reason, "severity": sev})
    
    # FCF Growth (hasta ±4 pts)
    if fcf_growth_3y is not None:
        if fcf_growth_3y >= 0.15:
            adj = 4
            sev = "excellent"
            reason = f"FCF creciente ({fcf_growth_3y:.1%})"
        elif fcf_growth_3y >= 0.05:
            adj = 2
            sev = "good"
            reason = f"FCF estable/creciente ({fcf_growth_3y:.1%})"
        elif fcf_growth_3y >= -0.05:
            adj = 0
            sev = "ok"
            reason = f"FCF estable ({fcf_growth_3y:.1%})"
        else:
            adj = -3
            sev = "moderate"
            reason = f"FCF decreciente ({fcf_growth_3y:.1%})"
        
        base_score += adj
        adjustments.append({"metric": "Crecimiento FCF 3Y", "value": f"{fcf_growth_3y:.1%}", "adjustment": adj, "reason": reason, "severity": sev})
    
    # Growth Company Bonus
    if is_growth_company:
        adj = 2
        base_score += adj
        adjustments.append({"metric": "Growth Company", "value": "Sí", "adjustment": adj, "reason": "Perfil de alto crecimiento", "severity": "good"})
    
    final_score = max(0, min(20, base_score))
    
    return {
        "category": "Crecimiento",
        "emoji": "📈",
        "score": final_score,
        "max_score": 20,
        "base": 10,
        "adjustments": adjustments,
        "total_adjustment": final_score - 10
    }


def calculate_score_v2(
    ratio_values: Dict[str, Any],
    contextual_values: Dict[str, Any],
    z_score_value: Optional[float] = None,
    z_score_level: str = "N/A",
    f_score_value: Optional[int] = None,
    sector_key: str = "default",
    real_sector: str = "",  # Sector real de Yahoo Finance
    wacc: Optional[float] = None  # Para el spread ROIC-WACC en rentabilidad
) -> Dict[str, Any]:
    """
    Sistema de Scoring v2.3 - Adaptativo Growth/Value + Sector Financiero
    
    Calcula score total basado en 5 categorías × 20 pts = 100 máximo
    
    v2.3: MODELO ADAPTATIVO para sector financiero
    - Detecta si es banco/seguro/asset management
    - Usa Financial Health Score en lugar de Altman Z-Score
    - Ajusta benchmarks de ROA/ROE para estándares bancarios
    - Oculta ratios que no aplican (Current Ratio, D/E tradicional)
    
    Returns:
        Dict con score total, desglose por categoría, y explicaciones
    """
    # Obtener umbrales sectoriales
    thresholds = SECTOR_THRESHOLDS.get(sector_key, ThresholdConfig())
    
    # Determinar si es growth company
    revenue_growth = contextual_values.get("revenue_cagr_3y")
    is_growth = revenue_growth is not None and revenue_growth > 0.15
    
    # =====================================================
    # v2.3: DETECCIÓN DE SECTOR FINANCIERO
    # =====================================================
    is_financial = is_financial_sector(real_sector) or is_financial_sector(sector_key)
    financial_health_data = None
    
    if is_financial:
        # Calcular Financial Health Score (reemplaza Z-Score)
        # v3.2: Ahora incluye D/E bancario para interpretación correcta
        fh_score, fh_level, fh_interpretation, fh_details = financial_health_score(
            roa=ratio_values.get("roa"),
            roe=ratio_values.get("roe"),
            total_equity=contextual_values.get("total_equity"),
            total_assets=contextual_values.get("total_assets"),
            book_value=contextual_values.get("book_value"),
            book_value_prior=contextual_values.get("book_value_prior"),
            dividend_yield=ratio_values.get("dividend_yield"),
            payout_ratio=ratio_values.get("payout_ratio"),
            debt_to_equity=ratio_values.get("debt_to_equity")  # v3.2: D/E bancario
        )
        
        financial_health_data = {
            "score": fh_score,
            "level": fh_level,
            "interpretation": fh_interpretation,
            "details": fh_details
        }
        
        # Usar versión adaptada de solidez para financieras
        # v3.2: Pasar D/E para interpretación correcta (2.6x es conservador para banco)
        solidez = score_solidez_financiera_financial(
            financial_health=fh_score,
            financial_health_level=fh_level,
            financial_health_details=fh_details,
            roe=ratio_values.get("roe"),
            roa=ratio_values.get("roa"),
            price_to_book=ratio_values.get("pb"),
            debt_to_equity=ratio_values.get("debt_to_equity")  # v3.2: D/E bancario
        )
    else:
        # Versión estándar para empresas no financieras
        solidez = score_solidez_financiera(
            z_score=z_score_value,
            z_score_level=z_score_level,
            current_ratio=ratio_values.get("current_ratio"),
            debt_to_equity=ratio_values.get("debt_to_equity"),
            interest_coverage=ratio_values.get("interest_coverage"),
            sector_de_threshold=thresholds.debt_equity_high
        )
    
    rentabilidad = score_rentabilidad(
        roe=ratio_values.get("roe"),
        roa=ratio_values.get("roa"),
        operating_margin=ratio_values.get("operating_margin"),
        net_margin=ratio_values.get("net_margin"),
        sector_roe_threshold=thresholds.roe_low,
        sector_roa_threshold=thresholds.roa_low,
        roic=ratio_values.get("roic"),
        # WACC no es interpretable para financieras -> sin señal de spread ahí.
        wacc=(None if is_financial else wacc),
        sector_roe_high=thresholds.roe_high,
        sector_roa_high=thresholds.roa_high
    )
    
    # v2.4: Pasar datos de crecimiento + forward metrics a valoración
    valoracion = score_valoracion(
        pe=ratio_values.get("pe"),
        p_fcf=ratio_values.get("p_fcf"),
        ev_ebitda=ratio_values.get("ev_ebitda"),
        peg=ratio_values.get("peg"),
        sector_pe=contextual_values.get("sector_pe"),
        sector_ev_ebitda=contextual_values.get("sector_ev_ebitda"),
        fcf_yield=ratio_values.get("fcf_yield"),
        revenue_growth_3y=contextual_values.get("revenue_cagr_3y"),
        eps_growth_3y=contextual_values.get("eps_cagr_3y"),
        roe=ratio_values.get("roe"),
        roic=ratio_values.get("roic"),
        operating_margin=ratio_values.get("operating_margin"),
        fcf_growth_3y=contextual_values.get("fcf_cagr_3y"),
        dividend_yield=ratio_values.get("dividend_yield"),
        # v2.4: Nuevos parámetros
        forward_pe=ratio_values.get("forward_pe"),
        earnings_yield=ratio_values.get("earnings_yield"),
        # v3.3: REITs se valoran por P/FFO (P/E y P/FCF son engañosos ahí)
        is_reit=(sector_key == "real_estate"),
        p_ffo=ratio_values.get("p_ffo")
    )
    
    calidad = score_calidad_ganancias(
        f_score=f_score_value,
        fcf=ratio_values.get("fcf"),
        ocf=ratio_values.get("operating_cash_flow"),
        net_income=ratio_values.get("net_income"),
        fcf_to_net_income=ratio_values.get("fcf_to_net_income")
    )
    
    crecimiento = score_crecimiento(
        revenue_growth_3y=contextual_values.get("revenue_cagr_3y"),
        eps_growth_3y=contextual_values.get("eps_cagr_3y"),
        fcf_growth_3y=contextual_values.get("fcf_cagr_3y"),
        is_growth_company=is_growth
    )
    
    # Calcular totales
    categories = [solidez, rentabilidad, valoracion, calidad, crecimiento]
    total_score = sum(cat["score"] for cat in categories)
    
    # Determinar nivel general
    if total_score >= 80:
        level = "Excelente"
        level_color = "#22c55e"
    elif total_score >= 65:
        level = "Favorable"
        level_color = "#84cc16"
    elif total_score >= 50:
        level = "Neutral"
        level_color = "#eab308"
    elif total_score >= 35:
        level = "Precaución"
        level_color = "#f97316"
    else:
        level = "Alto Riesgo"
        level_color = "#ef4444"
    
    # v2.2: Extraer información del perfil de la empresa
    company_type = valoracion.get("company_type", "blend")
    growth_quality = valoracion.get("growth_quality_score", 50)
    
    result = {
        "score": total_score,
        "max_score": 100,
        "level": level,
        "level_color": level_color,
        "categories": categories,
        "category_scores": {
            "solidez": solidez["score"],
            "rentabilidad": rentabilidad["score"],
            "valoracion": valoracion["score"],
            "calidad": calidad["score"],
            "crecimiento": crecimiento["score"]
        },
        "is_growth_company": is_growth,
        # Nuevos campos v2.2
        "company_type": company_type,
        "growth_quality_score": growth_quality,
        # v2.3: Campos para sector financiero
        "is_financial_sector": is_financial,
        "financial_health": financial_health_data
    }
    
    return result


# =============================================================================
# DCF SENSITIVITY ANALYSIS - v2.9
# =============================================================================

def dcf_sensitivity_analysis(
    fcf: Optional[float],
    shares_outstanding: Optional[float],
    current_price: Optional[float] = None,
    base_growth_rate: float = 0.15,
    base_discount_rate: float = 0.10,
    growth_rate_range: tuple = (-0.05, 0.05, 0.025),  # (min_delta, max_delta, step)
    discount_rate_range: tuple = (-0.02, 0.02, 0.01),  # (min_delta, max_delta, step)
    terminal_growth: float = DCF_TERMINAL_GROWTH,
    net_debt: Optional[float] = 0.0,
) -> Dict[str, Any]:
    """
    Genera una matriz de sensibilidad para análisis DCF.
    
    Muestra cómo cambia el valor justo con diferentes combinaciones de:
    - Growth Rate (tasa de crecimiento)
    - Discount Rate (WACC)
    
    Args:
        fcf: Free Cash Flow actual
        shares_outstanding: Acciones en circulación
        current_price: Precio actual (para comparación)
        base_growth_rate: Tasa de crecimiento base
        base_discount_rate: Tasa de descuento base (WACC)
        growth_rate_range: (delta_min, delta_max, step) para growth rates
        discount_rate_range: (delta_min, delta_max, step) para discount rates
        terminal_growth: Tasa de crecimiento terminal
    
    Returns:
        Dict con matriz de sensibilidad, estadísticas y metadata
    """
    # Keep the ENTIRE discount-rate grid inside the headline DCF's WACC band
    # [0.06, 0.20] (dcf_multi_stage_dynamic clamps WACC there). The grid spans
    # base + the discount_rate_range deltas, so bound the base so neither the
    # low nor the high column leaves the band. Without this, a low-beta stock's
    # low WACC pushes the low columns toward the terminal growth rate, where the
    # terminal value explodes into absurd fair values (e.g. a $1857 cell for a
    # $50 stock) that paint the table "deeply undervalued".
    _wacc_lo, _wacc_hi = 0.06, 0.20
    if base_discount_rate is not None:
        base_discount_rate = max(_wacc_lo - discount_rate_range[0],
                                 min(base_discount_rate, _wacc_hi - discount_rate_range[1]))

    result = {
        "matrix": [],
        "growth_rates": [],
        "discount_rates": [],
        "base_case": {
            "growth_rate": base_growth_rate,
            "discount_rate": base_discount_rate,
            "fair_value": None
        },
        "statistics": {
            "min_value": None,
            "max_value": None,
            "mean_value": None,
            "median_value": None,
            "current_price": current_price,
            "upside_base_case": None
        },
        "interpretation": None,
        "is_valid": False,
        "warnings": []
    }
    
    # Validaciones
    if fcf is None or fcf <= 0:
        result["warnings"].append("FCF no disponible o negativo")
        return result
    
    if shares_outstanding is None or shares_outstanding <= 0:
        result["warnings"].append("Shares outstanding no disponible")
        return result
    
    # Generar rangos de tasas
    gr_min, gr_max, gr_step = growth_rate_range
    dr_min, dr_max, dr_step = discount_rate_range
    
    # Growth rates: de menor a mayor
    growth_rates = []
    gr = base_growth_rate + gr_min
    while gr <= base_growth_rate + gr_max + 0.001:
        growth_rates.append(round(gr, 4))
        gr += gr_step
    
    # Discount rates: de menor a mayor
    discount_rates = []
    dr = base_discount_rate + dr_min
    while dr <= base_discount_rate + dr_max + 0.001:
        discount_rates.append(round(dr, 4))
        dr += dr_step
    
    result["growth_rates"] = growth_rates
    result["discount_rates"] = discount_rates
    
    # Generar matriz de valores
    matrix = []
    all_values = []
    base_value = None
    
    for growth_rate in growth_rates:
        row = []
        for discount_rate in discount_rates:
            # Validar que discount_rate > terminal_growth
            if discount_rate <= terminal_growth:
                row.append(None)
                continue
            
            # Calcular DCF
            dcf_result = dcf_multi_stage(
                fcf=fcf,
                shares_outstanding=shares_outstanding,
                high_growth_rate=growth_rate,
                terminal_growth=terminal_growth,
                discount_rate=discount_rate,
                net_debt=net_debt
            )
            
            fair_value = dcf_result.get("fair_value_per_share")
            row.append(fair_value)
            
            if fair_value is not None:
                all_values.append(fair_value)
                
                # Identificar caso base
                if (abs(growth_rate - base_growth_rate) < 0.001 and 
                    abs(discount_rate - base_discount_rate) < 0.001):
                    base_value = fair_value
                    result["base_case"]["fair_value"] = fair_value
        
        matrix.append(row)
    
    result["matrix"] = matrix
    
    # Calcular estadísticas
    if all_values:
        result["statistics"]["min_value"] = min(all_values)
        result["statistics"]["max_value"] = max(all_values)
        result["statistics"]["mean_value"] = sum(all_values) / len(all_values)
        
        sorted_values = sorted(all_values)
        n = len(sorted_values)
        result["statistics"]["median_value"] = (
            sorted_values[n // 2] if n % 2 == 1 
            else (sorted_values[n // 2 - 1] + sorted_values[n // 2]) / 2
        )
        
        # Calcular upside si tenemos precio actual
        if current_price and current_price > 0 and base_value:
            upside = ((base_value / current_price) - 1) * 100
            result["statistics"]["upside_base_case"] = upside
        
        result["is_valid"] = True
        
        # Interpretación
        if current_price and current_price > 0:
            undervalued_count = sum(1 for v in all_values if v > current_price)
            total_scenarios = len(all_values)
            undervalued_pct = (undervalued_count / total_scenarios) * 100
            
            if undervalued_pct >= 80:
                result["interpretation"] = f"Muy probablemente subvalorada ({undervalued_pct:.0f}% de escenarios)"
            elif undervalued_pct >= 60:
                result["interpretation"] = f"Probablemente subvalorada ({undervalued_pct:.0f}% de escenarios)"
            elif undervalued_pct >= 40:
                result["interpretation"] = f"Valoración mixta ({undervalued_pct:.0f}% escenarios favorables)"
            elif undervalued_pct >= 20:
                result["interpretation"] = f"Probablemente sobrevalorada ({100-undervalued_pct:.0f}% de escenarios)"
            else:
                result["interpretation"] = f"Muy probablemente sobrevalorada ({100-undervalued_pct:.0f}% de escenarios)"
    
    return result


