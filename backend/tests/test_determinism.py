"""Determinismo: mismas entradas congeladas -> salidas idénticas byte a byte
(análisis sin redondear y bytes del PDF), en el mismo proceso y entre
procesos con distinta semilla de hash (orden de sets/dicts de str)."""
import json
import os
import subprocess
import sys

import fixture_backend as fb


def _hashes(res):
    return {s: [fb.sha256(fb.raw_json(a)), fb.sha256(pdf)] for s, (a, pdf) in res.items()}


def test_same_process_twice_identical(outputs):
    second = fb.compute_outputs(fb.TICKERS)
    assert _hashes(second) == _hashes(outputs)


def test_across_processes_and_hash_seeds(outputs):
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixture_backend.py")
    runs = []
    for seed in ("0", "4242"):
        env = dict(os.environ, PYTHONHASHSEED=seed)
        env.pop("FINNHUB_API_KEY", None)
        out = subprocess.run([sys.executable, script], env=env, capture_output=True,
                             text=True, check=True, timeout=600).stdout
        runs.append(json.loads(out.strip().splitlines()[-1]))
    assert runs[0] == runs[1] == _hashes(outputs)
