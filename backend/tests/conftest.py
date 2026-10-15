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
# Fase 0 del plan de fiabilidad: el juego panel (31 tickers) entra SOLO en la regresión y el determinismo.
# No se añade a ENVS: los tests de invariantes están escritos para los 6 tickers de local/prod, y lo que el
# panel revela es la línea base (docs/fiabilidad/F0_LINEA_BASE.md), no un fallo de la suite.
REG_ENVS = ENVS + ([fb.PANEL_ENV] if fb.panel_available() else [])
REG_ENV_TICKERS = [(e, t) for e in REG_ENVS for t in fb.env_tickers(e)]
# Fase 1 (D8): juegos para los tests ATADOS a los 6 tickers (NFLX, JPM, O, FCX, SNOW, V). "panel" sustituye al
# retirado "prod" como ruta de producción (plan B + Finnhub); solo se indexan esos 6 tickers.
BOUND_ENVS = ["local"] + ([fb.PANEL_ENV] if fb.panel_available() else [])


def env_id(param):
    return f"{param[0]}-{param[1]}" if isinstance(param, tuple) else str(param)


@pytest.fixture(scope="session")
def outputs_by_env():
    """{env: {TICKER: (analysis, pdf_bytes)}} desde fixtures, calculado una vez."""
    cache = {}

    def get(env):
        if env not in cache:
            cache[env] = fb.compute_outputs(fb.env_tickers(env), fb.fixtures_dir(env))
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
