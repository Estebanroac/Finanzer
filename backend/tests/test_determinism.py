"""Determinismo: mismas entradas congeladas -> salidas idénticas byte a byte
(análisis sin redondear y bytes del PDF), en el mismo proceso y entre
procesos con distinta semilla de hash (orden de sets/dicts de str), para
cada juego de datos disponible."""
import json
import os
import subprocess
import sys

import pytest

import fixture_backend as fb
from conftest import ENVS


def _hashes(res):
    return {s: [fb.sha256(fb.raw_json(a)), fb.sha256(pdf)] for s, (a, pdf) in res.items()}


@pytest.mark.parametrize("env", ENVS)
def test_same_process_twice_identical(env, outputs_by_env):
    second = fb.compute_outputs(fb.TICKERS, fb.fixtures_dir(env))
    assert _hashes(second) == _hashes(outputs_by_env(env))


@pytest.mark.parametrize("env", ENVS)
def test_across_processes_and_hash_seeds(env, outputs_by_env):
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixture_backend.py")
    runs = []
    for seed in ("0", "4242"):
        envvars = dict(os.environ, PYTHONHASHSEED=seed)
        envvars.pop("FINNHUB_API_KEY", None)
        out = subprocess.run([sys.executable, script, env], env=envvars, capture_output=True,
                             text=True, check=True, timeout=600).stdout
        runs.append(json.loads(out.strip().splitlines()[-1]))
    assert runs[0] == runs[1] == _hashes(outputs_by_env(env))
