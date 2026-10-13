"""
Etapa 9c: display.charts (datos de los gráficos de la web).

Los gráficos no pueden contradecir a las lecturas: cada marcador cae en la zona cuya
etiqueta es la lectura de la tabla (las zonas salen de la misma config que los lectores),
y lo que no aplica o no es significativo lleva su estado y su motivo, nunca un hueco.
Corre sobre los 12 juegos con golden y la muestra amplia.
"""
import os

import pytest
from fastapi import HTTPException

import fixture_backend as fb

STATES = {"con_dato", "sin_dato", "no_aplica", "no_significativo"}


@pytest.fixture(scope="module")
def analyses(outputs_by_env):
    out = [(f"{e}/{s}", o[0]) for e in fb.available_envs() for s, o in outputs_by_env(e).items()]
    sample_dir = fb.fixtures_dir(fb.SAMPLE_ENV)
    if os.path.isdir(sample_dir):
        with fb.replay(sample_dir) as store:
            for s in fb.SAMPLE_TICKERS:
                try:
                    out.append((f"muestra/{s}", fb.run_analysis(s, store)))
                except HTTPException:
                    pass
    return out


def _zone_of(zones, v):
    for z in zones:
        if z["from"] <= v <= z["to"]:
            return z
    return zones[0] if v < zones[0]["from"] else zones[-1]


def test_gauges_marker_falls_in_the_zone_of_its_reading(analyses):
    checked = 0
    for name, a in analyses:
        for g in a["display"]["charts"]["solvency"]["gauges"]:
            assert g["state"] in STATES, (name, g)
            if g["state"] != "con_dato" or g.get("informative") or g.get("net_cash") or g.get("negative"):
                assert g["state"] == "con_dato" or g.get("text") or g["state"] == "sin_dato", (name, g)
                continue
            z = _zone_of(g["zones"], g["value"])
            # "Alto, servible" (D/E alto con cobertura holgada) es la lectura de la zona "Alto".
            assert g["reading"].startswith(z["label"]), (name, g["key"], g["value"], z, g["reading"])
            assert z["tone"] == g["tone"] or g["reading"] != z["label"], (name, g["key"])
            checked += 1
    assert checked > 30


def test_fair_value_price_falls_in_the_zone_of_the_badge(analyses):
    checked = 0
    for name, a in analyses:
        fv = a["display"]["charts"]["valuation"]["fair_value"]
        assert fv["state"] in STATES, name
        if fv["state"] != "con_dato":
            assert fv["state"] == "sin_dato" or fv.get("text"), (name, fv)
            continue
        z = _zone_of(fv["zones"], fv["price"])
        assert fv["badge"]["label"].replace(" (fiabilidad baja)", "") == z["label"], (name, fv["price"], z, fv["badge"])
        lo, hi = fv["axis"]
        assert lo < fv["price"] < hi and lo < fv["fair_value"] < hi
        checked += 1
    assert checked >= 10


def test_altman_value_falls_in_its_model_zone(analyses):
    for name, a in analyses:
        al = a["display"]["charts"]["institutional"]["altman"]
        if al["state"] == "con_dato":
            assert _zone_of(al["zones"], al["value"])["label"] == al["zone"], (name, al)
        else:
            assert al["state"] in STATES and al.get("text"), (name, al)


def test_not_applicable_never_leaves_an_empty_chart(analyses):
    """Banco (JPM), REIT (O), pre-beneficio (SNOW) y utilities: estado propio con motivo."""
    by = dict(analyses)
    jpm = by["prod/JPM"]["display"]["charts"]
    assert {g["key"]: g["state"] for g in jpm["solvency"]["gauges"]} == {
        "current_ratio": "no_aplica", "interest_coverage": "no_aplica", "net_debt_to_ebitda": "no_aplica",
        "de": "no_aplica"}
    assert all(g.get("text") for g in jpm["solvency"]["gauges"])
    assert jpm["valuation"]["fair_value"]["state"] == "no_aplica" and jpm["valuation"]["fair_value"]["text"]
    assert {f["key"]: f["state"] for f in jpm["results_flow"]}["fcf"] == "no_aplica"
    o = by["prod/O"]["display"]["charts"]
    assert o["institutional"]["altman"]["state"] == "no_aplica"
    snow = by["prod/SNOW"]["display"]["charts"]
    assert snow["solvency"]["runway"]["state"] == "con_dato"


def test_comparison_only_applicable_metrics(analyses):
    for name, a in analyses:
        c = a["display"]["charts"]["comparison"]
        na = set(a["display"]["na_keys"])
        keys = {i["key"] for g in c["groups"] for i in g["items"]}
        if "pe" in na:
            assert "pe" not in keys, name
        if "roe" in na:
            assert "roe" not in keys, name
        assert c["total"] == len(keys) and 0 <= c["better"] <= c["total"], name
        assert c["note"], name
        for g in c["groups"]:
            for i in g["items"]:
                assert (i["tone"] == "pos") == (i["reading"] in ("Muy superior", "Superior", "Descuento profundo",
                                                                  "Descuento")), (name, i)
