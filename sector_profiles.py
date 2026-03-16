"""
Sector Profiles Module
======================
Sistema de perfiles dinámicos por sector que ajusta métricas, pesos,
benchmarks y evaluaciones según la industria de cada empresa.

Cada sector tiene características financieras únicas que hacen que
las métricas "normales" varíen significativamente.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum


class SectorType(Enum):
    """Tipos de sectores principales."""
    TECHNOLOGY = "technology"
    FINANCIALS = "financials"
    HEALTHCARE = "healthcare"
    CONSUMER_CYCLICAL = "consumer_cyclical"
    CONSUMER_DEFENSIVE = "consumer_defensive"
    INDUSTRIALS = "industrials"
    ENERGY = "energy"
    UTILITIES = "utilities"
    REAL_ESTATE = "real_estate"
    MATERIALS = "materials"
    COMMUNICATION = "communication"
    UNKNOWN = "unknown"


@dataclass
class MetricWeight:
    """Peso de una métrica en el score total (0-100)."""
    weight: float  # Peso relativo (suma de todos = 100)
    importance: str  # "critical", "high", "medium", "low"
    show: bool = True  # Si mostrar esta métrica


@dataclass
class MetricThreshold:
    """Umbrales para evaluar una métrica."""
    excellent: float  # Verde brillante
    good: float  # Verde
    acceptable: float  # Amarillo
    concerning: float  # Naranja
    poor: float  # Rojo
    lower_is_better: bool = False  # True para métricas como P/E, Deuda


@dataclass
class SectorProfile:
    """
    Perfil completo de un sector con todas sus configuraciones.
    """
    name: str
    display_name: str
    description: str
    
    # Métricas primarias para este sector (las más importantes)
    primary_metrics: List[str] = field(default_factory=list)
    
    # Métricas secundarias (importantes pero no críticas)
    secondary_metrics: List[str] = field(default_factory=list)
    
    # Métricas a ignorar o que no aplican
    ignore_metrics: List[str] = field(default_factory=list)
    
    # Métricas especiales del sector (ej: FFO para REITs)
    special_metrics: List[str] = field(default_factory=list)
    
    # Pesos de cada métrica para el score
    metric_weights: Dict[str, MetricWeight] = field(default_factory=dict)
    
    # Umbrales específicos del sector
    thresholds: Dict[str, MetricThreshold] = field(default_factory=dict)
    
    # Benchmarks típicos del sector
    typical_values: Dict[str, float] = field(default_factory=dict)
    
    # ETF representativo del sector
    sector_etf: str = "SPY"
    
    # Notas específicas para mostrar al usuario
    sector_notes: List[str] = field(default_factory=list)


# ============================================
# DEFINICIÓN DE PERFILES POR SECTOR
# ============================================

SECTOR_PROFILES: Dict[str, SectorProfile] = {
    
    # ==========================================
    # TECNOLOGÍA
    # ==========================================
    "technology": SectorProfile(
        name="technology",
        display_name="Tecnología",
        description="Empresas de software, hardware, semiconductores, servicios IT",
        sector_etf="XLK",
        
        primary_metrics=["pe", "revenue_growth", "gross_margin", "operating_margin", "fcf_yield"],
        secondary_metrics=["ps", "ev_ebitda", "roe", "debt_to_equity", "current_ratio"],
        ignore_metrics=["dividend_yield", "payout_ratio"],  # Muchas tech no pagan dividendos
        
        metric_weights={
            "pe": MetricWeight(15, "high"),
            "revenue_growth": MetricWeight(20, "critical"),
            "gross_margin": MetricWeight(15, "critical"),
            "operating_margin": MetricWeight(12, "high"),
            "fcf_yield": MetricWeight(10, "high"),
            "roe": MetricWeight(8, "medium"),
            "debt_to_equity": MetricWeight(8, "medium"),
            "ps": MetricWeight(7, "medium"),
            "current_ratio": MetricWeight(5, "low"),
        },
        
        thresholds={
            "pe": MetricThreshold(15, 25, 35, 50, 80, lower_is_better=True),
            "gross_margin": MetricThreshold(0.70, 0.60, 0.50, 0.40, 0.30, lower_is_better=False),
            "operating_margin": MetricThreshold(0.30, 0.20, 0.15, 0.10, 0.05, lower_is_better=False),
            "revenue_growth": MetricThreshold(0.30, 0.20, 0.10, 0.05, 0.0, lower_is_better=False),
            "roe": MetricThreshold(0.30, 0.20, 0.15, 0.10, 0.05, lower_is_better=False),
            "debt_to_equity": MetricThreshold(0.2, 0.4, 0.6, 1.0, 1.5, lower_is_better=True),
        },
        
        typical_values={
            "pe": 28.0,
            "ps": 6.0,
            "gross_margin": 0.55,
            "operating_margin": 0.20,
            "net_margin": 0.15,
            "roe": 0.20,
            "debt_to_equity": 0.40,
            "current_ratio": 2.0,
        },
        
        sector_notes=[
            "📈 El crecimiento de ingresos es la métrica más crítica",
            "💻 Márgenes brutos altos (>50%) son esperados en software",
            "💰 Muchas empresas reinvierten en lugar de pagar dividendos",
            "⚠️ P/E altos pueden estar justificados por alto crecimiento (ver PEG)",
        ]
    ),
    
    # ==========================================
    # FINANCIERO (Bancos, Aseguradoras, etc.)
    # ==========================================
    "financials": SectorProfile(
        name="financials",
        display_name="Financiero",
        description="Bancos, aseguradoras, gestoras de activos, fintech",
        sector_etf="XLF",
        
        primary_metrics=["pb", "roe", "net_margin", "dividend_yield", "efficiency_ratio"],
        secondary_metrics=["pe", "tier1_capital", "npl_ratio", "nim"],
        ignore_metrics=["ev_ebitda", "current_ratio", "quick_ratio", "gross_margin"],
        special_metrics=["net_interest_margin", "efficiency_ratio", "tier1_capital"],
        
        metric_weights={
            "pb": MetricWeight(20, "critical"),
            "roe": MetricWeight(20, "critical"),
            "net_margin": MetricWeight(15, "high"),
            "dividend_yield": MetricWeight(12, "high"),
            "pe": MetricWeight(10, "medium"),
            "debt_to_equity": MetricWeight(5, "low"),  # No aplica igual en bancos
        },
        
        thresholds={
            "pb": MetricThreshold(0.8, 1.2, 1.5, 2.0, 3.0, lower_is_better=True),
            "roe": MetricThreshold(0.15, 0.12, 0.10, 0.08, 0.05, lower_is_better=False),
            "pe": MetricThreshold(8, 12, 15, 18, 25, lower_is_better=True),
            "net_margin": MetricThreshold(0.30, 0.25, 0.20, 0.15, 0.10, lower_is_better=False),
            "dividend_yield": MetricThreshold(0.05, 0.04, 0.03, 0.02, 0.01, lower_is_better=False),
        },
        
        typical_values={
            "pe": 12.0,
            "pb": 1.2,
            "roe": 0.12,
            "net_margin": 0.25,
            "dividend_yield": 0.03,
            "debt_to_equity": 8.0,  # ¡Muy alto es normal!
        },
        
        sector_notes=[
            "🏦 P/Book es MÁS importante que P/E en bancos",
            "📊 Ratios de deuda NO aplican - los bancos son apalancados por naturaleza",
            "💵 ROE consistente >10% es señal de buen banco",
            "⚠️ Mira NPL ratio (préstamos morosos) y Tier 1 Capital para riesgo",
        ]
    ),
    
    # ==========================================
    # BIENES RAÍCES (REITs)
    # ==========================================
    "real_estate": SectorProfile(
        name="real_estate",
        display_name="Bienes Raíces (REITs)",
        description="Fideicomisos de inversión inmobiliaria, desarrolladoras",
        sector_etf="VNQ",
        
        primary_metrics=["ffo_pershare", "affo", "dividend_yield", "pb", "occupancy_rate"],
        secondary_metrics=["debt_to_equity", "nav_premium"],
        ignore_metrics=["pe", "eps", "net_margin", "gross_margin"],  # P/E no aplica a REITs
        special_metrics=["ffo", "affo", "nav", "cap_rate"],
        
        metric_weights={
            "dividend_yield": MetricWeight(25, "critical"),
            "pb": MetricWeight(20, "critical"),
            "debt_to_equity": MetricWeight(15, "high"),
            "occupancy_rate": MetricWeight(15, "high"),
            "ffo_growth": MetricWeight(15, "high"),
        },
        
        thresholds={
            "dividend_yield": MetricThreshold(0.07, 0.05, 0.04, 0.03, 0.02, lower_is_better=False),
            "pb": MetricThreshold(0.9, 1.1, 1.3, 1.5, 2.0, lower_is_better=True),
            "debt_to_equity": MetricThreshold(0.5, 0.8, 1.0, 1.5, 2.0, lower_is_better=True),
        },
        
        typical_values={
            "pe": None,  # No usar
            "pb": 1.2,
            "dividend_yield": 0.045,
            "debt_to_equity": 0.80,
        },
        
        sector_notes=[
            "🏢 NO uses P/E - usa P/FFO (Funds From Operations)",
            "💰 Dividend yield es crucial - REITs deben distribuir 90% de ingresos",
            "📊 P/NAV (vs valor neto de activos) es mejor que P/Book",
            "🏗️ Tasa de ocupación y calidad de inquilinos son clave",
        ]
    ),
    
    # ==========================================
    # CONSUMO CÍCLICO (Retail, Autos, Hoteles)
    # ==========================================
    "consumer_cyclical": SectorProfile(
        name="consumer_cyclical",
        display_name="Consumo Cíclico",
        description="Retail, automóviles, hoteles, restaurantes, entretenimiento",
        sector_etf="XLY",
        
        primary_metrics=["pe", "revenue_growth", "operating_margin", "inventory_turnover", "same_store_sales"],
        secondary_metrics=["debt_to_equity", "current_ratio", "roe"],
        ignore_metrics=[],
        special_metrics=["same_store_sales", "inventory_turnover", "customer_acquisition_cost"],
        
        metric_weights={
            "pe": MetricWeight(15, "high"),
            "revenue_growth": MetricWeight(18, "critical"),
            "operating_margin": MetricWeight(15, "high"),
            "same_store_sales": MetricWeight(15, "critical"),
            "inventory_turnover": MetricWeight(12, "high"),
            "debt_to_equity": MetricWeight(10, "medium"),
            "current_ratio": MetricWeight(8, "medium"),
            "roe": MetricWeight(7, "medium"),
        },
        
        thresholds={
            "pe": MetricThreshold(12, 18, 25, 35, 50, lower_is_better=True),
            "operating_margin": MetricThreshold(0.15, 0.10, 0.07, 0.05, 0.03, lower_is_better=False),
            "revenue_growth": MetricThreshold(0.15, 0.10, 0.05, 0.02, 0.0, lower_is_better=False),
            "debt_to_equity": MetricThreshold(0.3, 0.5, 0.8, 1.2, 2.0, lower_is_better=True),
            "current_ratio": MetricThreshold(2.0, 1.5, 1.2, 1.0, 0.8, lower_is_better=False),
        },
        
        typical_values={
            "pe": 20.0,
            "operating_margin": 0.08,
            "net_margin": 0.05,
            "roe": 0.15,
            "debt_to_equity": 0.60,
            "current_ratio": 1.3,
        },
        
        sector_notes=[
            "🛒 Same-store sales (SSS) es clave para retailers",
            "📦 Rotación de inventario indica eficiencia operativa",
            "⚠️ Sector muy sensible a ciclos económicos",
            "💳 Mira tendencias de consumo y competencia online",
        ]
    ),
    
    # ==========================================
    # CONSUMO DEFENSIVO (Alimentos, Bebidas, Household)
    # ==========================================
    "consumer_defensive": SectorProfile(
        name="consumer_defensive",
        display_name="Consumo Defensivo",
        description="Alimentos, bebidas, productos del hogar, supermercados",
        sector_etf="XLP",
        
        primary_metrics=["pe", "dividend_yield", "payout_ratio", "operating_margin", "debt_to_equity"],
        secondary_metrics=["revenue_growth", "roe", "current_ratio"],
        ignore_metrics=[],
        
        metric_weights={
            "pe": MetricWeight(18, "high"),
            "dividend_yield": MetricWeight(18, "critical"),
            "operating_margin": MetricWeight(15, "high"),
            "debt_to_equity": MetricWeight(12, "high"),
            "payout_ratio": MetricWeight(12, "high"),
            "roe": MetricWeight(10, "medium"),
            "revenue_growth": MetricWeight(8, "medium"),
            "current_ratio": MetricWeight(7, "low"),
        },
        
        thresholds={
            "pe": MetricThreshold(15, 20, 25, 30, 40, lower_is_better=True),
            "dividend_yield": MetricThreshold(0.04, 0.03, 0.025, 0.02, 0.01, lower_is_better=False),
            "operating_margin": MetricThreshold(0.18, 0.15, 0.12, 0.08, 0.05, lower_is_better=False),
            "debt_to_equity": MetricThreshold(0.4, 0.6, 0.8, 1.2, 1.5, lower_is_better=True),
            "payout_ratio": MetricThreshold(0.50, 0.60, 0.70, 0.80, 0.90, lower_is_better=True),
        },
        
        typical_values={
            "pe": 22.0,
            "dividend_yield": 0.028,
            "operating_margin": 0.12,
            "net_margin": 0.08,
            "roe": 0.18,
            "debt_to_equity": 0.70,
        },
        
        sector_notes=[
            "🛡️ Sector defensivo - menos volátil en recesiones",
            "💰 Dividendos estables son muy valorados",
            "📊 Crecimiento lento pero constante es normal",
            "🏷️ Poder de marca y pricing power son clave",
        ]
    ),
    
    # ==========================================
    # ENERGÍA (Petróleo, Gas, Renovables)
    # ==========================================
    "energy": SectorProfile(
        name="energy",
        display_name="Energía",
        description="Petróleo, gas natural, energías renovables, servicios energéticos",
        sector_etf="XLE",
        
        primary_metrics=["ev_ebitda", "fcf_yield", "debt_to_equity", "dividend_yield", "reserve_replacement"],
        secondary_metrics=["pe", "roe", "operating_margin"],
        ignore_metrics=["ps"],  # Ventas fluctúan mucho con precios de commodities
        special_metrics=["reserve_life", "production_cost", "reserve_replacement_ratio"],
        
        metric_weights={
            "ev_ebitda": MetricWeight(18, "critical"),
            "fcf_yield": MetricWeight(18, "critical"),
            "debt_to_equity": MetricWeight(15, "high"),
            "dividend_yield": MetricWeight(15, "high"),
            "roe": MetricWeight(12, "medium"),
            "operating_margin": MetricWeight(12, "medium"),
            "pe": MetricWeight(10, "low"),  # Muy volátil con precios de commodities
        },
        
        thresholds={
            "ev_ebitda": MetricThreshold(4, 6, 8, 10, 15, lower_is_better=True),
            "fcf_yield": MetricThreshold(0.12, 0.08, 0.06, 0.04, 0.02, lower_is_better=False),
            "debt_to_equity": MetricThreshold(0.3, 0.5, 0.7, 1.0, 1.5, lower_is_better=True),
            "dividend_yield": MetricThreshold(0.06, 0.04, 0.03, 0.02, 0.01, lower_is_better=False),
        },
        
        typical_values={
            "pe": 12.0,
            "ev_ebitda": 6.0,
            "fcf_yield": 0.08,
            "debt_to_equity": 0.45,
            "dividend_yield": 0.04,
        },
        
        sector_notes=[
            "⛽ EV/EBITDA es mejor que P/E (ganancias muy cíclicas)",
            "💰 FCF Yield indica capacidad de pagar dividendos y reducir deuda",
            "📊 Reservas y costos de producción son métricas clave",
            "⚠️ Muy sensible a precios de petróleo/gas - evalúa breakeven",
        ]
    ),
    
    # ==========================================
    # UTILITIES (Electricidad, Agua, Gas)
    # ==========================================
    "utilities": SectorProfile(
        name="utilities",
        display_name="Servicios Públicos",
        description="Electricidad, agua, gas natural, energía regulada",
        sector_etf="XLU",
        
        primary_metrics=["dividend_yield", "payout_ratio", "debt_to_ebitda", "pe", "regulated_vs_unregulated"],
        secondary_metrics=["roe", "operating_margin", "interest_coverage"],
        ignore_metrics=["revenue_growth", "ps"],  # Crecimiento limitado por regulación
        
        metric_weights={
            "dividend_yield": MetricWeight(25, "critical"),
            "payout_ratio": MetricWeight(15, "high"),
            "debt_to_ebitda": MetricWeight(15, "high"),
            "pe": MetricWeight(15, "high"),
            "interest_coverage": MetricWeight(12, "high"),
            "roe": MetricWeight(10, "medium"),
            "operating_margin": MetricWeight(8, "medium"),
        },
        
        thresholds={
            "dividend_yield": MetricThreshold(0.05, 0.04, 0.035, 0.03, 0.02, lower_is_better=False),
            "pe": MetricThreshold(14, 17, 20, 23, 28, lower_is_better=True),
            "debt_to_ebitda": MetricThreshold(3.0, 4.0, 5.0, 6.0, 7.0, lower_is_better=True),
            "payout_ratio": MetricThreshold(0.60, 0.70, 0.75, 0.80, 0.90, lower_is_better=True),
            "interest_coverage": MetricThreshold(4.0, 3.0, 2.5, 2.0, 1.5, lower_is_better=False),
        },
        
        typical_values={
            "pe": 18.0,
            "dividend_yield": 0.035,
            "payout_ratio": 0.65,
            "debt_to_ebitda": 4.5,
            "roe": 0.10,
        },
        
        sector_notes=[
            "🔌 Sector muy regulado - retornos predecibles pero limitados",
            "💰 Dividend yield y estabilidad son las métricas clave",
            "📊 Deuda alta es normal pero mira cobertura de intereses",
            "⚡ Transición energética puede afectar valoraciones futuras",
        ]
    ),
    
    # ==========================================
    # SALUD (Pharma, Biotech, Servicios médicos)
    # ==========================================
    "healthcare": SectorProfile(
        name="healthcare",
        display_name="Salud",
        description="Farmacéuticas, biotecnología, dispositivos médicos, servicios de salud",
        sector_etf="XLV",
        
        primary_metrics=["pe", "revenue_growth", "rd_ratio", "gross_margin", "pipeline_value"],
        secondary_metrics=["operating_margin", "debt_to_equity", "roe", "fcf_yield"],
        ignore_metrics=[],
        special_metrics=["rd_to_revenue", "pipeline_value", "patent_expiry"],
        
        metric_weights={
            "pe": MetricWeight(15, "high"),
            "revenue_growth": MetricWeight(18, "critical"),
            "gross_margin": MetricWeight(15, "high"),
            "rd_ratio": MetricWeight(12, "high"),
            "operating_margin": MetricWeight(12, "high"),
            "debt_to_equity": MetricWeight(10, "medium"),
            "roe": MetricWeight(10, "medium"),
            "fcf_yield": MetricWeight(8, "medium"),
        },
        
        thresholds={
            "pe": MetricThreshold(15, 22, 30, 40, 60, lower_is_better=True),
            "gross_margin": MetricThreshold(0.75, 0.65, 0.55, 0.45, 0.35, lower_is_better=False),
            "operating_margin": MetricThreshold(0.25, 0.20, 0.15, 0.10, 0.05, lower_is_better=False),
            "revenue_growth": MetricThreshold(0.15, 0.10, 0.05, 0.02, 0.0, lower_is_better=False),
            "debt_to_equity": MetricThreshold(0.3, 0.5, 0.8, 1.2, 2.0, lower_is_better=True),
        },
        
        typical_values={
            "pe": 25.0,
            "gross_margin": 0.65,
            "operating_margin": 0.18,
            "rd_ratio": 0.15,
            "roe": 0.15,
            "debt_to_equity": 0.50,
        },
        
        sector_notes=[
            "💊 Pipeline de productos y patentes son cruciales",
            "🔬 Inversión en I+D alta es señal de innovación",
            "📊 Biotech sin ingresos: evalúa cash runway y pipeline",
            "⚠️ Riesgo de vencimiento de patentes (patent cliff)",
        ]
    ),
    
    # ==========================================
    # INDUSTRIALES (Manufactura, Transporte, Defensa)
    # ==========================================
    "industrials": SectorProfile(
        name="industrials",
        display_name="Industriales",
        description="Manufactura, aeroespacial, defensa, transporte, construcción",
        sector_etf="XLI",
        
        primary_metrics=["pe", "ev_ebitda", "operating_margin", "roe", "order_backlog"],
        secondary_metrics=["debt_to_equity", "current_ratio", "revenue_growth", "dividend_yield"],
        ignore_metrics=[],
        special_metrics=["order_backlog", "book_to_bill", "capacity_utilization"],
        
        metric_weights={
            "pe": MetricWeight(15, "high"),
            "ev_ebitda": MetricWeight(15, "high"),
            "operating_margin": MetricWeight(15, "high"),
            "roe": MetricWeight(12, "high"),
            "debt_to_equity": MetricWeight(12, "high"),
            "order_backlog": MetricWeight(10, "high"),
            "revenue_growth": MetricWeight(10, "medium"),
            "current_ratio": MetricWeight(6, "medium"),
            "dividend_yield": MetricWeight(5, "low"),
        },
        
        thresholds={
            "pe": MetricThreshold(14, 18, 22, 28, 35, lower_is_better=True),
            "ev_ebitda": MetricThreshold(8, 10, 12, 15, 20, lower_is_better=True),
            "operating_margin": MetricThreshold(0.15, 0.12, 0.10, 0.07, 0.05, lower_is_better=False),
            "roe": MetricThreshold(0.20, 0.15, 0.12, 0.08, 0.05, lower_is_better=False),
            "debt_to_equity": MetricThreshold(0.4, 0.6, 0.8, 1.2, 1.5, lower_is_better=True),
        },
        
        typical_values={
            "pe": 20.0,
            "ev_ebitda": 11.0,
            "operating_margin": 0.11,
            "roe": 0.15,
            "debt_to_equity": 0.60,
        },
        
        sector_notes=[
            "🏭 Order backlog indica demanda futura",
            "📊 Márgenes operativos son clave en manufactura",
            "⚠️ Sector cíclico - muy sensible a economía",
            "🔧 CapEx alto es normal - evalúa retorno sobre inversión",
        ]
    ),
    
    # ==========================================
    # MATERIALES (Minería, Químicos, Papel)
    # ==========================================
    "materials": SectorProfile(
        name="materials",
        display_name="Materiales",
        description="Minería, químicos, acero, papel, materiales de construcción",
        sector_etf="XLB",
        
        primary_metrics=["ev_ebitda", "fcf_yield", "debt_to_equity", "operating_margin", "reserve_life"],
        secondary_metrics=["pe", "roe", "dividend_yield"],
        ignore_metrics=["ps"],
        special_metrics=["reserve_life", "production_cost", "commodity_exposure"],
        
        metric_weights={
            "ev_ebitda": MetricWeight(20, "critical"),
            "fcf_yield": MetricWeight(18, "critical"),
            "debt_to_equity": MetricWeight(15, "high"),
            "operating_margin": MetricWeight(15, "high"),
            "roe": MetricWeight(12, "medium"),
            "pe": MetricWeight(10, "medium"),
            "dividend_yield": MetricWeight(10, "medium"),
        },
        
        thresholds={
            "ev_ebitda": MetricThreshold(5, 7, 9, 12, 15, lower_is_better=True),
            "fcf_yield": MetricThreshold(0.10, 0.07, 0.05, 0.03, 0.01, lower_is_better=False),
            "debt_to_equity": MetricThreshold(0.3, 0.5, 0.7, 1.0, 1.5, lower_is_better=True),
            "operating_margin": MetricThreshold(0.20, 0.15, 0.10, 0.07, 0.04, lower_is_better=False),
        },
        
        typical_values={
            "pe": 14.0,
            "ev_ebitda": 7.0,
            "operating_margin": 0.12,
            "debt_to_equity": 0.50,
        },
        
        sector_notes=[
            "⛏️ Sector muy cíclico - depende de precios de commodities",
            "📊 EV/EBITDA es mejor que P/E por volatilidad",
            "💰 FCF en la parte alta del ciclo debe usarse para pagar deuda",
            "⚠️ Evalúa costos de producción vs precio del commodity",
        ]
    ),
    
    # ==========================================
    # COMUNICACIONES (Telecom, Media, Internet)
    # ==========================================
    "communication": SectorProfile(
        name="communication",
        display_name="Comunicaciones",
        description="Telecomunicaciones, medios, entretenimiento, redes sociales",
        sector_etf="XLC",
        
        primary_metrics=["pe", "ev_ebitda", "revenue_growth", "arpu", "subscriber_growth"],
        secondary_metrics=["operating_margin", "debt_to_equity", "fcf_yield", "dividend_yield"],
        ignore_metrics=[],
        special_metrics=["arpu", "churn_rate", "subscriber_count"],
        
        metric_weights={
            "pe": MetricWeight(15, "high"),
            "ev_ebitda": MetricWeight(15, "high"),
            "revenue_growth": MetricWeight(18, "critical"),
            "operating_margin": MetricWeight(12, "high"),
            "subscriber_metrics": MetricWeight(12, "high"),
            "debt_to_equity": MetricWeight(10, "medium"),
            "fcf_yield": MetricWeight(10, "medium"),
            "dividend_yield": MetricWeight(8, "medium"),
        },
        
        thresholds={
            "pe": MetricThreshold(15, 22, 30, 40, 55, lower_is_better=True),
            "ev_ebitda": MetricThreshold(8, 10, 13, 16, 20, lower_is_better=True),
            "revenue_growth": MetricThreshold(0.20, 0.12, 0.06, 0.02, 0.0, lower_is_better=False),
            "operating_margin": MetricThreshold(0.25, 0.20, 0.15, 0.10, 0.05, lower_is_better=False),
            "debt_to_equity": MetricThreshold(0.5, 0.8, 1.2, 1.8, 2.5, lower_is_better=True),
        },
        
        typical_values={
            "pe": 20.0,
            "ev_ebitda": 10.0,
            "operating_margin": 0.18,
            "debt_to_equity": 0.90,
        },
        
        sector_notes=[
            "📱 Telecom tradicional: dividendos y FCF son clave",
            "📊 Media digital: crecimiento de usuarios y engagement",
            "💰 Alto CapEx en infraestructura (5G, fibra)",
            "⚠️ Competencia intensa - evalúa moats y pricing power",
        ]
    ),
}


# ============================================
# MAPEO DE SECTORES DE YAHOO FINANCE
# ============================================

YAHOO_SECTOR_MAPPING = {
    # Tecnología
    "technology": "technology",
    "software": "technology",
    "hardware": "technology",
    "semiconductors": "technology",
    "information technology": "technology",
    
    # Financiero
    "financial services": "financials",
    "financial": "financials",
    "financials": "financials",
    "banks": "financials",
    "insurance": "financials",
    
    # Bienes Raíces
    "real estate": "real_estate",
    "reit": "real_estate",
    
    # Consumo Cíclico
    "consumer cyclical": "consumer_cyclical",
    "consumer discretionary": "consumer_cyclical",
    "retail": "consumer_cyclical",
    "automotive": "consumer_cyclical",
    "restaurants": "consumer_cyclical",
    
    # Consumo Defensivo
    "consumer defensive": "consumer_defensive",
    "consumer staples": "consumer_defensive",
    "food & beverage": "consumer_defensive",
    "household products": "consumer_defensive",
    
    # Energía
    "energy": "energy",
    "oil & gas": "energy",
    
    # Utilities
    "utilities": "utilities",
    
    # Salud
    "healthcare": "healthcare",
    "health care": "healthcare",
    "biotechnology": "healthcare",
    "pharmaceuticals": "healthcare",
    
    # Industriales
    "industrials": "industrials",
    "industrial": "industrials",
    "aerospace": "industrials",
    "defense": "industrials",
    
    # Materiales
    "basic materials": "materials",
    "materials": "materials",
    "mining": "materials",
    "chemicals": "materials",
    
    # Comunicaciones
    "communication services": "communication",
    "communication": "communication",
    "telecommunications": "communication",
    "media": "communication",
}


def get_sector_profile(sector_name: str) -> SectorProfile:
    """
    Obtiene el perfil del sector basado en el nombre.
    Hace matching flexible con nombres de Yahoo Finance.
    """
    if not sector_name:
        return get_default_profile()
    
    sector_lower = sector_name.lower().strip()
    
    # Buscar en el mapeo
    mapped_sector = YAHOO_SECTOR_MAPPING.get(sector_lower)
    
    if mapped_sector and mapped_sector in SECTOR_PROFILES:
        return SECTOR_PROFILES[mapped_sector]
    
    # Búsqueda parcial
    for key, value in YAHOO_SECTOR_MAPPING.items():
        if key in sector_lower or sector_lower in key:
            if value in SECTOR_PROFILES:
                return SECTOR_PROFILES[value]
    
    # Default
    return get_default_profile()


def get_default_profile() -> SectorProfile:
    """Perfil por defecto cuando no se puede determinar el sector."""
    return SectorProfile(
        name="unknown",
        display_name="General",
        description="Perfil genérico para empresas sin sector identificado",
        sector_etf="SPY",
        
        primary_metrics=["pe", "roe", "operating_margin", "debt_to_equity", "revenue_growth"],
        secondary_metrics=["pb", "ps", "current_ratio", "dividend_yield"],
        
        metric_weights={
            "pe": MetricWeight(15, "high"),
            "roe": MetricWeight(15, "high"),
            "operating_margin": MetricWeight(12, "high"),
            "debt_to_equity": MetricWeight(12, "high"),
            "revenue_growth": MetricWeight(12, "high"),
            "current_ratio": MetricWeight(8, "medium"),
            "dividend_yield": MetricWeight(8, "medium"),
            "pb": MetricWeight(8, "medium"),
            "ps": MetricWeight(5, "low"),
        },
        
        thresholds={
            "pe": MetricThreshold(15, 20, 28, 40, 60, lower_is_better=True),
            "roe": MetricThreshold(0.20, 0.15, 0.10, 0.07, 0.03, lower_is_better=False),
            "operating_margin": MetricThreshold(0.20, 0.15, 0.10, 0.05, 0.02, lower_is_better=False),
            "debt_to_equity": MetricThreshold(0.3, 0.5, 0.8, 1.2, 2.0, lower_is_better=True),
        },
        
        typical_values={
            "pe": 20.0,
            "roe": 0.12,
            "operating_margin": 0.12,
            "debt_to_equity": 0.60,
        },
        
        sector_notes=[
            "📊 Usando métricas generales del mercado",
            "⚠️ Considera buscar benchmarks específicos del sector",
        ]
    )


# Métricas que se almacenan como decimales y deben mostrarse como porcentaje
_PERCENTAGE_METRICS = {
    "gross_margin", "operating_margin", "net_margin",
    "roe", "roa", "roic", "revenue_growth", "eps_growth",
    "dividend_yield", "fcf_yield", "earnings_growth",
}


def _format_typical(metric_name: str, typical: float) -> str:
    """Formatea el valor típico según el tipo de métrica."""
    if metric_name in _PERCENTAGE_METRICS:
        return f"{typical:.1%}"
    return f"{typical:.1f}"


def evaluate_metric_by_sector(
    metric_name: str,
    value: float,
    sector_profile: SectorProfile
) -> Tuple[str, str, str]:
    """
    Evalúa una métrica según el perfil del sector.
    
    Returns:
        Tuple de (evaluación, color, explicación)
        evaluación: "excelente", "bueno", "aceptable", "preocupante", "pobre"
        color: código hex del color
        explicación: texto explicativo
    """
    if value is None:
        return ("sin_datos", "#a1a1aa", "No hay datos disponibles")
    
    threshold = sector_profile.thresholds.get(metric_name)
    if not threshold:
        return ("sin_umbral", "#a1a1aa", "Sin umbral definido para este sector")
    
    typical = sector_profile.typical_values.get(metric_name)
    
    # Evaluar según si menor es mejor
    typical_str = _format_typical(metric_name, typical) if typical else ""

    if threshold.lower_is_better:
        if value <= threshold.excellent:
            evaluation = "excelente"
            color = "#22c55e"  # Verde brillante
            vs_typical = f"Muy por debajo del típico ({typical_str})" if typical else ""
        elif value <= threshold.good:
            evaluation = "bueno"
            color = "#4ade80"  # Verde
            vs_typical = f"Mejor que típico ({typical_str})" if typical else ""
        elif value <= threshold.acceptable:
            evaluation = "aceptable"
            color = "#eab308"  # Amarillo
            vs_typical = f"Cerca del típico ({typical_str})" if typical else ""
        elif value <= threshold.concerning:
            evaluation = "preocupante"
            color = "#f97316"  # Naranja
            vs_typical = f"Por encima del típico ({typical_str})" if typical else ""
        else:
            evaluation = "pobre"
            color = "#ef4444"  # Rojo
            vs_typical = f"Muy por encima del típico ({typical_str})" if typical else ""
    else:
        if value >= threshold.excellent:
            evaluation = "excelente"
            color = "#22c55e"
            vs_typical = f"Muy por encima del típico ({typical_str})" if typical else ""
        elif value >= threshold.good:
            evaluation = "bueno"
            color = "#4ade80"
            vs_typical = f"Mejor que típico ({typical_str})" if typical else ""
        elif value >= threshold.acceptable:
            evaluation = "aceptable"
            color = "#eab308"
            vs_typical = f"Cerca del típico ({typical_str})" if typical else ""
        elif value >= threshold.concerning:
            evaluation = "preocupante"
            color = "#f97316"
            vs_typical = f"Por debajo del típico ({typical_str})" if typical else ""
        else:
            evaluation = "pobre"
            color = "#ef4444"
            vs_typical = f"Muy por debajo del típico ({typical_str})" if typical else ""
    
    return (evaluation, color, vs_typical)


def calculate_sector_adjusted_score(
    ratios: Dict[str, float],
    sector_profile: SectorProfile
) -> Tuple[int, Dict[str, any]]:
    """
    Calcula el score ajustado por sector.
    
    Returns:
        Tuple de (score 0-100, breakdown detallado)
    """
    total_weight = 0
    weighted_score = 0
    breakdown = {}
    
    for metric_name, weight_config in sector_profile.metric_weights.items():
        value = ratios.get(metric_name)
        if value is None:
            continue
        
        evaluation, color, explanation = evaluate_metric_by_sector(
            metric_name, value, sector_profile
        )
        
        # Convertir evaluación a puntos (0-100)
        score_map = {
            "excelente": 100,
            "bueno": 80,
            "aceptable": 60,
            "preocupante": 40,
            "pobre": 20,
        }
        
        metric_score = score_map.get(evaluation, 50)
        weighted_score += metric_score * weight_config.weight
        total_weight += weight_config.weight
        
        breakdown[metric_name] = {
            "value": value,
            "score": metric_score,
            "weight": weight_config.weight,
            "evaluation": evaluation,
            "color": color,
            "explanation": explanation,
            "importance": weight_config.importance,
        }
    
    # Calcular score final
    final_score = int(weighted_score / total_weight) if total_weight > 0 else 50
    
    return (final_score, breakdown)
