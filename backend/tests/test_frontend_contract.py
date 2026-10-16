"""Etapa 9b: contrato backend -> frontend y umbrales literales en la web.

Ejecuta los dos guardianes del frontend (Node) sobre las salidas ACTUALES del
backend (los 12 casos de fixtures):
  · frontend/scripts/check-contract.mjs: falla si src/lib/api.ts declara (y por
    tanto la web puede leer) un campo que el backend no expone, o con otro tipo;
  · frontend/scripts/check-analysis-literals.mjs: falla si un componente de
    análisis compara contra un umbral numérico literal.
Se saltan si no hay Node o node_modules (typescript) en el entorno.
"""
import os
import shutil
import subprocess

import pytest

import fixture_backend as fb
from conftest import ENVS

FRONTEND = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
NODE = shutil.which("node")
needs_node = pytest.mark.skipif(
    not NODE or not os.path.isdir(os.path.join(FRONTEND, "node_modules", "typescript")),
    reason="sin Node o sin node_modules del frontend")


def _run(script, *args):
    return subprocess.run([NODE, os.path.join("scripts", script), *args], cwd=FRONTEND,
                          capture_output=True, text=True, timeout=300)


@needs_node
def test_frontend_reads_only_exposed_fields(outputs_by_env, tmp_path):
    dirs = []
    for env in ENVS:
        d = tmp_path / env
        d.mkdir()
        for sym, (analysis, _) in outputs_by_env(env).items():
            (d / f"{sym}.json").write_text(fb.stable_json(analysis), encoding="utf-8")
        dirs.append(str(d))
    # Casos raros que ningún ticker real cubre (tests/contract_forced.py): los mismos que ve `npm run check`.
    extra = tmp_path / "forzado"
    extra.mkdir()
    import contract_forced
    contract_forced.write(contract_forced.build({t: a for t, (a, _) in outputs_by_env(ENVS[-1]).items()}), str(extra))
    r = _run("check-contract.mjs", "--strict-unions", *dirs, str(extra))
    assert r.returncode == 0, r.stderr or r.stdout


def test_forced_samples_are_up_to_date(outputs_by_env):
    """Las muestras forzadas guardadas (tests/golden/forzados, las que lee `npm run check`) son las de hoy."""
    import contract_forced
    if ENVS[-1] != "local":
        pytest.skip("las muestras forzadas salen del juego local")
    now = contract_forced.build({t: a for t, (a, _) in outputs_by_env("local").items()})
    for name, a in now.items():
        path = os.path.join(contract_forced.FORCED_DIR, f"{name}.json")
        assert os.path.isfile(path), f"falta {path}: ../.venv313/bin/python tests/contract_forced.py --write"
        with open(path, encoding="utf-8") as fh:
            assert fh.read() == fb.stable_json(a), f"{name} desactualizada: tests/contract_forced.py --write"


@needs_node
def test_contract_check_detects_missing_field(outputs_by_env, tmp_path):
    """El guardián no es vacuo: sin `display.cover` en la salida, falla."""
    a = dict(outputs_by_env("local")["NFLX"][0])
    a["display"] = {k: v for k, v in a["display"].items() if k != "cover"}
    (tmp_path / "NFLX.json").write_text(fb.stable_json(a), encoding="utf-8")
    r = _run("check-contract.mjs", str(tmp_path))
    assert r.returncode == 1 and "display.cover" in r.stderr


@needs_node
def test_no_literal_thresholds_in_analysis_components():
    r = _run("check-analysis-literals.mjs")
    assert r.returncode == 0, r.stderr or r.stdout
