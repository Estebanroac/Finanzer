"""
Finanzer - Funciones de formateo centralizadas.
Evita duplicación de código en app.py, comparison.py y pdf_generator.py.
"""

from typing import Optional, Union

Number = Union[int, float, None]


def fmt(val: Number, tipo: str = "number", na_text: str = "N/A") -> str:
    """
    Formatea valores numéricos para display.
    
    Args:
        val: Valor a formatear
        tipo: Tipo de formato:
            - "number": Número simple (2 decimales)
            - "percent" o "%": Porcentaje (asume decimal, ej: 0.15 → "15.0%")
            - "multiple" o "x": Múltiplo (ej: 2.5 → "2.5x")
            - "currency" o "$": Moneda con sufijos (T/B/M)
        na_text: Texto para valores None (default "N/A", usar "—" para PDFs)
    
    Returns:
        String formateado
    
    Examples:
        >>> fmt(0.156, "percent")
        '15.6%'
        >>> fmt(2.5, "multiple")
        '2.5x'
        >>> fmt(1500000000, "currency")
        '$1.5B'
    """
    if val is None:
        return na_text
    
    try:
        v = float(val)
        
        # Porcentaje
        if tipo in ("percent", "%"):
            # Si el valor es > 2, probablemente ya viene como porcentaje
            return f"{v * 100:.1f}%" if abs(v) < 2 else f"{v:.1f}%"
        
        # Múltiplo
        if tipo in ("multiple", "x"):
            return f"{v:.1f}x"
        
        # Moneda con sufijos
        if tipo in ("currency", "$"):
            sign = "-" if v < 0 else ""
            abs_v = abs(v)
            if abs_v >= 1e12:
                return f"{sign}${abs_v/1e12:.2f}T"
            elif abs_v >= 1e9:
                return f"{sign}${abs_v/1e9:.1f}B"
            elif abs_v >= 1e6:
                return f"{sign}${abs_v/1e6:.0f}M"
            else:
                return f"{sign}${abs_v:.2f}"
        
        # Número simple (default)
        return f"{v:.1f}"
    
    except (TypeError, ValueError):
        return na_text


def get_metric_color(val: Number, metric: str) -> str:
    """
    Retorna clase CSS de color basado en si el valor es bueno o malo.
    
    Args:
        val: Valor de la métrica
        metric: Nombre de la métrica (pe, roe, debt_equity, net_margin, score, fcf_yield, dividend_yield)
    
    Returns:
        Clase CSS: "text-success", "text-warning", "text-danger", o ""
    """
    if val is None:
        return ""
    
    try:
        # Métricas donde menor es mejor
        if metric == "pe":
            return "text-success" if val < 20 else "text-warning" if val < 30 else "text-danger"
        if metric == "debt_equity":
            return "text-success" if val < 0.5 else "text-warning" if val < 1.5 else "text-danger"
        
        # Métricas donde mayor es mejor (vienen como decimal, ej: 0.15 = 15%)
        if metric == "roe":
            return "text-success" if val > 0.15 else "text-warning" if val > 0.08 else "text-danger"
        if metric == "net_margin":
            return "text-success" if val > 0.15 else "text-warning" if val > 0.05 else "text-danger"
        if metric == "fcf_yield":
            return "text-success" if val > 0.05 else "text-warning" if val > 0.02 else "text-danger"
        if metric == "dividend_yield":
            return "text-success" if val > 0.03 else "text-warning" if val > 0.01 else ""
        
        # Score (0-100)
        if metric == "score":
            return "text-success" if val >= 70 else "text-warning" if val >= 50 else "text-danger"
        
    except (TypeError, ValueError):
        pass
    
    return ""
