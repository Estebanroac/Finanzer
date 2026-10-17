"""Fase 3 (T5, F3_DISENO §4): crecimiento por modelo de negocio."""
from classify import GROWTH_PROFITABLE, MATURE
from financial_ratios import score_crecimiento
from settings import cfg


def _rev(r):
    return next(a for a in r["adjustments"] if a["metric"].startswith(("Crecimiento Ingresos", "Retorno total")))


def test_high_dividend_mature_growth_is_total_return():
    T = cfg("thresholds.score.crecimiento")
    y = T["mature_total_return_min_yield"]
    r = score_crecimiento(0.01, 0.02, 0.02, archetype=MATURE, dividend_yield=y + 0.01)
    a = _rev(r)
    assert a["metric"] == "Retorno total (dividendo + ingresos por acción)"
    assert abs(a["raw"] - (y + 0.02)) < 1e-12 and "rentabilidad por dividendo" in a["reason"]
    # Por debajo del umbral, o fuera de MATURE, sigue siendo crecimiento de ingresos.
    assert _rev(score_crecimiento(0.01, 0.02, 0.02, archetype=MATURE, dividend_yield=y - 0.01))["metric"] == \
        "Crecimiento Ingresos 3Y"
    assert _rev(score_crecimiento(0.01, 0.02, 0.02, archetype=GROWTH_PROFITABLE, dividend_yield=y + 0.01))[
        "metric"] == "Crecimiento Ingresos 3Y"
