"""
Formato de cifras de los textos del informe y de la web (etapa 9b).

Una sola forma de escribir importes: el signo va antes del símbolo y con el
signo menos tipográfico ("−$147.78B", no "$-147.78B"), las series en miles de
millones no se redondean a enteros y los importes por acción llevan dos
decimales ("−$1.10 por acción").
"""
import contextlib
import contextvars
from typing import Optional

MINUS = "−"
# Fiabilidad (V4 · moneda): la moneda de los importes que se formatean. El análisis fija la de su precio (la de la
# capitalización, la variación del día y los estados, que se convierten a ella); fuera de un análisis, USD. En USD se
# escribe "$"; en otra, su código delante, como la cabecera de /v2 ("EUR 397.00", "−EUR 1.10", "EUR 45.18B").
_CURRENCY: contextvars.ContextVar = contextvars.ContextVar("numfmt_currency", default=None)
# Escalera de NFLX (30-oct): el margen EBITDA del análisis, para el motivo de un EV/EBITDA acotado (ev_ebitda_detail).
_EBITDA_MARGIN: contextvars.ContextVar = contextvars.ContextVar("numfmt_ebitda_margin", default=None)


@contextlib.contextmanager
def currency(code: Optional[str]):
    """Los importes formateados dentro del bloque van en `code` (None o "USD": "$"); el margen EBITDA del análisis,
    también solo dentro del bloque."""
    token, mtoken = _CURRENCY.set(code), _EBITDA_MARGIN.set(None)
    try:
        yield
    finally:
        _CURRENCY.reset(token)
        _EBITDA_MARGIN.reset(mtoken)


def set_ebitda_margin(m: Optional[float]) -> None:
    """Fija el margen EBITDA del análisis (main._compute_analysis y display.build_display)."""
    _EBITDA_MARGIN.set(m)


def set_currency(code: Optional[str]) -> None:
    """Fija la moneda hasta que el `currency()` que la envuelve termine (main._compute_analysis)."""
    _CURRENCY.set(code)


def symbol(cur: Optional[str] = None) -> str:
    """"$" en USD; si no, el código de la moneda y un espacio. `cur` manda sobre la moneda del contexto."""
    code = cur or _CURRENCY.get()
    return "$" if code in (None, "", "USD") else f"{code} "
_UNITS = ((1e12, "T"), (1e9, "B"), (1e6, "M"))
PER_SHARE_MAX = 1e4   # por debajo, una serie de importes es por acción (BPA, FCF por acción…)


def _sign(v: float) -> str:
    return MINUS if v < 0 else ""


def money(v: Optional[float], cur: Optional[str] = None) -> str:
    """Importe total con unidad: $45.18B, −$147.78B, $869.41M (EUR 45.18B en euros)."""
    if v is None:
        return "N/A"
    a, sym = abs(v), symbol(cur)
    for div, suffix in _UNITS:
        if a >= div:
            return f"{_sign(v)}{sym}{a / div:.2f}{suffix}"
    return f"{_sign(v)}{sym}{a:,.0f}"


def price(v: Optional[float], cur: Optional[str] = None) -> str:
    """Precio o importe por acción: $368.89, −$1.10 (EUR 397.00 en euros)."""
    if v is None:
        return "N/A"
    return f"{_sign(v)}{symbol(cur)}{abs(v):,.2f}"


def whole(v: Optional[float], cur: Optional[str] = None) -> str:
    """Importe por acción redondeado a la unidad: $142, −$8, "—" sin dato."""
    if v is None:
        return "—"
    r = round(v)
    return f"{_sign(r)}{symbol(cur)}{abs(r):,.0f}"


def estimate(v: Optional[float], cur: Optional[str] = None) -> str:
    """F8 · P3: un valor estimado (el valor justo de un modelo) a dos cifras significativas, sin falsa precisión:
    $116.08 → $120, $7.13 → $7.1, EUR 403.87 → EUR 400. "—" sin dato."""
    if v is None:
        return "—"
    if v == 0:
        return f"{symbol(cur)}0"
    import math
    d = math.floor(math.log10(abs(v)))
    r = round(v, 1 - d)
    dec = max(0, 1 - d)
    return f"{_sign(r)}{symbol(cur)}{abs(r):,.{dec}f}"


def ev_ebitda(v: float, dec: int = 2) -> str:
    """EV/EBITDA con un EBITDA casi nulo (TTWO: 1035,7x), por encima de `thresholds.multiples_display.ev_ebitda_shown_max`:
    «> 100x», como el margen de seguridad (numfmt de la revisión de COST); la cifra exacta va en el detalle
    (ev_ebitda_detail). Solo cómo se muestra: la puntuación no cambia."""
    from settings import cfg
    mx = cfg("thresholds.multiples_display.ev_ebitda_shown_max")
    return f"> {mx:g}x" if v > mx else f"{v:.{dec}f}x"


def ev_ebitda_detail(v: Optional[float], margin: Optional[float] = None, use_context: bool = True) -> Optional[str]:
    """El detalle del EV/EBITDA acotado (ev_ebitda): la cifra exacta y su motivo; None si se muestra entero. El motivo,
    con el margen EBITDA: «EBITDA casi nulo» si no llega a la materialidad de N1
    (`thresholds.normalization.nonoperating_tolerance_revenue` de los ingresos: TTWO 0,5 %, CRWD), «múltiplo extremo» si
    la pasa (PLTR: 177,8x con un EBITDA que no es casi nulo); sin el margen (ni el del análisis, set_ebitda_margin), solo
    la cifra. `use_context=False`: un múltiplo sobre otro EBITDA (el normalizado de una cíclica), sin el margen del TTM."""
    from settings import cfg
    if v is None or v <= cfg("thresholds.multiples_display.ev_ebitda_shown_max"):
        return None
    margin = margin if (margin is not None or not use_context) else _EBITDA_MARGIN.get()
    if margin is None:
        return f"cifra exacta {v:.1f}x"
    if margin <= cfg("thresholds.normalization.nonoperating_tolerance_revenue"):
        return f"cifra exacta {v:.1f}x: EBITDA casi nulo ({margin:.1%} de los ingresos)"
    return f"cifra exacta {v:.1f}x: múltiplo extremo"


def amount(v: Optional[float], cur: Optional[str] = None) -> str:
    """Importe de una serie de los estados: total con unidad o, si es pequeño, por acción."""
    if v is None:
        return "N/A"
    return money(v, cur) if abs(v) >= PER_SHARE_MAX else f"{price(v, cur)} por acción"


def signed_pct(v: Optional[float], dec: int = 0) -> str:
    """Porcentaje (ya en %) con signo explícito: +45%, −33%."""
    if v is None:
        return "N/A"
    s = "+" if v > 0 else (MINUS if v < 0 else "")
    return f"{s}{abs(v):.{dec}f}%"


def pp(v: Optional[float], dec: int = 1) -> str:
    """Rediseño E2a: diferencia entre dos porcentajes, en puntos porcentuales (0.884 → "+88.4 pp", −0.02 → "−2.0 pp")."""
    if v is None:
        return "—"
    s = "+" if v > 0 else (MINUS if v < 0 else "")
    return f"{s}{abs(v) * 100:.{dec}f} pp"


MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre")


def date_long(iso: Optional[str]) -> str:
    """'2026-10-13' → '13 de octubre de 2026' (fase 2b: fechas de los avisos)."""
    if not iso:
        return "—"
    y, m, d = (int(x) for x in str(iso)[:10].split("-"))
    return f"{d} de {MESES[m - 1]} de {y}"


def period(basis: Optional[str], normalized: bool = False) -> str:
    """V7 (M2): el periodo de un ratio, para escribirlo junto a la cifra: 'TTM' (4 trimestres) o 'último ejercicio'
    (sin 4 trimestres consecutivos); con el beneficio normalizado, 'TTM, sin partidas no recurrentes'."""
    p = "último ejercicio" if basis == "anual" else "TTM"
    return f"{p}, sin partidas no recurrentes" if normalized else p
