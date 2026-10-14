"""Regresión: el comportamiento actual desde fixtures == golden, en cada juego
de datos disponible (local siempre; prod cuando se haya importado).

Si falla tras un cambio intencionado, revisa con
`python3 tests/diff_golden.py --env <env>` y regenera de forma explícita.
Los golden describen el comportamiento ACTUAL (con sus bugs), no el correcto.
"""
import json
import os

import pytest

import fixture_backend as fb
from conftest import ENVS, REG_ENVS, REG_ENV_TICKERS, env_id


def test_seams_exist():
    """Los puntos de enganche de la capa de inyección siguen existiendo."""
    assert fb.check_seams() == []


def test_local_env_present():
    assert "local" in ENVS


@pytest.mark.parametrize("env_sym", REG_ENV_TICKERS, ids=env_id)
def test_fixtures_have_metadata(env_sym):
    env, sym = env_sym
    store = fb.FixtureStore(fb.fixtures_dir(env))
    store.load(sym)
    meta = store.meta[sym]
    assert meta["ticker"] == sym and meta["environment"] == env
    assert meta["captured_at_utc"]
    assert "participated" in meta["finnhub"] and "degraded" in meta["yahoo"]


@pytest.mark.parametrize("env_sym", REG_ENV_TICKERS, ids=env_id)
def test_analysis_matches_golden(env_sym, outputs_by_env):
    env, sym = env_sym
    jpath, _ = fb.golden_paths(sym, fb.golden_dir(env))
    assert os.path.isfile(jpath), f"falta golden: python3 tests/diff_golden.py --env {env} --regenerate {sym}"
    with open(jpath, encoding="utf-8") as fh:
        golden = fh.read()
    if fb.stable_json(outputs_by_env(env)[sym][0]) != golden:
        pytest.fail(f"[{env}] {sym}: el análisis difiere del golden. "
                    f"Detalle: python3 tests/diff_golden.py --env {env} {sym}")


@pytest.mark.parametrize("env_sym", REG_ENV_TICKERS, ids=env_id)
def test_pdf_text_matches_golden(env_sym, outputs_by_env):
    env, sym = env_sym
    _, tpath = fb.golden_paths(sym, fb.golden_dir(env))
    with open(tpath, encoding="utf-8") as fh:
        golden = fh.read()
    if fb.pdf_text(outputs_by_env(env)[sym][1]) != golden:
        pytest.fail(f"[{env}] {sym}: el texto del PDF difiere del golden. "
                    f"Detalle: python3 tests/diff_golden.py --env {env} {sym}")


@pytest.mark.parametrize("env", REG_ENVS)
def test_replay_uses_only_recorded_inputs(env, outputs_by_env):
    """Ningún acceso del pipeline queda sin servir desde los fixtures (compute_outputs falla si alguno
    no está grabado; los tickers rechazados, como SPY, también cuentan)."""
    assert set(outputs_by_env(env)) == set(fb.env_tickers(env))
    with fb.replay(fb.fixtures_dir(env)) as store:
        for sym in fb.env_tickers(env):
            try:
                fb.run_analysis(sym, store)
            except Exception as e:      # rechazo HTTP esperado (422): no es un acceso no grabado
                assert getattr(e, "status_code", None), e
        assert store.misses == []


@pytest.mark.parametrize("env_sym", REG_ENV_TICKERS, ids=env_id)
def test_golden_is_valid_json(env_sym):
    env, sym = env_sym
    with open(fb.golden_paths(sym, fb.golden_dir(env))[0], encoding="utf-8") as fh:
        g = json.load(fh)
        assert g.get("symbol") == sym or g.get("__http_error__")


@pytest.mark.skipif(not {"local", "prod"} <= set(ENVS), reason="faltan los juegos local y prod")
def test_local_vs_prod_compare_runs(capsys):
    """El modo --local-vs-prod de diff_golden corre y atribuye causas."""
    import diff_golden
    assert diff_golden.compare_envs(["NFLX"], full=False) == 0
    out = capsys.readouterr().out
    assert "NFLX" in out and "← causa:" in out
