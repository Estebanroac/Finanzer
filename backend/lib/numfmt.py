"""
Formato de cifras de los textos del informe y de la web (etapa 9b).

Una sola forma de escribir importes: el signo va antes del símbolo y con el
signo menos tipográfico ("−$147.78B", no "$-147.78B"), las series en miles de
millones no se redondean a enteros y los importes por acción llevan dos
decimales ("−$1.10 por acción").
"""
from typing import Optional

MINUS = "−"
_UNITS = ((1e12, "T"), (1e9, "B"), (1e6, "M"))
PER_SHARE_MAX = 1e4   # por debajo, una serie de importes es por acción (BPA, FCF por acción…)


def _sign(v: float) -> str:
    return MINUS if v < 0 else ""


def money(v: Optional[float]) -> str:
    """Importe total con unidad: $45.18B, −$147.78B, $869.41M."""
    if v is None:
        return "N/A"
    a = abs(v)
    for div, suffix in _UNITS:
        if a >= div:
            return f"{_sign(v)}${a / div:.2f}{suffix}"
    return f"{_sign(v)}${a:,.0f}"


def price(v: Optional[float]) -> str:
    """Precio o importe por acción: $368.89, −$1.10."""
    if v is None:
        return "N/A"
    return f"{_sign(v)}${abs(v):,.2f}"


def whole(v: Optional[float]) -> str:
    """Importe por acción redondeado al dólar (celdas del grid de sensibilidad): $142, −$8, "—" sin dato."""
    if v is None:
        return "—"
    r = round(v)
    return f"{_sign(r)}${abs(r):,.0f}"


def amount(v: Optional[float]) -> str:
    """Importe de una serie de los estados: total con unidad o, si es pequeño, por acción."""
    if v is None:
        return "N/A"
    return money(v) if abs(v) >= PER_SHARE_MAX else f"{price(v)} por acción"


def signed_pct(v: Optional[float], dec: int = 0) -> str:
    """Porcentaje (ya en %) con signo explícito: +45%, −33%."""
    if v is None:
        return "N/A"
    s = "+" if v > 0 else (MINUS if v < 0 else "")
    return f"{s}{abs(v):.{dec}f}%"
