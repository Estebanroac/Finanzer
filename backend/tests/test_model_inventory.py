"""
Modelo general: tools/model_inventory.py lee el motor sin perder componentes.

- Todo componente que el código registra en la cobertura tiene su fórmula y su referencia en META (y META no guarda
  componentes que ya no existen): si alguien añade una variable al score, el inventario lo obliga a describirla.
- La lectura estática encuentra lo que el motor registra de verdad (la muestra medida con los fixtures).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "tools"))

import model_inventory as mi  # noqa: E402


def _static():
    return {(c["category"], c["name"]) for c in mi.scored_components() if not c["name"].startswith("(")}


def test_cada_componente_del_codigo_esta_en_meta():
    names = {n for _, n in _static()}
    assert names - set(mi.META) == set(), "componentes sin fórmula en META"
    assert set(mi.META) - names - {"P/B frente al ROE regulado"} == set(), "META con componentes que ya no existen"
    assert mi.canon("DCF inverso (FCF − SBC)") == mi.canon("DCF inverso (FFO)") == "DCF inverso"


def test_la_lectura_estatica_ve_lo_que_el_motor_registra():
    sample = mi.fixture_sample()
    measured = {(cat, n) for (cat, n) in mi.applicability(sample)["table"]}
    static = _static()
    # El nombre del DCF inverso de utility sale de la reverse del análisis (no es un literal): solo medido.
    assert measured - static <= {("Valoración", "P/B frente al ROE regulado")}, measured - static
    assert {("Solidez Financiera", "Altman Z"), ("Crecimiento", "Crecimiento del BPA"),
            ("Rentabilidad", "FFO / activos"), ("Valoración", "Bloque de múltiplos")} <= static


def test_resuelve_bandas_de_bucles_y_claves_no_aplica():
    by = {(c["category"], c["name"]): c for c in mi.scored_components()}
    eps = by[("Crecimiento", "Crecimiento del BPA")]
    assert eps["points"] == ["thresholds.score.crecimiento.eps_points"] and eps["na_key"] == "eps_growth"
    opm = [c for c in mi.scored_components() if c["name"] == "Margen operativo" and c["function"] == "score_rentabilidad"]
    assert [c["na_key"] for c in opm] == ["operating_margin"]
    assert by[("Solidez Financiera", "Altman Z")]["points"] == ["thresholds.score.solidez.altman_points"]


def test_ramas_por_arquetipo_y_tipos_de_clasificacion():
    files = [os.path.join(mi.LIB, "financial_ratios.py")]
    br = mi.archetype_branches(files)
    assert any("REIT" in b["types"] and b["function"] == "score_valoracion" for b in br)
    rules = {(r["archetype"], r["rule"]) for r in mi.classification_rules()}
    assert ("FINANCIAL", "industria_banco") in rules and ("MATURE", "por_defecto") in rules
    assert set(mi.TARGET_TYPES.values()) and {t for t, _ in mi.TARGET_TYPES.values()} <= set(mi.TARGET)
