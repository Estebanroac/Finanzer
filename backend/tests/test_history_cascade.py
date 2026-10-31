"""
F8 (auditoría externa del 26-oct-2026): historia de 10 años con EDGAR en cascada (capex, margen operativo y BPA).

Un concepto de relevo solo entra si es el único que usa el emisor, si coincide con la serie en el último ejercicio común
(y solo para los posteriores), o, el BPA de continuadas, si cuadra con beneficio / acciones en cada ejercicio. La otra
taxonomía completa los ejercicios anteriores al cambio de norma solo si coincide en un ejercicio común. Lo que falta es
«sin dato» con su motivo, no se completa con Yahoo y la persistencia no se mide sobre ello. Cifras de LLY, VZ, SHEL y
TM de companyfacts (26-oct-2026; registro F8_INDEPENDIENTES §historia).
"""
import history_10y as H
import persistence as P
import sec_edgar as edgar
from test_edgar_history import _f, _facts, _years


def _fy(tax, unit, concept_values, end="12-31"):
    return {"units": {unit: [_f(f"{y - 1}-04-01" if end == "03-31" else f"{y}-01-01", f"{y}-{end}", v,
                                f"{y}-06-20" if end == "03-31" else f"{y + 1}-02-01", "20-F" if tax == "ifrs-full"
                                else "10-K", f"k{y}") for y, v in concept_values]}}


def test_lly_capex_con_el_unico_concepto_que_usa():
    vals = [(2022, 1.85e9), (2023, 3.45e9), (2024, 5.06e9), (2025, 7.84e9)]
    h = edgar.annual_history(_facts(PaymentsToAcquireOtherPropertyPlantAndEquipment=_years(vals)), "capex")
    assert [v["value"] for v in h["values"]] == [-7.84e9, -5.06e9, -3.45e9, -1.85e9]
    assert h["relay"][0]["how"].startswith("único concepto")


def test_vz_capex_relevo_verificado_y_solo_posterior():
    """VZ: PaymentsToAcquireProductiveAssets hasta 2018; desde 2017, PaymentsToAcquireOtherProductiveAssets (igual en
    2017 y 2018). Antes de 2017 el otro concepto era una partida menor (2014: 0,18): no entra."""
    facts = _facts(PaymentsToAcquireProductiveAssets=_years([(2014, 17.19e9), (2017, 17.25e9), (2018, 16.66e9)]),
                   PaymentsToAcquireOtherProductiveAssets=_years([(2014, 0.18e9), (2017, 17.25e9), (2018, 16.66e9),
                                                                  (2019, 17.94e9), (2025, 17.01e9)]))
    h = edgar.annual_history(facts, "capex")
    by = {v["fy_end"][:4]: -v["value"] for v in h["values"]}
    assert by == {"2025": 17.01e9, "2019": 17.94e9, "2018": 16.66e9, "2017": 17.25e9, "2014": 17.19e9}
    assert "2018" in h["relay"][0]["how"]


def test_relevo_que_no_coincide_no_entra():
    facts = _facts(PaymentsToAcquireProductiveAssets=_years([(2017, 17.25e9), (2018, 16.66e9)]),
                   PaymentsToAcquireOtherProductiveAssets=_years([(2018, 0.5e9), (2019, 0.6e9)]))
    h = edgar.annual_history(facts, "capex")
    assert [v["fy_end"][:4] for v in h["values"]] == ["2018", "2017"] and not h.get("relay")


def test_shel_bpa_de_continuadas_si_cuadra_con_beneficio_entre_acciones():
    ni = [(2024, 16.09e9), (2025, 17.5e9)]
    sh = [(2024, 6.36e9), (2025, 6.0e9)]
    eps = [(2024, 2.53), (2025, 3.40)]          # 2025 no cuadra (17,5 / 6,0 = 2,92): discontinuadas → fuera
    facts = _facts(tax="ifrs-full", ProfitLossAttributableToOwnersOfParent=_fy("ifrs-full", "USD", ni),
                   AdjustedWeightedAverageShares=_fy("ifrs-full", "shares", sh),
                   DilutedEarningsLossPerShareFromContinuingOperations=_fy("ifrs-full", "USD/shares", eps))
    h = edgar.annual_history(facts, "diluted_eps")
    assert [(v["fy_end"][:4], v["value"]) for v in h["values"]] == [("2024", 2.53)]
    assert "cuadra" in h["relay"][0]["how"]


def test_tm_otra_taxonomia_solo_si_coincide():
    """TM pasa a NIIF en el FY2021. FY2020 en las dos: resultado operativo 2.442,87 (US GAAP) y 2.399,23 (NIIF),
    −1,8 %: completa; flujo operativo 3.590,64 y 2.398,50, −33 %: no completa y se dice."""
    facts = _facts(tax="ifrs-full", unit="JPY", assets_end="2025-03-31")
    facts["facts"]["ifrs-full"].update(
        ProfitLossFromOperatingActivities=_fy("ifrs-full", "JPY", [(2020, 2399.23e9), (2021, 2197.75e9),
                                                                    (2025, 4795.59e9)], "03-31"),
        CashFlowsFromUsedInOperatingActivities=_fy("ifrs-full", "JPY", [(2020, 2398.5e9), (2025, 3696.93e9)], "03-31"))
    facts["facts"]["us-gaap"] = {
        "OperatingIncomeLoss": _fy("us-gaap", "JPY", [(2019, 2467.55e9), (2020, 2442.87e9)], "03-31"),
        "NetCashProvidedByUsedInOperatingActivities": _fy("us-gaap", "JPY", [(2019, 3766.6e9), (2020, 3590.64e9)],
                                                          "03-31")}
    op = edgar.annual_history(facts, "operating_income")
    assert "2019-03-31" in [v["fy_end"] for v in op["values"]] and op["cross_taxonomy"]["verified_on"] == "2020-03-31"
    cf = edgar.annual_history(facts, "operating_cash_flow")
    assert "2019-03-31" not in [v["fy_end"] for v in cf["values"]] and cf["cross_taxonomy_rejected"]


def test_sin_concepto_es_sin_dato_con_motivo():
    facts = _facts(Revenues=_years([(y, 100.0) for y in range(2016, 2026)]),
                   NetIncomeLoss=_years([(y, 10.0) for y in range(2016, 2026)]))
    hist = edgar.history(facts)
    assert hist["capex"]["values"] == [] and "conceptos propios" in hist["capex"]["reason"]
    assert "resultado operativo" in hist["operating_income"]["reason"]
    h = H.build(hist, 10)
    assert "conceptos propios" in h["field_reasons"]["capex"] and "operating_income" in h["field_reasons"]


def test_concepto_que_se_deja_de_usar():
    """JNJ: OperatingIncomeLoss solo en 2010–2014; en la ventana 2016–2025, sin dato con el motivo."""
    facts = _facts(Revenues=_years([(y, 100.0) for y in range(2010, 2026)]),
                   OperatingIncomeLoss=_years([(y, 20.0) for y in range(2010, 2015)]))
    h = H.build(edgar.history(facts), 10)
    assert "hasta el ejercicio 2014" in h["field_reasons"]["operating_income"]


def test_persistencia_no_se_completa_con_yahoo_ni_se_mide_sin_capex():
    """Sin capex ni resultado operativo en EDGAR: Yahoo no los completa; Rentabilidad con el margen neto y Calidad de
    ganancias sin la prueba del FCF (antes: 4 años de Yahoo y el resto «no cumple»)."""
    ys = range(2021, 2026)
    hist = {"revenue": {"values": [{"fy_end": f"{y}-12-31", "value": 100.0} for y in ys]},
            "net_income": {"values": [{"fy_end": f"{y}-12-31", "value": 10.0} for y in ys]},
            "operating_cash_flow": {"values": [{"fy_end": f"{y}-12-31", "value": 15.0} for y in ys]},
            "operating_income": {"values": [], "reason": "x"}, "capex": {"values": [], "reason": "y"}}
    st = {"operating_income": [20.0] * 4, "capital_expenditure": [-30.0] * 4,
          "inc_ends": [f"{y}-12-31" for y in (2025, 2024, 2023, 2022)],
          "cf_ends": [f"{y}-12-31" for y in (2025, 2024, 2023, 2022)]}
    merged = P.merge_history(hist, st)
    assert merged["operating_income"]["values"] == [] and merged["capex"]["values"] == []
    m = P.measure(merged, "MATURE", "edgar")
    assert m["Rentabilidad"]["anchor"] == "margen neto" and "sin resultado operativo" in m["Rentabilidad"]["rule"]
    assert m["Calidad de Ganancias"]["persistence"] == 1.0 and "FCF sin dato" in m["Calidad de Ganancias"]["rule"]
