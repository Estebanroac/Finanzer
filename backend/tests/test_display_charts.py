"""
Etapa 9c: display.charts (datos de los gráficos de la web).

Los gráficos no pueden contradecir a las lecturas: cada marcador cae en la zona cuya
etiqueta es la lectura de la tabla (las zonas salen de la misma config que los lectores),
y lo que no aplica o no es significativo lleva su estado y su motivo, nunca un hueco.
Corre sobre el juego local y el panel.
"""

import pytest

import fixture_backend as fb
import invariants as inv


@pytest.fixture(scope="module")
def analyses(outputs_by_env):
    """Juego local y panel (fase 1, D8: el panel sustituye a prod y a la muestra). Sin los rechazados (SPY)."""
    import conftest
    return [(f"{e}/{s}", o[0]) for e in conftest.REG_ENVS for s, o in outputs_by_env(e).items()
            if not o[0].get("__http_error__")]


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
    jpm = by["panel/JPM"]["display"]["charts"]
    assert {g["key"]: g["state"] for g in jpm["solvency"]["gauges"]} == {
        "current_ratio": "no_aplica", "interest_coverage": "no_aplica", "net_debt_to_ebitda": "no_aplica",
        "de": "no_aplica"}
    assert all(g.get("text") for g in jpm["solvency"]["gauges"])
    assert jpm["valuation"]["fair_value"]["state"] == "no_aplica" and jpm["valuation"]["fair_value"]["text"]
    assert {f["key"]: f["state"] for f in jpm["results_flow"]}["fcf"] == "no_aplica"
    o = by["panel/O"]["display"]["charts"]
    assert o["institutional"]["altman"]["state"] == "no_aplica"
    snow = by["panel/SNOW"]["display"]["charts"]
    assert snow["solvency"]["runway"]["state"] == "con_dato"


def test_comparison_only_applicable_metrics(analyses):
    for name, a in analyses:
        inv.chart_comparison_only_applicable_metrics(a, None)


def test_multiples_role_matches_the_score_breakdown(analyses):
    """Miembro del bloque = ajuste in_block del desglose; lo que no entra ni puntúa aparte es informativo."""
    by = dict(analyses)
    for name, a in analyses:
        inv.chart_multiples_role_matches_breakdown(a, None)
    # cierre de la 1.0 (9-nov-2026): con la regla L1 ningún múltiplo puntúa ni forma un bloque en la gráfica: todos son
    # informativos y la lista de lo que puntúa queda vacía. El P/E TTM no se dibuja (el único P/E es el de la L1).
    for sym in ("NFLX", "FCX", "O"):
        V = by[f"panel/{sym}"]["display"]["charts"]["valuation"]
        assert {m["role"] for m in V["multiples"]} <= {"informative"} and V["scored"] == [] and not V.get("block"), sym
        # el P/E TTM no se dibuja con cifra (en un REIT queda «No aplica», sin valor: su regla L1 usa el P/FFO)
        assert all(m["state"] != "con_dato" for m in V["multiples"] if m["key"] == "pe"), sym
    # el cálculo del bloque sigue en el desglose del motor
    assert any(x.get("in_block") for x in by["panel/NFLX"]["score"]["breakdown"]["Valoración"]["adjustments"])


def test_upside_phrase_follows_the_sensitivity_grid(analyses):
    """Etapa 9c: dentro del grid, "exigentes pero posibles"; fuera, "ningún supuesto razonable". Nunca "muy optimistas"."""
    for name, a in analyses:
        inv.chart_upside_phrase_follows_grid(a, None)