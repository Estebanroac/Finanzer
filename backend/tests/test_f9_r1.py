"""
F9 · R1 (revisión externa del informe de NU, 27-oct-2026): prima de riesgo país en el Ke.

- Ke = Rf + β·ERP + λ·CRP con la CRP de Damodaran (config/country_risk.toml, con su fecha), ponderada por dónde opera
  la empresa: la geografía de los ingresos del XBRL o, sin ella, la sede operativa (nunca el domicilio legal);
- λ = 1; lo añadido es máx(0, ERP_x − ERP_EE.UU.): EE. UU. y los países Aaa no suman;
- país identificado, su prima; región con nombre, la media de Damodaran; cubo vago, sin atribuir (decisión del PM);
- los pisos de F8 · E1 se aplican después, sobre el Ke con la prima.
"""
import pytest

import cost_of_capital as cc
import country_risk as cr
from settings import cfg

T = cfg("country_risk")


def _geo(*rows, reconciles=True):
    return {"status": "ok", "axis": "StatementBusinessSegmentsAxis", "segments": [],
            "secondary": {"axis": "StatementGeographicalAxis", "reconciles": reconciles,
                          "segments": [{"member": m, "label": l, "share_last": w} for m, l, w in rows]}}


def test_table_has_its_date_and_the_us_base():
    assert T["updated"] == "2026-01-05" and T["us_erp"] == pytest.approx(0.0446)
    assert T["erp"]["United States"] == pytest.approx(T["us_erp"])
    assert cr.premium(T["erp"]["Brazil"]) == pytest.approx(0.0301, abs=1e-4)


def test_nu_uses_its_operating_headquarters_not_the_cayman_domicile():
    """NU: el 20-F no desglosa la geografía en XBRL; la sede operativa de EDGAR es Brasil (constituida en Caimán)."""
    e = cr.exposure({"status": "sin_dato"}, "Brazil")
    assert e["basis"] == "sede" and e["country"] == "Brazil"
    assert e["crp"] == pytest.approx(T["erp"]["Brazil"] - T["us_erp"])
    assert cr.exposure(None, "Cayman Islands")["crp"] != e["crp"]
    assert "Brasil, sede operativa" in cr.text(e)


@pytest.mark.parametrize("country", ["United States", "Netherlands", "Germany", "Switzerland", "Singapore"])
def test_us_and_aaa_countries_add_nothing(country):
    assert cr.exposure(None, country)["crp"] == 0
    assert cr.text(cr.exposure(None, country)) is None


def test_developed_markets_add_little():
    """La comprobación del PM: Reino Unido, Francia y Japón suman menos de 1 pp."""
    for c in ("United Kingdom", "France", "Japan"):
        assert 0 < cr.exposure(None, c)["crp"] < 0.01


def test_revenue_geography_weights_countries_and_named_regions():
    """Decisión del PM (27-oct, «(b) ampliada»): país, su prima; región con nombre, la media de Damodaran; un cubo vago,
    sin atribuir (0, declarado)."""
    e = cr.exposure(_geo(("country:CN", "China", 0.6), ("srt:EuropeMember", "Europe", 0.3),
                         ("us-gaap:NonUsMember", "Non-US", 0.1)), "Netherlands")
    assert e["basis"] == "geografía" and e["identified"] == pytest.approx(0.9)
    kinds = {w["label"]: (w["kind"], w["name"]) for w in e["weights"]}
    assert kinds == {"China": ("país", "China"), "Europe": ("región", "Europe"), "Non-US": ("no atribuido", None)}
    exp = 0.6 * cr.premium(T["erp"]["China"]) + 0.3 * cr.premium(T["region_erp"]["Europe"])
    assert e["crp"] == pytest.approx(exp)
    assert e["unattributed"] == {"share": pytest.approx(0.1), "labels": ["Non-US"]}
    assert "el 10% de los ingresos no tiene país identificado («Non-US»)" in cr.text(e)
    assert cr.source_label(e) == "país y región"


def test_vague_buckets_below_coverage_fall_back_to_headquarters_and_keep_the_warning():
    """KO (60 % «Non-US») y AAPL (48 % «Other Countries»): menos del 80 % identificado → la sede (EE. UU.: 0), con el
    aviso del no atribuido."""
    e = cr.exposure(_geo(("us-gaap:NonUsMember", "Non-US", 0.6), ("country:US", "United States", 0.4)),
                    "United States")
    assert e["basis"] == "sede" and e["crp"] == 0 and "cubren el 40%" in e["reason"]
    assert e["unattributed"]["share"] == pytest.approx(0.6)
    assert cr.text(e).endswith("el 60% de los ingresos no tiene país identificado («Non-US»)")
    assert cr.source_label(e) == "sede"


def test_several_regions_without_a_published_mean_are_not_attributed():
    """«Asia Pacific and Africa» (UL, SHEL) no tiene media de Damodaran: sin atribuir. EMEA sí es una agrupación."""
    assert cr._member("Asia Pacific And Africa")["kind"] == "no atribuido"
    assert cr._member("Europe, Middle East, Africa")["name"] == "EMEA"
    assert cr._member("Emerging Markets")["name"] == "Emerging Markets"
    assert cr._member("Korea, Republic of") == {"label": "Korea, Republic of", "kind": "país", "name": "Korea",
                                                 "erp": T["erp"]["Korea"]}


def test_geography_that_does_not_reconcile_counts_against_the_consolidated_total():
    """Segmentos que suman el 50 % de los ingresos consolidados (gap −50 %): China 100 % de la suma es el 50 % del
    total; el resto queda sin desglose y, con menos del 80 % identificado, manda la sede."""
    g = _geo(("country:CN", "China", 1.0), reconciles=False)
    g["secondary"]["gap_pct"] = -0.5
    e = cr.exposure(g, "Netherlands")
    assert e["identified"] == pytest.approx(0.5) and e["basis"] == "sede" and e["crp"] == 0
    assert e["unattributed"]["labels"] == ["sin desglose"]
    # sin total consolidado con que conciliar, la sede
    assert cr.exposure(_geo(("country:CN", "China", 1.0), reconciles=False), "Netherlands")["basis"] == "sede"


def test_floor_applies_after_the_country_premium():
    """El piso compara con CAPM + CRP: NU (CAPM 6,97 % + 3,01 pp) ya no lo necesita."""
    rf, beta = 0.0529, 0.40
    ke0 = cc.equity_cost(beta, rf, preadjusted=True)
    assert ke0["floor"] is not None
    crp = cr.exposure(None, "Brazil")["crp"]
    ke = cc.equity_cost(beta, rf, preadjusted=True, crp=crp)
    assert ke["floor"] is None and ke["value"] == pytest.approx(ke["capm"] + crp) and ke["crp"] == crp
    # con una prima pequeña, el piso sigue mandando y lo dice frente al CAPM con la prima
    small = cc.equity_cost(beta, rf, preadjusted=True, crp=0.001)
    assert small["floor"]["crp"] == 0.001 and small["value"] == pytest.approx(small["floor"]["value"])


def test_lambda_is_one_and_documented():
    assert cfg("valuation.country_risk.lambda") == 1.0


def test_member_labels_and_country_of_domicile():
    """TSM: «… [member]» y «Europe Middle East and Africa» sin coma son EMEA; UL: el «país de domicilio» de la NIIF 8 es
    el de la sede operativa; NVDA: «China Including Hong Kong» nombra el país."""
    assert cr._member("Europe Middle East and Africa [member]")["name"] == "EMEA"
    m = cr._member("Country of domicile [member]", "ifrs-full:CountryOfDomicileMember", "United Kingdom")
    assert (m["kind"], m["name"]) == ("país", "United Kingdom")
    assert cr._member("China Including Hong Kong")["name"] == "China"
