"""Regresión: el comportamiento actual desde fixtures == golden.

Si falla tras un cambio intencionado, revisa con `python3 tests/diff_golden.py`
y regenera de forma explícita. Los golden describen el comportamiento ACTUAL
(con sus bugs), no el correcto.
"""
import json
import os

import pytest

import fixture_backend as fb


def test_seams_exist():
    """Los puntos de enganche de la capa de inyección siguen existiendo."""
    assert fb.check_seams() == []


@pytest.mark.parametrize("sym", fb.TICKERS)
def test_fixtures_have_metadata(sym, fixture_store):
    meta = fixture_store.meta[sym]
    assert meta["ticker"] == sym
    assert meta["captured_at_utc"] and meta["versions"]["yfinance"]
    assert "participated" in meta["finnhub"]


@pytest.mark.parametrize("sym", fb.TICKERS)
def test_analysis_matches_golden(sym, analysis):
    jpath, _ = fb.golden_paths(sym)
    assert os.path.isfile(jpath), f"falta golden de {sym}: python3 tests/diff_golden.py --regenerate {sym}"
    with open(jpath, encoding="utf-8") as fh:
        golden = fh.read()
    current = fb.stable_json(analysis(sym))
    if current != golden:
        pytest.fail(f"{sym}: el análisis difiere del golden. Detalle: python3 tests/diff_golden.py {sym}")


@pytest.mark.parametrize("sym", fb.TICKERS)
def test_pdf_text_matches_golden(sym, outputs):
    _, tpath = fb.golden_paths(sym)
    with open(tpath, encoding="utf-8") as fh:
        golden = fh.read()
    if fb.pdf_text(outputs[sym][1]) != golden:
        pytest.fail(f"{sym}: el texto del PDF difiere del golden. Detalle: python3 tests/diff_golden.py {sym}")


def test_replay_uses_only_recorded_inputs():
    """Ningún acceso del pipeline queda sin servir desde los fixtures."""
    with fb.replay() as store:
        for sym in fb.TICKERS:
            fb.run_analysis(sym, store)
        assert store.misses == []


def test_golden_is_valid_json():
    for sym in fb.TICKERS:
        with open(fb.golden_paths(sym)[0], encoding="utf-8") as fh:
            assert json.load(fh)["symbol"] == sym
