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


# ═══════════════════════ F16 bis · integridad de los datos de la L1 ═══════════════════════

def test_groups_reit_and_financials_apart_from_their_gics_sector():
    assert L.group("REIT", "Real Estate") == "REIT" and L.group("FINANCIAL", "Financials") == "Financieras"
    assert L.group("MATURE", "Financials") == "Financials" and L.group(None, "Energy") == "Energy"


def test_reit_uses_p_ffo():
    b = L.basis(1e10, {"status": "ok", "ni_ttm": 1e8}, "REIT", {"p_ffo": 18.0}, None, None)
    assert b["metric"] == "P/FFO" and b["multiple"] == 18.0
    b = L.basis(1e10, {"status": "ok", "ni_ttm": 1e8}, "REIT", {"p_ffo": -3.0}, None, None)
    assert b["multiple"] is None and "P/FFO" in b["reason"]


def test_normalized_earnings_same_cut_discontinued_and_losses():
    inp = {"status": "ok", "ni_ttm": 100.0, "end": "2025-09-30", "discontinued": 20.0}
    norm = {"used_in_score": True, "items": [{"applied": True, "net": -30.0, "type": "deterioro"},
                                             {"applied": True, "net": 20.0, "type": "discontinuadas"}]}
    b = L.basis(1000.0, inp, "MATURE", {}, norm, "2025-09-30")
    # 100 − 20 discontinuadas − (−30) deterioro; la partida «discontinuadas» del motor no se resta dos veces
    assert b["earnings"] == 110.0 and b["pe_reported"] == 10.0 and abs(b["multiple"] - 1000 / 110) < 1e-9
    assert b["normalized"] and "sin discontinuadas" in b["notes"]
    b = L.basis(1000.0, {"status": "ok", "ni_ttm": 10.0, "end": "2025-09-30"}, "MATURE", {},
                {"used_in_score": True, "items": [{"applied": True, "net": 15.0, "type": "venta"}]}, "2025-09-30")
    assert b["multiple"] is None and "normalizado" in b["reason"] and "≤ 0" in b["reason"]


def test_other_cut_uses_the_edgar_charges_after_tax():
    inp = {"status": "ok", "ni_ttm": 100.0, "end": "2025-09-30", "charges": {"pretax": -50.0}}
    b = L.basis(1000.0, inp, "MATURE", {}, {"used_in_score": True, "items": [{"applied": True, "net": -999.0}]},
                "2025-06-30", tax_rate=0.2)
    assert b["earnings"] == 140.0 and b["normalized"]                  # 100 − (−50 × 0,8); no las del otro corte
    assert b["notes"] == ["sin cargos ni ventas no recurrentes de EDGAR"]


def test_recurrent_charges_only_the_excess_and_never_a_phantom_charge():
    from normalize import recurrence
    assert recurrence(-0.2, [-1.0, -1.2, -1.1, -0.9])["excess"] == 0.0          # menor que su promedio: nada
    r = recurrence(-3.0, [-1.0, -1.0, -1.0, 0.0])
    assert r["recurrent"] and abs(r["excess"] + 2.0) < 1e-12                    # solo el exceso
    assert recurrence(-3.0, [0.0, -1.0, 0.0, 0.0])["excess"] == -3.0            # no recurrente: todo


def test_pending_statement_is_a_warning_next_to_the_label():
    inp = {"status": "ok", "ni_ttm": 100.0, "end": "2025-06-30",
           "pending": {"form": "10-Q", "report_date": "2025-09-30", "filed": "2025-10-30"}}
    b = L.basis(1000.0, inp, "MATURE", {}, None, None)
    assert "10-Q" in b["warning"] and b["multiple"] == 10.0
    p = L.price(1000.0, inp, "Energy", config=_ref(), l1_basis=b)
    assert p["warning"] == b["warning"]
    import display
    assert "aviso: EDGAR ya tiene el 10-Q" in display.l1_note(p)


def test_small_group_compares_with_the_whole_universe():
    rows = [{"symbol": f"S{i}", "group": "Energy", "pe": 10 + (i % 30)} for i in range(60)]
    rows += [{"symbol": f"R{i}", "group": "Real Estate", "pe": 500.0} for i in range(2)]
    r = L.build_reference(rows, "2026-11-07", "prueba")
    assert r["small_groups"] == ["Real Estate"] and "Real Estate" not in r["sector_median"]
    p = L.price(500.0, {"status": "ok", "ni_ttm": 1.0}, "Real Estate", config=r)
    assert p["median_scope"] == "mercado" and p["sector_median"] == r["market_median"] and p["level"] == "exigente"
    import display
    assert "todo el universo" in display.l1_note(p) and "todo el universo" in display.l1_note_short(p)


def test_losses_and_sales_falling_more_than_30pct_is_not_mature():
    from classify import classify
    st = {"revenue": [10.0, 15.0, 18.0, 20.0], "operating_income": [-3.5, -1.2, 2.4, 4.0], "total_assets": []}
    c = classify(sector="Healthcare", industry="Biotechnology", eps_ttm=-8.0, net_margin_ttm=-0.9, statements_fy=st,
                 operating_margin_ttm=-1.0)
    assert c["archetype"] == "GROWTH_PRE_PROFIT" and c["rule"] == "perdidas_con_ventas_en_caida"
    # un cargo financiero (pérdida neta con margen operativo positivo) no basta
    c = classify(sector="Healthcare", industry="Biotechnology", eps_ttm=-1.0, net_margin_ttm=-0.1, statements_fy=st,
                 operating_margin_ttm=0.1)
    assert c["rule"] != "perdidas_con_ventas_en_caida"


def test_quality_penalizes_ocf_below_net_income_and_eps_growth_is_bounded():
    from settings import cfg
    import alert_interpretations as AI
    assert cfg("thresholds.score.calidad.ocf_below_ni_points") < 0

    class _Ctx:
        def __init__(self, e3, r3, arch="MATURE"):
            self.c, self.archetype = {"eps_cagr_3y": e3, "revenue_cagr_3y": r3}, arch
    pp = cfg("thresholds.dcf_reliability.growth_divergence_pp")
    assert abs(AI.eps_growth_bounded(_Ctx(0.60, 0.10)) - (0.10 + pp)) < 1e-12
    assert AI.eps_growth_bounded(_Ctx(0.12, 0.10)) is None                     # por debajo del tope: sin acotar
    assert AI.eps_growth_bounded(_Ctx(0.60, 0.10, AI.CYCLICAL)) is None        # cíclicas: sin acotar


def test_market_cap_with_the_shares_of_the_earnings():
    inp = {"status": "ok", "ni_ttm": 100.0, "end": "2026-09-30", "concept": "us-gaap:NetIncomeLoss",
           "diluted_shares": 447e6}
    # IBKR: la cotización cuenta todas las unidades (1.690 M), el balance y el beneficio, la clase A (440 M)
    sc = {"basis": "implicito", "factor": 0.26, "statement_shares": 440e6, "price_shares": 1690e6}
    b = L.basis(1690.0, inp, "MATURE", {}, None, "2026-09-30", currency={"converted": False, "share_class": sc})
    assert abs(b["multiple"] - 4.40) < 1e-9 and "acciones del balance" in b["shares_note"]
    # un ADR (con conversión de moneda) no se toca: su capitalización ya está en la clase de la cotización
    b = L.basis(1690.0, inp, "MATURE", {}, None, "2026-09-30", currency={"converted": True, "share_class": sc})
    assert b["multiple"] == 16.9 and b["shares_note"] is None
    # un factor oficial o una fracción simple (desdoblamiento, ADR) tampoco
    b = L.basis(1690.0, inp, "MATURE", {}, None, "2026-09-30",
                currency={"converted": False, "share_class": {**sc, "basis": "inferido"}})
    assert b["shares_note"] is None
    # EDGAR no lo confirma (desdoblamiento posterior que Yahoo aplica hacia atrás): no se toca
    b = L.basis(1690.0, {**inp, "diluted_shares": 90e6}, "MATURE", {}, None, "2026-09-30",
                currency={"converted": False, "share_class": sc})
    assert b["shares_note"] is None
    # un emisor IFRS (ADR que presenta en dólares, BP) tampoco
    b = L.basis(1690.0, {**inp, "concept": "ifrs-full:ProfitLoss"}, "MATURE", {}, None, "2026-09-30",
                currency={"converted": False, "share_class": sc})
    assert b["shares_note"] is None


def test_old_period_without_a_newer_filing_is_warned():
    inp = {"status": "ok", "ni_ttm": 100.0, "end": "2025-12-31"}
    b = L.basis(1000.0, inp, "MATURE", {}, None, "2026-09-30")
    assert b["multiple"] == 10.0 and "2025-12-31" in b["warning"] and "2026-09-30" in b["warning"]
    assert L.basis(1000.0, {**inp, "end": "2026-06-30"}, "MATURE", {}, None, "2026-09-30")["warning"] is None


def test_unread_pending_report_is_retried():
    import sec_edgar
    first = {"status": "ok", "facts_status": "ok", "pending_filings": [
        {"form": "10-Q", "date": "2026-11-05", "read": False, "reason": "presupuesto de EDGAR agotado (3 s)",
         "transient": True}]}
    again = {"status": "ok", "facts_status": "ok", "pending_filings": [{"form": "10-Q", "date": "2026-11-05",
                                                                         "read": True, "reason": None}]}
    r = sec_edgar.retry_if_transient(first, "C", fetcher=lambda *a: again)
    assert r["retried"] and r["pending_filings"][0]["read"]
    # sin informes pendientes sin leer, no se reintenta
    ok = {**again}
    assert sec_edgar.retry_if_transient(ok, "C", fetcher=lambda *a: 1 / 0) is ok
