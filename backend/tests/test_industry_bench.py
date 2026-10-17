"""Fase 4/7 (F4_PARADA §5; permiso del usuario del 2026-10-17): referencia por industria y región de Damodaran
(lib/industry_bench.py, config/industries.toml) y país del emisor (EDGAR o sufijo del ticker). Sin red."""
import math

import pytest

import industry_bench as IB
from beta import _norm
from settings import cfg


# ─────────────────────────── el archivo generado ───────────────────────────
def test_industries_file_is_complete_and_dated():
    I = cfg("industries")
    assert I["columns"][0] == "firms" and "pe" in I["columns"] and "pe_avg" in I["columns"]
    assert "Damodaran" in I["source"] and I["as_of"] >= "2026-01-01"
    for reg in ("us", "europe", "japan", "emerging", "global"):
        rows = I["regions"][reg]["industries"]
        assert len(rows) > 90 and IB.MARKET_ROW in rows, reg
        assert all(len(v) == len(I["columns"]) for v in rows.values()), reg


def test_every_mapped_industry_exists_in_every_region():
    """El mapa de industrias de Yahoo (el de la beta del sector) apunta a filas que existen."""
    B, I = cfg("betas"), cfg("industries")
    targets = set(B["yahoo_industries"].values()) | {g for grp in B["yahoo_sectors"].values() for g in grp}
    for reg in I["regions"]:
        missing = targets - set(I["regions"][reg]["industries"])
        assert not missing, (reg, sorted(missing))


# ─────────────────────────── región ───────────────────────────
@pytest.mark.parametrize("country,reg", [("United States", "us"), ("United Kingdom", "europe"), ("Netherlands", "europe"),
                                         ("Japan", "japan"), ("Taiwan", "emerging"), ("Canada", "global"),
                                         (None, "global"), ("Unknown", "global")])
def test_region_by_country(country, reg):
    assert IB.region(country) == reg


# ─────────────────────────── industria ───────────────────────────
def test_industry_in_its_region_with_aggregates_and_source():
    r = IB.industry("Technology", "Software - Application", "United States")
    assert r["basis"] == "industria" and r["damodaran"] == "Software (System & Application)" and r["region"] == "us"
    row = cfg("industries.regions.us.industries")["Software (System & Application)"]
    cols = cfg("industries.columns")
    assert r["values"]["pe"] == pytest.approx(row[cols.index("pe")]) and r["firms"] == row[0]
    assert "pe_avg" not in r["values"]                       # solo para la prueba de dominio
    assert "Damodaran" in r["source"] and r["as_of"] == cfg("industries.as_of")


def test_european_bank_uses_european_banks():
    """BCS (revisión externa F1): P/B frente a los bancos europeos, no a los de EE. UU."""
    us = IB.industry("Financial Services", "Banks - Diversified", "United States")
    eu = IB.industry("Financial Services", "Banks - Diversified", "United Kingdom")
    assert eu["region"] == "europe" and eu["values"]["pb"] < us["values"]["pb"]


def test_too_few_firms_uses_the_global_industry():
    I = cfg("industries")
    n = I["regions"]["us"]["industries"]["Oil/Gas (Integrated)"][0]
    assert n < cfg("sectors.benchmarks.industry.min_firms")
    r = IB.industry("Energy", "Oil & Gas Integrated", "United States")
    assert r["basis"] == "industria_global" and r["region"] == "global" and r["home_region"] == "us"
    assert f"{n} empresas" in r["home_why"]


def test_dominated_industry_uses_the_global_industry():
    """Auto & Truck de EE. UU.: el agregado (Tesla) supera en más de un 50% a la media simple: no representa a un
    fabricante; se usa la industria global."""
    I, cols = cfg("industries"), cfg("industries.columns")
    row = I["regions"]["us"]["industries"]["Auto & Truck"]
    assert row[cols.index("pe")] >= cfg("sectors.benchmarks.industry.dominance_ratio") * row[cols.index("pe_avg")]
    r = IB.industry("Consumer Cyclical", "Auto Manufacturers", "United States")
    assert r["basis"] == "industria_global" and "dominada" in r["home_why"]
    assert r["values"]["pe"] < row[cols.index("pe")]


def test_unmapped_industry_uses_its_sector_weighted_by_firms():
    r = IB.industry("Technology", "Industria que no existe", "United States")
    assert r["basis"] == "sector" and isinstance(r["damodaran"], list)
    rows = [(cfg("industries.regions.us.industries")[g], g) for g in r["damodaran"]]
    cols = cfg("industries.columns")
    pts = [(v[0], v[cols.index("pe")]) for v, _ in rows if v[0] > 0 and math.isfinite(v[cols.index("pe")])]
    assert r["values"]["pe"] == pytest.approx(sum(w * x for w, x in pts) / sum(w for w, _ in pts))


def test_nothing_mapped_returns_none():
    assert IB.industry(None, None, "United States") is None


def test_hyphen_inside_a_word_is_kept():
    """KO: "Beverages—Non-Alcoholic" casa con "beverages - non-alcoholic" (antes se partía el guion interno)."""
    assert _norm("Beverages—Non-Alcoholic") == "beverages - non-alcoholic"
    assert _norm("Banks - Regional") == _norm("Banks—Regional") == "banks - regional"
    assert IB.industry("Consumer Defensive", "Beverages—Non-Alcoholic", "United States")["damodaran"] == "Beverage (Soft)"


# ─────────────────────────── benchmark del análisis ───────────────────────────
def test_select_benchmark_has_a_source_for_every_value():
    import main
    b = main._select_benchmark("technology", "MATURE", "Technology", "Software - Application", "United States")
    assert b["profile"] == "sector" and b["provisional"] is False and b["short"] == "industria"
    assert set(b["sources"]) == set(b["values"]) and all("Damodaran" in s for s in b["sources"].values())
    # lo que Damodaran no da no se rellena a mano: sin referencia
    assert not {"forward_pe", "peg", "pfcf", "fcf_yield", "roa"} & set(b["values"])


def test_missing_scored_multiple_comes_from_the_region_market():
    """P/E y EV/EBITDA puntúan: si la industria no los tiene (bancos sin EV/EBITDA), el mercado de su región."""
    import main
    b = main._select_benchmark("financials", "FINANCIAL", "Financial Services", "Banks - Diversified",
                               "United States")
    assert "ev_ebitda" in b["values"] and "la industria no tiene dato" in b["sources"]["ev_ebitda"]


def test_without_industry_the_provisional_sector_table_is_said():
    import main
    b = main._select_benchmark("technology", "MATURE")
    assert b["provisional"] is True and b["short"] == "sector" and b["values"] == main._get_sector_benchmarks(
        "technology")


# ─────────────────────────── país del emisor ───────────────────────────
@pytest.mark.parametrize("addr,country", [
    ({"business": {"stateOrCountry": "CA", "stateOrCountryDescription": "CA"}}, "United States"),
    ({"business": {"stateOrCountry": "P7", "stateOrCountryDescription": "Netherlands"}}, "Netherlands"),
    ({"business": {"country": "Taiwan", "countryCode": "F5", "isForeignLocation": 1}}, "Taiwan"),
    ({"mailing": {"stateOrCountry": "X0", "stateOrCountryDescription": "United Kingdom"}}, "United Kingdom"),
    ({}, None)])
def test_issuer_country_from_edgar_address(addr, country):
    import sec_edgar
    assert sec_edgar.issuer_country({"addresses": addr}) == country


def test_country_precedence_yahoo_then_edgar_then_suffix():
    import yf_adapter as Y
    info = {"country": "Spain", "_edgar": {"country": "United Kingdom"}}
    Y._apply_country("SAN", info)
    assert info["country"] == "Spain"                                          # el de Yahoo, si llega
    info = {"country": "Unknown", "_edgar": {"country": "Korea, Republic of"}}
    Y._apply_country("XX", info)
    assert info["country"] == "South Korea" and info["_provenance"]["country"]["source"] == "sec_edgar"
    info = {"country": None, "_edgar": {"status": "sin_cik"}}
    Y._apply_country("MC.PA", info)
    assert info["country"] == "France" and "sufijo .PA" in info["_provenance"]["country"]["detail"]
    info = {"country": None}
    Y._apply_country("T", info)                                                # AT&T: "T" no es el sufijo ".T"
    assert info["country"] is None
