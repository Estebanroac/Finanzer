"""
Perfiles de sector: mapeo Yahoo → clave canónica + ETF de referencia.
========================================================================

NOTA (auditoría sectorial 2026-07): este módulo contenía ~530 líneas de
metric_weights, primary/secondary_metrics, thresholds y typical_values por
sector que NINGÚN código consumía — un sistema de ponderación paralelo que
nunca se conectó al scorer y daba la ilusión de una adaptación inexistente.
La adaptación sectorial REAL vive en:
  - SECTOR_THRESHOLDS (financial_ratios.py): umbrales del score por sector
  - get_sector_specific_adjustments (financial_ratios.py): ajustes de alertas
  - _get_sector_benchmarks (main.py): medianas para valoración relativa
Aquí queda solo lo que sí se usa: el mapeo de nombres de Yahoo a claves
canónicas (eslabón central de toda la cadena sectorial) y el ETF de
referencia por sector.
"""

from dataclasses import dataclass


@dataclass
class SectorProfile:
    """Identidad mínima de un sector: clave canónica, nombre y ETF proxy."""
    name: str
    display_name: str
    sector_etf: str


SECTOR_PROFILES = {
    "technology": SectorProfile("technology", "Tecnología", "XLK"),
    "financials": SectorProfile("financials", "Financiero", "XLF"),
    "real_estate": SectorProfile("real_estate", "Bienes Raíces (REITs)", "VNQ"),
    "consumer_cyclical": SectorProfile("consumer_cyclical", "Consumo Cíclico", "XLY"),
    "consumer_defensive": SectorProfile("consumer_defensive", "Consumo Defensivo", "XLP"),
    "energy": SectorProfile("energy", "Energía", "XLE"),
    "utilities": SectorProfile("utilities", "Utilities", "XLU"),
    "healthcare": SectorProfile("healthcare", "Salud", "XLV"),
    "industrials": SectorProfile("industrials", "Industriales", "XLI"),
    "materials": SectorProfile("materials", "Materiales Básicos", "XLB"),
    "communication": SectorProfile("communication", "Comunicaciones", "XLC"),
}

# Mapeo de los nombres de sector que devuelve Yahoo Finance (y variantes de
# industria frecuentes) a la clave canónica usada por TODO el sistema
# sectorial (SECTOR_THRESHOLDS, benchmarks, ajustes de alertas).
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


def get_default_profile() -> SectorProfile:
    """Perfil neutro cuando el sector no se reconoce."""
    return SectorProfile("unknown", "Desconocido", "SPY")


def get_sector_profile(sector_name: str) -> SectorProfile:
    """Resuelve el perfil del sector con matching flexible.

    Acepta tanto la clave canónica snake_case (main.py pasa el sector YA
    mapeado, ej. 'real_estate') como el nombre crudo de Yahoo ('Real Estate').
    """
    if not sector_name:
        return get_default_profile()

    sector_lower = sector_name.lower().strip()

    # Clave canónica directa (sin este chequeo, consumer_cyclical /
    # consumer_defensive / real_estate caían al default por el doble mapeo:
    # YAHOO_SECTOR_MAPPING usa claves con espacios).
    if sector_lower in SECTOR_PROFILES:
        return SECTOR_PROFILES[sector_lower]

    # Nombre de Yahoo → clave canónica
    mapped_sector = YAHOO_SECTOR_MAPPING.get(sector_lower)
    if mapped_sector and mapped_sector in SECTOR_PROFILES:
        return SECTOR_PROFILES[mapped_sector]

    # Búsqueda parcial (variantes de industria no listadas)
    for key, canonical in YAHOO_SECTOR_MAPPING.items():
        if key in sector_lower or sector_lower in key:
            return SECTOR_PROFILES[canonical]

    return get_default_profile()
