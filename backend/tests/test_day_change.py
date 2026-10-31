"""Rediseño E2a (T4): variación del día frente al cierre de la sesión anterior, con la serie de la misma sesión."""
import math

import pandas as pd

import price_history as ph


def _f(closes):
    idx = pd.to_datetime([f"2026-10-{d:02d}" for d in range(13, 13 + len(closes))])
    return pd.DataFrame({"close": closes, "adj_close": closes, "volume": [1.0] * len(closes),
                         "dividend": [0.0] * len(closes), "split": [0.0] * len(closes)}, index=idx)


def test_variacion_contra_el_cierre_anterior():
    r = ph.day_change(_f([100.0, 102.0, 101.0]), 103.0)
    assert r["status"] == "ok" and r["prev_close"] == 102.0
    assert math.isclose(r["change"], 1.0) and math.isclose(r["change_pct"], 103 / 102 - 1)
    assert r["session"] == "2026-10-15"


def test_ultima_sesion_sin_cierre_cuenta_como_la_del_precio():
    r = ph.day_change(_f([100.0, 102.0, float("nan")]), 104.0)
    assert r["prev_close"] == 102.0 and r["session"] == "2026-10-15"


def test_sin_serie_o_sin_precio():
    assert ph.day_change(None, 100.0)["status"] == "sin_dato"
    assert ph.day_change(_f([100.0, 101.0]), None)["status"] == "sin_dato"
    one = ph.day_change(_f([100.0]), 100.0)
    assert one["status"] == "sin_dato" and one["reason"]


def test_el_analisis_trae_la_variacion():
    """Con el replay: el cierre anterior es el penúltimo cierre de la serie que usó el propio análisis (XOM)."""
    import logging
    import fixture_backend as fb
    logging.disable(logging.CRITICAL)
    with fb.replay(fb.fixtures_dir("panel")) as store:
        a = fb.run_analysis("XOM", store)
        frame = ph.peek("XOM")["frame"]
    pc = a["price_change"]
    assert pc["status"] == "ok"
    assert pc["prev_close"] == float(frame["close"].iloc[:-1].dropna().iloc[-1])
    assert pc["session"] == frame.index[-1].strftime("%Y-%m-%d")
    assert math.isclose(pc["change"], a["price"] - pc["prev_close"])
