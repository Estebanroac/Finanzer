"""Fase 5 (PEAD; bitácora, fila "fecha de resultados"): la sorpresa del BPA frente al consenso (Finnhub) con la fecha
del 8-K de resultados (SEC EDGAR) y la reacción y deriva frente al S&P 500. Contexto: no puntúa. Sin red."""
import pandas as pd
import pytest

import market_context as MC
from settings import cfg

IDX = pd.bdate_range("2026-06-01", "2026-10-14")


def _series(jump_day=None, jump=0.0, drift_per_day=0.0):
    v, out = 100.0, []
    for d in IDX:
        if jump_day is not None and d == pd.Timestamp(jump_day):
            v *= 1 + jump
        elif jump_day is not None and d > pd.Timestamp(jump_day):
            v *= 1 + drift_per_day
        out.append(v)
    return pd.Series(out, index=IDX)


FIL = [{"form": "8-K", "filingDate": "2026-07-29", "items": "2.02,9.01"},
       {"form": "8-K", "filingDate": "2026-08-15", "items": "5.07"},
       {"form": "10-Q", "filingDate": "2026-07-30", "items": ""}]
SURP = [{"period": "2026-06-30", "actual": 2.20, "estimate": 2.00}, {"period": "2026-03-31", "actual": 1.9, "estimate": 2.0}]


def test_surprise_dated_by_the_8k_and_measured_against_the_market():
    p = MC.pead("X", _series("2026-07-29", 0.10, 0.001), _series(), FIL, SURP)
    assert p["status"] == "ok" and p["period"] == "2026-06-30" and p["announced"] == "2026-07-29"
    assert p["surprise"] == pytest.approx(0.10) and p["reaction"] == pytest.approx(1.10 * 1.001 - 1)  # día 0 y +1
    after = len(IDX) - 1 - (list(IDX).index(pd.Timestamp("2026-07-29")) + 1)
    assert p["drift"] > 0 and p["sessions"] == min(after, cfg("market.context.pead_window_sessions"))
    row = next(r for r in MC.readings({"signals": {}, "pead": p}) if r["key"] == "pead")
    assert "la deriva va en la dirección de la sorpresa" in row["text"] and "Bernard y Thomas" in row["text"]


def test_drift_against_the_surprise_is_said():
    p = MC.pead("X", _series("2026-07-29", 0.05, -0.002), _series(), FIL, SURP)
    row = next(r for r in MC.readings({"signals": {}, "pead": p}) if r["key"] == "pead")
    assert "va en contra de la sorpresa" in row["text"]


def test_inline_surprise_does_not_talk_about_drift():
    p = MC.pead("X", _series("2026-07-29", 0.05, 0.001), _series(), FIL, [{"period": "2026-06-30", "actual": 2.01,
                                                                            "estimate": 2.0}])
    row = next(r for r in MC.readings({"signals": {}, "pead": p}) if r["key"] == "pead")
    assert "en línea con el consenso" in row["text"] and "Bernard" not in row["text"]


def test_announcement_after_the_series_is_not_used():
    """Lo que se sabía ese día: un 8-K posterior a la serie no cuenta (vale para el replay y el estudio)."""
    fil = FIL + [{"form": "8-K", "filingDate": "2026-10-20", "items": "2.02"}]
    surp = [{"period": "2026-09-30", "actual": 3, "estimate": 2}] + SURP
    assert MC.pead("X", _series(), _series(), fil, surp)["period"] == "2026-06-30"


def test_last_session_announcement_cannot_be_measured_yet():
    fil = [{"form": "8-K", "filingDate": "2026-10-14", "items": "2.02"}]
    p = MC.pead("X", _series(), _series(), fil, [{"period": "2026-09-30", "actual": 3, "estimate": 2}])
    assert p["status"] == "ok" and p["reaction"] is None
    row = next(r for r in MC.readings({"signals": {}, "pead": p}) if r["key"] == "pead")
    assert "aún no se pueden medir" in row["text"]


def test_few_sessions_after_do_not_judge_drift():
    fil = [{"form": "8-K", "filingDate": "2026-10-10", "items": "2.02"}]
    p = MC.pead("X", _series("2026-10-10", 0.05, 0.01), _series(), fil, [{"period": "2026-09-30", "actual": 3,
                                                                          "estimate": 2}])
    row = next(r for r in MC.readings({"signals": {}, "pead": p}) if r["key"] == "pead")
    assert p["sessions"] < cfg("market.context.pead_min_sessions") and "aún pocas sesiones" in row["text"]


def test_foreign_filer_without_8k_says_why():
    p = MC.pead("X", _series(), _series(), [{"form": "6-K", "filingDate": "2026-07-29", "items": ""}], SURP)
    assert p["status"] == "sin_dato" and "8-K" in p["reason"]


def test_never_scores():
    """D5: el contexto de mercado no entra en el score (el PEAD vive en market_context)."""
    import inspect
    import financial_ratios
    assert "pead" not in inspect.getsource(financial_ratios)
