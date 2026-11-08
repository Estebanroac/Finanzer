"""
F15 (expectativas golden del evaluador, 6-nov-2026): el lector de las expectativas, las reglas globales y las tres
correcciones del precio (P/FCF de mantenimiento, el máximo del DCF solo fuera de la tabla de sensibilidad y R11).
"""
import os

import pytest

import expectativas as X
import financial_ratios as fr
import verdict as V

BANCO = ("/Users/joseestebanroa/Downloads/Finanzer/archivo-historico/evidencias-de-pruebas/"
         "f15_banco110_2026-11-06/final")


# ── el archivo de expectativas ──
def test_the_expectations_file_reads_whole():
    g = X.load_yaml()
    assert len(g["empresas"]) == 110 and [r["id"] for r in g["reglas_globales"]] == [f"R{i}" for i in range(1, 12)]
    assert g["reglas_globales"][1]["regla"].endswith("difieren más de 40%.")       # valor en dos líneas
    e = {x["ticker"]: x for x in g["empresas"]}
    assert e["MSFT"]["precio_aceptable"] == ["entre exigente y muy exigente", "exigente"]
    assert e["GOOGL"]["por_que"].startswith("P/E normalizado ~27x con crecimiento de 18%: ")   # entre comillas
    assert e["MRNA"]["arquetipo_no"] == ["MATURE"] and e["WFC"]["debe_mostrar"] == ["riesgo de crédito no medido"]
    assert all(p in g["escala_precio"] for x in g["empresas"] for p in x["precio_aceptable"])


def test_a_company_check_no_longer_checks_price_or_confidence():
    """F16: los rangos de precio del YAML se retiraron (la etiqueta es la regla L1). Fase 1 · pendientes: también
    `confianza_max` (la confianza ya no se muestra; la consistencia no mide lo mismo). Los dos siguen en el YAML."""
    e = {"precio_aceptable": ["exigente"], "confianza_max": "baja"}
    a = {"verdict": {"text": "Calidad sólida · precio atractivo", "consistency": "consistente"}}
    assert X.check_company(e, a) == []
    assert X.price_label(a) == "atractivo"
    g = X.load_yaml()
    assert sum(1 for x in g["empresas"] if x.get("confianza_max")) == 31      # registro intacto


def test_global_rules_catch_a_single_method_floor_price():
    a = {"verdict": {"price_level": "muy exigente"},
         "confidence": {"dimensions": {"convergence": {"methods": [
             {"evaluable": True, "direction": "cara"}, {"evaluable": True, "direction": "en precio"}]}}}}
    assert any(r.startswith("R11") for r in X.global_rules("X", a))


# ── causa 1: P/FCF con el flujo del DCF ──
def _val(**kw):
    base = dict(pe=None, p_fcf=60.0, ev_ebitda=None, peg=None)
    base.update(kw)
    return fr.score_valoracion(**base)


def test_pfcf_uses_the_maintenance_flow_when_the_dcf_does():
    r = _val(archetype="MATURE", xv={"p_fcf_maintenance": 24.0})
    row = next(x for x in r["adjustments"] if x["metric"].startswith("P/FCF"))
    assert row["metric"] == "P/FCF de mantenimiento" and row["value"] == "24.00x" and "mismo que el DCF" in row["reason"]
    plain = next(x for x in _val(archetype="MATURE", xv={})["adjustments"]
                 if x["metric"].startswith("P/FCF"))
    assert plain["metric"] == "P/FCF" and plain["adjustment"] < row["adjustment"]


# ── causa 3: el máximo del DCF solo si ningún supuesto razonable alcanza el precio ──
def _dcf(grid):
    r = _val(p_fcf=None, archetype="MATURE", xv={},
             dcf={"upside": -0.45, "reliability": "alta", "grid_contains_price": grid})
    return next(x for x in r["adjustments"] if x.get("key") == "dcf")


def test_dcf_max_penalty_only_outside_the_sensitivity_grid():
    assert _dcf(False)["adjustment"] == -4
    inside = _dcf(True)
    assert inside["adjustment"] == -2 and "tabla de sensibilidad" in inside["reason"]


# ── R11: ningún método solo lleva el precio a «muy exigente» ──
def _cats(points):
    return [{"category": "Valoración", "score": points, "max": 20, "included": True}]


def test_one_method_alone_cannot_make_the_price_very_demanding():
    one = [{"evaluable": True, "direction": "cara"}, {"evaluable": True, "direction": "en precio"}]
    p = V.price(_cats(4), "media", methods=one)
    assert p["score_raw"] == 30 and p["single_method_floor"]["from"] == 20 and p["level"] == "exigente"
    two = [{"evaluable": True, "direction": "cara"}, {"evaluable": True, "direction": "cara"}]
    assert V.price(_cats(4), "media", methods=two)["level"] == "muy exigente"


# ── el banco congelado: cero incumplimientos de las reglas globales y ninguna regresión ──
def test_frozen_bank_meets_the_global_rules_and_keeps_its_passes():
    if not os.path.isdir(BANCO):
        pytest.skip("sin el banco congelado de las 110")
    r = X.evaluate(BANCO)
    assert not r["rules"], r["rules"]
    import json
    with open(X.ESTADO, encoding="utf-8") as fh:
        prev = set(json.load(fh)["ok"])
    assert prev <= set(r["ok"]), sorted(prev - set(r["ok"]))
