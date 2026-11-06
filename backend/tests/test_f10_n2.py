"""F10 · N2 (revisión del informe de NVIDIA; regla del modelo general): la referencia de la industria nunca incluye a la
propia empresa (lib/self_exclusion.py, lib/industry_bench._self)."""
import json
import os

import pytest

from self_exclusion import PARTS, without
from settings import cfg

GOLDEN = os.path.join(os.path.dirname(__file__), "golden", "panel")
# Semiconductor de EE. UU. (Damodaran, 5-ene-2026), en millones de USD
SEMI = {"mcap": 7857941.525, "book_equity": 493315.32, "ev": 7979087.4598, "invested_capital": 487029.8372,
        "total_debt": 203607.4948, "revenue": 508201.111, "gross_profit": 299697.003, "ebitda": 227750.76,
        "ebit": 179446.881, "net_income": 154726.948}
SEMI_VALUES = {"pe": 48.8101, "ev_ebitda": 25.9106, "pb": 13.3122, "roe": 0.3136, "roic": 0.2723,
               "gross_margin": 0.5897, "operating_margin": 0.3533, "net_margin": 0.3045, "interest_coverage": 23.0608,
               "de": 0.3429}


def _golden(sym):
    with open(os.path.join(GOLDEN, f"{sym}.json"), encoding="utf-8") as fh:
        return json.load(fh)


def _fig(**v):
    return {"status": "ok", "values": v}


def test_zero_weight_gives_the_published_reference():
    z = _fig(mcap=0.0, ev=0.0, ebitda=0.0, net_income=0.0, book_equity=0.0, ebit=0.0, revenue=0.0,
             gross_profit=0.0, interest=0.0, total_debt=0.0, invested_capital=0.0)
    w = without(SEMI_VALUES, SEMI, z)
    assert w["weight"] == 0.0
    for col, v in SEMI_VALUES.items():
        assert w["values"][col] == pytest.approx(v), col


def test_continuous_in_the_weight():
    """La referencia sin la empresa se mueve poco a poco con su tamaño (sin umbral)."""
    pes = [without({"pe": 48.8101}, SEMI, _fig(mcap=k * 1000.0, net_income=k * 20.0))["values"]["pe"]
           for k in (0, 1, 2, 4)]
    assert pes[0] == pytest.approx(48.8101)
    assert all(abs(b - a) < 0.1 for a, b in zip(pes, pes[1:]))


def test_multiple_uses_the_published_subset_not_all_firms():
    """NFLX (Entertainment, EE. UU.): con el beneficio de TODAS las empresas (pérdidas incluidas) la referencia salía
    221x; con el ancla (capitalización) y el beneficio implícito en el P/E publicado (solo empresas con beneficio):
    (A − a) / (A / P/E − e)."""
    ent = {"mcap": 1_000_000.0, "net_income": 15_000.0}
    w = without({"pe": 32.46}, ent, _fig(mcap=387_000.0, net_income=10_000.0))
    assert w["values"]["pe"] == pytest.approx((1_000_000 - 387_000) / (1_000_000 / 32.46 - 10_000))
    assert 25 < w["values"]["pe"] < 35


def test_company_with_losses_is_not_in_the_pe_aggregate():
    w = without({"pe": 37.52, "net_margin": 0.2}, {"mcap": 100.0, "revenue": 50.0},
                _fig(mcap=2.0, net_income=-1.0, revenue=1.0))
    assert w["columns"]["pe"]["how"] == "no_entra" and w["values"]["pe"] == 37.52
    assert w["columns"]["net_margin"]["how"] == "sin_empresa"


def test_every_column_has_an_anchor_in_the_dollar_file():
    cols = set(cfg("industries.dollar_columns"))
    assert {p[2] for p in PARTS.values()} <= cols
    assert set(PARTS) <= set(cfg("industries.columns"))


def test_nvda_reference_without_nvidia_is_declared():
    """NVDA en el panel: el 58 % de la capitalización de los semiconductores de EE. UU. a 5-ene-2026 (cierre de ese
    día × acciones; doce meses a oct-2025 de SEC EDGAR)."""
    ind = _golden("NVDA")["benchmark"]["industry"]
    se = ind["self_exclusion"]
    assert se["method"] == "sin_empresa" and 0.55 < se["weight"] < 0.62
    assert se["declaration"] == f"referencia de la industria sin NVIDIA, que pesa el {se['weight'] * 100:.0f} %"
    assert se["cut"] == "2025-10-26" and se["date"] == cfg("industries.dollar_as_of")
    a = _golden("NVDA")
    assert a["benchmark"]["values"]["pe"] == pytest.approx(se["columns"]["pe"]["after"])
    assert ind["published"]["pe"] == pytest.approx(48.8101)
    assert "sin NVIDIA, que pesa el" in a["display"]["sections"]["valuation"]["reference_note"]


def test_almost_all_the_industry_falls_back_to_the_global_industry():
    """AAPL ≈ 91 % de «Computers/Peripherals» de EE. UU. (≥ `self_max_weight`): lo que queda son restos. F14 · paso 6:
    antes que la mediana de 7 pares, el grupo más amplio: la misma industria a escala global sin Apple, dicho."""
    a = _golden("AAPL")
    ib = a["benchmark"]["industry"]
    se = ib["self_exclusion"]
    assert ib["basis"] == "industria_global" and se["method"] == "sin_empresa"
    assert se["weight"] < cfg("sectors.benchmarks.industry.self_max_weight") and ib["firms"] >= 10
    assert "casi solo Apple" in ib["home_why"]


def test_the_reference_never_includes_the_company():
    """En todo el panel: o la referencia es sin la empresa (o la mediana de sus pares), o Damodaran no la cuenta."""
    for f in sorted(os.listdir(GOLDEN)):
        if not f.endswith(".json"):
            continue
        b = _golden(f[:-5]).get("benchmark") or {}
        if not b or b.get("provisional"):
            continue
        se = (b.get("industry") or {}).get("self_exclusion")
        assert se and se["method"] in ("sin_empresa", "mediana_pares", "no_figura", "agregado_peso_menor"), f
        assert se.get("declaration"), f
        # F11 · T1: con ella dentro solo si pesa menos de `self_negligible_weight` y no hay cifras para restarla (BCS)
        if se["method"] == "agregado_peso_menor":
            assert se["weight"] < cfg("sectors.benchmarks.industry.self_negligible_weight"), f


def test_reference_anchor_by_industry_and_with_several_industries():
    """F11 · T2: el ancla es la industria de Damodaran, sin la región ni la forma (NU: el ROE estable del agregado
    global y el P/B del emergente dependen de la misma industria); una referencia de sector trae varias (VYLR: el
    análisis fallaba con una lista)."""
    import industry_bench as ib
    assert ib.reference_anchor("Bank (Money Center)", "global", {"method": "sin_empresa"}) == \
        ib.reference_anchor("Bank (Money Center)", "emerging", {"method": "mediana_pares", "peers_scope": "todas"})
    assert ib.reference_anchor(["Bank (Money Center)", "Banks (Regional)"], "us", None).startswith("las industrias")
    assert ib.reference_anchor(None, "us", None) is None
