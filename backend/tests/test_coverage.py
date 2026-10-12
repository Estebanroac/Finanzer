"""Etapa 5: datos faltantes y cobertura.

Principio: un dato ausente nunca cuenta como incumplimiento ni como cero. Se
excluye, se reporta la cobertura y, si es insuficiente, el indicador se declara
no concluyente. Datos sintéticos.
"""
import pytest

import fixture_backend  # noqa: F401  (añade backend/ y lib/ al path)
from financial_ratios import piotroski_evaluate, piotroski_f_score, piotroski_level
from settings import cfg

_FULL = dict(
    net_income=100, roa_current=0.10, roa_prior=0.08, operating_cash_flow=150,
    long_term_debt_current=80, long_term_debt_prior=100,
    current_ratio_current=2.0, current_ratio_prior=1.5,
    shares_current=95, shares_prior=100,
    gross_margin_current=0.50, gross_margin_prior=0.40,
    asset_turnover_current=1.1, asset_turnover_prior=1.0,
)
_PRIORS = ("roa_prior", "long_term_debt_prior", "current_ratio_prior", "shares_prior",
           "gross_margin_prior", "asset_turnover_prior")


def _states(r):
    return {c["key"]: c["state"] for c in r["criteria"]}


# ─────────────────────────── Piotroski: tres estados ───────────────────────────
def test_piotroski_states_cumple_no_cumple_sin_dato():
    r = piotroski_evaluate(**dict(_FULL, roa_current=-0.01, shares_prior=None))
    st = _states(r)
    assert st["roa_positive"] == "no_cumple"
    assert st["roa_improved"] == "no_cumple"
    assert st["no_dilution"] == "sin_dato"
    assert st["cfo_positive"] == "cumple"
    assert set(st.values()) <= {"cumple", "no_cumple", "sin_dato"}


def test_missing_data_is_not_a_failure():
    """Un criterio sin dato no resta: X/N con N < 9."""
    r = piotroski_evaluate(**dict(_FULL, shares_prior=None))
    assert r["score"] == 8 and r["evaluated"] == 8


def test_full_coverage_is_identity():
    r = piotroski_evaluate(**_FULL)
    assert r["evaluated"] == 9 and r["scaled_score"] == 9 and isinstance(r["scaled_score"], int)
    assert r["conclusive"] and r["interpretation"].startswith("Excelente")


def test_scaling_with_seven_or_eight_evaluated():
    # 6 de 8 evaluados -> 6·9/8 = 6.75 -> banda >= 6 ("Bueno")
    r = piotroski_evaluate(**dict(_FULL, shares_prior=None, gross_margin_current=0.30,
                                  asset_turnover_current=0.9))
    assert (r["score"], r["evaluated"]) == (6, 8)
    assert r["scaled_score"] == pytest.approx(6.75)
    assert r["interpretation"].startswith("Bueno") and piotroski_level(r["scaled_score"], True) == "Bueno"
    # 7 evaluados es el mínimo concluyente
    r7 = piotroski_evaluate(**dict(_FULL, shares_prior=None, gross_margin_prior=None))
    assert r7["evaluated"] == 7 and r7["conclusive"] and r7["scaled_score"] == pytest.approx(9.0)


def test_below_min_evaluated_is_inconclusive():
    assert cfg("valuation.models.piotroski.min_evaluated") == 7
    r = piotroski_evaluate(**dict(_FULL, shares_prior=None, gross_margin_prior=None,
                                  asset_turnover_prior=None))
    assert r["evaluated"] == 6 and not r["conclusive"] and r["scaled_score"] is None
    assert "no concluyente" in r["interpretation"]
    assert piotroski_level(None, False) == "No concluyente"


def test_no_history_is_inconclusive_and_not_counted_as_failures():
    r = piotroski_evaluate(**{k: (None if k in _PRIORS else v) for k, v in _FULL.items()})
    assert (r["score"], r["evaluated"]) == (3, 3) and not r["conclusive"]
    assert sum(1 for c in r["criteria"] if c["state"] == "no_cumple") == 0


def test_legacy_wrapper_keeps_contract():
    score, details, interp = piotroski_f_score(**_FULL)
    assert score == 9 and len(details) == 9 and all(d.startswith("✓") for d in details)


def test_main_reads_structured_state_not_symbol(outputs_by_env):
    """main.py expone el estado estructurado; 'passed' sale del estado, no del texto."""
    import conftest
    for env in conftest.ENVS:
        for sym, (a, _) in outputs_by_env(env).items():
            pf = a["piotroski_f"]
            for key, c in pf["details"].items():
                assert c["state"] in {"cumple", "no_cumple", "sin_dato"}, (env, sym, key)
                assert c["passed"] == (c["state"] == "cumple")
            n_eval = sum(1 for c in pf["details"].values() if c["state"] != "sin_dato")
            assert pf["evaluated"] == n_eval
            assert pf["score"] == sum(1 for c in pf["details"].values() if c["state"] == "cumple")
