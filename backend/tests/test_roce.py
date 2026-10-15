"""ROCE (etapa 6): EBIT / (activos totales − pasivo corriente), solo MATURE y CYCLICAL."""
import pytest

from classify import not_applicable_text

from archetype_metrics import roce


def _st(ebit, ta, cl, oi=None):
    return {"ebit": ebit, "operating_income": oi or [], "total_assets": ta, "current_liabilities": cl}


def test_roce_definition_and_fallback_to_operating_income():
    r = roce("MATURE", _st([13.5], [55.6], [10.98]), {})
    assert r["roce"] == pytest.approx(13.5 / (55.6 - 10.98)) and r["state"] == "ok"
    r = roce("MATURE", _st([], [99.63], [35.05], oi=[26.56]), {})     # sin fila EBIT: resultado operativo
    assert r["roce"] == pytest.approx(26.56 / (99.63 - 35.05))


@pytest.mark.parametrize("arch", ["FINANCIAL", "REIT"])
def test_roce_not_applicable(arch):
    r = roce(arch, _st([5.0], [100.0], [10.0]), {"roic": 0.1})
    assert r["roce"] is None and r["state"] == "no_aplica" and r["reason"].startswith(not_applicable_text(arch))


@pytest.mark.parametrize("st", [_st([5.0], [10.0], [12.0]),          # capital empleado <= 0
                                _st([5.0], [10.0], []),              # sin pasivo corriente
                                _st([], [10.0], [2.0])])             # sin EBIT
def test_roce_missing_is_never_zero(st):
    r = roce("MATURE", st, {})
    assert r["roce"] is None and r["state"] == "sin_dato" and r["reason"]


def test_cyclical_reports_cycle_average_and_incomplete_cycle():
    r = roce("CYCLICAL", _st([6.74, 7.23, 6.52, 7.28], [58.17, 54.85, 52.51, 51.09], [6.02, 5.5, 5.82, 6.34]), {})
    vals = [6.74 / 52.15, 7.23 / 49.35, 6.52 / 46.69, 7.28 / 44.75]
    assert r["roce_avg"] == pytest.approx(sum(vals) / 4) and r["years"] == 4 and r["cycle_incomplete"] is True
    assert "roce_avg" not in roce("MATURE", _st([1.0], [10.0], [2.0]), {})


def test_divergence_flag_and_probable_causes():
    st = _st([10.0], [120.0], [20.0])                                 # ROCE 10%
    r = roce("MATURE", st, {"roic": 0.25, "cash": 30.0, "total_assets": 120.0})
    assert r["diverges"] and r["gap"] == pytest.approx(-0.15)
    assert any("caja excedente" in c for c in r["causes"])
    r = roce("MATURE", st, {"roic": 0.18})
    assert r["diverges"] is False and "causes" not in r
    r = roce("MATURE", _st([30.0], [120.0], [20.0]), {"roic": 0.15})  # ROCE 30% > ROIC
    assert any("base fiscal" in c for c in r["causes"])


def test_fixtures(outputs_by_env):
    import conftest
    for env in conftest.BOUND_ENVS:
        out = outputs_by_env(env)
        nflx = out["NFLX"][0]["key_metrics"]
        assert nflx["roce"] == pytest.approx(0.3026, abs=5e-4)      # RECON §4: 30.3%
        fcx = out["FCX"][0]["key_metrics"]
        assert fcx["roce"] == pytest.approx(0.1292, abs=5e-4)       # RECON §4: 12.9%
        assert fcx["roce_cycle_incomplete"] is True and fcx["roce_years"] == 4
        for sym in ("JPM", "O"):
            km = out[sym][0]["key_metrics"]
            assert km["roce"] is None and km["roce_state"] == "no_aplica"
        # la comparación con el ROIC siempre se informa (con TTM, FCX ya no diverge > 10 pp)
        div = out["FCX"][0]["key_metrics"]["roce_roic_divergence"]
        assert set(div) == {"diverges", "gap", "causes"}
