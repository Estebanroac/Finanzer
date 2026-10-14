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
import invariants as inv


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


def test_gauges_marker_falls_in_the_zone_of_its_reading(analyses):
    checked = sum(inv.chart_gauges_marker_in_reading_zone(a, None) for _, a in analyses)
    assert checked > 30


def test_fair_value_price_falls_in_the_zone_of_the_badge(analyses):
    checked = sum(inv.chart_fair_value_in_badge_zone(a, None) for _, a in analyses)
    assert checked >= 10


def test_altman_value_falls_in_its_model_zone(analyses):
    for name, a in analyses:
        inv.chart_altman_in_model_zone(a, None)


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
        inv.chart_comparison_only_applicable_metrics(a, None)


def test_multiples_role_matches_the_score_breakdown(analyses):
    """Miembro del bloque = ajuste in_block del desglose; lo que no entra ni puntúa aparte es informativo."""
    by = dict(analyses)
    for name, a in analyses:
        inv.chart_multiples_role_matches_breakdown(a, None)
    nf = {m["key"]: m["role"] for m in by["prod/NFLX"]["display"]["charts"]["valuation"]["multiples"]}
    assert nf["pb"] == nf["fcf_yield"] == "informative" and nf["pe"] == nf["pfcf"] == "block"
    fcx = by["prod/FCX"]["display"]["charts"]["valuation"]
    assert {s["key"] for s in fcx["scored"] if s["in_block"]} == {"p_fcf_normalizado", "ev_ebitda_normalizado"}
    assert {m["key"]: m["role"] for m in fcx["multiples"]}["pfcf"] == "informative"
    o = by["prod/O"]["display"]["charts"]["valuation"]
    assert [s["key"] for s in o["scored"] if not s["in_block"]] == ["p_ffo_reit"]


def test_upside_phrase_follows_the_sensitivity_grid(analyses):
    """Etapa 9c: dentro del grid, "exigentes pero posibles"; fuera, "ningún supuesto razonable". Nunca "muy optimistas"."""
    for name, a in analyses:
        inv.chart_upside_phrase_follows_grid(a, None)