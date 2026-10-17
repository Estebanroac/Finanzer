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


def test_base_le_zero_is_not_significant_and_category_stays():
    # AMZN: BPA y FCF del año base <= 0 -> no significativos; la categoría se mide con los ingresos.
    r = score_crecimiento(0.117, None, None, archetype=MATURE, eps_reason="BPA inicial <= 0: CAGR no definido",
                          fcf_growth_reason="FCF inicial <= 0: CAGR no definido")
    c = r["coverage"]
    assert c["conclusive"] and c["coverage"] == 1.0 and set(c["not_significant"]) == {"Crecimiento del BPA",
                                                                                       "Crecimiento del FCF"}
    # Sin dato por otra causa sigue siendo dato ausente.
    r = score_crecimiento(0.117, None, None, archetype=MATURE, eps_reason="sin 4 ejercicios",
                          fcf_growth_reason="sin 4 ejercicios")
    assert not r["coverage"]["conclusive"]
