"""Rediseño E2a (T10): display.extended — los datos nuevos ya formateados (numfmt) para /v2. Solo datos; la única
frase (la base de los próximos resultados) se declara al guardián."""
import logging

import pytest

import fixture_backend as fb
from display import _extended_block


@pytest.fixture(scope="module")
def three():
    logging.disable(logging.CRITICAL)
    with fb.replay(fb.fixtures_dir("panel")) as store:
        return {t: fb.run_analysis(t, store) for t in ("AAPL", "JPM", "MC.PA")}


def test_variacion_del_dia(three):
    pc = three["AAPL"]["display"]["extended"]["price_change"]
    raw = three["AAPL"]["price_change"]
    assert pc["status"] == "ok" and pc["session"] == raw["session"]
    assert pc["value_txt"].startswith(("+$", "−$")) and pc["pct_txt"].endswith("%")
    assert pc["tone"] == ("pos" if raw["change"] > 0 else "neg" if raw["change"] < 0 else "neu")


def test_tono_neutro_sin_cambio():
    a = {"price_change": {"status": "ok", "change": 0.0, "change_pct": 0.0, "session": "2026-10-16"}}
    assert _extended_block(a)["price_change"]["tone"] == "neu"
    assert _extended_block(a)["price_change"]["value_txt"] == "$0.00"


def test_ficha_y_sin_edgar(three):
    assert three["AAPL"]["display"]["extended"]["company_profile"]["rows"][0]["value"] == "3571 · Electronic Computers"
    mc = three["MC.PA"]["display"]["extended"]
    assert mc["company_profile"]["status"] == "sin_dato" and mc["company_profile"]["reason"]
    assert mc["history_10y"]["status"] == "sin_dato" and mc["history_10y"]["reason"] and mc["history_10y"]["rows"] == []


def test_historia_formateada(three):
    h = three["AAPL"]["display"]["extended"]["history_10y"]
    assert h["status"] == "ok" and len(h["rows"]) == 10 and h["currency"] == "USD"
    r = h["rows"][-1]
    assert r["year"] == 2025 and r["revenue_txt"].startswith("$") and r["revenue_txt"].endswith("B")
    assert r["net_margin_txt"].endswith("%") and r["revenue_growth_txt"][0] in "+−0" and r["gap_before"] is False


def test_historia_en_la_moneda_de_los_estados():
    a = {"history_10y": {"status": "ok", "currency": "GBP", "source": "x", "reason": None,
                         "rows": [{"year": 2025, "revenue": 4.1e10, "net_income": None, "free_cash_flow": -2e9,
                                   "operating_margin": None, "net_margin": 0.2, "revenue_growth": None}]}}
    r = _extended_block(a)["history_10y"]["rows"][0]
    assert r["revenue_txt"] == "GBP 41.00B" and r["fcf_txt"] == "−GBP 2.00B" and r["net_income_txt"] == "—"


def test_piotroski_valores(three):
    pv = {x["key"]: x for x in three["AAPL"]["display"]["extended"]["piotroski_values"]}
    assert set(pv) == set(three["AAPL"]["piotroski_f"]["details"])
    assert pv["roa_improved"]["cur_txt"].endswith("%") and pv["roa_improved"]["compare"] == "prior_year"
    assert pv["roa_positive"]["prev_txt"] is None and pv["roa_positive"]["compare"] == "zero"
    assert pv["earnings_quality"]["compare"] == "ni" and pv["earnings_quality"]["cur_txt"].startswith("$")


def test_proximos_resultados_y_noticias(three):
    e = three["AAPL"]["display"]["extended"]
    ne = e["next_earnings"]
    assert ne["status"] == "ok" and ne["kind"] == "anunciada" and ne["date_txt"] == "2 de noviembre de 2026"
    assert "2 de noviembre de 2026" in ne["basis"]
    assert len(e["news"]) == 6 and {"summary", "image", "lang", "datetime"} <= set(e["news"][0])
    assert len(three["AAPL"]["display"]["sections"]["market"]["news"]) == 5      # la web actual no cambia
