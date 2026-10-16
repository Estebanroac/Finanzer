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

import copy

import display
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
    # Caso raro que ningún ticker real cubre: categoría no concluyente (cobertura < 50%),
    # generado por el mismo display.build_display sobre SNOW prod forzado.
    a = copy.deepcopy(outputs_by_env(ENVS[-1])["SNOW"][0])
    a["score"]["breakdown"]["Crecimiento"].update(conclusive=False, coverage=0.33)
    a["display"] = display.build_display(a)
    extra = tmp_path / "forzado"
    extra.mkdir()
    (extra / "SNOW_no_concluyente.json").write_text(fb.stable_json(a), encoding="utf-8")
    # Etapa 9c, gráficos que ningún ticker de los 12 cubre: runway en años (pre-beneficio que
    # quema caja) y caja neta en Deuda neta / EBITDA.
    r = copy.deepcopy(outputs_by_env(ENVS[-1])["SNOW"][0])
    r["archetype_metrics"]["runway"] = {"state": "runway", "years": 1.8}
    r["display"] = display.build_display(r)
    assert r["display"]["charts"]["solvency"]["runway"].get("years") == 1.8
    (extra / "SNOW_runway.json").write_text(fb.stable_json(r), encoding="utf-8")
    n = copy.deepcopy(outputs_by_env(ENVS[-1])["V"][0])
    n["key_metrics"]["net_debt_to_ebitda"] = -0.4
    n["display"] = display.build_display(n)
    assert any(g.get("net_cash") for g in n["display"]["charts"]["solvency"]["gauges"])
    (extra / "V_caja_neta.json").write_text(fb.stable_json(n), encoding="utf-8")
    # Fase 2b (T5): EBIT < 0 con deuda neta (cobertura negativa). Con la deuda coherente con el EBITDA, SNOW pasó a
    # caja neta y ningún ticker de los juegos lo cubre.
    q = copy.deepcopy(outputs_by_env(ENVS[-1])["SNOW"][0])
    q["key_metrics"].update(net_debt=4e8, interest_coverage=-8.4, interest_coverage_state="negativa")
    q["display"] = display.build_display(q)
    assert any(g.get("negative") for g in q["display"]["charts"]["solvency"]["gauges"])
    (extra / "SNOW_cobertura_negativa.json").write_text(fb.stable_json(q), encoding="utf-8")
    r = _run("check-contract.mjs", "--strict-unions", *dirs, str(extra))
    assert r.returncode == 0, r.stderr or r.stdout


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
