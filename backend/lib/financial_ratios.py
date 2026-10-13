"""
Financial Ratios Calculator Module
==================================
Módulo completo para cálculo de ratios financieros y sistema de alertas
para análisis fundamental de acciones.

Autor: Esteban
Versión: 3.1 - Configuración Centralizada
"""

import math
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass
from enum import Enum

# Configuración única (backend/config/*.toml, validada al importar settings).
from settings import cfg
from classify import FINANCIAL, REIT, GROWTH_PRE_PROFIT, CYCLICAL, MATURE, not_applicable, norm_industry

_WACC = cfg("valuation.wacc")
_DCF = cfg("valuation.dcf")
_GRID = cfg("valuation.grid")
_ALTMAN = cfg("valuation.models.altman")
_PIOTROSKI = cfg("valuation.models.piotroski")
_FHEALTH = cfg("valuation.models.financial_health")
_BENCH_FALLBACK = cfg("sectors.benchmarks.engine_fallback")  # PROVISIONAL
_SC = cfg("thresholds.score")
_CAT = cfg("thresholds.score.category")
_CAT_COVERAGE = cfg("thresholds.score.coverage")

DCF_TERMINAL_GROWTH = _DCF["terminal_growth"]
DCF_WACC_DEFAULT = _WACC["default"]
DCF_HIGH_GROWTH_YEARS = _DCF["high_growth_years"]
DCF_TRANSITION_YEARS = _DCF["transition_years"]


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
FINANCIAL_SECTORS = cfg("sectors.financials.sector_names")

# Benchmarks específicos para sector financiero
# CALIBRADOS según estándares reales del sector bancario (Q1 2024)
# Fuente: Promedios de grandes bancos, requisitos Basilea III/IV
FINANCIAL_BENCHMARKS = cfg("sectors.financials.benchmarks")  # PROVISIONAL (ver sectors.toml)


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
    financial_keywords = cfg("sectors.financials.keywords")
    return any(kw in sector_lower for kw in financial_keywords)

def altman_model(sector: Optional[str], industry: Optional[str] = None) -> str:
    """Modelo de Altman por sector/industria (etapa 7): "original" (Z, 1968) para
    los sectores e industrias manufactureros de la config; "z_double_prime" (Z'')
    para el resto. Coincidencia EXACTA (antes por subcadena: "financial services"
    entraba por "services"). Sin sector: Z'' (no exige ventas)."""
    if norm_industry(industry) in _ALTMAN["manufacturing_industries"] or \
            (sector or "").strip().lower() in _ALTMAN["manufacturing_sectors"]:
        return "original"
    return "z_double_prime"


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
    not_applicable_reason: Optional[str] = None,
    industry: str = "",
) -> Tuple[Optional[float], str, str, dict]:
    """
    Altman Z-Score. El MODELO depende solo del arquetipo (FINANCIAL y REIT: no
    aplica) y del sector/industria de la clasificación (altman_model), nunca de
    qué datos hay: el mismo ticker usa el mismo modelo en cualquier entorno.

    Cada variante con SUS variables (los coeficientes y cortes solo valen con ellas):

    1) Z-Score ORIGINAL (1968) — empresas manufactureras públicas
       Z = 1.2×X1 + 1.4×X2 + 3.3×X3 + 0.6×X4 + 1.0×X5
       X4 = capitalización bursátil / pasivo total
       Safe > 2.99 | Grey 1.81–2.99 | Distress < 1.81

    2) Z''-Score (1995) — servicios, tech, non-manufacturing
       Elimina X5 (asset turnover) porque sesga a empresas asset-light.
       Z'' = 6.56×X1 + 3.26×X2 + 6.72×X3 + 1.05×X4
       X4 = patrimonio CONTABLE / pasivo total (etapa 7; antes la capitalización,
       que no es la variable del modelo y daba zona segura a SNOW con utilidades
       retenidas negativas: X4 18.05 frente a 0.27)
       Safe > 2.60 | Grey 1.10–2.60 | Distress < 1.10

    Sin la variable X4 de la variante (capitalización en Z, patrimonio contable en
    Z'') el Z es "sin dato" (antes cambiaba en silencio al Z' de empresas privadas:
    el modelo dependía del dato disponible).

    Returns:
        Tuple[z_score, risk_level, interpretation, details_dict]
    """
    # ── No aplica al arquetipo (etapa 6) ──
    # Lo decide el clasificador (FINANCIAL: depósitos = pasivos; REIT:
    # apalancamiento estructural y sin ciclo de circulante), no el sector:
    # antes se excluía todo "Financial Services", incluidas redes de pago (V).
    if not_applicable_reason:
        return (
            None,
            "N/A",
            f"{not_applicable_reason}. El Altman Z-Score fue diseñado para empresas industriales y comerciales.",
            {"model": "No Aplicable", "reason": "no_aplica", "sector": sector or ""},
        )

    is_non_manufacturing = altman_model(sector, industry) == "z_double_prime"

    # ── Validate minimum required inputs ──
    if total_assets is None or total_assets == 0:
        return None, "N/A", "Datos insuficientes para calcular Z-Score", {}
    if ebit is None:
        return None, "N/A", "Datos insuficientes: falta EBIT / Operating Income", {}
    if total_liabilities is None or total_liabilities == 0:
        return None, "N/A", "Datos insuficientes: faltan pasivos totales", {}

    # Altman exige TODOS sus componentes (etapa 5): un dato ausente ya no se toma
    # como 0. Sin cualquiera de ellos el Z no se calcula ("sin dato" con motivo)
    # y Solidez se reescala sobre sus componentes disponibles.
    missing = []
    if working_capital is None:
        missing.append("capital de trabajo")
    if retained_earnings is None:
        missing.append("utilidades retenidas")
    if is_non_manufacturing:
        if book_value_equity is None:
            missing.append("patrimonio contable")
    else:
        if market_value_equity is None or market_value_equity == 0:
            missing.append("valor de mercado del patrimonio")
        if sales is None:
            missing.append("ventas")
    if missing:
        return (None, "N/A", "Datos insuficientes para el Z-Score: falta " + ", ".join(missing),
                {"reason": "sin_dato", "missing": missing})
    wc, re = working_capital, retained_earnings

    try:
        X1 = wc / total_assets
        X2 = re / total_assets
        X3 = ebit / total_assets

        details = {"X1_wc_ta": round(X1, 4), "X2_re_ta": round(X2, 4), "X3_ebit_ta": round(X3, 4)}

        if is_non_manufacturing:
            # ── Z''-Score (services / tech / non-manufacturing) ──
            X4 = book_value_equity / total_liabilities
            c = _ALTMAN["non_manufacturing_coef"]
            z = c[0]*X1 + c[1]*X2 + c[2]*X3 + c[3]*X4
            model_name = "Z''-Score (No Manufactura)"
            safe_threshold, grey_threshold = _ALTMAN["non_manufacturing_safe"], _ALTMAN["non_manufacturing_grey"]
            details.update({"X4_book_tl": round(X4, 4)})

        else:
            # ── Z-Score Original (manufacturing) ──
            X4 = market_value_equity / total_liabilities
            X5 = (sales / total_assets) if sales else 0
            c = _ALTMAN["original_coef"]
            z = c[0]*X1 + c[1]*X2 + c[2]*X3 + c[3]*X4 + c[4]*X5
            model_name = "Z-Score Original (Manufactura)"
            safe_threshold, grey_threshold = _ALTMAN["original_safe"], _ALTMAN["original_grey"]
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
    H = _FHEALTH
    
    # 1. ROA (0-3 puntos) - Crítico para bancos
    if roa is not None:
        max_possible += H["roa_points"][0]
        roa_pct = roa if roa < 1 else roa / 100  # Normalizar si viene como porcentaje
        if roa_pct >= b["roa_excellent"]:
            pts = H["roa_points"][0]
            detail = f"ROA excelente ({roa_pct*100:.2f}% ≥ 0.5%)"
            severity = "excellent"
        elif roa_pct >= b["roa_good"]:
            pts = H["roa_points"][1]
            detail = f"ROA bueno ({roa_pct*100:.2f}% ≥ 0.3%)"
            severity = "good"
        elif roa_pct >= b["roa_acceptable"]:
            pts = H["roa_points"][2]
            detail = f"ROA aceptable ({roa_pct*100:.2f}% ≥ 0.2%)"
            severity = "ok"
        else:
            pts = 0
            detail = f"ROA bajo ({roa_pct*100:.2f}% < 0.2%)"
            severity = "weak"
        score += pts
        details.append({"metric": "ROA Bancario", "points": pts, "max": H["roa_points"][0], "detail": detail, "severity": severity})
    
    # 2. ROE (0-3 puntos)
    if roe is not None:
        max_possible += H["roe_points"][0]
        roe_pct = roe if roe < 1 else roe / 100
        if roe_pct >= b["roe_excellent"]:
            pts = H["roe_points"][0]
            detail = f"ROE excelente ({roe_pct*100:.1f}% ≥ 12%)"
            severity = "excellent"
        elif roe_pct >= b["roe_good"]:
            pts = H["roe_points"][1]
            detail = f"ROE bueno ({roe_pct*100:.1f}% ≥ 8%)"
            severity = "good"
        elif roe_pct >= b["roe_acceptable"]:
            pts = H["roe_points"][2]
            detail = f"ROE aceptable ({roe_pct*100:.1f}% ≥ 6%)"
            severity = "ok"
        else:
            pts = 0
            detail = f"ROE bajo ({roe_pct*100:.1f}% < 6%)"
            severity = "weak"
        score += pts
        details.append({"metric": "ROE", "points": pts, "max": H["roe_points"][0], "detail": detail, "severity": severity})
    
    # 3. D/E Bancario (0-2 puntos) - NUEVO: Interpretación correcta para bancos
    # Los bancos operan normalmente con D/E de 8-15x, así que 2.6x es MUY conservador
    if debt_to_equity is not None:
        max_possible += H["de_points"][0]
        if debt_to_equity < b["de_very_conservative"]:
            pts = H["de_points"][0]
            detail = f"D/E muy conservador ({debt_to_equity:.1f}x < 5x) - Excelente para banco"
            severity = "excellent"
        elif debt_to_equity < b["de_conservative"]:
            pts = H["de_points"][1]
            detail = f"D/E conservador ({debt_to_equity:.1f}x < 10x) - Sólido"
            severity = "good"
        elif debt_to_equity < b["de_normal"]:
            pts = H["de_points"][2]
            detail = f"D/E normal ({debt_to_equity:.1f}x) - Típico bancario"
            severity = "ok"
        else:
            pts = 0
            detail = f"D/E elevado ({debt_to_equity:.1f}x > 15x)"
            severity = "moderate"
        score += pts
        details.append({"metric": "D/E Bancario", "points": pts, "max": H["de_points"][0], "detail": detail, "severity": severity})
    elif total_equity is not None and total_assets is not None and total_assets > 0:
        # Fallback: usar Equity/Assets si no hay D/E
        max_possible += H["equity_to_assets_points"][0]
        equity_ratio = total_equity / total_assets
        if equity_ratio >= b["equity_to_assets_solid"]:
            pts = H["equity_to_assets_points"][0]
            detail = f"Capitalización sólida ({equity_ratio*100:.1f}% ≥ 6%)"
            severity = "excellent"
        elif equity_ratio >= b["equity_to_assets_good"]:
            pts = H["equity_to_assets_points"][1]
            detail = f"Capitalización aceptable ({equity_ratio*100:.1f}%)"
            severity = "ok"
        else:
            pts = 0
            detail = f"Capitalización baja ({equity_ratio*100:.1f}%)"
            severity = "weak"
        score += pts
        details.append({"metric": "Equity/Assets", "points": pts, "max": H["equity_to_assets_points"][0], "detail": detail, "severity": severity})
    
    # 4. Book Value Growth (0-1 punto)
    if book_value is not None and book_value_prior is not None and book_value_prior > 0:
        max_possible += H["book_value_growth_points"]
        bv_growth = (book_value - book_value_prior) / book_value_prior
        if bv_growth > 0:
            pts = H["book_value_growth_points"]
            detail = f"Book Value creciendo ({bv_growth*100:.1f}% YoY)"
            severity = "excellent"
        else:
            pts = 0
            detail = f"Book Value decreciendo ({bv_growth*100:.1f}% YoY)"
            severity = "weak"
        score += pts
        details.append({"metric": "Book Value Growth", "points": pts, "max": H["book_value_growth_points"], "detail": detail, "severity": severity})
    
    # 5. Dividend (0-1 punto) - Bancos suelen pagar dividendos
    if dividend_yield is not None and dividend_yield > 0:
        max_possible += H["dividend_points"]
        # Un payout negativo (dividendos pagados con ganancias negativas, año en
        # pérdidas) NO es sostenible: antes `payout < 0.60` lo daba por sostenible.
        _sustainable = 0 <= payout_ratio < b["payout_sustainable"] if payout_ratio is not None else True
        if _sustainable:
            pts = H["dividend_points"]
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
        details.append({"metric": "Dividendo", "points": pts, "max": H["dividend_points"], "detail": detail, "severity": severity})
    
    # =====================================================
    # MANEJO DE DATOS FALTANTES: Escalar a 10 puntos
    # Si solo tenemos algunos datos, escalar proporcionalmente
    # NO penalizar por datos que no tenemos
    # =====================================================
    if max_possible > 0:
        # Escalar score a base 10
        scaled_score = round((score / max_possible) * H["scale"])
    else:
        # Sin datos: puntuación neutral (5/10)
        scaled_score = H["neutral_without_data"]
        details.append({
            "metric": "Datos Limitados", 
            "points": H["neutral_without_data"], 
            "max": H["scale"], 
            "detail": "Análisis limitado - métricas bancarias regulatorias no disponibles",
            "severity": "neutral"
        })
    
    # Determinar nivel de riesgo e interpretación
    if scaled_score >= H["level_bands"][0]:
        risk_level = "STRONG"
        interpretation = "Excelente - Institución financiera muy sólida"
    elif scaled_score >= H["level_bands"][1]:
        risk_level = "GOOD"
        interpretation = "Buena salud financiera"
    elif scaled_score >= H["level_bands"][2]:
        risk_level = "NEUTRAL"
        interpretation = "Neutral - Dentro de parámetros normales"
    else:
        risk_level = "WEAK"
        interpretation = "Por debajo del promedio sectorial"
    
    # Agregar nota si el análisis es limitado
    if max_possible < H["limited_analysis_below"]:
        interpretation += " (análisis limitado por datos disponibles)"
    
    return scaled_score, risk_level, interpretation, details


PIOTROSKI_CRITERIA = (
    "roa_positive", "cfo_positive", "roa_improved", "earnings_quality",
    "debt_reduced", "current_ratio_improved", "no_dilution",
    "gross_margin_improved", "asset_turnover_improved",
)
PIOTROSKI_STATES = ("cumple", "no_cumple", "sin_dato")
_PIO_SYMBOL = {"cumple": "✓", "no_cumple": "✗", "sin_dato": "✗"}


def piotroski_evaluate(
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
) -> Dict[str, Any]:
    """
    Piotroski F-Score (Piotroski, 2000) con TRES estados por criterio.

    Cada una de las 9 señales es "cumple", "no_cumple" o "sin_dato". Un dato
    ausente NO cuenta como incumplimiento (etapa 5): se excluye y se reporta la
    cobertura "X/N evaluados".

      · N >= min_evaluated (7, config): resultado escalado a base 9 (X·9/N)
        para las bandas 8/6/4/2 y para los puntos de Calidad.
      · N <  min_evaluated: "no concluyente"; no aporta a Calidad.

    RENTABILIDAD: ROA > 0 · CFO > 0 · ROA mejoró · CFO > beneficio neto
    APALANCAMIENTO/LIQUIDEZ: deuda LP ≤ año previo · current ratio mejoró · sin dilución
    EFICIENCIA: margen bruto mejoró · rotación de activos mejoró
    """
    crit = []

    def add(key, state, detail):
        crit.append({"key": key, "state": state, "detail": detail})

    def cmp(key, cur, prev, ok, ok_txt, ko_txt, nodata_txt):
        if cur is None or prev is None:
            add(key, "sin_dato", nodata_txt)
        elif ok(cur, prev):
            add(key, "cumple", ok_txt)
        else:
            add(key, "no_cumple", ko_txt)

    # 1. ROA positivo
    if roa_current is None:
        add("roa_positive", "sin_dato", "Sin datos de ROA")
    elif roa_current > 0:
        add("roa_positive", "cumple", "ROA positivo")
    else:
        add("roa_positive", "no_cumple", "ROA negativo")
    # 2. CFO positivo
    if operating_cash_flow is None:
        add("cfo_positive", "sin_dato", "Sin datos de Cash Flow Operativo")
    elif operating_cash_flow > 0:
        add("cfo_positive", "cumple", "Cash Flow Operativo positivo")
    else:
        add("cfo_positive", "no_cumple", "CFO negativo")
    # 3. ROA mejoró
    cmp("roa_improved", roa_current, roa_prior, lambda c, p: c > p,
        "ROA mejoró vs año anterior", "ROA no mejoró", "Sin datos ROA histórico")
    # 4. Calidad de earnings (CFO > Net Income)
    cmp("earnings_quality", operating_cash_flow, net_income, lambda c, p: c > p,
        "CFO > Net Income (earnings de calidad)", "CFO < Net Income (alerta calidad)",
        "Sin datos para calidad de earnings")
    # 5. Deuda LP disminuyó o igual
    cmp("debt_reduced", long_term_debt_current, long_term_debt_prior, lambda c, p: c <= p,
        "Deuda LP estable o disminuyó", "Deuda LP aumentó", "Sin datos de deuda LP histórica")
    # 6. Current Ratio mejoró
    cmp("current_ratio_improved", current_ratio_current, current_ratio_prior, lambda c, p: c > p,
        "Liquidez (Current Ratio) mejoró", "Liquidez no mejoró", "Sin datos de liquidez histórica")
    # 7. Sin dilución
    cmp("no_dilution", shares_current, shares_prior, lambda c, p: c <= p,
        "Sin dilución de acciones", "Emisión de nuevas acciones (dilución)", "Sin datos de acciones históricas")
    # 8. Margen bruto mejoró
    cmp("gross_margin_improved", gross_margin_current, gross_margin_prior, lambda c, p: c > p,
        "Margen bruto mejoró", "Margen bruto no mejoró", "Sin datos de margen bruto histórico")
    # 9. Rotación de activos mejoró
    cmp("asset_turnover_improved", asset_turnover_current, asset_turnover_prior, lambda c, p: c > p,
        "Eficiencia de activos mejoró", "Eficiencia de activos no mejoró", "Sin datos de asset turnover histórico")

    total = len(PIOTROSKI_CRITERIA)
    passed = sum(1 for c in crit if c["state"] == "cumple")
    evaluated = sum(1 for c in crit if c["state"] != "sin_dato")
    conclusive = evaluated >= _PIOTROSKI["min_evaluated"]
    scaled = None
    if conclusive:
        # Con los 9 evaluados el escalado es la identidad (y se conserva el int).
        scaled = passed if evaluated == total else passed * total / evaluated

    pb = _PIOTROSKI["bands"]
    if not conclusive:
        interpretation = (f"Datos históricos limitados ({total - evaluated}/{total} señales sin evaluar) "
                          f"- F-Score no concluyente")
    elif scaled >= pb[0]:
        interpretation = "Excelente - Fortaleza financiera excepcional"
    elif scaled >= pb[1]:
        interpretation = "Bueno - Salud financiera sólida"
    elif scaled >= pb[2]:
        interpretation = "Neutral - Monitorear indicadores"
    elif scaled >= pb[3]:
        interpretation = "Débil - Señales de debilidad financiera"
    else:
        interpretation = "Crítico - Alto riesgo de problemas"

    return {
        "score": passed,
        "evaluated": evaluated,
        "max_score": total,
        "scaled_score": scaled,
        "conclusive": conclusive,
        "criteria": crit,
        "interpretation": interpretation,
    }


def piotroski_level(scaled: Optional[float], conclusive: bool) -> str:
    """Insignia de la escala única (Fuerte/Bueno/Neutral/Débil/Crítico)."""
    if not conclusive or scaled is None:
        return "No concluyente"
    b = _PIOTROSKI["bands"]
    return ("Fuerte" if scaled >= b[0] else "Bueno" if scaled >= b[1]
            else "Neutral" if scaled >= b[2] else "Débil" if scaled >= b[3] else "Crítico")


def piotroski_f_score(*args, **kwargs) -> Tuple[int, List[str], str]:
    """Compatibilidad: (aprobados, detalles con ✓/✗, interpretación).

    Un criterio sin dato aparece como "✗ Sin datos..." en el texto, pero NO
    cuenta como incumplimiento: usa piotroski_evaluate para el estado."""
    r = piotroski_evaluate(*args, **kwargs)
    details = [f"{_PIO_SYMBOL[c['state']]} {c['detail']}" for c in r["criteria"]]
    return r["score"], details, r["interpretation"]


# Etapa 9a: métricas del desglose calculadas con el beneficio normalizado (etapa 7).
_NORMALIZED_LABELS = {"ROE": ("roe", "ROE normalizado"), "ROA": ("roa", "ROA normalizado"),
                      "Margen Neto": ("net_margin", "Margen neto normalizado"),
                      "FCF / Net Income": ("fcf_to_net_income", "FCF / beneficio neto normalizado"),
                      "P/E vs Sector": ("pe", "P/E normalizado vs Sector")}


def label_normalized(categories: List[Dict[str, Any]], keys) -> None:
    """Toda cifra del desglose calculada con el beneficio normalizado lo indica en
    el nombre ("ROE normalizado" 55.9%) y lleva normalized=True. El Forward P/E
    compara el P/E normalizado con el forward: lo dice su motivo."""
    keys = set(keys or [])
    if not keys:
        return
    for cat in categories:
        for a in cat.get("adjustments") or []:
            m = a.get("metric")
            if m in _NORMALIZED_LABELS and _NORMALIZED_LABELS[m][0] in keys:
                a["metric"], a["normalized"] = _NORMALIZED_LABELS[m][1], True
            elif m == "Forward P/E" and "pe" in keys and a.get("reason"):
                a["reason"] = a["reason"].replace("P/E", "P/E normalizado", 1)
                a["normalized"] = True


def eps_vs_revenue_growth(revenue_growth: Optional[float], eps_growth: Optional[float],
                          archetype: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """BPA frente a ingresos: DATO INFORMATIVO, no puntúa (etapa 9a).

    Crecimiento ya puntúa el BPA y los ingresos por separado; puntuar además su
    diferencia contaría el BPA dos veces. Mismos crecimientos que usa Crecimiento.
    Sin dato si falta alguno o el BPA no aplica al arquetipo."""
    if not_applicable(archetype, "eps_growth") or revenue_growth is None or eps_growth is None:
        return None
    gap = eps_growth - revenue_growth
    tol = cfg("thresholds.pdf.eps_revenue_gap")
    if gap > tol:
        state, label = "expansion", "BPA por delante"
        reading = ("el BPA crece más rápido que los ingresos: márgenes en expansión, apalancamiento "
                   "operativo o recompras")
    elif gap < -tol:
        state, label = "compresion", "BPA por detrás"
        reading = "el BPA crece más despacio que los ingresos: márgenes en compresión o dilución"
    else:
        state, label = "en_linea", "En línea"
        reading = "el BPA crece en línea con los ingresos"
    return {"revenue_growth": revenue_growth, "eps_growth": eps_growth, "gap": gap, "state": state,
            "label": label, "reading": reading, "scored": False,
            "note": "dato informativo: no puntúa (Crecimiento ya puntúa BPA e ingresos por separado)"}


def growth_for_bands(g: Optional[float]) -> Optional[float]:
    """Estancamiento (etapa 6): un crecimiento entre −tolerancia y 0 se puntúa como
    plano (la banda 0–x%), no como contracción. Agregados aproximados como el FFO
    tienen un error de medición de ese orden. El valor mostrado no cambia."""
    tol = _SC["crecimiento"]["flat_tolerance"]
    return 0.0 if (g is not None and -tol <= g < 0) else g


def _pts_str(v: int) -> str:
    """Puntos como texto de desglose: "+15", "-10", "0"."""
    return "0" if v == 0 else f"{v:+d}"


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
    
    T = _SC["company_type"]

    def vote(table):
        for k, v in table.items():
            scores[k] += v

    # Evaluar métricas de crecimiento
    has_strong_growth = False
    has_quality_growth = False
    
    if revenue_growth_3y is not None:
        b = T["revenue_bounds"]
        if revenue_growth_3y >= b[0]:
            vote(T["revenue_votes_0"])
            has_strong_growth = True
            reasons.append(f"Revenue growth {revenue_growth_3y:.0%}")
        elif revenue_growth_3y >= b[1]:
            vote(T["revenue_votes_1"])
            has_strong_growth = True
        elif revenue_growth_3y >= b[2]:
            vote(T["revenue_votes_2"])
        elif growth_for_bands(revenue_growth_3y) < 0:
            vote(T["revenue_votes_negative"])
    
    if eps_growth_3y is not None:
        b = T["eps_bounds"]
        if eps_growth_3y >= b[0]:
            vote(T["eps_votes_0"])
            has_quality_growth = True
        elif eps_growth_3y >= b[1]:
            vote(T["eps_votes_1"])
    
    # Evaluar valoración
    if pe is not None and pe > 0:
        pe_threshold = sector_pe if sector_pe and sector_pe > 0 else _BENCH_FALLBACK["pe"]
        pe_ratio_to_sector = pe / pe_threshold
        b = T["pe_to_sector_bounds"]
        if pe_ratio_to_sector <= b[0]:
            vote(T["pe_votes_0"])
            reasons.append(f"P/E muy bajo vs sector")
        elif pe_ratio_to_sector <= b[1]:
            vote(T["pe_votes_1"])
        elif pe_ratio_to_sector <= b[2]:
            vote(T["pe_votes_2"])
        elif pe_ratio_to_sector <= b[3]:
            vote(T["pe_votes_3"])
        else:
            vote(T["pe_votes_4"])
            reasons.append(f"P/E elevado ({pe:.0f}x)")
    
    # Evaluar calidad (ROE)
    if roe is not None:
        b = T["roe_bounds"]
        if roe >= b[0]:
            vote(T["roe_votes_0"])
            has_quality_growth = True
            reasons.append(f"ROE excepcional {roe:.0%}")
        elif roe >= b[1]:
            vote(T["roe_votes_1"])
        elif roe < b[2]:
            vote(T["roe_votes_low"])
    
    # Evaluar dividendos
    if dividend_yield is not None:
        b = T["dividend_yield_bounds"]
        if dividend_yield >= b[0]:
            vote(T["dividend_votes_0"])
            reasons.append(f"Alto dividendo {dividend_yield:.1%}")
        elif dividend_yield >= b[1]:
            vote(T["dividend_votes_1"])
    
    # FCF Yield (indicador de value)
    if fcf_yield is not None:
        b = T["fcf_yield_bounds"]
        if fcf_yield >= b[0]:
            vote(T["fcf_yield_votes_0"])
        elif fcf_yield >= b[1]:
            vote(T["fcf_yield_votes_1"])
    
    # Determinar tipo ganador
    best_type = max(scores, key=scores.get)
    best_score = scores[best_type]
    
    # Si hay crecimiento fuerte + calidad, es GARP o Growth legítimo
    if has_strong_growth and has_quality_growth:
        if scores["garp"] >= scores["growth"] - T["garp_tiebreak_margin"]:
            best_type = "garp"
        else:
            best_type = "growth"
        # Reducir speculative si hay calidad
        scores["speculative_growth"] = max(0, scores["speculative_growth"] - T["speculative_reduction"])
    
    # Calcular confianza
    total_score = sum(scores.values())
    confidence = best_score / max(total_score, 1)
    
    # Si la confianza es baja, es blend
    if confidence < T["blend_max_confidence"] or best_score < T["blend_min_votes"]:
        best_type = "blend"
        confidence = T["blend_confidence"]
    
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
    T = _SC["growth_quality"]
    score = T["base"]  # Base neutral
    breakdown = []
    
    # 1. Crecimiento de Revenue (hasta ±15 pts)
    if revenue_growth_3y is not None:
        b, p = T["revenue_bounds"], T["revenue_points"]
        if revenue_growth_3y >= b[0]:
            score += p[0]
            breakdown.append(("Revenue Growth", _pts_str(p[0]), "Excepcional"))
        elif revenue_growth_3y >= b[1]:
            score += p[1]
            breakdown.append(("Revenue Growth", _pts_str(p[1]), "Fuerte"))
        elif revenue_growth_3y >= b[2]:
            score += p[2]
            breakdown.append(("Revenue Growth", _pts_str(p[2]), "Sólido"))
        elif growth_for_bands(revenue_growth_3y) >= 0:
            score += p[3]
            breakdown.append(("Revenue Growth", _pts_str(p[3]), "Estable"))
        else:
            score += p[4]
            breakdown.append(("Revenue Growth", _pts_str(p[4]), "Contracción"))
    
    # 2. EPS vs Revenue growth (hasta ±10 pts)
    if eps_growth_3y is not None and revenue_growth_3y is not None:
        m, p = T["eps_vs_revenue_mults"], T["eps_vs_revenue_points"]
        if eps_growth_3y > revenue_growth_3y * m[0]:
            score += p[0]
            breakdown.append(("EPS vs Revenue", _pts_str(p[0]), "Expansión de márgenes"))
        elif eps_growth_3y >= revenue_growth_3y:
            score += p[1]
            breakdown.append(("EPS vs Revenue", _pts_str(p[1]), "Márgenes estables"))
        elif eps_growth_3y >= revenue_growth_3y * m[1]:
            score += p[2]
            breakdown.append(("EPS vs Revenue", _pts_str(p[2]), "Compresión leve"))
        else:
            score += p[3]
            breakdown.append(("EPS vs Revenue", _pts_str(p[3]), "Compresión severa"))
    
    # 3. FCF Growth (hasta ±10 pts)
    if fcf_growth_3y is not None:
        b, p = T["fcf_bounds"], T["fcf_points"]
        if fcf_growth_3y >= b[0]:
            score += p[0]
            breakdown.append(("FCF Growth", _pts_str(p[0]), "Excelente"))
        elif fcf_growth_3y >= b[1]:
            score += p[1]
            breakdown.append(("FCF Growth", _pts_str(p[1]), "Positivo"))
        elif growth_for_bands(fcf_growth_3y) >= 0:
            score += p[2]
            breakdown.append(("FCF Growth", _pts_str(p[2]), "Estable"))
        else:
            score += p[3]
            breakdown.append(("FCF Growth", _pts_str(p[3]), "Negativo"))
    
    # 4. ROE/ROIC - Calidad del capital (hasta ±10 pts)
    best_return = max(filter(None, [roe, roic]), default=None)
    if best_return is not None:
        b, p = T["return_bounds"], T["return_points"]
        if best_return >= b[0]:
            score += p[0]
            breakdown.append(("Return on Capital", _pts_str(p[0]), "Excepcional"))
        elif best_return >= b[1]:
            score += p[1]
            breakdown.append(("Return on Capital", _pts_str(p[1]), "Bueno"))
        elif best_return >= b[2]:
            score += p[2]
            breakdown.append(("Return on Capital", _pts_str(p[2]), "Aceptable"))
        else:
            score += p[3]
            breakdown.append(("Return on Capital", _pts_str(p[3]), "Bajo"))
    
    # 5. Margen operativo (hasta ±5 pts)
    if operating_margin is not None:
        b, p = T["operating_margin_bounds"], T["operating_margin_points"]
        if operating_margin >= b[0]:
            score += p[0]
            breakdown.append(("Op. Margin", _pts_str(p[0]), "Muy alto"))
        elif operating_margin >= b[1]:
            score += p[1]
            breakdown.append(("Op. Margin", _pts_str(p[1]), "Saludable"))
        elif operating_margin < b[2]:
            score += p[2]
            breakdown.append(("Op. Margin", _pts_str(p[2]), "Bajo"))
    
    # Normalizar a 0-100
    score = max(T["min"], min(T["max"], score))
    
    # Determinar nivel
    lv = T["level_bands"]
    if score >= lv[0]:
        level = "exceptional"
        label = "Crecimiento Excepcional"
    elif score >= lv[1]:
        level = "high_quality"
        label = "Alta Calidad"
    elif score >= lv[2]:
        level = "moderate"
        label = "Calidad Moderada"
    elif score >= lv[3]:
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


_TD = cfg("sectors.score_thresholds.default")


@dataclass
class ThresholdConfig:
    """Umbrales del score ajustables por sector (defaults en sectors.toml)."""
    # Valoración
    pe_overvalued_mult: float = _TD["pe_overvalued_mult"]
    pe_undervalued_mult: float = _TD["pe_undervalued_mult"]
    pe_historical_overvalued_mult: float = _TD["pe_historical_overvalued_mult"]
    pe_historical_undervalued_mult: float = _TD["pe_historical_undervalued_mult"]
    p_fcf_high: float = _TD["p_fcf_high"]
    p_fcf_low: float = _TD["p_fcf_low"]
    ev_ebitda_overvalued_mult: float = _TD["ev_ebitda_overvalued_mult"]
    ev_ebitda_undervalued_mult: float = _TD["ev_ebitda_undervalued_mult"]
    fcf_yield_low: float = _TD["fcf_yield_low"]
    fcf_yield_high: float = _TD["fcf_yield_high"]
    peg_overvalued: float = _TD["peg_overvalued"]
    peg_undervalued: float = _TD["peg_undervalued"]

    # Apalancamiento
    net_debt_ebitda_high: float = _TD["net_debt_ebitda_high"]
    net_debt_ebitda_low: float = _TD["net_debt_ebitda_low"]
    debt_equity_high: float = _TD["debt_equity_high"]
    interest_coverage_low: float = _TD["interest_coverage_low"]

    # Liquidez
    current_ratio_low: float = _TD["current_ratio_low"]
    current_ratio_high: float = _TD["current_ratio_high"]
    quick_ratio_low: float = _TD["quick_ratio_low"]

    # Rentabilidad
    roe_high: float = _TD["roe_high"]
    roe_low: float = _TD["roe_low"]
    roa_high: float = _TD["roa_high"]
    roa_low: float = _TD["roa_low"]
    operating_margin_low: float = _TD["operating_margin_low"]
    net_margin_low: float = _TD["net_margin_low"]

    # Volatilidad
    beta_high: float = _TD["beta_high"]
    beta_low: float = _TD["beta_low"]


def _sector_thresholds():
    out = {}
    for sector, overrides in cfg("sectors.score_thresholds.overrides").items():
        try:
            out[sector] = ThresholdConfig(**overrides)
        except TypeError as e:
            from settings import SettingsError
            raise SettingsError(f"sectors.score_thresholds.overrides.{sector}: {e}") from None
    out["default"] = ThresholdConfig()
    return out


# Configuraciones por sector (PROVISIONALES: ver sectors.toml)
SECTOR_THRESHOLDS = _sector_thresholds()


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


def roic_significant(invested_capital: Optional[float], total_assets: Optional[float]) -> bool:
    """Regla M (etapa 9a): el ROIC no es significativo si el capital invertido
    (patrimonio + deuda − caja) es menor que roic_min_invested_capital_share de los
    activos: la caja encoge el denominador y el ratio se dispara (SNOW)."""
    if invested_capital is None or invested_capital <= 0:
        return False
    if not total_assets or total_assets <= 0:
        return True
    return invested_capital >= cfg("thresholds.score.rentabilidad.roic_min_invested_capital_share") * total_assets


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


def interest_coverage_state(ic: Optional[float], net_debt: Optional[float]) -> Optional[str]:
    """Estado de la cobertura de intereses (etapa 5).

    · "no_significativo": EBIT < 0 (cobertura negativa) con caja neta (caja >
      deuda total). No hay riesgo de impago: los intereses se pagan con caja;
      la ratio no tiene sentido y no puntúa (misma regla M de la etapa 3).
    · "negativa": EBIT < 0 con deuda neta. Señal real de riesgo: se penaliza,
      pero la cifra negativa no se presenta como una cobertura.
    · "ok": cobertura >= 0. None si no hay cobertura."""
    if ic is None:
        return None
    if ic < 0:
        return "no_significativo" if (net_debt is not None and net_debt < 0) else "negativa"
    return "ok"


def net_debt_ebitda_state(ebitda: Optional[float], net_debt: Optional[float]) -> Optional[str]:
    """Estado de deuda neta/EBITDA (regla M, etapa 5).

    · "no_significativo": EBITDA <= 0. La ratio no tiene sentido (su signo lo
      decide el EBITDA, no la caja): no se lee ni como caja neta ni como deuda.
    · "caja_neta": caja > deuda total (deuda neta < 0) con EBITDA > 0.
    · "ok": deuda neta >= 0 con EBITDA > 0. None si falta algún dato."""
    if ebitda is not None and ebitda <= 0:
        return "no_significativo"
    if ebitda is None or net_debt is None:
        return None
    return "caja_neta" if net_debt < 0 else "ok"


NET_CASH_TEXT = "la posición de caja supera a la deuda total (caja neta)"
IC_NOT_SIGNIFICANT = "No significativo: EBIT < 0 con caja neta (caja > deuda total); los intereses se pagan con caja"
IC_NEGATIVE = "Negativa (EBIT < 0)"


# =========================
# RATIOS DE EFICIENCIA
# =========================

def asset_turnover(revenue: Optional[float], average_total_assets: Optional[float]) -> Optional[float]:
    """Asset Turnover = Revenue / Average Total Assets."""
    return safe_div(revenue, average_total_assets)


def inventory_turnover(cost_of_goods_sold: Optional[float], average_inventory: Optional[float]) -> Optional[float]:
    """Inventory Turnover = Cost of Goods Sold / Average Inventory."""
    return safe_div(cost_of_goods_sold, average_inventory)


def graham_number(eps: Optional[float], book_value_ps: Optional[float]) -> Optional[float]:
    """Graham Number = sqrt(22.5 × EPS × Book Value per Share).
    Precio máximo a pagar según Benjamin Graham.
    """
    if eps is None or book_value_ps is None:
        return None
    if eps <= 0 or book_value_ps <= 0:
        return None
    return (cfg("valuation.graham.multiplier") * eps * book_value_ps) ** 0.5


def dcf_multi_stage(
    fcf: Optional[float],
    shares_outstanding: Optional[float],
    high_growth_rate: float = _DCF["signature_default_growth"],
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
        # Salvaguarda (etapa 8): con g >= WACC el valor terminal de Gordon no está
        # definido (divide por <= 0). Sin dato con motivo, nunca un valor.
        result["warnings"].append("g >= WACC: el valor terminal no está definido")
        result["invalid_reason"] = (f"crecimiento terminal {terminal_growth:.1%} >= WACC {discount_rate:.1%}: "
                                    "el valor terminal no está definido")
        return result

    # Etapa 8: un crecimiento de corto plazo por debajo del terminal ya NO se eleva
    # al terminal (FCX local 1.6% -> 2.5%): se respeta y converge hacia el terminal
    # en la etapa 2, igual que uno por encima converge hacia abajo.
    
    MAX_GROWTH = _DCF["growth_cap"]
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
    
    decay_factor = _DCF["exponential_decay_factor"] if decay_type == "exponential" else 1.0
    
    for year in range(1, high_growth_years + 1):
        if decay_type == "linear":
            year_growth = high_growth_rate - (yearly_decay * (year - 1))
        elif decay_type == "exponential":
            year_growth = terminal_growth + (high_growth_rate - terminal_growth) * (decay_factor ** (year - 1))
        else:
            year_growth = high_growth_rate
        
        # no cruza el terminal: converge hacia él desde arriba o desde abajo
        year_growth = max(year_growth, terminal_growth) if high_growth_rate >= terminal_growth \
            else min(year_growth, terminal_growth)
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
        year_growth = end_stage1_growth - (transition_decay * (i + 1))   # lineal hasta el terminal
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
    
    if result["value_composition"]["terminal_pct"] > _DCF["terminal_value_warning_pct"]:
        result["warnings"].append(
            f"Terminal value representa {result['value_composition']['terminal_pct']:.0f}% del valor"
        )
    
    return result


def dcf_multi_stage_dynamic(
    fcf: Optional[float],
    shares_outstanding: Optional[float],
    wacc: Optional[float] = None,
    total_debt: Optional[float] = None,
    cash: Optional[float] = None,
    revenue_growth_3y: Optional[float] = None,
    eps_growth_3y: Optional[float] = None,
    fcf_growth_3y: Optional[float] = None,
    terminal_growth: float = DCF_TERMINAL_GROWTH,
    high_growth_years: int = DCF_HIGH_GROWTH_YEARS,
    transition_years: int = DCF_TRANSITION_YEARS,
    margin_of_safety_pct: float = 0.0,
) -> Dict[str, Any]:
    """
    DCF Multi-Stage Dinámico - Combina modelo de 3 etapas con 
    WACC y growth calculados dinámicamente.

    Etapa 8: el WACC llega ya calculado y acotado (cost_of_capital.wacc): el
    mismo que el grid y el spread ROIC−WACC. Sin WACC no hay DCF.
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
    }
    
    if fcf is None or shares_outstanding is None or shares_outstanding <= 0:
        result["warnings"].append("FCF o shares no disponibles")
        return result
    
    if fcf <= 0:
        result["warnings"].append("FCF negativo - DCF no aplicable")
        return result
    
    if wacc is None:
        result["warnings"].append("sin WACC (sin capitalización para los pesos)")
        result["invalid_reason"] = "sin WACC: no hay capitalización bursátil para ponderar"
        return result
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
        (fcf_growth_3y, "fcf_growth_3y", _DCF["source_cap_fcf"]),
        (eps_growth_3y, "eps_growth_3y", _DCF["source_cap_eps"]),
        (revenue_growth_3y, "revenue_growth_3y", _DCF["source_cap_revenue"]),
    ]
    
    for growth_val, source, cap in growth_candidates:
        if growth_val is not None and growth_val > _DCF["min_source_growth"]:
            growth_rate = min(growth_val, cap)   # etapa 8: sin suelo en el terminal
            growth_source = source
            break
    
    if growth_rate is None:
        growth_rate = _DCF["default_growth"]
        growth_source = "default_estimate"
        result["warnings"].append("Growth estimado en 8%")
    
    result["growth_estimated"] = growth_rate
    result["growth_source"] = growth_source
    
    # EJECUTAR DCF MULTI-STAGE
    if growth_rate > _DCF["decay_exponential_above"]:
        decay_type = "exponential"
    elif growth_rate > _DCF["decay_linear_above"]:
        decay_type = "linear"
    else:
        decay_type = "step"
    result["decay_type"] = decay_type  # el grid de sensibilidad usa el mismo
    
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
    
    if model_result.get("invalid_reason"):
        result["invalid_reason"] = model_result["invalid_reason"]
    if model_result["is_valid"]:
        result["fair_value_per_share"] = model_result["fair_value_per_share"]
        result["fair_value_with_mos"] = model_result["fair_value_with_mos"]
        result["is_valid"] = True

    return result


def margin_of_safety(intrinsic_value: Optional[float], current_price: Optional[float]) -> Optional[float]:
    """Margin of Safety = (Intrinsic Value - Current Price) / Intrinsic Value.
    Positivo indica subvaloración, negativo indica sobrevaloración.
    """
    if intrinsic_value is None or current_price is None or intrinsic_value == 0:
        return None
    return (intrinsic_value - current_price) / intrinsic_value


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
    # Etapa 8: la tasa efectiva de la empresa (main.py, cost_of_capital.effective_tax_rate),
    # la misma del escudo fiscal del WACC; sin ella, el tipo legal.
    tax_rate = d.get("tax_rate", cfg("valuation.tax.statutory_rate"))
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
        if invested_cap <= 0 or not roic_significant(invested_cap, d.get("total_assets")):
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


class CategoryCoverage:
    """Cobertura de una categoría del score (etapa 5).

    Cada componente APLICABLE se registra con sus puntos posibles (de la config)
    y su ajuste, o None si no tiene dato. La categoría puntúa sobre los
    componentes con dato y se reescala a su rango completo, como
    financial_health_score: la parte positiva de los ajustes sobre la suma de
    máximos disponibles y la negativa sobre la de mínimos. Así:
      · con todos los datos el factor es 1 y el score no cambia;
      · con un dato ausente el resultado queda entre el que tendría con ese dato
        en su peor y en su mejor valor (no penaliza como incumplimiento ni
        premia por ocultarlo).
    Los bonos (forward P/E, GARP, growth, rescates) quedan fuera del reescalado.

    Etapa 6: un componente puede además NO APLICAR al arquetipo (`na` con el
    motivo). No es un dato ausente: no cuenta en la cobertura (ni en el
    numerador ni en el denominador), no puede volver la categoría no
    concluyente y el informe lo muestra como "No aplica a …", aparte de "sin dato".
    """

    def __init__(self):
        self.items = []
        self.reasons: Dict[str, str] = {}
        self.not_applicable: Dict[str, str] = {}
        # Etapa 9a (bloque de múltiplos): los miembros de un bloque cuentan en la
        # cobertura pero no se reescalan uno a uno; se reescala el bloque (derived).
        self.unscaled: set = set()
        self.derived: List[Any] = []

    def comp(self, name: str, points, adj, reason: Optional[str] = None, na: Optional[str] = None,
             rescale: bool = True) -> None:
        if na:
            self.not_applicable[name] = na
            return
        pts = [p for p in points]
        self.items.append((name, max(pts), min(pts), adj))
        if not rescale:
            self.unscaled.add(name)
        if adj is None and reason:
            self.reasons[name] = reason

    def derived_comp(self, name: str, points, adj) -> None:
        """Componente derivado (el bloque): entra en el reescalado, no en el recuento."""
        self.derived.append((name, max(points), min(points), adj))

    @property
    def scaled_items(self) -> List[Any]:
        return [it for it in self.items if it[0] not in self.unscaled] + self.derived

    @property
    def missing(self) -> List[str]:
        return [n for n, _, _, a in self.items if a is None]

    def report(self) -> Dict[str, Any]:
        n = len(self.items)
        ev = n - len(self.missing)
        cov = (ev / n) if n else None
        return {"components": n, "evaluated": ev, "coverage": cov, "missing": self.missing,
                "missing_reasons": dict(self.reasons),
                "not_applicable": dict(self.not_applicable),
                "applicable": self.applicable,
                "conclusive": self.conclusive,
                "low_confidence": (cov is not None and cov < _CAT_COVERAGE["low_confidence_below"])}

    @property
    def applicable(self) -> bool:
        """False solo si NINGÚN componente aplica al arquetipo (categoría "no aplica")."""
        return len(self.items) > 0

    @property
    def conclusive(self) -> bool:
        """Con menos de min_conclusive (50%) de componentes con dato la categoría
        no se reescala: se excluye del total y se declara no concluyente."""
        n = len(self.items)
        return n > 0 and (n - len(self.missing)) / n >= _CAT_COVERAGE["min_conclusive"]

    def apply(self, base_score, adjustments: List[Dict[str, Any]]):
        """Devuelve base_score con el reescalado aplicado (sin cambio si cobertura completa)."""
        if self.not_applicable:
            whys = sorted(set(self.not_applicable.values()))
            if len(whys) > 1:   # motivos distintos: cada uno con sus componentes
                whys = [", ".join(n for n, w in self.not_applicable.items() if w == why) + f": {why}"
                        for why in whys]
            adjustments.append({
                "metric": "No aplica", "value": ", ".join(self.not_applicable), "adjustment": 0,
                "reason": "; ".join(whys) + " (no cuenta en la cobertura)", "severity": "neutral",
            })
        if not self.missing:
            return base_score
        if not self.conclusive:
            n, ev = len(self.items), len(self.items) - len(self.missing)
            adjustments.append({
                "metric": "Cobertura", "value": f"{ev}/{n} componentes", "adjustment": 0,
                "reason": ("Categoría no concluyente: menos del "
                           f"{_CAT_COVERAGE['min_conclusive']:.0%} de sus componentes con dato; "
                           "se excluye del total (sin dato: " + ", ".join(self.missing) + ")"),
                "severity": "neutral",
            })
            return base_score
        items = self.scaled_items
        av = [(mx, mn, a) for _, mx, mn, a in items if a is not None]
        r_pos = sum(mx for _, mx, _, _ in items)
        r_neg = sum(-mn for _, _, mn, _ in items)
        ra_pos = sum(mx for mx, _, _ in av)
        ra_neg = sum(-mn for _, mn, _ in av)
        s_pos = sum(a for _, _, a in av if a > 0)
        s_neg = sum(a for _, _, a in av if a < 0)
        scaled = ((s_pos * r_pos / ra_pos) if ra_pos else 0) + ((s_neg * r_neg / ra_neg) if ra_neg else 0)
        delta = round(scaled) - (s_pos + s_neg)
        n, ev = len(self.items), len(self.items) - len(self.missing)
        if all(a is not None for *_, a in items):
            # Solo faltan miembros de un bloque: el bloque ya promedia sobre los que
            # tienen dato, no hay nada que reescalar.
            return base_score
        adjustments.append({
            "metric": "Cobertura", "value": f"{ev}/{n} componentes", "adjustment": delta,
            "reason": ("Reescalado sobre los componentes con dato (sin dato: " + ", ".join(self.missing) + ")"),
            "severity": "neutral",
        })
        return base_score + delta


def score_solidez_financiera(
    z_score: Optional[float],
    z_score_level: str,
    current_ratio: Optional[float],
    debt_to_equity: Optional[float],
    interest_coverage: Optional[float],
    sector_de_threshold: float = _TD["debt_equity_high"],
    net_debt: Optional[float] = None,
    archetype: Optional[str] = None,
    runway: Optional[Dict[str, Any]] = None,
    market: bool = False,
    net_debt_to_ebitda: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Categoría 1: Solidez Financiera (20 pts máximo)
    GROWTH_PRE_PROFIT: el runway sustituye al Altman (que no aplica), con su peso.
    Base: 10 pts, ajusta según métricas
    """
    T = _SC["solidez"]
    base_score = _CAT["base"]
    _a = {}  # ajuste de cada componente con dato (etapa 5: cobertura)
    adjustments = []
    # Etapa 6: componentes que no aplican al arquetipo (REIT: Altman).
    _na = {k: not_applicable(archetype, k) for k in ("altman", "current_ratio", "de", "interest_coverage")}
    if _na["altman"]:
        z_score = None
    if _na["current_ratio"]:
        current_ratio = None
    if _na["de"]:
        debt_to_equity = None
    if _na["interest_coverage"]:
        interest_coverage = None
    
    # Z-Score (peso alto: hasta ±6 pts)
    if z_score is not None:
        if z_score_level == "SAFE":
            adj = T["altman_points"][0]
            adjustments.append({"metric": "Altman Z-Score", "value": f"{z_score:.2f}", "adjustment": adj, "reason": "Zona segura - Muy baja probabilidad de quiebra", "severity": "excellent"})
        elif z_score_level == "GREY":
            adj = T["altman_points"][1]
            adjustments.append({"metric": "Altman Z-Score", "value": f"{z_score:.2f}", "adjustment": adj, "reason": "Zona gris - Requiere monitoreo cercano", "severity": "moderate"})
        elif z_score_level == "DISTRESS":
            adj = T["altman_points"][2]
            adjustments.append({"metric": "Altman Z-Score", "value": f"{z_score:.2f}", "adjustment": adj, "reason": "Zona peligro - Riesgo significativo de problemas", "severity": "severe"})
        else:
            adj = 0
        base_score += adj
        _a["altman"] = adj if z_score_level in ("SAFE", "GREY", "DISTRESS") else None
    
    # Current Ratio (hasta ±4 pts)
    if current_ratio is not None:
        b, p = T["current_bounds"], T["current_points"]
        if current_ratio >= b[0]:
            adj = p[0]
            sev = "excellent"
            reason = f"Liquidez excelente - Cubre 2x sus deudas corto plazo"
        elif current_ratio >= b[1]:
            adj = p[1]
            sev = "good"
            reason = f"Liquidez sólida - Buena capacidad de pago ({current_ratio:.2f}x)"
        elif current_ratio >= b[2]:
            adj = p[2]
            sev = "ok"
            reason = f"Liquidez justa - Cubre sus obligaciones ({current_ratio:.2f}x)"
        elif current_ratio >= b[3]:
            adj = p[3]
            sev = "moderate"
            reason = f"Liquidez ajustada - Poco margen de maniobra ({current_ratio:.2f}x)"
        else:
            adj = p[4]
            sev = "severe"
            reason = f"Riesgo de liquidez - Podría tener problemas de pago ({current_ratio:.2f}x)"
        
        base_score += adj
        _a["current"] = adj
        adjustments.append({"metric": "Current Ratio", "value": f"{current_ratio:.2f}x", "adjustment": adj, "reason": reason, "severity": sev})
    
    # Etapa 9a: el D/E no puntúa (queda informativo) en REIT, cuyo apalancamiento se
    # mide por deuda neta/EBITDA, ni con caja neta (regla M: no mide apalancamiento).
    _de_info = None
    if debt_to_equity is not None and archetype == REIT:
        _de_info = "Informativo: en REIT el apalancamiento se mide por deuda neta/EBITDA"
    elif debt_to_equity is not None and net_debt is not None and net_debt < 0:
        _de_info = "No significativo con caja neta (más efectivo que deuda): no mide apalancamiento, no puntúa"
    if _de_info:
        adjustments.append({"metric": "Deuda/Equity", "value": f"{debt_to_equity:.2f}x", "adjustment": 0,
                            "reason": _de_info, "severity": "neutral", "informative": True})
    # Debt/Equity (hasta ±5 pts) - proporcional al sector
    elif debt_to_equity is not None:
        threshold = sector_de_threshold
        m, p = T["de_mults"], T["de_points"]
        if debt_to_equity < 0:
            # Negative book equity (buybacks) makes D/E negative and useless as a
            # leverage gauge — a very negative value is NOT "low debt". Treat it
            # neutral; interest coverage and the leverage flags (which use
            # equity-independent ratios) assess the real leverage.
            adj = 0
            sev = "ok"
            reason = f"D/E no informativo (patrimonio negativo, {debt_to_equity:.1f}x) — evaluar por cobertura de intereses"
        elif debt_to_equity <= threshold * m[0]:
            adj = p[0]
            sev = "excellent"
            reason = f"Deuda muy baja - Estructura financiera conservadora"
        elif debt_to_equity <= threshold:
            adj = p[1]
            sev = "good"
            reason = f"Deuda controlada - Dentro del rango saludable ({debt_to_equity:.2f}x)"
        elif debt_to_equity <= threshold * m[1]:
            adj = p[2]
            sev = "ok"
            reason = f"Deuda aceptable - Cerca del límite {'del mercado' if market else 'sectorial'} ({debt_to_equity:.2f}x)"
        elif debt_to_equity <= threshold * m[2]:
            adj = p[3]
            sev = "moderate"
            reason = (f"Deuda elevada - Por encima {'del mercado' if market else 'del sector'} "
                      f"({debt_to_equity:.2f}x vs {threshold:.1f}x)")
        elif interest_coverage is not None and interest_coverage >= T["de_mitigation_coverage"]:
            # Mitigación: D/E alto pero el beneficio operativo cubre los
            # intereses con mucha holgura — típico de mega-caps con patrimonio
            # encogido por recompras, no de empresas sobre-apalancadas. Sin esta
            # gradación, un D/E de 1.0x con cobertura 40x recibía la misma
            # penalización máxima que uno de 8x al borde del impago.
            adj = T["de_mitigated_points"]
            sev = "moderate"
            reason = (f"Deuda alta ({debt_to_equity:.2f}x) pero fácilmente servible "
                      f"(cobertura {interest_coverage:.0f}x) — riesgo acotado")
        else:
            adj = T["de_severe_points"]
            sev = "severe"
            reason = f"Deuda muy alta - Riesgo financiero elevado ({debt_to_equity:.2f}x)"
        
        base_score += adj
        _a["de"] = adj if debt_to_equity >= 0 else None  # D/E < 0: no significativo
        adjustments.append({"metric": "Deuda/Equity", "value": f"{debt_to_equity:.2f}x", "adjustment": adj, "reason": reason, "severity": sev})
    
    # Interest Coverage (hasta ±3 pts). EBIT < 0 con caja neta: no significativo,
    # no puntúa (sin dato). EBIT < 0 con deuda neta: se penaliza (riesgo real).
    _ic_state = interest_coverage_state(interest_coverage, net_debt)
    _ic_reason = None
    if _ic_state == "no_significativo":
        _ic_reason = IC_NOT_SIGNIFICANT
        adjustments.append({"metric": "Cobertura Intereses", "value": "No significativo", "adjustment": 0,
                            "reason": _ic_reason, "severity": "neutral"})
    elif interest_coverage is not None:
        b, p = T["coverage_bounds"], T["coverage_points"]
        if interest_coverage >= b[0]:
            adj = p[0]
            sev = "excellent"
            reason = "Cobertura excelente"
        elif interest_coverage >= b[1]:
            adj = p[1]
            sev = "good"
            reason = "Cobertura sólida"
        elif interest_coverage >= b[2]:
            adj = p[2]
            sev = "ok"
            reason = "Cobertura aceptable"
        elif interest_coverage >= b[3]:
            adj = p[3]
            sev = "moderate"
            reason = "Cobertura ajustada"
        else:
            adj = p[4]
            sev = "severe"
            reason = "Riesgo de cobertura"
        
        base_score += adj
        _a["coverage"] = adj
        if _ic_state == "negativa":
            reason = f"{reason} - EBIT negativo con deuda neta"
        adjustments.append({"metric": "Cobertura Intereses",
                            "value": "EBIT < 0" if _ic_state == "negativa" else f"{interest_coverage:.1f}x",
                            "adjustment": adj, "reason": reason, "severity": sev})
    
    # Runway (GROWTH_PRE_PROFIT, hasta ±6 pts como el Altman al que sustituye)
    _rw_reason = None
    if archetype == GROWTH_PRE_PROFIT:
        rw = runway or {"state": "sin_dato", "reason": "sin FCF TTM"}
        b, p = T["runway_bounds"], T["runway_points"]
        if rw["state"] == "autofinanciada":
            adj, sev, val = p[0], "excellent", "Autofinanciada"
            reason = "FCF TTM positivo: no consume caja"
        elif rw["state"] == "runway":
            y = rw["years"]
            val = f"{y:.1f} años"
            if y >= b[0]:
                adj, sev, reason = p[0], "excellent", f"Caja para más de {b[0]:.0f} años de quema de FCF"
            elif y >= b[1]:
                adj, sev, reason = p[1], "good", "Caja holgada frente a la quema de FCF"
            elif y >= b[2]:
                adj, sev, reason = p[2], "moderate", "Tendrá que financiarse en el horizonte del plan"
            else:
                adj, sev, reason = p[3], "severe", "Menos de un año de caja: financiación urgente, probablemente dilutiva"
        else:
            adj, _rw_reason = None, rw.get("reason") or "sin dato"
        if adj is not None:
            base_score += adj
            _a["runway"] = adj
            adjustments.append({"metric": "Runway", "value": val, "adjustment": adj, "reason": reason,
                                "severity": sev})

    cov = CategoryCoverage()
    cov.comp("Altman Z", T["altman_points"], _a.get("altman"), na=_na["altman"])
    if archetype == GROWTH_PRE_PROFIT:
        cov.comp("Runway", T["runway_points"], _a.get("runway"), _rw_reason)
    cov.comp("Current ratio", T["current_points"], _a.get("current"), na=_na["current_ratio"])
    # REIT (etapa 9a): deuda neta/EBITDA con bandas de REIT es la métrica de apalancamiento.
    if archetype == REIT:
        b, p = T["reit_nde_bounds"], T["reit_nde_points"]
        _nde_reason = None
        if net_debt_to_ebitda is None:
            _nde_reason = "sin deuda neta/EBITDA"
        else:
            if net_debt_to_ebitda < 0:
                adj, sev, lab = p[0], "excellent", "Caja neta"
            else:
                adj, sev, lab = _banded(net_debt_to_ebitda, b, p,
                                        ("Conservador para un REIT", "Adecuado para un REIT", "En línea con REIT",
                                         "Elevado para un REIT", "Alto para un REIT"), higher=False)
            base_score += adj
            _a["nde"] = adj
            adjustments.append({"metric": "Deuda neta/EBITDA", "value": f"{net_debt_to_ebitda:.1f}x", "adjustment": adj,
                                "reason": f"{lab} ({net_debt_to_ebitda:.1f}x; bandas REIT ≤{b[0]:.1f}x / ≤{b[1]:.1f}x / "
                                          f"≤{b[2]:.1f}x / ≤{b[3]:.1f}x)", "severity": sev})
        cov.comp("Deuda neta/EBITDA", p, _a.get("nde"), _nde_reason)
    if not _de_info and archetype != REIT:   # en REIT el D/E es informativo, con o sin dato
        cov.comp("D/E", [*T["de_points"], T["de_mitigated_points"], T["de_severe_points"]], _a.get("de"),
                 na=_na["de"])
    cov.comp("Cobertura de intereses", T["coverage_points"], _a.get("coverage"), _ic_reason,
             na=_na["interest_coverage"])
    base_score = cov.apply(base_score, adjustments)
    final_score = max(_CAT["min"], min(_CAT["max"], base_score))
    
    return {
        "category": "Solidez Financiera",
        "emoji": "🏛️",
        "score": final_score,
        "max_score": _CAT["max"],
        "base": _CAT["base"],
        "adjustments": adjustments,
        "total_adjustment": final_score - _CAT["base"],
        "coverage": cov.report(),
    }


def score_solidez_financiera_financial(
    financial_health: Optional[int],
    financial_health_level: str,
    financial_health_details: List[Dict[str, Any]],
    roe: Optional[float],
    roa: Optional[float],
    price_to_book: Optional[float],
    debt_to_equity: Optional[float] = None,  # Nuevo: D/E para interpretar correctamente
    archetype: Optional[str] = None,
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
    T = _SC["solidez_financial"]
    has_regulatory_data = False  # Yahoo Finance no tiene CET1, Tier 1, etc.
    
    # =====================================================
    # ESTRATEGIA CONSERVADORA:
    # Sin métricas regulatorias, máximo = 18/20
    # Los 2 puntos restantes requieren CET1, Tier 1, NPL, etc.
    # =====================================================
    MAX_WITHOUT_REGULATORY = T["max_without_regulatory"]
    # Etapa 6 (arquetipo FINANCIAL): el D/E contable no aplica (los depósitos son
    # pasivo) y el P/B pasa a Valoración, frente al justificado por el ROE.
    _na_de = not_applicable(archetype, "de")
    if _na_de:
        debt_to_equity = None
    if archetype == FINANCIAL:
        price_to_book = None
    
    if financial_health is not None:
        # Mapeo lineal: FHS 0-10 → Solidez 4-18 (conservador)
        # Fórmula: solidez = 4 + (financial_health * 1.4)
        base_score = T["health_offset"] + (financial_health * T["health_multiplier"])
        _a = {"health": base_score - _CAT["base"]}  # etapa 5: cobertura
        
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
            "adjustment": round(base_score - _CAT["base"]),  # Relativo a base 10
            "reason": reason, 
            "severity": sev,
            "details": financial_health_details
        })
    else:
        # Sin datos: puntuación NEUTRAL (10/20), no penalizar
        base_score = _CAT["base"]
        _a = {}
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
            bonus = T["de_points"][0]
            sev = "excellent"
            reason = f"D/E muy conservador ({debt_to_equity:.1f}x < 5x) - Excepcional para banco"
        elif debt_to_equity < b["de_conservative"]:  # 5-10x
            bonus = T["de_points"][1]
            sev = "good"
            reason = f"D/E conservador ({debt_to_equity:.1f}x) - Sólido para banco"
        elif debt_to_equity < b["de_normal"]:  # 10-15x
            bonus = T["de_points"][2]
            sev = "ok"
            reason = f"D/E normal ({debt_to_equity:.1f}x) - Típico bancario"
        else:  # >15x
            bonus = T["de_points"][3]
            sev = "moderate"
            reason = f"D/E elevado ({debt_to_equity:.1f}x > 15x)"
        
        base_score += bonus
        _a["de"] = bonus
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
            adj = T["pb_points"][0]
            sev = "excellent"
            reason = f"P/B atractivo ({price_to_book:.2f}x) - Bajo valor en libros"
        elif price_to_book <= b["pb_fair"]:  # 0.8-1.2x
            adj = T["pb_points"][1]
            sev = "good"
            reason = f"P/B justo ({price_to_book:.2f}x)"
        elif price_to_book <= b["pb_expensive"]:  # 1.2-2.0x
            adj = T["pb_points"][2]
            sev = "ok"
            reason = f"P/B elevado ({price_to_book:.2f}x)"
        else:  # >2.0x
            adj = T["pb_points"][3]
            sev = "moderate"
            reason = f"P/B muy alto ({price_to_book:.2f}x > 2x)"
        
        base_score += adj
        _a["pb"] = adj
        adjustments.append({
            "metric": "Price/Book",
            "value": f"{price_to_book:.2f}x",
            "adjustment": adj,
            "reason": reason,
            "severity": sev
        })
    
    cov = CategoryCoverage()
    _h_lo = T["health_offset"] - _CAT["base"]
    _h_hi = T["health_offset"] + _FHEALTH["scale"] * T["health_multiplier"] - _CAT["base"]
    cov.comp("Salud bancaria", (_h_lo, _h_hi), _a.get("health"))
    cov.comp("D/E bancario", T["de_points"], _a.get("de"), na=_na_de)
    if archetype != FINANCIAL:
        cov.comp("P/B", T["pb_points"], _a.get("pb"))
    base_score = cov.apply(base_score, adjustments)

    # Aplicar cap conservador: sin métricas regulatorias, máximo 18/20
    if not has_regulatory_data:
        final_score = max(_CAT["min"], min(MAX_WITHOUT_REGULATORY, round(base_score)))
        methodology_note = "Evaluación adaptada para sector bancario (máx 18/20 sin datos regulatorios CET1/Tier1)"
    else:
        final_score = max(_CAT["min"], min(_CAT["max"], round(base_score)))
        methodology_note = "Evaluación completa con métricas regulatorias"
    
    return {
        "category": "Solidez Financiera",
        "emoji": "🏦",
        "score": final_score,
        "max_score": _CAT["max"],
        "base": _CAT["base"],
        "adjustments": adjustments,
        "total_adjustment": final_score - _CAT["base"],
        "is_financial_sector": True,
        "coverage": cov.report(),
        "methodology_note": methodology_note
    }


def score_rentabilidad(
    roe: Optional[float],
    roa: Optional[float],
    operating_margin: Optional[float],
    net_margin: Optional[float],
    *,
    sector_roe_threshold: float,
    sector_roa_threshold: float,
    sector_roe_high: float,
    sector_roa_high: float,
    roic: Optional[float] = None,
    wacc: Optional[float] = None,
    archetype: Optional[str] = None,
    market: bool = False,
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
    T = _SC["rentabilidad"]
    base_score = _CAT["base"]
    _a = {}  # etapa 5: cobertura
    adjustments = []
    # Referencia de las bandas: el sector o, si el arquetipo lo contradice, el mercado.
    su, para, adj_ref = (("el mercado", "frente al mercado", "del mercado") if market
                         else ("su sector", "para su sector", "sectorial"))
    # Etapa 6 (FINANCIAL): sin margen operativo (no hay EBIT bancario) ni spread
    # ROIC−WACC (el WACC no es interpretable en un balance bancario).
    _na_opm, _na_spread = not_applicable(archetype, "operating_margin"), not_applicable(archetype, "roic_wacc")
    if _na_opm:
        operating_margin = None
    if _na_spread:
        wacc = None

    # ROE (peso alto: hasta ±6 pts) — bandas relativas al roe_high sectorial
    if roe is not None:
        p = T["roe_points"]
        if roe < 0 and roa is not None and roa > T["negative_equity_min_roa"]:
            # Negative book equity (e.g. from heavy buybacks: HD, MCD, SBUX,
            # ABBV) makes ROE negative even for very profitable companies — a
            # balance-sheet artifact, not value destruction. Don't apply the
            # harsh penalty; ROA and margins carry the real profitability signal.
            adj = 0
            sev = "ok"
            reason = f"ROE negativo por patrimonio negativo (recompras) — no penalizado; ROA {roa:.1%} sólido"
        elif roe >= sector_roe_high * T["roe_high_mult"]:
            adj = p[0]
            sev = "excellent"
            reason = f"Excepcional {para} ({roe:.1%} vs {sector_roe_high:.0%} rango alto {adj_ref})"
        elif roe >= sector_roe_high:
            adj = p[1]
            sev = "good"
            reason = f"Muy bueno ({roe:.1%}) - En el rango alto de {su}"
        elif roe >= sector_roe_threshold:
            adj = p[2]
            sev = "ok"
            reason = f"Bueno ({roe:.1%}) - Competitivo en {su}"
        elif roe >= T["roe_floor"]:
            adj = p[3]
            sev = "moderate"
            reason = f"Bajo ({roe:.1%}) - Por debajo de lo esperado"
        elif roe >= 0:
            adj = p[4]
            sev = "moderate"
            reason = f"Muy bajo ({roe:.1%}) - Poco eficiente con el capital"
        else:
            adj = p[5]
            sev = "severe"
            reason = f"Negativo ({roe:.1%}) - Destruye valor para accionistas"
        
        base_score += adj
        # ROE < 0 por patrimonio negativo (recompras): no significativo
        _a["roe"] = None if (roe < 0 and roa is not None and roa > T["negative_equity_min_roa"]) else adj
        adjustments.append({"metric": "ROE", "value": f"{roe:.1%}", "adjustment": adj, "reason": reason, "severity": sev})
    
    # ROA (hasta ±4 pts) — bandas relativas al roa_high sectorial
    if roa is not None:
        p = T["roa_points"]
        if roa >= sector_roa_high * T["roa_high_mult"]:
            adj = p[0]
            sev = "excellent"
            reason = f"Excelente {para} ({roa:.1%})"
        elif roa >= sector_roa_high:
            adj = p[1]
            sev = "good"
            reason = f"Bueno ({roa:.1%}) - Rango alto de {su}"
        elif roa >= sector_roa_threshold:
            adj = p[2]
            sev = "ok"
            reason = f"Aceptable ({roa:.1%}) - Normal para {su}"
        elif roa >= 0:
            adj = p[3]
            sev = "moderate"
            reason = f"Bajo ({roa:.1%}) - Activos poco productivos"
        else:
            adj = p[4]
            sev = "severe"
            reason = f"Negativo ({roa:.1%}) - Perdiendo dinero con sus activos"
        
        base_score += adj
        _a["roa"] = adj
        adjustments.append({"metric": "ROA", "value": f"{roa:.1%}", "adjustment": adj, "reason": reason, "severity": sev})
    
    # Operating Margin (hasta ±5 pts)
    if operating_margin is not None:
        b, p = T["operating_margin_bounds"], T["operating_margin_points"]
        if operating_margin >= b[0]:
            adj = p[0]
            sev = "excellent"
            reason = f"Excepcional ({operating_margin:.1%}) - Alto poder de fijación de precios"
        elif operating_margin >= b[1]:
            adj = p[1]
            sev = "good"
            reason = f"Muy bueno ({operating_margin:.1%}) - Operaciones eficientes"
        elif operating_margin >= b[2]:
            adj = p[2]
            sev = "ok"
            reason = f"Bueno ({operating_margin:.1%}) - Márgenes saludables"
        elif operating_margin >= b[3]:
            adj = p[3]
            sev = "moderate"
            reason = f"Ajustado ({operating_margin:.1%}) - Márgenes bajo presión"
        elif operating_margin >= 0:
            adj = p[4]
            sev = "moderate"
            reason = f"Bajo ({operating_margin:.1%}) - Costos erosionan ganancias"
        else:
            adj = p[5]
            sev = "severe"
            reason = f"Negativo ({operating_margin:.1%}) - Operaciones no rentables"
        
        base_score += adj
        _a["opm"] = adj
        adjustments.append({"metric": "Margen Operativo", "value": f"{operating_margin:.1%}", "adjustment": adj, "reason": reason, "severity": sev})
    
    # Net Margin (hasta ±3 pts)
    if net_margin is not None:
        b, p = T["net_margin_bounds"], T["net_margin_points"]
        if net_margin >= b[0]:
            adj = p[0]
            sev = "excellent"
            reason = f"Excelente ({net_margin:.1%}) - Alta rentabilidad final"
        elif net_margin >= b[1]:
            adj = p[1]
            sev = "good"
            reason = f"Bueno ({net_margin:.1%}) - Ganancias sólidas"
        elif net_margin >= b[2]:
            adj = p[2]
            sev = "ok"
            reason = f"Aceptable ({net_margin:.1%}) - Márgenes estándar"
        elif net_margin >= 0:
            adj = p[3]
            sev = "moderate"
            reason = f"Bajo ({net_margin:.1%}) - Poca ganancia por venta"
        else:
            adj = p[4]
            sev = "severe"
            reason = f"Negativo ({net_margin:.1%})"
        
        base_score += adj
        _a["nm"] = adj
        adjustments.append({"metric": "Margen Neto", "value": f"{net_margin:.1%}", "adjustment": adj, "reason": reason, "severity": sev})

    # ROIC - WACC spread (hasta ±3): ¿la empresa genera retornos por encima de su
    # costo de capital? Es el filtro de CREACIÓN DE VALOR económico que faltaba: el
    # ROE/ROA se miden contra umbrales absolutos, así una empresa con ROE alto puede
    # DESTRUIR valor si su WACC es mayor. Señal moderada para complementar (no
    # duplicar) el ROE. No aplica a financieras (se pasa wacc=None para ellas).
    if roic is not None and wacc is not None:
        spread = roic - wacc
        b, p = T["spread_bounds"], T["spread_points"]
        if spread >= b[0]:
            adj = p[0]; sev = "excellent"
            reason = f"Crea mucho valor (ROIC {roic:.1%} vs WACC {wacc:.1%}, spread +{spread:.1%})"
        elif spread >= b[1]:
            adj = p[1]; sev = "good"
            reason = f"Crea valor (ROIC {roic:.1%} > WACC {wacc:.1%}, spread +{spread:.1%})"
        elif spread >= b[2]:
            adj = p[2]; sev = "ok"
            reason = f"Retorno por encima del costo de capital (spread +{spread:.1%})"
        elif spread >= b[3]:
            adj = p[3]; sev = "moderate"
            reason = f"Retorno apenas por debajo del costo de capital (spread {spread:.1%})"
        else:
            adj = p[4]; sev = "severe"
            reason = f"Destruye valor (ROIC {roic:.1%} < WACC {wacc:.1%}, spread {spread:.1%})"
        base_score += adj
        _a["spread"] = adj
        adjustments.append({"metric": "ROIC vs WACC", "value": f"{spread:+.1%}", "adjustment": adj, "reason": reason, "severity": sev})

    cov = CategoryCoverage()
    cov.comp("ROE", T["roe_points"], _a.get("roe"))
    cov.comp("ROA", T["roa_points"], _a.get("roa"))
    cov.comp("Margen operativo", T["operating_margin_points"], _a.get("opm"), na=_na_opm)
    cov.comp("Margen neto", T["net_margin_points"], _a.get("nm"))
    if _na_spread:
        cov.comp("ROIC−WACC", T["spread_points"], None, na=_na_spread)
    elif wacc is not None:  # sin WACC estimado no hay spread que evaluar
        cov.comp("ROIC−WACC", T["spread_points"], _a.get("spread"))
    base_score = cov.apply(base_score, adjustments)
    final_score = max(_CAT["min"], min(_CAT["max"], base_score))

    return {
        "category": "Rentabilidad",
        "emoji": "💰",
        "score": final_score,
        "max_score": _CAT["max"],
        "base": _CAT["base"],
        "adjustments": adjustments,
        "total_adjustment": final_score - _CAT["base"],
        "coverage": cov.report(),
    }


def block_max(members: int) -> int:
    """Máximo del bloque según sus miembros: ±2 con 1, ±4 con 2, ±6 con 3 o más (config)."""
    m = cfg("thresholds.score.valoracion.multiples_block_max_by_members")
    return m[max(1, min(members, len(m))) - 1] if members else m[0]


def multiples_block(members: Dict[str, Any], label: str, missing: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    """Bloque de múltiplos correlacionados (etapa 9a): promedio de los ajustes
    normalizados de los miembros con dato (positivo / máximo, negativo / |mínimo|),
    escalado a block_max(n) y redondeado (mitades lejos de cero).
    members = {nombre: (ajuste, puntos)}. None si ningún miembro tiene dato."""
    if not members:
        return None
    T = _SC["valoracion"]
    norm = {k: (a / max(pts) if a > 0 else (a / abs(min(pts)) if a < 0 else 0.0)) for k, (a, pts) in members.items()}
    mean_ = sum(norm.values()) / len(norm)
    bmax = block_max(len(norm))
    raw = mean_ * bmax
    block = int(math.floor(abs(raw) + 0.5)) * (1 if raw >= 0 else -1)
    bs = T["multiples_block_strong"]
    sev = ("excellent" if mean_ >= bs else "good" if mean_ > 0 else "ok" if mean_ == 0
           else "severe" if mean_ <= -bs else "moderate")
    n = len(norm)
    adj = {"metric": label, "value": f"{n} múltiplo{'s' if n != 1 else ''}", "adjustment": block, "severity": sev,
           "block_mean": mean_, "block_members": list(norm), "block_max": bmax,
           "reason": (f"promedio de los ajustes reescalados a ±1 ({', '.join(f'{k} {v:+.2f}' for k, v in norm.items())}) "
                      f"= {mean_:+.2f} × {bmax} (máximo con {n} miembro{'s' if n != 1 else ''}) = {raw:+.1f}"
                      + (f"; sin dato: {', '.join(missing)}" if missing else ""))}
    return {"block": block, "raw": raw, "mean": mean_, "max": bmax, "adjustment": adj}


def score_valoracion(
    pe: Optional[float],
    p_fcf: Optional[float],
    ev_ebitda: Optional[float],
    peg: Optional[float],
    sector_pe: Optional[float] = None,
    sector_ev_ebitda: Optional[float] = None,
    fcf_yield: Optional[float] = None,
    benchmark_profile: Optional[str] = None,
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
    p_ffo: Optional[float] = None,
    # Etapa 6: rama por arquetipo y sus métricas (lib/archetype_metrics.py)
    archetype: Optional[str] = None,
    xv: Optional[Dict[str, Any]] = None,
    # Etapa 8: el DCF como componente acotado por su fiabilidad
    dcf: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Categoría 3: Valoración (20 pts máximo)

    Etapa 8: el DCF es un componente con aporte acotado por su fiabilidad (±4
    alta, ±2 media, 0 baja), fuera del rescate de growth: el rescate limita las
    penalizaciones de los múltiplos, no la del DCF (fallo 1 del spec: el DCF no
    restaba nada al score).
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
    T = _SC["valoracion"]
    base_score = _CAT["base"]
    adjustments = []
    _a = {}  # etapa 5: cobertura (componentes nucleares; bonos y rescates aparte)
    _blk: Dict[str, Any] = {}  # etapa 9a: miembros del bloque de múltiplos -> (ajuste, puntos)
    _pb_blk: Dict[str, Any] = {}  # FINANCIAL: bloque P/B y P/TBV frente a sus justificados
    _pb_block_adj = _pb_block_max = None
    # Etapa 6: el arquetipo decide qué múltiplos aplican y cuáles se normalizan.
    xv = xv or {}
    if archetype is not None:
        is_reit = archetype == REIT
    _na = {k: not_applicable(archetype, k) for k in ("pe", "peg", "forward_pe", "p_fcf", "ev_ebitda", "garp")}
    if archetype == GROWTH_PRE_PROFIT and xv.get("ebitda") is not None and xv["ebitda"] <= 0:
        # Sin EBITDA positivo el múltiplo no existe: no aplica (no es un dato ausente).
        _na["ev_ebitda"] = "No aplica a GROWTH_PRE_PROFIT: EBITDA <= 0, sin resultado operativo que capitalizar"
    _cyc = archetype == CYCLICAL
    _cyc_note = (f" (ciclo incompleto: {xv.get('cycle_years')} ejercicios)" if _cyc and xv.get("cycle_incomplete")
                 else "")
    if _cyc:
        # CYCLICAL: EV/EBITDA y P/FCF sobre EBITDA y FCF normalizados (promedio de
        # los ejercicios disponibles), no sobre un solo año de la fase del ciclo.
        ev_ebitda = xv.get("ev_ebitda_normalized")
        p_fcf = xv.get("p_fcf_normalized")

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
    # company_type y growth_quality_score son informativos (perfil de la empresa):
    # desde la etapa 9a no modifican el atractivo del precio.


    # ─── REIT: P/FFO en lugar de P/E y P/FCF (hasta ±4 pts) ────
    # El beneficio neto de un REIT está deprimido por la depreciación de
    # inmuebles (no-cash) y su FCF por el capex de cartera: P/E y P/FCF son
    # métricas engañosas para el sector. El estándar es P/FFO.
    if is_reit:
        if p_ffo is not None and p_ffo > 0:
            b, p = T["reit_pffo_bounds"], T["reit_pffo_points"]
            if p_ffo <= b[0]:
                adj = p[0]; sev = "excellent"
                reason = f"Barato por FFO ({p_ffo:.1f}x)"
            elif p_ffo <= b[1]:
                adj = p[1]; sev = "good"
                reason = f"Atractivo por FFO ({p_ffo:.1f}x)"
            elif p_ffo <= b[2]:
                adj = p[2]; sev = "ok"
                reason = f"En línea ({p_ffo:.1f}x FFO)"
            elif p_ffo <= b[3]:
                adj = p[3]; sev = "moderate"
                reason = f"Caro por FFO ({p_ffo:.1f}x)"
            else:
                adj = p[4]; sev = "severe"
                reason = f"Muy caro por FFO ({p_ffo:.1f}x)"
            base_score += adj
            _a["pffo"] = adj
            adjustments.append({"metric": "P/FFO (REIT)", "value": f"{p_ffo:.1f}x", "adjustment": adj, "reason": reason, "severity": sev})
        # Etapa 9a: la rentabilidad por dividendo del REIT puntúa en Crecimiento, dentro
        # del retorno total (dividendo + FFO por acción), no aquí: no se cuenta dos veces.

    # ─── FINANCIAL: P/B y P/TBV frente a los justificados por su retorno ────
    if archetype == FINANCIAL:
        b, p = T["financial_pb_ratio_bounds"], T["financial_pb_points"]
        for key, label, ret_lbl, mult, just, ratio in (
                ("pb", "P/B frente a ROE", "ROE", xv.get("pb"), xv.get("pb_justified"), xv.get("pb_ratio")),
                ("ptbv", "P/TBV frente a ROTE", "ROTE", xv.get("ptbv"), xv.get("ptbv_justified"), xv.get("ptbv_ratio"))):
            if ratio is None:
                continue
            if ratio <= b[0]:
                adj, sev, tag = p[0], "excellent", "Barato"
            elif ratio <= b[1]:
                adj, sev, tag = p[1], "good", "Atractivo"
            elif ratio <= b[2]:
                adj, sev, tag = p[2], "ok", "En línea"
            elif ratio <= b[3]:
                adj, sev, tag = p[3], "moderate", "Prima"
            else:
                adj, sev, tag = p[4], "severe", "Caro"
            reason = (f"{tag}: {mult:.2f}x frente a {just:.2f}x justificado por su {ret_lbl} "
                      f"(Ke {xv.get('cost_of_equity', 0):.1%} con β ajustada {xv.get('beta_adjusted', 0):.2f}, "
                      f"g {xv.get('terminal_growth', 0):.1%})")
            _a[key] = adj
            _pb_blk[label] = (adj, p)
            adjustments.append({"metric": label, "value": f"{ratio:.2f}× justificado", "adjustment": adj,
                                "reason": reason, "severity": sev, "in_block": True})
        # Etapa 9a: P/B y P/TBV frente a sus justificados miden lo mismo: un bloque.
        _pbres = multiples_block(_pb_blk, "Bloque P/B y P/TBV")
        if _pbres:
            adjustments.append(_pbres["adjustment"])
            base_score += _pbres["block"]
            _pb_block_adj, _pb_block_max = _pbres["block"], _pbres["max"]

    # ─── GROWTH_PRE_PROFIT: EV/Ventas y regla de 40 ────
    if archetype == GROWTH_PRE_PROFIT:
        evs, r40 = xv.get("ev_sales"), xv.get("rule_of_40")
        if evs is not None:
            b, p = T["ev_sales_bounds"], T["ev_sales_points"]
            i = next((k for k, x in enumerate(b) if evs <= x), len(b))
            adj = p[i]
            sev = ("excellent", "good", "ok", "moderate", "severe")[i]
            reason = ("Barato", "Atractivo", "En línea", "Exigente", "Muy caro")[i] + f" por ventas ({evs:.1f}x)"
            base_score += adj
            _a["evs"] = adj
            adjustments.append({"metric": "EV/Ventas", "value": f"{evs:.1f}x", "adjustment": adj,
                                "reason": reason, "severity": sev})
        if r40 is not None:
            b, p = T["rule_of_40_bounds"], T["rule_of_40_points"]
            i = next((k for k, x in enumerate(b) if r40 >= x), len(b))
            adj = p[i]
            sev = ("excellent", "good", "ok", "moderate", "severe")[i]
            reason = (f"Crecimiento {xv.get('revenue_cagr_3y', 0):.1%} (CAGR 3 años) + margen FCF "
                      f"{xv.get('fcf_margin', 0):.1%} = {r40 * 100:.0f}")
            base_score += adj
            _a["r40"] = adj
            adjustments.append({"metric": "Regla de 40", "value": f"{r40 * 100:.0f}", "adjustment": adj,
                                "reason": reason, "severity": sev})

    # ─── P/E vs Sector (hasta ±5 pts) — si aplica al arquetipo ─────
    if not _na["pe"] and not is_reit and pe is not None and pe > 0:
        pe_threshold = sector_pe if sector_pe and sector_pe > 0 else _BENCH_FALLBACK["pe"]
        # Benchmark del mercado amplio cuando el arquetipo contradice al sector (main._select_benchmark).
        _vs = " mercado" if benchmark_profile == "market" else ""

        # Etapa 9a: una sola banda por arquetipo. Sin bandas "growth" más tolerantes ni
        # atenuación por calidad del crecimiento: el crecimiento entra al precio una sola
        # vez, vía PEG y DCF.
        m, p = T["pe_value_mults"], T["pe_value_points"]
        if pe <= pe_threshold * m[0]:
            adj = p[0]; sev = "excellent"
            reason = f"Muy barato ({pe:.1f}x vs {pe_threshold:.1f}x{_vs or ' sector'})"
        elif pe <= pe_threshold * m[1]:
            adj = p[1]; sev = "good"
            reason = f"Atractivo ({pe:.1f}x)"
        elif pe <= pe_threshold * m[2]:
            adj = p[2]; sev = "ok"
            reason = f"En línea ({pe:.1f}x vs {pe_threshold:.1f}x{_vs})"
        elif pe <= pe_threshold * m[3]:
            adj = p[3]; sev = "moderate"
            reason = f"Premium ({pe:.1f}x vs {pe_threshold:.1f}x{_vs})"
        else:
            adj = p[4]; sev = "severe"
            reason = f"Muy caro ({pe:.1f}x vs {pe_threshold:.1f}x{_vs})"

        _a["pe"] = adj
        _blk["P/E"] = (adj, T["pe_value_points"])
        adjustments.append({"metric": "P/E vs Sector", "value": f"{pe:.1f}x", "adjustment": adj, "reason": reason,
                            "severity": sev, "in_block": True})

    # ─── Forward P/E (miembro del bloque de múltiplos) ────────────────
    if not _na["forward_pe"] and forward_pe is not None and forward_pe > 0 and pe is not None and pe > 0:
        pe_compression = (pe - forward_pe) / pe  # % de "mejora" esperada
        b, p = T["forward_compression_bounds"], T["forward_compression_points"]
        if pe_compression >= b[0]:  # Forward P/E 25%+ menor que trailing
            adj, sev = p[0], "excellent"
            reason = f"Fuerte compresión P/E ({pe:.0f}x → {forward_pe:.0f}x forward)"
        elif pe_compression >= b[1]:
            adj, sev = p[1], "good"
            reason = f"P/E mejorando ({pe:.0f}x → {forward_pe:.0f}x forward)"
        elif pe_compression >= b[2]:
            adj, sev = p[2], "good"
            reason = f"P/E estable a mejor ({pe:.0f}x → {forward_pe:.0f}x)"
        else:
            # Etapa 9a: con dato y sin compresión cuenta como 0 en el promedio del bloque.
            adj, sev = 0, "ok"
            reason = f"Sin compresión del P/E ({pe:.0f}x → {forward_pe:.0f}x forward)"
        _blk["Forward P/E"] = (adj, [*p, 0])
        adjustments.append({"metric": "Forward P/E", "value": f"{forward_pe:.1f}x", "adjustment": adj,
                            "reason": reason, "severity": sev, "in_block": True})

    # ─── P/FCF (hasta ±4 pts) — omitido para REITs (capex de cartera) ──
    if not _na["p_fcf"] and not is_reit and p_fcf is not None and p_fcf > 0:
        # Etapa 9a: bandas de valor únicamente (ver P/E).
        b, p = T["pfcf_value_bounds"], T["pfcf_value_points"]
        if p_fcf <= b[0]:
            adj = p[0]; sev = "excellent"
            reason = f"Muy atractivo ({p_fcf:.1f}x)"
        elif p_fcf <= b[1]:
            adj = p[1]; sev = "good"
            reason = f"Bueno ({p_fcf:.1f}x)"
        elif p_fcf <= b[2]:
            adj = p[2]; sev = "ok"
            reason = f"Aceptable ({p_fcf:.1f}x)"
        elif p_fcf <= b[3]:
            adj = p[3]; sev = "moderate"
            reason = f"Elevado ({p_fcf:.1f}x)"
        else:
            adj = p[4]; sev = "severe"
            reason = f"Muy alto ({p_fcf:.1f}x)"

        _a["pfcf"] = adj
        _blk["P/FCF"] = (adj, T["pfcf_value_points"])
        adjustments.append({"metric": "P/FCF normalizado" if _cyc else "P/FCF", "value": f"{p_fcf:.1f}x",
                            "adjustment": adj, "reason": reason + _cyc_note, "severity": sev, "in_block": True})

    # ─── EV/EBITDA vs Sector (hasta ±4 pts) ────────────
    if not _na["ev_ebitda"] and ev_ebitda is not None and ev_ebitda > 0:
        ev_threshold = sector_ev_ebitda if sector_ev_ebitda and sector_ev_ebitda > 0 else _BENCH_FALLBACK["ev_ebitda"]
        _vs = " mercado" if benchmark_profile == "market" else ""

        # Etapa 9a: bandas de valor únicamente (ver P/E).
        m, p = T["ev_ebitda_value_mults"], T["ev_ebitda_value_points"]
        if ev_ebitda <= ev_threshold * m[0]:
            adj = p[0]; sev = "excellent"
            reason = f"Muy barato ({ev_ebitda:.1f}x vs {ev_threshold:.1f}x{_vs})"
        elif ev_ebitda <= ev_threshold:
            adj = p[1]; sev = "good"
            reason = f"Atractivo ({ev_ebitda:.1f}x)"
        elif ev_ebitda <= ev_threshold * m[1]:
            adj = p[2]; sev = "ok"
            reason = f"En línea ({ev_ebitda:.1f}x)"
        elif ev_ebitda <= ev_threshold * m[2]:
            adj = p[3]; sev = "moderate"
            reason = f"Premium ({ev_ebitda:.1f}x vs {ev_threshold:.1f}x{_vs})"
        else:
            adj = p[4]; sev = "severe"
            reason = f"Muy caro ({ev_ebitda:.1f}x vs {ev_threshold:.1f}x{_vs})"

        _a["ev"] = adj
        _blk["EV/EBITDA"] = (adj, T["ev_ebitda_value_points"])
        adjustments.append({"metric": "EV/EBITDA normalizado vs Sector" if _cyc else "EV/EBITDA vs Sector",
                            "value": f"{ev_ebitda:.1f}x", "adjustment": adj, "reason": reason + _cyc_note,
                            "severity": sev, "in_block": True})

    # ─── PEG Ratio (hasta ±4 pts) ─────────────────────
    if not _na["peg"] and peg is not None and peg > 0:
        b, p = T["peg_bounds"], T["peg_points"]
        if peg <= b[0]:
            adj = p[0]; sev = "excellent"
            reason = f"Muy atractivo ({peg:.2f})"
        elif peg <= b[1]:
            adj = p[1]; sev = "good"
            reason = f"Bueno ({peg:.2f})"
        elif peg <= b[2]:
            adj = p[2]; sev = "ok"
            reason = f"Razonable ({peg:.2f})"
        elif peg <= b[3]:
            adj = p[3]; sev = "moderate"
            reason = f"Caro para su crecimiento ({peg:.2f})"
        else:
            adj = p[4]; sev = "severe"  # v2.4: max -3 en vez de -4
            reason = f"Muy caro ({peg:.2f})"

        _a["peg"] = adj
        _blk["PEG"] = (adj, T["peg_points"])
        adjustments.append({"metric": "PEG Ratio", "value": f"{peg:.2f}", "adjustment": adj, "reason": reason,
                            "severity": sev, "in_block": True})

    # ─── Bloque de múltiplos correlacionados (etapa 9a) ─────
    # P/E, Forward P/E, P/FCF, EV/EBITDA y PEG miden lo mismo (precio frente a
    # beneficio o caja): sumarlos contaba varias veces una sola señal.
    _missing_blk = [k for k in T["multiples_block"] if k not in _blk
                    and not _na.get({"P/E": "pe", "Forward P/E": "forward_pe", "P/FCF": "p_fcf",
                                     "EV/EBITDA": "ev_ebitda", "PEG": "peg"}[k])]
    _bres = multiples_block(_blk, "Bloque de múltiplos", _missing_blk)
    _block_raw = _block_adj = _bmax_used = None
    if _bres:
        adjustments.append(_bres["adjustment"])
        base_score += _bres["block"]
        _block_raw, _block_adj, _bmax_used = _bres["raw"], _bres["block"], _bres["max"]

    # ─── De-dup de valoración (Fase B) ─────────────────
    # Se eliminaron los bonos separados de "FCF Yield" (+3) y "Earnings Yield"
    # (+2): fcf_yield = 1/p_fcf y earnings_yield = 1/pe, así que premiaban el
    # MISMO hecho ("barato por FCF" / "barato por ganancias") que las bandas de
    # P/FCF (±4) y P/E ya puntúan arriba -> doble conteo que inflaba valoración
    # a las value stocks. Las bandas de P/FCF y P/E quedan como señal primaria.
    # (fcf_yield/earnings_yield siguen usándose para alertas y ajuste de growth,
    # no para un bonus redundante de valoración.)

    # Etapa 9a: el bono GARP, el de Growth Quality y el rescate de penalizaciones
    # para growth se construían con métricas de calidad (crecimiento, ROE/ROIC,
    # márgenes): ya no puntúan en el atractivo del precio. La calidad del
    # crecimiento se mide en Calidad del negocio (Crecimiento y Rentabilidad).

    # ─── DCF (etapa 8): ±4 alta, ±2 media, 0 baja ─────
    _dcf = dcf or {}
    _dcf_adj, _dcf_reason = None, None
    if not _dcf.get("na") and _dcf.get("upside") is not None and _dcf.get("reliability"):
        up, rel = _dcf["upside"], _dcf["reliability"]
        b = T["dcf_upside_bounds"]
        i = next((k for k, x in enumerate(b) if up >= x), len(b))
        tag = ("Claramente barata", "Barata", "En precio", "Cara", "Claramente cara")[i]
        if rel == "baja":
            adj, sev = 0, "neutral"
            reason = ("El DCF no concilia con el precio bajo ningún supuesto razonable; no se usa en el score"
                      if _dcf.get("grid_contains_price") is False else
                      "DCF de fiabilidad baja: no se usa en el score")
        else:
            adj = (T["dcf_points_high"] if rel == "alta" else T["dcf_points_medium"])[i]
            sev = ("excellent", "good", "ok", "moderate", "severe")[i]
            reason = f"{tag} por DCF (fiabilidad {rel})"
        base_score += adj
        _dcf_adj = adj
        adjustments.append({"metric": "DCF (upside)", "value": f"{up:+.0%}", "adjustment": adj,
                            "reason": reason + (": " + "; ".join(_dcf.get("reasons") or []) if _dcf.get("reasons") else ""),
                            "severity": sev, "reliability": rel})
    elif not _dcf.get("na"):
        _dcf_reason = _dcf.get("missing_reason") or "sin DCF"

    # Componentes aplicables: múltiplos <= 0 cuentan como sin dato (no significativos).
    cov = CategoryCoverage()
    if archetype == FINANCIAL:
        cov.comp("P/B frente a ROE", T["financial_pb_points"], _a.get("pb"), rescale=False)
        cov.comp("P/TBV frente a ROTE", T["financial_pb_points"], _a.get("ptbv"), rescale=False)
        _pbm = _pb_block_max or block_max(len([n for n, *_ in cov.items if n.startswith(("P/B", "P/TBV"))]))
        cov.derived_comp("Bloque P/B y P/TBV", [_pbm, -_pbm], _pb_block_adj)
    if is_reit:
        cov.comp("P/FFO", T["reit_pffo_points"], _a.get("pffo"))
    if archetype == GROWTH_PRE_PROFIT:
        cov.comp("EV/Ventas", T["ev_sales_points"], _a.get("evs"))
        cov.comp("Regla de 40", T["rule_of_40_points"], _a.get("r40"))
    # Miembros del bloque: cuentan en la cobertura, pero se reescala el bloque, no cada uno.
    if is_reit and archetype is None:
        pass  # llamada antigua sin arquetipo: P/E y P/FCF omitidos para REIT
    else:
        cov.comp("P/E", T["pe_value_points"], _a.get("pe"), na=_na["pe"], rescale=False)
        cov.comp("P/FCF", T["pfcf_value_points"], _a.get("pfcf"), na=_na["p_fcf"], rescale=False)
    cov.comp("EV/EBITDA", T["ev_ebitda_value_points"], _a.get("ev"),
             na=_na["ev_ebitda"], rescale=False)
    cov.comp("PEG", T["peg_points"], _a.get("peg"), na=_na["peg"], rescale=False)
    # Rango del bloque en el reescalado: el de sus miembros con dato (o el de los
    # aplicables si ninguno tiene dato).
    _n_app = len([n for n, *_ in cov.items if n in ("P/E", "P/FCF", "EV/EBITDA", "PEG")])
    _bm = _bmax_used or block_max(_n_app)
    if _n_app:
        cov.derived_comp("Bloque de múltiplos", [_bm, -_bm], _block_adj)
    if dcf is not None:
        cov.comp("DCF", T["dcf_points_high"], _dcf_adj, _dcf_reason, na=_dcf.get("na"))
    from valuation_confidence import multiples_signal
    # Señal de los múltiplos para la convergencia: el bloque (sin redondear) cuenta
    # como un solo múltiplo, junto a los de la rama (P/FFO, EV/Ventas, P/B…).
    _mult_signal = multiples_signal(
        [it for it in cov.items if it[0] not in cov.unscaled]
        + ([("Bloque de múltiplos", _bm, -_bm, _block_raw)] if _block_raw is not None else []))
    base_score = cov.apply(base_score, adjustments)
    final_score = max(_CAT["min"], min(_CAT["max"], base_score))

    return {
        "category": "Valoración",
        "emoji": "💵",
        "score": final_score,
        "max_score": _CAT["max"],
        "base": _CAT["base"],
        "adjustments": adjustments,
        "total_adjustment": final_score - _CAT["base"],
        "coverage": cov.report(),
        "company_type": company_type,
        "growth_quality_score": growth_quality_score,
        "growth_quality_label": growth_quality["label"],
        "multiples_signal": _mult_signal,
    }


def _banded(value: float, bounds, points, labels, higher: bool = True):
    """Tramo de `value` en bandas descendentes (higher=True: ≥ bounds[i]). (ajuste, severidad, etiqueta)."""
    i = next((k for k, b in enumerate(bounds) if (value >= b if higher else value <= b)), len(bounds))
    return points[i], ("excellent", "good", "ok", "moderate", "severe")[i], labels[i]


def _rentabilidad_branch(archetype: str, comps: List[Any], na_keys) -> Dict[str, Any]:
    """Rentabilidad por rama (etapa 9a): comps = [(nombre, puntos, valor, ajuste, motivo, fmt, sin_dato)]."""
    base_score = _CAT["base"]
    adjustments = []
    cov = CategoryCoverage()
    for name, pts, value, adj, reason, fmt, missing_reason in comps:
        if adj is not None:
            base_score += adj
            adjustments.append({"metric": name, "value": fmt.format(value), "adjustment": adj, "reason": reason,
                                "severity": _banded_sev(adj, pts)})
        cov.comp(name, pts, adj, missing_reason)
    for key, label in na_keys:
        cov.comp(label, [0], None, na=not_applicable(archetype, key))
    base_score = cov.apply(base_score, adjustments)
    final_score = max(_CAT["min"], min(_CAT["max"], base_score))
    return {"category": "Rentabilidad", "emoji": "💰", "score": final_score, "max_score": _CAT["max"],
            "base": _CAT["base"], "adjustments": adjustments, "total_adjustment": final_score - _CAT["base"],
            "coverage": cov.report()}


def _banded_sev(adj, pts):
    i = list(pts).index(adj) if adj in pts else 2
    return ("excellent", "good", "ok", "moderate", "severe")[min(i, 4)]


_RENT_NA_COMMON = (("roe", "ROE"), ("roa", "ROA"), ("net_margin", "Margen neto"), ("roic_wacc", "ROIC−WACC"))


def score_rentabilidad_reit(xv: Dict[str, Any]) -> Dict[str, Any]:
    """REIT (etapa 9a): rentabilidad sobre el FFO. ROE, ROA, margen neto y ROIC−WACC
    (sobre el beneficio neto, deprimido por la depreciación) y los márgenes bruto y
    operativo (arrendamiento neto) no aplican."""
    T = _SC["rentabilidad"]
    comps = []
    for name, key, b, p, labels in (
            ("FFO / patrimonio", "ffo_to_equity", T["reit_ffo_equity_bounds"], T["reit_ffo_equity_points"],
             ("Excelente", "Alto", "En línea", "Bajo", "Muy bajo")),
            ("Margen FFO", "ffo_margin", T["reit_ffo_margin_bounds"], T["reit_ffo_margin_points"],
             ("Excelente", "Alto", "En línea", "Bajo", "Muy bajo"))):
        v = xv.get(key)
        if v is None:
            comps.append((name, p, None, None, None, "{}", "sin FFO, patrimonio o ingresos"))
            continue
        adj, _, lab = _banded(v, b, p, labels)
        what = "retorno del FFO sobre el patrimonio contable" if key == "ffo_to_equity" else "FFO sobre ingresos"
        comps.append((name, p, v, adj, f"{lab} ({v:.1%}) - {what}", "{:.1%}", None))
    return _rentabilidad_branch(REIT, comps, _RENT_NA_COMMON + (("gross_margin", "Margen bruto"),
                                                               ("operating_margin", "Margen operativo")))


def score_rentabilidad_growth(xv: Dict[str, Any], gross_margin: Optional[float]) -> Dict[str, Any]:
    """GROWTH_PRE_PROFIT (etapa 9a): margen bruto, mejora interanual del margen
    operativo y margen FCF. ROE, ROA, margen neto, ROIC−WACC y el nivel del margen
    operativo son negativos por definición del arquetipo: no aplican."""
    T = _SC["rentabilidad"]
    comps = []
    gm = gross_margin if gross_margin is not None else xv.get("gross_margin")
    if gm is None:
        comps.append(("Margen bruto", T["gpp_gross_margin_points"], None, None, None, "{}", "sin margen bruto"))
    else:
        adj, _, lab = _banded(gm, T["gpp_gross_margin_bounds"], T["gpp_gross_margin_points"],
                              ("Excelente", "Alto", "En línea", "Bajo", "Muy bajo"))
        comps.append(("Margen bruto", T["gpp_gross_margin_points"], gm, adj,
                      f"{lab} ({gm:.1%}) - margen que financiará la escala", "{:.1%}", None))
    ch = xv.get("operating_margin_change")
    if ch is None:
        comps.append(("Mejora del margen operativo", T["gpp_opm_change_points"], None, None, None, "{}",
                      xv.get("operating_margin_change_reason") or "sin margen operativo de dos ejercicios"))
    else:
        adj, _, lab = _banded(ch, T["gpp_opm_change_bounds"], T["gpp_opm_change_points"],
                              ("Fuerte mejora", "Mejora", "Estable", "Empeora", "Fuerte deterioro"))
        comps.append(("Mejora del margen operativo", T["gpp_opm_change_points"], ch * 100, adj,
                      f"{lab} ({ch * 100:+.1f} pp interanual: {xv.get('operating_margin_fy_prior', 0):.1%} → "
                      f"{xv.get('operating_margin_fy', 0):.1%})", "{:+.1f} pp", None))
    fm = xv.get("fcf_margin")
    if fm is None:
        comps.append(("Margen FCF", T["gpp_fcf_margin_points"], None, None, None, "{}", "sin FCF o ingresos"))
    else:
        adj, _, lab = _banded(fm, T["gpp_fcf_margin_bounds"], T["gpp_fcf_margin_points"],
                              ("Excelente", "Alto", "Equilibrio", "Quema moderada", "Quema alta"))
        comps.append(("Margen FCF", T["gpp_fcf_margin_points"], fm, adj, f"{lab} ({fm:.1%}) - FCF sobre ingresos",
                      "{:.1%}", None))
    return _rentabilidad_branch(GROWTH_PRE_PROFIT, comps, _RENT_NA_COMMON + (("operating_margin", "Margen operativo"),))


def score_calidad_ganancias(
    f_score: Optional[int],
    fcf: Optional[float],
    ocf: Optional[float],
    net_income: Optional[float],
    fcf_to_net_income: Optional[float],
    earnings_consistency: Optional[float] = None,
    archetype: Optional[str] = None,
    xv: Optional[Dict[str, Any]] = None,
    ffo_payout: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Categoría 4: Calidad de Ganancias (20 pts máximo)
    Base: 10 pts

    Etapa 6: FINANCIAL sustituye Piotroski, OCF, FCF y FCF/BN (no aplican) por
    estabilidad del ROE, eficiencia aproximada y crecimiento del valor en libros;
    REIT sustituye Piotroski y FCF/BN por el payout sobre FFO.
    """
    T = _SC["calidad"]
    base_score = _CAT["base"]
    _a = {}  # etapa 5: cobertura
    adjustments = []
    xv = xv or {}
    _na = {k: not_applicable(archetype, k) for k in ("piotroski", "ocf", "fcf", "fcf_to_ni")}
    if _na["piotroski"]:
        f_score = None
    if _na["ocf"]:
        ocf = None
    if _na["fcf"]:
        fcf = None
    if _na["fcf_to_ni"]:
        fcf_to_net_income = None

    def _band(key, label, value, value_txt, bounds, points, higher_better, texts):
        nonlocal base_score
        if value is None:
            return
        i = next((k for k, x in enumerate(bounds) if (value >= x if higher_better else value <= x)), len(bounds))
        adj = points[i]
        base_score += adj
        _a[key] = adj
        adjustments.append({"metric": label, "value": value_txt, "adjustment": adj, "reason": texts[i],
                            "severity": ("excellent", "good", "moderate", "severe")[i]})

    if archetype == FINANCIAL:
        sd = xv.get("roe_std")
        _band("roe_std", "Estabilidad del ROE", sd, None if sd is None else f"σ {sd * 100:.1f} pp",
              T["financial_roe_std_bounds"], T["financial_roe_std_points"], False,
              [f"ROE muy estable ({xv.get('roe_years')} ejercicios)", "ROE estable", "ROE algo volátil",
               "ROE volátil: beneficio poco recurrente"])
        ef = xv.get("efficiency_ratio")
        _band("efficiency", "Eficiencia (aprox.)", ef, None if ef is None else f"{ef:.1%}",
              T["financial_efficiency_bounds"], T["financial_efficiency_points"], False,
              ["Muy eficiente (gastos no financieros / ingresos)", "Eficiente", "Eficiencia mejorable",
               "Ineficiente: gastos altos sobre ingresos"])
        bv = xv.get("book_value_cagr_3y")
        _bv_lbl = "tangible" if xv.get("book_value_basis") == "tangible" else "contable"
        _band("bv_growth", "Crecimiento del valor en libros", growth_for_bands(bv), None if bv is None else f"{bv:.1%}",
              T["financial_bv_growth_bounds"], T["financial_bv_growth_points"], True,
              [f"Valor en libros {_bv_lbl} creciendo con fuerza (CAGR 3 años)", f"Valor en libros {_bv_lbl} creciendo",
               f"Valor en libros {_bv_lbl} casi plano", f"Valor en libros {_bv_lbl} decreciente"])
    if archetype == REIT:
        _band("ffo_payout", "Payout sobre FFO", ffo_payout, None if ffo_payout is None else f"{ffo_payout:.0%}",
              T["reit_ffo_payout_bounds"], T["reit_ffo_payout_points"], False,
              ["Dividendo holgadamente cubierto por el FFO", "Dividendo cubierto por el FFO",
               "Dividendo justo frente al FFO", "Dividendo por encima de lo que genera el FFO"])
    
    # Piotroski F-Score (peso alto: hasta ±7 pts)
    if f_score is not None:
        # Piotroski escalado a base 9 cuando se evaluaron 7-8 criterios (etapa 5).
        _fs = f_score if isinstance(f_score, int) else f"{f_score:.1f}"
        b, p = _PIOTROSKI["bands"], T["fscore_points"]
        if f_score >= b[0]:
            adj = p[0]
            sev = "excellent"
            reason = f"Fortaleza excepcional ({_fs}/9)"
        elif f_score >= b[1]:
            adj = p[1]
            sev = "good"
            reason = f"Buena salud ({_fs}/9)"
        elif f_score >= b[2]:
            adj = p[2]
            sev = "ok"
            reason = f"Neutral ({_fs}/9)"
        elif f_score >= b[3]:
            adj = p[3]
            sev = "moderate"
            reason = f"Debilidad ({_fs}/9)"
        else:
            adj = p[4]
            sev = "severe"
            reason = f"Señales de deterioro ({_fs}/9)"
        
        base_score += adj
        _a["fscore"] = adj
        adjustments.append({"metric": "Piotroski F-Score", "value": f"{_fs}/9", "adjustment": adj, "reason": reason, "severity": sev})
    
    # Operating Cash Flow (hasta ±4 pts)
    if ocf is not None:
        if ocf > 0:
            adj = T["ocf_points"][0]
            sev = "good"
            reason = "Genera efectivo operativo"
        else:
            adj = T["ocf_points"][1]
            sev = "severe"
            reason = "Quema efectivo operativo"
        
        base_score += adj
        _a["ocf"] = adj
        adjustments.append({"metric": "Cash Flow Operativo", "value": "Positivo" if ocf > 0 else "Negativo", "adjustment": adj, "reason": reason, "severity": sev})
    
    # FCF (hasta ±4 pts)
    if fcf is not None:
        if fcf > 0:
            adj = T["fcf_points"][0]
            sev = "good"
            reason = "FCF positivo"
        else:
            adj = T["fcf_points"][1]
            sev = "severe"
            reason = "FCF negativo"
        
        base_score += adj
        _a["fcf"] = adj
        adjustments.append({"metric": "Free Cash Flow", "value": "Positivo" if fcf > 0 else "Negativo", "adjustment": adj, "reason": reason, "severity": sev})
    
    # Calidad FCF vs Net Income (hasta ±3 pts)
    if fcf_to_net_income is not None and net_income is not None and net_income > 0:
        b, p = T["fcf_to_ni_bounds"], T["fcf_to_ni_points"]
        if fcf_to_net_income >= b[0]:
            adj = p[0]
            sev = "excellent"
            reason = f"FCF > Net Income ({fcf_to_net_income:.1%})"
        elif fcf_to_net_income >= b[1]:
            adj = p[1]
            sev = "good"
            reason = f"FCF sólido vs ganancias ({fcf_to_net_income:.1%})"
        elif fcf_to_net_income >= b[2]:
            adj = p[2]
            sev = "ok"
            reason = f"FCF aceptable ({fcf_to_net_income:.1%})"
        else:
            adj = p[3]
            sev = "moderate"
            reason = f"Ganancias sin respaldo de cash ({fcf_to_net_income:.1%})"
        
        base_score += adj
        _a["fcf_ni"] = adj
        adjustments.append({"metric": "FCF / Net Income", "value": f"{fcf_to_net_income:.0%}", "adjustment": adj, "reason": reason, "severity": sev})
    
    cov = CategoryCoverage()
    if archetype == FINANCIAL:
        cov.comp("Estabilidad del ROE", T["financial_roe_std_points"], _a.get("roe_std"))
        cov.comp("Eficiencia (aprox.)", T["financial_efficiency_points"], _a.get("efficiency"),
                 xv.get("efficiency_reason"))
        cov.comp("Crecimiento del valor en libros", T["financial_bv_growth_points"], _a.get("bv_growth"),
                 xv.get("book_value_cagr_3y_reason"))
    if archetype == REIT:
        cov.comp("Payout sobre FFO", T["reit_ffo_payout_points"], _a.get("ffo_payout"))
    # Piotroski None = no concluyente (o sin dato): no aporta y Calidad se reescala.
    cov.comp("Piotroski F", T["fscore_points"], _a.get("fscore"), na=_na["piotroski"])
    cov.comp("Flujo operativo", T["ocf_points"], _a.get("ocf"), na=_na["ocf"])
    cov.comp("FCF", T["fcf_points"], _a.get("fcf"), na=_na["fcf"])
    if _na["fcf_to_ni"]:
        cov.comp("FCF / beneficio neto", T["fcf_to_ni_points"], None, na=_na["fcf_to_ni"])
    elif not (net_income is not None and net_income <= 0):  # FCF/BN no aplica con BN <= 0
        cov.comp("FCF / beneficio neto", T["fcf_to_ni_points"], _a.get("fcf_ni"))
    else:
        # Regla M (etapa 9a): con beneficio <= 0 el ratio no mide la conversión en caja.
        adjustments.append({"metric": "FCF / beneficio neto", "value": "No significativo", "adjustment": 0,
                            "reason": "Beneficio neto <= 0: el ratio no mide la conversión del beneficio en caja",
                            "severity": "neutral"})
    base_score = cov.apply(base_score, adjustments)
    final_score = max(_CAT["min"], min(_CAT["max"], base_score))
    
    return {
        "category": "Calidad de Ganancias",
        "emoji": "✅",
        "score": final_score,
        "max_score": _CAT["max"],
        "base": _CAT["base"],
        "adjustments": adjustments,
        "total_adjustment": final_score - _CAT["base"],
        "coverage": cov.report(),
    }


def score_crecimiento(
    revenue_growth_3y: Optional[float],
    eps_growth_3y: Optional[float],
    fcf_growth_3y: Optional[float],
    is_growth_company: bool = False,
    fcf_growth_reason: Optional[str] = None,
    archetype: Optional[str] = None,
    revenue_note: Optional[str] = None,
    revenue_reason: Optional[str] = None,
    dividend_yield: Optional[float] = None,
    eps_reason: Optional[str] = None,
    eps_note: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Categoría 5: Crecimiento (20 pts máximo)

    Etapa 9a — REIT: el componente principal es el RETORNO TOTAL = rentabilidad
    por dividendo + CAGR del FFO por acción (llega en revenue_growth_3y), con sus
    propias bandas; la rentabilidad por dividendo ya no puntúa en Valoración.
    Base: 10 pts

    Etapa 6: el crecimiento de ingresos que llega ya es el de la rama (FINANCIAL:
    YoY de los estados; CYCLICAL: promedio de ciclo acotado) y `revenue_note`
    lo explica. BPA (GROWTH_PRE_PROFIT) y FCF (FINANCIAL, CYCLICAL) pueden no aplicar.
    """
    T = _SC["crecimiento"]
    base_score = _CAT["base"]
    _a = {}  # etapa 5: cobertura (el bono growth company queda fuera)
    adjustments = []
    _na_eps, _na_fcf = not_applicable(archetype, "eps_growth"), not_applicable(archetype, "fcf_growth")
    if _na_eps:
        eps_growth_3y = None
    if _na_fcf:
        fcf_growth_3y = None
    
    # Revenue Growth 3Y (hasta ±5 pts). REIT (etapa 6): el crecimiento se mide
    # por acción — llega el CAGR del FFO por acción, con sus propias bandas.
    _reit = archetype == REIT
    _rev_metric = "Retorno total (dividendo + FFO por acción)" if _reit else "Crecimiento Ingresos 3Y"
    _ffo_ps = revenue_growth_3y
    if _reit:
        if revenue_growth_3y is not None and dividend_yield is not None:
            revenue_growth_3y = dividend_yield + growth_for_bands(revenue_growth_3y)
            revenue_note = (f"rentabilidad por dividendo {dividend_yield:.1%} + FFO por acción {_ffo_ps:+.1%} "
                            "(CAGR 3 años)" + (f"; {revenue_note}" if revenue_note else ""))
        elif revenue_growth_3y is not None:
            revenue_reason = "sin rentabilidad por dividendo: no hay retorno total"
            revenue_growth_3y = None
    if revenue_growth_3y is not None:
        b, p = (T["reit_total_return_bounds"], T["reit_total_return_points"]) if _reit \
            else (T["revenue_bounds"], T["revenue_points"])
        if revenue_growth_3y >= b[0]:
            adj = p[0]
            sev = "excellent"
            reason = f"Crecimiento excepcional ({revenue_growth_3y:.1%})"
        elif revenue_growth_3y >= b[1]:
            adj = p[1]
            sev = "good"
            reason = f"Crecimiento sólido ({revenue_growth_3y:.1%})"
        elif revenue_growth_3y >= b[2]:
            adj = p[2]
            sev = "ok"
            reason = f"Crecimiento moderado ({revenue_growth_3y:.1%})"
        elif growth_for_bands(revenue_growth_3y) >= 0:
            adj = p[3]
            sev = "moderate"
            reason = f"Crecimiento plano ({revenue_growth_3y:.1%})"
        else:
            adj = p[4]
            sev = "severe"
            reason = f"Contracción ({revenue_growth_3y:.1%})"
        
        base_score += adj
        _a["rev"] = adj
        adjustments.append({"metric": _rev_metric, "value": f"{revenue_growth_3y:.1%}", "adjustment": adj,
                            "reason": reason + (f" — {revenue_note}" if revenue_note else ""), "severity": sev})
    
    # EPS Growth 3Y (hasta ±5 pts)
    if eps_growth_3y is not None:
        b, p = T["eps_bounds"], T["eps_points"]
        if eps_growth_3y >= b[0]:
            adj = p[0]
            sev = "excellent"
            reason = f"EPS excepcional ({eps_growth_3y:.1%})"
        elif eps_growth_3y >= b[1]:
            adj = p[1]
            sev = "good"
            reason = f"EPS sólido ({eps_growth_3y:.1%})"
        elif eps_growth_3y >= b[2]:
            adj = p[2]
            sev = "ok"
            reason = f"EPS moderado ({eps_growth_3y:.1%})"
        elif growth_for_bands(eps_growth_3y) >= 0:
            adj = p[3]
            sev = "moderate"
            reason = f"EPS plano ({eps_growth_3y:.1%})"
        else:
            adj = p[4]
            sev = "severe"
            reason = f"EPS en declive ({eps_growth_3y:.1%})"
        
        base_score += adj
        _a["eps"] = adj
        adjustments.append({"metric": "Crecimiento EPS 3Y", "value": f"{eps_growth_3y:.1%}", "adjustment": adj,
                            "reason": reason + (f" — {eps_note}" if eps_note else ""), "severity": sev})
    
    # FCF Growth (hasta ±4 pts)
    if fcf_growth_3y is not None:
        b, p = T["fcf_bounds"], T["fcf_points"]
        if fcf_growth_3y >= b[0]:
            adj = p[0]
            sev = "excellent"
            reason = f"FCF creciente ({fcf_growth_3y:.1%})"
        elif fcf_growth_3y >= b[1]:
            adj = p[1]
            sev = "good"
            reason = f"FCF estable/creciente ({fcf_growth_3y:.1%})"
        elif fcf_growth_3y >= b[2]:
            adj = p[2]
            sev = "ok"
            reason = f"FCF estable ({fcf_growth_3y:.1%})"
        else:
            adj = p[3]
            sev = "moderate"
            reason = f"FCF decreciente ({fcf_growth_3y:.1%})"
        
        base_score += adj
        _a["fcf"] = adj
        adjustments.append({"metric": "Crecimiento FCF por acción 3Y" if _reit else "Crecimiento FCF 3Y",
                            "value": f"{fcf_growth_3y:.1%}", "adjustment": adj, "reason": reason, "severity": sev})
    
    # Etapa 9a: sin bono "Growth Company": las bandas de crecimiento ya lo puntúan
    # (contarlo aparte puntuaba dos veces el mismo crecimiento de ingresos).
    
    cov = CategoryCoverage()
    if _reit:
        cov.comp("Retorno total", T["reit_total_return_points"], _a.get("rev"), revenue_reason)
    else:
        cov.comp("Crecimiento de ingresos", T["revenue_points"], _a.get("rev"), revenue_reason)
    cov.comp("Crecimiento del BPA", T["eps_points"], _a.get("eps"), eps_reason, na=_na_eps)
    cov.comp("Crecimiento del FCF", T["fcf_points"], _a.get("fcf"), fcf_growth_reason, na=_na_fcf)
    base_score = cov.apply(base_score, adjustments)
    final_score = max(_CAT["min"], min(_CAT["max"], base_score))
    
    return {
        "category": "Crecimiento",
        "emoji": "📈",
        "score": final_score,
        "max_score": _CAT["max"],
        "base": _CAT["base"],
        "adjustments": adjustments,
        "total_adjustment": final_score - _CAT["base"],
        "coverage": cov.report(),
    }


def calculate_score_v2(
    ratio_values: Dict[str, Any],
    contextual_values: Dict[str, Any],
    z_score_value: Optional[float] = None,
    z_score_level: str = "N/A",
    f_score_value: Optional[int] = None,
    sector_key: str = "default",
    real_sector: str = "",  # Sector real de Yahoo Finance
    wacc: Optional[float] = None,  # Para el spread ROIC-WACC en rentabilidad
    archetype: str = MATURE,       # etapa 6: salida de classify.classify
    archetype_values: Optional[Dict[str, Any]] = None,  # lib/archetype_metrics.compute
    dcf: Optional[Dict[str, Any]] = None,  # etapa 8: {upside, reliability, na, missing_reason}
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
    # Obtener umbrales sectoriales (o los del mercado: sector_key "market", main._select_benchmark)
    thresholds = SECTOR_THRESHOLDS.get(sector_key, ThresholdConfig())
    _market = sector_key == "market"
    
    # Determinar si es growth company
    revenue_growth = contextual_values.get("revenue_cagr_3y")
    is_growth = revenue_growth is not None and revenue_growth > _SC["total"]["growth_company_min_revenue_cagr"]
    
    # =====================================================
    # Etapa 6: el arquetipo (clasificador único) decide la rama; ya no se
    # detecta aquí "es financiera" por el nombre del sector.
    # =====================================================
    xv = archetype_values or {}
    is_financial = archetype == FINANCIAL
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
            # Etapa 6: el D/E contable no aplica a FINANCIAL (depósitos = pasivo).
            debt_to_equity=None if not_applicable(archetype, "de") else ratio_values.get("debt_to_equity"),
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
            debt_to_equity=ratio_values.get("debt_to_equity"),  # v3.2: D/E bancario
            archetype=archetype,
        )
    else:
        # Versión estándar para empresas no financieras
        solidez = score_solidez_financiera(
            z_score=z_score_value,
            z_score_level=z_score_level,
            current_ratio=ratio_values.get("current_ratio"),
            debt_to_equity=ratio_values.get("debt_to_equity"),
            interest_coverage=ratio_values.get("interest_coverage"),
            sector_de_threshold=thresholds.debt_equity_high,
            net_debt=ratio_values.get("net_debt"),
            archetype=archetype,
            runway=xv.get("runway"),
            market=_market,
            net_debt_to_ebitda=(ratio_values.get("net_debt_to_ebitda")
                                if ratio_values.get("net_debt_to_ebitda") is not None
                                else contextual_values.get("net_debt_to_ebitda")),
        )
    
    if archetype == REIT:
        rentabilidad = score_rentabilidad_reit(xv)
    elif archetype == GROWTH_PRE_PROFIT:
        rentabilidad = score_rentabilidad_growth(xv, ratio_values.get("gross_margin"))
    else:
        rentabilidad = None
    rentabilidad = rentabilidad or score_rentabilidad(
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
        sector_roa_high=thresholds.roa_high,
        archetype=archetype,
        market=_market,
    )
    
    # v2.4: Pasar datos de crecimiento + forward metrics a valoración
    valoracion = score_valoracion(
        pe=ratio_values.get("pe"),
        p_fcf=ratio_values.get("p_fcf"),
        ev_ebitda=ratio_values.get("ev_ebitda"),
        peg=ratio_values.get("peg"),
        sector_pe=contextual_values.get("sector_pe"),
        sector_ev_ebitda=contextual_values.get("sector_ev_ebitda"),
        benchmark_profile=contextual_values.get("benchmark_profile"),
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
        is_reit=(archetype == REIT),
        p_ffo=ratio_values.get("p_ffo"),
        archetype=archetype,
        xv=xv,
        dcf=dcf,
    )
    
    calidad = score_calidad_ganancias(
        f_score=f_score_value,
        fcf=ratio_values.get("fcf"),
        ocf=ratio_values.get("operating_cash_flow"),
        net_income=ratio_values.get("net_income"),
        fcf_to_net_income=ratio_values.get("fcf_to_net_income"),
        archetype=archetype,
        xv=xv,
        ffo_payout=ratio_values.get("ffo_payout"),
    )
    
    crecimiento = score_crecimiento(
        revenue_growth_3y=contextual_values.get("revenue_cagr_3y"),
        eps_growth_3y=contextual_values.get("eps_cagr_3y"),
        fcf_growth_3y=contextual_values.get("fcf_cagr_3y"),
        is_growth_company=is_growth,
        fcf_growth_reason=contextual_values.get("fcf_cagr_3y_reason"),
        archetype=archetype,
        revenue_note=contextual_values.get("revenue_growth_note"),
        revenue_reason=contextual_values.get("revenue_growth_reason"),
        dividend_yield=ratio_values.get("dividend_yield"),
        eps_reason=contextual_values.get("eps_growth_reason"),
        eps_note=contextual_values.get("eps_growth_note"),
    )
    
    # Calcular totales. Las categorías no concluyentes (cobertura < 50%) se
    # excluyen y el total se reescala a 100 sobre las restantes (etapa 5).
    categories = [solidez, rentabilidad, valoracion, calidad, crecimiento]
    label_normalized(categories, contextual_values.get("normalized_metrics"))
    if _market:   # perfil market: el nombre dice contra qué se compara
        for cat in categories:
            for a in cat.get("adjustments") or []:
                if (a.get("metric") or "").endswith(" vs Sector"):
                    a["metric"] = a["metric"][:-len(" vs Sector")] + " vs mercado"
    for cat in categories:
        cat["conclusive"] = (cat.get("coverage") or {}).get("conclusive", True)
        # Etapa 6: una categoría sin ningún componente aplicable al arquetipo
        # tampoco puntúa, pero es "no aplica", no "no concluyente".
        cat["applicable"] = (cat.get("coverage") or {}).get("applicable", True)
    included = [cat for cat in categories if cat["conclusive"] and cat["applicable"]]
    # Etapa 9a: no hay score total único. Dos puntuaciones 0–100 (lib/verdict.py):
    # Calidad del negocio (Solidez, Rentabilidad, Calidad de ganancias, Crecimiento)
    # y Atractivo del precio (Valoración), cada una reescalada a 100 sobre sus
    # categorías concluyentes y aplicables. La contracción del precio por la
    # confianza se aplica en main.py, cuando la confianza ya está calculada.
    from verdict import part_score, quality as _quality
    quality_part = _quality(categories)
    price_part = part_score(categories, cfg("thresholds.score.price.categories"))

    # v2.2: Extraer información del perfil de la empresa
    company_type = valoracion.get("company_type", "blend")
    growth_quality = valoracion.get("growth_quality_score", _SC["total"]["growth_quality_default"])
    
    result = {
        "quality": quality_part,
        "price_raw": price_part,
        "eps_vs_revenue_growth": eps_vs_revenue_growth(contextual_values.get("revenue_cagr_3y"),
                                                       contextual_values.get("eps_cagr_3y"), archetype),
        "categories": categories,
        "category_scores": {
            "solidez": solidez["score"],
            "rentabilidad": rentabilidad["score"],
            "valoracion": valoracion["score"],
            "calidad": calidad["score"],
            "crecimiento": crecimiento["score"]
        },
        "is_growth_company": is_growth,
        "excluded_categories": [cat["category"] for cat in categories if cat["applicable"] and not cat["conclusive"]],
        "not_applicable_categories": [cat["category"] for cat in categories if not cat["applicable"]],
        "score_conclusive": bool(included),
        "categories_included": len(included),
        "categories_total": len(categories),
        # Nuevos campos v2.2
        "company_type": company_type,
        "growth_quality_score": growth_quality,
        # v2.3: Campos para sector financiero
        "is_financial_sector": is_financial,
        "archetype": archetype,
        "financial_health": financial_health_data,
        # Etapa 5: cobertura por categoría (componentes con dato / aplicables).
        "coverage": {
            "solidez": solidez.get("coverage"),
            "rentabilidad": rentabilidad.get("coverage"),
            "valoracion": valoracion.get("coverage"),
            "calidad": calidad.get("coverage"),
            "crecimiento": crecimiento.get("coverage"),
        },
    }
    
    return result


# =============================================================================
# DCF SENSITIVITY ANALYSIS - v2.9
# =============================================================================

def dcf_sensitivity_analysis(
    fcf: Optional[float],
    shares_outstanding: Optional[float],
    current_price: Optional[float] = None,
    base_growth_rate: float = _DCF["signature_default_growth"],
    base_discount_rate: float = _WACC["default"],
    growth_rate_range: tuple = _GRID["growth_range"],  # (min_delta, max_delta, step)
    discount_rate_range: tuple = _GRID["discount_range"],  # (min_delta, max_delta, step)
    terminal_growth: float = DCF_TERMINAL_GROWTH,
    net_debt: Optional[float] = 0.0,
    decay_type: str = "linear",
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
        decay_type: decaimiento del crecimiento; main.py pasa el del DCF (etapa 4)
    
    Returns:
        Dict con matriz de sensibilidad, estadísticas y metadata
    """
    # Etapa 8: el grid se centra en el WACC USADO (el mismo del DCF y del spread,
    # ya acotado al único rango de config) y en el crecimiento usado. Las filas y
    # columnas que salen del rango (crecimiento fuera de [suelo, tope]; WACC fuera
    # de [clamp_min, clamp_max]) se RECORTAN: el grid puede quedar asimétrico y lo
    # dice (trimmed). Antes la base se desplazaba a [8%, 18%] para que las
    # columnas cupieran, y el caso base del grid dejaba de ser el del DCF.
    _wacc_lo, _wacc_hi = _WACC["clamp_min"], _WACC["clamp_max"]
    _g_lo, _g_hi = _DCF["min_source_growth"], _DCF["source_cap_revenue"]

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
    
    # Generar rangos de tasas (valores exactos: la celda base reproduce el DCF)
    def _axis(base, rng, lo, hi):
        d_min, d_max, step = rng
        n = int(round((d_max - d_min) / step))
        vals = [base + d_min + k * step for k in range(n + 1)]
        kept = [v for v in vals if lo - 0.001 <= v <= hi + 0.001]
        cut = [round(v, 4) for v in vals if v not in kept]
        return kept, cut

    growth_exact, g_cut = _axis(base_growth_rate, growth_rate_range, _g_lo, _g_hi)
    discount_exact, d_cut = _axis(base_discount_rate, discount_rate_range, _wacc_lo, _wacc_hi)
    growth_rates = [round(g, 4) for g in growth_exact]
    discount_rates = [round(d, 4) for d in discount_exact]
    notes = []
    if g_cut:
        notes.append(f"crecimiento recortado en [{_g_lo:.0%}, {_g_hi:.0%}]: se omiten "
                     + ", ".join(f"{g:.1%}" for g in g_cut))
    if d_cut:
        notes.append(f"WACC recortado en [{_wacc_lo:.0%}, {_wacc_hi:.0%}]: se omiten "
                     + ", ".join(f"{d:.1%}" for d in d_cut))
    result["trimmed"] = {"growth": g_cut, "discount": d_cut, "note": "; ".join(notes) or None}
    result["base_growth_idx"] = min(range(len(growth_exact)), key=lambda i: abs(growth_exact[i] - base_growth_rate))
    result["base_discount_idx"] = min(range(len(discount_exact)),
                                      key=lambda i: abs(discount_exact[i] - base_discount_rate))

    result["growth_rates"] = growth_rates
    result["discount_rates"] = discount_rates
    
    # Generar matriz de valores
    matrix = []
    all_values = []
    base_value = None
    
    for gi, growth_rate in enumerate(growth_exact):
        row = []
        for di, discount_rate in enumerate(discount_exact):
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
                net_debt=net_debt,
                decay_type=decay_type,
            )
            
            fair_value = dcf_result.get("fair_value_per_share")
            row.append(fair_value)
            
            if fair_value is not None:
                all_values.append(fair_value)
                
                # Identificar caso base
                if gi == result["base_growth_idx"] and di == result["base_discount_idx"]:
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
            
            ip = _GRID["interpretation_pct"]
            if undervalued_pct >= ip[0]:
                result["interpretation"] = f"Muy probablemente subvalorada ({undervalued_pct:.0f}% de escenarios)"
            elif undervalued_pct >= ip[1]:
                result["interpretation"] = f"Probablemente subvalorada ({undervalued_pct:.0f}% de escenarios)"
            elif undervalued_pct >= ip[2]:
                result["interpretation"] = f"Valoración mixta ({undervalued_pct:.0f}% escenarios favorables)"
            elif undervalued_pct >= ip[3]:
                result["interpretation"] = f"Probablemente sobrevalorada ({100-undervalued_pct:.0f}% de escenarios)"
            else:
                result["interpretation"] = f"Muy probablemente sobrevalorada ({100-undervalued_pct:.0f}% de escenarios)"
    
    return result


