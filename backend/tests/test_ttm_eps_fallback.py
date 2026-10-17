"""Fase 6 (medición Render frente a local, CAT): sin BPA ni acciones diluidas trimestrales, el BPA TTM no puede ser el
del ejercicio junto al beneficio de doce meses (P/E 38.9x en Render frente a 31.4x). Sin red."""
import pytest

import ttm
import yf_adapter as Y


def _t(ni_ttm=10_844e6):
    return {"cut": "2026-06-30", "values": {"netIncome": ni_ttm, "totalRevenue": 67e9}, "missing": {},
            "quarters": {"inc": ["2026-06-30", "2026-03-31", "2025-12-31", "2025-09-30"], "cf": []},
            "balance_date": None, "quarterly": {}, "quarter_min": {}, "eps": None}


@pytest.fixture
def no_quarterly_eps(monkeypatch):
    monkeypatch.setattr(Y, "_stmt_ticker", lambda s: object())
    monkeypatch.setattr(ttm, "build_ttm", lambda *a, **k: _t())


def test_fy_eps_is_scaled_to_the_ttm_net_income(no_quarterly_eps):
    info = {"trailingEps": 18.81, "_statements_fy": {"net_income": [8_777e6]}, "_fy_dates": {}}
    out = Y._apply_ttm("CAT", info, plan_b=True)
    assert out["trailingEps"] == pytest.approx(18.81 * 10_844e6 / 8_777e6) and out["_eps_net_income"] == 10_844e6
    assert "aproximado" in out["_provenance"]["trailingEps"]["detail"] and out["_ttm"]["eps"] == "ttm"


def test_without_fy_net_income_there_is_no_eps_of_another_period(no_quarterly_eps):
    info = {"trailingEps": 18.81, "_statements_fy": {"net_income": [None]}, "_fy_dates": {}}
    out = Y._apply_ttm("CAT", info, plan_b=True)
    assert out["trailingEps"] is None and out["_provenance"]["trailingEps"]["source"] == "sin_dato"
