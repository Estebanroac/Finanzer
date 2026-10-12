"""lib/historical_metrics.py: CAGR extraído de data_fetcher (aún sin llamadas)."""
import pytest

import historical_metrics as hm


def test_cagr_basic_and_guards():
    assert hm.cagr(121.0, 100.0, 2) == pytest.approx(0.10)
    assert hm.cagr(100.0, 0.0, 2) is None
    assert hm.cagr(-5.0, 100.0, 2) is None
    assert hm.cagr(100.0, 50.0, 0) is None
    assert hm.cagr(None, 50.0, 1) is None


def test_series_cagr_uses_start_at_period_not_oldest():
    rev = [146.41, 133.1, 121.0, 110.0, 50.0]   # 10% anual los 3 últimos años
    assert hm.series_cagr(rev, 3) == pytest.approx(0.10)
    assert hm.series_cagr(rev[:3], 3) == pytest.approx(0.10)  # solo 2 periodos disponibles
    assert hm.series_cagr([100.0], 3) is None


def test_contextual_keys_and_thresholds():
    ctx = hm.contextual_from_history({"revenue": [133.1, 121.0, 110.0], "fcf": [5.0, -1.0, -2.0, None]})
    assert ctx["revenue_cagr_3y"] == pytest.approx(0.10)
    assert "revenue_cagr_5y" not in ctx
    assert ctx["fcf_trend_negative_years"] == 2
    ctx5 = hm.contextual_from_history({"revenue": [161.051, 146.41, 133.1, 121.0, 110.0]})
    assert ctx5["revenue_cagr_5y"] == pytest.approx(0.10)
    assert hm.contextual_from_history({"revenue": [1.0, 2.0]}) == {}
    assert hm.contextual_from_history(None) == {}


def test_fcf_cagr_defined_only_for_positive_series():
    assert hm.fcf_cagr([133.1, 121.0, 110.0, 100.0])[0] == pytest.approx(0.10)
    assert hm.fcf_cagr([133.1, 121.0, 110.0, 100.0, 5.0])[0] == pytest.approx(0.10)  # usa 4 ejercicios
    v, why = hm.fcf_cagr([10.0, 5.0, 3.0, -1.0])
    assert v is None and "inicial" in why
    v, why = hm.fcf_cagr([-10.0, 5.0, 3.0, 2.0])
    assert v is None and "signo" in why
    v, why = hm.fcf_cagr([10.0, -5.0, 3.0, 2.0])
    assert v is None and "signo" in why
    v, why = hm.fcf_cagr([10.0, 5.0, 3.0])
    assert v is None and "4 ejercicios" in why
    v, why = hm.fcf_cagr([10.0, None, 3.0, 2.0])
    assert v is None and why
