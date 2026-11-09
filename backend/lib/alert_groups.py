"""
Fase 1 · pendientes de la prueba hacia atrás (decisión del usuario, 7-nov-2026): una sola alerta roja.

Versión 1.0 (decisión del usuario, 8-nov-2026): esa alerta se RETIRA. En el segundo corte (5-nov-2024) no se confirmó:
las que la tenían cayeron un 40 % o más menos que el resto (11,1 % frente a 17,6 %), y con los dos cortes juntos el
cociente (× 1,37) no llega al × 1,5 fijado. Desde aquí `red_flags` queda vacío y la valoración extrema es la primera
línea de la «Lectura de valoración», sin color, con la evidencia de los dos cortes. Lo de abajo describe la Fase 1.

La prueba hacia atrás (corte 5-nov-2025) mostró que las alertas rojas del motor no anticipan caídas mejor que la tasa
de partida, salvo una: la valoración del motor anterior en «muy exigente» (control: 34,7 % de caídas ≥ 40 % en los 12
meses siguientes frente al 14,9 % del resto). Desde aquí:

  · red_flags  = solo «Riesgo de caída fuerte por valoración extrema», con la lectura de valoración del motor anterior
                 (`price_attractiveness.valuation_reading`, la que se sigue calculando en paralelo) en «muy exigente».
  · balance    = «Estado del balance», sin color de alerta: Altman, EBIT < 0 y cobertura crítica, caja libre negativa,
                 apalancamiento, destrucción de valor, márgenes y ROE negativos (las rojas de esos tipos y las
                 advertencias de apalancamiento).
  · valuation  = «Lectura de valoración», sin color: las de las categorías Valoración y Valor intrínseco (el precio
                 lo decide la regla L1; el DCF y los múltiplos son lectura).
  · warnings y strengths, como estaban; una roja que no encaje en ninguno de los dos grupos pasa a advertencia.

Parámetros y evidencia: config/thresholds.toml [alerts.valuation_extreme].
"""
import re
from typing import Any, Dict, List, Optional

from settings import cfg

GROUPS = ("red_flags", "warnings", "strengths", "balance", "valuation")
VALUATION_CATEGORIES = ("Valoración", "Valor intrínseco")
# Titulares (inicio del `reason` de alert_interpretations) que son estado del balance.
_BALANCE = re.compile(
    r"^(Riesgo de insolvencia|Debilidad financiera|Cobertura de intereses (negativa|crítica)|Flujo de caja libre "
    r"negativo|Apalancamiento elevado|Destruye valor|Margen (neto|operativo)( normalizado)? negativo|"
    r"ROE( normalizado)? negativo)")
EXTREME_LEVEL = "muy exigente"
# Cierre de la 1.0 (9-nov-2026): un solo P/E en el informe, el normalizado de doce meses de la regla L1. Las señales del
# P/E del motor anterior («Valoración exigente — P/E normalizado 50.4x», «Cotiza con descuento — P/E 12.0x»…) lo
# repetían con otra cifra: no entran en la lectura de valoración.
_PE_SIGNAL = re.compile(r" — P/E\b")


def is_pe_signal(x: Dict[str, Any]) -> bool:
    return is_valuation(x) and bool(_PE_SIGNAL.search(x.get("reason") or ""))


def is_balance(x: Dict[str, Any]) -> bool:
    return bool(_BALANCE.match(x.get("reason") or ""))


def is_valuation(x: Dict[str, Any]) -> bool:
    return (x.get("category") or "") in VALUATION_CATEGORIES


def _pct(x: float) -> str:
    return f"{x * 100:.1f}".replace(".", ",") + " %"


def extreme_valuation(reading: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Versión 1.0: la lectura (sin color) si la valoración del motor anterior cae en «muy exigente»; None si no."""
    r = reading or {}
    if r.get("level") != EXTREME_LEVEL:
        return None
    C = cfg("thresholds.alerts.valuation_extreme")
    # Cierre de la 1.0 (9-nov-2026): sin número de 0 a 100; la única nota de precio es la de la regla L1
    return {"category": "Valoración", "reason": "Valoración extrema según múltiplos y DCF",
            "detail": (f"La valoración por múltiplos y DCF, que se calcula como lectura, la sitúa en "
                       f"«{EXTREME_LEVEL}». En la prueba hacia atrás ({C['sample']}), el {_pct(C['rate'])} de las "
                       f"que estaban en ese nivel ({C['hits']} de {C['n']}) cayó un {C['drawdown'] * 100:.0f} % o más "
                       f"en algún momento de los {C['horizon_months']} meses siguientes, frente al "
                       f"{_pct(C['base_rate'])} del resto; en el corte de 2024 cayeron menos que el resto. No anticipa "
                       f"caídas: es una lectura, no una alerta."),
            "evidence": {k: C[k] for k in ("rate", "base_rate", "hits", "n", "drawdown", "horizon_months", "sample")}}


def regroup(alerts: Optional[Dict[str, Any]], price: Optional[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Las alertas de build_signals (ya en sus grupos) con la alerta roja de valoración extrema. Acepta también el
    formato anterior de tres grupos (por si llega de otra ruta): lo reparte con las mismas reglas."""
    al = alerts or {}
    out: Dict[str, List[Dict[str, Any]]] = {k: list(al.get(k) or []) for k in GROUPS}
    out["red_flags"], out["warnings"] = [], []
    for k in ("red_flags", "warnings"):
        for x in al.get(k) or []:
            (out["valuation"] if is_valuation(x) else out["balance"] if is_balance(x) else out["warnings"]).append(x)
    out["valuation"] += [x for x in out["strengths"] if is_valuation(x)]
    out["strengths"] = [x for x in out["strengths"] if not is_valuation(x)]
    if (price or {}).get("rule") == "L1":
        out["valuation"] = [x for x in out["valuation"] if not is_pe_signal(x)]
    ext = extreme_valuation((price or {}).get("valuation_reading"))
    if ext:
        out["valuation"].insert(0, ext)        # versión 1.0: la primera de la lectura de valoración, sin color
    return out
