"""
F13 · reglas de cordura de la revisión externa de 110 empresas (docs/fiabilidad/revision-110-2026-11-05.md).

Cada regla, sobre un análisis mínimo: salta en el caso que la revisión verificó y no salta en el sano. Las reglas miden;
no cambian ninguna salida del motor.
"""
import model_invariants as m


def _st(rule, a):
    return m.RULES[rule][0](a, {})["state"]


def test_rating_contable_flags_a_default_rating_with_positive_cash():
    a = {"wacc": {"value": 0.20, "clamped": True, "rating": {"rating": "D", "coverage": -4.4}},
         "key_metrics": {"operating_income_normalized": 3.1e9, "operating_cash_flow": 4.2e9}}
    assert _st("rating_contable", a) == "violacion"                                      # KHC
    a["key_metrics"] = {"operating_income_normalized": -1e9, "operating_cash_flow": -2e8}
    assert _st("rating_contable", a) == "ok"                                             # impago con caja negativa
    assert _st("rating_contable", {"wacc": {"value": 0.08, "rating": {"rating": "A"}}}) == "ok"


def test_inverso_una_vez_flags_the_reverse_dcf_inside_the_multiples():
    conv = {"methods": [{"method": "DCF inverso"},
                        {"method": "múltiplos frente al sector", "readings": {"P/E": 1.0, "DCF inverso (FFO)": -0.5}}]}
    a = {"confidence": {"dimensions": {"convergence": conv}}}
    assert _st("inverso_una_vez", a) == "violacion"                                      # PSA, PLD
    conv["methods"][1]["readings"].pop("DCF inverso (FFO)")
    assert _st("inverso_una_vez", a) == "ok"


def test_confianza_base_fragil_flags_high_confidence_on_a_fragile_base():
    a = {"confidence": {"level": "alta"}, "price_attractiveness": {"level": "atractivo"},
         "key_metrics": {"free_cash_flow": -28.7e9, "operating_cash_flow": 46.9e9},
         "altman_z": {"applicable": True, "zone": "distress", "z_score": 0.83}}
    assert _st("confianza_base_fragil", a) == "violacion"                                # ORCL
    a["confidence"]["level"] = "media"
    assert _st("confianza_base_fragil", a) == "ok"
    b = {"confidence": {"level": "alta"}, "price_attractiveness": {"level": "muy exigente"},
         "key_metrics": {"pe_normalized": 28.5, "forward_pe": 17.6}}
    assert _st("confianza_base_fragil", b) == "violacion"                                # XEL


def test_commodity_producer_is_cyclical_and_its_peak_does_not_wait_for_consensus():
    nem = {"profile": {"industry": "Gold"}, "classification": {"archetype": "MATURE", "rule": "por_defecto"},
           "earnings_peak": {"flag": False, "ttm_over_median": 1.75, "conditions": {"a": True, "b": False}}}
    assert _st("ciclica_por_industria", nem) == "violacion"
    assert _st("pico_ciclico", nem) == "violacion"
    lly = {"profile": {"industry": "Drug Manufacturers - General"}, "classification": {"archetype": "GROWTH_PROFITABLE"},
           "earnings_peak": {"flag": False, "ttm_over_median": 2.06}}
    assert _st("pico_ciclico", lly) == "no_aplica"                                       # crecimiento, no pico


def test_referencia_acotada_flags_negative_or_inflated_references():
    a = {"benchmark": {"profile": "sector", "values": {"net_margin": -0.081, "roe": 0.24},
                       "industry": {"damodaran": "Cable TV", "self_exclusion": {"method": "sin_empresa", "columns": {
                           "net_margin": {"before": 0.10, "after": -0.081}, "roe": {"before": 0.22, "after": 0.24}}}}}}
    assert _st("referencia_acotada", a) == "violacion"                                   # CMCSA
    a["benchmark"]["values"]["net_margin"] = 0.09
    assert _st("referencia_acotada", a) == "ok"


def test_roe_bajo_only_when_it_does_not_cover_its_cost():
    a = {"alerts": {"warnings": [{"reason": "ROE bajo — 22.5% (TTM)"}]}, "cost_of_equity": {"value": 0.085}}
    assert _st("roe_bajo_coherente", a) == "violacion"                                   # WMT
    a["alerts"]["warnings"][0]["reason"] = "ROE bajo — 6.0% (TTM)"
    assert _st("roe_bajo_coherente", a) == "ok"


def test_roe_with_a_tiny_equity_is_not_a_strength():
    a = {"key_metrics": {"total_equity": 2.88e8, "total_assets": 1.674e10, "roe": 7.13},
         "alerts": {"strengths": [{"reason": "ROE normalizado excepcional — 927.2%"}]}}
    assert _st("roe_patrimonio_infimo", a) == "violacion"                                # CL


def test_utility_regulada_and_its_normalization():
    a = {"classification": {"archetype": "UTILITY"}, "alerts": {"red_flags": [{"reason": "Destruye valor — ROIC 5%"}]}}
    assert _st("utility_regulada", a) == "violacion"
    xel = {"classification": {"archetype": "UTILITY"},
           "earnings_normalization": {"reported_net_income": 2.669e9, "after_tax": {"applied": True, "out": 6.0e8}}}
    assert _st("normalizacion_utility", xel) == "violacion"


def test_ffo_series_without_jumps():
    psa = {"classification": {"archetype": "REIT"},
           "archetype_metrics": {"ffo_per_share_series": [15.6, 17.1, 16.5, 28.7]}}
    assert _st("ffo_sin_saltos", psa) == "violacion"
    psa["archetype_metrics"]["ffo_per_share_series"] = [15.6, 16.1, 16.5, 17.0]
    assert _st("ffo_sin_saltos", psa) == "ok"


def test_abstencion_without_profile_or_price_history():
    ea = {"price_attractiveness": {"level": "exigente"}, "profile": {"sector": "Unknown"},
          "data_provenance": {"price_history": {"rows": 1}}}
    assert _st("abstencion_sin_datos", ea) == "violacion"
    ea["profile"]["sector"], ea["data_provenance"]["price_history"]["rows"] = "Technology", 501
    assert _st("abstencion_sin_datos", ea) == "ok"


def test_flujo_por_intensidad_flags_heavy_investors_valued_on_todays_fcf():
    meta = {"classification": {"archetype": "MATURE"}, "key_metrics": {"operating_cash_flow": 1.16e11,
                                                                        "free_cash_flow": 2.55e10},
            "dcf": {"available": True, "fcf_basis": "FCF − SBC", "upside": -97}}
    assert _st("flujo_por_intensidad", meta) == "violacion"
    meta["key_metrics"]["free_cash_flow"] = 6e10
    assert _st("flujo_por_intensidad", meta) == "ok"


def test_base_inflada_catches_pfizer_2022():
    fcf = [14.4, 14.8, 13.8, 10.5, 12.2, 29.9, 26.0, 4.8, 9.8, 9.1]
    pfe = {"history_10y": {"rows": [{"year": 2016 + i, "free_cash_flow": v * 1e9} for i, v in enumerate(fcf)]}}
    r = m.base_inflada(pfe, {})
    assert r["state"] == "violacion" and "2022" in r["violations"][0]["detail"]
    assert "−29." in r["violations"][0]["detail"]
