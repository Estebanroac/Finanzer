"""
F8 · E9 (auditoría externa del 26-oct-2026, §3 E9): la rentabilidad no ignora el capital invertido.

- el diferencial ROIC − WACC manda: < 0, Rentabilidad con tope de 10/20; < −3 pp, de 6/20;
- márgenes frente a los de su industria de Damodaran (agregado: sin percentil con datos gratuitos), no absolutos;
- con un D/E por encima del umbral del sector, el ROE (inflado por el apalancamiento) cede su sitio al ROIC.
"""
import pytest

import financial_ratios as fr
from settings import cfg

BASE = dict(sector_roe_threshold=0.10, sector_roa_threshold=0.04, sector_roe_high=0.15, sector_roa_high=0.08)


def _r(**kw):
    args = dict(roe=0.188, roa=0.047, operating_margin=0.30, net_margin=0.40, roic=0.046, wacc=0.083, **BASE)
    args.update(kw)
    return fr.score_rentabilidad(**args)


def _adj(r, name):
    return next((x for x in r["adjustments"] if x["metric"].startswith(name)), None)


def test_spread_below_minus_3pp_caps_at_6():
    """NEE (26-oct): ROIC 4,6 % y WACC 8,3 % (−3,8 pp) con Rentabilidad 20/20."""
    r = _r()
    assert r["score"] == 6 and _adj(r, "Tope por ROIC − WACC")["cap"] and "6/20" in _adj(r, "Tope")["value"]


def test_negative_spread_caps_at_10_and_positive_does_not_cap():
    assert _r(roic=0.056, wacc=0.065)["score"] <= 10                     # AWK: −0,9 pp
    r = _r(roic=0.20, wacc=0.08)
    assert _adj(r, "Tope") is None and r["score"] > 10


def test_no_cap_without_wacc():
    assert _adj(_r(wacc=None), "Tope") is None                           # financieras: WACC no interpretable


def test_margins_are_read_against_the_industry_in_points():
    """En puntos porcentuales frente al agregado de la industria (ajuste del PM): NEE 30 % en Power (21,5 %) son +8,5 pp."""
    rel = _r(roic=0.2, industry_operating_margin=0.2147, industry_net_margin=0.1273)
    m = _adj(rel, "Margen operativo")
    assert m["adjustment"] == cfg("thresholds.score.rentabilidad.operating_margin_points")[1]
    assert "+8.5 pp frente al margen de su industria" in m["reason"]
    absolute = _adj(_r(roic=0.2), "Margen operativo")
    assert absolute["adjustment"] == 5 and "bandas absolutas" in absolute["reason"]
    assert _adj(_r(roic=0.2, net_margin=-0.01, industry_net_margin=0.1), "Margen neto")["severity"] == "severe"


@pytest.mark.parametrize("name,om,iom,nm,inm,op_pts,net_pts", [
    ("UNH", 0.048, 0.030, 0.031, 0.0125, 1, 0),      # margen hundido: en línea con su industria, no excepcional
    ("WMT", 0.044, 0.068, 0.030, 0.056, -1, 0),
    ("MSFT", 0.468, 0.330, 0.403, 0.255, 3, 3),
    ("KO", 0.296, 0.205, 0.286, 0.134, 3, 3),
    ("NVDA", 0.652, 0.353, 0.637, 0.304, 5, 3),
])
def test_margin_cases_from_the_audit(name, om, iom, nm, inm, op_pts, net_pts):
    r = _r(roic=0.2, wacc=0.08, operating_margin=om, net_margin=nm, industry_operating_margin=iom,
           industry_net_margin=inm)
    assert (_adj(r, "Margen operativo")["adjustment"], _adj(r, "Margen neto")["adjustment"]) == (op_pts, net_pts), name


def test_low_margin_low_industry_never_beats_high_margin_high_industry():
    """Prueba de cordura del PM: a igual diferencia relativa sobre su industria (1,6 veces), una empresa de margen bajo
    en una industria de margen bajo no saca más Rentabilidad que una de margen alto en una de margen alto."""
    low = _r(roic=0.2, wacc=0.08, operating_margin=0.048, net_margin=0.02, industry_operating_margin=0.03,
             industry_net_margin=0.0125)
    high = _r(roic=0.2, wacc=0.08, operating_margin=0.48, net_margin=0.20, industry_operating_margin=0.30,
              industry_net_margin=0.125)
    m = lambda r: sum(x["adjustment"] for x in r["adjustments"] if x["metric"].startswith("Margen"))
    assert m(low) < m(high) and low["score"] <= high["score"]


def test_high_leverage_swaps_roe_for_roic():
    r = _r(roic=0.12, wacc=0.08, debt_to_equity=1.87, sector_de_threshold=1.5)
    row = _adj(r, "ROIC (en lugar del ROE")
    assert row and row["leverage_swap"] and row["value"] == "12.00%" and "D/E de 1.87" in row["reason"]
    # un ROE ausente no cambia nada: con D/E alto el sitio es del ROIC igual
    assert _r(roe=None, roic=0.12, wacc=0.08, debt_to_equity=1.87, sector_de_threshold=1.5)["score"] == r["score"]
    assert _adj(r, "ROE") is None
    assert _adj(_r(roic=0.12, wacc=0.08, debt_to_equity=1.2, sector_de_threshold=1.5), "ROE")["value"] == "18.80%"


def test_config_matches_the_audit():
    T = cfg("thresholds.score.rentabilidad")
    assert sorted(map(tuple, T["spread_caps"])) == [(-0.03, 6.0), (0.0, 10.0)]
