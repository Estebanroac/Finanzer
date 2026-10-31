"""
F8 · E2 (auditoría externa del 26-oct-2026, NEE): bandera de pico de beneficio.

La detección de no recurrentes depende de las partidas que la fuente etiqueta; un beneficio TTM inflado por algo que no
se etiqueta (NEE: la valoración a mercado de sus coberturas, 11,64 mil millones TTM frente a 6,83 en FY2025) se trataba
como recurrente y el P/E salía «atractivo». Prueba estadística, con dos condiciones:

  (a) el beneficio TTM supera en más de `ttm_over_median` la mediana de los `median_years` últimos ejercicios;
  (b) el mercado tampoco cree en ese nivel: el forward P/E supera en más de `forward_premium` el P/E TTM (equivale a un
      BPA esperado más de un 17 % por debajo del TTM, así que cubre las dos formas de la auditoría).

Presupuesto 0: no hay consenso de pago. El forward P/E de Yahoo solo entra si es coherente con el resto: el beneficio
que implica no queda por debajo del menor entre el TTM y la mediana dividido por `forward_coherence_factor` (un error
de escala de la fuente activaría (b) por error). Si no lo es o no hay, la bandera se decide solo con (a) y se declara:
sin la segunda condición puede marcar un crecimiento genuino.

Con la bandera, el P/E del score es la media del P/E sobre la mediana de 3 años y el forward P/E (solo el primero sin
forward fiable), y el texto lo dice («beneficio TTM atípico»). Parámetros: config/valuation.toml [earnings_peak].
"""
from statistics import median
from typing import Any, Dict, List, Optional

from settings import cfg


def _pos(x: Optional[float]) -> bool:
    return x is not None and x > 0


def detect(*, ni_ttm: Optional[float], ni_reported: Optional[float], fy_net_income: List[Optional[float]],
           pe_score: Optional[float], pe_reported: Optional[float],
           forward_pe: Optional[float], period: str = "TTM") -> Optional[Dict[str, Any]]:
    """None sin datos con que medir; si no, {flag, conditions, ttm_over_median, median, forward, pe_median, pe_score,
    pe_ttm, basis, reason}.

    ni_ttm: el beneficio TTM con que se valora (normalizado si aplica); ni_reported y pe_reported: los reportados, con
    los que se compara el forward; fy_net_income: beneficio de los ejercicios completos, del más reciente al más
    antiguo; pe_score: el P/E que puntúa sin la bandera; period: el del beneficio («TTM» o «último ejercicio», sin 4
    trimestres consecutivos), para los textos."""
    C = cfg("valuation.earnings_peak")
    n = C["median_years"]
    fy = [v for v in (fy_net_income or [])[:n] if v is not None]
    if len(fy) < n or not _pos(ni_ttm) or not _pos(pe_score):
        return None
    med = median(fy)
    if med <= 0:
        return None
    over = ni_ttm / med - 1
    cond_a = over > C["ttm_over_median"]
    fwd = {"pe": forward_pe, "coherent": False, "reason": None, "premium": None}
    if not _pos(forward_pe):
        fwd["reason"] = "sin forward P/E de la fuente"
    elif not (_pos(pe_reported) and _pos(ni_reported)):
        fwd["reason"] = "sin P/E reportado con que compararlo"
    else:
        implied = ni_reported * pe_reported / forward_pe          # beneficio que implica el forward
        k = C["forward_coherence_factor"]
        lo = min(med, ni_ttm) / k
        fwd["premium"] = forward_pe / pe_reported - 1
        # Solo el lado que puede activar (b) por error: un forward que implica muchísimo menos beneficio (error de
        # escala). Uno que implica más nunca pone la bandera (MU: 3,2 veces el BPA TTM en el ciclo de memoria).
        if implied >= lo:
            fwd["coherent"] = True
        else:
            fwd["reason"] = (f"el beneficio que implica el forward P/E ({implied / 1e9:.2f} mil millones) queda por "
                             f"debajo de {lo / 1e9:.2f}, un tercio del menor entre el TTM y la mediana")
    cond_b = (fwd["premium"] > C["forward_premium"]) if fwd["coherent"] else None
    flag = bool(cond_a and (cond_b if fwd["coherent"] else True))
    pe_median = pe_score * ni_ttm / med
    out = {"flag": flag, "conditions": {"a": cond_a, "b": cond_b}, "ttm_over_median": over, "median": med,
           "years": n, "forward": fwd, "pe_ttm": pe_score, "pe_median": pe_median, "pe_score": None,
           "period": period, "basis": None, "reason": None}
    if not flag:
        return out
    if fwd["coherent"]:
        out["pe_score"] = (pe_median + forward_pe) / 2
        out["basis"] = "media del P/E sobre la mediana de 3 ejercicios y el forward P/E"
        why = (f"supera en un {over:.0%} la mediana de los {n} últimos ejercicios y el forward P/E ({forward_pe:.1f}x) "
               f"es un {fwd['premium']:.0%} mayor que el {period}: el mercado tampoco cree en ese nivel")
    else:
        out["pe_score"] = pe_median
        out["basis"] = "P/E sobre la mediana de 3 ejercicios (sin forward fiable: solo la primera condición)"
        why = (f"supera en un {over:.0%} la mediana de los {n} últimos ejercicios; sin forward fiable "
               f"({fwd['reason']}) la bandera se decide solo con esa condición y puede marcar un crecimiento genuino")
    out["reason"] = (f"beneficio {'del ' if period != 'TTM' else ''}{period} atípico: {why}. El P/E que puntúa es "
                     f"{out['pe_score']:.1f}x ({out['basis']})")
    return out
