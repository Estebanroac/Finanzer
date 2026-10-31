"""Rediseño E2a (T3): ficha de la empresa desde EDGAR submissions (SIC, sede, constitución, cierre fiscal, tipo de
emisor), sin red adicional: viene en la misma respuesta que la lista de filings."""
import logging

import company_profile
import sec_edgar

RAW = {"sic": "3571", "sicDescription": "Electronic Computers", "stateOfIncorporation": "CA",
       "stateOfIncorporationDescription": "CA", "fiscalYearEnd": "0926", "category": "Large accelerated filer",
       "website": "", "addresses": {"business": {"city": "CUPERTINO", "stateOrCountry": "CA",
                                                 "stateOrCountryDescription": "CA"}}}


def test_submission_profile_extrae_los_campos():
    p = sec_edgar.submission_profile(RAW)
    assert p["sic"] == "3571" and p["sic_description"] == "Electronic Computers"
    assert p["fiscal_year_end"] == "0926" and p["city"] == "CUPERTINO"
    assert p["website"] is None


def test_submission_profile_sin_campos():
    p = sec_edgar.submission_profile({})
    assert set(p.values()) == {None}


def test_ficha_legible():
    f = company_profile.build(sec_edgar.submission_profile(RAW), {"country": "United States"})
    rows = {r["key"]: r["value"] for r in f["rows"]}
    assert rows["sic"] == "3571 · Electronic Computers"
    assert rows["hq"] == "Cupertino, California"
    assert rows["fiscal_year_end"] == "26 de septiembre"
    assert rows["category"] == "Gran emisor (large accelerated filer)"
    assert "website" not in rows
    assert f["status"] == "ok" and f["source"].startswith("SEC EDGAR")


def test_categoria_combinada():
    raw = dict(RAW, category="Non-accelerated filer<br>Smaller reporting company")
    rows = {r["key"]: r["value"] for r in company_profile.build(sec_edgar.submission_profile(raw), {})["rows"]}
    assert rows["category"] == ("Emisor no acelerado (non-accelerated filer) · "
                                "Pequeña empresa declarante (smaller reporting company)")


def test_sin_edgar_dice_por_que():
    f = company_profile.build(None, {"country": "France"})
    assert f["status"] == "sin_dato" and f["rows"] == [] and f["reason"]
    g = company_profile.build(None, {}, edgar_status="no_disponible", edgar_reason="tiempo agotado")
    assert g["status"] == "sin_dato" and "tiempo agotado" in g["reason"]


def test_el_analisis_trae_la_ficha():
    import fixture_backend as fb
    logging.disable(logging.CRITICAL)
    with fb.replay(fb.fixtures_dir("panel")) as store:
        aapl = fb.run_analysis("AAPL", store)
        mc = fb.run_analysis("MC.PA", store)
    rows = {r["key"]: r["value"] for r in aapl["company_profile"]["rows"]}
    assert rows["sic"] == "3571 · Electronic Computers" and rows["hq"] == "Cupertino, California"
    assert aapl["data_provenance"]["edgar"]["profile"]["sic"] == "3571"
    assert mc["company_profile"]["status"] == "sin_dato" and mc["company_profile"]["reason"]


def test_direcciones_extranjeras():
    tsm = {"addresses": {"business": {"city": "HSINCHU", "stateOrCountry": None, "stateOrCountryDescription": None,
                                      "country": "Taiwan"}}}
    toyota = {"addresses": {"business": {"city": "JAPAN", "stateOrCountry": "M0",
                                         "stateOrCountryDescription": "Japan"}}}
    novo = {"addresses": {"business": {"city": "BAGSVAERD DENMARK", "stateOrCountry": "G7",
                                       "stateOrCountryDescription": "Denmark"}}}
    hq = lambda raw: {r["key"]: r["value"] for r in company_profile.build(sec_edgar.submission_profile(raw), {})["rows"]}["hq"]
    assert hq(tsm) == "Hsinchu, Taiwan"
    assert hq(toyota) == "Japan"
    assert hq(novo) == "Bagsvaerd Denmark"


def test_estados_de_eeuu_con_su_nombre():
    """Revisión del PM: el código del estado (DE, CA) no lo entiende el lector; lo que no es un estado se queda igual."""
    raw = dict(RAW, stateOfIncorporation="DE", stateOfIncorporationDescription="DE")
    rows = {r["key"]: r["value"] for r in company_profile.build(sec_edgar.submission_profile(raw), {})["rows"]}
    assert rows["incorporation"] == "Delaware" and rows["hq"] == "Cupertino, California"
    uk = {"stateOfIncorporationDescription": "United Kingdom",
          "addresses": {"business": {"city": "LONDON", "stateOrCountry": "X0", "stateOrCountryDescription": "United Kingdom"}}}
    rows = {r["key"]: r["value"] for r in company_profile.build(sec_edgar.submission_profile(uk), {})["rows"]}
    assert rows["incorporation"] == "United Kingdom" and rows["hq"] == "London, United Kingdom"
    ny = dict(RAW, addresses={"business": {"city": "NEW YORK", "stateOrCountry": "NY", "stateOrCountryDescription": "NY"}})
    assert {r["key"]: r["value"] for r in company_profile.build(sec_edgar.submission_profile(ny), {})["rows"]}["hq"] \
        == "New York, Nueva York"
