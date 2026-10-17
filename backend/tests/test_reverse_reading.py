"""Fase 3 (T3, D3): DCF inverso conectado, con las tasas base como referencia principal (F3_DISENO §2, §8.1)."""
import math

import pytest

import base_rates as br
import reverse_dcf as rd
import reverse_reading as rr
from settings import cfg


def test_lognormal_fit_reproduces_the_published_std():
    med, std = 0.072, 0.130
    s = br._lognormal_sigma(med, std)
    m = 1 + med
    var = (math.exp(s * s) - 1) * math.exp(s * s) * m * m
    assert math.sqrt(var) == pytest.approx(std, rel=1e-9)


def test_share_at_the_median_is_one_half_and_falls_with_growth():
    row = cfg("base_rates.table")["1-5"]["Technology"]
    rev = 3e9 / cfg("base_rates.size.deflator_to_2020")        # 3 mil millones de 2020
    assert br.share_sustaining(row["median"][3], rev, "Technology")["share"] == pytest.approx(0.5)
    shares = [br.share_sustaining(g, rev, "Technology")["share"] for g in (0.0, 0.1, 0.2, 0.3)]
    assert all(a > b for a, b in zip(shares, shares[1:]))


def test_thin_cells_fall_back_to_the_size_row():
    r = br.share_sustaining(0.05, 200e9, "Healthcare")            # 100+ Healthcare: 7 observaciones a 10 años
    assert r["cell"] == "100+ · All" and r["count"] >= cfg("base_rates.min_count")


def test_size_is_deflated_to_2020_dollars():
    f = cfg("base_rates.size.deflator_to_2020")
    assert br.size_bin(10e9 / f * 0.999) == "5-10" and br.size_bin(10e9 / f * 1.001) == "10-25"
    assert br.industry_for("Communication Services") == "Technology" and br.industry_for(None) == "All"


def test_reading_rules():
    T = cfg("valuation.reverse_dcf")
    # Tasas base mandan: excepcional aunque la historia propia lo haya superado.
    assert rd.read_against_base_rates(0.25, 0.05, 0.40)["band"] == rd.VERY_DEMANDING
    assert rd.read_against_base_rates(0.12, 0.20, 0.20)["band"] == rd.DEMANDING
    # Con tasas base razonables, la historia propia: ±band_pp.
    assert rd.read_against_base_rates(0.05, 0.5, 0.05 + T["band_pp"] + 0.01)["band"] == rd.CHEAP
    assert rd.read_against_base_rates(0.05, 0.5, 0.05)["band"] == rd.IN_PRICE
    assert rd.read_against_base_rates(0.12, 0.3, 0.02)["band"] == rd.DEMANDING
    # Sin historia propia.
    assert rd.read_against_base_rates(0.0, 0.9, None)["band"] == rd.CHEAP
    assert rd.read_against_base_rates(0.05, 0.5, None)["band"] == rd.IN_PRICE
    # Fuera del dominio de búsqueda (§8.3): se informa como tal.
    assert rd.read_against_base_rates(None, None, None, "superior")["band"] == rd.VERY_DEMANDING
    assert rd.read_against_base_rates(None, None, None, "inferior")["band"] == rd.CHEAP


def test_ten_year_cagr_of_the_path():
    tg = cfg("valuation.dcf.terminal_growth")
    assert rd.ten_year_cagr(tg) == pytest.approx(tg)
    g10 = rd.ten_year_cagr(0.20)
    assert tg < g10 < 0.20


def test_reading_end_to_end_and_sentence():
    own = {"cagr": 0.08, "years": 10, "basis": "por_accion", "label": "sus ingresos por acción"}
    x = rr.reading(price=100.0, flow=4e9, shares=1e9, rate=0.09, net_debt=0.0, revenue_usd=40e9,
                   sector="Consumer Defensive", own=own, flow_label="FCF − SBC")
    assert x["state"] == rd.OK and x["band"] in (rd.CHEAP, rd.IN_PRICE, rd.DEMANDING, rd.VERY_DEMANDING)
    v = rd.equity_value_per_share(x["g_star"], 4.0, 0.09, x["terminal_growth"], 10, 6)
    assert v == pytest.approx(100.0, rel=1e-6)                    # reconstruye el precio
    t = x["text"]
    assert t.startswith("El precio actual exige que el FCF − SBC por acción crezca un ")
    assert "en los últimos 10 años, sus ingresos por acción crecieron un 8.0% anual" in t
    assert "de las empresas comparables (ventas de 25 a 50 mil millones, consumo)" in t
    # Precio que no se reconcilia: "exige más de +60%".
    y = rr.reading(price=1000.0, flow=1e8, shares=1e9, rate=0.09, net_debt=0.0, revenue_usd=40e9,
                   sector="Technology", own=own, flow_label="FCF")
    assert y["band"] == rd.VERY_DEMANDING and "más de un 60% anual" in y["text"]


def test_size_bin_revenue_is_converted_to_usd(monkeypatch):
    """Revisión de código F3 (hallazgo 4): las ventas van en la moneda de la cotización; el tramo de tamaño se mide
    en USD y, sin tipo de cambio, no se lee otra moneda como USD."""
    import currency
    import main

    class Fx:
        def close_at(self, d):
            return 0.00072          # USD por 1 KRW

    monkeypatch.setattr(currency, "fetch_fx", lambda fin, px, cls: Fx())
    assert main._revenue_usd(2e12, "KRW") == pytest.approx(1.44e9)
    assert main._revenue_usd(5e9, "USD") == 5e9

    def boom(fin, px, cls):
        raise currency.CurrencyConversionError("sin red")
    monkeypatch.setattr(currency, "fetch_fx", boom)
    assert main._revenue_usd(2e12, "KRW") is None
