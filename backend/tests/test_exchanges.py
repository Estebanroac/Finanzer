"""Rediseño E2a (T2): nombre de la bolsa en lugar del código del proveedor (NMS → Nasdaq)."""
import glob
import json

import exchanges


def test_codigos_conocidos():
    assert exchanges.name("NMS") == "Nasdaq"
    assert exchanges.name("NYQ") == "NYSE"
    assert exchanges.name("PAR") == "Euronext París"


def test_desconocido_se_muestra_tal_cual():
    assert exchanges.name("XYZ") == "XYZ"
    assert exchanges.name(None) is None
    assert exchanges.name("") is None


def test_todos_los_codigos_del_golden_tienen_nombre():
    codes = set()
    for p in glob.glob("tests/golden/*/*.json"):
        prof = (json.load(open(p, encoding="utf-8")) or {}).get("profile") or {}
        codes.add(prof.get("exchange_code") or prof.get("exchange"))
    assert {c for c in codes if c and exchanges.name(c) == c and c not in ("NYSE",)} == set()


def test_el_analisis_publica_el_nombre_y_conserva_el_codigo():
    import logging
    import fixture_backend as fb
    logging.disable(logging.CRITICAL)
    with fb.replay(fb.fixtures_dir("panel")) as store:
        a = fb.run_analysis("AAPL", store)
    assert a["profile"]["exchange"] == "Nasdaq"
    assert a["profile"]["exchange_code"] == "NMS"
