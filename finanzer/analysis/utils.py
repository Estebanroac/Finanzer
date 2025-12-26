"""
Finanzer - Utilidades de análisis financiero.
Funciones helper para cálculos seguros con valores None.
"""

from typing import Optional


def safe_div(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    """
    Divide numerator by denominator de forma segura.
    Retorna None si denominator es cero o None.
    """
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def safe_multiply(*args: Optional[float]) -> Optional[float]:
    """
    Multiplica valores de forma segura.
    Retorna None si algún argumento es None.
    """
    if any(arg is None for arg in args):
        return None
    result = 1.0
    for arg in args:
        result *= arg
    return result


def safe_subtract(a: Optional[float], b: Optional[float]) -> Optional[float]:
    """
    Resta b de a de forma segura.
    Retorna None si algún argumento es None.
    """
    if a is None or b is None:
        return None
    return a - b


def safe_add(*args: Optional[float]) -> Optional[float]:
    """
    Suma valores de forma segura.
    Retorna None si algún argumento es None.
    """
    if any(arg is None for arg in args):
        return None
    return sum(args)


def safe_percentage(value: Optional[float], total: Optional[float]) -> Optional[float]:
    """
    Calcula porcentaje de forma segura.
    Retorna None si hay error.
    """
    result = safe_div(value, total)
    return result * 100 if result is not None else None


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Limita un valor entre min y max."""
    return max(min_val, min(value, max_val))


def format_large_number(value: Optional[float], decimals: int = 2) -> str:
    """
    Formatea números grandes a notación legible (K, M, B, T).
    
    Ejemplos:
        1234567890 -> "1.23B"
        1234567 -> "1.23M"
        1234 -> "1.23K"
    """
    if value is None:
        return "N/A"
    
    try:
        abs_val = abs(value)
        sign = "-" if value < 0 else ""
        
        if abs_val >= 1e12:
            return f"{sign}${abs_val/1e12:.{decimals}f}T"
        elif abs_val >= 1e9:
            return f"{sign}${abs_val/1e9:.{decimals}f}B"
        elif abs_val >= 1e6:
            return f"{sign}${abs_val/1e6:.{decimals}f}M"
        elif abs_val >= 1e3:
            return f"{sign}${abs_val/1e3:.{decimals}f}K"
        else:
            return f"{sign}${abs_val:.{decimals}f}"
    except (TypeError, ValueError):
        return "N/A"


def format_ratio(value: Optional[float], ratio_type: str = "multiple") -> str:
    """
    Formatea un ratio financiero para display.
    
    Args:
        value: El valor a formatear
        ratio_type: "multiple" (2.5x), "percent" (25.0%), "number" (2.50)
    """
    if value is None:
        return "N/A"
    
    try:
        if ratio_type == "percent":
            return f"{value * 100:.1f}%" if abs(value) < 2 else f"{value:.1f}%"
        elif ratio_type == "multiple":
            return f"{value:.2f}x"
        else:
            return f"{value:.2f}"
    except (TypeError, ValueError):
        return "N/A"
