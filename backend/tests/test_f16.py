"""F16: la etiqueta de precio es la regla L1 de la prueba hacia atrás (lib/precio_l1.py)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))

import precio_l1 as L  # noqa: E402
import verdict as V  # noqa: E402


def _ref():
    rows = []
    for i in range(1, 91):          # tres sectores con P/E 10..39 repetidos: mediana 24,5 en cada uno
        rows.append({"symbol": f"S{i}", "gics_sector": ("Energy", "Utilities", "Financials")[i % 3],
                     "pe": 10 + (i % 30)})
    rows.append({"symbol": "NEG", "gics_sector": "Energy", "pe": None})
    return L.build_reference(rows, "2026-11-06", "prueba")


def test_reference_has_sector_medians_cuts_and_quantiles():
    r = _ref()
    assert r["n"] == 90 and set(r["sector_median"]) == {"Energy", "Utilities", "Financials"}
    assert len(r["relative_quantiles"]) == 101 and r["cuts"][0] < 1 < r["cuts"][1]


def test_three_levels_by_the_terciles_of_the_relative_pe():
    r = _ref()
    ok = {"status": "ok", "ni_ttm": 1.0}
    med = r["sector_median"]["Energy"]
    cheap = L.price(med * 0.5, ok, "Energy", "media", config=r)
    mid = L.price(med * 1.0, ok, "Energy", "media", config=r)
    dear = L.price(med * 2.0, ok, "Energy", "baja", config=r)
    assert (cheap["level"], mid["level"], dear["level"]) == ("atractivo", "razonable", "exigente")
    assert cheap["score"] > mid["score"] > dear["score"] and cheap["rule"] == "L1"
    assert not dear["contracted"] and dear["level_raw"] == "exigente"        # la confianza no mueve el precio


def test_no_positive_earnings_no_price_verdict():
    r = _ref()
    p = L.price(100.0, {"status": "ok", "ni_ttm": -5.0}, "Energy", "media", config=r)
    assert p["level"] is None and "≤ 0" in p["reason"]
    p = L.price(100.0, {"status": "sin_dato", "reason": "sin estados de SEC EDGAR"}, "Energy", None, config=r)
    assert p["level"] is None and p["reason"] == "sin estados de SEC EDGAR"


def test_reprice_with_another_confidence_keeps_the_l1_level():
    r = _ref()
    p = L.price(r["sector_median"]["Energy"] * 2.0, {"status": "ok", "ni_ttm": 1.0}, "Energy", "media", config=r)
    q = V.reprice(p, "baja")
    assert q["level"] == p["level"] and q["score"] == p["score"] and q["confidence"] == "baja"


def test_verdict_text_with_the_l1_level():
    r = _ref()
    p = L.price(r["sector_median"]["Energy"] * 0.5, {"status": "ok", "ni_ttm": 1.0}, "Energy", "baja", config=r)
    v = V.verdict({"level": "sólida"}, p, {"level": "baja"})
    assert v["text"] == "Calidad sólida · precio atractivo" and v["price_level_raw"] is None


def _f(start, end, val, filed, form="10-Q"):
    return {"start": start, "end": end, "val": val, "filed": filed, "form": form}


def test_ttm_from_cumulative_quarters_like_the_backtest():
    fs = [_f("2024-01-01", "2024-12-31", 400, "2025-02-01", "10-K"),
          _f("2024-01-01", "2024-09-30", 290, "2024-11-01"),
          _f("2025-01-01", "2025-03-31", 110, "2025-05-01"),
          _f("2025-01-01", "2025-06-30", 230, "2025-08-01"),
          _f("2025-01-01", "2025-09-30", 350, "2025-11-01"),
          _f("2024-01-01", "2024-06-30", 190, "2024-08-01"),
          _f("2024-01-01", "2024-03-31", 90, "2024-05-01")]
    v, how = L._Flow("NetIncomeLoss", fs).ttm(L._D("2025-09-30"))
    assert round(v) == 460 and how in ("4 trimestres", "anual + acumulado 273 días − el del año anterior")


def test_profit_loss_minus_minority_when_only_the_consolidated_is_tagged():
    facts = {"facts": {"us-gaap": {
        "ProfitLoss": {"units": {"USD": [_f("2024-10-01", "2025-09-30", 1000, "2025-11-01", "10-K")]}},
        "NetIncomeLossAttributableToNoncontrollingInterest": {"units": {"USD": [
            _f("2024-10-01", "2025-09-30", 50, "2025-11-01", "10-K")]}},
        "Revenues": {"units": {"USD": [_f("2024-10-01", "2025-09-30", 9000, "2025-11-01", "10-K")]}}}}}
    import sec_edgar as edgar
    orig_tax, orig_unit = edgar.taxonomy, edgar.reporting_unit
    edgar.taxonomy, edgar.reporting_unit = (lambda f: "us-gaap"), (lambda f, t: "USD")
    try:
        v, concept, how = L.ni_ttm(facts, L._D("2025-09-30"))
    finally:
        edgar.taxonomy, edgar.reporting_unit = orig_tax, orig_unit
    assert v == 950 and "ProfitLoss" in concept and how == "anual"


def test_sec_edgar_keeps_the_concepts_l1_needs():
    import sec_edgar as edgar
    assert all(c in edgar._WANTED["us-gaap"] for c in L.EXTRA_US)


def test_bands_match_the_config_the_web_reads():
    from settings import cfg
    c = cfg("thresholds.score.price_l1")
    assert list(c["bands"]) == L.BANDS and list(c["labels"]) == L.LABELS


def test_note_cites_the_rule_and_its_figures():
    import display
    t = display.l1_note({"level": "exigente", "pe_ttm": 36.21, "sector_median": 27.8, "relative": 1.3025,
                         "gics_sector": "Information Technology"})
    assert t == "P/E 36.2x frente a la mediana de tecnología (27.8x), 1.30 veces: en el tercio más caro del universo"
    assert display.l1_note({"reason": "beneficio de doce meses ≤ 0: el P/E no tiene sentido"}).startswith(
        "Precio sin veredicto: beneficio")


def test_no_l1_verdict_says_why_in_the_verdict():
    p = L.price(100.0, {"status": "ok", "ni_ttm": -5.0}, "Energy", "media", config=_ref())
    v = V.verdict({"level": "débil"}, p, {"level": "media"})
    assert v["text"] == "Calidad débil · precio sin veredicto"
    assert v["confidence_text"] == "(beneficio de doce meses ≤ 0: el P/E no tiene sentido)"
