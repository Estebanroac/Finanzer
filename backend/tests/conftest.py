import logging
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fixture_backend as fb  # noqa: E402

logging.disable(logging.CRITICAL)

# Juegos de datos presentes (local siempre; prod cuando se haya importado).
ENVS = fb.available_envs()
ENV_TICKERS = [(e, t) for e in ENVS for t in fb.TICKERS]


def env_id(param):
    return f"{param[0]}-{param[1]}" if isinstance(param, tuple) else str(param)


@pytest.fixture(scope="session")
def outputs_by_env():
    """{env: {TICKER: (analysis, pdf_bytes)}} desde fixtures, calculado una vez."""
    cache = {}

    def get(env):
        if env not in cache:
            cache[env] = fb.compute_outputs(fb.TICKERS, fb.fixtures_dir(env))
        return cache[env]
    return get


@pytest.fixture(scope="session")
def outputs(outputs_by_env):
    """Salidas del juego local (las que usan humo y bugs conocidos)."""
    return outputs_by_env("local")


@pytest.fixture(scope="session")
def analysis(outputs):
    return lambda sym: outputs[sym.upper()][0]


@pytest.fixture(scope="session")
def fixture_store():
    """Inputs crudos congelados del juego local (solo lectura)."""
    store = fb.FixtureStore(fb.fixtures_dir("local"))
    for sym in fb.TICKERS:
        store.load(sym)
    return store
