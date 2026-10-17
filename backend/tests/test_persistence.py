"""Fase 4 (T1): la calidad por encima de "excelente" exige persistencia (lib/persistence.py). Sin red."""
import pytest

import persistence as P


def _h(**series):
    return {k: {"values": [{"fy_end": f"{2020 + i}-12-31", "value": v} for i, v in enumerate(vals)]}
            for k, vals in series.items()}


STEADY = _h(revenue=[100, 110, 120, 130, 140, 150], operating_income=[30, 33, 36, 39, 42, 45],
            net_income=[20, 22, 24, 26, 28, 30], operating_cash_flow=[25, 27, 29, 31, 33, 35],
            capex=[-5, -5, -5, -5, -5, -5])


def test_steady_business_is_fully_persistent():
    m = P.measure(STEADY, "MATURE", "edgar")
    assert m["denominator"] == 5
    for c in ("Rentabilidad", "Crecimiento", "Calidad de Ganancias"):
        assert m[c]["persistence"] == pytest.approx(1.0), c


def test_recent_margin_peak_is_not_persistent():
    h = _h(revenue=[100, 100, 100, 100, 100, 100], operating_income=[5, 5, 5, 5, 20, 30],
           net_income=[3] * 6, operating_cash_flow=[4] * 6, capex=[-1] * 6)
    m = P.measure(h, "MATURE", "edgar")
    # 75% de 30% = 22.5%: solo el último ejercicio lo cumple.
    assert m["Rentabilidad"]["years_ok"] == ["2025"]
    assert m["Crecimiento"]["persistence"] == 0.0           # ingresos planos: no crecen


def test_missing_years_count_as_not_proven():
    h = _h(revenue=[100, 110, 120], operating_income=[30, 33, 36], net_income=[20, 22, 24],
           operating_cash_flow=[25, 27, 29], capex=[-5, -5, -5])
    m = P.measure(h, "MATURE", "estados")
    assert m["denominator"] == 5 and m["Rentabilidad"]["persistence"] == pytest.approx(3 / 5)


def test_perimeter_year_leaves_the_window_but_sets_the_reference_margin():
    h = dict(STEADY, discontinued={"values": [{"fy_end": "2025-12-31", "value": 10}]})
    m = P.measure(h, "MATURE", "edgar")
    assert m["denominator"] == 4 and "2025" not in m["Rentabilidad"]["years"]
    assert m["Rentabilidad"]["persistence"] == pytest.approx(1.0)


def _cats(*scores):
    names = ["Solidez Financiera", "Rentabilidad", "Calidad de Ganancias", "Crecimiento"]
    return [{"category": n, "score": s} for n, s in zip(names, scores)]


def test_excellent_is_untouched_and_extraordinary_needs_history():
    meas = {"Rentabilidad": {"persistence": 0.2, "years_ok": ["2025"], "rule": "r"},
            "Crecimiento": {"persistence": 1.0, "years_ok": [], "rule": "g"},
            "Calidad de Ganancias": {"persistence": 1.0, "years_ok": [], "rule": "c"}, "denominator": 5}
    q = {"score": 80}
    P.adjust_quality(q, _cats(16, 16, 16, 16), meas)
    assert q["score"] == 80 and not q["persistence"]["applied"]
    q = {"score": 100}
    P.adjust_quality(q, _cats(20, 20, 20, 20), meas)
    # Ponderada por los puntos sobre 16: (4·1 + 4·0.2 + 4·1 + 4·1) / 16 = 0.8 -> 80 + 20 × 0.8 = 96.
    assert q["score"] == 96 and q["persistence"]["applied"]
    assert "100 → 96" in q["persistence"]["text"] and "1 de 5 ejercicios" in q["persistence"]["text"]


def test_without_measure_nothing_changes():
    q = {"score": 100}
    P.adjust_quality(q, _cats(20, 20, 20, 20), None)
    assert q == {"score": 100}
