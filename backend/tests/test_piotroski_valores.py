"""Rediseño E2a (T6): Piotroski con el valor actual y el de comparación de cada criterio (los estados y la puntuación
no cambian)."""
from financial_ratios import piotroski_evaluate

ARGS = dict(net_income=90.0, roa_current=0.25, roa_prior=0.20, operating_cash_flow=110.0,
            long_term_debt_current=80.0, long_term_debt_prior=90.0, current_ratio_current=1.1,
            current_ratio_prior=0.9, shares_current=15.0, shares_prior=16.0, gross_margin_current=0.46,
            gross_margin_prior=0.44, asset_turnover_current=1.1, asset_turnover_prior=1.0)


def test_cada_criterio_trae_sus_valores():
    c = {x["key"]: x for x in piotroski_evaluate(**ARGS)["criteria"]}
    assert (c["roa_improved"]["cur"], c["roa_improved"]["prev"], c["roa_improved"]["unit"]) == (0.25, 0.20, "pct")
    assert (c["earnings_quality"]["cur"], c["earnings_quality"]["prev"], c["earnings_quality"]["compare"]) == (110.0, 90.0, "ni")
    assert c["roa_positive"]["prev"] is None and c["roa_positive"]["compare"] == "zero"
    assert c["cfo_positive"]["cur"] == 110.0 and c["cfo_positive"]["unit"] == "money"
    assert c["no_dilution"]["unit"] == "shares" and c["debt_reduced"]["unit"] == "money"
    assert c["current_ratio_improved"]["unit"] == "ratio" and c["asset_turnover_improved"]["unit"] == "ratio"
    assert c["gross_margin_improved"]["unit"] == "pct" and c["gross_margin_improved"]["compare"] == "prior_year"


def test_sin_dato_conserva_lo_que_hay():
    c = {x["key"]: x for x in piotroski_evaluate(**dict(ARGS, roa_prior=None))["criteria"]}
    assert c["roa_improved"]["state"] == "sin_dato"
    assert (c["roa_improved"]["cur"], c["roa_improved"]["prev"]) == (0.25, None)


def test_estados_y_puntuacion_no_cambian():
    r = piotroski_evaluate(**ARGS)
    assert r["score"] == 9 and all(x["state"] == "cumple" for x in r["criteria"])


def test_el_analisis_propaga_los_valores():
    import logging
    import fixture_backend as fb
    logging.disable(logging.CRITICAL)
    with fb.replay(fb.fixtures_dir("panel")) as store:
        a = fb.run_analysis("AAPL", store)
    d = a["piotroski_f"]["details"]["roa_improved"]
    assert d["unit"] == "pct" and d["compare"] == "prior_year" and d["cur"] is not None and d["prev"] is not None
