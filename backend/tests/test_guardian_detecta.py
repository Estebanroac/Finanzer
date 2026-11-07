"""
Fase 1 del plan de fiabilidad: el guardián narrativo DETECTA. Para cada predicado y cada mecanismo (red de seguridad
en web y en PDF, lista negra, anexo técnico, reglas estructurales): un caso sintético que lo cumple no falla y la
misma frase con el dato violado falla con esa regla. Sin red.
"""
import pytest

import guardian as g
from claims import claim


def _rules(text, claims, a_ok, pdf=""):
    """Reglas que fallan con `text` en el display, registrado con `claims` (None = sin registrar)."""
    a = {"display": {"frase": text}, **a_ok}
    recs = [] if claims is None else [{"text": text, "claims": claims, "source": "test"}]
    return {f["rule"].split(":")[0] for f in g.check(a, pdf, recs)}


KM = "key_metrics"
# predicado -> (frase, afirmaciones, análisis que la cumple, análisis que la viola)
CASES = {
    "ebit_negative": ("con EBIT negativo y caja neta, la cobertura no es significativa",
                      [claim("ebit_negative"), claim("net_cash")],
                      {KM: {"operating_income": -1e8, "net_debt": -5e8}},
                      {KM: {"operating_income": 2.6e9, "net_debt": -5e8}}),
    "no_interest_burden": ("sin carga financiera neta: los ingresos financieros cubren los gastos",
                           [claim("no_interest_burden")],
                           {KM: {"operating_income": 2.6e9, "net_interest_income": 2.9e8}},
                           {KM: {"operating_income": 2.6e9, "net_interest_income": -1e8}}),
    "roce": ("ROCE 68.72% (EBIT / capital empleado, antes de impuestos), 30.2 pp por debajo del ROIC",
             [claim("roce")], {KM: {"roce": 0.687206, "roic": 0.989}}, {KM: {"roce": 0.6971, "roic": 0.989}}),
    "net_cash": ("la posición de caja supera a la deuda total (caja neta)", [claim("net_cash")],
                 {KM: {"net_debt": -1e9}}, {KM: {"net_debt": 4e8}}),
    "net_debt": ("el resultado operativo es negativo y la empresa tiene deuda neta",
                 [claim("net_debt"), claim("ebit_negative")],
                 {KM: {"net_debt": 4e8, "operating_income": -1}}, {KM: {"net_debt": -4e8, "operating_income": -1}}),
    "pos52": ("cotiza en el 95% del rango de 52 semanas, en la zona de máximos", [claim("pos52")],
              {"price": 95.0, KM: {"price_52w_high": 100.0, "price_52w_low": 0.0}},
              {"price": 40.0, KM: {"price_52w_high": 100.0, "price_52w_low": 0.0}}),
    "buyback": ("la compañía recompró un 2.0% neto de sus acciones", [claim("buyback")],
                {KM: {"buyback_yield": 0.02}}, {KM: {"buyback_yield": -0.02}}),
    "growth": ("los ingresos se contraen un 3.0% anual de ciclo medio",
               [claim("growth", value=-0.03, cycle=True, cagr=False)], {}, None),
    "vs_bench": ("ROE de 30.0% frente a 20.0% del sector (+50%): muy superior",
                 [claim("vs_bench", value=0.30, bench=0.20)], {}, None),
    "spread": ("cada dólar reinvertido crea valor económico", [claim("spread")],
               {KM: {"roic_wacc_spread": 0.05}}, {KM: {"roic_wacc_spread": -0.05}}),
    "implied_growth": ("El precio actual exige que el FCF − SBC por acción crezca un 12.5% anual durante 10 años "
                       "(17.0% los 5 primeros y convergencia al 2.5%); en los últimos 10 años, sus ingresos por "
                       "acción crecieron un 11.2% anual.",
                       [claim("implied_growth", field="reverse_dcf.main.g10", value=0.125)],
                       {"reverse_dcf": {"main": {"g10": 0.125, "own_growth": {"cagr": 0.112}}}},
                       {"reverse_dcf": {"main": {"g10": 0.205, "own_growth": {"cagr": 0.112}}}}),
    "implied_return": ("El precio descuenta un ROTE sostenido del 10.1%; el banco obtiene un 10.7% en el último "
                       "ejercicio (ajustado por AT1).",
                       [claim("implied_return", field="archetype_metrics.implied.implied", value=0.101)],
                       {"archetype_metrics": {"implied": {"implied": 0.101, "own": 0.107}}},
                       {"archetype_metrics": {"implied": {"implied": 0.151, "own": 0.107}}}),
    "quality_persistence": ("Por encima de 80 (umbral de persistencia; «excelente» empieza en 85), la calidad exige persistencia: 100 → 93. rentabilidad: margen "
                            "operativo positivo y al menos el 75% del último (29.5%) en 2 de 5 ejercicios.",
                            [claim("quality_persistence", field="quality.persistence.weighted", value=0.65)],
                            {"quality": {"score": 93, "persistence": {"applied": True, "score_before": 100, "weighted": 0.65}}},
                            {"quality": {"score": 96, "persistence": {"applied": True, "score_before": 100,
                                                                      "weighted": 0.65}}}),
    "level_border": ("en la frontera con «exigente» (a 1 punto): un cambio pequeño en los datos o en los supuestos "
                     "cambiaría el nivel",
                     [claim("level_border", field="price_attractiveness.border.points", value=1, part="price")],
                     {"price_attractiveness": {"border": {"neighbor": "exigente", "points": 1}}},
                     {"price_attractiveness": {"border": {"neighbor": "exigente", "points": 2}}}),
    "premortem": ("el FCF − SBC por acción creciera al menos un 8.9% anual durante 10 años, como exige el precio; "
                  "historia propia: sus ingresos por acción, 1.0% anual en 10 años",
                  [claim("premortem", field="reverse_dcf.main.g10", value=0.089, kind_pm="precio_inverso")],
                  {"price_attractiveness": {"level": "muy exigente"},
                   "reverse_dcf": {"main": {"g10": 0.089, "own_growth": {"cagr": 0.010, "years": 10}}}},
                  {"price_attractiveness": {"level": "razonable"},
                   "reverse_dcf": {"main": {"g10": 0.089, "own_growth": {"cagr": 0.010, "years": 10}}}}),
    "market_signal": ("en los 12 meses anteriores al último, la acción subió un 34.3%: el mercado viene premiando la "
                      "acción", [claim("market_signal", field="market_context.signals.momentum_12_1.value",
                                       value=0.343, signal="momentum")],
                      {"market_context": {"signals": {"momentum_12_1": {"value": 0.343}}}},
                      {"market_context": {"signals": {"momentum_12_1": {"value": -0.343}}}}),
    "behavioral": ("Cotiza a un 1.5% de su máximo de 52 semanas. Cerca del máximo, el mercado tiende a infravalorar las "
                   "buenas noticias y a incorporarlas tarde: el máximo actúa como ancla (George y Hwang, 2004).",
                   [claim("behavioral", field="market_context.anchor_gap", value=-0.015, kind_b="anclaje_52s")],
                   {"key_metrics": {"price": 98.5, "price_52w_high": 100.0}, "market_context": {"anchor_gap": -0.015}},
                   {"key_metrics": {"price": 90.0, "price_52w_high": 100.0}, "market_context": {"anchor_gap": -0.015}}),
    "dcf_upside": ("el valor intrínseco estimado está un 20% por debajo del precio", [claim("dcf_upside")],
                   {"dcf": {"upside": -20.0}}, {"dcf": {"upside": 20.0}}),
    "dcf_rel": ("DCF no concluyente (fiabilidad baja)", [claim("dcf_rel")],
                {"dcf": {"reliability": {"level": "baja"}}}, {"dcf": {"reliability": {"level": "alta"}}}),
    "altman_zone": ("Altman Z de 2.31 (zona gris)", [claim("altman_zone")],
                    {"altman_z": {"zone": "grey"}}, {"altman_z": {"zone": "safe"}}),
    "runway": ("la empresa está autofinanciada", [claim("runway")],
               {"archetype_metrics": {"runway": {"state": "autofinanciada"}}},
               {"archetype_metrics": {"runway": {"state": "runway"}}}),
    "price_contraction": ("ajustado de 30 a 35 por confianza media",
                          [claim("price_contraction", raw=30, score=35, confidence="media")],
                          {"price_attractiveness": {"score_raw": 30, "score": 35, "confidence": "media"},
                           "confidence": {"level": "media"}},
                          {"price_attractiveness": {"score_raw": 30, "score": 40, "confidence": "media"},
                           "confidence": {"level": "media"}}),
    "price_l1": ("P/E 36.2x frente a la mediana de tecnología (27.8x), 1.30 veces: en el tercio más caro del universo",
                 [claim("price_l1", pe=36.21, median=27.8, relative=1.3025, level="exigente")],
                 {"price_attractiveness": {"rule": "L1", "pe_ttm": 36.21, "sector_median": 27.8, "relative": 1.3025,
                                           "level": "exigente"}},
                 {"price_attractiveness": {"rule": "L1", "pe_ttm": 36.21, "sector_median": 30.1, "relative": 1.2030,
                                           "level": "exigente"}}),
    "basis": ("Crecimiento de ingresos (3 años)", [claim("basis", per="3 años", metric="revenue_growth")],
              {"classification": {"archetype": "MATURE"}}, {"classification": {"archetype": "CYCLICAL"}}),
    "eps_vs_revenue": ("el BPA crece más rápido que los ingresos",
                       [claim("eps_vs_revenue", eps=0.10, revenue=0.05)], {}, None),
    "next_earnings": ("Fecha anunciada (2 de noviembre de 2026, tras el cierre) en el calendario de resultados de "
                      "Finnhub.",
                      [claim("next_earnings", field="market_context.next_earnings.date", value="2026-11-02",
                             kind_ne="anunciada")],
                      {"market_context": {"next_earnings": {"date": "2026-11-02", "kind": "anunciada"}}},
                      {"market_context": {"next_earnings": {"date": "2026-11-02", "kind": "estimada"}}}),
    "share_dilution_3y": ("la emisión de acciones crece más deprisa que el FFO, y diluye al accionista",
                          [claim("share_dilution_3y")],
                          {"growth_basis": {"shares_cagr_3y": 0.05}}, {"growth_basis": {"shares_cagr_3y": 0.0005}}),
}
# Para los predicados que comparan el texto con el valor declarado, la violación cambia la afirmación.
BAD_CLAIMS = {
    "growth": [claim("growth", value=+0.03, cycle=True, cagr=False)],          # verbo 'se contraen' con +3%
    "vs_bench": [claim("vs_bench", value=0.10, bench=0.20)],                    # 'superior' con brecha negativa
    "eps_vs_revenue": [claim("eps_vs_revenue", eps=0.02, revenue=0.05)],
}


def test_every_predicate_has_a_case():
    assert set(CASES) == set(g.PREDICATES)


@pytest.mark.parametrize("kind", sorted(CASES))
def test_predicate_detects_its_violation(kind):
    text, cl, ok, bad = CASES[kind]
    assert kind not in _rules(text, cl, ok), "el caso correcto no debe fallar"
    if bad is not None:
        assert kind in _rules(text, cl, bad)
    else:
        assert kind in _rules(text, BAD_CLAIMS[kind], ok)


def test_cycle_bound_must_be_said_as_bound():
    text = "los ingresos se contraen un 5.0% anual de ciclo medio"
    assert "growth" in _rules(text, [claim("growth", value=-0.05, cycle=True)], {})
    said = "los ingresos se contraen un 5.0% anual de ciclo medio (acotado al mínimo que admite el modelo)"
    assert "growth" not in _rules(said, [claim("growth", value=-0.05, cycle=True)], {})


def test_declared_value_must_match_the_field():
    cl = [claim("net_cash", field="key_metrics.net_debt", value=-5.0)]
    assert "net_cash" in _rules("con caja neta", cl, {KM: {"net_debt": -7.0}})      # valor declarado ≠ campo
    assert "net_cash" not in _rules("con caja neta", cl, {KM: {"net_debt": -5.0}})


def test_unbacked_claim_word_fails_in_display_and_pdf():
    assert "sin_respaldo" in _rules("la empresa tiene caja neta", None, {})
    assert "sin_respaldo" in _rules("sin afirmaciones", None, {}, pdf="la empresa tiene caja\nneta de sobra")
    # registrada con una afirmación de OTRO tipo tampoco vale
    assert "sin_respaldo" in _rules("la empresa tiene caja neta", [claim("spread")], {KM: {"roic_wacc_spread": 1}})


def test_pdf_word_traced_to_a_display_sentence_across_line_breaks():
    text = "la posición de caja supera a la deuda total (caja neta)"
    pdf = "la posición de caja supera a la deuda total (caja\nneta). La deuda es servible"
    assert "sin_respaldo" not in _rules(text, [claim("net_cash")], {KM: {"net_debt": -1}}, pdf=pdf)


def test_fragment_not_in_the_report_is_not_evaluated():
    a = {"display": {"frase": "otra cosa"}, KM: {"operating_income": 5.0}}
    recs = [{"text": "EBIT negativo", "claims": [claim("ebit_negative")], "source": "t"}]
    assert not [f for f in g.check(a, "", recs) if f["rule"] == "ebit_negative"]


def test_english_and_codes_fail_outside_the_annex():
    assert "ingles" in _rules("Salud financiera bancaria de 10/10 (STRONG)", [], {})
    assert "codigo_interno" in _rules("Arquetipo por defecto (regla por_defecto)", [], {})
    pdf = "Informe en castellano.\nDetalle técnico para auditoría\nArquetipo MATURE (regla por_defecto)"
    rules = {f["rule"] for f in g.check({"display": {}}, pdf, [])}
    assert not rules & {"ingles", "codigo_interno"}, rules
    assert {"ingles", "codigo_interno"} <= {f["rule"] for f in g.check({"display": {}}, pdf.replace(
        "Detalle técnico para auditoría", "Detalle"), [])}


def test_market_benchmark_must_not_say_sector():
    a = {"benchmark": {"profile": "market"}}
    assert "referencia_mercado" in _rules("múltiplos frente al sector", [], a)
    assert "referencia_mercado" not in _rules("múltiplos frente al mercado", [], a)
    assert "referencia_mercado" not in _rules("múltiplos frente al sector", [], {"benchmark": {"profile": "sector"}})


def test_not_applicable_card_with_a_figure_fails():
    """#10: la tarjeta que no aplica no lleva cifra (AMT margen neto 31.1% con "No aplica")."""
    bad = {"summary": {"cards": [{"key": "net_margin", "label": "Margen neto", "value": "31.1", "pill": "No aplica",
                                  "state": "no_aplica"}]}}
    ok = {"summary": {"cards": [{"key": "net_margin", "label": "Margen neto", "value": "—", "pill": "No aplica",
                                 "state": "no_aplica"}]},
          "cover": {"kpis": [{"key": "roe", "label": "ROE", "value": "—", "state": "no_aplica"}]}}
    kpi = {"cover": {"kpis": [{"key": "roe", "label": "ROE", "value": "91.40%", "state": "no_aplica"}]}}
    rules = lambda d: {f["rule"] for f in g.check({"display": d}, "", [])}
    assert "no_aplica_con_cifra" in rules(bad) and "no_aplica_con_cifra" in rules(kpi)
    assert "no_aplica_con_cifra" not in rules(ok)
    row = {"sections": {"valuation": {"rows": [{"key": "fcf_yield", "label": "FCF Yield", "value": "29.31%",
                                                "reading": "No aplica a bancos y aseguradoras", "state": "no_aplica"}]}}}
    assert "no_aplica_con_cifra" in rules(row)                       # BCS: la tabla también (registro #14)
    row["sections"]["valuation"]["rows"][0]["value"] = "—"
    assert "no_aplica_con_cifra" not in rules(row)


def test_position_in_52w_range_is_between_0_and_100():
    """XOM: "cotiza en el 101% del rango de 52 semanas" con el precio por encima del máximo de la fuente."""
    text = "cotiza en el 101% del rango de 52 semanas, en la zona de máximos"
    above = {"price": 101.0, KM: {"price_52w_high": 100.0, "price_52w_low": 0.0}}
    assert "pos52" in _rules(text, [claim("pos52")], above)
    ok = {"price": 100.0, KM: {"price_52w_high": 100.0, "price_52w_low": 0.0}}
    assert "pos52" not in _rules("cotiza en el 100% del rango de 52 semanas, en la zona de máximos",
                                 [claim("pos52")], ok)


def test_negative_multiple_on_a_card_fails():
    rules = lambda d: {f["rule"] for f in g.check({"display": d}, "", [])}
    assert "ratio_negativo_en_tarjeta" in rules({"cover": {"kpis": [
        {"key": "net_debt_to_ebitda", "label": "Deuda neta/EBITDA", "value": "-3.45x", "state": "con_dato"}]}})
    assert "ratio_negativo_en_tarjeta" in rules({"summary": {"cards": [
        {"key": "ev_ebitda", "label": "EV/EBITDA", "value": "-5.4", "unit": "x", "state": "con_dato"}]}})
    assert "ratio_negativo_en_tarjeta" not in rules({"cover": {"kpis": [
        {"key": "net_cash", "label": "Caja neta", "value": "$9.04B", "state": "con_dato"},
        {"key": "net_margin", "label": "Margen neto", "value": "-20.10%", "state": "con_dato"}]}})


def test_dividend_identities():
    """BCS (fase 1): 50.30% de dividend yield con payout 28.2% y E/P 13.6% (lo que paga: 3.8%)."""
    ids = lambda a: {r for r, _ in g.identities(a)}
    bcs = {KM: {"dividend_yield": 0.503, "payout_ratio": 0.282, "earnings_yield": 0.136,
                "buyback_yield": 0.0386, "shareholder_yield": 0.5416}}
    assert "identidad_dividendo" in ids(bcs)
    ok = {KM: {"dividend_yield": 0.0231, "payout_ratio": 0.772, "earnings_yield": 0.036,
               "buyback_yield": 0.01, "shareholder_yield": 0.0331}}
    assert not ids(ok)
    reit = {KM: {"dividend_yield": 0.0588, "payout_ratio": 0.7865, "payout_basis": "ffo", "p_ffo": 13.7,
                 "earnings_yield": 0.0245}}   # O: el payout es sobre el FFO, no sobre el beneficio
    assert not ids(reit)
    assert "identidad_shareholder" in ids({KM: {"dividend_yield": 0.02, "buyback_yield": 0.01,
                                                "shareholder_yield": 0.05}})
    flagged = {KM: {"dividend_yield": None, "buyback_yield": 0.0386, "shareholder_yield": 0.0386},
               "data_validation": [{"rule": "dividendo_sin_fuente", "old": None}]}
    assert "identidad_shareholder" in ids(flagged)
    scored = {KM: {"dividend_yield": None, "shareholder_yield": None},
              "data_validation": [{"rule": "identidad_dividendo", "old": 0.503}],
              "financial_health": {"details": [{"detail": "Dividendo sostenible (50.30%)"}]}}
    assert "identidad_no_puntua" in ids(scored)


def _dv(rate, ttm, price, **kw):
    pay = {"ttm_total": ttm, "extraordinary": kw.pop("extraordinary", [])}
    return {"price": price, "data_provenance": {"dividend": {"rate": rate, "payments": pay, **kw}}}


def test_dividend_identity_two_directions_fase_2b():
    """Fase 2b: magnitudes equivalentes (indicado frente a lo cobrado en 12 meses, la misma unidad)."""
    ids = lambda a: {r for r, _ in g.identities(a)}
    # NVDA: 0.25 × 4 = 1.00 con 0.52 cobrados y payout × E/P muy por debajo: una subida verificada no se anula.
    nvda = {KM: {"dividend_yield": 1.0 / 221.3, "payout_ratio": 0.035, "earnings_yield": 0.024},
            **_dv(1.0, 0.52, 221.3, change={"kind": "aumento", "date": "2026-06-04", "from": 0.01, "to": 0.25})}
    assert not ids(nvda)
    sin_subida = {KM: dict(nvda[KM]), **_dv(1.0, 0.40, 221.3)}
    assert "identidad_dividendo" in ids(sin_subida)
    # PGR: 0.40 indicado frente a 13.90 cobrados: vale con el extraordinario separado, no sin él.
    pgr = {KM: {"dividend_yield": 0.4 / 210.0}, **_dv(0.4, 13.9, 210.0,
                                                    extraordinary=[{"date": "2026-01-02", "amount": 13.6}])}
    assert not ids(pgr)
    pgr_mudo = {KM: {"dividend_yield": 0.4 / 210.0}, **_dv(0.4, 13.9, 210.0)}
    assert "identidad_dividendo" in ids(pgr_mudo)
    # BCS: el yield tiene que ser el indicado por ADR / el precio del ADR (no 11.5 peniques / 22.79 dólares).
    bcs = {KM: {"dividend_yield": 11.5 / 22.79}, **_dv(0.62, 0.62, 22.79)}
    assert "identidad_dividendo" in ids(bcs)
    assert not ids({KM: {"dividend_yield": 0.62 / 22.79}, **_dv(0.62, 0.62, 22.79)})


def test_structural_rules():
    v = {"text": "Calidad sólida · precio razonable"}
    assert "veredicto" in {f["rule"] for f in g.check(
        {"verdict": v, "display": {"cover": {"verdict": {"text": "Calidad débil · precio razonable"}}}}, "", [])}
    assert "base_ttm" in {f["rule"] for f in g.check(
        {"data_provenance": {"ttm": {"basis": "anual"}}, "display": {}}, "P/E (TTM) 17.0", [])}
    cur = {"data_provenance": {"currency": {"statements": "TWD", "price": "USD", "converted": True}}}
    note = {"cover": {"currency_note": "Estados en EUR convertidos a USD"}}
    assert "moneda" in {f["rule"] for f in g.check({**cur, "display": note}, "", [])}


def test_saying_there_is_no_ttm_is_not_a_ttm_claim():
    """F2a (UL, base anual): "Beneficio FY2025 (sin TTM)" y "sin TTM: estados anuales" dicen lo correcto; la regla
    solo salta cuando el texto afirma TTM."""
    anual = {"data_provenance": {"ttm": {"basis": "anual"}}, "display": {}}
    pdf = "beneficio fy2025 (sin ttm): reportado $10.70b · calidad de fuente (media): sin ttm: estados anuales"
    assert "base_ttm" not in {f["rule"] for f in g.check(anual, pdf, [])}
    assert "base_ttm" in {f["rule"] for f in g.check(anual, pdf + " · p/e (ttm) 17.0", [])}


def test_reit_ffo_fall_cites_issuance_only_when_shares_grow():
    """T3.6 (AMT): con acciones planas la caída del FFO por acción no se atribuye a la emisión."""
    from alert_interpretations import Ctx, _growth
    from settings import cfg
    thr = cfg("thresholds.growth.per_share_min_shares_cagr")

    def text(sh):
        ctx = Ctx({}, {"revenue_cagr_3y": -0.038}, sector="real estate", real_sector="Real Estate",
                  archetype="REIT", archetype_values={"shares_cagr_3y": sh})
        return _growth(ctx)["detail"] if isinstance(_growth(ctx), dict) else str(_growth(ctx))
    assert "emisión de acciones" in text(thr + 0.01)
    assert "emisión de acciones" not in text(0.0005) and "+0.05%" in text(0.0005)
    assert "se reduce un 1.50%" in text(-0.015)


def test_pead_drift_said_backwards_fails():
    """Fase 5 (PEAD): la deriva dicha en la dirección de la sorpresa cuando va en contra, o con otra cifra, falla."""
    P = {"status": "ok", "period": "2026-06-30", "announced": "2026-07-29", "actual": 4.74, "estimate": 4.33,
         "surprise": 0.0947, "reaction": 0.146, "drift": -0.05, "sessions": 53, "window": 60, "window_passed": False}
    text = ("resultados del trimestre cerrado el 2026-06-30, publicados el 2026-07-29: BPA de 4.74 frente a 4.33 de "
            "consenso, una sorpresa del +9.5%. Entre la sesión anterior al anuncio y la siguiente, la acción +14.6% "
            "frente al S&P 500; en las 53 sesiones siguientes, −5.0% frente al S&P 500: la deriva va en la dirección "
            "de la sorpresa.")
    c = claim("market_signal", field="market_context.pead.surprise", value=0.0947, signal="pead")
    assert g.PREDICATES["market_signal"]({"market_context": {"pead": P}}, c, g.norm(text))
    ok = text.replace("en la dirección", "en contra")
    assert not g.PREDICATES["market_signal"]({"market_context": {"pead": P}}, c, g.norm(ok))
    assert g.PREDICATES["market_signal"]({"market_context": {"pead": dict(P, drift=-0.08)}}, c, g.norm(ok))



def test_dcf_percentages_say_what_the_sentence_says():
    """V7 (M1): «el precio excede en 66%» con $343 frente a $116 es falso (excede un 195%); «el valor está un 66% por
    debajo del precio» es lo correcto. El guardián lo detecta en las dos direcciones."""
    aapl = {"price": 343.0, "dcf": {"upside": -66.2, "fair_value": 116.0}}
    claims = [claim("dcf_upside")]
    assert "dcf_upside" in _rules("el precio excede en 66% el valor intrínseco estimado", claims, aapl)
    assert "dcf_upside" in _rules("el precio está un 66% por encima del valor intrínseco estimado", claims, aapl)
    assert "dcf_upside" not in _rules("el precio excede en 196% el valor intrínseco estimado", claims, aapl)
    assert "dcf_upside" not in _rules("el valor intrínseco estimado ($116) está un 66% por debajo del precio ($343)",
                                      claims, aapl)
    assert "dcf_upside" in _rules("el valor intrínseco estimado está un 40% por debajo del precio", claims, aapl)


def test_roe_and_growth_say_their_period():
    """V7 (M2): el ROE de la prosa lleva su periodo (TTM, último ejercicio o FY del DuPont) y la ventana de un
    crecimiento a 3 años es la de los estados."""
    a = {"growth_basis": {"revenue_window": "FY2022–FY2025"}}
    assert "periodo_roe" in _rules("el ROE de 119.9% es excepcional para su sector", None, a)
    assert "periodo_roe" in _rules("ROE excepcional — 119.9%", None, a)
    assert "periodo_roe" not in _rules("el ROE (TTM) de 119.9% es excepcional para su sector", None, a)
    assert "periodo_roe" not in _rules("ROE de FY2025: 151.9% = margen neto 26.9%", None, a)
    assert "periodo_roe" not in _rules("se justificaría con un ROE del 21.6%, 3.96 veces el valor contable", None, a)
    assert "ventana_crecimiento" in _rules("el BPA crece 6.9% anual en 3 años (FY2021–FY2024)", None, a)
    assert "ventana_crecimiento" not in _rules("el BPA crece 6.9% anual en 3 años (FY2022–FY2025)", None, a)


def test_labels_follow_the_number():
    """V7 (M3): «FCF estable (-3.9%)» y un KPI «En rango» sin referencia son etiquetas que el número no sostiene."""
    assert "etiqueta_signo" in _rules("FCF estable (-3.9%)", None, {})
    assert "etiqueta_signo" not in _rules("FCF estable (-1.5%)", None, {})
    assert "etiqueta_signo" not in _rules("FCF en ligero descenso (-3.9%)", None, {})
    card = {"label": "ROE", "value": "119.9", "pill": "En rango", "bench": ""}
    a = {"display": {"summary": {"cards": [card]}}}
    assert "kpi_sin_referencia" in {f["rule"] for f in g.check(a, "", [])}
    a["display"]["summary"]["cards"][0] = dict(card, pill="Sin referencia")
    assert "kpi_sin_referencia" not in {f["rule"] for f in g.check(a, "", [])}


def test_reader_texts_without_internal_mechanics():
    """V7 (M4): «−0.53 × 6 (máximo con 5 miembros)», «^TNX no disponible… valor de config», «grid completo» y
    «(factor 1.0): sin ajustar 15» son mecánica del motor: fuera de la prosa (la fórmula va al anexo)."""
    for t in ("= -0.53 × 6 (máximo con 5 miembros) = -3.2", "Rf: ^TNX no disponible (sin cotización): valor de config",
              "el grid completo (68.77–218.01) no contiene el precio", "(factor 1.0): sin ajustar 15 → ajustado a 15"):
        assert "mecanica_interna" in _rules(t, None, {}), t
    assert "mecanica_interna" not in _rules("la tabla de sensibilidad del DCF (de $68.77 a $218.01) no contiene el "
                                            "precio ($342.96)", None, {})


def test_scoring_names_say_what_scores():
    """V7 (M5): «DCF (upside) −4» junto a «el DCF directo no concilia… se usa el DCF inverso» se contradecían (F8 · E8: «tiene fiabilidad baja»)."""
    def a_with(metric, reason, value="-66%"):
        return {"score": {"breakdown": {"Valoración": {"adjustments": [
            {"metric": metric, "reason": reason, "value": value, "adjustment": -4}]}}}}
    inv = "El DCF directo tiene fiabilidad baja; se usa el DCF inverso: …"
    assert "nombre_puntua" in {f["rule"] for f in g.check(a_with("DCF (upside)", inv), "", [])}
    assert "nombre_puntua" not in {f["rule"] for f in g.check(a_with("DCF inverso (lo que exige el precio)", inv), "", [])}
    off = "DCF de fiabilidad baja: no se usa en el score"
    assert "nombre_puntua" in {f["rule"] for f in g.check(a_with("DCF (upside)", off), "", [])}
    assert "nombre_puntua" not in {f["rule"] for f in g.check(a_with("DCF directo: descartado, no puntúa", off), "", [])}



def test_one_truth_about_the_dcf():
    """V7 (M5, una sola verdad): AAPL. La tarjeta del precio, la línea de «Confianza del veredicto» y la convergencia
    cuentan lo mismo: el DCF directo (fiabilidad baja) no puntúa; el −4 es del DCF inverso y la confianza lo dice."""
    def a_with(row, summary):
        return {"dcf": {"reliability": {"level": "baja"}},
                "display": {"confidence": {"summary": summary},
                            "summary": {"composition": {"price": {"rows": [dict(row, kind="signed")]}}}}}
    ok = ("Confianza del veredicto: alta. El DCF directo, de fiabilidad baja, no puntúa ni cuenta para la "
          "convergencia; en Valoración puntúa el DCF inverso (−4 puntos).")
    inv = {"label": "DCF inverso (lo que exige el precio) · muy exigente", "value": -4}
    rules = lambda a: {f["rule"] for f in g.check(a, "", [])}
    assert "una_verdad" not in rules(a_with(inv, ok))
    assert "una_verdad" in rules(a_with({"label": "DCF (upside) · -66%", "value": -4}, ok))
    assert "una_verdad" in rules(a_with(inv, "Confianza del veredicto: alta. La calidad del negocio no se contrae."))
    assert "una_verdad" in rules(a_with(inv, ok.replace("−4", "−3")))


def test_punctuation_of_the_whole_panel():
    """V7 (puntuación): KO decía «…en 3 de 5 ejercicios.; en la frontera con «sólida»… cambiaría el nivel», con «.;»
    y sin punto final. El guardián mira el texto completo (web y PDF) y exige el cierre de cada frase declarada."""
    def fails(note, pdf=""):
        a = {"display": {"cover": {"quality": {"note": note, "title": "CALIDAD DEL NEGOCIO"}}}}
        return {f["rule"] for f in g.check(a, pdf, [])}
    ko = ("Por encima de 80 (umbral de persistencia; «excelente» empieza en 85), la calidad exige persistencia: 82 → 81. Calidad de ganancias: FCF positivo en 3 de 5 "
          "ejercicios.; en la frontera con «sólida» (a 2 puntos): un cambio pequeño cambiaría el nivel")
    assert {"puntuacion_doble", "frase_sin_cierre"} <= fails(ko)
    assert not {"puntuacion_doble", "frase_sin_cierre"} & fails(ko.replace(".;", ";") + ".")
    for bad in ("Cotiza en la zona media..", "una frase;. otra", "Rentabilidad.\n; sigue"):
        assert "puntuacion_doble" in fails("Nota correcta y cerrada.", pdf=bad), bad
    assert "puntuacion_doble" not in fails("Nota correcta y cerrada.", pdf="Esta lectura sería errónea si…")
    a = {"display": {"nuevo": {"campo": "un texto largo que nadie ha declarado"}}}
    assert "frase_sin_cierre" in {f["rule"] for f in g.check(a, "", [])}


def test_industry_names_in_spanish():
    """V7 (nombres en español): «opera en Beverages—Non-Alcoholic (Consumer Defensive)», «industria REIT - Retail»
    o «(Consumer Electronics)» en la prosa o las fichas; el original solo en la metodología y el anexo."""
    def rules(text, path=("cover", "classification_notes"), pdf=""):
        d = {path[0]: {path[1]: [text]}}
        return {f["rule"] for f in g.check({"display": d}, pdf, [])}
    for t in ("The Coca-Cola Company opera en Beverages—Non-Alcoholic (Consumer Defensive).",
              "Sociedad inmobiliaria cotizada; industria REIT - Retail.", "no muestra ciclo (Consumer Electronics).",
              "Referencia: industria «Computers/Peripherals»; Damodaran clasifica a la empresa en esa industria."):
        assert "industria_en_ingles" in rules(t), t
    assert "industria_en_ingles" in rules("Ficha.", pdf="AAPL · Technology · Consumer Electronics · Nasdaq")
    for t in ("The Coca-Cola Company opera en bebidas sin alcohol (consumo defensivo).",
              "NextEra Energy y Taiwan Semiconductor cotizan en EE. UU.", "Energy Transfer reparte su caja."):
        assert "industria_en_ingles" not in rules(t), t
    # el original sí puede ir en el anexo, en la metodología y en la ficha SIC de la SEC
    assert "industria_en_ingles" not in rules("Industria de referencia: Computers/Peripherals, Damodaran.",
                                               path=("annex", "items"))
    assert "industria_en_ingles" not in rules("Ficha.", pdf="Industria (código SIC) 3674 · Semiconductors & Related")
    assert "industria_en_ingles" not in rules("Ficha.", pdf="Texto.\nMETODOLOGÍA\nindustria «Computers/Peripherals»")

def test_engine_labels_in_spanish():
    """V7 (M6): «Cash Flow Operativo», «EPS moderado», «Crecimiento Ingresos 3Y», «compañías growth» son etiquetas
    del motor sin traducir."""
    for t in ("Cash Flow Operativo", "EPS moderado (6.9%)", "Crecimiento Ingresos 3Y", "un ritmo propio de compañías growth",
              "FCF > Net Income (106.0%)", "Premium (39.3x vs 34.3x)", "PEG Ratio"):
        assert "anglicismo" in _rules(t, None, {}), t
    for t in ("Flujo de caja operativo", "BPA moderado (6.9%)", "Crecimiento de ingresos a 3 años", "Piotroski F-Score"):
        assert "anglicismo" not in _rules(t, None, {}), t
