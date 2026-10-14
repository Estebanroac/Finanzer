"""
Fase 0 del plan de fiabilidad: los invariantes GENÉRICOS (invariants.py) sobre los 31 tickers del panel.

Un test por (invariante, ticker). Lo que hoy falla está en PANEL_KNOWN_FAILURES con su motivo y entra en la
suite como xfail ESTRICTO: si se arregla, XPASS rompe la suite a propósito y hay que quitar la entrada. Esa
tabla es el inventario de F3 en código (docs/fiabilidad/F0_LINEA_BASE.md). Sin red; no toca el motor.
Los tests ATADOS a los 6 tickers de local/prod no se corren aquí.
"""
import pytest

import fixture_backend as fb
import invariants as inv

pytestmark = pytest.mark.skipif(not fb.panel_available(), reason="sin fixtures del panel")

# (invariante, ticker) -> motivo. Rellenado con la captura del panel del 2026-10-14.
_CYCLE_FLOOR = ("la intro dice 'se contraen un 5.0% anual de ciclo medio' y el invariante busca '-5.0%' literal "
                "(probable falso positivo del invariante con crecimientos negativos, por decidir); además el -5.0% "
                "de ingresos y BPA es la cota inferior del ciclo medio [-5%, 10%] presentada como dato medido")
PANEL_KNOWN_FAILURES = {
    ("growth_texts_cite_the_scored_figure", "XOM"): _CYCLE_FLOOR,
    ("growth_texts_cite_the_scored_figure", "DOW"): _CYCLE_FLOOR,
}

REJECTED = {"SPY"}   # el backend lo rechaza (422): no hay análisis que comprobar


def _params():
    out = []
    for name in inv.GENERIC:
        for sym in fb.PANEL_TICKERS:
            if sym in REJECTED:
                continue
            reason = PANEL_KNOWN_FAILURES.get((name, sym))
            marks = [pytest.mark.xfail(strict=True, raises=AssertionError, reason=reason)] if reason else []
            out.append(pytest.param(name, sym, marks=marks, id=f"{name}-{sym}"))
    return out


@pytest.mark.parametrize("name,sym", _params())
def test_generic_invariant_on_panel(name, sym, outputs_by_env):
    a, pdf = outputs_by_env(fb.PANEL_ENV)[sym]
    inv.GENERIC[name](a, fb.pdf_text(pdf))


def test_known_failures_table_is_well_formed():
    for (name, sym), reason in PANEL_KNOWN_FAILURES.items():
        assert name in inv.GENERIC and sym in fb.PANEL_TICKERS and reason, (name, sym)


def test_rejected_tickers_are_rejected(outputs_by_env):
    for sym in REJECTED:
        a, pdf = outputs_by_env(fb.PANEL_ENV)[sym]
        assert a.get("__http_error__") == 422 and pdf is None, sym
