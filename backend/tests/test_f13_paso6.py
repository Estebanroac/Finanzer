"""
F13 · paso 6 (revisión de 110 empresas, familia G): utilities sin el diferencial ROIC − WACC, el tipo fiscal recurrente
negativo en la normalización y el espectro solo en operadoras. Cifras del banco congelado del 5-nov-2026 y de EDGAR.
"""
import telecom_spectrum
from alert_interpretations import build_signals
from classify import not_applicable
from normalize import tax_rate_normalized


def test_utility_spread_is_not_applicable():
    """Las 10 utilities del banco tenían «Destruye valor» (spread −1,2 a −3,6 pp) y restaban hasta 4 puntos."""
    assert not_applicable("UTILITY", "roic_wacc") and "regulador" in not_applicable("UTILITY", "roic_wacc")
    out = build_signals({"roic": 0.05}, {}, sector="Utilities", archetype="UTILITY", roic_wacc_spread=-0.029)
    assert not any("valor" in str(x.get("reason")) and "spread" in str(x.get("reason"))
                   for k in ("red_flags", "warnings", "strengths") for x in out[k])


def test_recurrent_negative_tax_rate_is_the_rate():
    """XEL: tipo efectivo negativo cinco años seguidos (créditos fiscales); antes, el legal del 21 %."""
    hist = [(1.81e9, -0.084 * 1.81e9), (1.75e9, -0.09 * 1.75e9), (1.83e9, -0.262 * 1.83e9), (2.0e9, -0.138 * 2.0e9)]
    r = tax_rate_normalized(2.1e9, -0.046 * 2.1e9, hist)
    assert r["rate"] < 0 and "mediana de 5" in r["source"]


def test_one_off_tax_benefit_stays_out_by_the_median():
    hist = [(10e9, 2.1e9), (9e9, 1.9e9), (8e9, -2.0e9), (8e9, 1.6e9)]
    assert abs(tax_rate_normalized(10e9, 2.0e9, hist)["rate"] - 0.20) < 1e-9


def test_rate_below_the_floor_is_an_event_not_a_rate():
    """UBER: la liberación de la provisión fiscal (−46 % a −140 %) no es un tipo: con pocos válidos, el legal."""
    r = tax_rate_normalized(1e9, -0.9e9, [(1e9, -0.8e9), (1e9, -0.7e9), (1e9, 0.09e9)])
    assert "legal" in r["source"]


def _hist():
    ends = [f"{y}-12-31" for y in range(2025, 2015, -1)]
    return {"revenue": {"values": [{"fy_end": e} for e in ends]},
            "spectrum_purchases": {"values": [{"fy_end": e, "value": 2.5e9, "concept": "us-gaap:PaymentsToAcquireIntangibleAssets"}
                                              for e in ends]}}


def test_spectrum_only_for_carriers():
    """CMCSA: Yahoo la pone en «Telecom Services», pero su PaymentsToAcquireIntangibleAssets es software."""
    assert telecom_spectrum.adjustment(_hist(), "Telecom Services", "Cable TV") is None
    assert telecom_spectrum.adjustment(_hist(), "Telecom Services", "Telecom. Services")["status"] == "ok"
    assert telecom_spectrum.adjustment(_hist(), "Telecom Services")["status"] == "ok"     # sin clasificar: la de Yahoo
