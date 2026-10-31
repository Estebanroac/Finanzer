"""F10 · N3 (revisión del informe de NVIDIA): PEG con el crecimiento del BPA desde un año valle. El crecimiento usa el
mismo método que los ingresos (historical_metrics.growth_rate); si el año base es anómalo y la regresión no tiene
ejercicios fuera de la ventana con los que diluirlo, el PEG no es significativo (main.py, GROWTH_PROFITABLE)."""
import pytest

from historical_metrics import growth_rate

NVDA_EPS = [4.9, 2.94, 1.19, 0.174]          # FY2026 → FY2023, diluido (Yahoo)


def test_nvda_anomalous_base_without_more_years_is_not_robust():
    r = growth_rate(NVDA_EPS, 3, what="BPA")
    assert r["anomalous_base"] and r["method"] == "log_lineal"
    assert r["value"] == pytest.approx(1.98, abs=0.01) and r["robust"] is False


def test_with_years_beyond_the_window_the_regression_is_the_alternative():
    r = growth_rate(NVDA_EPS + [0.16, 0.12, 0.05], 3, what="BPA")
    assert r["anomalous_base"] and r["robust"] is True and r["value"] < 1.98


def test_without_an_anomalous_base_nothing_changes():
    r = growth_rate([4.9, 4.0, 3.3, 2.7], 3, what="BPA")
    # F10 · crecimiento desde una base anómala: toda serie expone `robust` (sin base anómala, el CAGR es robusto)
    assert r["method"] == "cagr" and not r["anomalous_base"] and r["robust"] is True
