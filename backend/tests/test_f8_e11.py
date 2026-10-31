"""
F8 · E11 (auditoría externa del 26-oct-2026, §3 E11): la confianza cumple su regla y afecta a la calidad.

- la más baja manda: ninguna dimensión evaluada (la cobertura incluida) queda por debajo de la confianza final; es
  genérico, venga de donde venga la bajada (PM, 27-oct: unos estados desfasados que bajan la cobertura a «media»);
- con confianza baja la calidad también se contrae hacia 50 (×0,85);
- contra la saturación, «excelente» desde 85 (el cuartil superior de 68 casos); el codo de la persistencia sigue en 80,
  así que subir la etiqueta no cambia ninguna puntuación.
"""
import pytest

import valuation_confidence as vc
from settings import cfg
from verdict import contract_quality


def _dim(level):
    return {"level": level, "reasons": [f"motivo {level}"]}


def _conf(**levels):
    dims = {k: _dim(levels.get(k, "alta")) for k in ("convergence", "coverage", "source", "stability")}
    dims["fuente_oficial"] = {"level": "alta", "reasons": []}
    return vc.verdict_confidence(dims)


def test_lowest_dimension_rules_mrna_case():
    """MRNA (26-oct): cobertura baja y confianza media."""
    c = _conf(coverage="baja")
    assert c["level"] == "baja" and any("la más baja manda: cobertura baja" in r for r in c["reasons"])


def test_simulated_medium_coverage_caps_at_media():
    """PM, 27-oct (AMZN con E6: estados desfasados, cobertura «media» y confianza «alta»): la confianza nunca supera a
    la cobertura, venga de donde venga la bajada. Se simula una cobertura media sin otra debilidad."""
    c = _conf(coverage="media")
    assert c["level"] == "media" and any("cobertura media" in r for r in c["reasons"])


def test_all_high_stays_high_and_no_evaluable_does_not_cap():
    assert _conf()["level"] == "alta"
    assert _conf(convergence="no_evaluable")["level"] == "alta"


def test_quality_contracts_only_with_low_confidence():
    q = {"score": 82, "level": "excelente"}
    low = contract_quality(q, "baja")
    assert (low["score_raw"], low["score"], low["contracted"]) == (82, round(50 + 32 * 0.85), True)
    assert low["level"] == "sólida"                                   # XOM (26-oct): 82 «excelente» sin contraer
    assert contract_quality(q, "media")["score"] == 82 and not contract_quality(q, "media")["contracted"]
    assert contract_quality(low, "baja")["score"] == low["score"]       # idempotente: parte de la cruda


def test_excellent_starts_at_85():
    Q = cfg("thresholds.score.quality")
    assert Q["bands"][0] == 85 and Q["confidence_factor"]["baja"] == pytest.approx(0.85)
    assert contract_quality({"score": 84}, None)["level"] == "sólida"
    assert contract_quality({"score": 85}, None)["level"] == "excelente"


def test_raising_excellent_does_not_loosen_persistence():
    """KO (golden): 82 → 81 por persistencia con el codo en 80. Si el codo siguiera al umbral de «excelente» (85), 82
    quedaría por debajo y la persistencia dejaría de aplicarse: subir la etiqueta subiría la puntuación."""
    import persistence as P
    assert cfg("thresholds.quality_persistence.knee") == 80 < cfg("thresholds.score.quality.bands")[0]
    names = ["Solidez Financiera", "Rentabilidad", "Calidad de Ganancias", "Crecimiento"]
    meas = {n: {"persistence": 0.5, "years_ok": ["2025"], "rule": "r"} for n in names}
    meas["denominator"] = 5
    q = {"score": 82}
    P.adjust_quality(q, [{"category": n, "score": 17} for n in names], meas)
    assert q["score"] == 81 and q["persistence"]["applied"]
