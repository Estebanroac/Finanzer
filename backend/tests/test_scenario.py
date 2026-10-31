"""Rediseño E2a (T7): escenario del usuario con el mismo DCF por etapas del motor (sin estado; no cambia el
veredicto). Con los supuestos base reproduce exactamente el valor del motor."""
import glob
import json

import pytest

import scenario

SI = {"status": "ok", "reason": None, "fcf": 100.0, "shares_outstanding": 10.0, "net_debt": 0.0, "price": 100.0,
      "currency": "USD", "base": {"high_growth_rate": 0.1, "high_growth_years": 5, "transition_years": 5,
                                  "terminal_growth": 0.025, "discount_rate": 0.09, "decay_type": "step"}}


@pytest.fixture(scope="module")
def panel():
    """El golden del panel (Task 11: ya trae scenario_inputs)."""
    out = {}
    for path in sorted(glob.glob("tests/golden/panel/*.json")):
        a = json.load(open(path, encoding="utf-8"))
        if not a.get("__http_error__"):
            out[a["symbol"]] = a
    return out


def test_con_los_supuestos_base_reproduce_el_valor_del_motor(panel):
    n = 0
    for t, a in panel.items():
        si = a.get("scenario_inputs") or {}
        fv = (a.get("dcf") or {}).get("fair_value")
        if si.get("status") != "ok" or fv is None:
            assert fv is None or (a.get("dcf") or {}).get("not_significant"), t
            continue
        r = scenario.run(si, {})
        assert r["status"] == "ok" and r["clamped"] == [], t
        assert r["fair_value"] == pytest.approx(fv, rel=1e-9), t
        n += 1
    assert n >= 20          # la mayoría del panel tiene DCF significativo


def test_sin_dcf_dice_por_que(panel):
    si = panel["JPM"]["scenario_inputs"]
    assert si["status"] == "sin_dato" and si["reason"]
    assert scenario.run(si, {})["status"] == "sin_dato"


def test_recorta_supuestos_fuera_de_rango():
    r = scenario.run(SI, {"high_growth_rate": 0.9, "terminal_growth": 0.085})
    assert r["status"] == "ok"
    assert r["assumptions_used"]["high_growth_rate"] == 0.50
    assert r["assumptions_used"]["terminal_growth"] <= 0.09 - 0.02
    assert set(r["clamped"]) == {"high_growth_rate", "terminal_growth"}


def test_mas_descuento_menos_valor():
    base = scenario.run(SI, {})["fair_value"]
    assert scenario.run(SI, {"discount_rate": 0.11})["fair_value"] < base
    assert scenario.run(SI, {"discount_rate": 0.11})["upside"] == pytest.approx(
        scenario.run(SI, {"discount_rate": 0.11})["fair_value"] / 100.0 - 1)


def test_endpoint_sin_estado():
    """El endpoint (sin cliente HTTP: el entorno no trae httpx; el curl contra el replay lo prueba por HTTP)."""
    from fastapi import HTTPException
    import main
    r = main.scenario_v2({"inputs": SI, "assumptions": {"discount_rate": 0.11}})
    assert r["status"] == "ok" and r["assumptions_used"]["discount_rate"] == 0.11
    with pytest.raises(HTTPException) as e:
        main.scenario_v2({"assumptions": {}})
    assert e.value.status_code == 422


# ─────────────── Rediseño E3 (Task 7): margen de caja, preajustes, qué exige el precio y sensibilidad ───────────────
from settings import cfg  # noqa: E402

SI3 = {**SI, "revenue": 400.0, "fcf_margin": 0.25, "archetype": "MATURE",
       "reverse": {"flow_per_share": 10.0, "net_debt_per_share": 0.0, "rate": 0.09, "terminal_growth": 0.025}}


def test_scenario_inputs_traen_margen_arquetipo_inverso_preajustes_y_limites(panel):
    a = panel["AAPL"]
    si = a["scenario_inputs"]
    assert si["status"] == "ok" and si["archetype"] == a["classification"]["archetype"]
    assert si["revenue"] and si["fcf_margin"] == pytest.approx(si["fcf"] / si["revenue"])
    rv = a["reverse_dcf"]["main"]
    assert si["reverse"] == {"flow_per_share": rv["flow_per_share"], "net_debt_per_share": rv["net_debt_per_share"],
                             "rate": rv["rate"], "terminal_growth": rv["terminal_growth"]}
    b = si["bounds"]
    for name, k in (("growth", "high_growth_rate"), ("discount", "discount_rate"), ("terminal", "terminal_growth")):
        for side in ("pessimistic", "optimistic"):
            v = si["presets"][side][k]
            assert b[name][0] <= v <= b[name][1], (name, side, v)
    assert si["presets"]["pessimistic"]["high_growth_rate"] < si["base"]["high_growth_rate"] < \
        si["presets"]["optimistic"]["high_growth_rate"]
    assert b["fcf_margin"][0] < si["fcf_margin"] < b["fcf_margin"][1]


def test_preajustes_son_los_extremos_de_la_tabla_de_sensibilidad_del_informe():
    G = cfg("valuation.grid")
    P = cfg("valuation.scenario.presets.default")
    assert P["pessimistic"]["growth"] == G["growth_range"][0] and P["optimistic"]["growth"] == G["growth_range"][1]
    assert P["pessimistic"]["discount"] == G["discount_range"][1] and P["optimistic"]["discount"] == G["discount_range"][0]


def test_con_los_supuestos_base_exige_el_mismo_crecimiento_que_el_inverso_del_motor(panel):
    n = 0
    for t, a in panel.items():
        si = a.get("scenario_inputs") or {}
        rv = (a.get("reverse_dcf") or {}).get("main") or {}
        if si.get("status") != "ok" or not si.get("reverse") or rv.get("state") != "ok":
            continue
        if si["base"]["discount_rate"] != rv["rate"]:
            continue          # el inverso usa otra tasa (REIT: Ke); el escenario dice la suya
        r = scenario.run(si, {})
        assert r["implied_growth"]["state"] == "ok", t
        assert r["implied_growth"]["g_star"] == pytest.approx(rv["g_star"], rel=1e-6), t
        assert r["implied_growth"]["g10"] == pytest.approx(rv["g10"], rel=1e-6), t
        n += 1
    assert n >= 10


def test_margen_de_caja_mueve_el_flujo_y_el_valor():
    base = scenario.run(SI3, {})
    assert base["fair_value"] == pytest.approx(scenario.run(SI, {})["fair_value"])      # FCF base = el del motor
    more = scenario.run(SI3, {"fcf_margin": 0.30})
    assert more["fair_value"] > base["fair_value"]
    assert more["assumptions_used"]["fcf_margin"] == 0.30
    assert more["implied_growth"]["g_star"] < base["implied_growth"]["g_star"]   # más caja: el precio exige menos
    lo, hi = cfg("valuation.scenario.margin_rel_min"), cfg("valuation.scenario.margin_rel_max")
    r = scenario.run(SI3, {"fcf_margin": 0.99})
    assert r["assumptions_used"]["fcf_margin"] == pytest.approx(0.25 * hi) and "fcf_margin" in r["clamped"]
    assert scenario.run(SI3, {"fcf_margin": 0.01})["assumptions_used"]["fcf_margin"] == pytest.approx(0.25 * lo)


def test_sensibilidad_5x5_monotona_y_centrada_en_los_supuestos_del_usuario():
    r = scenario.run(SI3, {"high_growth_rate": 0.12, "discount_rate": 0.10})
    s = r["sensitivity"]
    assert len(s["growth"]) == 5 and len(s["discount"]) == 5 and len(s["values"]) == 5
    assert s["growth"][2] == pytest.approx(0.12) and s["discount"][2] == pytest.approx(0.10)
    assert s["values"][2][2] == pytest.approx(r["fair_value"])
    for row in s["values"]:                                   # más WACC → menos valor
        vals = [v for v in row if v is not None]
        assert all(a > b for a, b in zip(vals, vals[1:]))
    for j in range(5):                                        # más crecimiento → más valor (filas de menos a más)
        col = [row[j] for row in s["values"] if row[j] is not None]
        assert all(a < b for a, b in zip(col, col[1:]))


def test_sensibilidad_cada_celda_vacia_dice_por_que():
    """V4b · 4 (PM): una celda sin valor lleva su porqué en `why` («fuera» de los límites del análisis o «≤ 0»); las que
    tienen valor, None. La web lo pinta en lugar de un «—»."""
    for over in ({"high_growth_rate": 0.12, "discount_rate": 0.10}, {"high_growth_rate": -0.10, "discount_rate": 0.16},
                 {"high_growth_rate": cfg("valuation.scenario.growth_max"), "discount_rate": cfg("valuation.scenario.discount_min")}):
        s = scenario.run(SI3, over)["sensitivity"]
        assert len(s["why"]) == len(s["values"])
        for vals, whys in zip(s["values"], s["why"]):
            for v, w in zip(vals, whys):
                assert (v is None) == (w is not None)
                assert w in (None, "fuera", "≤ 0")


def test_sensibilidad_base_igual_a_la_del_informe(panel):
    """Con los supuestos base, la tabla del escenario es la del informe (mismos pasos: config [grid])."""
    a = panel["AAPL"]
    r = scenario.run(a["scenario_inputs"], {})
    grid = a["sensitivity"]
    assert not (grid.get("trimmed") or {}).get("growth") and not (grid.get("trimmed") or {}).get("discount")
    mine = r["sensitivity"]
    assert [round(g, 4) for g in mine["growth"]] == grid["growth_rates"]        # el informe redondea los ejes
    assert [round(d, 4) for d in mine["discount"]] == grid["discount_rates"]
    n = 0
    for row_m, row_g in zip(mine["values"], grid["matrix"]):
        for vm, vg in zip(row_m, row_g):
            if vm is not None and vg is not None:
                assert vm == pytest.approx(vg, abs=0.006)                       # y los valores a céntimos
                n += 1
    assert n == 25


def test_bandas_y_tono_los_decide_el_motor_como_en_el_informe(panel):
    """Revisión V6 (F17): la banda de cada celda y el tono del resultado vienen del motor (la misma regla que la
    sensibilidad del informe), no del navegador."""
    import display
    a = panel["AAPL"]
    r = scenario.run(a["scenario_inputs"], {})
    s, price = r["sensitivity"], a["scenario_inputs"]["price"]
    assert s["band_labels"] == display.sensitivity_band_labels() and len(s["band_labels"]) == 5
    assert s["bands"] == [[display.sensitivity_band(v, price) for v in row] for row in s["values"]]
    assert {b for row in s["bands"] for b in row} <= {0, 1, 2, 3, 4, None}
    # con los supuestos base, las mismas bandas que la tabla del informe
    rep = a["display"]["sections"]["valuation"]["sensitivity"]
    assert [[c["band"] for c in row["cells"]] for row in rep["rows"]] == s["bands"]
    assert r["upside_tone"] == ("pos" if r["upside"] >= 0 else "neg")
    assert display.sensitivity_band(None, 100) is None and display.sensitivity_band(150, None) is None
