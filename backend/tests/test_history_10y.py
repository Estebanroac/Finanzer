"""Rediseño E2a (T5): historia de 10 ejercicios desde la historia anual de EDGAR que ya trae el análisis
(yinfo["_history_fy"], forma de sec_edgar.history): sin red adicional."""
import math

import history_10y


def _series(field_values, unit="USD"):
    """{fy_end: valor} → la forma de sec_edgar.annual_history (del más reciente al más antiguo)."""
    vals = [{"fy_end": e, "value": v, "concept": "us-gaap:X", "taxonomy": "us-gaap"}
            for e, v in sorted(field_values.items(), reverse=True)]
    return {"values": vals, "unit": unit, "cross_taxonomy": None}


def _hist(n_years, first=2014):
    ends = [f"{first + i}-12-31" for i in range(n_years)]
    rev = {e: 100.0 * (1.1 ** i) for i, e in enumerate(ends)}
    return {
        "revenue": _series(rev),
        "operating_income": _series({e: v * 0.2 for e, v in rev.items()}),
        "net_income": _series({e: v * 0.15 for e, v in rev.items()}),
        "diluted_eps": _series({e: v / 100 for e, v in rev.items()}, unit="USD/shares"),
        "diluted_shares": _series({e: 100.0 for e in ends}, unit="shares"),
        "operating_cash_flow": _series({e: v * 0.25 for e, v in rev.items()}),
        "capex": _series({e: -v * 0.05 for e, v in rev.items()}),    # sec_edgar guarda el capex con signo negativo
    }


def test_diez_ejercicios_del_mas_antiguo_al_mas_reciente():
    r = history_10y.build(_hist(12), 10)
    assert r["status"] == "ok" and r["currency"] == "USD" and r["reason"] is None
    assert [x["year"] for x in r["rows"]] == list(range(2016, 2026))
    first = r["rows"][0]
    rev = 100.0 * 1.1 ** 2
    assert math.isclose(first["revenue"], rev)
    assert math.isclose(first["free_cash_flow"], rev * 0.25 - rev * 0.05)
    assert math.isclose(first["net_margin"], 0.15) and math.isclose(first["operating_margin"], 0.2)
    # el crecimiento del primer año publicado usa el ejercicio anterior, aunque no se publique
    assert math.isclose(first["revenue_growth"], 0.1)
    assert first["fy_end"] == "2016-12-31"
    assert r["source"].startswith("SEC EDGAR")


def test_pocos_ejercicios_se_dice():
    r = history_10y.build(_hist(4), 10)
    assert r["status"] == "ok" and len(r["rows"]) == 4
    assert r["reason"] == "EDGAR trae 4 ejercicios"
    assert r["rows"][0]["revenue_growth"] is None


def test_sin_historia():
    assert history_10y.build(None, 10)["status"] == "sin_dato"
    assert history_10y.build({}, 10)["status"] == "sin_dato"
    assert history_10y.build(None, 10)["reason"]


def test_fcf_solo_con_los_dos_datos():
    h = _hist(3)
    h["capex"] = _series({})
    r = history_10y.build(h, 10)
    assert all(x["free_cash_flow"] is None for x in r["rows"]) and r["rows"][-1]["capex"] is None


def test_el_analisis_trae_la_historia():
    import logging
    import fixture_backend as fb
    logging.disable(logging.CRITICAL)
    with fb.replay(fb.fixtures_dir("panel")) as store:
        aapl = fb.run_analysis("AAPL", store)
        mc = fb.run_analysis("MC.PA", store)
    h = aapl["history_10y"]
    assert h["status"] == "ok" and [x["year"] for x in h["rows"]] == list(range(2016, 2026))
    assert h["currency"] == "USD"
    assert mc["history_10y"]["status"] == "sin_dato" and mc["history_10y"]["reason"]


def test_hueco_en_la_historia_no_se_presenta_como_crecimiento_anual():
    """Revisión del PM: si EDGAR no trae un ejercicio, el crecimiento no se compara contra dos años atrás."""
    h = _hist(6)
    for f in ("revenue", "net_income", "operating_cash_flow"):
        h[f]["values"] = [v for v in h[f]["values"] if v["fy_end"] != "2017-12-31"]
    rows = {r["year"]: r for r in history_10y.build(h, 10)["rows"]}
    assert 2017 not in rows
    assert rows[2018]["revenue_growth"] is None and rows[2018]["gap_before"] is True
    assert rows[2019]["gap_before"] is False and math.isclose(rows[2019]["revenue_growth"], 0.1)
    assert rows[2014]["gap_before"] is False           # el primero: sin anterior, no es un hueco


def test_cierre_desplazado_dentro_de_la_tolerancia():
    """Un cambio de calendario de pocas semanas (52/53 semanas) sigue siendo el ejercicio anterior."""
    h = _hist(3)
    for f in h.values():
        for v in f["values"]:
            if v["fy_end"] == "2015-12-31":
                v["fy_end"] = "2015-12-26"
    rows = history_10y.build(h, 10)["rows"]
    assert rows[-1]["gap_before"] is False and rows[-1]["revenue_growth"] is not None


def test_ejercicio_de_52_53_semanas_que_cierra_a_primeros_de_enero_es_del_anio_anterior():
    """V4b: JNJ cierra en el domingo más cercano al 31 de diciembre; el FY2022 terminó el 1-ene-2023 y la ficha decía
    «2023» dos veces. Un cierre en los primeros `fy_year_shift_days` días de enero es del año anterior."""
    ends = ["2021-01-03", "2022-01-02", "2023-01-01", "2023-12-31", "2024-12-29"]
    h = {"revenue": _series({e: 100.0 for e in ends}), "net_income": _series({e: 10.0 for e in ends})}
    r = history_10y.build(h, 10)
    assert [x["year"] for x in r["rows"]] == [2020, 2021, 2022, 2023, 2024]
    assert [x["fy_end"] for x in r["rows"]] == ends
