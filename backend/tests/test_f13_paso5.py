"""
F13 · paso 5 (revisión de 110 empresas, patrón H): la referencia sin la empresa acotada (self_exclusion.without), sin
«ROE bajo» con el ROE por encima del Ke (alert_interpretations._roe) y ROE «n.s.» con un patrimonio ínfimo
(financial_ratios.score_rentabilidad, validate.validate_outputs). Cifras del banco congelado del 5-nov-2026.
"""
import self_exclusion as SE
from alert_interpretations import build_signals
from financial_ratios import score_rentabilidad
from validate import validate_outputs

# Cable TV global (Damodaran, ene-2026) y Comcast al corte del conjunto: márgenes 5,7 % → −8,1 % sin ella
_DOLLARS = {"mcap": 400_000.0, "revenue": 500_000.0, "book_equity": 300_000.0}


def _fig(net_income, revenue=220_000.0, book=96_000.0, mcap=176_000.0):
    return {"values": {"net_income": net_income, "revenue": revenue, "book_equity": book, "mcap": mcap}}


def test_sign_flip_goes_to_peer_median():
    """CMCSA: sin ella el margen neto de la industria pasa de 5,7 % a negativo: son restos."""
    wo = SE.without({"net_margin": 0.057}, _DOLLARS, _fig(net_income=46_350.0))
    c = wo["columns"]["net_margin"]
    assert c["how"] == "sin_dato" and c["why"] == "salto" and c["implausible"] < 0
    assert "net_margin" not in wo["values"]


def test_shift_beyond_factor_goes_to_peer_median():
    """BRK-B: el P/B de su industria sin ella pasa de 1,8x a 7,3x."""
    d = {"mcap": 1000.0, "book_equity": 1000.0 / 1.783}
    wo = SE.without({"pb": 1.783}, d, {"values": {"mcap": 820.0, "book_equity": 535.0}})
    assert wo["columns"]["pb"]["why"] == "salto"


def test_small_remainder_goes_to_peer_median():
    """ABBV: Biotecnología de EE. UU. ya publicada en pérdidas (−5 %); sin ella −8,3 %: no sirve de referencia."""
    wo = SE.without({"net_margin": -0.05}, _DOLLARS, _fig(net_income=6_400.0, revenue=56_000.0))
    assert wo["columns"]["net_margin"]["why"] == "resto"


def test_plausible_change_stays():
    """Quitar a una empresa que pesa poco no cambia la referencia de forma sospechosa."""
    wo = SE.without({"net_margin": 0.10}, _DOLLARS, _fig(net_income=1_200.0, revenue=10_000.0, mcap=8_000.0))
    assert wo["columns"]["net_margin"]["how"] == "sin_empresa"
    assert abs(wo["values"]["net_margin"] - (0.10 * 500_000 - 1_200) / 490_000) < 1e-12


def _roe_alerts(roe, ke, industry_roe=0.40, equity_to_assets=None, roa=0.08):
    ratios = {"roe": roe, "roa": roa}
    fin = {"industry_roe": industry_roe, "cost_of_equity": ke, "equity_to_assets": equity_to_assets}
    out = build_signals(ratios, fin, sector="Technology", archetype="MATURE")
    return [x for k in ("red_flags", "warnings", "strengths") for x in out[k] if "ROE" in str(x.get("reason"))]


def test_no_low_roe_when_it_covers_cost_of_equity():
    """META: ROE 26,2 % frente a una industria del 40 %, con un Ke del 9,6 %: el accionista está remunerado."""
    assert _roe_alerts(0.262, 0.096) == []
    assert "bajo" in _roe_alerts(0.08, 0.096)[0]["reason"]


def test_tiny_equity_roe_is_neither_strength_nor_warning():
    """CL: patrimonio 1,7 % de los activos, ROE 713 %: antes «ROE excepcional»."""
    assert _roe_alerts(7.13, 0.088, industry_roe=0.24, equity_to_assets=0.017) == []
    assert _roe_alerts(7.13, 0.088, industry_roe=0.24, equity_to_assets=0.20) != []


def _score(roe, eta, de=None):
    return score_rentabilidad(roe, 0.12, 0.25, 0.15, sector_roe_threshold=0.10, sector_roa_threshold=0.04,
                              sector_roe_high=0.20, sector_roa_high=0.08, debt_to_equity=de, sector_de_threshold=2.0,
                              equity_to_assets=eta)


def test_tiny_equity_roe_does_not_score():
    s = _score(7.13, 0.017)
    roe = next(x for x in s["adjustments"] if x["metric"] == "ROE")
    assert roe["value"] == "n.s." and roe["adjustment"] == 0
    assert next(x for x in _score(0.30, 0.40)["adjustments"] if x["metric"] == "ROE")["adjustment"] > 0


def test_tiny_equity_roe_is_not_presented():
    r = {"key_metrics": {"roe": 7.13, "total_equity": 0.6e9, "total_assets": 35e9}, "ratios": {"roe": 7.13},
         "classification": {"archetype": "MATURE"}, "sector_info": {"sector": "Consumer Defensive"}}
    flags = validate_outputs(r)
    assert r["key_metrics"]["roe"] is None and any("1.7 %" in f["reason"] for f in flags)


def test_financials_keep_their_roe():
    """Bancos, aseguradoras y gestoras: el apalancamiento es su negocio (AMP, APO y PFG no son FINANCIAL)."""
    for arch, sector in (("FINANCIAL", "Financial Services"), ("MATURE", "Financial Services")):
        r = {"key_metrics": {"roe": 0.30, "total_equity": 1e9, "total_assets": 100e9}, "ratios": {"roe": 0.30},
             "classification": {"archetype": arch}, "sector_info": {"sector": sector}}
        validate_outputs(r)
        assert r["key_metrics"]["roe"] == 0.30
