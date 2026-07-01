"""
Finanzer - Utilidades de búsqueda y resolución de símbolos.
Valida y normaliza símbolos de acciones.
"""

import re
from typing import Dict


# Mapeo de nombres comunes a símbolos
COMPANY_NAMES: Dict[str, str] = {
    # Tech Giants
    "apple": "AAPL",
    "microsoft": "MSFT",
    "google": "GOOGL",
    "alphabet": "GOOGL",
    "amazon": "AMZN",
    "meta": "META",
    "facebook": "META",
    "nvidia": "NVDA",
    "tesla": "TSLA",
    "netflix": "NFLX",
    
    # Finance
    "berkshire": "BRK-B",
    "jpmorgan": "JPM",
    "jp morgan": "JPM",
    "goldman": "GS",
    "goldman sachs": "GS",
    "visa": "V",
    "mastercard": "MA",
    "bank of america": "BAC",
    "wells fargo": "WFC",
    
    # Healthcare
    "johnson": "JNJ",
    "johnson & johnson": "JNJ",
    "pfizer": "PFE",
    "unitedhealth": "UNH",
    "eli lilly": "LLY",
    "abbvie": "ABBV",
    
    # Consumer
    "walmart": "WMT",
    "coca-cola": "KO",
    "cocacola": "KO",
    "coca cola": "KO",
    "pepsi": "PEP",
    "pepsico": "PEP",
    "costco": "COST",
    "home depot": "HD",
    "mcdonald": "MCD",
    "mcdonalds": "MCD",
    "disney": "DIS",
    "nike": "NKE",
    "starbucks": "SBUX",
    
    # Industrial
    "boeing": "BA",
    "caterpillar": "CAT",
    "3m": "MMM",
    "honeywell": "HON",
    "ge": "GE",
    "general electric": "GE",
    
    # Semiconductors
    "amd": "AMD",
    "intel": "INTC",
    "qualcomm": "QCOM",
    "broadcom": "AVGO",
    "tsmc": "TSM",
    
    # Índices/ETFs
    "s&p": "SPY",
    "s&p 500": "SPY",
    "spy": "SPY",
    "nasdaq": "QQQ",
    "qqq": "QQQ",
    "dow": "DIA",
}


def resolve_symbol(query: str) -> str:
    """
    Resuelve y valida el símbolo de búsqueda.
    Validación PERMISIVA: sanitiza pero no rechaza símbolos potencialmente válidos.
    
    Args:
        query: Texto de búsqueda (puede ser nombre de empresa o ticker)
    
    Returns:
        Símbolo normalizado en mayúsculas
    """
    if not query:
        return ""
    
    query_clean = query.strip()
    
    # Límite de longitud razonable (símbolos más largos son raros)
    if len(query_clean) > 15:
        query_clean = query_clean[:15]
    
    # Buscar en mapeo de nombres comunes
    query_lower = query_clean.lower()
    if query_lower in COMPANY_NAMES:
        return COMPANY_NAMES[query_lower]
    
    # Sanitización: solo permitir caracteres válidos para tickers
    # Incluye: letras, números, punto (BRK.A), guión (BRK-B), espacio (para búsqueda)
    sanitized = re.sub(r'[^A-Za-z0-9\.\-\s]', '', query_clean)
    
    return sanitized.upper().strip()


def is_valid_ticker(symbol: str) -> bool:
    """
    Verifica si un símbolo tiene formato válido de ticker.
    
    Args:
        symbol: Símbolo a validar
    
    Returns:
        True si el formato es válido
    """
    if not symbol or len(symbol) > 10:
        return False
    
    # Patrón: 1-5 letras, opcionalmente seguido de .X o -X
    pattern = r'^[A-Z]{1,5}([.\-][A-Z]{1,2})?$'
    return bool(re.match(pattern, symbol.upper()))


def normalize_ticker(symbol: str) -> str:
    """
    Normaliza un ticker a formato estándar.
    
    Args:
        symbol: Símbolo a normalizar
    
    Returns:
        Símbolo en mayúsculas sin espacios
    """
    if not symbol:
        return ""
    return symbol.upper().strip().replace(" ", "")
