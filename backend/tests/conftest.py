import logging
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fixture_backend as fb  # noqa: E402

logging.disable(logging.CRITICAL)


@pytest.fixture(scope="session")
def outputs():
    """{TICKER: (analysis, pdf_bytes)} desde fixtures, calculado una vez."""
    return fb.compute_outputs(fb.TICKERS)


@pytest.fixture(scope="session")
def analysis(outputs):
    return lambda sym: outputs[sym.upper()][0]


@pytest.fixture(scope="session")
def fixture_store():
    """Acceso de solo lectura a los inputs crudos congelados."""
    store = fb.FixtureStore()
    for sym in fb.TICKERS:
        store.load(sym)
    return store
