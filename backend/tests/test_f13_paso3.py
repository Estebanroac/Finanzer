"""
F13 · paso 3 (revisión de 110 empresas, patrón 1): la confianza no cuenta dos veces el DCF inverso y no es «alta» con
una base frágil (valuation_confidence.multiples_signal y fragility_dimension).
"""
import valuation_confidence as vc


def test_reverse_dcf_rows_are_not_multiples():
    """PSA: la fila «DCF inverso (FFO)» entraba en la media de los múltiplos y además era método propio."""
    items = [("P/FFO", 4, -4, -1), ("EV/EBITDA", 4, -4, 0), ("DCF inverso (FFO)", 2, -2, -2),
             ("DCF inverso (flujo de mantenimiento)", 2, -2, -2), ("DCF", 4, -4, -4)]
    s = vc.multiples_signal(items)
    assert not any("DCF" in k for k in s["readings"])
    assert s["components"] == 2 and s["value"] == (-0.25 + 0.0) / 2


def _dims(**kw):
    base = {"convergence": {"level": "alta", "reasons": []}, "coverage": {"level": "alta", "reasons": []},
            "source": {"level": "alta", "reasons": []}, "stability": {"level": "alta", "reasons": []}}
    base.update(kw)
    return base


def test_fragile_base_caps_confidence_at_medium():
    """ORCL: caja libre −28,7 B$ con el flujo operativo positivo y Altman 0,83."""
    fr = vc.fragility_dimension("MATURE", {"free_cash_flow": -28.7e9, "operating_cash_flow": 46.9e9},
                                {"applicable": True, "zone": "distress", "z_score": 0.83})
    assert fr["level"] == "media" and len(fr["reasons"]) == 2
    assert vc.verdict_confidence(_dims(base=fr))["level"] == "media"
    assert vc.verdict_confidence(_dims(base={"level": "alta", "reasons": []}))["level"] == "alta"


def test_normalized_against_forward_gap_is_fragile():
    """XEL: P/E normalizado 28,5x frente a un forward de 17,8x (+60 %)."""
    fr = vc.fragility_dimension("UTILITY", {"pe_normalized": 28.5, "forward_pe": 17.8}, None)
    assert fr["level"] == "media"
    assert vc.fragility_dimension("UTILITY", {"pe_normalized": 20.0, "forward_pe": 17.8}, None)["level"] == "alta"


def test_bank_negative_fcf_is_not_fragile():
    """En un banco el FCF no mide nada (depósitos y préstamos son su operación)."""
    assert vc.fragility_dimension("FINANCIAL", {"free_cash_flow": -15e9, "operating_cash_flow": 3e9}, None)[
        "level"] == "alta"


def test_referential_altman_is_not_a_fragility_signal():
    """TM: con financiera cautiva el Z de Altman es solo referencial (business_model.altman_referential)."""
    z = {"applicable": True, "zone": "distress", "z_score": 1.59}
    assert vc.fragility_dimension("MATURE", {}, z, altman_referential=True)["level"] == "alta"
    assert vc.fragility_dimension("MATURE", {}, z)["level"] == "media"
