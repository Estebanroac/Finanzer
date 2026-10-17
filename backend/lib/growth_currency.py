"""
Crecimiento en la moneda de los estados (fase 3, T1b; F3_T1_PARADA1 §3, aprobado en el registro #25).

Un ADR presenta sus estados en su moneda (EUR, DKK, TWD, JPY, GBP) y el motor los convierte a la del precio (USD) con
lib/currency: los flujos de cada ejercicio, al promedio de sus cierres diarios. Medido en dólares, el crecimiento
incluye el tipo de cambio: UL crece +0.5% en USD y −3.8% en EUR (F2b_PARADA2 §6). La práctica estándar es medir el
crecimiento operativo sin el tipo de cambio (las empresas lo publican "a tipo constante" o "subyacente") y declarar
aparte el efecto divisa.

`local(st, currency)` deshace la conversión de las filas anuales de importes con los mismos tipos que usó
lib/currency (data_provenance.currency.rates, por fecha de cierre); las ratios (márgenes, por acción con acciones de
la misma clase) no cambian. El motor mide con ellas el crecimiento (interanual, CAGR, ciclo medio) y sigue valorando
en dólares: proyectar en dólares con el crecimiento local equivale a proyectar en la moneda local y convertir al
contado (el supuesto es que el tipo de cambio no tiene tendencia; F3_T1_PARADA1 §3).
"""
import copy
from typing import Any, Dict, List, Optional

# Filas anuales de importes (flujos del ejercicio) que entran en el crecimiento. Por estado de origen: el tipo es el
# del promedio del ejercicio (income_stmt y cashflow usan el mismo).
_FLOW_ROWS = {
    "inc": ("revenue", "gross_profit", "operating_income", "ebit", "ebitda", "net_income", "net_income_common",
            "diluted_eps"),
    "cf": ("operating_cash_flow", "capital_expenditure", "free_cash_flow", "depreciation_amortization",
           "stock_based_compensation"),
}
_RATE_KEYS = {"inc": "income_stmt", "cf": "cashflow"}


def converted(currency: Optional[Dict[str, Any]]) -> bool:
    c = currency or {}
    return bool(c.get("converted")) and bool(c.get("rates"))


def local(st: Optional[Dict[str, Any]], currency: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Copia de las filas anuales con los importes en la moneda de los estados (o las mismas si no se convirtieron).
    Un ejercicio sin tipo registrado queda sin dato: nunca se mezcla un importe convertido con uno sin convertir."""
    st = st or {}
    if not converted(currency):
        return st
    out = copy.deepcopy(st)
    rates_by = currency["rates"]
    for stmt, rows in _FLOW_ROWS.items():
        ends: List[str] = st.get(f"{stmt}_ends") or []
        rates = rates_by.get(_RATE_KEYS[stmt]) or {}
        for row in rows:
            vals = st.get(row)
            if not isinstance(vals, list):
                continue
            new = []
            for i, v in enumerate(vals):
                r = rates.get(ends[i]) if i < len(ends) else None
                new.append(None if v is None or not r else v / r)
            out[row] = new
    out["_currency_basis"] = currency.get("statements")
    return out


def fx_effect(usd: Optional[float], loc: Optional[float]) -> Optional[float]:
    """Efecto divisa en un crecimiento: el medido en la moneda del precio menos el de la moneda de los estados."""
    if usd is None or loc is None:
        return None
    return usd - loc


def yoy(values: Optional[List[Optional[float]]]) -> Optional[float]:
    """Crecimiento del último ejercicio (FY0 frente a FY1) de una serie anual, más reciente primero."""
    v = values or []
    if len(v) < 2 or v[0] is None or v[1] is None or v[1] <= 0:
        return None
    return v[0] / v[1] - 1.0
