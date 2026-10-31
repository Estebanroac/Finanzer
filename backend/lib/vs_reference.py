"""
F10 · B3 (escaneo del modelo general, `alertas_coherentes`): la lectura de una métrica frente a su referencia (la
industria de Damodaran sin la propia empresa, main._select_benchmark), en un solo sitio. La usan la fila de la tabla
(display.read_vs_sector) y la alerta de la misma métrica (alert_interpretations): las dos leen el mismo resultado; una
fortaleza nunca acompaña a una fila en rojo, ni un aviso a una en verde.

Bandas: `thresholds.pdf.vs_sector_bounds` (±35 % / ±10 % de brecha frente a la referencia).
"""
from typing import Optional, Tuple

from settings import cfg


def band(val: Optional[float], bench: Optional[float], higher_better: bool,
         level: bool = False) -> Optional[Tuple[str, str, float]]:
    """(lectura, tono, brecha en %) o None sin cifra o sin referencia. Tono: 'pos', 'neu', 'warn' o 'neg'.
    `level`: una métrica de nivel en la que menos es mejor (la deuda), no un múltiplo de precio."""
    if val is None or bench in (None, 0):
        return None
    diff = (val - bench) / abs(bench) * 100
    b = cfg("thresholds.pdf.vs_sector_bounds")
    if higher_better:
        if diff >= b[0]:   lab, tone = "Muy superior", 'pos'
        elif diff >= b[1]: lab, tone = "Superior", 'pos'
        elif diff > -b[1]: lab, tone = "En línea", 'neu'
        elif diff > -b[0]: lab, tone = "Inferior", 'warn'
        else:              lab, tone = "Muy inferior", 'neg'
    elif level:
        if diff <= -b[0]:   lab, tone = "Muy por debajo", 'pos'
        elif diff <= -b[1]: lab, tone = "Por debajo", 'pos'
        elif diff < b[1]:   lab, tone = "En línea", 'neu'
        elif diff < b[0]:   lab, tone = "Por encima", 'warn'
        else:               lab, tone = "Muy por encima", 'neg'
    else:
        if diff <= -b[0]:   lab, tone = "Descuento profundo", 'pos'
        elif diff <= -b[1]: lab, tone = "Descuento", 'pos'
        elif diff < b[1]:   lab, tone = "En línea", 'neu'
        elif diff < b[0]:   lab, tone = "Prima moderada", 'warn'
        else:               lab, tone = "Prima elevada", 'neg'
    return lab, tone, diff
