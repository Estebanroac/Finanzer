"""
F8 · E10 (auditoría externa del 26-oct-2026): variante de Altman por el SIC del emisor en SEC EDGAR y exclusiones.

SIC 2000–3999 (manufacturas, la muestra de Altman) → Z original; el resto → Z''. Sin SIC, por sector (como antes).
Midstream (4610–4619, 4922–4924), utilities (4911, 4931–4932, 4939–4941, 4961, 4991) y financieras (6000–6799): no
aplica, con un sustituto informativo (deuda neta/EBITDA y cobertura) y sin reequilibrar pesos. SIC de los casos:
submissions de EDGAR del 26-oct-2026 (registro F8_INDEPENDIENTES §E10).
"""
import pytest

import display
from classify import MATURE
from financial_ratios import altman_excluded, altman_model, altman_model_basis, score_solidez_financiera


@pytest.mark.parametrize("sic,sector,model", [
    ("3559", "technology", "original"),          # ASML: maquinaria de semiconductores (antes Z'' por sector)
    ("3674", "technology", "original"),          # MU, NVDA
    ("2834", "healthcare", "original"),          # LLY, JNJ
    ("1000", "basic materials", "z_double_prime"),   # FCX: minería (antes Z original por sector)
    ("4011", "industrials", "z_double_prime"),   # UNP: ferrocarril (antes Z original por sector)
    ("1311", "energy", "z_double_prime"),        # SHEL: extracción
    ("2911", "energy", "original"),              # XOM: refino
    ("7372", "technology", "z_double_prime"),    # MSFT
    ("5961", "consumer cyclical", "z_double_prime"),   # AMZN
])
def test_modelo_por_sic(sic, sector, model):
    assert altman_model(sector, "", sic) == model


def test_sin_sic_por_sector_y_se_declara():
    assert altman_model("industrials", "", None) == "original"
    assert altman_model("technology", "", "") == "z_double_prime"
    assert "sin SIC" in altman_model_basis(None)
    assert altman_model_basis("3559") == "por el SIC del emisor en SEC EDGAR: 3559, manufacturas"
    assert altman_model_basis("1000").endswith("fuera de manufacturas")


@pytest.mark.parametrize("sic", ["4922", "4923", "4924", "4610", "4911", "4931", "4941", "6324", "6021", "6798"])
def test_excluidos(sic):
    why = altman_excluded(sic)
    assert why and f"SIC {sic}" in why and "No aplica" in why


@pytest.mark.parametrize("sic", ["4953", "4011", "7389", "3559", "4813", None, "abc"])
def test_no_excluidos(sic):
    assert altman_excluded(sic) is None        # WM/RSG (4953), UNP, V/MA, ASML, VZ…


def test_excluido_no_aplica_en_solidez_sin_reequilibrar():
    """KMI (SIC 4922) clasificada como madura: el Altman no puntúa ni cuenta (no aplica), los demás componentes
    puntúan igual que con él y sus puntos no se redistribuyen."""
    kw = dict(current_ratio=1.5, debt_to_equity=0.8, interest_coverage=6.0, archetype=MATURE, net_debt=1e9,
              net_debt_to_ebitda=2.0)
    con = score_solidez_financiera(2.0, "GREY", **kw)
    sin = score_solidez_financiera(2.0, "GREY", **kw, business_model={"altman_excluded": altman_excluded("4922")})
    assert "Altman Z" in sin["coverage"]["not_applicable"]
    assert all(a["metric"] != "Altman Z-Score" for a in sin["adjustments"])
    adj = lambda r: {a["metric"]: a["adjustment"] for a in r["adjustments"]  # noqa: E731
                     if a["metric"] not in ("Altman Z-Score", "No aplica")}
    assert adj(sin) == adj(con)


def test_sustituto_informativo():
    alt = {"applicable": False, "interpretation": altman_excluded("4922"),
           "substitute": {"net_debt_to_ebitda": 4.12, "net_debt_to_ebitda_state": "ok", "interest_coverage": 2.5,
                          "interest_coverage_state": "ok"}}
    txt = display.altman_substitute_text(alt)
    assert "deuda neta/EBITDA 4.12x" in txt and "cobertura de intereses 2.50x" in txt and "sin puntos" in txt
    assert display.altman_substitute_text({"applicable": False, "substitute": None}) is None


# ───────────── financiera cautiva consolidada (decisión del PM, 27-oct-2026) ─────────────
import business_model as bm


def _segs(axis, items):
    return {"status": "ok", "axis": axis, "segments": [{"label": l, "share_last": s} for l, s in items]}


@pytest.mark.parametrize("segs,segment", [
    (_segs("SegmentsAxis", [("Automotive", 0.903), ("Financial Services Business", 0.097)]),
     "Financial Services Business"),                                                           # TM (20-F, IFRS)
    (_segs("StatementBusinessSegmentsAxis", [("Power & Energy", 0.397), ("Construction Industries", 0.363),
                                             ("Resource Industries", 0.178), ("Financial Products", 0.062)]),
     "Financial Products"),                                                                    # CAT
    (_segs("StatementBusinessSegmentsAxis", [("Ford Blue", 0.539), ("Ford Pro", 0.354), ("Ford Credit", 0.071),
                                             ("Ford Model e", 0.036)]), "Ford Credit"),        # F
    (_segs("StatementBusinessSegmentsAxis", [("GM North America", 0.835), ("GM Financial", 0.092)]), "GM Financial"),
    (_segs("StatementBusinessSegmentsAxis", [("Production and Precision Agriculture", 0.385),
                                             ("Financial Services", 0.136)]), "Financial Services"),   # DE
])
def test_cautiva_por_segmentos(segs, segment):
    c = bm.captive_finance(segs, None)
    assert c["detected"] is True and c["segment"] == segment


@pytest.mark.parametrize("segs", [
    _segs("StatementBusinessSegmentsAxis", [("Americas", 0.429), ("Europe", 0.267)]),               # AAPL
    _segs("SegmentsAxis", [("Marketing", 0.419), ("Integrated Gas", 0.144), ("Upstream", 0.019)]),  # SHEL
    _segs("StatementBusinessSegmentsAxis", [("Grasberg", 0.331), ("Morenci", 0.102)]),              # FCX
    _segs("StatementBusinessSegmentsAxis", [("Autos", 0.97), ("Financial Services", 0.03)]),        # < 5 %
    _segs("ProductOrServiceAxis", [("Vehicles", 0.9), ("Financing", 0.1)]),                         # no es de negocio
])
def test_sin_cautiva(segs):
    assert bm.captive_finance(segs, None)["detected"] is False


def test_cautiva_por_la_deuda_del_xbrl():
    """La detección US GAAP del motor (lib/debt.py: Cat Financial) también cuenta, sin segmentos."""
    c = bm.captive_finance(None, {"status": "ok", "name": "Cat Financial", "value": 34.456e9})
    assert c["detected"] is True and c["segment"] == "Cat Financial"


def test_sin_segmentos_no_se_sabe():
    c = bm.captive_finance({"status": "sin_dato", "reason": "no presenta estados en la SEC"}, None)
    assert c["detected"] is None and "SEC" in c["reason"]


def test_cautiva_referencial_en_solidez():
    """Con cautiva, el Altman se muestra y no puntúa (referencial); sin segmentos, puntúa (opción a)."""
    kw = dict(current_ratio=1.5, debt_to_equity=0.8, interest_coverage=6.0, archetype=MATURE, net_debt=1e9)
    ref = score_solidez_financiera(1.59, "DISTRESS", **kw, business_model={
        "altman_referential": True, "altman_referential_reason": bm.ALTMAN_REF_CAPTIVE,
        "captive_finance": {"detected": True}})
    alt = next(a for a in ref["adjustments"] if a["metric"] == "Altman Z-Score")
    assert alt["adjustment"] == 0 and "financiera cautiva" in alt["reason"] and "no puntúa" in alt["reason"]
    assert "Altman Z" not in ref["coverage"].get("not_applicable", {})
    sin = score_solidez_financiera(1.59, "DISTRESS", **kw, business_model={"captive_finance": {"detected": None}})
    assert next(a for a in sin["adjustments"] if a["metric"] == "Altman Z-Score")["adjustment"] < 0


def test_texto_de_la_tarjeta_con_cautiva():
    alt = {"substitute": {"net_debt_to_ebitda": 5.1, "net_debt_to_ebitda_state": "ok", "interest_coverage": 9.0,
                          "interest_coverage_state": "ok"}}
    bmx = {"altman_referential_reason": bm.ALTMAN_REF_CAPTIVE,
           "captive_finance": {"detected": True, "segment": "Financial Services Business", "share": 0.097}}
    t = display.altman_captive_text(alt, bmx)
    assert "financiera cautiva" in t and "«Financial Services Business», el 9.7%" in t and "deuda neta/EBITDA 5.10x" in t


@pytest.mark.parametrize("cr,de,ic", [(1.6, 0.5, 9.0), (0.8, 1.5, 2.0)])
def test_referencial_y_no_aplica_puntuan_igual(cr, de, ic):
    """Coherencia del denominador (PM, 27-oct-2026): un Altman «referencial» (cautiva) y uno «no aplica» (SIC) se
    tratan igual en Solidez: ninguno entra en los componentes (ni en el numerador ni en el denominador de la
    cobertura), ninguno suma ni resta, y la categoría conserva su base neutra y su máximo (el resto de componentes
    puede llegar a 20). No hay penalización por no tener un dato aplicable."""
    kw = dict(current_ratio=cr, debt_to_equity=de, interest_coverage=ic, archetype=MATURE, net_debt=1e9)
    na = score_solidez_financiera(3.5, "SAFE", **kw, business_model={"altman_excluded": altman_excluded("4922")})
    ref = score_solidez_financiera(3.5, "SAFE", **kw, business_model={
        "altman_referential": True, "altman_referential_reason": bm.ALTMAN_REF_CAPTIVE,
        "captive_finance": {"detected": True}})
    assert na["score"] == ref["score"]
    assert na["coverage"]["components"] == ref["coverage"]["components"] == 3
    assert not any(a["metric"] == "Cobertura" for a in na["adjustments"] + ref["adjustments"])
