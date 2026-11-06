"""
Fase 7 / F13 (paso 1): estado de la revisión de un parámetro de mercado (config/review.toml), con su próxima fecha.

Lo usan la herramienta `tests/revision_parametros.py` (informe de todos) y el motor en ejecución
(`cost_of_capital.capm_rates`: el par Rf–ERP vencido se avisa en el análisis). Antes (hasta F13) solo lo veía la
herramienta, y la revisión del 1-nov-2026 venció sin que nada lo dijera.

Estados:
  · "vigente": aún no ha llegado la próxima publicación esperada (fecha del dato + cadencia; si la consulta fue
    posterior a esa fecha, no había otra más nueva y cuenta desde la consulta);
  · "revisar": ya debería haber una más reciente en la fuente;
  · "sin fuente": PROVISIONAL, fijado a mano (no hay fecha que vigilar; hay que sustituirlo);
  · "vigente, dato antiguo": no hay otro más nuevo, pero el que hay tiene más de una cadencia y media.
"""
import datetime as _dt
from typing import Any, Dict, Optional, Tuple

from settings import cfg


def _plus(d: _dt.date, cadence_days: int) -> _dt.date:
    # cadencias de meses en meses de calendario (revisión de F7, hallazgo 10: 31 días desde el 1 de noviembre caían el
    # 2 de diciembre y se iban desplazando)
    months = round(cadence_days / 30.44)
    if 1 <= months <= 12 and abs(months * 30.44 - cadence_days) <= 3:
        y, m = divmod(d.month - 1 + months, 12)
        return d.replace(year=d.year + y, month=m + 1, day=min(d.day, 28))
    return d + _dt.timedelta(days=cadence_days)


def status(item: Dict[str, Any], today: _dt.date) -> Tuple[str, Optional[_dt.date]]:
    """(estado, próxima fecha esperada o None) de una fila de config/review.toml."""
    if not item["consulted"]:
        return "sin fuente", None
    consulted = _dt.date.fromisoformat(item["consulted"])
    base = _dt.date.fromisoformat(item["published"]) if item["published"] else consulted
    # Si se consultó después de la publicación esperada, se miró y no había otra más nueva: cuenta desde la consulta.
    if consulted >= _plus(base, item["cadence_days"]):
        base = consulted
    due = _plus(base, item["cadence_days"])
    st = "revisar" if today >= due else "vigente"
    # un dato de la fuente con más de una cadencia y media de antigüedad se marca aunque no haya otro (EV/EBITDA a 1T-2025)
    if st == "vigente" and item["published"] and \
            (today - _dt.date.fromisoformat(item["published"])).days > 1.5 * item["cadence_days"]:
        st = "vigente, dato antiguo"
    return st, due


def parameter(name: str, today: _dt.date) -> Dict[str, Any]:
    """{status, due, published} de un parámetro por su nombre en review.toml."""
    it = cfg("review.parameters")[name]
    st, due = status(it, today)
    return {"status": st, "due": due.isoformat() if due else None, "published": it["published"] or None}
