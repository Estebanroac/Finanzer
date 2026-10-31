"""
F9 · R2b (decisión del PM del 27-oct): la beta de abajo hacia arriba sale de la tabla de Damodaran de la región donde
opera la empresa, con la misma exposición que la prima de riesgo país: emergentes si la sede operativa o más del 50 %
de los ingresos identificados están en emergentes; si no, Europa con la misma regla; si no, EE. UU.
"""
import pytest

import beta as B
import country_risk as cr
from settings import cfg


def _geo(*rows):
    return {"status": "ok", "axis": "StatementGeographicalAxis", "reconciles": True,
            "segments": [{"member": m, "label": l, "share_last": w} for m, l, w in rows]}


def test_region_rule():
    assert cr.beta_region(cr.exposure(None, "Brazil"))["region"] == "emerging"           # NU: sede operativa
    assert cr.beta_region(cr.exposure(None, "Germany"))["region"] == "europe"            # SAP
    assert cr.beta_region(cr.exposure(None, "United States"))["region"] == "us"
    assert cr.beta_region(cr.exposure(None, "Japan"))["region"] == "us"                  # Asia desarrollada
    # KO: sede en EE. UU., 60 % «Non-US» sin atribuir
    ko = cr.exposure(_geo(("us-gaap:NonUsMember", "Non-US", 0.6), ("country:US", "United States", 0.4)),
                     "United States")
    assert cr.beta_region(ko)["region"] == "us"
    # ASML: sede en Países Bajos, pero el 80 % de los ingresos en China, Taiwán y Corea
    asml = cr.exposure(_geo(("country:CN", "China", 0.29), ("country:TW", "Taiwan", 0.26),
                            ("country:KR", "Korea, Republic of", 0.25), ("country:US", "United States", 0.13),
                            ("country:NL", "Netherlands", 0.07)), "Netherlands")
    r = cr.beta_region(asml)
    assert r["region"] == "emerging" and "80%" in r["reason"]


def test_nu_uses_the_emerging_markets_bank_beta():
    """NU: la beta propia no pasa los filtros; antes, Banks (Regional) de EE. UU. (0,40); ahora la de emergentes."""
    us = B.sector_beta("Financial Services", "Banks - Regional")
    em = B.sector_beta("Financial Services", "Banks - Regional", "emerging")
    assert us["value"] == pytest.approx(0.40) and em["value"] == pytest.approx(0.604, abs=1e-3)
    assert em["region"] == "emerging" and "emergentes" in em["source"]
    choice = {"source": "sector", "value": us["value"], "sector": us, "reason": "x (Damodaran, enero de 2026)",
              "bottom_up": B.unlevered_beta("Financial Services", "Banks - Regional")}
    out = B.regionalize(choice, cr.beta_region(cr.exposure(None, "Brazil")), "Financial Services",
                        "Banks - Regional")
    assert out["value"] == pytest.approx(em["value"]) and out["region"]["region"] == "emerging"
    assert "tabla de mercados emergentes" in out["reason"]
    fin = B.relever(out, 1e9, 1e10, 0.2, financial=True)
    assert fin["value"] == pytest.approx(em["value"])       # financiera: sin reapalancar


def test_us_and_own_beta_are_untouched():
    own = {"source": "propia", "value": 1.1}
    assert B.regionalize(own, {"region": "emerging", "reason": "x"}, "Technology", "Software - Application") is own
    sec = {"source": "sector", "value": 0.4, "bottom_up": {"value": 0.3}, "reason": "r"}
    assert B.regionalize(sec, {"region": "us", "reason": None}, "Financial Services", "Banks - Regional") is sec


def test_regional_tables_have_their_source_and_date():
    R = cfg("betas_regional")
    assert R["as_of"] == "2026-01" and len(R["emerging"]["industries"]) > 80 and len(R["europe"]["unlevered"]) > 80
    assert set(R["emerging"]["industries"]) <= set(cfg("betas")["industries"]) | {"Total Market (without financials)"}
