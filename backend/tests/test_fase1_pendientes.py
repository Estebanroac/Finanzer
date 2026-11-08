"""Fase 1 · pendientes de la prueba hacia atrás (decisión del usuario, 7-nov-2026)."""
import datetime as dt
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))

import alert_groups as G  # noqa: E402
import consistency as C  # noqa: E402
import precio_l1 as L  # noqa: E402
import verdict as V  # noqa: E402


# ── 1. la valoración extrema (versión 1.0, 8-nov-2026: ya no es alerta roja, es lectura) ──
def test_extreme_valuation_is_a_reading_with_the_two_cuts_evidence():
    assert G.extreme_valuation({"level": "exigente"}) is None
    ext = G.extreme_valuation({"level": "muy exigente", "score": 12})
    assert ext["reason"] == "Valoración extrema según múltiplos y DCF"
    assert "22,3 %" in ext["detail"] and "16,4 %" in ext["detail"] and "23 de 103" in ext["detail"]
    assert "2024 cayeron menos que el resto" in ext["detail"] and "no una alerta" in ext["detail"]


def test_old_red_flags_go_to_balance_or_valuation_reading():
    old = {"red_flags": [{"category": "Solidez financiera", "reason": "Riesgo de insolvencia — Altman Z 0.70"},
                         {"category": "Valor intrínseco", "reason": "Sobrevalorada según DCF −55%"},
                         {"category": "Rentabilidad", "reason": "ROE normalizado negativo −4%"},
                         {"category": "Flujo de caja", "reason": "Flujo de caja libre negativo"}],
           "warnings": [{"category": "Solidez financiera", "reason": "Apalancamiento elevado — 4.5x EBITDA"},
                        {"category": "Solidez financiera", "reason": "Liquidez ajustada — current ratio 0.82x"},
                        {"category": "Valoración", "reason": "FCF yield bajo — 2.4%"}],
           "strengths": [{"category": "Rentabilidad", "reason": "ROE excepcional"}]}
    out = G.regroup(old, {"valuation_reading": {"level": "razonable"}})
    assert out["red_flags"] == []
    assert [x["reason"][:20] for x in out["balance"]] == ["Riesgo de insolvenci", "ROE normalizado nega",
                                                          "Flujo de caja libre ", "Apalancamiento eleva"]
    assert len(out["valuation"]) == 2 and [x["reason"][:8] for x in out["warnings"]] == ["Liquidez"]
    out = G.regroup(old, {"valuation_reading": {"level": "muy exigente"}})
    assert out["red_flags"] == [] and out["valuation"][0]["reason"] == "Valoración extrema según múltiplos y DCF"
    # ninguna roja sobrevive, aunque llegue en el formato antiguo de otra ruta
    out = G.regroup({**old, "red_flags": [{"category": "Riesgo de mercado", "reason": "X"}]},
                    {"valuation_reading": {"level": "muy exigente"}})
    assert out["red_flags"] == [] and "X" in [x["reason"] for x in out["warnings"]]


# ── 2. consistencia con dos niveles ──
def _conf(conv, cov, methods=None):
    return {"level": "media", "dimensions": {
        "convergence": {"level": conv, "methods": methods or [
            {"method": "DCF", "evaluable": True, "direction": "cara"},
            {"method": "múltiplos frente al sector", "evaluable": True, "direction": "cara"}]},
        "coverage": {"level": cov}}}


def test_consistency_has_two_levels_and_no_high():
    assert C.compute(_conf("alta", "alta"))["level"] == "consistente"
    assert C.compute(_conf("alta", "media"))["level"] == "consistente"
    assert C.compute(_conf("alta", "baja"))["level"] == "mixta"
    assert C.compute(_conf("media", "alta"))["level"] == "mixta"
    m = C.compute(_conf("baja", "alta"))
    assert m["level"] == "mixta" and m["phrase"] == "el DCF directo y los múltiplos discrepan"
    assert set(C.LEVELS) == {"consistente", "mixta"}


def test_verdict_says_consistency_not_confidence():
    v = V.verdict({"level": "sólida"}, {"level": "razonable", "rule": "L1"}, _conf("baja", "alta"))
    assert v["confidence_text"] == "(consistencia mixta: el DCF directo y los múltiplos discrepan)"
    assert v["consistency"] == "mixta" and "confidence" not in v


# ── 2 bis. la calidad ya no se contrae ──
def test_quality_is_not_contracted_without_a_level():
    q = V.contract_quality({"score": 82, "score_raw": 82, "level": "sólida"}, None)
    assert q["score"] == 82 and not q["contracted"]


# ── 4. aviso de pico de beneficio en una cíclica ──
def test_cyclical_peak_warning_next_to_the_label():
    inp = {"status": "ok", "ni_ttm": 100.0, "end": "2026-09-30"}
    peak = {"conditions": {"a": True, "b": None}, "ttm_over_median": 3.4, "years": 3}
    b = L.basis(1000.0, inp, "CYCLICAL", {}, None, "2026-09-30", cycle_peak=peak)
    assert b["cycle_peak"] and "parte alta del ciclo" in b["warning"] and "340 %" in b["warning"]
    assert L.basis(1000.0, inp, "MATURE", {}, None, "2026-09-30", cycle_peak=peak)["warning"] is None
    peak_no = {**peak, "conditions": {"a": False, "b": None}}
    assert L.basis(1000.0, inp, "CYCLICAL", {}, None, "2026-09-30", cycle_peak=peak_no)["warning"] is None


# ── 5. alarma de la referencia ──
def test_reference_alarm_when_old_or_frozen():
    c = {"as_of": "2026-11-07", "cuts": [0.8, 1.2]}
    assert L.reference_alarm(c, dt.date(2026, 12, 12)) == []                              # 35 días: aún bien
    assert "36 días" in L.reference_alarm(c, dt.date(2026, 12, 13))[0]
    frozen = {**c, "previous_cuts": [0.8, 1.2], "previous_as_of": "2026-10-07"}
    assert any("no cambiaron" in x for x in L.reference_alarm(frozen, dt.date(2026, 11, 8)))
    assert L.reference_alarm({**c, "previous_cuts": [0.81, 1.2]}, dt.date(2026, 11, 8)) == []


# ── 6. display.consistency, con display.confidence como alias durante una versión ──
def test_display_consistency_with_the_old_alias():
    import json
    a = json.load(open(os.path.join(HERE, "golden", "panel", "AAPL.json"), encoding="utf-8"))
    d = a["display"]
    assert d["consistency"] == d["confidence"] and d["consistency"]["level"] in C.LEVELS
