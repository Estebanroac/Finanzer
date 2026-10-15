"""
Fase 0 del plan de fiabilidad: los invariantes extraídos a invariants.py siguen DETECTANDO errores.

Para cada uno de los 26: se toma un análisis real del juego local que lo cumple, se comprueba que pasa, se
inyecta una violación concreta y se exige AssertionError. Si una violación no se detecta, el invariante
quedó roto (o vacío) al extraerlo. Sin red.
"""
import copy

import pytest

import fixture_backend as fb
import invariants as inv


def _first(items, pred):
    return next(x for x in items if pred(x))


def _graham_on_na_pe(a, t):
    return a, t + "\nNúmero de Graham: 12.3"


# nombre -> (ticker base del juego local, función que viola el invariante: (a, text) -> (a, text))
# Las funciones mutan copias profundas; las precondiciones (que exista lo que se toca) las comprueba el test.
VIOLATIONS = {
    "piotroski_state_is_structured": ("NFLX", lambda a, t: (
        next(iter(a["piotroski_f"]["details"].values())).update(state="quizas") or a, t)),
    "display_contract": ("NFLX", lambda a, t: (
        a["display"]["cover"].update(kpis=a["display"]["cover"]["kpis"][:7]) or a, t)),
    "institutional_not_applicable_never_zero": ("NFLX", lambda a, t: (
        a["altman_z"].update(applicable=False, z_score=0.0) or a, t)),
    "confidence_reasons_translated": ("NFLX", lambda a, t: (
        a["display"]["cover"].update(confidence_reasons=["11 campos de Finnhub"]) or a, t)),
    "tooltips_only_applied_bands": ("NFLX", lambda a, t: (
        _first([tb for tip in a["display"]["tooltips"].values() for tb in tip["tables"]], lambda tb: tb["bands"])
        ["bands"][0].update(tone="rojo") or a, t)),
    "visible_texts_without_jargon_or_bad_formats": ("NFLX", lambda a, t: (
        a["display"]["cover"]["highlights"][0].update(text="Empresa MATURE con caja") or a, t)),
    "growth_texts_cite_the_scored_figure": ("NFLX", lambda a, t: (
        a["display"]["sections"]["growth"].update(intro="Crece mucho.") or a, t)),
    "piotroski_criteria_in_spanish": ("NFLX", lambda a, t: (
        a["display"]["sections"]["institutional"]["piotroski_criteria"][0].update(label="Net Income positive")
        or a, t)),
    "price_wording_without_jargon": ("NFLX", lambda a, t: (
        a["display"]["summary"].update(extra="precio crudo") or a, t)),
    "verdict_in_pdf": ("NFLX", lambda a, t: (a, t.replace(a["verdict"]["text"], ""))),
    "price_excludes_quality_built_bonuses": ("NFLX", lambda a, t: (
        a["score"]["breakdown"]["Valoración"]["adjustments"].append({"metric": "Perfil GARP", "adjustment": 2})
        or a, t)),
    "eps_vs_revenue_growth_is_informative_only": ("NFLX", lambda a, t: (
        a["score"]["breakdown"]["Crecimiento"]["adjustments"].append(
            {"metric": "BPA frente a ingresos", "adjustment": 1}) or a, t)),
    "multiples_block_averages_members_and_caps_at_max": ("NFLX", lambda a, t: (
        _first(a["score"]["breakdown"]["Valoración"]["adjustments"], lambda x: x["metric"].startswith("Bloque"))
        .update(adjustment=99) or a, t)),
    "normalized_figures_are_labelled": ("JPM", lambda a, t: (
        a.update(earnings_normalization={"differs": False}) or
        a["score"]["breakdown"]["Valoración"]["adjustments"].append({"metric": "P/E normalizado", "adjustment": 0})
        or a, t)),
    "range_52w_is_position_only": ("NFLX", lambda a, t: (a, t + "\nPRECIO · 52 SEM.")),
    "no_text_cites_a_not_applicable_metric": ("SNOW", _graham_on_na_pe),
    "cover_fits_one_page": ("NFLX", lambda a, t: (
        a, t.replace("===== página 2 =====", "===== página 2 =====\nFORTALEZA CLAVE", 1))),
    "provenance_in_vocabulary": ("NFLX", lambda a, t: (
        next(iter(a["data_provenance"]["fields"].values())).update(source="inventada") or a, t)),
    "no_archetype_codes_nor_sign_after_symbol": ("NFLX", lambda a, t: (a, "Valor razonable $-8\n" + t)),   # antes del anexo (D1)
    "dcf_never_negative_fair_value": ("NFLX", lambda a, t: (a["dcf"].update(fair_value=-5.0) or a, t)),
    "chart_gauges_marker_in_reading_zone": ("NFLX", lambda a, t: (
        _first(a["display"]["charts"]["solvency"]["gauges"],
               lambda g: g["state"] == "con_dato" and not (g.get("informative") or g.get("net_cash")
                                                           or g.get("negative")))
        .update(reading="ZZZ") or a, t)),
    "chart_fair_value_in_badge_zone": ("NFLX", lambda a, t: (
        a["display"]["charts"]["valuation"]["fair_value"]["badge"].update(label="Zona inventada") or a, t)),
    "chart_altman_in_model_zone": ("NFLX", lambda a, t: (
        a["display"]["charts"]["institutional"]["altman"].update(zone="Zona inventada") or a, t)),
    "chart_comparison_only_applicable_metrics": ("NFLX", lambda a, t: (
        a["display"]["charts"]["comparison"].update(total=a["display"]["charts"]["comparison"]["total"] + 1)
        or a, t)),
    "chart_multiples_role_matches_breakdown": ("NFLX", lambda a, t: (
        a["display"]["charts"]["valuation"]["multiples"].append({"key": "x", "role": "block"}) or a, t)),
    "chart_upside_phrase_follows_grid": ("NFLX", lambda a, t: (
        a["display"]["cover"]["highlights"][0].update(text="supuestos muy optimistas") or a, t)),
}


def test_every_generic_invariant_has_a_violation():
    assert set(VIOLATIONS) == set(inv.GENERIC)


@pytest.mark.parametrize("name", sorted(VIOLATIONS))
def test_invariant_detects_its_violation(name, outputs_by_env):
    sym, violate = VIOLATIONS[name]
    a0, pdf = outputs_by_env("local")[sym]
    text0 = fb.pdf_text(pdf)
    check = inv.GENERIC[name]
    check(copy.deepcopy(a0), text0)                       # el caso real lo cumple
    a, text = violate(copy.deepcopy(a0), text0)
    assert (a, text) != (a0, text0), "la violación no cambió nada"
    with pytest.raises(AssertionError):
        check(a, text)


def test_not_applicable_violation_uses_an_archetype_where_pe_does_not_apply(outputs_by_env):
    """Precondición de la violación de no_text_cites_a_not_applicable_metric."""
    from settings import cfg
    a = outputs_by_env("local")[VIOLATIONS["no_text_cites_a_not_applicable_metric"][0]][0]
    assert "pe" in cfg(f"sectors.archetypes.not_applicable.{a['classification']['archetype']}")


def test_growth_sign_by_verb_is_a_citation_but_a_wrong_verb_is_not():
    assert inv.cites_growth("Los ingresos se contraen un 5.0% anual de ciclo medio.", -0.05)
    assert inv.cites_growth("Los ingresos varían -5.0% anual.", -0.05)
    assert not inv.cites_growth("Los ingresos crecen 5.0% anual.", -0.05)
    assert not inv.cites_growth("Los ingresos se contraen un 4.0% anual.", -0.05)
    assert not inv.cites_growth("Los ingresos se contraen un 5.0% anual.", +0.05)
