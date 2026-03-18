"""
Finanzer - Configuración de métricas por sector.
Define las métricas clave y benchmarks para cada sector industrial.
"""

from typing import List, Dict, Any


def get_sector_metrics_config(sector: str) -> List[Dict[str, Any]]:
    """
    Retorna configuración de métricas según sector.
    
    IMPORTANTE: Los valores sector_val deben coincidir con los umbrales
    en SECTOR_THRESHOLDS de financial_ratios.py para consistencia.
    
    Args:
        sector: Nombre del sector (ej: "Technology", "Financial Services")
    
    Returns:
        Lista de dicts con configuración de métricas:
        - key: Clave del ratio en el dict de ratios
        - name: Nombre para mostrar (⭐ indica métrica clave del sector)
        - lower_better: True si valores menores son mejores
        - sector_val: Benchmark del sector
        - market_val: Benchmark del mercado (S&P 500)
        - fmt: Formato ("multiple", "percent", "decimal")
    """
    sector_lower = sector.lower() if sector else ""
    
    # Financial Services / Banks / Insurance
    if any(x in sector_lower for x in ["financial", "bank", "insurance"]):
        return [
            {"key": "pb", "name": "P/Book ⭐", "lower_better": True, "sector_val": 1.3, "market_val": 4.0, "fmt": "multiple"},
            {"key": "pe", "name": "P/E Ratio", "lower_better": True, "sector_val": 14.0, "market_val": 28.9, "fmt": "multiple"},
            {"key": "roe", "name": "ROE ⭐", "lower_better": False, "sector_val": 0.12, "market_val": 0.15, "fmt": "percent"},
            {"key": "net_margin", "name": "Margen Neto", "lower_better": False, "sector_val": 0.20, "market_val": 0.10, "fmt": "percent"},
            {"key": "dividend_yield", "name": "Dividend Yield", "lower_better": False, "sector_val": 0.025, "market_val": 0.015, "fmt": "percent"},
        ]
    
    # Technology / Software / Semiconductors
    elif any(x in sector_lower for x in ["tech", "software", "semiconductor", "information"]):
        return [
            {"key": "pe", "name": "P/E Ratio", "lower_better": True, "sector_val": 28.0, "market_val": 28.9, "fmt": "multiple"},
            {"key": "revenue_growth", "name": "Crec. Ingresos ⭐", "lower_better": False, "sector_val": 0.15, "market_val": 0.08, "fmt": "percent"},
            {"key": "gross_margin", "name": "Margen Bruto ⭐", "lower_better": False, "sector_val": 0.50, "market_val": 0.35, "fmt": "percent"},
            {"key": "operating_margin", "name": "Margen Operativo", "lower_better": False, "sector_val": 0.15, "market_val": 0.12, "fmt": "percent"},
            {"key": "roe", "name": "ROE", "lower_better": False, "sector_val": 0.22, "market_val": 0.15, "fmt": "percent"},
            {"key": "debt_to_equity", "name": "Deuda/Equity", "lower_better": True, "sector_val": 0.50, "market_val": 0.80, "fmt": "multiple"},
        ]
    
    # Healthcare / Biotech / Pharma
    elif any(x in sector_lower for x in ["health", "biotech", "pharma"]):
        return [
            {"key": "pe", "name": "P/E Ratio", "lower_better": True, "sector_val": 22.0, "market_val": 28.9, "fmt": "multiple"},
            {"key": "gross_margin", "name": "Margen Bruto ⭐", "lower_better": False, "sector_val": 0.55, "market_val": 0.35, "fmt": "percent"},
            {"key": "operating_margin", "name": "Margen Operativo", "lower_better": False, "sector_val": 0.12, "market_val": 0.12, "fmt": "percent"},
            {"key": "roe", "name": "ROE", "lower_better": False, "sector_val": 0.18, "market_val": 0.15, "fmt": "percent"},
            {"key": "debt_to_equity", "name": "Deuda/Equity", "lower_better": True, "sector_val": 0.60, "market_val": 0.80, "fmt": "multiple"},
        ]
    
    # Consumer Cyclical / Discretionary / Retail
    elif any(x in sector_lower for x in ["consumer cyclical", "consumer discretionary", "retail"]):
        return [
            {"key": "pe", "name": "P/E Ratio", "lower_better": True, "sector_val": 22.0, "market_val": 28.9, "fmt": "multiple"},
            {"key": "revenue_growth", "name": "Crec. Ingresos ⭐", "lower_better": False, "sector_val": 0.10, "market_val": 0.08, "fmt": "percent"},
            {"key": "operating_margin", "name": "Margen Operativo", "lower_better": False, "sector_val": 0.06, "market_val": 0.12, "fmt": "percent"},
            {"key": "roe", "name": "ROE", "lower_better": False, "sector_val": 0.18, "market_val": 0.15, "fmt": "percent"},
            {"key": "current_ratio", "name": "Current Ratio", "lower_better": False, "sector_val": 1.2, "market_val": 1.5, "fmt": "multiple"},
        ]
    
    # Energy / Oil & Gas
    elif any(x in sector_lower for x in ["energy", "oil", "gas"]):
        return [
            {"key": "ev_ebitda", "name": "EV/EBITDA ⭐", "lower_better": True, "sector_val": 6.0, "market_val": 12.0, "fmt": "multiple"},
            {"key": "fcf_yield", "name": "FCF Yield ⭐", "lower_better": False, "sector_val": 0.08, "market_val": 0.04, "fmt": "percent"},
            {"key": "roe", "name": "ROE", "lower_better": False, "sector_val": 0.12, "market_val": 0.15, "fmt": "percent"},
            {"key": "operating_margin", "name": "Margen Operativo", "lower_better": False, "sector_val": 0.08, "market_val": 0.12, "fmt": "percent"},
            {"key": "debt_to_equity", "name": "Deuda/Equity", "lower_better": True, "sector_val": 0.50, "market_val": 0.80, "fmt": "multiple"},
            {"key": "dividend_yield", "name": "Dividend Yield", "lower_better": False, "sector_val": 0.04, "market_val": 0.015, "fmt": "percent"},
        ]
    
    # Utilities
    elif any(x in sector_lower for x in ["utility", "utilities"]):
        return [
            {"key": "pe", "name": "P/E Ratio", "lower_better": True, "sector_val": 18.0, "market_val": 28.9, "fmt": "multiple"},
            {"key": "dividend_yield", "name": "Dividend Yield ⭐", "lower_better": False, "sector_val": 0.035, "market_val": 0.015, "fmt": "percent"},
            {"key": "roe", "name": "ROE", "lower_better": False, "sector_val": 0.10, "market_val": 0.15, "fmt": "percent"},
            {"key": "operating_margin", "name": "Margen Operativo", "lower_better": False, "sector_val": 0.12, "market_val": 0.12, "fmt": "percent"},
            {"key": "debt_to_equity", "name": "Deuda/Equity", "lower_better": True, "sector_val": 1.50, "market_val": 0.80, "fmt": "multiple"},
        ]
    
    # Consumer Defensive / Staples
    elif any(x in sector_lower for x in ["consumer defensive", "consumer staples"]):
        return [
            {"key": "pe", "name": "P/E Ratio", "lower_better": True, "sector_val": 22.0, "market_val": 28.9, "fmt": "multiple"},
            {"key": "dividend_yield", "name": "Dividend Yield ⭐", "lower_better": False, "sector_val": 0.025, "market_val": 0.015, "fmt": "percent"},
            {"key": "roe", "name": "ROE", "lower_better": False, "sector_val": 0.20, "market_val": 0.15, "fmt": "percent"},
            {"key": "operating_margin", "name": "Margen Operativo", "lower_better": False, "sector_val": 0.10, "market_val": 0.12, "fmt": "percent"},
            {"key": "gross_margin", "name": "Margen Bruto", "lower_better": False, "sector_val": 0.35, "market_val": 0.35, "fmt": "percent"},
        ]
    
    # Industrials / Aerospace / Defense
    elif any(x in sector_lower for x in ["industrial", "aerospace", "defense"]):
        return [
            {"key": "pe", "name": "P/E Ratio", "lower_better": True, "sector_val": 20.0, "market_val": 28.9, "fmt": "multiple"},
            {"key": "roe", "name": "ROE", "lower_better": False, "sector_val": 0.15, "market_val": 0.15, "fmt": "percent"},
            {"key": "operating_margin", "name": "Margen Operativo", "lower_better": False, "sector_val": 0.08, "market_val": 0.12, "fmt": "percent"},
            {"key": "debt_to_equity", "name": "Deuda/Equity", "lower_better": True, "sector_val": 0.80, "market_val": 0.80, "fmt": "multiple"},
            {"key": "current_ratio", "name": "Current Ratio", "lower_better": False, "sector_val": 1.3, "market_val": 1.5, "fmt": "multiple"},
        ]
    
    # Real Estate / REITs
    elif any(x in sector_lower for x in ["real estate", "reit"]):
        return [
            {"key": "dividend_yield", "name": "Dividend Yield ⭐", "lower_better": False, "sector_val": 0.04, "market_val": 0.015, "fmt": "percent"},
            {"key": "pb", "name": "P/Book", "lower_better": True, "sector_val": 2.0, "market_val": 4.0, "fmt": "multiple"},
            {"key": "roe", "name": "ROE", "lower_better": False, "sector_val": 0.08, "market_val": 0.15, "fmt": "percent"},
            {"key": "operating_margin", "name": "Margen Operativo", "lower_better": False, "sector_val": 0.25, "market_val": 0.12, "fmt": "percent"},
            {"key": "debt_to_equity", "name": "Deuda/Equity", "lower_better": True, "sector_val": 2.00, "market_val": 0.80, "fmt": "multiple"},
        ]
    
    # Communication Services / Media / Telecom
    elif any(x in sector_lower for x in ["communication", "media", "telecom"]):
        return [
            {"key": "pe", "name": "P/E Ratio", "lower_better": True, "sector_val": 18.0, "market_val": 28.9, "fmt": "multiple"},
            {"key": "roe", "name": "ROE", "lower_better": False, "sector_val": 0.15, "market_val": 0.15, "fmt": "percent"},
            {"key": "operating_margin", "name": "Margen Operativo", "lower_better": False, "sector_val": 0.15, "market_val": 0.12, "fmt": "percent"},
            {"key": "debt_to_equity", "name": "Deuda/Equity", "lower_better": True, "sector_val": 1.00, "market_val": 0.80, "fmt": "multiple"},
            {"key": "dividend_yield", "name": "Dividend Yield", "lower_better": False, "sector_val": 0.02, "market_val": 0.015, "fmt": "percent"},
        ]
    
    # Materials / Mining / Chemicals
    elif any(x in sector_lower for x in ["material", "mining", "chemical"]):
        return [
            {"key": "pe", "name": "P/E Ratio", "lower_better": True, "sector_val": 15.0, "market_val": 28.9, "fmt": "multiple"},
            {"key": "ev_ebitda", "name": "EV/EBITDA ⭐", "lower_better": True, "sector_val": 8.0, "market_val": 12.0, "fmt": "multiple"},
            {"key": "roe", "name": "ROE", "lower_better": False, "sector_val": 0.12, "market_val": 0.15, "fmt": "percent"},
            {"key": "operating_margin", "name": "Margen Operativo", "lower_better": False, "sector_val": 0.10, "market_val": 0.12, "fmt": "percent"},
            {"key": "debt_to_equity", "name": "Deuda/Equity", "lower_better": True, "sector_val": 0.60, "market_val": 0.80, "fmt": "multiple"},
        ]
    
    # Default / Unknown sector
    else:
        return [
            {"key": "pe", "name": "P/E Ratio", "lower_better": True, "sector_val": 20.0, "market_val": 28.9, "fmt": "multiple"},
            {"key": "roe", "name": "ROE", "lower_better": False, "sector_val": 0.15, "market_val": 0.15, "fmt": "percent"},
            {"key": "net_margin", "name": "Margen Neto", "lower_better": False, "sector_val": 0.10, "market_val": 0.10, "fmt": "percent"},
            {"key": "operating_margin", "name": "Margen Operativo", "lower_better": False, "sector_val": 0.12, "market_val": 0.12, "fmt": "percent"},
            {"key": "debt_to_equity", "name": "Deuda/Equity", "lower_better": True, "sector_val": 0.80, "market_val": 0.80, "fmt": "multiple"},
            {"key": "current_ratio", "name": "Current Ratio", "lower_better": False, "sector_val": 1.5, "market_val": 1.5, "fmt": "multiple"},
        ]


# Benchmarks generales del mercado (S&P 500)
MARKET_BENCHMARKS = {
    "pe": 28.9,
    "pb": 4.0,
    "ps": 2.5,
    "roe": 0.15,
    "roa": 0.06,
    "net_margin": 0.10,
    "operating_margin": 0.12,
    "gross_margin": 0.35,
    "debt_to_equity": 0.80,
    "current_ratio": 1.5,
    "dividend_yield": 0.015,
    "ev_ebitda": 12.0,
    "fcf_yield": 0.04,
    "revenue_growth": 0.08,
}
