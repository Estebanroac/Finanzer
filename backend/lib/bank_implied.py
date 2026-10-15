"""
ROTE y ROE implícitos en el precio de un banco (preparación de la fase 3; F3_DISENO_METODO §3).

Es la inversa del múltiplo justificado que ya usa el motor (archetype_metrics.justified_multiple):
    P/TBV = (ROTE − g) / (Ke − g)   ⇒   ROTE implícito = P/TBV × (Ke − g) + g
Con el P/TBV justificado del motor, devuelve exactamente el ROTE que usó el motor. Igual con P/B y ROE.

NO está conectado al motor: ningún módulo lo importa todavía. Sin cifra inventada: Ke ≤ g o múltiplo ≤ 0 devuelven
`no_aplica` con su motivo. La sensibilidad lee sus pasos de config/valuation.toml [bank_implied].
"""
from typing import Any, Dict, Optional, Sequence

from archetype_metrics import justified_multiple
from settings import cfg

OK, NOT_APPLICABLE = "ok", "no_aplica"


def _implied_return(multiple: Optional[float], ke: Optional[float], g: Optional[float],
                    label: str) -> Dict[str, Any]:
    out = {"state": OK, "reason": None, "value": None, "multiple": multiple, "ke": ke, "g": g}
    if ke is None or g is None:
        return dict(out, state=NOT_APPLICABLE, reason="sin coste del capital (Ke) o sin crecimiento terminal")
    if ke <= g:
        return dict(out, state=NOT_APPLICABLE, reason="Ke ≤ g: el múltiplo justificado (Gordon) no está definido")
    if multiple is None or multiple <= 0:
        return dict(out, state=NOT_APPLICABLE, reason=f"{label} sin dato o ≤ 0: no hay retorno que despejar")
    return dict(out, value=multiple * (ke - g) + g)


def implied_rote(p_tbv: Optional[float], ke: Optional[float], g: Optional[float]) -> Dict[str, Any]:
    """ROTE sostenido que descuenta el precio: P/TBV × (Ke − g) + g."""
    return _implied_return(p_tbv, ke, g, "P/TBV")


def implied_roe(p_b: Optional[float], ke: Optional[float], g: Optional[float]) -> Dict[str, Any]:
    """ROE sostenido que descuenta el precio: P/B × (Ke − g) + g."""
    return _implied_return(p_b, ke, g, "P/B")


def rote_sensitivity(p_tbv: Optional[float], ke: Optional[float], g: Optional[float],
                     deltas_pp: Optional[Sequence[float]] = None,
                     rote_center: Optional[float] = None) -> Dict[str, Any]:
    """P/TBV justificado para ROTE = centro ± deltas (en tanto por uno: 0.02 = 2 pp).

    El centro es el ROTE implícito, salvo que se pase otro (p. ej. el ROTE del banco). Cada fila da el ROTE y el
    P/TBV justificado (None si ROTE ≤ g: el modelo de Gordon no da múltiplo positivo), para frases como
    "con un ROTE del 12% se justificaría 1.1x".
    """
    base = implied_rote(p_tbv, ke, g)
    deltas = cfg("valuation.bank_implied.rote_sensitivity_deltas") if deltas_pp is None else deltas_pp
    out = {"state": base["state"], "reason": base["reason"], "implied_rote": base["value"], "rows": []}
    if base["state"] != OK:
        return out
    center = base["value"] if rote_center is None else rote_center
    out["center"] = center
    out["rows"] = [{"delta": d, "rote": center + d, "ptbv_justified": justified_multiple(center + d, ke, g)}
                   for d in deltas]
    return out
